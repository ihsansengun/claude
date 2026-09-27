import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import sys
import types

from demand_radar.cli import main
from demand_radar.cluster import agglomerate, cluster_phrases
from demand_radar.extract import assign_concepts, emergent_phrases, has_intent, load_taxonomy
from demand_radar.models import Signal
from demand_radar.report import dump_signals, load_signals
from demand_radar.scoring import DEFAULT_WEIGHTS, _momentum, _percentiles, _search_growth, score_concepts
from demand_radar.sources import appstore, github, googletrends, hackernews, producthunt, reddit

FIXTURES = Path(__file__).with_name("fixtures")
NOW = datetime(2026, 9, 27, tzinfo=timezone.utc)


def sig(title, source="hackernews", days_ago=1, points=10, comments=0, text=""):
    return Signal(source, title, f"https://x/{source}/{title}", NOW - timedelta(days=days_ago), text, points, comments)


class SourceParsers(unittest.TestCase):
    def test_hackernews(self):
        out = hackernews.parse(json.loads((FIXTURES / "hn.json").read_text()))
        self.assertEqual(len(out), 2)
        self.assertEqual(out[0].engagement, 412)
        self.assertEqual(out[1].url, "https://news.ycombinator.com/item?id=2")
        self.assertEqual(out[0].created_at.tzinfo, timezone.utc)

    def test_reddit(self):
        out = reddit.parse(json.loads((FIXTURES / "reddit.json").read_text()))
        self.assertEqual(out[0].url, "https://www.reddit.com/r/SomebodyMakeThis/comments/abc/x/")
        self.assertEqual(out[0].comments, 88)

    def test_github(self):
        out = github.parse(json.loads((FIXTURES / "github.json").read_text()))
        self.assertIn("coding agent", out[0].title)
        self.assertIn("mcp", out[0].text)

    def test_appstore_rank_to_engagement(self):
        out = appstore.parse(json.loads((FIXTURES / "appstore.json").read_text()))
        self.assertEqual([s.rank for s in out], [1, 2])
        self.assertGreater(out[0].engagement, out[1].engagement)

    def test_producthunt(self):
        out = producthunt.parse((FIXTURES / "producthunt.xml").read_bytes())
        self.assertEqual(out[0].title, "Nightowl")
        self.assertIn("sleep", out[0].text)
        self.assertNotIn("<p>", out[0].text)

    def test_googletrends_trending_rss(self):
        out = googletrends.parse_trending((FIXTURES / "trends_rss.xml").read_bytes())
        self.assertEqual([s.engagement for s in out], [2000, 1_000_000])
        self.assertIn("GLP-1", out[0].text)
        self.assertEqual(out[0].created_at, datetime(2026, 9, 26, 17, tzinfo=timezone.utc))
        self.assertIsNone(out[0].series_for)

    def test_googletrends_interest_strips_prefix_and_partial(self):
        payload = googletrends._strip_xssi((FIXTURES / "trends_multiline.txt").read_bytes())
        out = googletrends.parse_interest(payload, "sleep app", "Sleep")
        self.assertEqual([s.engagement for s in out], [40, 60, 100])  # partial week dropped
        self.assertTrue(all(s.series_for == "Sleep" for s in out))

    def test_googletrends_traffic_parsing(self):
        self.assertEqual(googletrends._traffic("200+"), 200)
        self.assertEqual(googletrends._traffic("10K+"), 10_000)
        self.assertEqual(googletrends._traffic(None), 0)

    def test_search_terms_match_taxonomy(self):
        self.assertEqual(set(googletrends.load_terms()), set(load_taxonomy()))


class Extraction(unittest.TestCase):
    def test_intent_phrases(self):
        self.assertTrue(has_intent(sig("Is there an app that tracks my houseplants?")))
        self.assertTrue(has_intent(sig("I'd pay for a calorie counter that works offline")))
        self.assertTrue(has_intent(sig("Open-source alternative to Notion")))
        self.assertFalse(has_intent(sig("Show HN: My weekend project")))

    def test_taxonomy_word_boundaries(self):
        tax = load_taxonomy()
        buckets = assign_concepts(
            [sig("A category catalog for career cards"), sig("Best app for my cat"), sig("Habit tracker for ADHD")], tax
        )
        self.assertNotIn("Cars & transport", buckets)
        self.assertEqual(len(buckets["Pets"]), 1)
        self.assertIn("Habit & productivity tracking", buckets)
        self.assertIn("Mental health & therapy", buckets)

    def test_emergent_phrases(self):
        signals = [sig(f"Show HN: plant care tracker v{i}") for i in range(3)] + [sig("unrelated thing")]
        phrases = emergent_phrases(signals, min_support=3)
        # "plant care tracker" subsumes "plant care" and "care tracker" at equal support.
        self.assertIn("plant care tracker", phrases)
        self.assertNotIn("plant care", phrases)


