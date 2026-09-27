import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import contextlib
import io
import ssl
import sys
import types
from unittest import mock

from demand_radar import http
from demand_radar.cli import collect, default_sources, main
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

    def test_googletrends_retries_once_after_429(self):
        import urllib.error

        payload = googletrends._strip_xssi((FIXTURES / "trends_multiline.txt").read_bytes())
        calls = {"sessions": 0, "interest": 0}

        class FakeSession:
            def __init__(self):
                calls["sessions"] += 1

            def interest(self, term, frame):
                calls["interest"] += 1
                if calls["interest"] == 1:
                    raise urllib.error.HTTPError("u", 429, "Too Many Requests", {}, None)
                return payload

        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            out = googletrends.fetch_interest(30, {"Sleep": "sleep app", "Pets": "pet app"},
                                              session_factory=FakeSession, sleep=lambda s: None)
        self.assertEqual(calls["sessions"], 2)  # fresh session after the refusal
        self.assertEqual({s.series_for for s in out}, {"Sleep", "Pets"})
        self.assertIn("retrying once", err.getvalue())

    def test_googletrends_gives_up_after_second_429(self):
        import urllib.error

        class Refusing:
            def interest(self, term, frame):
                raise urllib.error.HTTPError("u", 429, "Too Many Requests", {}, None)

        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            out = googletrends.fetch_interest(30, {"Sleep": "sleep app"}, session_factory=Refusing,
                                              sleep=lambda s: None)
        self.assertEqual(out, [])
        self.assertIn("still refused", err.getvalue())

    def test_search_terms_match_taxonomy(self):
        self.assertEqual(set(googletrends.load_terms()), set(load_taxonomy()))


class Extraction(unittest.TestCase):
    def test_intent_phrases(self):
        self.assertTrue(has_intent(sig("Is there an app that tracks my houseplants?")))
        self.assertTrue(has_intent(sig("I'd pay for a calorie counter that works offline")))
        self.assertTrue(has_intent(sig("Any good alternatives to Notion?")))
        self.assertTrue(has_intent(sig("Is there an open-source alternative for Figma?")))
        self.assertFalse(has_intent(sig("Show HN: My weekend project")))

    def test_launches_are_not_asks(self):
        # Pitching an alternative is supply, not demand.
        self.assertFalse(has_intent(sig("Open-source alternative to Notion")))
        self.assertFalse(has_intent(sig("Show HN: I'd pay for this, so I built it")))
        self.assertFalse(has_intent(sig("Launch HN: Acme (YC S26), is there an app for that? Now there is")))
        self.assertFalse(has_intent(sig("Is there an app for X?", source="github")))
        self.assertFalse(has_intent(sig("Is there an app for X?", source="producthunt")))
        self.assertTrue(has_intent(sig("Ask HN: Is there an app for X?")))

    def test_browser_keyword_needs_context(self):
        buckets = assign_concepts(
            [sig("Show HN: A Postgres client that runs in your browser"), sig("Chrome extension to mute tabs")],
            load_taxonomy(),
        )
        self.assertEqual(len(buckets["Browsers & extensions"]), 1)

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
        rising = [sig("x", days_ago=d) for d in (1, 2, 3, 4, 20)]
        cooling = [sig("x", days_ago=d) for d in (5, 25, 26, 27, 28)]
        self.assertGreater(_momentum(rising, NOW, 30), 1)
        self.assertLess(_momentum(cooling, NOW, 30), 1)

    def test_momentum_unknown_with_few_posts(self):
        self.assertIsNone(_momentum([sig("x", days_ago=d) for d in (1, 2, 3)], NOW, 30))

    def test_recent_only_feeds_dont_fake_momentum(self):
        # Product Hunt / charts only list the last few days; they must not read as "rising".
        hn = [sig("x", days_ago=d) for d in (3, 8, 18, 22, 26, 28)]
        ph = [sig("x", "producthunt", days_ago=1) for _ in range(20)]
        self.assertAlmostEqual(_momentum(hn + ph, NOW, 30), _momentum(hn, NOW, 30))

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


