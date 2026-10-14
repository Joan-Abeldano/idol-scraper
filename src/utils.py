import re
from urllib.parse import parse_qs, unquote, urlparse


def extract_real_url(raw_url):
    raw_url = (raw_url or "").replace(r"\/", "/")
    if "/api/kpics-image" in raw_url or "/_next/image" in raw_url:
        parsed = urlparse(raw_url)
        qs = parse_qs(parsed.query)
        if "url" in qs and qs["url"]:
            return unquote(qs["url"][0])
    return raw_url


def slugify(text):
    return re.sub(r"[^a-zA-Z0-9]+", "-", (text or "")).strip("-")


def sanitize_filename(name, fallback="kpop_photo"):
    cleaned = re.sub(r'[\\/*?:"<>|]', "", name or "").strip()
    return cleaned or fallback
