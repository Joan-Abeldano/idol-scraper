import os
import sys

PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
if getattr(sys, "frozen", False):
    PROJECT_ROOT = os.path.dirname(sys.executable)
else:
    PROJECT_ROOT = os.path.dirname(PACKAGE_DIR)

DATA_DIR = os.environ.get("KPOP_DATA_DIR", PROJECT_ROOT)
DOWNLOAD_ROOT = os.path.join(DATA_DIR, "kpop_downloaded")
DB_PATH = os.path.join(DATA_DIR, "kpop_cache.db")

BASE_URL = "https://kpopping.com"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

RSC_HEADERS = {
    **HEADERS,
    "RSC": "1",
    "Next-Url": "/idols/female",
}

REQUEST_TIMEOUT = 12
DOWNLOAD_TIMEOUT = 25
HTTP_POOL_SIZE = 25

PHOTO_PAGE_LIMIT = 50
ALBUM_WORKERS = 4

SEARCH_DEBOUNCE_MS = 150
THUMB_CACHE_CAPACITY = 120

MIME_TO_EXT = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "image/avif": ".avif",
}
