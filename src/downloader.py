import os
from dataclasses import dataclass
from typing import Optional

from .config import DOWNLOAD_TIMEOUT, HEADERS, MIME_TO_EXT
from .utils import sanitize_filename


@dataclass
class DownloadResult:
    status: str
    path: Optional[str] = None
    error: Optional[str] = None


class PhotoDownloader:
    def __init__(self, session, download_root):
        self.session = session
        self.download_root = download_root

    def _ensure_dir(self):
        os.makedirs(self.download_root, exist_ok=True)
        return self.download_root

    def download(self, photo, custom_name=None):
        try:
            out_dir = self._ensure_dir()
            base_name = custom_name if custom_name else photo["title"]
            clean_name = sanitize_filename(base_name)

            resp = self.session.get(
                photo["url"], headers=HEADERS, timeout=DOWNLOAD_TIMEOUT, stream=True
            )
            if resp.status_code != 200:
                return DownloadResult("failed", error=f"HTTP {resp.status_code}")

            content_type = resp.headers.get("Content-Type", "").split(";")[0].strip().lower()
            ext = MIME_TO_EXT.get(content_type)
            if not ext:
                ext = os.path.splitext(photo["url"].split("?")[0])[-1] or ".jpg"

            target_path = os.path.join(out_dir, f"{clean_name}{ext}")

            if os.path.exists(target_path) and os.path.getsize(target_path) > 0 and not custom_name:
                return DownloadResult("exists", path=target_path)

            counter = 1
            root, ext_part = os.path.splitext(target_path)
            while os.path.exists(target_path) and os.path.getsize(target_path) > 0:
                target_path = f"{root}_{counter}{ext_part}"
                counter += 1

            with open(target_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=65536):
                    f.write(chunk)

            return DownloadResult("saved", path=target_path)
        except Exception as e:
            return DownloadResult("failed", error=str(e))

    def download_all(self, photos, on_progress=None, cancel_evt=None):
        results = []
        total = len(photos)
        for i, photo in enumerate(photos, 1):
            if cancel_evt is not None and cancel_evt.is_set():
                break
            result = self.download(photo)
            results.append(result)
            if on_progress:
                on_progress(i, total, result)
        return results
