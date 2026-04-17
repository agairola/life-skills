# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A collection of **Agent Skills** (plugin spec: `.claude-plugin/plugin.json`) that give AI agents practical, real-world capabilities — mostly Australia/Sydney-focused (fuel prices, beaches, air quality, transit, rental prices, UV, parks, speed cameras, dams, traffic, tolls) plus a local neural TTS skill (`read-aloud`). Each skill is self-contained under `skills/<name>/` and installed via `npx skills add agairola/life-skills --skill <name>`.

Skills are designed to run in any chat platform (Telegram, WhatsApp, Signal, Discord, terminal), so formatting and location-resolution rules are shared across skills.

## Commands

All Python scripts are **PEP 723 inline-scripted** — they declare their own dependencies and are invoked via `uv run` (never `python` directly). `uv` is required.

```bash
# Run a skill script directly (same as the skill would)
uv run skills/fuel-pricing/scripts/fuel_prices.py --location "Newtown, NSW"

# Run all tests (pytest is not required; tests are plain assert-based)
uv run --with pytest pytest tests/ -v

# Run a single test file / test function
uv run --with pytest pytest tests/test_skills.py -v
uv run --with pytest pytest tests/test_script_execution.py::test_script_syntax -v
```

`tests/test_skills.py` validates SKILL.md structure (frontmatter, line limits, required sections). `tests/test_script_execution.py` validates that scripts parse, respond to `--help`, and produce valid JSON — offline-capable scripts (`dam-levels`, `speed-cameras`, `sydney-tolls`, `rental-prices`) get full integration tests; network-dependent scripts get syntax + `--help` + graceful-degradation checks.

## Architecture

### Skill anatomy

Each `skills/<name>/` contains:
- `SKILL.md` — required. YAML frontmatter (`name`, `description`, `allowed-tools`, optional `argument-hint`) followed by the agent-facing instructions. Body must stay under 500 lines (enforced by tests).
- `scripts/*.py` — PEP 723 scripts with `#!/usr/bin/env -S uv run --script` shebang and inline `dependencies = [...]` block. **Do not add requirements.txt or pyproject.toml per skill** — dependencies live in the script header so `uv run` handles everything.
- `references/` — optional long-form docs the skill references via relative links (e.g. `api_upgrade.md`).
- `evals/evals.json` — optional scenario tests for the skill's agent behavior.

Scripts are invoked by the agent via `uv run "${CLAUDE_SKILL_DIR}/scripts/<name>.py" …` — `CLAUDE_SKILL_DIR` is set by the harness; hardcoded paths will break installed skills.

### Shared conventions (why skills look similar)

Two files in the **top-level** `references/` directory are the source of truth for cross-skill behavior — update them here rather than copying rules into each SKILL.md:

- `references/location-flow.md` — mandatory location-resolution flow. Skills must ask the user for location (or accept shared location pins) before falling back to IP geolocation. Skills that need location flags are listed as `LOCATION_SKILLS` in `tests/test_skills.py`.
- `references/platform-formatting.md` — no markdown tables (they break on mobile chat), provide both Google + Apple Maps links for top results, end with a follow-up prompt.

When adding a new location-aware skill, link to these files from SKILL.md rather than duplicating the rules, and add the skill name to `EXPECTED_SKILLS` / `LOCATION_SKILLS` in `tests/test_skills.py`.

### Offline-first design

Data sources fall into tiers: some skills embed a snapshot of data (dam levels, speed cameras, tolls, rental medians) so they work fully offline; others fetch live data with graceful degradation when the network or an optional API key is unavailable. Both test suites assert these fallbacks exist — don't remove offline paths when refactoring.

### Optional API keys

Skills listed in `API_KEY_SKILLS` (`fuel-pricing`, `sydney-commute`, `sydney-traffic`) read optional keys from `~/.config/<skill-name>/credentials.json`. Scripts must still work without the key (return community/public-data fallback) — this is validated by the graceful-degradation tests.

## Adding or reviewing a skill

**Always use the `skill-creator` skill** (`skill-creator:skill-creator`) when creating a new skill, modifying an existing skill's SKILL.md/scripts, or reviewing a skill for quality. It enforces the Agent Skills spec (frontmatter, description triggers, line limits, progressive disclosure) and can run evals — do not hand-author SKILL.md from memory.

Invoke it via the `Skill` tool with `skill-creator:skill-creator` before making structural changes. Typical prompts: "create a new skill for X", "review skills/<name> against the spec", "optimize the description for skills/<name>".

Repo-specific steps that still apply after `skill-creator` produces the skill:

1. SKILL.md must link to `../../references/location-flow.md` and `../../references/platform-formatting.md` where relevant (don't duplicate their rules).
2. Scripts must be PEP 723 with the `#!/usr/bin/env -S uv run --script` shebang, support `--help`, and emit JSON on `--json` (tests enforce this).
3. Register the skill in `tests/test_skills.py` (`EXPECTED_SKILLS`, plus `LOCATION_SKILLS` / `API_KEY_SKILLS` if applicable) and `tests/test_script_execution.py` (`SCRIPTS`, and `OFFLINE_SCRIPTS` if the skill works without network).
4. Run the full test suite before committing.
