#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "httpx>=0.27.0",
# ]
# ///
"""
Speed Cameras NSW — find fixed speed cameras and red light cameras near you.

Zero-config: works immediately with no API keys.

Usage:
    uv run speed_cameras.py                              # cameras near you (auto-detect location)
    uv run speed_cameras.py --location "Homebush NSW"    # cameras near a suburb
    uv run speed_cameras.py --lat -33.87 --lng 151.21    # cameras near coordinates
    uv run speed_cameras.py --radius 10                  # wider search radius
    uv run speed_cameras.py --road "Pacific Highway"     # filter by road name
    uv run speed_cameras.py --type fixed_speed           # filter by camera type
"""

import argparse
import asyncio
import json
import math
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote_plus

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
# Embedded camera data — curated list of NSW fixed speed / red light cameras
# ---------------------------------------------------------------------------

CAMERAS: list[dict] = [
    # Motorways & tunnels
    {"type": "fixed_speed", "road": "M2 Hills Motorway", "suburb": "Baulkham Hills", "direction": "Eastbound", "lat": -33.7637, "lng": 151.0014},
    {"type": "fixed_speed", "road": "M2 Hills Motorway", "suburb": "Baulkham Hills", "direction": "Westbound", "lat": -33.7640, "lng": 151.0020},
    {"type": "fixed_speed", "road": "M5 East Motorway", "suburb": "Arncliffe", "direction": "Eastbound", "lat": -33.9350, "lng": 151.1570},
    {"type": "fixed_speed", "road": "M5 East Motorway", "suburb": "Arncliffe", "direction": "Westbound", "lat": -33.9355, "lng": 151.1565},
    {"type": "fixed_speed", "road": "M4 Motorway", "suburb": "Merrylands", "direction": "Eastbound", "lat": -33.8320, "lng": 150.9890},
    {"type": "fixed_speed", "road": "M4 Motorway", "suburb": "Merrylands", "direction": "Westbound", "lat": -33.8325, "lng": 150.9885},
    {"type": "fixed_speed", "road": "Eastern Distributor", "suburb": "Woolloomooloo", "direction": "Southbound", "lat": -33.8710, "lng": 151.2220},
    {"type": "fixed_speed", "road": "Eastern Distributor", "suburb": "Woolloomooloo", "direction": "Northbound", "lat": -33.8715, "lng": 151.2215},
    {"type": "fixed_speed", "road": "Harbour Tunnel", "suburb": "Sydney", "direction": "Northbound", "lat": -33.8580, "lng": 151.2110},
    {"type": "fixed_speed", "road": "Harbour Tunnel", "suburb": "Sydney", "direction": "Southbound", "lat": -33.8585, "lng": 151.2105},
    {"type": "fixed_speed", "road": "Lane Cove Tunnel", "suburb": "Lane Cove", "direction": "Eastbound", "lat": -33.8170, "lng": 151.1580},
    {"type": "fixed_speed", "road": "Lane Cove Tunnel", "suburb": "Lane Cove", "direction": "Westbound", "lat": -33.8175, "lng": 151.1575},
    {"type": "fixed_speed", "road": "NorthConnex", "suburb": "Wahroonga", "direction": "Northbound", "lat": -33.7200, "lng": 151.1180},
    {"type": "fixed_speed", "road": "NorthConnex", "suburb": "Wahroonga", "direction": "Southbound", "lat": -33.7205, "lng": 151.1175},
    {"type": "fixed_speed", "road": "WestConnex M8", "suburb": "Arncliffe", "direction": "Eastbound", "lat": -33.9370, "lng": 151.1540},
    {"type": "fixed_speed", "road": "WestConnex M8", "suburb": "Arncliffe", "direction": "Westbound", "lat": -33.9375, "lng": 151.1535},
    {"type": "fixed_speed", "road": "Cross City Tunnel", "suburb": "Sydney CBD", "direction": "Eastbound", "lat": -33.8750, "lng": 151.2090},
    {"type": "fixed_speed", "road": "Cross City Tunnel", "suburb": "Sydney CBD", "direction": "Westbound", "lat": -33.8755, "lng": 151.2085},
    {"type": "fixed_speed", "road": "M7 Motorway", "suburb": "Prestons", "direction": "Northbound", "lat": -33.9440, "lng": 150.8680},
    {"type": "fixed_speed", "road": "M7 Motorway", "suburb": "Prestons", "direction": "Southbound", "lat": -33.9445, "lng": 150.8675},
    {"type": "fixed_speed", "road": "M7 Motorway", "suburb": "Quakers Hill", "direction": "Northbound", "lat": -33.7340, "lng": 150.8830},
    {"type": "fixed_speed", "road": "M7 Motorway", "suburb": "Quakers Hill", "direction": "Southbound", "lat": -33.7345, "lng": 150.8825},
    # Pacific Highway corridor
    {"type": "fixed_speed", "road": "Pacific Highway", "suburb": "Wahroonga", "direction": "Northbound", "lat": -33.7180, "lng": 151.1170},
    {"type": "fixed_speed", "road": "Pacific Highway", "suburb": "Pymble", "direction": "Southbound", "lat": -33.7440, "lng": 151.1440},
    {"type": "fixed_speed", "road": "Pacific Highway", "suburb": "Chatswood", "direction": "Northbound", "lat": -33.7960, "lng": 151.1810},
    {"type": "fixed_speed", "road": "Pacific Highway", "suburb": "St Leonards", "direction": "Southbound", "lat": -33.8230, "lng": 151.1940},
    # Major arterials — north
    {"type": "fixed_speed", "road": "Epping Road", "suburb": "Lane Cove North", "direction": "Eastbound", "lat": -33.8050, "lng": 151.1470},
    {"type": "fixed_speed", "road": "Pennant Hills Road", "suburb": "Thornleigh", "direction": "Southbound", "lat": -33.7310, "lng": 151.0810},
    {"type": "fixed_speed", "road": "Mona Vale Road", "suburb": "St Ives", "direction": "Eastbound", "lat": -33.7280, "lng": 151.1690},
    {"type": "fixed_speed", "road": "Burns Bay Road", "suburb": "Lane Cove", "direction": "Westbound", "lat": -33.8190, "lng": 151.1530},
    {"type": "fixed_speed", "road": "Military Road", "suburb": "Neutral Bay", "direction": "Westbound", "lat": -33.8350, "lng": 151.2170},
    {"type": "fixed_speed", "road": "Warringah Road", "suburb": "Forestville", "direction": "Eastbound", "lat": -33.7620, "lng": 151.2080},
    {"type": "fixed_speed", "road": "Pittwater Road", "suburb": "Dee Why", "direction": "Northbound", "lat": -33.7510, "lng": 151.2860},
    # Major arterials — inner west / west
    {"type": "fixed_speed", "road": "Parramatta Road", "suburb": "Homebush", "direction": "Westbound", "lat": -33.8650, "lng": 151.0780},
    {"type": "fixed_speed", "road": "Victoria Road", "suburb": "Gladesville", "direction": "Northbound", "lat": -33.8370, "lng": 151.1280},
    {"type": "fixed_speed", "road": "Victoria Road", "suburb": "Ryde", "direction": "Southbound", "lat": -33.8190, "lng": 151.1060},
    {"type": "fixed_speed", "road": "Great Western Highway", "suburb": "Penrith", "direction": "Westbound", "lat": -33.7550, "lng": 150.6870},
    {"type": "fixed_speed", "road": "James Ruse Drive", "suburb": "Parramatta", "direction": "Northbound", "lat": -33.8130, "lng": 151.0120},
    {"type": "fixed_speed", "road": "Silverwater Road", "suburb": "Silverwater", "direction": "Southbound", "lat": -33.8380, "lng": 151.0430},
    {"type": "fixed_speed", "road": "Woodville Road", "suburb": "Merrylands", "direction": "Southbound", "lat": -33.8340, "lng": 150.9930},
    {"type": "fixed_speed", "road": "Old Windsor Road", "suburb": "Castle Hill", "direction": "Northbound", "lat": -33.7330, "lng": 150.9870},
    {"type": "fixed_speed", "road": "Windsor Road", "suburb": "Baulkham Hills", "direction": "Northbound", "lat": -33.7580, "lng": 150.9870},
    {"type": "fixed_speed", "road": "Cumberland Highway", "suburb": "South Wentworthville", "direction": "Southbound", "lat": -33.8160, "lng": 150.9640},
    {"type": "fixed_speed", "road": "Roberts Road", "suburb": "Greenacre", "direction": "Northbound", "lat": -33.8990, "lng": 151.0570},
    {"type": "fixed_speed", "road": "The Horsley Drive", "suburb": "Horsley Park", "direction": "Westbound", "lat": -33.8410, "lng": 150.8550},
    {"type": "fixed_speed", "road": "Elizabeth Drive", "suburb": "Cecil Park", "direction": "Westbound", "lat": -33.8780, "lng": 150.8370},
    # Major arterials — south
    {"type": "fixed_speed", "road": "Princes Highway", "suburb": "Kogarah", "direction": "Southbound", "lat": -33.9630, "lng": 151.1330},
    {"type": "fixed_speed", "road": "King Georges Road", "suburb": "Beverly Hills", "direction": "Southbound", "lat": -33.9520, "lng": 151.0820},
    {"type": "fixed_speed", "road": "Hume Highway", "suburb": "Liverpool", "direction": "Southbound", "lat": -33.9210, "lng": 150.9230},
    {"type": "fixed_speed", "road": "Canterbury Road", "suburb": "Canterbury", "direction": "Westbound", "lat": -33.9100, "lng": 151.1150},
    {"type": "fixed_speed", "road": "Botany Road", "suburb": "Mascot", "direction": "Southbound", "lat": -33.9230, "lng": 151.1900},
    {"type": "fixed_speed", "road": "General Holmes Drive", "suburb": "Mascot", "direction": "Southbound", "lat": -33.9350, "lng": 151.1870},
    {"type": "fixed_speed", "road": "Southern Cross Drive", "suburb": "Eastgardens", "direction": "Southbound", "lat": -33.9430, "lng": 151.2230},
    {"type": "fixed_speed", "road": "Forest Road", "suburb": "Hurstville", "direction": "Southbound", "lat": -33.9680, "lng": 151.0980},
    {"type": "fixed_speed", "road": "Henry Lawson Drive", "suburb": "Padstow", "direction": "Southbound", "lat": -33.9550, "lng": 151.0420},
    {"type": "fixed_speed", "road": "Camden Valley Way", "suburb": "Leppington", "direction": "Southbound", "lat": -33.9590, "lng": 150.8150},
    {"type": "fixed_speed", "road": "Narellan Road", "suburb": "Narellan", "direction": "Westbound", "lat": -34.0440, "lng": 150.7350},
    # Eastern suburbs
    {"type": "fixed_speed", "road": "Syd Einfeld Drive", "suburb": "Bondi Junction", "direction": "Eastbound", "lat": -33.8930, "lng": 151.2480},
    # Red light cameras
    {"type": "red_light", "road": "Anzac Bridge approach", "suburb": "Pyrmont", "direction": "Westbound", "lat": -33.8700, "lng": 151.1870},
    {"type": "red_light", "road": "Broadway/City Road", "suburb": "Chippendale", "direction": "Southbound", "lat": -33.8840, "lng": 151.1960},
    {"type": "red_light", "road": "Cleveland St/Crown St", "suburb": "Surry Hills", "direction": "Eastbound", "lat": -33.8860, "lng": 151.2100},
    {"type": "red_light", "road": "George St/Bridge St", "suburb": "Sydney CBD", "direction": "Northbound", "lat": -33.8630, "lng": 151.2070},
    {"type": "red_light", "road": "Oxford St/Crown St", "suburb": "Darlinghurst", "direction": "Eastbound", "lat": -33.8790, "lng": 151.2130},
    {"type": "red_light", "road": "King St", "suburb": "Newtown", "direction": "Southbound", "lat": -33.8960, "lng": 151.1780},
    {"type": "red_light", "road": "Stoney Creek Road", "suburb": "Beverly Hills", "direction": "Southbound", "lat": -33.9490, "lng": 151.0830},
    {"type": "red_light", "road": "Lyons Road", "suburb": "Drummoyne", "direction": "Northbound", "lat": -33.8540, "lng": 151.1540},
    # Combined fixed speed + red light
    {"type": "fixed_speed_and_red_light", "road": "Parramatta Road/Concord Road", "suburb": "Concord", "direction": "Westbound", "lat": -33.8610, "lng": 151.1040},
    {"type": "fixed_speed_and_red_light", "road": "Princes Highway/Railway Parade", "suburb": "Kogarah", "direction": "Southbound", "lat": -33.9640, "lng": 151.1320},
    {"type": "fixed_speed_and_red_light", "road": "Hume Highway/Woodville Road", "suburb": "Villawood", "direction": "Southbound", "lat": -33.8870, "lng": 151.0230},
    {"type": "fixed_speed_and_red_light", "road": "King Georges Road/Stoney Creek Road", "suburb": "Beverly Hills", "direction": "Southbound", "lat": -33.9510, "lng": 151.0825},
    {"type": "fixed_speed_and_red_light", "road": "Victoria Road/Lyons Road", "suburb": "Drummoyne", "direction": "Northbound", "lat": -33.8530, "lng": 151.1550},
]


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------