class Scoring(unittest.TestCase):
    def test_percentiles_ties(self):
        self.assertEqual(_percentiles([1, 1, 3]), [0.25, 0.25, 1.0])

    def test_momentum_rising_vs_cooling(self):
        rising = [sig("x", days_ago=2), sig("x", days_ago=3), sig("x", days_ago=4)]
        cooling = [sig("x", days_ago=25), sig("x", days_ago=26), sig("x", days_ago=27)]
        self.assertGreater(_momentum(rising, NOW, 30), 1)
        self.assertLess(_momentum(cooling, NOW, 30), 1)

    def test_demanded_concept_outranks_quiet_one(self):
        hot = [
            sig("Is there an app for sleep tracking?", "reddit", 1, 900, 300),
            sig("I'd pay for a sleep coach", "hackernews", 2, 400, 120),
            sig("Sleep sounds", "producthunt", 3),
        ]
        quiet = [sig("weather widget", days_ago=25, points=2), sig("weather again", days_ago=26, points=1)]
        ranked = score_concepts({"Sleep": hot, "Weather": quiet}, days=30, now=NOW)
        self.assertEqual(ranked[0].concept, "Sleep")
        self.assertEqual(ranked[0].intent, 2)
        self.assertEqual(ranked[0].diversity, 3)
        self.assertGreater(ranked[0].score, ranked[1].score)

    def test_search_series_feeds_growth_not_volume(self):
        def point(concept, days_ago, value):
            return Signal("googletrends", "term", "u", NOW - timedelta(days=days_ago), "", value, series_for=concept)

        posts = {c: [sig(f"{c} a", points=50), sig(f"{c} b", points=50)] for c in ("Up", "Down")}
        buckets = {
            "Up": posts["Up"] + [point("Up", 25, 20), point("Up", 5, 80)],
            "Down": posts["Down"] + [point("Down", 25, 80), point("Down", 5, 20)],
        }
        ranked = {c.concept: c for c in score_concepts(buckets, days=30, now=NOW)}
        self.assertEqual(ranked["Up"].volume, 2)  # series points aren't posts
        self.assertEqual(ranked["Up"].sources, ["hackernews"])
        self.assertGreater(ranked["Up"].search_growth, 1)
        self.assertLess(ranked["Down"].search_growth, 1)
        self.assertGreater(ranked["Up"].score, ranked["Down"].score)

    def test_search_weight_dropped_without_series(self):
        buckets = {"A": [sig("a", points=90), sig("a2", points=90)], "B": [sig("b", points=1), sig("b2", points=1)]}
        ranked = score_concepts(buckets, days=30, now=NOW)
        no_search = {k: w for k, w in DEFAULT_WEIGHTS.items() if k != "search"}
        expected = score_concepts(buckets, days=30, now=NOW, weights=no_search)
        # No search data anywhere: identical to scoring without the component.
        self.assertEqual([c.score for c in ranked], [c.score for c in expected])
        self.assertIsNone(ranked[0].search_growth)
        self.assertIsNone(_search_growth([], NOW, 30))

    def test_series_pinned_to_concept_and_ignored_by_phrases(self):
        pts = [Signal("googletrends", "sleep app", "u", NOW - timedelta(days=i), "", 50, series_for="Sleep") for i in range(5)]
        buckets = assign_concepts(pts, load_taxonomy())
        self.assertEqual(list(buckets), ["Sleep"])  # not also keyword-matched elsewhere
        self.assertEqual(emergent_phrases(pts, min_support=3), {})

    def test_min_volume_filters_singletons(self):
        self.assertEqual(score_concepts({"Lonely": [sig("x")]}, days=30, now=NOW), [])


