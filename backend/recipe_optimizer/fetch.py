"""Polite, cached HTTP access.

Every response is stored on disk, so a page is requested once and then reused.
Real network requests are spaced by ``REQUEST_DELAY_SECONDS``.
"""
from __future__ import annotations

import hashlib
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from . import config

log = logging.getLogger(__name__)
_last_request_at = 0.0


class FetchError(RuntimeError):
    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


def cache_path(namespace: str, url: str, form: dict | None, suffix: str) -> Path:
    key = url + ("|" + urllib.parse.urlencode(sorted(form.items())) if form else "")
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]
    return config.RAW_DIR / namespace / f"{digest}{suffix}"


def fetch(
    url: str,
    namespace: str,
    *,
    form: dict | None = None,
    suffix: str = ".dat",
    refresh: bool = False,
    offline: bool = False,
    retries: int = 2,
) -> bytes:
    """Return the response body for ``url``, reading the on-disk cache first."""
    global _last_request_at
    target = cache_path(namespace, url, form, suffix)
    if target.exists() and not refresh:
        log.debug("cache hit %s", url)
        return target.read_bytes()
    if offline:
        raise FetchError(f"Not cached and offline mode is on: {url}")

    data = urllib.parse.urlencode(form).encode("utf-8") if form else None
    last_error: FetchError | None = None
    for attempt in range(retries + 1):
        wait = config.REQUEST_DELAY_SECONDS - (time.monotonic() - _last_request_at)
        if wait > 0:
            time.sleep(wait)
        _last_request_at = time.monotonic()
        try:
            request = urllib.request.Request(url, data=data, headers={"User-Agent": config.USER_AGENT})
            with urllib.request.urlopen(request, timeout=config.REQUEST_TIMEOUT_SECONDS) as response:
                body = response.read()
        except urllib.error.HTTPError as error:
            last_error = FetchError(f"HTTP {error.code} for {url}", error.code)
            # 4xx (other than rate limiting) will not improve on retry.
            if error.code < 500 and error.code != 429:
                break
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as error:
            last_error = FetchError(f"Request failed for {url}: {error}")
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary = target.with_suffix(target.suffix + ".part")
            temporary.write_bytes(body)
            temporary.replace(target)
            log.info("fetched %s (%d bytes)", url, len(body))
            return body
        if attempt < retries:
            log.warning("%s; retrying", last_error)
            time.sleep(config.REQUEST_DELAY_SECONDS * (attempt + 2))
    assert last_error is not None
    raise last_error
