#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "httpx>=0.27.0",
# ]
# ///
"""
Park Alerts NSW — check alerts, closures, and fire bans for NSW National Parks.

Zero-config: works immediately with no API keys.

Usage:
    uv run park_alerts.py                                # all recent alerts
    uv run park_alerts.py --park "Blue Mountains"        # alerts for a specific park
    uv run park_alerts.py --category closures            # only park closures
    uv run park_alerts.py --category fire                # only fire bans
    uv run park_alerts.py --category conditions          # only changed conditions
    uv run park_alerts.py --limit 5                      # limit results
"""

import argparse
import asyncio
import json
import re
import sys
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

CATEGORY_MAP = {
    "closures": "Closed parks",
    "fire": "Fire bans",
    "conditions": "Changed conditions",
    "all": None,
}

RSS_URL = "https://www.nationalparks.nsw.gov.au/api/rssfeed/get"

# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------

CACHE_DIR = Path.home() / ".config" / "park-alerts"
CACHE_TTL_SECONDS = 1800  # 30 minutes


def _cache_path(key: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"{key}.json"


def cache_get(key: str) -> dict | None:
    path = _cache_path(key)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
        if time.time() - data.get("_cached_at", 0) < CACHE_TTL_SECONDS:
            return data.get("payload")
    except (json.JSONDecodeError, KeyError):
        pass
    return None


def cache_set(key: str, payload: dict) -> None:
    path = _cache_path(key)
    path.write_text(json.dumps({"_cached_at": time.time(), "payload": payload}))


# ---------------------------------------------------------------------------
# HTML stripping
# ---------------------------------------------------------------------------


def strip_html(text: str) -> str:
    """Remove HTML tags and decode HTML entities from text."""
    import html as html_mod
    cleaned = re.sub(r"<[^>]+>", "", text)
    cleaned = html_mod.unescape(cleaned)
    # Collapse whitespace
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


# ---------------------------------------------------------------------------
# Park name matching
# ---------------------------------------------------------------------------


def _normalize(s: str) -> str:
    """Lowercase and strip extra whitespace."""
    return " ".join(s.lower().split())


def _similarity_score(query: str, name: str) -> float:
    """Compute a simple similarity score between query and park name.

    Returns a float between 0 and 1. Higher is better.
    """
    q = _normalize(query)
    n = _normalize(name)

    # Exact match
    if q == n:
        return 1.0

    # Substring match
    if q in n:
        return 0.9

    # Starts-with match
    if n.startswith(q):
        return 0.85

    # Word overlap
    q_words = set(q.split())
    n_words = set(n.split())
    if not q_words:
        return 0.0
    common = q_words & n_words
    if common:
        return 0.5 + 0.3 * (len(common) / max(len(q_words), len(n_words)))

    # Prefix match on individual words
    for qw in q_words:
        for nw in n_words:
            if nw.startswith(qw) or qw.startswith(nw):
                return 0.4

    return 0.0


def matches_park(query: str, title: str) -> bool:
    """Check if a park title fuzzy-matches the query."""
    return _similarity_score(query, title) > 0.3


# ---------------------------------------------------------------------------
# RSS parsing
# ---------------------------------------------------------------------------


@dataclass
class Alert:
    park: str
    category: str
    description: str
    date: str
    date_sort: float  # epoch for sorting
    link: str


def parse_rss(xml_text: str) -> list[Alert]:
    """Parse RSS XML into a list of Alert objects."""
    alerts = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        print(f"Error parsing RSS XML: {e}", file=sys.stderr)
        return alerts

    # RSS 2.0: channel/item
    for item in root.iter("item"):
        title = item.findtext("title", "").strip()
        description_raw = item.findtext("description", "").strip()
        category = item.findtext("category", "").strip()
        pub_date = item.findtext("pubDate", "").strip()
        link = item.findtext("link", "").strip()

        # Strip HTML from description
        description = strip_html(description_raw)

        # Parse RFC 822 date for sorting
        date_sort = 0.0
        date_str = ""
        if pub_date:
            try:
                dt = parsedate_to_datetime(pub_date)
                date_sort = dt.timestamp()
                date_str = dt.strftime("%Y-%m-%d")
            except (ValueError, TypeError):
                date_str = pub_date

        alerts.append(Alert(
            park=title,
            category=category,
            description=description,
            date=date_str,
            date_sort=date_sort,
            link=link,
        ))

    return alerts


# ---------------------------------------------------------------------------
# Error output
# ---------------------------------------------------------------------------


def _err(message: str, **extra) -> None:
    """Print a JSON error to stdout and exit."""
    out = {"error": message}
    out.update(extra)
    print(json.dumps(out, indent=2))
    sys.exit(1)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check alerts, closures, and fire bans for NSW National Parks"
    )
    parser.add_argument(
        "--park", "-p", help="Filter by park name (fuzzy match)"
    )
    parser.add_argument(
        "--category",
        "-c",
        choices=["closures", "fire", "conditions", "all"],
        default="all",
        help="Filter by alert category (default: all)",
    )
    parser.add_argument(
        "--limit",
        "-l",
        type=int,
        default=10,
        help="Maximum number of results (default: 10)",
    )
    parser.add_argument("--no-cache", action="store_true", help="Skip cache")
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


async def main() -> None:
    import httpx

    args = parse_args()

    # Cache key
    cache_key = "rss_feed"
    if args.no_cache:
        feed_cache = _cache_path(cache_key)
        if feed_cache.exists():
            feed_cache.unlink()

    # 1. Fetch RSS feed
    cached_data = None if args.no_cache else cache_get(cache_key)
    if cached_data:
        print("Using cached RSS feed", file=sys.stderr)
        xml_text = cached_data.get("xml", "")
    else:
        async with httpx.AsyncClient() as client:
            try:
                print(f"Fetching RSS feed from {RSS_URL}...", file=sys.stderr)
                resp = await client.get(RSS_URL, timeout=15)
                resp.raise_for_status()
                xml_text = resp.text
                cache_set(cache_key, {"xml": xml_text})
            except Exception as e:
                print(f"Error fetching RSS feed: {e}", file=sys.stderr)
                _err(f"Failed to fetch park alerts from NSW National Parks RSS feed: {e}")

    # 2. Parse RSS
    alerts = parse_rss(xml_text)
    if not alerts:
        _err("No alerts found in the RSS feed. The feed may be temporarily empty or unavailable.")

    # 3. Filter by category
    category_filter = CATEGORY_MAP.get(args.category)
    if category_filter:
        alerts = [a for a in alerts if a.category == category_filter]

    # 4. Filter by park name
    if args.park:
        alerts = [a for a in alerts if matches_park(args.park, a.park)]

    # 5. Sort by date descending (most recent first)
    alerts.sort(key=lambda a: a.date_sort, reverse=True)

    # 6. Limit results
    alerts = alerts[: args.limit]

    # 7. Build output
    result = {
        "query": {
            "park": args.park or "all",
            "category": args.category,
        },
        "results": {
            "count": len(alerts),
            "alerts": [
                {
                    "park": a.park,
                    "category": a.category,
                    "description": a.description,
                    "date": a.date,
                    "link": a.link,
                }
                for a in alerts
            ],
        },
        "source": "NSW National Parks and Wildlife Service",
        "source_url": "https://www.nationalparks.nsw.gov.au/alerts/alerts-list",
    }

    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())