class Clustering(unittest.TestCase):
    def setUp(self):
        from cluster_corpus import S

        self.phrases = emergent_phrases(S, min_support=2, top=150)
        self.tax = load_taxonomy()

    def test_agglomerate_average_linkage(self):
        sim = [
            [1.0, 0.9, 0.1, 0.0],
            [0.9, 1.0, 0.2, 0.0],
            [0.1, 0.2, 1.0, 0.8],
            [0.0, 0.0, 0.8, 1.0],
        ]
        self.assertEqual(sorted(map(sorted, agglomerate(sim, 0.5))), [[0, 1], [2, 3]])
        self.assertEqual(len(agglomerate(sim, 0.95)), 4)
        # avg link between {0,1} and {2,3} is 0.075: only a very low threshold joins them.
        self.assertEqual(len(agglomerate(sim, 0.05)), 1)

    def test_merges_paraphrases_across_wording(self):
        themes = {t.label: t for t in cluster_phrases(self.phrases, self.tax)}
        self.assertIn("daily streak", themes["habit tracker"].aliases)
        self.assertTrue({"calorie counter", "food photo"} <= set(themes["macro tracker"].aliases))
        self.assertIn("meeting transcription", themes["meeting notes"].aliases)
        self.assertEqual(themes["doomscrolling blocker"].fits, "Screen time & digital wellbeing")

    def test_unrelated_ideas_stay_apart_and_new_niche_flagged(self):
        themes = cluster_phrases(self.phrases, self.tax)
        of = {p: t.label for t in themes for p in t.phrases}
        self.assertNotEqual(of["habit tracker"], of["meeting notes"])
        self.assertNotEqual(of["macro tracker"], of["doomscrolling blocker"])
        plants = next(t for t in themes if t.label == "plant watering")
        self.assertIsNone(plants.fits)  # no taxonomy category covers it

    def test_theme_signals_are_deduplicated(self):
        for t in cluster_phrases(self.phrases, self.tax):
            keys = [(s.source, s.url, s.title) for s in t.signals]
            self.assertEqual(len(keys), len(set(keys)))

    def test_sbert_backend_uses_embeddings(self):
        class FakeModel:
            def __init__(self, name):
                pass

            def encode(self, texts, normalize_embeddings=True):
                # 2-d "embeddings": habit-ish texts point one way, everything else the other.
                return [[1.0, 0.0] if ("habit" in t or "streak" in t) else [0.0, 1.0] for t in texts]

        fake = types.ModuleType("sentence_transformers")
        fake.SentenceTransformer = FakeModel
        sys.modules["sentence_transformers"] = fake
        try:
            themes = cluster_phrases(self.phrases, self.tax, method="sbert", threshold=0.9)
        finally:
            del sys.modules["sentence_transformers"]
        habit = next(t for t in themes if "habit tracker" in t.phrases)
        self.assertEqual(set(habit.phrases), {"habit tracker", "habit tracking", "daily streak"})


class EndToEnd(unittest.TestCase):
    def test_cli_from_saved_signals(self):
        now = datetime.now(timezone.utc)
        signals = [
            Signal("reddit", "Is there an app to track my habits?", "https://r/1", now - timedelta(days=2), "", 500, 90),
            Signal("hackernews", "Show HN: A habit tracker with streaks", "https://h/1", now - timedelta(days=3), "", 200, 40),
            Signal("producthunt", "Streaky: habit tracking for teams", "https://p/1", now - timedelta(days=4)),
            Signal("github", "budget-cli: personal budget in your terminal", "https://g/1", now - timedelta(days=20), "", 150, 10),
            Signal("reddit", "I'd pay for a budget app without ads", "https://r/2", now - timedelta(days=22), "", 80, 30),
            Signal("appstore", "Calm", "https://a/1", None, "Health & Fitness top-free", 1000.0, 0, 1),
        ]
        with tempfile.TemporaryDirectory() as d:
            src, md, js = Path(d, "s.json"), Path(d, "r.md"), Path(d, "r.json")
            src.write_text(dump_signals(signals))
            self.assertEqual(len(load_signals(src.read_text())), len(signals))
            self.assertEqual(main(["--from-signals", str(src), "--out", str(md), "--json", str(js)]), 0)
            report = md.read_text()
            data = json.loads(js.read_text())
        self.assertIn("Habit & productivity tracking", report)
        self.assertIn("Top unmet asks", report)
        self.assertEqual(data["concepts"][0]["concept"], "Habit & productivity tracking")
        self.assertEqual(data["total_signals"], 6)

    def test_cli_cluster_on_and_off(self):
        from cluster_corpus import S

        with tempfile.TemporaryDirectory() as d:
            src, md = Path(d, "s.json"), Path(d, "r.md")
            src.write_text(dump_signals(S))
            self.assertEqual(main(["--from-signals", str(src), "--out", str(md)]), 0)
            themed = md.read_text()
            self.assertEqual(main(["--from-signals", str(src), "--out", str(md), "--cluster", "off"]), 0)
            plain = md.read_text()
        self.assertIn("## Emerging themes", themed)
        self.assertIn("| habit tracker | habit tracking, daily streak |", themed)
        self.assertRegex(themed, r"\| plant watering \|.*\*\*new\*\* \|")
        self.assertIn("## Emerging phrases", plain)
        self.assertNotIn("## Emerging themes", plain)


if __name__ == "__main__":
    unittest.main()
