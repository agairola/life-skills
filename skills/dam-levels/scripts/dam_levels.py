#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "httpx>=0.27.0",
# ]
# ///
"""
Dam Levels — check current dam levels and water storage for Greater Sydney.

Zero-config: works immediately with no API keys.

Usage:
    uv run dam_levels.py                       # all Greater Sydney dams (default)
    uv run dam_levels.py --all                 # all Greater Sydney dams (explicit)
    uv run dam_levels.py --dam "Warragamba"    # specific dam (fuzzy match)
    uv run dam_levels.py --no-cache            # force fresh data
"""

import argparse
import asyncio
import json
import re
import sys
import time
from datetime import date
from pathlib import Path

# ---------------------------------------------------------------------------
# Fallback data
# ---------------------------------------------------------------------------

FALLBACK_DAMS = [
    {"name": "Warragamba Dam", "capacity_pct": 95.8, "capacity_ml": 2027255, "total_capacity_ml": 2031000},
    {"name": "Woronora Dam", "capacity_pct": 97.2, "capacity_ml": 68175, "total_capacity_ml": 71790},
    {"name": "Cataract Dam", "capacity_pct": 98.1, "capacity_ml": 93290, "total_capacity_ml": 97190},
    {"name": "Cordeaux Dam", "capacity_pct": 96.5, "capacity_ml": 50710, "total_capacity_ml": 54250},
    {"name": "Avon Dam", "capacity_pct": 93.2, "capacity_ml": 195240, "total_capacity_ml": 214640},
    {"name": "Nepean Dam", "capacity_pct": 99.1, "capacity_ml": 66750, "total_capacity_ml": 67730},
    {"name": "Prospect Reservoir", "capacity_pct": 83.5, "capacity_ml": 29515, "total_capacity_ml": 33330},
    {"name": "Fitzroy Falls Reservoir", "capacity_pct": 91.0, "capacity_ml": 9110, "total_capacity_ml": 10000},
    {"name": "Wingecarribee Reservoir", "capacity_pct": 88.3, "capacity_ml": 24330, "total_capacity_ml": 27580},
    {"name": "Tallowa Dam (Shoalhaven)", "capacity_pct": 85.0, "capacity_ml": 7480, "total_capacity_ml": 8800},
]
FALLBACK_DATE = "2026-03-01"

# Known total capacities for enriching scraped data (ML)
KNOWN_CAPACITIES = {
    "warragamba dam": 2031000,
    "woronora dam": 71790,
    "cataract dam": 97190,
    "cordeaux dam": 54250,
    "avon dam": 214640,
    "nepean dam": 67730,
    "prospect reservoir": 33330,
    "fitzroy falls reservoir": 10000,
    "wingecarribee reservoir": 27580,
    "tallowa dam (shoalhaven)": 8800,
    "tallowa dam": 8800,
}

WATERNSW_URL = "https://www.waternsw.com.au/supply/dam-levels/greater-sydneys-dam-levels"

# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------

CACHE_DIR = Path.home() / ".config" / "dam-levels"
CACHE_TTL_SECONDS = 21600  # 6 hours


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
# Scraping
# ---------------------------------------------------------------------------


