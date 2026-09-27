"""Turn raw signals into concepts: taxonomy matching, intent detection, emergent phrases."""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from .models import Signal

DEFAULT_TAXONOMY = Path(__file__).with_name("taxonomy.json")

# Phrases that indicate someone actively wants something that doesn't (yet) satisfy them.
# These are the strongest demand signals: unmet need + willingness to act/pay.
INTENT_PATTERNS = [
    r"\bis there (?:an?|any) (?:app|tool|service|website|extension)\b",
    r"\b(?:i|we)(?:'d| would) (?:happily )?pay\b",
    r"\bshut up and take my money\b",
    r"\b(?:i )?wish (?:there (?:was|were)|someone (?:would )?(?:made|built|make|build))\b",
    r"\bsomebody (?:should )?make\b",
    r"\blooking for (?:an?|some) (?:app|tool|service|alternative)\b",
    # Only *asking* for an alternative; "a cheaper alternative to X" is usually a launch pitch.
    r"\bany (?:good |decent |free |cheaper |open[- ]source )?alternatives? (?:to|for)\b",
    r"\balternatives? (?:to|for) [^?.!\n]{1,60}\?",
    r"\b(?:is there|know of|recommend) an? (?:[\w-]+ )?alternative\b",
    r"\bneed (?:an?|some) (?:app|tool)\b",
    r"\bwhy (?:is there no|isn't there an?)\b",
    r"\bapp idea\b|\brequest:",
]
_INTENT_RE = re.compile("|".join(INTENT_PATTERNS), re.IGNORECASE)

STOPWORDS = set(
    """a an the and or but if then so of to in on for with without by from at as is are was were be been being
    it its this that these those i me my we our you your he she they them their what which who whom how why when
    where there here do does did done have has had having can could should would will just not no yes than too very
    about into over under again more most some any all each other such only own same up down out off new now get got
    make made using use used app apps tool tools show hn ask anyone looking need want like built build building
    one way free best better good great first help really also still even much many via based simple open source
    my i'm i've it's don't can't what's let's vs your you're day days week year time people thing things something
    launch launched launching today introducing project side feedback idea ideas i'd we'd pay wish please
    actually alternative alternatives""".split()
)
# Site names and filler that recur in titles without describing a product.
NOISE_PHRASES = {"hacker news", "ask hn", "show hn", "launch hn", "product hunt", "open source", "open-source"}
_WEAK_MIDDLE = {"and", "or", "the", "a", "an", "of", "for", "with"}
_WORD_RE = re.compile(r"[a-z][a-z0-9+\-']*[a-z0-9+]|[a-z]")


def load_taxonomy(path: Path | None = None) -> dict[str, re.Pattern]:
    raw = json.loads((path or DEFAULT_TAXONOMY).read_text())
    compiled = {}
    for concept, keywords in raw.items():
        if concept.startswith("_"):
            continue
        parts = []
        for kw in keywords:
            if kw.endswith("*"):
                parts.append(re.escape(kw[:-1]) + r"[\w-]*")
            else:
                parts.append(re.escape(kw))
        compiled[concept] = re.compile(r"(?<![\w-])(?:" + "|".join(parts) + r")(?![\w-])", re.IGNORECASE)
    return compiled


# Sources that list things people *made* (supply), never requests for something.
SUPPLY_SOURCES = {"github", "producthunt", "appstore", "googletrends"}
_LAUNCH_RE = re.compile(r"^\s*(?:show|launch) hn\b", re.IGNORECASE)
# Sources whose `text` is long free-form prose (post bodies, attached news
# headlines). Keywords there are mostly incidental, so concepts are matched on
# the title only. Other sources' text is short and structured (GitHub topics,
# App Store genres, Product Hunt taglines) and describes the item itself.
TITLE_ONLY_SOURCES = {"hackernews", "reddit", "googletrends"}
# Reddit self-posts often put the ask in the body ("is there an app that…").
INTENT_BODY_SOURCES = {"reddit"}


def concept_text(signal: Signal) -> str:
    """The text taxonomy keywords are matched against."""
    return signal.title if signal.source in TITLE_ONLY_SOURCES else signal.body


def has_intent(signal: Signal) -> bool:
    """True when the post asks for a product, rather than launching one."""
    if signal.source in SUPPLY_SOURCES or _LAUNCH_RE.match(signal.title):
        return False
    text = signal.body if signal.source in INTENT_BODY_SOURCES else signal.title
    return bool(_INTENT_RE.search(text))


def assign_concepts(signals: list[Signal], taxonomy: dict[str, re.Pattern]) -> dict[str, list[Signal]]:
    """Map each concept to the signals that mention it. A signal can hit several concepts.

    Search-series points are pinned to their concept instead of keyword-matched.
    """
    buckets: dict[str, list[Signal]] = defaultdict(list)
    for sig in signals:
        if sig.series_for is not None:
            if sig.series_for in taxonomy:
                buckets[sig.series_for].append(sig)
            continue
        text = concept_text(sig)
        for concept, pattern in taxonomy.items():
            if pattern.search(text):
                buckets[concept].append(sig)
    return dict(buckets)


def tokens(text: str) -> list[str]:
    return _WORD_RE.findall(text.lower())


def emergent_phrases(signals: list[Signal], min_support: int = 3, top: int = 40) -> dict[str, list[Signal]]:
    """Find recurring 2-3 word phrases in titles that the taxonomy may not cover.

    A phrase counts once per signal, must appear in at least `min_support`
    signals, and may not start or end with a stopword. Phrases fully contained
    in a longer phrase with the same support are dropped as redundant.
    """
    support: Counter[str] = Counter()
    members: dict[str, list[Signal]] = defaultdict(list)
    for sig in signals:
        if sig.series_for is not None:
            continue
        words = tokens(sig.title)
        grams = set()
        for n in (2, 3):
            for i in range(len(words) - n + 1):
                gram = words[i : i + n]
                if gram[0] in STOPWORDS or gram[-1] in STOPWORDS or any(w.isdigit() for w in gram):
                    continue
                if (n == 3 and gram[1] in _WEAK_MIDDLE) or " ".join(gram) in NOISE_PHRASES:
                    continue
                grams.add(" ".join(gram))
        for g in grams:
            support[g] += 1
            members[g].append(sig)

    kept = {g: c for g, c in support.items() if c >= min_support}
    for g in list(kept):
        if any(g != other and g in other and kept[other] == kept[g] for other in kept):
            del kept[g]
    ranked = sorted(kept, key=lambda g: (-kept[g], g))[:top]
    return {g: members[g] for g in ranked}
