"""Shared HTTP client with retries for external API calls."""

from __future__ import annotations

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from settings import APP_VERSION

DEFAULT_TIMEOUT = 30


def _build_session() -> requests.Session:
    retry = Retry(
        total=3,
        connect=3,
        read=3,
        status=3,
        backoff_factor=0.75,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET"}),
        respect_retry_after_header=True,
    )
    session = requests.Session()
    session.headers.update({"User-Agent": f"war-dashboard/{APP_VERSION}"})
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


SESSION = _build_session()


def http_get(url: str, *, params: dict | None = None, timeout: int = DEFAULT_TIMEOUT) -> requests.Response:
    """Issue a retried GET request through the shared session."""
    return SESSION.get(url, params=params, timeout=timeout)