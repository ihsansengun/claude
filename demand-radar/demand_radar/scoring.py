"""Score concepts on how popular and in-demand they look right now.

Five components, each turned into a 0-1 percentile across concepts so no one
source's scale (HN points vs GitHub stars vs chart rank) dominates:

- engagement: how much attention matching signals got (log-damped, so one viral
  post doesn't swamp many solid ones)
- volume:     how many distinct signals mention the concept
- momentum:   recent half of the window vs the older half, divided by the same
              ratio for all posts (so 1.0 = growing as fast as the source overall;
              a source that simply has more recent posts doesn't lift everything),
              from sources that cover the whole window; None with too few posts
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


# Sources whose posts don't spread evenly over the window, so they'd fake a trend:
# feeds/charts that only show the last few days (always "recent"), and GitHub,
# where older repos have had longer to earn the stars needed to be listed.
NO_MOMENTUM_SOURCES = {"producthunt", "appstore", "googletrends", "github"}
MIN_MOMENTUM_POSTS = 5


MOMENTUM_PRIOR = 10.0  # pseudo-weight (~2 posts) pulling small concepts toward "no change"


def _recent_older(signals: list[Signal], now: datetime, days: int) -> tuple[float, float, int]:
    """Engagement-weighted activity in the recent and older halves of the window."""
    mid = now - timedelta(days=days / 2)
    start = now - timedelta(days=days)
    dated = [
        s for s in signals
        if s.created_at is not None and s.created_at >= start and s.source not in NO_MOMENTUM_SOURCES
    ]
    recent = older = 0.0
    for s in dated:
        weight = 1 + math.log1p(s.engagement)
        if s.created_at >= mid:
            recent += weight
        else:
            older += weight
    return recent, older, len(dated)


def _momentum(signals: list[Signal], now: datetime, days: int, baseline: float = 0.5) -> float | None:
    """Odds that activity is recent, relative to `baseline` (the population's recent share).

    1.0 means the concept's activity is as recent as everything else's; 2.0 means
    twice the odds of being recent (gaining share). None if too few posts.
    """
    recent, older, n = _recent_older(signals, now, days)
    if n < MIN_MOMENTUM_POSTS:
        return None
    # Smooth toward the baseline so a 2-post concept can't look explosive.
    odds = (recent + MOMENTUM_PRIOR * baseline) / (older + MOMENTUM_PRIOR * (1 - baseline))
    return odds / (baseline / (1 - baseline))


def _recent_share(signals: list[Signal], now: datetime, days: int) -> float | None:
    recent, older, n = _recent_older(signals, now, days)
    if n < MIN_MOMENTUM_POSTS or recent == 0 or older == 0:
        return None
    return recent / (recent + older)


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


def _examples(signals: list[Signal], n: int) -> list[Signal]:
    """Top posts, interleaved across sources so GitHub star counts don't crowd out HN posts."""
    def rank(s: Signal) -> tuple:
        return (has_intent(s), s.engagement + s.comments)

    by_source: dict[str, list[Signal]] = {}
    for s in sorted(signals, key=rank, reverse=True):
        by_source.setdefault(s.source, []).append(s)
    queues = sorted(by_source.values(), key=lambda q: rank(q[0]), reverse=True)
    out: list[Signal] = []
    while len(out) < n and any(queues):
        for q in queues:
            if q and len(out) < n:
                out.append(q.pop(0))
    return out


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
    population: list[Signal] | None = None,
) -> list[ConceptScore]:
    """Score each bucket. `population` (all collected signals) sets the momentum
    baseline; by default it's every post across the buckets."""
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
    if population is None:
        population = list({(s.source, s.url, s.title): s for _, sigs in concepts for s in sigs}.values())
    baseline = _recent_share([s for s in population if s.series_for is None], now, days)
    momentum = [
        None if baseline is None else _momentum(s, now, days, baseline) for _, s in concepts
    ]

    raw = {
        "engagement": [_engagement(s) for _, s in concepts],
        "volume": [float(len(s)) for _, s in concepts],
        # Unknown momentum/search sit at neutral (no change) rather than bottom.
        "momentum": [1.0 if m is None else m for m in momentum],
        "intent": [float(sum(has_intent(x) for x in s)) for _, s in concepts],
        "diversity": [float(len({x.source for x in s})) for _, s in concepts],
        "search": [1.0 if g is None else g for g in growth],
    }
    # A component nobody has data for would only add noise; drop it.
    if all(g is None for g in growth):
        weights = {k: w for k, w in weights.items() if k != "search"}
    if all(m is None for m in momentum):
        weights = {k: w for k, w in weights.items() if k != "momentum"}
    pct = {k: _percentiles(v) for k, v in raw.items()}
    total_w = sum(weights.values())

    results = []
    for i, (concept, sigs) in enumerate(concepts):
        score = 100 * sum(weights[k] * pct[k][i] for k in weights) / total_w
        results.append(
            ConceptScore(
                concept=concept,
                score=round(score, 1),
                volume=len(sigs),
                engagement=round(raw["engagement"][i], 1),
                momentum=None if momentum[i] is None else round(momentum[i], 2),
                intent=int(raw["intent"][i]),
                diversity=int(raw["diversity"][i]),
                search_growth=None if growth[i] is None else round(growth[i], 2),
                sources=sorted({s.source for s in sigs}),
                examples=_examples(sigs, examples),
            )
        )
    results.sort(key=lambda r: r.score, reverse=True)
    return results