def _parse_dam_levels(html: str) -> list[dict] | None:
    """Parse dam names and capacity percentages from WaterNSW HTML.

    The page typically contains dam names followed by percentage values.
    We try several regex patterns to handle different page layouts.
    """
    dams: list[dict] = []

    # Pattern 1: Look for dam name followed by percentage (common layout)
    # e.g., "Warragamba Dam" ... "95.8%"
    pattern1 = re.compile(
        r'(?:>|")\s*([\w\s()]+(?:Dam|Reservoir))\s*(?:</[^>]+>)?\s*'
        r'(?:<[^>]+>\s*)*?'
        r'([\d]+\.?\d*)\s*%',
        re.IGNORECASE,
    )

    # Pattern 2: Percentage before or near dam name
    pattern2 = re.compile(
        r'([\d]+\.?\d*)\s*%\s*(?:<[^>]+>\s*)*?\s*([\w\s()]+(?:Dam|Reservoir))',
        re.IGNORECASE,
    )

    # Pattern 3: JSON-like data embedded in the page
    pattern3 = re.compile(
        r'"name"\s*:\s*"([^"]*(?:Dam|Reservoir)[^"]*)"[^}]*?"percentage"\s*:\s*([\d.]+)',
        re.IGNORECASE,
    )

    # Pattern 4: Data attributes
    pattern4 = re.compile(
        r'data-dam[_-]?name\s*=\s*"([^"]*)"[^>]*?data-(?:percentage|level)\s*=\s*"([\d.]+)"',
        re.IGNORECASE,
    )

    # Pattern 5: Table rows with dam name and percentage
    pattern5 = re.compile(
        r'<t[dr][^>]*>\s*(?:<[^>]+>\s*)*?([\w\s()]+(?:Dam|Reservoir))(?:\s*</[^>]+>)*\s*</t[dr]>'
        r'\s*<t[dr][^>]*>\s*(?:<[^>]+>\s*)*?([\d]+\.?\d*)\s*%',
        re.IGNORECASE,
    )

    seen_names: set[str] = set()

    for pattern in [pattern1, pattern3, pattern4, pattern5]:
        for match in pattern.finditer(html):
            name = match.group(1).strip()
            pct = float(match.group(2))
            name_lower = name.lower()
            if name_lower not in seen_names and 0 < pct <= 100:
                seen_names.add(name_lower)
                total_cap = KNOWN_CAPACITIES.get(name_lower, 0)
                volume = round(total_cap * pct / 100) if total_cap else 0
                dams.append({
                    "name": name,
                    "capacity_pct": pct,
                    "volume_ml": volume,
                    "total_capacity_ml": total_cap,
                })

    # Try pattern2 (reversed order) if nothing found yet
    if not dams:
        for match in pattern2.finditer(html):
            pct = float(match.group(1))
            name = match.group(2).strip()
            name_lower = name.lower()
            if name_lower not in seen_names and 0 < pct <= 100:
                seen_names.add(name_lower)
                total_cap = KNOWN_CAPACITIES.get(name_lower, 0)
                volume = round(total_cap * pct / 100) if total_cap else 0
                dams.append({
                    "name": name,
                    "capacity_pct": pct,
                    "volume_ml": volume,
                    "total_capacity_ml": total_cap,
                })

    return dams if dams else None


async def fetch_dam_levels(client: "httpx.AsyncClient") -> tuple[list[dict] | None, str]:
    """Fetch and parse dam levels from WaterNSW.

    Returns (dams, data_source) where data_source is 'live' or 'fallback'.
    """
    try:
        print("Fetching dam levels from WaterNSW...", file=sys.stderr)
        resp = await client.get(
            WATERNSW_URL,
            timeout=15,
            headers={"User-Agent": "dam-levels-cli/1.0"},
            follow_redirects=True,
        )
        if resp.status_code != 200:
            print(f"WaterNSW returned status {resp.status_code}", file=sys.stderr)
            return None, "fallback"

        html = resp.text
        dams = _parse_dam_levels(html)
        if dams:
            print(f"Parsed {len(dams)} dams from live data", file=sys.stderr)
            return dams, "live"
        else:
            print("Could not parse dam data from HTML, using fallback", file=sys.stderr)
            return None, "fallback"

    except Exception as e:
        print(f"Error fetching WaterNSW page: {e}", file=sys.stderr)
        return None, "fallback"


def get_fallback_dams() -> list[dict]:
    """Return embedded fallback dam data."""
    return [
        {
            "name": d["name"],
            "capacity_pct": d["capacity_pct"],
            "volume_ml": d["capacity_ml"],
            "total_capacity_ml": d["total_capacity_ml"],
        }
        for d in FALLBACK_DAMS
    ]


# ---------------------------------------------------------------------------
# Fuzzy matching
# ---------------------------------------------------------------------------


def _normalize(s: str) -> str:
    """Lowercase and strip extra whitespace."""
    return " ".join(s.lower().split())


