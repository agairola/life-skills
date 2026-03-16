#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "httpx>=0.27.0",
# ]
# ///
"""
UV Sun — check current UV index and sun safety advice for Australian cities.

Zero-config: works immediately with no API keys.

Usage:
    uv run uv_sun.py                    # Sydney (default)
    uv run uv_sun.py --city Melbourne   # specific city
    uv run uv_sun.py --all              # all cities sorted by UV index
    uv run uv_sun.py --no-cache         # skip cache
"""

import argparse
import asyncio
import json
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ARPANSA_URL = "https://uvdata.arpansa.gov.au/xml/uvvalues.xml"
SOURCE_URL = "https://www.arpansa.gov.au/our-services/monitoring/ultraviolet-radiation-monitoring"

# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------

CACHE_DIR = Path.home() / ".config" / "uv-sun"
CACHE_TTL_SECONDS = 600  # 10 minutes


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
# UV category and advice
# ---------------------------------------------------------------------------


def uv_category(index: float) -> str:
    """Map UV index to category per WHO/ARPANSA scale."""
    if index < 0:
        return "Unknown"
    if index <= 2:
        return "Low"
    if index <= 5:
        return "Moderate"
    if index <= 7:
        return "High"
    if index <= 10:
        return "Very High"
    return "Extreme"


def sun_protection_advice(category: str) -> str:
    """Sun protection advice based on UV category."""
    advice = {
        "Low": "No sun protection required for most people",
        "Moderate": "Sun protection recommended from 10am to 3pm",
        "High": "Sun protection recommended from 9am to 4pm",
        "Very High": "Sun protection essential from 8am to 5pm",
        "Extreme": "Sun protection essential all day — avoid outdoor exposure if possible",
    }
    return advice.get(category, "Check UV index before going outside")


def exercise_advice(category: str) -> str:
    """Outdoor exercise advice based on UV category."""
    advice = {
        "Low": "Safe to exercise outdoors without sun protection",
        "Moderate": "Safe to exercise outdoors with sun protection",
        "High": "Exercise outdoors with full sun protection — hat, sunscreen, sunglasses",
        "Very High": "Consider exercising early morning or late afternoon to avoid peak UV",
        "Extreme": "Avoid outdoor exercise during peak UV hours — exercise indoors or before 8am / after 5pm",
    }
    return advice.get(category, "Check UV index before exercising outdoors")


def spf_recommendation(category: str) -> str:
    """SPF recommendation based on UV category."""
    spf = {
        "Low": "SPF 15+ if spending extended time outdoors",
        "Moderate": "SPF 30+",
        "High": "SPF 50+",
        "Very High": "SPF 50+",
        "Extreme": "SPF 50+ reapplied every 2 hours",
    }
    return spf.get(category, "SPF 30+")


# ---------------------------------------------------------------------------
# City matching
# ---------------------------------------------------------------------------


def _normalize(s: str) -> str:
    """Lowercase and strip extra whitespace."""
    return " ".join(s.lower().split())


def fuzzy_match_city(query: str, cities: list[dict]) -> dict | None:
    """Fuzzy match a city query against the parsed city list.

    Tries: exact match, substring match, word overlap.
    """
    q = _normalize(query)

    # Exact match
    for city in cities:
        if _normalize(city["city"]) == q:
            return city

    # Substring match
    matches = []
    for city in cities:
        city_name = _normalize(city["city"])
        if q in city_name or city_name in q:
            matches.append(city)

    if len(matches) == 1:
        return matches[0]

    # Word overlap
    if not matches:
        q_words = set(q.split())
        for city in cities:
            city_words = set(_normalize(city["city"]).split())
            if q_words & city_words:
                matches.append(city)

    if len(matches) == 1:
        return matches[0]
    if matches:
        # Return shortest name (most specific)
        return min(matches, key=lambda c: len(c["city"]))

    return None


# ---------------------------------------------------------------------------
# XML parsing
# ---------------------------------------------------------------------------


