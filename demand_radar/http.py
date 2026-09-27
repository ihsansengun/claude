"""Tiny stdlib HTTP helper so the tool has no third-party dependencies."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request

USER_AGENT = "demand-radar/0.1 (+https://github.com/ihsansengun/claude)"


def get(url: str, *, headers: dict[str, str] | None = None, retries: int = 2, timeout: float = 20) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **(headers or {})})
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except urllib.error.HTTPError as exc:
            # Retry only on rate limiting / transient server errors.
            if exc.code not in (429, 500, 502, 503, 504) or attempt == retries:
                raise
        except urllib.error.URLError:
            if attempt == retries:
                raise
        time.sleep(2 ** (attempt + 1))
    raise RuntimeError("unreachable")


def get_json(url: str, **kwargs) -> object:
    return json.loads(get(url, **kwargs))
