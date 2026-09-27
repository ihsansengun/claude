"""Google Trends: what people are searching for, and whether it's growing.

Two feeds, both unofficial and keyless:

- Trending searches RSS: today's breakout searches, as ordinary signals whose
  engagement is Google's approximate search volume. Mostly news and events,
  so it only adds weight when a trend happens to hit an app concept.
- Interest over time: for each concept in `search_terms.json`, the relative
  search interest across the window. These points are pinned to their concept
  (`Signal.series_for`) and feed the scoring's search-growth component rather
  than volume or engagement, because Trends values are 0-100 relative to each
  term's own peak and aren't comparable across terms.

The interest endpoints are rate limited hard (HTTP 429). Requests are spaced
out, and when Google starts refusing, the source returns what it has so far.
"""

from __future__ import annotations

import http.cookiejar
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

from ..http import USER_AGENT, get, ssl_context
from ..models import Signal

NAME = "googletrends"
GEO = "US"
TERMS_FILE = Path(__file__).resolve().parent.parent / "search_terms.json"
REQUEST_DELAY = 1.5  # seconds between interest requests
HT = "{https://trends.google.com/trending/rss}"


# --- trending searches RSS -------------------------------------------------

def _traffic(text: str | None) -> float:
    """'200+', '2,000+', '10K+', '1M+' -> number."""
    m = re.match(r"([\d.,]+)\s*([KkMm]?)", (text or "").strip())
    if not m:
        return 0.0
    value = float(m.group(1).replace(",", ""))
    return value * {"k": 1e3, "m": 1e6}.get(m.group(2).lower(), 1)


def parse_trending(xml_bytes: bytes) -> list[Signal]:
    root = ET.fromstring(xml_bytes)
    signals = []
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        if not title:
            continue
        news = [n.findtext(f"{HT}news_item_title") or "" for n in item.iter(f"{HT}news_item")]
        pub = item.findtext("pubDate")
        signals.append(
            Signal(
                source=NAME,
                title=title,
                text=" ".join(n.strip() for n in news if n.strip()),
                url="https://trends.google.com/trends/explore?" + urllib.parse.urlencode({"q": title, "geo": GEO}),
                created_at=parsedate_to_datetime(pub).astimezone(timezone.utc) if pub else None,
                # Log-scale later in scoring keeps a 1M+ news spike from swamping everything.
                engagement=_traffic(item.findtext(f"{HT}approx_traffic")),
            )
        )
    return signals


# --- interest over time ----------------------------------------------------

def _strip_xssi(body: bytes) -> dict:
    """Trends API responses start with an anti-JSON-hijacking prefix like `)]}',`."""
    text = body.decode("utf-8")
    return json.loads(text[text.index("{"):])


def _timeframe(days: int) -> str:
    if days <= 7:
        return "now 7-d"
    if days <= 30:
        return "today 1-m"
    if days <= 90:
        return "today 3-m"
    return "today 12-m"


def parse_interest(payload: dict, term: str, concept: str) -> list[Signal]:
    signals = []
    url = "https://trends.google.com/trends/explore?" + urllib.parse.urlencode({"q": term, "geo": GEO})
    for point in payload.get("default", {}).get("timelineData", []):
        if point.get("isPartial"):  # the current, incomplete bucket would read as a drop
            continue
        signals.append(
            Signal(
                source=NAME,
                title=term,
                url=url,
                created_at=datetime.fromtimestamp(int(point["time"]), tz=timezone.utc),
                engagement=float(point.get("value", [0])[0]),
                series_for=concept,
            )
        )
    return signals


class _Session:
    def __init__(self) -> None:
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPSHandler(context=ssl_context()),
            urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()),
        )
        self.opener.addheaders = [("User-Agent", USER_AGENT), ("Accept-Language", "en-US")]
        # Visiting the home page sets the NID cookie; the API 429s without it.
        self.get(f"https://trends.google.com/trends/?geo={GEO}")

    def get(self, url: str) -> bytes:
        with self.opener.open(url, timeout=20) as resp:
            return resp.read()

    def interest(self, term: str, timeframe: str) -> dict:
        req = {"comparisonItem": [{"keyword": term, "geo": GEO, "time": timeframe}], "category": 0, "property": ""}
        explore = _strip_xssi(
            self.get("https://trends.google.com/trends/api/explore?"
                     + urllib.parse.urlencode({"hl": "en-US", "tz": 0, "req": json.dumps(req)}))
        )
        widget = next(w for w in explore["widgets"] if w.get("id") == "TIMESERIES")
        time.sleep(REQUEST_DELAY)
        return _strip_xssi(
            self.get("https://trends.google.com/trends/api/widgetdata/multiline?"
                     + urllib.parse.urlencode({"hl": "en-US", "tz": 0, "req": json.dumps(widget["request"]),
                                               "token": widget["token"]}))
        )


def load_terms(path: Path = TERMS_FILE) -> dict[str, str]:
    return {k: v for k, v in json.loads(path.read_text()).items() if not k.startswith("_")}


def fetch_interest(days: int, terms: dict[str, str]) -> list[Signal]:
    session = _Session()
    signals: list[Signal] = []
    frame = _timeframe(days)
    for n, (concept, term) in enumerate(terms.items()):
        try:
            signals += parse_interest(session.interest(term, frame), term, concept)
        except urllib.error.HTTPError as exc:
            if exc.code == 429:
                print(f"    googletrends: rate limited after {n}/{len(terms)} terms; keeping partial data", file=sys.stderr)
                break
            print(f"    googletrends: '{term}' failed ({exc})", file=sys.stderr)
        time.sleep(REQUEST_DELAY)
    return signals


def fetch(days: int) -> list[Signal]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    signals: list[Signal] = []
    errors = []
    try:
        rss = get(f"https://trends.google.com/trending/rss?geo={GEO}")
        signals += [s for s in parse_trending(rss) if s.created_at is None or s.created_at >= cutoff]
    except Exception as exc:
        errors.append(f"trending RSS: {exc}")
    try:
        signals += fetch_interest(days, load_terms())
    except Exception as exc:
        errors.append(f"interest: {exc}")
    if errors and not signals:
        raise RuntimeError("; ".join(errors))
    for e in errors:
        print(f"    googletrends: {e}", file=sys.stderr)
    return signals
