---
name: speed-cameras
description: >-
  Find speed cameras and red light cameras near your location in NSW.
  Use this skill when the user asks about speed cameras, red light cameras,
  traffic cameras, camera locations, where the cameras are on a road,
  or wants to know about fixed speed cameras near them. Works with zero
  configuration — no API keys needed.
---

# Speed Cameras Skill

Find fixed speed cameras and red light cameras near you in NSW. Zero config — no API keys, no setup.

## Install

```bash
npx skills add agairola/life-skills --skill speed-cameras
```

## When to Use

Trigger this skill when the user:

- Asks about speed cameras or red light cameras
- Wants to know where cameras are on a particular road or motorway
- Asks about traffic cameras near them or near a location
- Mentions fixed speed cameras, camera enforcement, or speed camera locations
- Wants to plan a drive and check for cameras along a route
- Says "are there cameras on the M4" or "speed cameras near me"

## Prerequisites

- **uv** — `brew install uv` (macOS) or `pip install uv` (all platforms)
- **API keys** — not needed. Fully zero-config.
- **Dependencies** — declared inline (PEP 723), installed automatically by `uv run`.

## Setup Status

!`command -v uv > /dev/null 2>&1 && echo "uv: installed" || echo "uv: NOT INSTALLED"`

## Location Flow (IMPORTANT — follow this exactly)

Before searching for cameras, you MUST resolve the user's location. Follow these steps in order — do NOT skip ahead to IP fallback.

**Step 1: Check what the user already provided.**
- User shared a location pin (Telegram, WhatsApp, Signal, Discord)? Extract lat/lng -> use `--lat` / `--lng`. Done.
- User mentioned a suburb, city, or address? -> use `--location`. Done.
- User mentioned a specific road? -> use `--road` along with location. Done.

**Step 2: User said "near me" or "nearby" but gave no location.**
Ask them to share location. Tailor the ask to their platform:
- Telegram: "Tap the paperclip icon -> Location -> Send My Current Location"
- WhatsApp: "Tap the + button -> Location -> Send Your Current Location"
- Signal: "Tap the + button -> Location"
- Discord/terminal: "What suburb or postcode are you near?"

Wait for their response. Do not proceed without it.

**Step 3: User can't or won't share location.**
Ask: "No worries — what suburb or postcode are you near?" Wait for response.

**Step 4: User refuses to give any location info.**
Only now fall back to auto-detect (no location args). This uses IP geolocation which is city-level only and often wrong. If the result comes back with `confidence: "low"`, tell the user: "I got an approximate location of [city] from your IP but it may not be accurate. Can you tell me your suburb or postcode for better results?"

**Never silently use IP geolocation when you can ask the user instead.**

### Command Template

```bash
uv run "${CLAUDE_SKILL_DIR}/scripts/speed_cameras.py" [LOCATION_FLAGS] [OPTIONS]
```

### Options

| Flag | Values | Default | Purpose |
|------|--------|---------|---------|
| `--location` | suburb/city name | — | Find cameras near a place name |
| `--lat` | latitude (float) | — | Latitude for nearby search |
| `--lng` | longitude (float) | — | Longitude for nearby search |
| `--radius` | km (float) | `5` | Search radius in km |
| `--road` | road name (string) | — | Filter by road name (fuzzy match) |
| `--type` | `fixed_speed` / `red_light` / `fixed_speed_and_red_light` / `all` | `all` | Camera type filter |
| `--no-cache` | *(flag)* | off | Skip location cache |

Only parse **stdout** (JSON). Stderr contains diagnostics only.

### Common Commands

```bash
# Cameras near a suburb
uv run "${CLAUDE_SKILL_DIR}/scripts/speed_cameras.py" --location "Homebush NSW"

# User shared location via chat platform
uv run "${CLAUDE_SKILL_DIR}/scripts/speed_cameras.py" --lat -33.87 --lng 151.21

# Cameras on a specific road
uv run "${CLAUDE_SKILL_DIR}/scripts/speed_cameras.py" --road "Pacific Highway" --radius 50

# Only red light cameras near me
uv run "${CLAUDE_SKILL_DIR}/scripts/speed_cameras.py" --location "Surry Hills" --type red_light

# Auto-detect location (terminal — opens browser on first run)
uv run "${CLAUDE_SKILL_DIR}/scripts/speed_cameras.py"

# Wider search radius
uv run "${CLAUDE_SKILL_DIR}/scripts/speed_cameras.py" --location "Parramatta" --radius 15
```