class Tls(unittest.TestCase):
    def tearDown(self):
        http.ssl_context.cache_clear()

    @staticmethod
    def _some_real_certs(n=3):
        bundle = Path(ssl.get_default_verify_paths().openssl_cafile or "/etc/ssl/certs/ca-certificates.crt")
        if not bundle.is_file():
            raise unittest.SkipTest("no system CA bundle to borrow certificates from")
        end = "-----END CERTIFICATE-----"
        return "".join(c + end + "\n" for c in bundle.read_text().split(end)[:n])

    def test_macos_keychain_certs_are_trusted(self):
        pem = self._some_real_certs(3) + "-----BEGIN CERTIFICATE-----\nnot base64!!\n-----END CERTIFICATE-----\n"
        baseline = ssl.create_default_context().cert_store_stats()["x509_ca"]
        with mock.patch.object(http.sys, "platform", "darwin"), mock.patch.object(http, "_keychain_pem", return_value=pem):
            http.ssl_context.cache_clear()
            ctx = http.ssl_context()
        self.assertEqual(ctx.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(ctx.check_hostname)
        self.assertGreaterEqual(ctx.cert_store_stats()["x509_ca"], min(3, baseline + 1))

    def test_bad_keychain_entry_skipped(self):
        ctx = ssl.create_default_context()
        pem = self._some_real_certs(2) + "-----BEGIN CERTIFICATE-----\ngarbage\n-----END CERTIFICATE-----\n"
        self.assertEqual(http._load_pem_bundle(ctx, pem), 2)

    def test_keychain_unavailable_still_verifies(self):
        with mock.patch.object(http.sys, "platform", "darwin"), \
                mock.patch.object(http, "_keychain_pem", side_effect=FileNotFoundError("security")):
            http.ssl_context.cache_clear()
            self.assertEqual(http.ssl_context().verify_mode, ssl.CERT_REQUIRED)

    def test_hint_when_every_source_fails_certificates(self):
        def boom(days):
            raise OSError("<urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed>")

        fake = {"a": types.SimpleNamespace(fetch=boom), "b": types.SimpleNamespace(fetch=boom)}
        err = io.StringIO()
        with mock.patch("demand_radar.cli.REGISTRY", fake), contextlib.redirect_stderr(err):
            self.assertEqual(collect(["a", "b"], 30), [])
        self.assertIn("Install Certificates.command", err.getvalue())


class RedditAuth(unittest.TestCase):
    LISTING = {"data": {"children": [{"data": {"title": "Is there an app for X?", "permalink": "/r/a/1",
                                                "score": 5, "num_comments": 1, "created_utc": 4102444800}}]}}

    def test_oauth_when_credentials_set(self):
        calls = []

        def fake_get(url, **kw):
            calls.append((url, kw))
            return b'{"access_token": "tok", "expires_in": 86400}'

        def fake_get_json(url, headers):
            calls.append((url, headers))
            return self.LISTING

        env = {"REDDIT_CLIENT_ID": "id", "REDDIT_CLIENT_SECRET": "sec"}
        with mock.patch.dict("os.environ", env), mock.patch.object(reddit, "get", fake_get), \
                mock.patch.object(reddit, "get_json", fake_get_json):
            out = reddit.fetch(30)
        token_url, token_kw = calls[0]
        self.assertEqual(token_url, "https://www.reddit.com/api/v1/access_token")
        self.assertEqual(token_kw["data"], b"grant_type=client_credentials")
        self.assertTrue(token_kw["headers"]["Authorization"].startswith("Basic "))
        listing_url, headers = calls[1]
        self.assertTrue(listing_url.startswith("https://oauth.reddit.com/r/SomebodyMakeThis/top?"))
        self.assertEqual(headers["Authorization"], "bearer tok")
        self.assertIn("demand-radar", headers["User-Agent"])
        self.assertEqual(len(out), 1)  # same post from every listing is deduplicated

    def test_anonymous_403_explains_setup(self):
        import urllib.error

        def blocked(url, headers):
            raise urllib.error.HTTPError(url, 403, "Blocked", {}, None)

        with mock.patch.dict("os.environ", {}, clear=True), mock.patch.object(reddit, "get_json", blocked):
            with self.assertRaisesRegex(RuntimeError, "REDDIT_CLIENT_ID"):
                reddit.fetch(30)

    def test_reddit_skipped_by_default_without_credentials(self):
        with mock.patch.dict("os.environ", {}, clear=True):
            self.assertNotIn("reddit", default_sources())
            self.assertIn("hackernews", default_sources())
        with mock.patch.dict("os.environ", {"REDDIT_CLIENT_ID": "i", "REDDIT_CLIENT_SECRET": "s"}):
            self.assertIn("reddit", default_sources())

    def test_anonymous_uses_public_json(self):
        urls = reddit.listing_urls(30, "https://www.reddit.com")
        self.assertTrue(urls[0].startswith("https://www.reddit.com/r/SomebodyMakeThis/top.json?t=month"))
        self.assertTrue(any(u.startswith("https://www.reddit.com/search.json?") for u in urls))


class FirstLiveRunRegressions(unittest.TestCase):
    """Cases taken from the first real report."""

    def test_long_bodies_and_news_text_dont_assign_concepts(self):
        tax = load_taxonomy()
        hn = sig("Show HN: Drop – A rootless Linux sandbox", text="Great for productivity, habit of mine, calendar too")
        trend = Signal("googletrends", "nfl scores", "u", NOW, "Game recap: Raiders win the game", 100000)
        gh = Signal("github", "kado: open-source app", "u", NOW, "habit-tracker ios", 500)
        buckets = assign_concepts([hn, trend, gh], tax)
        self.assertNotIn("Games & gamification", buckets)
        self.assertEqual([x.source for x in buckets["Habit & productivity tracking"]], ["github"])

    def test_launch_style_alternatives_are_not_asks(self):
        for title in [
            "Good Alternative to the Cloud",
            "AI Startup launches a faster and cheaper alternative to LLMs for AI automation",
            "Stripe Withholding Balance of $100000",
            "Ask HN: How to Reactivate ChatGPT Account? Is there a way?",
        ]:
            self.assertFalse(has_intent(sig(title, text="I'm so frustrated. Is there a tool?")), title)
        self.assertTrue(has_intent(sig("Ask HN: Any Alternatives to Archive.ph & co?")))
        self.assertTrue(has_intent(sig("Alternatives to Notion for small teams?")))
        # Reddit asks often live in the body.
        self.assertTrue(has_intent(sig("Need help", source="reddit", text="Is there an app that does this?")))

    def test_noise_phrases_dropped(self):
        posts = [sig(f"Hacker News clone in {x}: code and codex") for x in "abc"]
        phrases = emergent_phrases(posts, min_support=3)
        self.assertNotIn("hacker news", phrases)
        self.assertNotIn("code and codex", phrases)

    def test_momentum_is_relative_to_overall_growth(self):
        # Every concept skews recent because the whole feed does: none should look "rising".
        def skewed(label):
            return [sig(f"{label} {d}", days_ago=d) for d in (1, 2, 3, 4, 5, 6, 20)]

        ranked = score_concepts({"A": skewed("a"), "B": skewed("b")}, days=30, now=NOW)
        for c in ranked:
            self.assertAlmostEqual(c.momentum, 1.0, places=2)

    def test_momentum_ranks_share_gainers_above_flat(self):
        flat = [sig(f"f{d}", days_ago=d) for d in (2, 6, 10, 18, 22, 26)]
        spiking = [sig(f"s{d}", days_ago=d) for d in (1, 1, 2, 2, 3, 3, 4, 25)]
        feed = flat + spiking + [sig(f"o{d}", days_ago=d) for d in (1, 2, 3, 4, 5, 20)]
        ranked = {c.concept: c for c in score_concepts({"flat": flat, "spike": spiking}, days=30, now=NOW,
                                                        population=feed)}
        self.assertLess(ranked["flat"].momentum, 1)
        self.assertGreater(ranked["spike"].momentum, 1)

    def test_examples_mix_sources(self):
        posts = [Signal("github", f"repo {i}", f"g{i}", NOW, "", 5000 + i) for i in range(5)]
        posts += [sig("small hn post", points=50), sig("another hn post", points=40)]
        ranked = score_concepts({"X": posts, "Y": posts[:2]}, days=30, now=NOW, examples=4)
        x = next(c for c in ranked if c.concept == "X")
        self.assertEqual([e.source for e in x.examples].count("hackernews"), 2)


if __name__ == "__main__":
    unittest.main()
