"""GitHub: fastest-starred new repositories. Set GITHUB_TOKEN for higher rate limits."""

from __future__ import annotations

import os
import urllib.parse
from datetime import datetime, timedelta, timezone

from ..http import get_json
from ..models import Signal

NAME = "github"


def parse(payload: dict) -> list[Signal]:
    signals = []
    for repo in payload.get("items", []):
        topics = " ".join(repo.get("topics") or [])
        signals.append(
            Signal(
                source=NAME,
                title=f"{repo.get('name', '')}: {repo.get('description') or ''}".strip(": "),
                text=topics,
                url=repo.get("html_url", ""),
                created_at=datetime.fromisoformat(repo["created_at"].replace("Z", "+00:00")) if repo.get("created_at") else None,
                engagement=float(repo.get("stargazers_count") or 0),
                comments=float(repo.get("forks_count") or 0),
            )
        )
    return signals


def fetch(days: int) -> list[Signal]:
    since = (datetime.now(timezone.utc) - timedelta(days=days)).date().isoformat()
    headers = {"Accept": "application/vnd.github+json"}
    if token := os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = f"Bearer {token}"
    params = urllib.parse.urlencode({"q": f"created:>{since} stars:>25", "sort": "stars", "order": "desc", "per_page": 100})
    return parse(get_json(f"https://api.github.com/search/repositories?{params}", headers=headers))