## Presenting Results

DO NOT use markdown tables. They don't render on mobile chat platforms (Telegram, WhatsApp, Signal). Use plain text with line breaks instead.

### Map Links

Each camera in the JSON includes two URL fields:
- `google_maps_url` — pins exact lat/lng
- `apple_maps_url` — pins exact lat/lng with label

Use hyperlinks (not raw URLs) where the platform supports them:
- **Telegram, Discord, terminal**: Use markdown links — `[Road Name](url)`
- **WhatsApp, Signal, SMS**: These don't support hyperlinks. Put the link on a separate line.

Provide **both** Google Maps and Apple Maps links so the user can choose.

### Camera List

For platforms with hyperlinks (Telegram, Discord, terminal):
```
Speed cameras near Homebush (within 5 km):

1. [Parramatta Road](google_maps_url) — Fixed speed camera
   Suburb: Homebush · Westbound · 1.2 km away
   [Apple Maps](apple_maps_url)
2. [Victoria Road](google_maps_url) — Fixed speed camera
   Suburb: Gladesville · Northbound · 3.1 km away
3. [M4 Motorway](google_maps_url) — Fixed speed camera
   Suburb: Merrylands · Eastbound · 4.8 km away

3 cameras found within 5 km
```

For platforms without hyperlinks (WhatsApp, Signal, SMS):
```
Speed cameras near Homebush (within 5 km):

1. Parramatta Road — Fixed speed camera
   Suburb: Homebush · Westbound · 1.2 km away
   Google Maps: [google_maps_url]
   Apple Maps: [apple_maps_url]
2. Victoria Road — Fixed speed camera
   Suburb: Gladesville · Northbound · 3.1 km away
   Google Maps: [google_maps_url]
3. M4 Motorway — Fixed speed camera
   Suburb: Merrylands · Eastbound · 4.8 km away
   Google Maps: [google_maps_url]

3 cameras found within 5 km
```

### Formatting Rules

- Sort by distance ascending (closest first)
- Show camera type in human-readable form: "Fixed speed camera", "Red light camera", "Fixed speed + red light camera"
- Include direction (Northbound, Southbound, etc.)
- Both Google Maps and Apple Maps for the closest result; Google Maps only for the rest
- If `--road` was used, mention the road filter in the summary
- Invite follow-up: "Want me to check a different area or road?"

## Handling Edge Cases

- **Low confidence** (`confidence: "low"`): Do not silently show results. Tell the user: "I got an approximate location of [city] but it may not be exact. What suburb or postcode are you near?" Rerun with their answer.
- **No results** (empty cameras): "No cameras found within [radius]km of [location]. Want me to try a wider search?" If a road filter was used: "No cameras found on [road] within [radius]km. Try without the road filter or with a wider radius."
- **Non-NSW location**: Camera data covers NSW only. If the user is clearly outside NSW, let them know: "Speed camera data is currently available for NSW only."

## Reference

### Camera Types

| Type | Description |
|------|-------------|
| `fixed_speed` | Fixed speed camera — detects vehicles exceeding the speed limit |
| `red_light` | Red light camera — detects vehicles running red lights |
| `fixed_speed_and_red_light` | Combined camera — detects both speed and red light offences |

### Data Source

Camera locations are sourced from publicly available NSW Government data on fixed speed camera and red light camera positions. The embedded dataset covers ~70 camera locations across the Sydney metropolitan area and surrounds. Mobile speed camera locations are not included as they change daily. No API key is needed. No user data is sent to any service beyond coordinates for geocoding.

### Script Location Fallback (internal — for reference only)

When the script runs, it resolves location internally in this order:

1. **Explicit args** — `--lat`/`--lng` or `--location` (Nominatim geocoding)
2. **Browser consent** — localhost page requesting `navigator.geolocation` (WiFi, ~15-50ft accuracy, cached 24hrs)
3. **IP geolocation** — ip-api.com (city-level only, often inaccurate for non-city users)

The agent should almost never reach step 3. The Location Flow above ensures the user provides location info before the script runs.
