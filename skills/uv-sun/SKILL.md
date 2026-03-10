---
name: uv-sun
description: >-
  Check the current UV index and sun safety advice for Australian cities.
  Use this skill when the user asks about UV index, sunscreen, sun protection,
  sunburn risk, whether it's safe to be outside in the sun, SPF recommendation,
  or sun safety for any Australian city. Works with zero configuration — no API keys needed.
---

# UV Sun Skill

Check current UV index and sun safety advice for Australian cities. Zero config — no API keys, no setup.

## When to Use

Trigger this skill when the user:

- Asks about the UV index or UV level
- Asks about sunscreen, SPF, or sun protection
- Wants to know if it's safe to be outside in the sun
- Asks about sunburn risk
- Asks whether they need a hat, sunglasses, or sun protection
- Wants sun safety advice for an Australian city
- Mentions ARPANSA or UV monitoring

## Prerequisites

- **uv** — `brew install uv` (macOS) or `pip install uv` (all platforms)
- **API keys** — not needed. ARPANSA UV data is fully open.
- **Dependencies** — declared inline (PEP 723), installed automatically by `uv run`.

## Setup Status

!`command -v uv > /dev/null 2>&1 && echo "uv: installed" || echo "uv: NOT INSTALLED"`

## Command Template

```bash
uv run "${CLAUDE_SKILL_DIR}/scripts/uv_sun.py" [OPTIONS]
```

## Options

| Flag | Values | Default | Purpose |
|------|--------|---------|---------|
| `--city` | city name (string) | `Sydney` | City to look up (fuzzy matched) |
| `--all` | *(flag)* | off | Show all cities sorted by UV index descending |
| `--no-cache` | *(flag)* | off | Force fresh data |

Only parse **stdout** (JSON). Stderr contains diagnostics only.

## Common Commands

```bash
# Default — Sydney UV index
uv run "${CLAUDE_SKILL_DIR}/scripts/uv_sun.py"

# Specific city
uv run "${CLAUDE_SKILL_DIR}/scripts/uv_sun.py" --city Melbourne

# Fuzzy match — "bris" matches "Brisbane"
uv run "${CLAUDE_SKILL_DIR}/scripts/uv_sun.py" --city bris

# All Australian cities sorted by UV index
uv run "${CLAUDE_SKILL_DIR}/scripts/uv_sun.py" --all

# Force fresh data
uv run "${CLAUDE_SKILL_DIR}/scripts/uv_sun.py" --city Perth --no-cache
```

## Presenting Results

DO NOT use markdown tables. They don't render on mobile chat platforms (Telegram, WhatsApp, Signal). Use plain text with line breaks instead.

### Single City Mode

```
UV Index for Sydney: 5.2 (Moderate)
Measured at 12:30 on 2026-03-11

Sun protection: Sun protection recommended from 10am to 3pm
SPF: SPF 30+
Exercise: Safe to exercise outdoors with sun protection

Source: ARPANSA UV Monitoring
```

### All Cities Mode

```
UV Index across Australia (highest to lowest):

Darwin — 11.3 (Extreme)
Townsville — 9.8 (Very High)
Brisbane — 8.1 (Very High)
Alice Springs — 7.5 (High)
Perth — 6.4 (High)
Sydney — 5.2 (Moderate)
Gold Coast — 5.0 (Moderate)
Adelaide — 4.8 (Moderate)
Newcastle — 4.5 (Moderate)
Canberra — 3.9 (Moderate)
Melbourne — 3.2 (Moderate)
Hobart — 2.1 (Low)

Source: ARPANSA UV Monitoring
```

### Formatting Rules

- Single city: show UV index, category, sun protection advice, SPF, and exercise advice
- All cities: list sorted by UV index descending, show city name, UV index, and category
- Always include the measurement time and date
- For exercise questions, lead with the exercise advice
- For sunscreen questions, lead with the SPF recommendation
- Invite follow-up: "Ask me about a specific city or say 'all cities' for the full list."

## Handling Edge Cases

- **City not found**: "I couldn't find a city matching '[query]' in the ARPANSA data. Available cities include: [list]. Try one of those."
- **No data available**: "UV data isn't available from ARPANSA right now. The feed may be temporarily down — try again in a few minutes."
- **Night time / zero UV**: The UV index may be 0 or very low outside daylight hours. Note this: "The UV index is currently 0 — it's outside daylight hours. UV levels will update when the sun rises."
- **API errors**: "Couldn't get UV data right now. The ARPANSA feed may be temporarily unavailable — try again in a few minutes."

## Reference

### UV Index Categories

| UV Index | Category | Sun Protection |
|----------|----------|----------------|
| 0-2 | Low | No protection required for most people |
| 3-5 | Moderate | Sun protection recommended 10am-3pm |
| 6-7 | High | Sun protection recommended 9am-4pm |
| 8-10 | Very High | Sun protection essential 8am-5pm |
| 11+ | Extreme | Sun protection essential all day |

### SPF Recommendations

| Category | SPF | Notes |
|----------|-----|-------|
| Low | SPF 15+ | Only if spending extended time outdoors |
| Moderate | SPF 30+ | Apply before going outside |
| High | SPF 50+ | Reapply every 2 hours |
| Very High | SPF 50+ | Reapply every 2 hours, seek shade |
| Extreme | SPF 50+ | Reapply every 2 hours, avoid peak hours |

### Available Cities

The ARPANSA feed covers major Australian cities including: Sydney, Melbourne, Brisbane, Adelaide, Perth, Darwin, Hobart, Canberra, Townsville, Alice Springs, Newcastle, Gold Coast. The `--all` flag shows every city in the feed.

### Data Source

All data comes from ARPANSA (Australian Radiation Protection and Nuclear Safety Agency) via their public UV monitoring XML feed. No API key needed. Data updates every few minutes during daylight hours. No user data is sent to any service.
