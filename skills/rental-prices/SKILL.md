---
name: rental-prices
description: >-
  Check median rental prices for Sydney suburbs.
  Use this skill when the user asks about rent prices, how much rent is,
  rental costs, median rent, weekly rent, affordable suburbs, cheap rent,
  2-bedroom rent, unit prices, house rental costs, or any Sydney rental
  market question. Works with zero configuration — no API keys needed.
---

# Rental Prices Skill

Check median rental prices for Sydney suburbs. Zero config — no API keys, no setup. Data is embedded directly in the script (NSW DCJ Rent and Sales Report, Q4 2025).

## When to Use

Trigger this skill when the user:

- Asks about rental prices, rent costs, or how much rent is in a suburb
- Wants to know median weekly rent for a Sydney suburb
- Asks about affordable suburbs or cheap rent in Sydney
- Wants to compare rents between suburbs or property types
- Asks about 1/2/3/4-bedroom unit or house rental costs
- Says "how much is rent in Newtown" or "cheap 2-bedroom units"
- Wants to find suburbs within a rental budget
- Asks about nearby rental prices relative to a location

## Prerequisites

- **uv** — `brew install uv` (macOS) or `pip install uv` (all platforms)
- **API keys** — not needed. Fully zero-config.
- **Dependencies** — declared inline (PEP 723), installed automatically by `uv run`.

## Setup Status

!`command -v uv > /dev/null 2>&1 && echo "uv: installed" || echo "uv: NOT INSTALLED"`

## Location Flow (for --location mode only)

Location resolution is only needed when the user wants nearby suburbs. For `--suburb`, `--postcode`, `--budget` (without location), or default mode, no location is needed.

**Step 1: Check what the user already provided.**
- User shared a location pin (Telegram, WhatsApp, Signal, Discord)? Extract lat/lng -> use `--lat` / `--lng`. Done.
- User mentioned a suburb, city, or address? -> use `--location`. Done.
- User mentioned a specific suburb name? -> use `--suburb`. Done.

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
uv run "${CLAUDE_SKILL_DIR}/scripts/rental_prices.py" [OPTIONS]
```

### Options

| Flag | Values | Default | Purpose |
|------|--------|---------|---------|
| `--suburb` | suburb name (string) | — | Search for a specific suburb by name (fuzzy match) |
| `--postcode` | postcode (string) | — | Search by postcode |
| `--bedrooms` | 1, 2, 3, 4 | all | Filter by bedroom count |
| `--type` | house, unit, all | `all` | Property type filter |
| `--budget` | max weekly rent (int) | — | Find suburbs within budget |
| `--location` | suburb/city name | — | Find nearby suburbs by place name |
| `--lat` | latitude (float) | — | Latitude for nearby search |
| `--lng` | longitude (float) | — | Longitude for nearby search |
| `--radius` | km (float) | `5` | Search radius for nearby mode |
| `--no-cache` | *(flag)* | off | Force fresh data |

Only parse **stdout** (JSON). Stderr contains diagnostics only.

### Common Commands

```bash
# Search for a specific suburb
uv run "${CLAUDE_SKILL_DIR}/scripts/rental_prices.py" --suburb "Newtown"

# Search by postcode
uv run "${CLAUDE_SKILL_DIR}/scripts/rental_prices.py" --postcode 2042

# Filter by bedrooms and property type
uv run "${CLAUDE_SKILL_DIR}/scripts/rental_prices.py" --suburb "Bondi" --bedrooms 2 --type unit

# Find suburbs within a budget
uv run "${CLAUDE_SKILL_DIR}/scripts/rental_prices.py" --budget 500 --type unit --bedrooms 2

# Find suburbs within budget near a location
uv run "${CLAUDE_SKILL_DIR}/scripts/rental_prices.py" --budget 600 --type unit --bedrooms 2 --location "Redfern"

# Nearby suburbs with rents
uv run "${CLAUDE_SKILL_DIR}/scripts/rental_prices.py" --location "Coogee, NSW" --radius 3

