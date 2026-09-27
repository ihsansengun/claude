"""Score concepts on how popular and in-demand they look right now.

Five components, each turned into a 0-1 percentile across concepts so no one
source's scale (HN points vs GitHub stars vs chart rank) dominates:

- engagement: how much attention matching signals got (log-damped, so one viral
  post doesn't swamp many solid ones)
- volume:     how many distinct signals mention the concept
- momentum:   recent half of the window vs the older half (is it accelerating?)
- intent:     how many signals are explicit asks ("is there an app", "I'd pay")
- diversity:  how many independent sources agree

The final score is a weighted sum scaled to 0-100.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

from .extract import has_intent
from .models import ConceptScore, Signal

DEFAULT_WEIGHTS = {"engagement": 0.30, "volume": 0.15, "momentum": 0.20, "intent": 0.25, "diversity": 0.10}


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
    concepts = [(c, sigs) for c, sigs in buckets.items() if len(sigs) >= min_volume]
    if not concepts:
        return []

    raw = {
        "engagement": [_engagement(s) for _, s in concepts],
        "volume": [float(len(s)) for _, s in concepts],
        "momentum": [_momentum(s, now, days) for _, s in concepts],
        "intent": [float(sum(has_intent(x) for x in s)) for _, s in concepts],
        "diversity": [float(len({x.source for x in s})) for _, s in concepts],
    }
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
                sources=sorted({s.source for s in sigs}),
                examples=top[:examples],
            )
        )
    results.sort(key=lambda r: r.score, reverse=True)
    return results