CACHE_DIR = Path.home() / ".config" / "speed-cameras"
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

NOMINATIM_HEADERS = {"User-Agent": "speed-cameras-cli/1.0"}

LOCATION_HTML = """<!DOCTYPE html>
<html><head><title>Speed Cameras - Location</title>
<style>
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
         display: flex; justify-content: center; align-items: center; height: 100vh;
         margin: 0; background: #f5f5f5; }
  .card { background: white; border-radius: 12px; padding: 40px; text-align: center;
          box-shadow: 0 2px 10px rgba(0,0,0,0.1); max-width: 400px; }
  h2 { margin: 0 0 8px; }
  p { color: #666; margin: 0 0 24px; }
  .status { font-size: 18px; color: #333; }
  .ok { color: #22863a; }
  .err { color: #cb2431; }
</style></head>
<body><div class="card">
  <h2>Speed Cameras</h2>
  <p>Allow location access to find speed cameras near you.</p>
  <div class="status" id="s">Requesting location...</div>
</div>
<script>
if (!navigator.geolocation) {
  document.getElementById('s').innerHTML = '<span class="err">Geolocation not supported</span>';
} else {
  navigator.geolocation.getCurrentPosition(
    function(pos) {
      document.getElementById('s').innerHTML = '<span class="ok">Location found! You can close this tab.</span>';
      fetch('/callback', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({lat: pos.coords.latitude, lng: pos.coords.longitude,
                              accuracy: pos.coords.accuracy})
      });
    },
    function(err) {
      document.getElementById('s').innerHTML = '<span class="err">Location denied: ' + err.message + '</span>';
      fetch('/callback', {method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({error: err.message})});
    },
    {enableHighAccuracy: true, timeout: 15000, maximumAge: 60000}
  );
}
</script></body></html>"""


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