# Nearby by coordinates
uv run "${CLAUDE_SKILL_DIR}/scripts/rental_prices.py" --lat -33.89 --lng 151.27 --radius 5

# Default: top 10 most affordable 2br units
uv run "${CLAUDE_SKILL_DIR}/scripts/rental_prices.py"
```

## Presenting Results

DO NOT use markdown tables. They don't render on mobile chat platforms (Telegram, WhatsApp, Signal). Use plain text with line breaks instead.

### Suburb Search: Single Suburb Detail

```
Newtown (2042) — Median Weekly Rents

Units:
  1 bed: $480/wk
  2 bed: $650/wk
  3 bed: $830/wk

Houses:
  2 bed: $800/wk
  3 bed: $1,050/wk
  4 bed: $1,350/wk

Source: NSW DCJ Rent and Sales Report, Q4 2025
```

### Budget Search: Affordable Suburbs

```
Suburbs with 2-bedroom units under $500/wk:

1. Mount Druitt (2770) — $430/wk
2. Campbelltown (2560) — $440/wk
3. Fairfield (2165) — $440/wk
4. Cabramatta (2166) — $440/wk
5. Penrith (2750) — $470/wk

15 suburbs found under $500/wk
Source: NSW DCJ Rent and Sales Report, Q4 2025
```

### Nearby: Suburb List with Rents

```
Suburbs near Bondi (within 5 km):

1. Bondi (2026) — 0.0 km
   Unit: $600–$1,100/wk · House: $1,000–$1,800/wk
2. Bondi Beach (2026) — 0.1 km
   Unit: $620–$1,150/wk · House: $1,050–$1,900/wk
3. Bronte (2024) — 1.4 km
   Unit: $580–$1,050/wk · House: $1,000–$1,750/wk

8 suburbs found within 5 km
Source: NSW DCJ Rent and Sales Report, Q4 2025
```

### Formatting Rules

- Always show rent as "$X/wk" format with dollar sign and /wk suffix
- For ranges, show min–max (e.g., "$480–$830/wk")
- Use commas in numbers over 999 (e.g., "$1,050/wk")
- Always include the data source and quarter
- When showing multiple property types, group by type (Units / Houses)
- For budget mode, sort by rent ascending
- For nearby mode, sort by distance ascending
- Invite follow-up: "Ask me about a specific suburb for full detail" or "Want to see houses instead of units?"

## Handling Edge Cases

- **No match** for suburb name: "I couldn't find a suburb matching '[name]' in the rental data. Try a different spelling or use --postcode instead. Coverage: ~100 popular Sydney suburbs."
- **No results** within budget: "No suburbs found with [type] [bedrooms] under $[budget]/wk. The cheapest option is [suburb] at $[rent]/wk. Want me to increase the budget?"
- **No nearby suburbs**: "No suburbs found within [radius]km. Try a wider radius with --radius 10. Note: this tool covers ~100 popular Sydney suburbs."
- **Low confidence location** (`confidence: "low"`): Do not silently show results. Tell the user: "I got an approximate location of [city] but it may not be exact. What suburb or postcode are you near?" Rerun with their answer.
- **Outside Sydney**: "Rental data currently covers Sydney suburbs only. For other areas, check the NSW DCJ Rent and Sales Report at https://www.facs.nsw.gov.au/resources/statistics/rent-and-sales"

## Reference

### Data Coverage

- ~100 popular Sydney suburbs
- Property types: units (1br, 2br, 3br) and houses (2br, 3br, 4br)
- Data period: Q4 2025
- Values are median weekly rents in AUD

### Data Source

All data is based on the NSW Department of Communities and Justice (DCJ) Rent and Sales Report. Data is embedded directly in the script — no API calls needed for rental data. Location features (--location, --lat/--lng) use Nominatim for geocoding and ip-api.com as a fallback. No API keys required. No user data is sent to any service beyond coordinates for geocoding.
