"""Core data types shared across sources, extraction, and scoring."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Signal:
    """One observation from the outside world that might indicate demand.

    A signal is a post, a repo, a chart entry, a launch, etc. `engagement` is
    the source's native popularity number (upvotes, stars, votes), and
    `comments` is discussion volume when available.
    """

    source: str
    title: str
    url: str
    created_at: datetime | None = None
    text: str = ""
    engagement: float = 0.0
    comments: float = 0.0
    # Rank on a chart (1 = top); only set by chart-style sources.
    rank: int | None = None
    # Set on search-interest time-series points (e.g. Google Trends): the concept
    # this point measures. These feed search growth, not volume or engagement.
    series_for: str | None = None

    @property
    def body(self) -> str:
        return f"{self.title}\n{self.text}"


@dataclass
class ConceptScore:
    concept: str
    score: float
    volume: int
    engagement: float
    momentum: float
    intent: float
    diversity: int
    # Recent vs older search interest; None when no search series covers the concept.
    search_growth: float | None = None
    sources: list[str] = field(default_factory=list)
    examples: list[Signal] = field(default_factory=list)