def parse_uv_xml(xml_text: str) -> list[dict]:
    """Parse ARPANSA UV XML into a list of city dicts."""
    root = ET.fromstring(xml_text)
    cities = []

    for location in root.iter("location"):
        city_id = location.get("id", "")
        index_el = location.find("index")
        time_el = location.find("time")
        date_el = location.find("date")
        status_el = location.find("status")

        if index_el is None or not index_el.text:
            continue

        try:
            uv_index = float(index_el.text)
        except (ValueError, TypeError):
            continue

        city_time = time_el.text.strip() if time_el is not None and time_el.text else ""
        city_date = date_el.text.strip() if date_el is not None and date_el.text else ""
        status = status_el.text.strip() if status_el is not None and status_el.text else ""

        # Normalize date from DD/MM/YYYY to YYYY-MM-DD
        if city_date and "/" in city_date:
            parts = city_date.split("/")
            if len(parts) == 3:
                city_date = f"{parts[2]}-{parts[1]}-{parts[0]}"

        category = uv_category(uv_index)

        cities.append({
            "city": city_id,
            "uv_index": uv_index,
            "category": category,
            "time": city_time,
            "date": city_date,
            "status": status,
        })

    return cities


def build_city_result(city_data: dict) -> dict:
    """Build a full result dict for a single city."""
    category = city_data["category"]
    return {
        "city": city_data["city"],
        "uv_index": city_data["uv_index"],
        "category": category,
        "time": city_data["time"],
        "date": city_data["date"],
        "sun_protection": sun_protection_advice(category),
        "exercise_advice": exercise_advice(category),
        "spf_recommendation": spf_recommendation(category),
        "source": "ARPANSA",
        "source_url": SOURCE_URL,
    }


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
        description="Check UV index and sun safety for Australian cities"
    )
    parser.add_argument(
        "--city", "-c", default="Sydney",
        help="City name to look up (default: Sydney, fuzzy matched)"
    )
    parser.add_argument(
        "--all", "-a", action="store_true",
        help="Show all cities sorted by UV index descending"
    )
    parser.add_argument(
        "--no-cache", action="store_true",
        help="Skip cache and fetch fresh data"
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


async def main() -> None:
    import httpx

    args = parse_args()

    cache_key = "uv_data"
    if args.no_cache:
        path = _cache_path(cache_key)
        if path.exists():
            path.unlink()

    # Fetch UV data
    cached_data = None if args.no_cache else cache_get(cache_key)
    if cached_data:
        print("Using cached UV data", file=sys.stderr)
        xml_text = cached_data.get("xml")
    else:
        try:
            async with httpx.AsyncClient() as client:
                print("Fetching UV data from ARPANSA...", file=sys.stderr)
                resp = await client.get(ARPANSA_URL, timeout=15)
                resp.raise_for_status()
                xml_text = resp.text
                cache_set(cache_key, {"xml": xml_text})
        except Exception as e:
            print(f"Error fetching UV data: {e}", file=sys.stderr)
            _err(f"Failed to fetch UV data from ARPANSA: {e}")

    # Parse XML
    cities = parse_uv_xml(xml_text)
    if not cities:
        _err("No UV data available from ARPANSA. The feed may be temporarily unavailable.")

    # --all mode: return all cities sorted by UV index descending
    if args.all:
        cities.sort(key=lambda c: c["uv_index"], reverse=True)
        result = {
            "cities": [build_city_result(c) for c in cities],
            "source": "ARPANSA",
            "source_url": SOURCE_URL,
        }
        print(json.dumps(result, indent=2))
        return

    # Single city mode
    matched = fuzzy_match_city(args.city, cities)
    if not matched:
        available = sorted(c["city"] for c in cities)
        _err(
            f"No city matching '{args.city}' found in ARPANSA data.",
            available_cities=available,
            suggestion="Try one of the listed city names.",
        )

    result = build_city_result(matched)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
