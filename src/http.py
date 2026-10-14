import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .config import HTTP_POOL_SIZE


def create_session(pool_size=HTTP_POOL_SIZE):
    session = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=[500, 502, 503, 504],
    )
    adapter = HTTPAdapter(
        pool_connections=pool_size,
        pool_maxsize=pool_size,
        max_retries=retries,
    )
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session
