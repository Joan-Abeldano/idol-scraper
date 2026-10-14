import re
import string
import urllib.parse
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .cache import LRUImageCache
from .config import (
    ALBUM_CACHE_CAPACITY,
    ALBUM_WORKERS,
    BASE_URL,
    DIRECTORY_WORKERS,
    HEADERS,
    PHOTO_PAGE_LIMIT,
    REQUEST_TIMEOUT,
    RSC_HEADERS,
)
from .utils import extract_real_url, slugify

EVENT_STATUS = "status"
EVENT_IDOLS = "idols"

_UUID_RE = re.compile(
    r"([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})"
)
_UUID_QUERY_RE = re.compile(
    r"idol=([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})"
)


class KpoppingScraper:
    def __init__(self, session, db=None):
        self.session = session
        self.db = db
        self._album_cache = LRUImageCache(capacity=ALBUM_CACHE_CAPACITY)

    def harvest_directory(self, known_idols=None):
        found_idols = {item["slug"]: item for item in (known_idols or [])}
        alphabet = ["num"] + list(string.ascii_uppercase)

        yield EVENT_STATUS, "Fetching idol directory sections..."
        with ThreadPoolExecutor(max_workers=DIRECTORY_WORKERS) as executor:
            pages = list(executor.map(self._fetch_section, alphabet))

        for letter, html in zip(alphabet, pages):
            yield EVENT_STATUS, f"Scanning letter section '{letter}'..."
            if not html:
                continue

            try:
                batch = []

                json_matches = re.findall(
                    r'"id":"([^"]+)","name":"([^"]+)".*?"group":"([^"]*)"', html
                )
                for idol_id, name, group in json_matches:
                    if idol_id not in found_idols and not idol_id.startswith("$"):
                        clean_grp = group if group and group != "$undefined" else ""
                        display_name = f"{name} ({clean_grp})" if clean_grp else name
                        item = {
                            "name": display_name,
                            "raw_name": name,
                            "slug": idol_id,
                            "url": f"{BASE_URL}/profiles/idol/{idol_id}",
                            "uuid": None,
                            "group": clean_grp,
                        }
                        found_idols[idol_id] = item
                        batch.append(item)

                soup = BeautifulSoup(html, "html.parser")
                for a in soup.find_all("a", href=True):
                    href = a["href"]
                    if "/profiles/idol/" in href:
                        slug = href.split("?")[0].rstrip("/").split("/")[-1]
                        if slug and slug not in found_idols:
                            raw_name = a.get_text(strip=True) or slug.replace("-", " ").title()
                            item = {
                                "name": raw_name,
                                "raw_name": raw_name,
                                "slug": slug,
                                "url": f"{BASE_URL}/profiles/idol/{slug}",
                                "uuid": None,
                                "group": "",
                            }
                            found_idols[slug] = item
                            batch.append(item)

                if batch:
                    self._save(batch)
                    yield EVENT_IDOLS, batch

            except Exception:
                continue

        for sm in (
            f"{BASE_URL}/sitemap-idols.xml",
            f"{BASE_URL}/sitemap.xml",
            f"{BASE_URL}/sitemap-0.xml",
        ):
            try:
                resp = self.session.get(sm, headers=HEADERS, timeout=10)
                if resp.status_code == 200 and "xml" in resp.headers.get("Content-Type", ""):
                    root = ET.fromstring(resp.content)
                    urls = root.findall(
                        ".//{http://www.sitemaps.org/schemas/sitemap/0.9}loc"
                    ) or root.findall(".//loc")
                    batch = []
                    for u in urls:
                        link = (u.text or "").strip()
                        if "/profiles/idol/" in link:
                            slug = link.rstrip("/").split("/")[-1]
                            if slug and slug not in found_idols:
                                raw_name = slug.replace("-", " ").title()
                                item = {
                                    "name": raw_name,
                                    "raw_name": raw_name,
                                    "slug": slug,
                                    "url": link,
                                    "uuid": None,
                                    "group": "",
                                }
                                found_idols[slug] = item
                                batch.append(item)
                    if batch:
                        self._save(batch)
                        yield EVENT_IDOLS, batch
            except Exception:
                pass

    def _fetch_section(self, letter):
        target_url = f"{BASE_URL}/idols/female?letter={letter}"
        try:
            resp = self.session.get(
                target_url, headers=RSC_HEADERS, timeout=REQUEST_TIMEOUT
            )
            return resp.text
        except Exception:
            return None

    def scrape_group_members(self, group_name):
        slug = slugify(group_name)
        candidates = [
            f"{BASE_URL}/profiles/group/{slug}",
            f"{BASE_URL}/profiles/group/{group_name}",
        ]

        found_members = []
        for url in candidates:
            try:
                resp = self.session.get(url, headers=HEADERS, timeout=10)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    for a in soup.find_all("a", href=True):
                        href = a["href"]
                        if "/profiles/idol/" in href:
                            m_slug = href.split("?")[0].rstrip("/").split("/")[-1]
                            raw_name = a.get_text(strip=True) or m_slug.replace("-", " ").title()
                            if m_slug and raw_name and raw_name.lower() != "idols":
                                if not any(x["slug"] == m_slug for x in found_members):
                                    found_members.append(
                                        {
                                            "slug": m_slug,
                                            "raw_name": raw_name,
                                            "name": f"{raw_name} ({group_name})",
                                            "url": urljoin(BASE_URL, href),
                                            "uuid": None,
                                            "group": group_name,
                                        }
                                    )
                    if found_members:
                        break
            except Exception:
                continue

        if found_members:
            self._save(found_members)
        return found_members

    def discover_uuid(self, idol):
        try:
            resp = self.session.get(idol["url"], headers=HEADERS, timeout=REQUEST_TIMEOUT)
            if resp.status_code == 200:
                html = resp.text
                match = _UUID_QUERY_RE.search(html) or _UUID_RE.search(html)
                if match:
                    uuid = match.group(1)
                    idol["uuid"] = uuid
                    if self.db:
                        self.db.update_uuid(idol["slug"], uuid)
                    return uuid
        except Exception:
            pass
        return None

    def fetch_album_photos(self, slug, album_title, cancel_evt=None):
        if cancel_evt is not None and cancel_evt.is_set():
            return []

        cached = self._album_cache.get(slug)
        if cached is not None:
            return cached

        album_url = f"{BASE_URL}/kpics/{slug}"
        photos = []
        seen = set()

        try:
            resp = self.session.get(album_url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            if resp.status_code == 200:
                html = resp.text

                album_section = re.search(r'\\?"albumImages\\?":\s*\[(.*?)\]', html, re.DOTALL)
                if album_section:
                    raw_block = album_section.group(1)
                    found_srcs = re.findall(r'\\?"src\\?":\s*\\?"([^\\",]+)\\?"', raw_block)
                    for idx, src in enumerate(found_srcs, 1):
                        clean_url = extract_real_url(src)
                        if clean_url not in seen:
                            seen.add(clean_url)
                            photos.append(
                                {"title": f"{album_title} (#{idx})", "url": clean_url}
                            )

                if not photos:
                    soup = BeautifulSoup(html, "html.parser")
                    for btn in soup.find_all("button", attrs={"data-photo-index": True}):
                        img = btn.find("img")
                        if img:
                            src = img.get("src") or img.get("data-src")
                            if src:
                                clean_url = extract_real_url(urljoin(BASE_URL, src))
                                if clean_url not in seen:
                                    seen.add(clean_url)
                                    photos.append(
                                        {
                                            "title": f"{album_title} (#{len(photos) + 1})",
                                            "url": clean_url,
                                        }
                                    )
        except Exception:
            pass

        self._album_cache.put(slug, photos)
        return photos

    def fetch_idol_photos(
        self,
        idol,
        cancel_evt,
        on_status=None,
        on_batch=None,
        on_empty=None,
    ):
        def status(text):
            if on_status:
                on_status(text)

        seen_urls = set()
        emitted = 0
        uuid = idol.get("uuid")

        if not uuid and not cancel_evt.is_set():
            uuid = self.discover_uuid(idol)

        if not uuid or cancel_evt.is_set():
            if not cancel_evt.is_set():
                status(f"Could not locate UUID for {idol['raw_name']}.")
            return

        offset = 0
        all_albums = []
        while not cancel_evt.is_set():
            api_url = (
                f"{BASE_URL}/api/photos?idolId={urllib.parse.quote(uuid)}"
                f"&limit={PHOTO_PAGE_LIMIT}&offset={offset}&sort=hot"
            )
            try:
                resp = self.session.get(api_url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
                if resp.status_code != 200:
                    break

                items = resp.json()
                if not isinstance(items, list) or len(items) == 0:
                    break

                all_albums.extend(items)
                offset += len(items)

                if len(items) < PHOTO_PAGE_LIMIT:
                    break
            except Exception:
                break

        if cancel_evt.is_set():
            return

        if not all_albums:
            status(f"No photos found for {idol['raw_name']}.")
            if on_empty:
                on_empty()
            return

        status(f"Found {len(all_albums)} albums. Extracting every photo...")

        def process_item(item):
            if cancel_evt.is_set():
                return []

            title = item.get("title") or idol["raw_name"]
            src = extract_real_url(item.get("src", ""))
            album_count = item.get("albumCount") or 1
            slug = item.get("slug")

            if album_count > 1 and slug:
                detailed = self.fetch_album_photos(slug, title, cancel_evt)
                if detailed:
                    return detailed

            if src:
                return [{"title": title, "url": src}]
            return []

        with ThreadPoolExecutor(max_workers=ALBUM_WORKERS) as executor:
            for album_photos in executor.map(process_item, all_albums):
                if cancel_evt.is_set():
                    return

                new_batch = []
                for p in album_photos:
                    if p["url"] not in seen_urls:
                        seen_urls.add(p["url"])
                        new_batch.append(p)

                if new_batch:
                    emitted += len(new_batch)
                    if on_batch:
                        on_batch(new_batch)

        if not cancel_evt.is_set():
            status(
                f"Completed! Loaded {emitted:,} working photos for {idol['raw_name']}."
            )

    def _save(self, idols):
        if self.db:
            self.db.save_idols_batch(idols)
