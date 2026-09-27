"""Group similar emerging phrases into themes.

Raw phrase mining fragments one idea into many rows ("habit tracker",
"tracking habits", "streak app"). This module merges them:

1. Each phrase gets a similarity to every other phrase, from one of two backends:
   - `tfidf` (default, stdlib only), a blend of three views:
       * words: the phrase's own words, lightly stemmed ("tracker"/"tracking")
       * context: the centroid of the posts that contain the phrase
       * category profile: which taxonomy concepts those posts match, so
         "calorie counter" and "food photo" meet under Diet without sharing a word
     This is shallow semantics; it relies on the taxonomy to bridge synonyms.
   - `sbert` (optional, `pip install sentence-transformers`): real sentence
     embeddings of the phrase plus a few of its post titles.
2. Average-linkage agglomerative clustering merges phrases until no pair of
   clusters is more similar than the threshold.
3. Each theme is named after its best-supported phrase, keeps its other
   phrases as aliases, and is linked to the taxonomy concept most of its posts
   already match, or flagged as new when none dominates.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass, field

from .extract import STOPWORDS, concept_text, tokens
from .models import Signal

DEFAULT_THRESHOLDS = {"tfidf": 0.35, "sbert": 0.55}
TFIDF_BLEND = {"words": 0.4, "context": 0.2, "category": 0.4}
SBERT_MODEL = "all-MiniLM-L6-v2"
# A theme "fits" a taxonomy concept when at least this share of its posts match it.
FIT_SHARE = 0.5


@dataclass
class Theme:
    label: str
    aliases: list[str]
    signals: list[Signal]
    fits: str | None = None
    fit_share: float = 0.0
    phrases: list[str] = field(default_factory=list)


# --- tfidf backend ---------------------------------------------------------

def _stem(word: str) -> str:
    for suffix in ("ing", "ers", "er", "es", "s"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            return word[: -len(suffix)]
    return word


def _terms(text: str) -> list[str]:
    words = [_stem(w) for w in tokens(text) if w not in STOPWORDS and not w.isdigit()]
    return words + [f"{a} {b}" for a, b in zip(words, words[1:])]


def _tfidf(docs: list[list[str]]) -> list[dict[str, float]]:
    df = Counter(t for doc in docs for t in set(doc))
    n = len(docs)
    vecs = []
    for doc in docs:
        tf = Counter(doc)
        vec = {t: (1 + math.log(c)) * math.log((1 + n) / (1 + df[t])) for t, c in tf.items()}
        vecs.append(_normalize(vec))
    return vecs


def _normalize(vec: dict[str, float]) -> dict[str, float]:
    norm = math.sqrt(sum(v * v for v in vec.values()))
    return {t: v / norm for t, v in vec.items()} if norm else {}


def _dot(a: dict[str, float], b: dict[str, float]) -> float:
    if len(a) > len(b):
        a, b = b, a
    return sum(v * b.get(t, 0.0) for t, v in a.items())


def _key(s: Signal) -> tuple:
    return (s.source, s.url, s.title)


def _category_profile(signals: list[Signal], taxonomy: dict[str, re.Pattern]) -> dict[str, float]:
    return _normalize(dict(Counter(c for s in signals for c, pat in taxonomy.items() if pat.search(concept_text(s)))))


def tfidf_similarity(items: list[tuple[str, list[Signal]]], taxonomy: dict[str, re.Pattern]) -> list[list[float]]:
    # IDF fit over every distinct post, so words common to all posts ("app") count little.
    posts: dict[tuple, Signal] = {}
    for _, sigs in items:
        for s in sigs:
            posts.setdefault(_key(s), s)
    keys = list(posts)
    post_vecs = dict(zip(keys, _tfidf([_terms(posts[k].body) for k in keys])))

    context = []
    for _, sigs in items:
        centroid: Counter[str] = Counter()
        for s in sigs:
            centroid.update(post_vecs[_key(s)])
        context.append(_normalize(dict(centroid)))
    # Phrase-text vectors get their own IDF over the phrase pool.
    phrase = _tfidf([_terms(p) for p, _ in items])
    category = [_category_profile(sigs, taxonomy) for _, sigs in items]
    w = TFIDF_BLEND

    n = len(items)
    sim = [[1.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            sim[i][j] = sim[j][i] = (
                w["words"] * _dot(phrase[i], phrase[j])
                + w["context"] * _dot(context[i], context[j])
                + w["category"] * _dot(category[i], category[j])
            )
    return sim


# --- sbert backend ---------------------------------------------------------

def sbert_similarity(items: list[tuple[str, list[Signal]]], taxonomy: dict[str, re.Pattern]) -> list[list[float]]:  # noqa: ARG001
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise RuntimeError("--cluster sbert needs `pip install sentence-transformers`") from exc
    texts = [
        p + " — " + "; ".join(s.title for s in sorted(sigs, key=lambda s: -s.engagement)[:5])
        for p, sigs in items
    ]
    emb = [[float(x) for x in row] for row in SentenceTransformer(SBERT_MODEL).encode(texts, normalize_embeddings=True)]
    return [[sum(x * y for x, y in zip(a, b)) for b in emb] for a in emb]


BACKENDS = {"tfidf": tfidf_similarity, "sbert": sbert_similarity}


# --- clustering ------------------------------------------------------------

def agglomerate(sim: list[list[float]], threshold: float) -> list[list[int]]:
    """Average-linkage clustering; returns index groups, merged while best link >= threshold."""
    clusters: dict[int, list[int]] = {i: [i] for i in range(len(sim))}
    link = {(i, j): sim[i][j] for i in clusters for j in clusters if i < j}
    while link:
        (a, b), best = max(link.items(), key=lambda kv: kv[1])
        if best < threshold:
            break
        na, nb = len(clusters[a]), len(clusters[b])
        clusters[a] += clusters.pop(b)
        for k in clusters:
            if k == a:
                continue
            # Lance-Williams update for average linkage.
            ak, bk = (min(a, k), max(a, k)), (min(b, k), max(b, k))
            link[ak] = (na * link[ak] + nb * link.pop(bk)) / (na + nb)
        link.pop((a, b))
    return list(clusters.values())


def _fit(signals: list[Signal], taxonomy: dict[str, re.Pattern]) -> tuple[str | None, float]:
    counts = Counter(c for s in signals for c, pat in taxonomy.items() if pat.search(concept_text(s)))
    if not counts:
        return None, 0.0
    concept, hits = counts.most_common(1)[0]
    share = hits / len(signals)
    return (concept if share >= FIT_SHARE else None), share


def cluster_phrases(
    phrases: dict[str, list[Signal]],
    taxonomy: dict[str, re.Pattern],
    *,
    method: str = "tfidf",
    threshold: float | None = None,
) -> list[Theme]:
    items = list(phrases.items())
    if not items:
        return []
    sim = BACKENDS[method](items, taxonomy)
    groups = agglomerate(sim, DEFAULT_THRESHOLDS[method] if threshold is None else threshold)

    themes = []
    for group in groups:
        # Name the theme after its best-supported phrase; break ties by how similar a
        # phrase is to the rest of the theme, so the label is its most typical wording.
        centrality = {i: sum(sim[i][j] for j in group if j != i) for i in group}
        members = [items[i] for i in sorted(group, key=lambda i: (-len(items[i][1]), -centrality[i], items[i][0]))]
        seen: dict[tuple, Signal] = {}
        for _, sigs in members:
            for s in sigs:
                seen.setdefault(_key(s), s)
        signals = list(seen.values())
        fits, share = _fit(signals, taxonomy)
        names = [p for p, _ in members]
        themes.append(Theme(label=names[0], aliases=names[1:], signals=signals, fits=fits,
                            fit_share=round(share, 2), phrases=names))
    return themes
