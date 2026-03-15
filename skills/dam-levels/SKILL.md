---
name: dam-levels
description: >-
  Check current dam levels and water storage for Greater Sydney.
  Use this skill when the user asks about dam levels, water storage,
  Warragamba Dam, how full dams are, water restrictions, dam capacity,
  Sydney water supply, or reservoir levels. Works with zero configuration — no API keys needed.
allowed-tools: Bash(uv run *), Read
argument-hint: "[dam name]"
---

# Dam Levels Skill

Check current dam levels and water storage for Greater Sydney. Zero config — no API keys, no setup.

## Install

```bash
npx skills add agairola/life-skills --skill dam-levels
```

## When to Use

Trigger this skill when the user:

- Asks about dam levels, water storage, or reservoir levels
- Asks how full Warragamba Dam (or any Sydney dam) is
- Asks about water restrictions or water supply
- Wants to know dam capacity or volume
- Mentions Sydney water supply, dam storage, or drought conditions
- Asks "how much water do we have" or similar

## Prerequisites

- **uv** — `brew install uv` (macOS) or `pip install uv` (all platforms)
- **API keys** — not needed. Data is scraped from the public WaterNSW website.
- **Dependencies** — declared inline (PEP 723), installed automatically by `uv run`.

## Setup Status

!`command -v uv > /dev/null 2>&1 && echo "uv: installed" || echo "uv: NOT INSTALLED"`

### Command Template

```bash
uv run "${CLAUDE_SKILL_DIR}/scripts/dam_levels.py" [OPTIONS]
```

### Options

| Flag | Values | Default | Purpose |
|------|--------|---------|---------|
| `--dam` | dam name (string) | *(none)* | Search for a specific dam by name (fuzzy matched) |
| `--all` | *(flag)* | on | Show all Greater Sydney dams (default behaviour) |
| `--no-cache` | *(flag)* | off | Force fresh data |

Only parse **stdout** (JSON). Stderr contains diagnostics only.

### Common Commands

```bash
# All Greater Sydney dams (default)
uv run "${CLAUDE_SKILL_DIR}/scripts/dam_levels.py"

# Specific dam by name (fuzzy matched)
uv run "${CLAUDE_SKILL_DIR}/scripts/dam_levels.py" --dam "Warragamba"

# Another dam
uv run "${CLAUDE_SKILL_DIR}/scripts/dam_levels.py" --dam "Woronora"

# Force fresh data
uv run "${CLAUDE_SKILL_DIR}/scripts/dam_levels.py" --no-cache

# Explicit all dams
uv run "${CLAUDE_SKILL_DIR}/scripts/dam_levels.py" --all
```

## Presenting Results

Follow the formatting rules in [../../references/platform-formatting.md](../../references/platform-formatting.md). Key skill-specific formatting below.

### All Dams (default)

```
Greater Sydney Dam Levels:

Total system: 95.2% (2,565,855 ML of 2,696,310 ML)
Water restrictions: No restrictions (system above 60%)

Warragamba Dam — 95.8% (2,027,255 ML)
Avon Dam — 93.2% (195,240 ML)
Cataract Dam — 98.1% (93,290 ML)
Woronora Dam — 97.2% (68,175 ML)
Nepean Dam — 99.1% (66,750 ML)
Cordeaux Dam — 96.5% (50,710 ML)
Prospect Reservoir — 83.5% (29,515 ML)
Wingecarribee Reservoir — 88.3% (24,330 ML)
Fitzroy Falls Reservoir — 91.0% (9,110 ML)
Tallowa Dam (Shoalhaven) — 85.0% (7,480 ML)

Source: WaterNSW
```

### Single Dam (--dam)

```
Warragamba Dam — 95.8%

Volume: 2,027,255 ML of 2,031,000 ML total capacity
Water restrictions: No restrictions (system above 60%)

Source: WaterNSW
```

### Formatting Rules

- Sort dams by volume (largest first) for the all-dams view
- Format ML values with commas for readability (e.g., 2,027,255 ML)
- Always include the total system percentage and water restriction status
- If using fallback data, note it clearly: "Note: Live data was unavailable. Showing data from [date]."
- Invite follow-up: "Ask me about a specific dam for more detail."

## Handling Edge Cases

- **Fallback data** (`data_source: "fallback"`): Show results but add a note — "Note: Live data from WaterNSW was unavailable. Showing stored data from [fallback date]. Check waternsw.com.au for the latest."
- **No matching dam** (error response): "No dam matching '[query]' found. Available dams: [list]. Try a different name."
- **Scraping failure**: The script automatically falls back to embedded data. If even that fails, show the error message from the JSON.
- **Water restrictions**: Always mention the restriction status prominently. If restrictions are likely (below 60%), emphasise this.

## Reference

### Greater Sydney Dams

| Dam | Total Capacity (ML) |
|-----|-------------------|
| Warragamba Dam | 2,031,000 |
| Avon Dam | 214,640 |
| Cataract Dam | 97,190 |
| Woronora Dam | 71,790 |
| Nepean Dam | 67,730 |
| Cordeaux Dam | 54,250 |
| Prospect Reservoir | 33,330 |
| Wingecarribee Reservoir | 27,580 |
| Fitzroy Falls Reservoir | 10,000 |
| Tallowa Dam (Shoalhaven) | 8,800 |

### Water Restriction Levels

| System Level | Status |
|-------------|--------|
| Above 60% | No restrictions |
| 50-60% | Level 1 restrictions likely |
| 40-50% | Level 2 restrictions likely |
| Below 40% | Severe restrictions likely |

### Data Source

Data is scraped from the public WaterNSW website. If scraping fails, embedded fallback data is used. No API key is needed. No user data is sent to any service.
