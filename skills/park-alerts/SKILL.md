---
name: park-alerts
description: >-
  Check alerts, closures, and fire bans for NSW National Parks.
  Use this skill when the user asks about park closures, fire bans,
  track closures, park conditions, whether a park is open, Blue Mountains
  conditions, bushwalking, hiking, camping trip planning, track conditions,
  or any NSW national park alert. Works with zero configuration — no API keys needed.
allowed-tools: Bash(uv run *), Read
argument-hint: "[park name]"
---

# Park Alerts Skill

Check alerts, closures, and fire bans for NSW National Parks. Zero config — no API keys, no setup.

## Install

```bash
npx skills add agairola/life-skills --skill park-alerts
```

## When to Use

Trigger this skill when the user:

- Asks about park closures or whether a park is open
- Asks about fire bans or fire danger in national parks
- Wants to know about track closures or changed conditions
- Asks about Blue Mountains conditions or any NSW national park alert
- Says "is the park open" or "park conditions"
- Asks about bushwalking or hiking conditions in NSW parks

## Prerequisites

- **uv** — `brew install uv` (macOS) or `pip install uv` (all platforms)
- **API keys** — not needed. Fully zero-config.
- **Dependencies** — declared inline (PEP 723), installed automatically by `uv run`.

## Setup Status

!`command -v uv > /dev/null 2>&1 && echo "uv: installed" || echo "uv: NOT INSTALLED"`

## Command Template

```bash
uv run "${CLAUDE_SKILL_DIR}/scripts/park_alerts.py" [OPTIONS]
```

## Options

| Flag | Values | Default | Purpose |
|------|--------|---------|---------|
| `--park` | park name (string) | *(none)* | Filter alerts by park name (fuzzy match) |
| `--category` | `closures` `fire` `conditions` `all` | `all` | Filter by alert category |
| `--limit` | integer | `10` | Maximum number of results |
| `--no-cache` | *(flag)* | off | Force fresh data |

Only parse **stdout** (JSON). Stderr contains diagnostics only.

## Common Commands

```bash
# All recent alerts (default limit 10)
uv run "${CLAUDE_SKILL_DIR}/scripts/park_alerts.py"

# Alerts for a specific park
uv run "${CLAUDE_SKILL_DIR}/scripts/park_alerts.py" --park "Blue Mountains"

# Only park closures
uv run "${CLAUDE_SKILL_DIR}/scripts/park_alerts.py" --category closures

# Only fire bans
uv run "${CLAUDE_SKILL_DIR}/scripts/park_alerts.py" --category fire

# Changed conditions for a specific park
uv run "${CLAUDE_SKILL_DIR}/scripts/park_alerts.py" --park "Royal" --category conditions

# More results
uv run "${CLAUDE_SKILL_DIR}/scripts/park_alerts.py" --park "Kosciuszko" --limit 20

# Force fresh data
uv run "${CLAUDE_SKILL_DIR}/scripts/park_alerts.py" --park "Blue Mountains" --no-cache
```

## Presenting Results

Follow the formatting rules in [../../references/platform-formatting.md](../../references/platform-formatting.md). Key skill-specific formatting below.

### Alert List

For platforms with hyperlinks (Telegram, Discord, terminal):
```
Blue Mountains National Park — 3 alerts:

1. Changed conditions — 10 Mar 2026
   Track closed due to landslide near Wentworth Falls.
   [More info](link_url)

2. Fire bans — 9 Mar 2026
   Total fire ban in effect for the Greater Blue Mountains area.
   [More info](link_url)

3. Changed conditions — 8 Mar 2026
   Grand Canyon Track reopened after maintenance.
   [More info](link_url)

Source: NSW National Parks and Wildlife Service
```

For platforms without hyperlinks (WhatsApp, Signal, SMS):
```
Blue Mountains National Park — 3 alerts:

1. Changed conditions — 10 Mar 2026
   Track closed due to landslide near Wentworth Falls.
   More info: [link_url]

2. Fire bans — 9 Mar 2026
   Total fire ban in effect for the Greater Blue Mountains area.
   More info: [link_url]

3. Changed conditions — 8 Mar 2026
   Grand Canyon Track reopened after maintenance.
   More info: [link_url]

Source: NSW National Parks and Wildlife Service
```

### Formatting Rules

- Group alerts by park when showing multiple parks
- Show category, date, and description for each alert
- Include the link for each alert so users can get full details
- Most recent alerts first
- When user asks about a specific park, lead with the park name and alert count
- When showing all alerts, group or list clearly with park names prominent
- Invite follow-up: "Ask me about a specific park or category for more detail"

## Handling Edge Cases

- **No alerts found** (park filter matched nothing): "No alerts found for [park name]. This usually means no current issues — the park is likely open. Check the NSW National Parks website for confirmation."
- **No alerts in category**: "No [closures/fire bans/changed conditions] found. Try a different category or check all alerts."
- **Empty RSS feed**: "Couldn't get park alerts right now. The NSW National Parks feed may be temporarily unavailable — try again in a few minutes."
- **API errors**: "Couldn't fetch park alerts. The NSW National Parks API may be temporarily unavailable — try again in a few minutes."
- **Ambiguous park name**: Show all matching alerts and let the user narrow down. "I found alerts for several parks matching '[query]' — here are the results."

## Reference

### Alert Categories

The RSS feed uses these category labels:

- Closed parks — full or partial park closures
- Fire bans — total fire bans and fire danger warnings
- Changed conditions — track closures, facility changes, hazards, reopenings
- Moderate fire danger — lower-level fire danger notices

The `--category` flag maps user-friendly names to these:
- `closures` matches "Closed parks"
- `fire` matches "Fire bans"
- `conditions` matches "Changed conditions"
- `all` shows everything (including Moderate fire danger)

### Data Source

All data comes from the NSW National Parks and Wildlife Service RSS feed. No API key needed. Data is updated by NPWS as conditions change. No user data is sent to any external service.
