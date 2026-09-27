"""Reddit listings and searches.

Reddit blocks most anonymous scripted traffic (HTTP 403 "Blocked"), so the
reliable path is the official API with a free "script" app:

1. Go to https://www.reddit.com/prefs/apps and click "create another app".
2. Pick "script", name it anything, redirect uri http://localhost:8080.
3. export REDDIT_CLIENT_ID=<id under the app name> REDDIT_CLIENT_SECRET=<secret>

With those set, requests go through oauth.reddit.com using an app-only token
(read-only, no Reddit password needed). Without them we try the public .json
endpoints, which may work depending on your network.
"""

from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.parse
from datetime import datetime, timedelta, timezone

from ..http import get, get_json
from ..models import Signal

NAME = "reddit"
# Reddit asks for a unique, descriptive user agent and throttles generic ones.
REDDIT_UA = f"python:demand-radar:0.1 (by /u/{os.environ.get('REDDIT_USERNAME', 'demand-radar')})"
SETUP_HINT = (
    "Reddit blocked the anonymous request. Create a free API app at https://www.reddit.com/prefs/apps "
    "(type: script) and set REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET; see demand-radar/README.md."
)

# Communities where people ask for, pitch, or launch apps.
SUBREDDITS = ["SomebodyMakeThis", "AppIdeas", "SideProject", "startups", "SaaS", "Entrepreneur", "androidapps", "iosapps"]
SEARCHES = ['"is there an app"', '"i would pay for"', '"looking for an app"', '"wish there was an app"']


def parse(payload: dict) -> list[Signal]:
    signals = []
    for child in payload.get("data", {}).get("children", []):
        post = child.get("data", {})
        if not post.get("title"):
            continue
        signals.append(
            Signal(
                source=NAME,
                title=post["title"],
                text=(post.get("selftext") or "")[:2000],
                url="https://www.reddit.com" + post.get("permalink", ""),
                created_at=datetime.fromtimestamp(post["created_utc"], tz=timezone.utc) if post.get("created_utc") else None,
                engagement=float(post.get("score") or 0),
                comments=float(post.get("num_comments") or 0),
            )
        )
    return signals


def _window(days: int) -> str:
    return "week" if days <= 7 else "month" if days <= 31 else "year"


def app_token(client_id: str, client_secret: str) -> str:
    """App-only OAuth token (client credentials grant): read access, no user login."""
    basic = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    body = get(
        "https://www.reddit.com/api/v1/access_token",
        data=urllib.parse.urlencode({"grant_type": "client_credentials"}).encode(),
        headers={"Authorization": f"Basic {basic}", "User-Agent": REDDIT_UA},
    )
    token = json.loads(body).get("access_token")
    if not token:
        raise RuntimeError(f"Reddit OAuth failed: {body[:200]!r} (check REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET)")
    return token


def listing_urls(days: int, base: str) -> list[str]:
    t = _window(days)
    suffix = ".json" if base == "https://www.reddit.com" else ""
    urls = [f"{base}/r/{sub}/top{suffix}?t={t}&limit=100&raw_json=1" for sub in SUBREDDITS]
    urls += [
        f"{base}/search{suffix}?"
        + urllib.parse.urlencode({"q": q, "t": t, "sort": "top", "limit": 100, "raw_json": 1})
        for q in SEARCHES
    ]
    return urls


def fetch(days: int) -> list[Signal]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    client_id, secret = os.environ.get("REDDIT_CLIENT_ID"), os.environ.get("REDDIT_CLIENT_SECRET")
    if client_id and secret:
        base = "https://oauth.reddit.com"
        headers = {"Authorization": f"bearer {app_token(client_id, secret)}", "User-Agent": REDDIT_UA}
    else:
        base, headers = "https://www.reddit.com", {"User-Agent": REDDIT_UA}

    seen: dict[str, Signal] = {}
    for url in listing_urls(days, base):
        try:
            payload = get_json(url, headers=headers)
        except urllib.error.HTTPError as exc:
            if exc.code == 403 and base == "https://www.reddit.com":
                raise RuntimeError(SETUP_HINT) from exc
            raise
        for sig in parse(payload):
            if sig.created_at is None or sig.created_at >= cutoff:
                seen.setdefault(sig.url, sig)
    return list(seen.values())
