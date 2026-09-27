"""Hacker News via the public Algolia search API (no key required)."""

from __future__ import annotations

import urllib.parse
from datetime import datetime, timedelta, timezone

from ..http import get_json
from ..models import Signal

NAME = "hackernews"

# Queries that surface launches and explicit asks for tools.
QUERIES = [
    "Show HN",
    "Ask HN is there a tool",
    "Ask HN is there an app",
    "I would pay for",
    "alternative to",
    "wish there was",
]


def parse(payload: dict) -> list[Signal]:
    signals = []
    for hit in payload.get("hits", []):
        title = hit.get("title") or hit.get("story_title")
        if not title:
            continue
        object_id = hit.get("objectID", "")
        signals.append(
            Signal(
                source=NAME,
                title=title,
                text=hit.get("story_text") or "",
                url=hit.get("url") or f"https://news.ycombinator.com/item?id={object_id}",
                created_at=datetime.fromtimestamp(hit["created_at_i"], tz=timezone.utc) if hit.get("created_at_i") else None,
                engagement=float(hit.get("points") or 0),
                comments=float(hit.get("num_comments") or 0),
            )
        )
    return signals


def fetch(days: int) -> list[Signal]:
    since = int((datetime.now(timezone.utc) - timedelta(days=days)).timestamp())
    seen: dict[str, Signal] = {}
    for query in QUERIES:
        params = urllib.parse.urlencode(
            {"query": query, "tags": "story", "numericFilters": f"created_at_i>{since}", "hitsPerPage": 100}
        )
        for sig in parse(get_json(f"https://hn.algolia.com/api/v1/search?{params}")):
            seen.setdefault(sig.url, sig)
    return list(seen.values())
