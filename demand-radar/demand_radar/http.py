"""Tiny stdlib HTTP helper so the tool has no third-party dependencies."""

from __future__ import annotations

import functools
import json
import os
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.request

USER_AGENT = "demand-radar/0.1 (+https://github.com/ihsansengun/claude)"

# System + admin/MDM-installed roots (e.g. a corporate TLS-inspection CA), and the user's login keychain.
MACOS_KEYCHAINS = [
    "/System/Library/Keychains/SystemRootCertificates.keychain",
    "/Library/Keychains/System.keychain",
    os.path.expanduser("~/Library/Keychains/login.keychain-db"),
]


def _keychain_pem() -> str:
    keychains = [k for k in MACOS_KEYCHAINS if os.path.exists(k)]
    result = subprocess.run(
        ["security", "find-certificate", "-a", "-p", *keychains], capture_output=True, text=True, timeout=30
    )
    return result.stdout


def _load_pem_bundle(ctx: ssl.SSLContext, pem: str) -> int:
    """Load each certificate separately so one odd keychain entry can't sink the rest."""
    loaded = 0
    end = "-----END CERTIFICATE-----"
    for chunk in pem.split(end):
        if "-----BEGIN CERTIFICATE-----" not in chunk:
            continue
        try:
            ctx.load_verify_locations(cadata=chunk[chunk.index("-----BEGIN"):] + end + "\n")
            loaded += 1
        except ssl.SSLError:
            pass
    return loaded


def _has_default_cas() -> bool:
    paths = ssl.get_default_verify_paths()
    if paths.cafile and os.path.isfile(paths.cafile):
        return True
    return bool(paths.capath and os.path.isdir(paths.capath) and os.listdir(paths.capath))


@functools.lru_cache(maxsize=None)
def ssl_context() -> ssl.SSLContext:
    """A verifying TLS context that also trusts what the operating system trusts.

    Python from python.org on macOS ships without any CA certificates, and
    networks that inspect TLS use a company root that only the Keychain knows
    about. Either way plain `urlopen` fails with CERTIFICATE_VERIFY_FAILED
    while browsers work. So on macOS we add the Keychain's certificates, and
    elsewhere fall back to certifi when Python has no CA bundle at all.
    `SSL_CERT_FILE` is honoured as usual via the default context.
    """
    ctx = ssl.create_default_context()
    if sys.platform == "darwin":
        try:
            _load_pem_bundle(ctx, _keychain_pem())
        except (OSError, subprocess.SubprocessError):
            pass
    if not _has_default_cas():
        try:
            import certifi

            ctx.load_verify_locations(certifi.where())
        except ImportError:
            pass
    return ctx


def get(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    data: bytes | None = None,
    retries: int = 2,
    timeout: float = 20,
) -> bytes:
    """Fetch a URL (POST when `data` is given) with retries on transient errors."""
    req = urllib.request.Request(url, data=data, headers={"User-Agent": USER_AGENT, **(headers or {})})
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=ssl_context()) as resp:
                return resp.read()
        except urllib.error.HTTPError as exc:
            # Retry only on rate limiting / transient server errors.
            if exc.code not in (429, 500, 502, 503, 504) or attempt == retries:
                raise
        except urllib.error.URLError as exc:
            # A certificate failure won't fix itself on retry.
            if attempt == retries or isinstance(exc.reason, ssl.SSLCertVerificationError):
                raise
        time.sleep(2 ** (attempt + 1))
    raise RuntimeError("unreachable")


def get_json(url: str, **kwargs) -> object:
    return json.loads(get(url, **kwargs))
