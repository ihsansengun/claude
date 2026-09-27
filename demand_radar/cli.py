"""Command line entry point: `python -m demand_radar --help`."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from .extract import assign_concepts, emergent_phrases, has_intent, load_taxonomy
from .models import Signal
from .report import dump_signals, load_signals, to_json, to_markdown
from .scoring import score_concepts
from .sources import REGISTRY


def collect(names: list[str], days: int) -> list[Signal]:
    signals: list[Signal] = []
    for name in names:
        try:
            got = REGISTRY[name].fetch(days)
            print(f"  {name}: {len(got)} signals", file=sys.stderr)
            signals += got
        except Exception as exc:  # one flaky source shouldn't sink the run
            print(f"  {name}: FAILED ({exc})", file=sys.stderr)
    return signals


def analyze(signals: list[Signal], *, days: int, taxonomy_path: Path | None, now: datetime, top: int):
    concepts = score_concepts(assign_concepts(signals, load_taxonomy(taxonomy_path)), days=days, now=now)
    phrases = score_concepts(emergent_phrases(signals), days=days, now=now, min_volume=3, examples=3)
    asks = sorted((s for s in signals if has_intent(s)), key=lambda s: s.engagement + s.comments, reverse=True)[:top]
    return concepts, phrases, asks


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="demand_radar", description="Find popular, high-demand app concepts from public signals.")
    p.add_argument("--days", type=int, default=30, help="look-back window in days (default 30)")
    p.add_argument("--sources", default=",".join(REGISTRY), help=f"comma-separated subset of: {', '.join(REGISTRY)}")
    p.add_argument("--taxonomy", type=Path, help="custom concept taxonomy JSON (default: bundled taxonomy.json)")
    p.add_argument("--top", type=int, default=20, help="rows per section (default 20)")
    p.add_argument("--out", type=Path, help="write Markdown report here (default: stdout)")
    p.add_argument("--json", type=Path, help="also write machine-readable results here")
    p.add_argument("--save-signals", type=Path, help="save raw collected signals for replay/history")
    p.add_argument("--from-signals", type=Path, help="skip fetching; analyze a previously saved signals file")
    args = p.parse_args(argv)

    now = datetime.now(timezone.utc)
    if args.from_signals:
        signals = load_signals(args.from_signals.read_text())
        sources = sorted({s.source for s in signals})
        # Measure momentum relative to when the data was collected, not today.
        now = max((s.created_at for s in signals if s.created_at), default=now)
    else:
        sources = [s.strip() for s in args.sources.split(",") if s.strip()]
        if unknown := [s for s in sources if s not in REGISTRY]:
            p.error(f"unknown source(s): {', '.join(unknown)}")
        print(f"Collecting {args.days} days of signals...", file=sys.stderr)
        signals = collect(sources, args.days)
    if args.save_signals:
        args.save_signals.write_text(dump_signals(signals))
    if not signals:
        print("No signals collected; nothing to analyze.", file=sys.stderr)
        return 1

    concepts, phrases, asks = analyze(signals, days=args.days, taxonomy_path=args.taxonomy, now=now, top=args.top)
    meta = dict(days=args.days, total_signals=len(signals), sources=sources, generated_at=now)
    md = to_markdown(concepts, phrases, asks, top=args.top, **meta)
    if args.out:
        args.out.write_text(md)
        print(f"Wrote {args.out}", file=sys.stderr)
    else:
        print(md)
    if args.json:
        args.json.write_text(to_json(concepts, phrases, asks, **meta))
    return 0
