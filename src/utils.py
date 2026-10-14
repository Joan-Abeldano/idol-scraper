import re
from urllib.parse import parse_qs, quote, unquote, urlparse

from .config import BASE_URL


def extract_real_url(raw_url):
    raw_url = (raw_url or "").replace(r"\/", "/")
    if "/api/kpics-image" in raw_url or "/_next/image" in raw_url:
        parsed = urlparse(raw_url)
        qs = parse_qs(parsed.query)
        if "url" in qs and qs["url"]:
            return unquote(qs["url"][0])
    return raw_url


def build_preview_url(real_url, width, quality=75):
    if not real_url:
        return real_url
    if "/_next/image" in real_url:
        return real_url
    return f"{BASE_URL}/_next/image?url={quote(real_url, safe='')}&w={width}&q={quality}"


def slugify(text):
    return re.sub(r"[^a-zA-Z0-9]+", "-", (text or "")).strip("-")


def sanitize_filename(name, fallback="kpop_photo"):
    cleaned = re.sub(r'[\\/*?:"<>|]', "", name or "").strip()
    return cleaned or fallback
