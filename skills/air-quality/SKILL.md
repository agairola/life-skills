---
name: air-quality
description: >-
  Check current air quality and pollution levels at NSW monitoring stations.
  Use this skill when the user asks about air quality, AQI, PM2.5, PM10,
  pollution levels, smoke, haze, whether it's safe to run or exercise
  outside, bushfire smoke, or air quality health advice. Works with zero
  configuration — no API keys needed.
---

# Air Quality Skill

Check current air quality and pollution levels at NSW monitoring stations. Zero config — no API keys, no setup.

## When to Use

Trigger this skill when the user:

- Asks about air quality, AQI, or pollution levels
- Asks about PM2.5, PM10, ozone, or other pollutants
- Asks whether it's safe to run, cycle, or exercise outside
- Mentions smoke, haze, or bushfire smoke
- Wants health advice related to air quality
- Asks about air quality at a specific suburb or monitoring station

## Prerequisites

- **uv** — `brew install uv` (macOS) or `pip install uv` (all platforms)
- **API keys** — not needed. The NSW Air Quality API is fully open.
- **Dependencies** — declared inline (PEP 723), installed automatically by `uv run`.

## Setup Status

!`command -v uv > /dev/null 2>&1 && echo "uv: installed" || echo "uv: NOT INSTALLED"`

## Location Flow (IMPORTANT — follow this exactly)

Before fetching air quality data, you MUST resolve the user's location. Follow these steps in order — do NOT skip ahead to IP fallback.

**Step 1: Check what the user already provided.**
- User shared a location pin (Telegram, WhatsApp, Signal, Discord)? Extract lat/lng → use `--lat` / `--lng`. Done.
- User mentioned a suburb, city, or address? → use `--location`. Done.
- User mentioned a specific monitoring site? → use `--site`. Done.

**Step 2: User said "near me" or "nearby" but gave no location.**
Ask them to share location. Tailor the ask to their platform:
- Telegram: "Tap the paperclip icon → Location → Send My Current Location"
- WhatsApp: "Tap the + button → Location → Send Your Current Location"
- Signal: "Tap the + button → Location"
- Discord/terminal: "What suburb or postcode are you near?"

Wait for their response. Do not proceed without it.

**Step 3: User can't or won't share location.**
Ask: "No worries — what suburb or postcode are you near?" Wait for response.

**Step 4: User refuses to give any location info.**
Only now fall back to auto-detect (no location args). This uses IP geolocation which is city-level only and often wrong. If the result comes back with `confidence: "low"`, tell the user: "I got an approximate location of [city] from your IP but it may not be accurate. Can you tell me your suburb or postcode for better results?"

**Never silently use IP geolocation when you can ask the user instead.**

### Command Template

```bash
uv run "${CLAUDE_SKILL_DIR}/scripts/air_quality.py" [LOCATION_FLAGS] [OPTIONS]
```

### Options

| Flag | Values | Default | Purpose |
|------|--------|---------|---------|
| `--location` | suburb/city name | *(none)* | Specify location by name |
| `--lat` | decimal degrees | *(none)* | Latitude |
| `--lng` | decimal degrees | *(none)* | Longitude |
| `--site` | monitoring site name | *(none)* | Direct site lookup (fuzzy matched) |
| `--pollutant` | `PM2.5` `PM10` `O3` `NO2` `CO` `NEPH` | *(all)* | Filter to a specific pollutant |
| `--no-cache` | *(flag)* | off | Force fresh data |

Only parse **stdout** (JSON). Stderr contains diagnostics only.

### Common Commands

```bash
# User shared location via chat platform
uv run "${CLAUDE_SKILL_DIR}/scripts/air_quality.py" --lat -33.92 --lng 151.23

# User mentioned a place
uv run "${CLAUDE_SKILL_DIR}/scripts/air_quality.py" --location "Randwick"

# User asked about a specific monitoring station
uv run "${CLAUDE_SKILL_DIR}/scripts/air_quality.py" --site "RANDWICK"

# Auto-detect location (terminal — opens browser on first run)
uv run "${CLAUDE_SKILL_DIR}/scripts/air_quality.py"

# Specific pollutant
uv run "${CLAUDE_SKILL_DIR}/scripts/air_quality.py" --location "Parramatta" --pollutant PM2.5

# Force fresh data
uv run "${CLAUDE_SKILL_DIR}/scripts/air_quality.py" --location "Chullora" --no-cache
```

## Presenting Results

DO NOT use markdown tables. They don't render on mobile chat platforms (Telegram, WhatsApp, Signal). Use plain text with line breaks instead.

### Two Response Modes

**General mode (no pollutant filter):** Show all readings + overall category + health advice.

