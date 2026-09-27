"""Apple App Store top charts via Apple's public marketing RSS (no key required).

Charts have no per-item timestamps, so these signals feed rank-based
engagement rather than momentum.
"""

from __future__ import annotations

from ..http import get_json
from ..models import Signal

NAME = "appstore"
CHARTS = ["top-free", "top-paid"]
COUNTRY = "us"
LIMIT = 100


def parse(payload: dict, chart: str = "top-free") -> list[Signal]:
    results = payload.get("feed", {}).get("results", [])
    signals = []
    for rank, app in enumerate(results, start=1):
        genres = " ".join(g.get("name", "") for g in app.get("genres", []))
        signals.append(
            Signal(
                source=NAME,
                title=app.get("name", ""),
                text=f"{genres} {chart}",
                url=app.get("url", ""),
                rank=rank,
                # Map chart position onto an upvote-like scale: #1 ~ 1000, #100 ~ 10.
                engagement=1000.0 / rank,
            )
        )
    return signals


def fetch(days: int) -> list[Signal]:  # noqa: ARG001 - charts are "now"
    signals = []
    for chart in CHARTS:
        url = f"https://rss.applemarketingtools.com/api/v2/{COUNTRY}/apps/{chart}/{LIMIT}/apps.json"
        signals += parse(get_json(url), chart)
    return signals
