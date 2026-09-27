"""Score concepts on how popular and in-demand they look right now.

Five components, each turned into a 0-1 percentile across concepts so no one
source's scale (HN points vs GitHub stars vs chart rank) dominates:

- engagement: how much attention matching signals got (log-damped, so one viral
  post doesn't swamp many solid ones)
- volume:     how many distinct signals mention the concept
- momentum:   recent half of the window vs the older half (is it accelerating?)
- intent:     how many signals are explicit asks ("is there an app", "I'd pay")
- diversity:  how many independent sources agree
- search:     growth in search interest (Google Trends), recent half vs older
              half; only used when search series were collected

The final score is a weighted sum scaled to 0-100.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

from .extract import has_intent
from .models import ConceptScore, Signal

DEFAULT_WEIGHTS = {
    "engagement": 0.30,
    "volume": 0.15,
    "momentum": 0.20,
    "intent": 0.25,
    "diversity": 0.10,
    "search": 0.15,
}


def _engagement(signals: list[Signal]) -> float:
    return sum(math.log1p(s.engagement) + 0.5 * math.log1p(s.comments) for s in signals)


def _momentum(signals: list[Signal], now: datetime, days: int) -> float:
    """Ratio of recent to older activity, smoothed. >1 means growing."""
    mid = now - timedelta(days=days / 2)
    start = now - timedelta(days=days)
    recent = older = 0.0
    for s in signals:
        if s.created_at is None or s.created_at < start:
            continue
        weight = 1 + math.log1p(s.engagement)
        if s.created_at >= mid:
            recent += weight
        else:
            older += weight
    # +2 smoothing keeps tiny concepts (1 post vs 0) from looking explosive.
    return (recent + 2) / (older + 2)


def _search_growth(series: list[Signal], now: datetime, days: int) -> float | None:
    """Mean search interest in the recent half of the window over the older half.

    Trends values are 0-100 relative to each term's own peak, so only a term's
    change over time is meaningful, not its level.
    """
    mid = now - timedelta(days=days / 2)
    start = now - timedelta(days=days)
    recent = [s.engagement for s in series if s.created_at and s.created_at >= mid]
    older = [s.engagement for s in series if s.created_at and start <= s.created_at < mid]
    if not recent or not older:
        return None
    # +1 smoothing so a term going from ~0 to 2 doesn't read as infinite growth.
    return (sum(recent) / len(recent) + 1) / (sum(older) / len(older) + 1)


def _percentiles(values: list[float]) -> list[float]:
    """Average-rank percentile in [0, 1]; ties share a rank."""
    if len(values) <= 1:
        return [1.0 if values and values[0] > 0 else 0.0 for _ in values]
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        avg = (i + j) / 2
        for k in range(i, j + 1):
            ranks[order[k]] = avg / (len(values) - 1)
        i = j + 1
    return ranks


def score_concepts(
    buckets: dict[str, list[Signal]],
    *,
    days: int,
    now: datetime | None = None,
    weights: dict[str, float] | None = None,
    min_volume: int = 2,
    examples: int = 5,
) -> list[ConceptScore]:
    now = now or datetime.now(timezone.utc)
    weights = weights or DEFAULT_WEIGHTS
    concepts, series = [], []
    for c, sigs in buckets.items():
        posts = [s for s in sigs if s.series_for is None]
        if len(posts) >= min_volume:
            concepts.append((c, posts))
            series.append([s for s in sigs if s.series_for is not None])
    if not concepts:
        return []
    growth = [_search_growth(s, now, days) for s in series]

    raw = {
        "engagement": [_engagement(s) for _, s in concepts],
        "volume": [float(len(s)) for _, s in concepts],
        "momentum": [_momentum(s, now, days) for _, s in concepts],
        "intent": [float(sum(has_intent(x) for x in s)) for _, s in concepts],
        "diversity": [float(len({x.source for x in s})) for _, s in concepts],
        # Concepts without search data sit at neutral (no growth) rather than bottom.
        "search": [1.0 if g is None else g for g in growth],
    }
    if all(g is None for g in growth):
        weights = {k: w for k, w in weights.items() if k != "search"}
    pct = {k: _percentiles(v) for k, v in raw.items()}
    total_w = sum(weights.values())

    results = []
    for i, (concept, sigs) in enumerate(concepts):
        score = 100 * sum(weights[k] * pct[k][i] for k in weights) / total_w
        top = sorted(sigs, key=lambda s: (has_intent(s), s.engagement + s.comments), reverse=True)
        results.append(
            ConceptScore(
                concept=concept,
                score=round(score, 1),
                volume=len(sigs),
                engagement=round(raw["engagement"][i], 1),
                momentum=round(raw["momentum"][i], 2),
                intent=int(raw["intent"][i]),
                diversity=int(raw["diversity"][i]),
                search_growth=None if growth[i] is None else round(growth[i], 2),
                sources=sorted({s.source for s in sigs}),
                examples=top[:examples],
            )
        )
    results.sort(key=lambda r: r.score, reverse=True)
    return results