For platforms with hyperlinks (Telegram, Discord, terminal):
```
Air quality near [location] ([site name], [distance]km away):

Overall: Good
Health: Air quality is good. Enjoy outdoor activities.
Exercise: Safe to exercise outdoors.

Readings (10:00-11:00):
PM2.5 — 8.2 µg/m³ (Good)
PM10 — 15.0 µg/m³ (Good)
O3 — 3.1 pphm (Good)
NO2 — 0.8 pphm (Good)
CO — 0.2 ppm (Good)
NEPH — 0.5 10⁻⁴ m⁻¹ (Good)

Station: RANDWICK · Sydney East
```

For platforms without hyperlinks (WhatsApp, Signal, SMS):
```
Air quality near [location] ([site name], [distance]km away):

Overall: Good
Health: Air quality is good. Enjoy outdoor activities.
Exercise: Safe to exercise outdoors.

Readings (10:00-11:00):
PM2.5 — 8.2 µg/m³ (Good)
PM10 — 15.0 µg/m³ (Good)
O3 — 3.1 pphm (Good)
NO2 — 0.8 pphm (Good)
CO — 0.2 ppm (Good)
NEPH — 0.5 10⁻⁴ m⁻¹ (Good)

Station: RANDWICK · Sydney East
```

**Exercise mode (user asked "is it safe to run/exercise outside?"):** Lead with the exercise safety answer, then category + exercise advice.

```
Safe to exercise outdoors? Yes — air quality is Good.

Exercise advice: Safe to exercise outdoors.
Health advice: Air quality is good. Enjoy outdoor activities.

Current readings at RANDWICK (10:00-11:00):
PM2.5 — 8.2 µg/m³ (Good)
PM10 — 15.0 µg/m³ (Good)
```

### Formatting Rules

- General mode: show all available readings + overall category + both health and exercise advice
- Exercise mode: lead with yes/no answer to the exercise question, then details
- Always include the observation time and station name
- When bushfire smoke is detected, lead with the bushfire advisory in bold/emphasis
- Invite follow-up: "Ask me about a specific pollutant or a different location."

## Handling Edge Cases

- **Low confidence** (`confidence: "low"`): Do not silently show results. Tell the user: "I got an approximate location of [city] but it may not be exact. What suburb or postcode are you near?" Rerun with their answer.
- **No readings** (empty readings in last 6 hours): "No recent readings available for [site]. Want me to try a different monitoring station?"
- **Bushfire smoke** (`bushfire_smoke: true`): Lead with the bushfire advisory prominently. Use emphasis/bold. Then show the full readings. Recommend staying indoors.
- **No nearby site** (no site within 50km): "No monitoring station found within 50km of your location. You can try --site to query a specific station. Available stations include [list a few]."
- **Stale data** (observations from several hours ago): Note the observation time prominently — "These readings are from [time], which is [N] hours ago. Current conditions may differ."

## Reference

### AQI Categories

| Category | Health Advice | Exercise Advice |
|----------|--------------|-----------------|
| Good | Air quality is good. Enjoy outdoor activities. | Safe to exercise outdoors. |
| Fair | Acceptable. Sensitive people should consider reducing prolonged outdoor exertion. | Generally safe. Sensitive individuals may want to reduce intensity. |
| Poor | Sensitive groups may experience health effects. Consider reducing prolonged outdoor exertion. | Consider indoor exercise. Sensitive groups should avoid outdoor exertion. |
| Very Poor | Health effects likely for everyone. Reduce prolonged outdoor exertion. | Exercise indoors only. Outdoor activity not recommended. |
| Extremely Poor | Health alert — everyone may experience serious health effects. Avoid outdoor activity. | Do not exercise outdoors. Stay indoors. |
| Hazardous | Health emergency. Stay indoors with windows closed. Run air purifiers if available. | Do not exercise. Minimise all physical exertion. |

### Pollutant Codes

| Code | Name | Unit |
|------|------|------|
| PM2.5 | Fine Particulate Matter | µg/m³ |
| PM10 | Coarse Particulate Matter | µg/m³ |
| O3 | Ozone | pphm |
| NO2 | Nitrogen Dioxide | pphm |
| CO | Carbon Monoxide | ppm |
| NEPH | Nephelometer (visibility/haze) | 10⁻⁴ m⁻¹ |

### Bushfire Smoke Detection

Bushfire smoke is flagged when PM2.5 > 25 µg/m³ AND (NEPH > 2.0 OR PM2.5 > 50). When detected, the JSON includes `bushfire_smoke: true` and a `bushfire_advisory` message.

### Script Location Fallback (internal — for reference only)

When the script runs, it resolves location internally in this order:

1. **Explicit args** — `--lat`/`--lng` or `--location` (Nominatim geocoding)
2. **Browser consent** — localhost page requesting `navigator.geolocation` (WiFi, ~15-50ft accuracy, cached 24hrs)
3. **IP geolocation** — ip-api.com (city-level only, often inaccurate for non-city users)

The agent should almost never reach step 3. The Location Flow above ensures the user provides location info before the script runs.
