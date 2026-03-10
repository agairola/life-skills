#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "httpx>=0.27.0",
# ]
# ///
"""
Rental Prices Sydney — check median rental prices for Sydney suburbs.

Zero-config: works immediately with no API keys.

Usage:
    uv run rental_prices.py                                  # top 10 most affordable 2br units
    uv run rental_prices.py --suburb "Newtown"               # rents for a specific suburb
    uv run rental_prices.py --postcode 2042                  # search by postcode
    uv run rental_prices.py --budget 500 --type unit --bedrooms 2  # suburbs within budget
    uv run rental_prices.py --location "Bondi" --radius 5    # nearby suburbs
    uv run rental_prices.py --lat -33.89 --lng 151.27        # nearby by coordinates
"""

import argparse
import asyncio
import json
import math
import sys
import time
from dataclasses import dataclass
from pathlib import Path

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class Location:
    lat: float
    lng: float
    city: str
    state: str
    postcode: str
    country: str
    method: str  # how we detected it


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------

CACHE_DIR = Path.home() / ".config" / "rental-prices"
CACHE_TTL_SECONDS = 3600  # 1 hour


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
# Geolocation
# ---------------------------------------------------------------------------

AU_STATES = {
    "New South Wales": "NSW",
    "Victoria": "VIC",
    "Queensland": "QLD",
    "South Australia": "SA",
    "Western Australia": "WA",
    "Tasmania": "TAS",
    "Northern Territory": "NT",
    "Australian Capital Territory": "ACT",
    "NSW": "NSW",
    "VIC": "VIC",
    "QLD": "QLD",
    "SA": "SA",
    "WA": "WA",
    "TAS": "TAS",
    "NT": "NT",
    "ACT": "ACT",
}

NOMINATIM_HEADERS = {"User-Agent": "rental-prices-cli/1.0"}


