import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from demand_radar.cli import main
from demand_radar.extract import assign_concepts, emergent_phrases, has_intent, load_taxonomy
from demand_radar.models import Signal
from demand_radar.report import dump_signals, load_signals
from demand_radar.scoring import _momentum, _percentiles, score_concepts
from demand_radar.sources import appstore, github, hackernews, producthunt, reddit

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

    def test_min_volume_filters_singletons(self):
        self.assertEqual(score_concepts({"Lonely": [sig("x")]}, days=30, now=NOW), [])


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


if __name__ == "__main__":
    unittest.main()
