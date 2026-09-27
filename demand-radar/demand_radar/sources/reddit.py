"""Reddit via the public .json listings (no key required, but rate limited)."""

from __future__ import annotations

import urllib.parse
from datetime import datetime, timedelta, timezone

from ..http import get_json
from ..models import Signal

NAME = "reddit"

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


def fetch(days: int) -> list[Signal]:
    t = _window(days)
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    urls = [f"https://www.reddit.com/r/{sub}/top.json?t={t}&limit=100" for sub in SUBREDDITS]
    urls += [
        "https://www.reddit.com/search.json?" + urllib.parse.urlencode({"q": q, "t": t, "sort": "top", "limit": 100})
        for q in SEARCHES
    ]
    seen: dict[str, Signal] = {}
    for url in urls:
        for sig in parse(get_json(url)):
            if sig.created_at is None or sig.created_at >= cutoff:
                seen.setdefault(sig.url, sig)
    return list(seen.values())