async def _geolocate_browser() -> Location | None:
    """Browser-based geolocation — opens localhost page that requests navigator.geolocation."""
    import http.server
    import threading
    import webbrowser

    result_holder: dict = {}
    server_ready = threading.Event()
    got_result = threading.Event()

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(LOCATION_HTML.encode())

        def do_POST(self):
            if self.path == "/callback":
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length)
                try:
                    result_holder.update(json.loads(body))
                except json.JSONDecodeError:
                    pass
                self.send_response(200)
                self.send_header("Content-Type", "text/plain")
                self.end_headers()
                self.wfile.write(b"ok")
                got_result.set()

        def log_message(self, format, *args):
            pass  # Suppress server logs

    # Find a free port
    import socket

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()

    server = http.server.HTTPServer(("127.0.0.1", port), Handler)
    server.timeout = 1  # 1-second poll so we can check got_result

    def run_server():
        server_ready.set()
        deadline = time.time() + 30
        while not got_result.is_set() and time.time() < deadline:
            server.handle_request()

    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()
    server_ready.wait()

    url = f"http://127.0.0.1:{port}"
    print("Opening browser for location access...", file=sys.stderr)
    webbrowser.open(url)

    # Wait for the callback (timeout 30 seconds)
    got_result.wait(timeout=30)
    server.server_close()

    if "error" in result_holder or "lat" not in result_holder:
        return None

    return Location(
        lat=result_holder["lat"],
        lng=result_holder["lng"],
        city="",
        state="",
        postcode="",
        country="",
        method=f"browser (accuracy: {result_holder.get('accuracy', '?')}m)",
    )


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