async def _geocode_forward(
    client: "httpx.AsyncClient", query: str
) -> Location | None:
    """Forward geocode via Nominatim /search — convert place name to coords."""
    try:
        resp = await client.get(
            "https://nominatim.openstreetmap.org/search",
            params={
                "q": query,
                "countrycodes": "au",
                "format": "jsonv2",
                "limit": 1,
                "addressdetails": 1,
            },
            headers=NOMINATIM_HEADERS,
            timeout=10,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        if not data:
            return None
        result = data[0]
        addr = result.get("address", {})
        suburb = addr.get("suburb") or addr.get("town") or addr.get("city") or ""
        state_raw = addr.get("state", "")
        state = AU_STATES.get(state_raw, state_raw)
        return Location(
            lat=float(result["lat"]),
            lng=float(result["lon"]),
            city=suburb,
            state=state,
            postcode=addr.get("postcode", ""),
            country=addr.get("country", "Australia"),
            method="nominatim-forward",
        )
    except Exception:
        return None


async def _geocode_reverse(
    client: "httpx.AsyncClient", lat: float, lng: float
) -> dict | None:
    """Reverse geocode via Nominatim /reverse — convert coords to address info."""
    try:
        resp = await client.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={
                "lat": lat,
                "lon": lng,
                "format": "jsonv2",
                "addressdetails": 1,
            },
            headers=NOMINATIM_HEADERS,
            timeout=10,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        addr = data.get("address", {})
        suburb = addr.get("suburb") or addr.get("town") or addr.get("city") or ""
        state_raw = addr.get("state", "")
        state = AU_STATES.get(state_raw, state_raw)
        return {
            "city": suburb,
            "state": state,
            "postcode": addr.get("postcode", ""),
            "country": addr.get("country", "Australia"),
        }
    except Exception:
        return None


async def _geolocate_ip(client: "httpx.AsyncClient") -> Location | None:
    """IP-based geolocation via ip-api.com — city-level, no key needed."""
    try:
        resp = await client.get(
            "http://ip-api.com/json/",
            params={"fields": "status,country,regionName,city,zip,lat,lon,timezone"},
            timeout=5,
        )
        data = resp.json()
        if data.get("status") != "success":
            return None
        state_raw = data.get("regionName", "")
        state = AU_STATES.get(state_raw, state_raw)
        return Location(
            lat=data["lat"],
            lng=data["lon"],
            city=data.get("city", ""),
            state=state,
            postcode=data.get("zip", ""),
            country=data.get("country", ""),
            method="ip-api.com",
        )
    except Exception:
        return None


async def location_from_args(
    args: argparse.Namespace, client: "httpx.AsyncClient"
) -> Location | None:
    """Build a Location from CLI args, or auto-detect via IP."""
    if args.lat is not None and args.lng is not None:
        # Reverse geocode to get accurate suburb/state/postcode
        rev = await _geocode_reverse(client, args.lat, args.lng)
        if rev:
            return Location(
                lat=args.lat,
                lng=args.lng,
                city=getattr(args, "location", None) or rev["city"],
                state=rev["state"],
                postcode=rev["postcode"],
                country=rev["country"],
                method="manual",
            )
        # Fall back to IP enrichment if Nominatim fails
        ip_loc = await _geolocate_ip(client)
        return Location(
            lat=args.lat,
            lng=args.lng,
            city=getattr(args, "location", None) or (ip_loc.city if ip_loc else ""),
            state=ip_loc.state if ip_loc else "",
            postcode=ip_loc.postcode if ip_loc else "",
            country="AU",
            method="manual",
        )
    if args.location:
        # Forward geocode to get accurate coords for the place
        geo_loc = await _geocode_forward(client, args.location)
        if geo_loc:
            return geo_loc
        # Fall back to IP-based behavior if Nominatim fails
        print(f"Warning: geocoding failed for '{args.location}', falling back to IP geolocation", file=sys.stderr)
        ip_loc = await _geolocate_ip(client)
        if ip_loc:
            ip_loc.city = args.location or ip_loc.city
            ip_loc.method = "ip-fallback"
            return ip_loc
        return Location(
            lat=0,
            lng=0,
            city=args.location or "",
            state="",
            postcode="",
            country="AU",
            method="manual",
        )
    # Auto-detect via IP
    return await _geolocate_ip(client)


# ---------------------------------------------------------------------------
# Distance calculation
# ---------------------------------------------------------------------------


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlng / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ---------------------------------------------------------------------------
# Suburb name matching
# ---------------------------------------------------------------------------


def _normalize(s: str) -> str:
    """Lowercase and strip extra whitespace."""
    return " ".join(s.lower().split())


def _similarity_score(query: str, name: str) -> float:
    """Compute a simple similarity score between query and suburb name.

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


# ---------------------------------------------------------------------------
# Embedded rental data
# ---------------------------------------------------------------------------

RENTAL_DATA = {
    "data_quarter": "Q4 2025",
    "data_source": "NSW DCJ Rent and Sales Report",
    "suburbs": [
        {"suburb": "Alexandria", "postcode": "2015", "lat": -33.9030, "lng": 151.1950, "rents": {"unit": {"1br": 580, "2br": 780, "3br": 1000}, "house": {"2br": 850, "3br": 1100, "4br": 1400}}},
        {"suburb": "Ashfield", "postcode": "2131", "lat": -33.8890, "lng": 151.1240, "rents": {"unit": {"1br": 480, "2br": 620, "3br": 780}, "house": {"2br": 650, "3br": 850, "4br": 1050}}},
        {"suburb": "Balmain", "postcode": "2041", "lat": -33.8560, "lng": 151.1790, "rents": {"unit": {"1br": 550, "2br": 750, "3br": 950}, "house": {"2br": 900, "3br": 1200, "4br": 1600}}},
        {"suburb": "Bankstown", "postcode": "2200", "lat": -33.9180, "lng": 151.0340, "rents": {"unit": {"1br": 400, "2br": 520, "3br": 620}, "house": {"2br": 500, "3br": 620, "4br": 750}}},
        {"suburb": "Bondi", "postcode": "2026", "lat": -33.8910, "lng": 151.2740, "rents": {"unit": {"1br": 600, "2br": 850, "3br": 1100}, "house": {"2br": 1000, "3br": 1400, "4br": 1800}}},
        {"suburb": "Bondi Beach", "postcode": "2026", "lat": -33.8920, "lng": 151.2750, "rents": {"unit": {"1br": 620, "2br": 880, "3br": 1150}, "house": {"2br": 1050, "3br": 1450, "4br": 1900}}},
        {"suburb": "Bondi Junction", "postcode": "2022", "lat": -33.8930, "lng": 151.2480, "rents": {"unit": {"1br": 560, "2br": 780, "3br": 1000}, "house": {"2br": 950, "3br": 1300, "4br": 1700}}},
        {"suburb": "Botany", "postcode": "2019", "lat": -33.9450, "lng": 151.1960, "rents": {"unit": {"1br": 480, "2br": 650, "3br": 820}, "house": {"2br": 700, "3br": 900, "4br": 1100}}},
        {"suburb": "Bronte", "postcode": "2024", "lat": -33.9030, "lng": 151.2640, "rents": {"unit": {"1br": 580, "2br": 820, "3br": 1050}, "house": {"2br": 1000, "3br": 1350, "4br": 1750}}},
        {"suburb": "Burwood", "postcode": "2134", "lat": -33.8770, "lng": 151.1030, "rents": {"unit": {"1br": 470, "2br": 600, "3br": 750}, "house": {"2br": 650, "3br": 830, "4br": 1000}}},
        {"suburb": "Camperdown", "postcode": "2050", "lat": -33.8880, "lng": 151.1770, "rents": {"unit": {"1br": 530, "2br": 720, "3br": 900}, "house": {"2br": 850, "3br": 1100, "4br": 1400}}},
        {"suburb": "Canterbury", "postcode": "2193", "lat": -33.9100, "lng": 151.1150, "rents": {"unit": {"1br": 420, "2br": 550, "3br": 680}, "house": {"2br": 580, "3br": 720, "4br": 880}}},
        {"suburb": "Castle Hill", "postcode": "2154", "lat": -33.7330, "lng": 150.9870, "rents": {"unit": {"1br": 450, "2br": 580, "3br": 720}, "house": {"2br": 600, "3br": 780, "4br": 950}}},
        {"suburb": "Chatswood", "postcode": "2067", "lat": -33.7960, "lng": 151.1810, "rents": {"unit": {"1br": 500, "2br": 680, "3br": 880}, "house": {"2br": 750, "3br": 1000, "4br": 1300}}},
        {"suburb": "Chippendale", "postcode": "2008", "lat": -33.8840, "lng": 151.1960, "rents": {"unit": {"1br": 560, "2br": 750, "3br": 950}, "house": {"2br": 900, "3br": 1150, "4br": 1500}}},
        {"suburb": "Coogee", "postcode": "2034", "lat": -33.9200, "lng": 151.2550, "rents": {"unit": {"1br": 550, "2br": 780, "3br": 1000}, "house": {"2br": 950, "3br": 1300, "4br": 1700}}},
        {"suburb": "Cronulla", "postcode": "2230", "lat": -34.0550, "lng": 151.1530, "rents": {"unit": {"1br": 480, "2br": 650, "3br": 820}, "house": {"2br": 700, "3br": 920, "4br": 1150}}},
        {"suburb": "Darlinghurst", "postcode": "2010", "lat": -33.8790, "lng": 151.2170, "rents": {"unit": {"1br": 550, "2br": 750, "3br": 950}, "house": {"2br": 900, "3br": 1200, "4br": 1550}}},
        {"suburb": "Dee Why", "postcode": "2099", "lat": -33.7510, "lng": 151.2860, "rents": {"unit": {"1br": 470, "2br": 630, "3br": 800}, "house": {"2br": 700, "3br": 900, "4br": 1100}}},
        {"suburb": "Dulwich Hill", "postcode": "2203", "lat": -33.9050, "lng": 151.1390, "rents": {"unit": {"1br": 450, "2br": 600, "3br": 750}, "house": {"2br": 700, "3br": 900, "4br": 1100}}},
        {"suburb": "Epping", "postcode": "2121", "lat": -33.7730, "lng": 151.0820, "rents": {"unit": {"1br": 430, "2br": 570, "3br": 700}, "house": {"2br": 600, "3br": 800, "4br": 1000}}},
        {"suburb": "Erskineville", "postcode": "2043", "lat": -33.9020, "lng": 151.1860, "rents": {"unit": {"1br": 520, "2br": 700, "3br": 880}, "house": {"2br": 850, "3br": 1100, "4br": 1400}}},
        {"suburb": "Glebe", "postcode": "2037", "lat": -33.8790, "lng": 151.1830, "rents": {"unit": {"1br": 520, "2br": 700, "3br": 880}, "house": {"2br": 850, "3br": 1100, "4br": 1400}}},
        {"suburb": "Homebush", "postcode": "2140", "lat": -33.8650, "lng": 151.0780, "rents": {"unit": {"1br": 430, "2br": 570, "3br": 700}, "house": {"2br": 600, "3br": 780, "4br": 950}}},
        {"suburb": "Hornsby", "postcode": "2077", "lat": -33.7020, "lng": 151.0990, "rents": {"unit": {"1br": 400, "2br": 530, "3br": 660}, "house": {"2br": 550, "3br": 720, "4br": 900}}},
        {"suburb": "Hurstville", "postcode": "2220", "lat": -33.9680, "lng": 151.0980, "rents": {"unit": {"1br": 420, "2br": 560, "3br": 700}, "house": {"2br": 600, "3br": 780, "4br": 950}}},
        {"suburb": "Kensington", "postcode": "2033", "lat": -33.9060, "lng": 151.2230, "rents": {"unit": {"1br": 510, "2br": 700, "3br": 880}, "house": {"2br": 850, "3br": 1100, "4br": 1400}}},
        {"suburb": "Kogarah", "postcode": "2217", "lat": -33.9630, "lng": 151.1330, "rents": {"unit": {"1br": 420, "2br": 560, "3br": 700}, "house": {"2br": 600, "3br": 780, "4br": 950}}},
        {"suburb": "Lane Cove", "postcode": "2066", "lat": -33.8150, "lng": 151.1650, "rents": {"unit": {"1br": 470, "2br": 640, "3br": 820}, "house": {"2br": 700, "3br": 950, "4br": 1250}}},
        {"suburb": "Leichhardt", "postcode": "2040", "lat": -33.8830, "lng": 151.1570, "rents": {"unit": {"1br": 480, "2br": 650, "3br": 830}, "house": {"2br": 800, "3br": 1050, "4br": 1350}}},
        {"suburb": "Liverpool", "postcode": "2170", "lat": -33.9210, "lng": 150.9230, "rents": {"unit": {"1br": 380, "2br": 480, "3br": 580}, "house": {"2br": 450, "3br": 560, "4br": 680}}},
        {"suburb": "Manly", "postcode": "2095", "lat": -33.7970, "lng": 151.2870, "rents": {"unit": {"1br": 550, "2br": 780, "3br": 1000}, "house": {"2br": 950, "3br": 1300, "4br": 1700}}},
        {"suburb": "Maroubra", "postcode": "2035", "lat": -33.9500, "lng": 151.2400, "rents": {"unit": {"1br": 500, "2br": 680, "3br": 870}, "house": {"2br": 800, "3br": 1050, "4br": 1350}}},
        {"suburb": "Marrickville", "postcode": "2204", "lat": -33.9110, "lng": 151.1550, "rents": {"unit": {"1br": 470, "2br": 620, "3br": 780}, "house": {"2br": 700, "3br": 900, "4br": 1100}}},
        {"suburb": "Mascot", "postcode": "2020", "lat": -33.9230, "lng": 151.1900, "rents": {"unit": {"1br": 530, "2br": 720, "3br": 900}, "house": {"2br": 800, "3br": 1050, "4br": 1300}}},
        {"suburb": "Mosman", "postcode": "2088", "lat": -33.8290, "lng": 151.2440, "rents": {"unit": {"1br": 520, "2br": 730, "3br": 950}, "house": {"2br": 950, "3br": 1350, "4br": 1800}}},
        {"suburb": "Neutral Bay", "postcode": "2089", "lat": -33.8350, "lng": 151.2170, "rents": {"unit": {"1br": 500, "2br": 680, "3br": 880}, "house": {"2br": 850, "3br": 1150, "4br": 1500}}},
        {"suburb": "Newtown", "postcode": "2042", "lat": -33.8980, "lng": 151.1790, "rents": {"unit": {"1br": 480, "2br": 650, "3br": 830}, "house": {"2br": 800, "3br": 1050, "4br": 1350}}},
        {"suburb": "North Sydney", "postcode": "2060", "lat": -33.8370, "lng": 151.2080, "rents": {"unit": {"1br": 530, "2br": 720, "3br": 920}, "house": {"2br": 900, "3br": 1200, "4br": 1600}}},
        {"suburb": "Paddington", "postcode": "2021", "lat": -33.8850, "lng": 151.2270, "rents": {"unit": {"1br": 530, "2br": 730, "3br": 950}, "house": {"2br": 950, "3br": 1300, "4br": 1700}}},
        {"suburb": "Parramatta", "postcode": "2150", "lat": -33.8170, "lng": 151.0030, "rents": {"unit": {"1br": 430, "2br": 560, "3br": 700}, "house": {"2br": 550, "3br": 700, "4br": 880}}},
        {"suburb": "Penrith", "postcode": "2750", "lat": -33.7550, "lng": 150.6870, "rents": {"unit": {"1br": 370, "2br": 470, "3br": 570}, "house": {"2br": 450, "3br": 550, "4br": 650}}},
        {"suburb": "Petersham", "postcode": "2049", "lat": -33.8940, "lng": 151.1530, "rents": {"unit": {"1br": 460, "2br": 620, "3br": 780}, "house": {"2br": 750, "3br": 980, "4br": 1250}}},
        {"suburb": "Pyrmont", "postcode": "2009", "lat": -33.8700, "lng": 151.1940, "rents": {"unit": {"1br": 580, "2br": 800, "3br": 1050}, "house": {"2br": 950, "3br": 1300, "4br": 1700}}},
        {"suburb": "Randwick", "postcode": "2031", "lat": -33.9140, "lng": 151.2410, "rents": {"unit": {"1br": 510, "2br": 700, "3br": 900}, "house": {"2br": 850, "3br": 1100, "4br": 1450}}},
        {"suburb": "Redfern", "postcode": "2016", "lat": -33.8930, "lng": 151.2040, "rents": {"unit": {"1br": 530, "2br": 720, "3br": 920}, "house": {"2br": 850, "3br": 1100, "4br": 1400}}},
        {"suburb": "Rhodes", "postcode": "2138", "lat": -33.8300, "lng": 151.0880, "rents": {"unit": {"1br": 500, "2br": 670, "3br": 850}, "house": {"2br": 700, "3br": 950, "4br": 1200}}},
        {"suburb": "Rockdale", "postcode": "2216", "lat": -33.9520, "lng": 151.1370, "rents": {"unit": {"1br": 420, "2br": 560, "3br": 700}, "house": {"2br": 600, "3br": 780, "4br": 950}}},
        {"suburb": "Rosebery", "postcode": "2018", "lat": -33.9170, "lng": 151.2050, "rents": {"unit": {"1br": 550, "2br": 750, "3br": 950}, "house": {"2br": 850, "3br": 1100, "4br": 1400}}},
        {"suburb": "Ryde", "postcode": "2112", "lat": -33.8140, "lng": 151.1060, "rents": {"unit": {"1br": 430, "2br": 570, "3br": 710}, "house": {"2br": 600, "3br": 800, "4br": 1000}}},
        {"suburb": "St Leonards", "postcode": "2065", "lat": -33.8230, "lng": 151.1940, "rents": {"unit": {"1br": 510, "2br": 690, "3br": 880}, "house": {"2br": 800, "3br": 1050, "4br": 1350}}},
        {"suburb": "Strathfield", "postcode": "2135", "lat": -33.8800, "lng": 151.0830, "rents": {"unit": {"1br": 420, "2br": 560, "3br": 700}, "house": {"2br": 600, "3br": 800, "4br": 1000}}},
        {"suburb": "Summer Hill", "postcode": "2130", "lat": -33.8920, "lng": 151.1390, "rents": {"unit": {"1br": 450, "2br": 600, "3br": 760}, "house": {"2br": 700, "3br": 920, "4br": 1150}}},
        {"suburb": "Surry Hills", "postcode": "2010", "lat": -33.8860, "lng": 151.2100, "rents": {"unit": {"1br": 560, "2br": 760, "3br": 980}, "house": {"2br": 950, "3br": 1250, "4br": 1600}}},
        {"suburb": "Sydney CBD", "postcode": "2000", "lat": -33.8688, "lng": 151.2093, "rents": {"unit": {"1br": 620, "2br": 900, "3br": 1200}, "house": {"2br": 1100, "3br": 1500, "4br": 2000}}},
        {"suburb": "Ultimo", "postcode": "2007", "lat": -33.8780, "lng": 151.1980, "rents": {"unit": {"1br": 560, "2br": 770, "3br": 980}, "house": {"2br": 900, "3br": 1200, "4br": 1550}}},
        {"suburb": "Wahroonga", "postcode": "2076", "lat": -33.7180, "lng": 151.1170, "rents": {"unit": {"1br": 400, "2br": 530, "3br": 670}, "house": {"2br": 600, "3br": 800, "4br": 1050}}},
        {"suburb": "Waterloo", "postcode": "2017", "lat": -33.9010, "lng": 151.2080, "rents": {"unit": {"1br": 550, "2br": 750, "3br": 950}, "house": {"2br": 850, "3br": 1100, "4br": 1400}}},
        {"suburb": "Waverley", "postcode": "2024", "lat": -33.8980, "lng": 151.2530, "rents": {"unit": {"1br": 550, "2br": 770, "3br": 990}, "house": {"2br": 950, "3br": 1300, "4br": 1700}}},
        {"suburb": "Wollstonecraft", "postcode": "2065", "lat": -33.8310, "lng": 151.1940, "rents": {"unit": {"1br": 480, "2br": 650, "3br": 840}, "house": {"2br": 800, "3br": 1050, "4br": 1350}}},
        {"suburb": "Woollahra", "postcode": "2025", "lat": -33.8870, "lng": 151.2410, "rents": {"unit": {"1br": 540, "2br": 750, "3br": 970}, "house": {"2br": 1000, "3br": 1400, "4br": 1850}}},
        {"suburb": "Zetland", "postcode": "2017", "lat": -33.9060, "lng": 151.2100, "rents": {"unit": {"1br": 560, "2br": 760, "3br": 960}, "house": {"2br": 850, "3br": 1100, "4br": 1400}}},
        {"suburb": "Blacktown", "postcode": "2148", "lat": -33.7700, "lng": 150.9060, "rents": {"unit": {"1br": 370, "2br": 470, "3br": 570}, "house": {"2br": 430, "3br": 530, "4br": 640}}},
        {"suburb": "Campbelltown", "postcode": "2560", "lat": -34.0650, "lng": 150.8140, "rents": {"unit": {"1br": 350, "2br": 440, "3br": 530}, "house": {"2br": 400, "3br": 500, "4br": 600}}},
        {"suburb": "Miranda", "postcode": "2228", "lat": -34.0340, "lng": 151.1030, "rents": {"unit": {"1br": 430, "2br": 570, "3br": 710}, "house": {"2br": 600, "3br": 780, "4br": 950}}},
        {"suburb": "Sutherland", "postcode": "2232", "lat": -34.0310, "lng": 151.0580, "rents": {"unit": {"1br": 420, "2br": 550, "3br": 680}, "house": {"2br": 580, "3br": 750, "4br": 920}}},
        {"suburb": "Brookvale", "postcode": "2100", "lat": -33.7670, "lng": 151.2720, "rents": {"unit": {"1br": 470, "2br": 630, "3br": 800}, "house": {"2br": 700, "3br": 920, "4br": 1150}}},
        {"suburb": "Freshwater", "postcode": "2096", "lat": -33.7780, "lng": 151.2880, "rents": {"unit": {"1br": 500, "2br": 680, "3br": 870}, "house": {"2br": 800, "3br": 1050, "4br": 1350}}},
        {"suburb": "Narrabeen", "postcode": "2101", "lat": -33.7130, "lng": 151.2960, "rents": {"unit": {"1br": 460, "2br": 610, "3br": 770}, "house": {"2br": 680, "3br": 880, "4br": 1100}}},
        {"suburb": "Moorebank", "postcode": "2170", "lat": -33.9430, "lng": 150.9550, "rents": {"unit": {"1br": 370, "2br": 470, "3br": 570}, "house": {"2br": 450, "3br": 560, "4br": 680}}},
        {"suburb": "Wentworthville", "postcode": "2145", "lat": -33.8070, "lng": 150.9710, "rents": {"unit": {"1br": 380, "2br": 490, "3br": 600}, "house": {"2br": 500, "3br": 630, "4br": 770}}},
        {"suburb": "Eastwood", "postcode": "2122", "lat": -33.7910, "lng": 151.0810, "rents": {"unit": {"1br": 410, "2br": 540, "3br": 670}, "house": {"2br": 580, "3br": 760, "4br": 950}}},
        {"suburb": "Meadowbank", "postcode": "2114", "lat": -33.8170, "lng": 151.0900, "rents": {"unit": {"1br": 450, "2br": 600, "3br": 750}, "house": {"2br": 650, "3br": 850, "4br": 1050}}},
        {"suburb": "Concord", "postcode": "2137", "lat": -33.8590, "lng": 151.1040, "rents": {"unit": {"1br": 450, "2br": 600, "3br": 760}, "house": {"2br": 700, "3br": 920, "4br": 1150}}},
        {"suburb": "Five Dock", "postcode": "2046", "lat": -33.8690, "lng": 151.1290, "rents": {"unit": {"1br": 460, "2br": 620, "3br": 780}, "house": {"2br": 750, "3br": 980, "4br": 1250}}},
        {"suburb": "Sans Souci", "postcode": "2219", "lat": -33.9870, "lng": 151.1330, "rents": {"unit": {"1br": 420, "2br": 560, "3br": 700}, "house": {"2br": 620, "3br": 800, "4br": 1000}}},
        {"suburb": "Caringbah", "postcode": "2229", "lat": -34.0430, "lng": 151.1220, "rents": {"unit": {"1br": 430, "2br": 570, "3br": 710}, "house": {"2br": 620, "3br": 800, "4br": 1000}}},
        {"suburb": "Arncliffe", "postcode": "2205", "lat": -33.9370, "lng": 151.1470, "rents": {"unit": {"1br": 420, "2br": 560, "3br": 700}, "house": {"2br": 600, "3br": 780, "4br": 950}}},
        {"suburb": "Lakemba", "postcode": "2195", "lat": -33.9190, "lng": 151.0750, "rents": {"unit": {"1br": 370, "2br": 470, "3br": 570}, "house": {"2br": 480, "3br": 600, "4br": 730}}},
        {"suburb": "Punchbowl", "postcode": "2196", "lat": -33.9290, "lng": 151.0530, "rents": {"unit": {"1br": 370, "2br": 470, "3br": 570}, "house": {"2br": 480, "3br": 590, "4br": 720}}},
        {"suburb": "Auburn", "postcode": "2144", "lat": -33.8490, "lng": 151.0330, "rents": {"unit": {"1br": 380, "2br": 490, "3br": 600}, "house": {"2br": 500, "3br": 620, "4br": 760}}},
        {"suburb": "Lidcombe", "postcode": "2141", "lat": -33.8640, "lng": 151.0470, "rents": {"unit": {"1br": 400, "2br": 520, "3br": 640}, "house": {"2br": 530, "3br": 670, "4br": 820}}},
        {"suburb": "Granville", "postcode": "2142", "lat": -33.8330, "lng": 151.0120, "rents": {"unit": {"1br": 370, "2br": 470, "3br": 570}, "house": {"2br": 470, "3br": 580, "4br": 710}}},
        {"suburb": "Merrylands", "postcode": "2160", "lat": -33.8340, "lng": 150.9930, "rents": {"unit": {"1br": 380, "2br": 490, "3br": 600}, "house": {"2br": 500, "3br": 620, "4br": 760}}},
        {"suburb": "Fairfield", "postcode": "2165", "lat": -33.8720, "lng": 150.9560, "rents": {"unit": {"1br": 350, "2br": 440, "3br": 530}, "house": {"2br": 430, "3br": 530, "4br": 640}}},
        {"suburb": "Cabramatta", "postcode": "2166", "lat": -33.8940, "lng": 150.9380, "rents": {"unit": {"1br": 350, "2br": 440, "3br": 530}, "house": {"2br": 420, "3br": 520, "4br": 630}}},
        {"suburb": "Mount Druitt", "postcode": "2770", "lat": -33.7670, "lng": 150.8190, "rents": {"unit": {"1br": 340, "2br": 430, "3br": 520}, "house": {"2br": 400, "3br": 490, "4br": 590}}},
        {"suburb": "Kellyville", "postcode": "2155", "lat": -33.7080, "lng": 150.9530, "rents": {"unit": {"1br": 430, "2br": 560, "3br": 700}, "house": {"2br": 580, "3br": 750, "4br": 920}}},
        {"suburb": "Bella Vista", "postcode": "2153", "lat": -33.7390, "lng": 150.9510, "rents": {"unit": {"1br": 440, "2br": 570, "3br": 710}, "house": {"2br": 590, "3br": 770, "4br": 950}}},
        {"suburb": "Norwest", "postcode": "2153", "lat": -33.7320, "lng": 150.9630, "rents": {"unit": {"1br": 460, "2br": 600, "3br": 750}, "house": {"2br": 620, "3br": 800, "4br": 980}}},
        {"suburb": "Macquarie Park", "postcode": "2113", "lat": -33.7770, "lng": 151.1280, "rents": {"unit": {"1br": 460, "2br": 610, "3br": 770}, "house": {"2br": 650, "3br": 850, "4br": 1050}}},
        {"suburb": "Gladesville", "postcode": "2111", "lat": -33.8310, "lng": 151.1280, "rents": {"unit": {"1br": 430, "2br": 580, "3br": 730}, "house": {"2br": 650, "3br": 870, "4br": 1100}}},
        {"suburb": "Drummoyne", "postcode": "2047", "lat": -33.8540, "lng": 151.1540, "rents": {"unit": {"1br": 470, "2br": 640, "3br": 810}, "house": {"2br": 800, "3br": 1050, "4br": 1350}}},
        {"suburb": "Rozelle", "postcode": "2039", "lat": -33.8620, "lng": 151.1700, "rents": {"unit": {"1br": 500, "2br": 680, "3br": 870}, "house": {"2br": 850, "3br": 1100, "4br": 1450}}},
        {"suburb": "Annandale", "postcode": "2038", "lat": -33.8830, "lng": 151.1700, "rents": {"unit": {"1br": 490, "2br": 660, "3br": 840}, "house": {"2br": 800, "3br": 1050, "4br": 1350}}},
        {"suburb": "Stanmore", "postcode": "2048", "lat": -33.8950, "lng": 151.1650, "rents": {"unit": {"1br": 460, "2br": 620, "3br": 780}, "house": {"2br": 750, "3br": 980, "4br": 1250}}},
        {"suburb": "Enmore", "postcode": "2042", "lat": -33.9010, "lng": 151.1740, "rents": {"unit": {"1br": 470, "2br": 630, "3br": 800}, "house": {"2br": 780, "3br": 1020, "4br": 1300}}},
        {"suburb": "St Peters", "postcode": "2044", "lat": -33.9130, "lng": 151.1790, "rents": {"unit": {"1br": 480, "2br": 640, "3br": 810}, "house": {"2br": 780, "3br": 1020, "4br": 1300}}},
        {"suburb": "Tempe", "postcode": "2044", "lat": -33.9210, "lng": 151.1620, "rents": {"unit": {"1br": 450, "2br": 600, "3br": 760}, "house": {"2br": 700, "3br": 900, "4br": 1100}}},
        {"suburb": "Wolli Creek", "postcode": "2205", "lat": -33.9310, "lng": 151.1510, "rents": {"unit": {"1br": 460, "2br": 620, "3br": 780}, "house": {"2br": 650, "3br": 850, "4br": 1050}}},
    ],
}


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------


def _get_suburbs() -> list[dict]:
    """Return the list of suburb dicts from embedded data."""
    return RENTAL_DATA["suburbs"]


def _filter_rents(rents: dict, prop_type: str, bedrooms: str | None) -> dict:
    """Filter rents dict by property type and bedrooms."""
    if prop_type == "all":
        filtered = {}
        for ptype in ("unit", "house"):
            if ptype in rents:
                if bedrooms:
                    key = f"{bedrooms}br"
                    if key in rents[ptype]:
                        filtered[ptype] = {key: rents[ptype][key]}
                else:
                    filtered[ptype] = rents[ptype]
        return filtered
    else:
        if prop_type not in rents:
            return {}
        if bedrooms:
            key = f"{bedrooms}br"
            if key in rents[prop_type]:
                return {prop_type: {key: rents[prop_type][key]}}
            return {}
        return {prop_type: rents[prop_type]}


def _get_rent_value(rents: dict, prop_type: str, bedrooms: str) -> int | None:
    """Get a specific rent value. Returns None if not found."""
    key = f"{bedrooms}br"
    if prop_type in rents and key in rents[prop_type]:
        return rents[prop_type][key]
    return None


def _match_suburb(query: str, suburbs: list[dict]) -> list[dict]:
    """Fuzzy match a suburb name against the list."""
    scored = []
    for s in suburbs:
        score = _similarity_score(query, s["suburb"])
        if score > 0:
            scored.append((score, s))

    scored.sort(key=lambda x: (-x[0], len(x[1]["suburb"])))

    if not scored:
        return []

    best_score = scored[0][0]
    # Return matches within 0.05 of best score
    return [s for sc, s in scored if sc >= best_score - 0.05][:5]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check median rental prices for Sydney suburbs")
    parser.add_argument("--suburb", "-s", help="Suburb name to search for (fuzzy match)")
    parser.add_argument("--postcode", "-p", help="Search by postcode")
    parser.add_argument("--bedrooms", "-b", choices=["1", "2", "3", "4"], help="Filter by bedroom count")
    parser.add_argument("--type", "-t", dest="prop_type", choices=["house", "unit", "all"], default="all", help="Property type (default: all)")
    parser.add_argument("--budget", type=int, help="Max weekly rent — find suburbs within budget")
    parser.add_argument("--location", "-l", help="Suburb or city name for nearby search")
    parser.add_argument("--lat", type=float, help="Latitude for nearby search")
    parser.add_argument("--lng", type=float, help="Longitude for nearby search")
    parser.add_argument("--radius", "-r", type=float, default=5.0, help="Search radius in km (default: 5)")
    parser.add_argument("--no-cache", action="store_true", help="Skip cache")
    return parser.parse_args()


async def main() -> None:
    import httpx

    args = parse_args()

    # Clear cache if requested
    if args.no_cache:
        for f in CACHE_DIR.glob("*.json"):
            f.unlink()

    suburbs = _get_suburbs()

    # --suburb mode: search by suburb name
    if args.suburb:
        matches = _match_suburb(args.suburb, suburbs)

        if not matches:
            print(json.dumps({
                "error": f"No suburbs found matching '{args.suburb}'.",
                "query": {"suburb": args.suburb, "type": args.prop_type, "bedrooms": args.bedrooms},
            }))
            sys.exit(1)

        top = matches[0]
        rents = _filter_rents(top["rents"], args.prop_type, args.bedrooms)

        alternatives = []
        for m in matches[1:]:
            alt_rents = _filter_rents(m["rents"], args.prop_type, args.bedrooms)
            if alt_rents:
                alternatives.append({
                    "suburb": m["suburb"],
                    "postcode": m["postcode"],
                    "rents": alt_rents,
                })

        result = {
            "query": {"suburb": args.suburb, "type": args.prop_type, "bedrooms": args.bedrooms},
            "results": {
                "suburb": top["suburb"],
                "postcode": top["postcode"],
                "rents": rents,
            },
            "data_quarter": RENTAL_DATA["data_quarter"],
            "source": RENTAL_DATA["data_source"],
            "note": "Median weekly rents in AUD. Actual rents may vary.",
        }

        if alternatives:
            result["alternatives"] = alternatives

        print(json.dumps(result, indent=2))
        return

    # --postcode mode: search by postcode
    if args.postcode:
        postcode_matches = [s for s in suburbs if s["postcode"] == args.postcode]

        if not postcode_matches:
            print(json.dumps({
                "error": f"No suburbs found with postcode '{args.postcode}'.",
                "query": {"postcode": args.postcode, "type": args.prop_type, "bedrooms": args.bedrooms},
            }))
            sys.exit(1)

        results_list = []
        for m in postcode_matches:
            rents = _filter_rents(m["rents"], args.prop_type, args.bedrooms)
            if rents:
                results_list.append({
                    "suburb": m["suburb"],
                    "postcode": m["postcode"],
                    "rents": rents,
                })

        result = {
            "query": {"postcode": args.postcode, "type": args.prop_type, "bedrooms": args.bedrooms},
            "results": {
                "count": len(results_list),
                "suburbs": results_list,
            },
            "data_quarter": RENTAL_DATA["data_quarter"],
            "source": RENTAL_DATA["data_source"],
            "note": "Median weekly rents in AUD. Actual rents may vary.",
        }

        print(json.dumps(result, indent=2))
        return

    # --budget mode: find suburbs within budget
    if args.budget is not None:
        budget = args.budget
        prop_type = args.prop_type
        bedrooms = args.bedrooms or "2"
        bed_key = f"{bedrooms}br"

        affordable = []
        for s in suburbs:
            # Check each applicable property type
            types_to_check = ["unit", "house"] if prop_type == "all" else [prop_type]
            for ptype in types_to_check:
                if ptype in s["rents"] and bed_key in s["rents"][ptype]:
                    rent = s["rents"][ptype][bed_key]
                    if rent <= budget:
                        affordable.append({
                            "suburb": s["suburb"],
                            "postcode": s["postcode"],
                            "median_rent": rent,
                            "type": ptype,
                            "bedrooms": bed_key,
                            "lat": s["lat"],
                            "lng": s["lng"],
                        })

        # If location provided, sort by distance; otherwise alphabetically
        ref_location = None
        if args.location or (args.lat is not None and args.lng is not None):
            async with httpx.AsyncClient() as client:
                ref_location = await location_from_args(args, client)

        if ref_location and ref_location.lat != 0:
            for entry in affordable:
                entry["distance_km"] = round(
                    haversine_km(ref_location.lat, ref_location.lng, entry["lat"], entry["lng"]), 1
                )
            affordable.sort(key=lambda x: x["distance_km"])
        else:
            affordable.sort(key=lambda x: (x["median_rent"], x["suburb"]))

        # Clean up lat/lng from output
        for entry in affordable:
            entry.pop("lat", None)
            entry.pop("lng", None)

        result = {
            "query": {"budget": budget, "type": prop_type if prop_type != "all" else "all", "bedrooms": bedrooms},
            "results": {
                "count": len(affordable),
                "suburbs": affordable,
            },
            "data_quarter": RENTAL_DATA["data_quarter"],
            "source": RENTAL_DATA["data_source"],
            "note": "Median weekly rents in AUD. Actual rents may vary.",
        }

        print(json.dumps(result, indent=2))
        return

    # --location / --lat / --lng mode: nearby suburbs
    if args.location or (args.lat is not None and args.lng is not None):
        async with httpx.AsyncClient() as client:
            location = await location_from_args(args, client)

        if not location or location.lat == 0:
            print(json.dumps({"error": "Could not determine location. Use --location or --lat/--lng."}))
            sys.exit(1)

        nearby = []
        for s in suburbs:
            dist = haversine_km(location.lat, location.lng, s["lat"], s["lng"])
            if dist <= args.radius:
                rents = _filter_rents(s["rents"], args.prop_type, args.bedrooms)
                if rents:
                    nearby.append({
                        "suburb": s["suburb"],
                        "postcode": s["postcode"],
                        "distance_km": round(dist, 1),
                        "rents": rents,
                    })

        nearby.sort(key=lambda x: x["distance_km"])
        nearby = nearby[:15]

        location_confidence = "high"
        if location.method in ("ip-api.com", "ip-fallback"):
            location_confidence = "low"

        result = {
            "location": {
                "city": location.city,
                "state": location.state,
                "postcode": location.postcode,
                "lat": location.lat,
                "lng": location.lng,
                "method": location.method,
                "confidence": location_confidence,
            },
            "query": {"radius_km": args.radius, "type": args.prop_type, "bedrooms": args.bedrooms, "mode": "nearby"},
            "results": {
                "count": len(nearby),
                "suburbs": nearby,
            },
            "data_quarter": RENTAL_DATA["data_quarter"],
            "source": RENTAL_DATA["data_source"],
            "note": "Median weekly rents in AUD. Actual rents may vary.",
        }

        if location_confidence == "low":
            result["location"]["note"] = (
                "Location was detected via IP address only (city-level accuracy). "
                "The user may not actually be in this area. Ask them to confirm their "
                "suburb or postcode for accurate results."
            )

        print(json.dumps(result, indent=2))
        return

    # Default: top 10 most affordable suburbs for 2br units
    affordable = []
    for s in suburbs:
        if "unit" in s["rents"] and "2br" in s["rents"]["unit"]:
            affordable.append({
                "suburb": s["suburb"],
                "postcode": s["postcode"],
                "median_rent": s["rents"]["unit"]["2br"],
                "type": "unit",
                "bedrooms": "2br",
            })

    affordable.sort(key=lambda x: x["median_rent"])
    affordable = affordable[:10]

    result = {
        "query": {"mode": "default_affordable", "type": "unit", "bedrooms": "2"},
        "results": {
            "count": len(affordable),
            "suburbs": affordable,
        },
        "data_quarter": RENTAL_DATA["data_quarter"],
        "source": RENTAL_DATA["data_source"],
        "note": "Top 10 most affordable suburbs for 2-bedroom units. Median weekly rents in AUD.",
    }

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
