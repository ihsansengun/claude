"""Product Hunt launches via the public Atom feed (no votes, but good for concept volume)."""

from __future__ import annotations

import html
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

from ..http import get
from ..models import Signal

NAME = "producthunt"
ATOM = "{http://www.w3.org/2005/Atom}"


def parse(xml_bytes: bytes) -> list[Signal]:
    root = ET.fromstring(xml_bytes)
    signals = []
    for entry in root.iter(f"{ATOM}entry"):
        title = entry.findtext(f"{ATOM}title") or ""
        content = html.unescape(re.sub(r"<[^>]+>", " ", entry.findtext(f"{ATOM}content") or ""))
        link = entry.find(f"{ATOM}link")
        published = entry.findtext(f"{ATOM}published")
        signals.append(
            Signal(
                source=NAME,
                title=title.strip(),
                text=" ".join(content.split()),
                url=link.get("href", "") if link is not None else "",
                created_at=datetime.fromisoformat(published.replace("Z", "+00:00")) if published else None,
            )
        )
    return signals


def fetch(days: int) -> list[Signal]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    return [s for s in parse(get("https://www.producthunt.com/feed")) if s.created_at is None or s.created_at >= cutoff]