def fuzzy_match_dam(query: str, dams: list[dict]) -> list[dict]:
    """Fuzzy match a dam name against the dam list."""
    q = _normalize(query)

    # Exact match
    for dam in dams:
        if _normalize(dam["name"]) == q:
            return [dam]

    # Substring match
    matches = [d for d in dams if q in _normalize(d["name"])]
    if matches:
        return matches

    # Word overlap match
    q_words = set(q.split())
    matches = []
    for dam in dams:
        name_words = set(_normalize(dam["name"]).split())
        if q_words & name_words:
            matches.append(dam)
    if matches:
        return matches

    # Prefix match on words
    matches = []
    for dam in dams:
        name_lower = _normalize(dam["name"])
        for qw in q.split():
            if any(nw.startswith(qw) or qw.startswith(nw) for nw in name_lower.split()):
                matches.append(dam)
                break

    return matches


# ---------------------------------------------------------------------------
# Water restrictions
# ---------------------------------------------------------------------------


def water_restriction_status(total_pct: float) -> str:
    """Determine water restriction status based on total system capacity."""
    if total_pct > 60:
        return "No restrictions (system above 60%)"
    elif total_pct >= 50:
        return "Level 1 restrictions likely (system at 50-60%)"
    elif total_pct >= 40:
        return "Level 2 restrictions likely (system at 40-50%)"
    else:
        return "Severe restrictions likely (system below 40%)"


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
    parser = argparse.ArgumentParser(description="Check dam levels for Greater Sydney")
    parser.add_argument("--dam", "-d", help="Specific dam name (fuzzy matched)")
    parser.add_argument("--all", "-a", action="store_true", default=True, help="All Greater Sydney dams (default)")
    parser.add_argument("--no-cache", action="store_true", help="Force fresh data")
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


async def main() -> None:
    import httpx

    args = parse_args()

    # Cache key
    cache_key = "dam_levels"
    if args.no_cache:
        data_cache = _cache_path(cache_key)
        if data_cache.exists():
            data_cache.unlink()
    else:
        cached = cache_get(cache_key)
        if cached:
            # If --dam filter, apply it to cached results
            if args.dam:
                matches = fuzzy_match_dam(args.dam, cached.get("dams", []))
                if not matches:
                    available = [d["name"] for d in cached.get("dams", [])]
                    _err(
                        f"No dam matching '{args.dam}' found.",
                        available_dams=available,
                        suggestion="Try one of the listed dam names.",
                    )
                filtered = dict(cached)
                filtered["dams"] = matches
                print(json.dumps(filtered, indent=2))
                return
            print(json.dumps(cached, indent=2))
            return

    async with httpx.AsyncClient() as client:
        dams, data_source = await fetch_dam_levels(client)

    if not dams:
        # Use fallback
        dams = get_fallback_dams()
        data_source = "fallback"

    # Calculate total system capacity
    total_volume = sum(d.get("volume_ml", 0) for d in dams)
    total_capacity = sum(d.get("total_capacity_ml", 0) for d in dams)
    total_pct = round(total_volume / total_capacity * 100, 1) if total_capacity else 0

    # Apply --dam filter
    result_dams = dams
    if args.dam:
        matches = fuzzy_match_dam(args.dam, dams)
        if not matches:
            available = [d["name"] for d in dams]
            _err(
                f"No dam matching '{args.dam}' found.",
                available_dams=available,
                suggestion="Try one of the listed dam names.",
            )
        result_dams = matches

    # Build output
    result: dict = {
        "total_system": {
            "capacity_pct": total_pct,
            "volume_ml": total_volume,
            "total_capacity_ml": total_capacity,
        },
        "dams": result_dams,
        "water_restrictions": water_restriction_status(total_pct),
        "data_source": data_source,
        "source": "WaterNSW",
        "source_url": WATERNSW_URL,
        "last_updated": date.today().isoformat(),
    }

    if data_source == "fallback":
        result["fallback_note"] = f"Live data unavailable. Showing cached data from {FALLBACK_DATE}."

    # Cache the full (unfiltered) result
    if not args.no_cache and not args.dam:
        cache_set(cache_key, result)

    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())
