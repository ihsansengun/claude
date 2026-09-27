"""Render results as Markdown (for people) and JSON (for other tools)."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime

from .extract import has_intent
from .models import ConceptScore, Signal


def _trend(momentum: float) -> str:
    if momentum >= 1.5:
        return "rising fast"
    if momentum >= 1.1:
        return "rising"
    if momentum > 0.9:
        return "steady"
    return "cooling"


def _signal_line(s: Signal) -> str:
    stats = f"#{s.rank}" if s.rank else f"{s.engagement:g} pts, {s.comments:g} comments"
    flag = " **[ask]**" if has_intent(s) else ""
    title = s.title.replace("|", "\\|").replace("\n", " ")[:140]
    return f"- [{title}]({s.url}) ({s.source}, {stats}){flag}"


def to_markdown(
    concepts: list[ConceptScore],
    phrases: list[ConceptScore],
    asks: list[Signal],
    *,
    days: int,
    total_signals: int,
    sources: list[str],
    generated_at: datetime,
    top: int = 20,
    themed: bool = False,
) -> str:
    out = [
        "# Demand Radar report",
        "",
        f"Generated {generated_at:%Y-%m-%d %H:%M} UTC · window: last {days} days · "
        f"{total_signals} signals from {', '.join(sources) or 'no sources'}",
        "",
        "Score is 0-100: a weighted percentile blend of engagement, volume, momentum, "
        "explicit asks (\"is there an app…\", \"I'd pay…\"), cross-source agreement, "
        "and Google search-interest growth when available. "
        "Trend compares the two halves of the window using only sources that span it "
        "(HN, Reddit); — means too few posts to tell.",
    ]
    if concepts and all(c.search_growth is None for c in concepts):
        out += [
            "",
            "_No Google Trends search-interest data this run (skipped, rate limited, or failed; "
            "see the terminal output), so Search is left out of the scores._",
        ]
    out += [
        "",
        "## Top concepts",
        "",
        "| # | Concept | Score | Signals | Asks | Sources | Trend | Search |",
        "|---|---------|------:|--------:|-----:|--------:|-------|--------|",
    ]
    for i, c in enumerate(concepts[:top], 1):
        search = "—" if c.search_growth is None else f"{_trend(c.search_growth)} ({c.search_growth:.2f}x)"
        trend = "—" if c.momentum is None else f"{_trend(c.momentum)} ({c.momentum:.2f}x)"
        out.append(
            f"| {i} | {c.concept} | {c.score} | {c.volume} | {c.intent} | {c.diversity} | "
            f"{trend} | {search} |"
        )
    out += ["", "## Evidence for the top concepts", ""]
    for c in concepts[: min(top, 10)]:
        out += [f"### {c.concept} ({c.score})", ""]
        out += [_signal_line(s) for s in c.examples]
        out.append("")

    if phrases and themed:
        out += [
            "## Emerging themes",
            "",
            "Recurring phrases from titles, clustered by meaning and independent of the taxonomy. "
            "**new** marks themes that no taxonomy category covers: candidate niches.",
            "",
            "| Theme | Also phrased as | Score | Signals | Asks | Sources | Category |",
            "|-------|-----------------|------:|--------:|-----:|--------:|----------|",
        ]
        for p in phrases[:top]:
            aka = ", ".join(p.aliases[:4]) + (f" (+{len(p.aliases) - 4})" if len(p.aliases) > 4 else "")
            out.append(
                f"| {p.concept} | {aka or '—'} | {p.score} | {p.volume} | {p.intent} | {p.diversity} | "
                f"{p.fits or '**new**'} |"
            )
        out.append("")
    elif phrases:
        out += [
            "## Emerging phrases",
            "",
            "Recurring phrases found in titles, independent of the taxonomy. "
            "Useful for spotting niches the category list doesn't name yet.",
            "",
            "| Phrase | Score | Signals | Asks | Sources |",
            "|--------|------:|--------:|-----:|--------:|",
        ]
        out += [f"| {p.concept} | {p.score} | {p.volume} | {p.intent} | {p.diversity} |" for p in phrases[:top]]
        out.append("")

    if asks:
        out += [
            "## Top unmet asks",
            "",
            "The most-engaged posts where someone explicitly asks for a product.",
            "",
        ]
        out += [_signal_line(s) for s in asks]
        out.append("")
    return "\n".join(out)


def _signal_dict(s: Signal) -> dict:
    d = asdict(s)
    d["created_at"] = s.created_at.isoformat() if s.created_at else None
    return d


def to_json(concepts: list[ConceptScore], phrases: list[ConceptScore], asks: list[Signal], **meta) -> str:
    def concept_dict(c: ConceptScore) -> dict:
        d = asdict(c)
        d["examples"] = [_signal_dict(s) for s in c.examples]
        return d

    meta = {k: (v.isoformat() if isinstance(v, datetime) else v) for k, v in meta.items()}
    return json.dumps(
        {
            **meta,
            "concepts": [concept_dict(c) for c in concepts],
            "emerging_phrases": [concept_dict(p) for p in phrases],
            "top_asks": [_signal_dict(s) for s in asks],
        },
        indent=2,
    )


def dump_signals(signals: list[Signal]) -> str:
    return json.dumps([_signal_dict(s) for s in signals], indent=1)


def load_signals(text: str) -> list[Signal]:
    out = []
    for d in json.loads(text):
        if d.get("created_at"):
            d["created_at"] = datetime.fromisoformat(d["created_at"])
        out.append(Signal(**d))
    return out