def _get_cached_location() -> Location | None:
    """Read cached location from disk. Expires after 24 hours."""
    path = CACHE_DIR / "location.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
        # Expire after 24 hours
        if time.time() - data.get("_cached_at", 0) > 86400:
            return None
        return Location(**data["location"])
    except (json.JSONDecodeError, KeyError, TypeError):
        return None


def _cache_location(loc: Location) -> None:
    """Cache location to disk for 24 hours."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = CACHE_DIR / "location.json"
    path.write_text(json.dumps({
        "_cached_at": time.time(),
        "location": {
            "lat": loc.lat, "lng": loc.lng, "city": loc.city,
            "state": loc.state, "postcode": loc.postcode,
            "country": loc.country, "method": loc.method,
        },
    }))


async def geolocate(client: "httpx.AsyncClient") -> Location | None:
    """Try the best available geolocation method.

    Chain:
      1. Cached location (from previous browser consent)
      2. Browser consent flow (opens browser, ~15-50ft accuracy, all OSes)
      3. IP geolocation (fallback, city-level accuracy)
    """
    # 1. Check for cached location (from a previous browser consent)
    cached_loc = _get_cached_location()
    if cached_loc:
        return cached_loc

    # 2. Try browser-based geolocation (works on all OSes, most accurate)
    browser_loc = await _geolocate_browser()
    if browser_loc:
        # Enrich with city/state/postcode via reverse geocoding (accurate to suburb)
        rev = await _geocode_reverse(client, browser_loc.lat, browser_loc.lng)
        if rev:
            browser_loc.city = rev["city"]
            browser_loc.state = rev["state"]
            browser_loc.postcode = rev["postcode"]
            browser_loc.country = rev["country"]
        else:
            # Fall back to IP enrichment if Nominatim fails
            ip_loc = await _geolocate_ip(client)
            if ip_loc:
                browser_loc.state = ip_loc.state
                browser_loc.postcode = ip_loc.postcode
                browser_loc.city = ip_loc.city
                browser_loc.country = ip_loc.country
        # Cache for future runs so the browser doesn't open every time
        _cache_location(browser_loc)
        return browser_loc

    # 3. Fallback to IP geolocation (works everywhere, city-level accuracy)
    return await _geolocate_ip(client)


def location_from_args(
    args: argparse.Namespace, client: "httpx.AsyncClient"
) -> "asyncio.coroutine":
    """Build a Location from CLI args, or auto-detect."""

    async def _resolve() -> Location | None:
        if args.lat is not None and args.lng is not None:
            # Reverse geocode to get accurate suburb/state/postcode
            rev = await _geocode_reverse(client, args.lat, args.lng)
            if rev:
                return Location(
                    lat=args.lat,
                    lng=args.lng,
                    city=args.location or rev["city"],
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
                city=args.location or (ip_loc.city if ip_loc else ""),
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
            # Can't geolocate at all — return a stub
            return Location(
                lat=0,
                lng=0,
                city=args.location or "",
                state="",
                postcode="",
                country="AU",
                method="manual",
            )
        # Auto-detect
        return await geolocate(client)

    return _resolve()


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
# Fuzzy road name matching
# ---------------------------------------------------------------------------


def _normalize(s: str) -> str:
    """Lowercase and strip extra whitespace."""
    return " ".join(s.lower().split())


def _road_matches(query: str, road: str) -> bool:
    """Check if a road name fuzzy-matches the query."""
    q = _normalize(query)
    r = _normalize(road)

    # Exact match
    if q == r:
        return True

    # Substring match (either direction)
    if q in r or r in q:
        return True

    # Word overlap — match if all query words appear in road name
    q_words = set(q.split())
    r_words = set(r.split())
    if q_words and q_words.issubset(r_words):
        return True

    # Prefix match on individual words
    for qw in q_words:
        for rw in r_words:
            if rw.startswith(qw) and len(qw) >= 3:
                return True

    return False


# ---------------------------------------------------------------------------
# Map URLs
# ---------------------------------------------------------------------------


def _google_maps_url(lat: float, lng: float, label: str) -> str:
    return f"https://www.google.com/maps/search/?api=1&query={lat},{lng}"


def _apple_maps_url(lat: float, lng: float, label: str) -> str:
    return f"https://maps.apple.com/?q={quote_plus(label)}&ll={lat},{lng}"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Find speed cameras and red light cameras near you in NSW"
    )
    parser.add_argument("--location", "-l", help="Suburb or city name (e.g., 'Homebush NSW')")
    parser.add_argument("--lat", type=float, help="Latitude")
    parser.add_argument("--lng", type=float, help="Longitude")
    parser.add_argument(
        "--radius", "-r", type=float, default=5.0, help="Search radius in km (default: 5)"
    )
    parser.add_argument(
        "--road", help="Filter by road name (fuzzy match)"
    )
    parser.add_argument(
        "--type", "-t", dest="camera_type", default="all",
        choices=["fixed_speed", "red_light", "fixed_speed_and_red_light", "all"],
        help="Camera type filter (default: all)"
    )
    parser.add_argument("--no-cache", action="store_true", help="Skip location cache")
    return parser.parse_args()


async def main() -> None:
    import httpx

    args = parse_args()

    # Handle --no-cache: clear location cache
    if args.no_cache:
        loc_cache = CACHE_DIR / "location.json"
        if loc_cache.exists():
            loc_cache.unlink()

    async with httpx.AsyncClient() as client:
        # Resolve user location
        location = await location_from_args(args, client)

    if not location:
        print(json.dumps({"error": "Could not determine location. Use --location or --lat/--lng."}))
        sys.exit(1)

    if location.country and location.country not in ("Australia", "AU"):
        print(json.dumps({
            "error": f"Detected location in {location.country}. This tool covers NSW cameras only.",
            "detected": {
                "city": location.city,
                "country": location.country,
                "lat": location.lat,
                "lng": location.lng,
            },
        }))
        sys.exit(1)

    # Flag IP-only detection so the agent knows accuracy is limited
    if location.method in ("ip-api.com", "ip-fallback") and not (args.lat and args.lng):
        location_confidence = "low"
    else:
        location_confidence = "high"

    # Filter cameras
    cameras = CAMERAS

    # Type filter
    if args.camera_type != "all":
        cameras = [c for c in cameras if c["type"] == args.camera_type]

    # Road filter (fuzzy)
    if args.road:
        cameras = [c for c in cameras if _road_matches(args.road, c["road"])]

    # Distance filter and sort
    nearby = []
    for cam in cameras:
        dist = haversine_km(location.lat, location.lng, cam["lat"], cam["lng"])
        if dist <= args.radius:
            nearby.append((dist, cam))

    nearby.sort(key=lambda x: x[0])

    # Build results
    camera_results = []
    for dist, cam in nearby:
        label = f"{cam['road']}, {cam['suburb']}"
        camera_results.append({
            "type": cam["type"],
            "road": cam["road"],
            "suburb": cam["suburb"],
            "direction": cam["direction"],
            "lat": cam["lat"],
            "lng": cam["lng"],
            "distance_km": round(dist, 1),
            "google_maps_url": _google_maps_url(cam["lat"], cam["lng"], label),
            "apple_maps_url": _apple_maps_url(cam["lat"], cam["lng"], label),
        })

    result = {
        "location": {
            "city": location.city,
            "state": location.state,
            "lat": location.lat,
            "lng": location.lng,
            "method": location.method,
            "confidence": location_confidence,
        },
        "query": {
            "radius_km": args.radius,
            "type": args.camera_type,
        },
        "results": {
            "count": len(camera_results),
            "cameras": camera_results,
        },
    }

    if args.road:
        result["query"]["road"] = args.road

    if location_confidence == "low":
        result["location"]["note"] = (
            "Location was detected via IP address only (city-level accuracy). "
            "The user may not actually be in this area. Ask them to confirm their "
            "suburb or postcode for accurate results."
        )

    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())
