#!/usr/bin/env python3
"""
TDD validation tests for life-skills.

Tests the structure, frontmatter, content, and consistency of all skills
against the Agent Skills specification.
"""

import json
import os
import re
import stat
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / "skills"
REFERENCES_DIR = REPO_ROOT / "references"

# All known skills
EXPECTED_SKILLS = [
    "air-quality",
    "beach-check",
    "dam-levels",
    "frame-tv",
    "fuel-pricing",
    "park-alerts",
    "rental-prices",
    "speed-cameras",
    "sydney-commute",
    "sydney-tolls",
    "sydney-traffic",
    "uv-sun",
]

# Skills that require location resolution
LOCATION_SKILLS = [
    "air-quality",
    "beach-check",
    "fuel-pricing",
    "rental-prices",
    "speed-cameras",
    "sydney-commute",
    "sydney-traffic",
]

# Skills that have optional API keys
API_KEY_SKILLS = [
    "frame-tv",
    "fuel-pricing",
    "sydney-commute",
    "sydney-traffic",
]

# Required frontmatter fields
REQUIRED_FRONTMATTER = ["name", "description", "allowed-tools"]
RECOMMENDED_FRONTMATTER = ["argument-hint"]

# Max SKILL.md body lines (spec says under 500)
MAX_SKILL_LINES = 500

passed = 0
failed = 0
errors = []


def test(name, condition, msg=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  \033[32m✓\033[0m {name}")
    else:
        failed += 1
        detail = f" — {msg}" if msg else ""
        errors.append(f"{name}{detail}")
        print(f"  \033[31m✗\033[0m {name}{detail}")


def parse_frontmatter(content):
    """Parse YAML frontmatter from SKILL.md content."""
    if not content.startswith("---"):
        return {}
    end = content.index("---", 3)
    fm_text = content[3:end].strip()
    # Simple YAML parser for our flat structure
    result = {}
    current_key = None
    current_value = []
    for line in fm_text.split("\n"):
        # Check for new key
        match = re.match(r'^(\S[\w-]+):\s*(.*)', line)
        if match:
            if current_key:
                result[current_key] = "\n".join(current_value).strip()
            current_key = match.group(1)
            current_value = [match.group(2)] if match.group(2) else []
        elif current_key:
            current_value.append(line.strip())
    if current_key:
        result[current_key] = "\n".join(current_value).strip()
    return result


def get_body(content):
    """Get the markdown body after frontmatter."""
    if not content.startswith("---"):
        return content
    end = content.index("---", 3)
    return content[end + 3:].strip()


# ============================================================================
# Test: Repository structure
# ============================================================================
print("\n\033[1m=== Repository Structure ===\033[0m")

test("skills/ directory exists", SKILLS_DIR.is_dir())
test("references/ directory exists", REFERENCES_DIR.is_dir())
test("plugin.json exists", (REPO_ROOT / ".claude-plugin" / "plugin.json").is_file())

for skill in EXPECTED_SKILLS:
    skill_dir = SKILLS_DIR / skill
    test(f"{skill}/ directory exists", skill_dir.is_dir())
    test(f"{skill}/SKILL.md exists", (skill_dir / "SKILL.md").is_file())
    test(f"{skill}/scripts/ directory exists", (skill_dir / "scripts").is_dir())

# ============================================================================
# Test: Shared reference files
# ============================================================================
print("\n\033[1m=== Shared References ===\033[0m")

test("references/location-flow.md exists", (REFERENCES_DIR / "location-flow.md").is_file())
test("references/platform-formatting.md exists", (REFERENCES_DIR / "platform-formatting.md").is_file())

if (REFERENCES_DIR / "location-flow.md").is_file():
    loc_content = (REFERENCES_DIR / "location-flow.md").read_text()
    test("location-flow.md has Step 1-4", all(f"Step {i}" in loc_content for i in range(1, 5)))
    test("location-flow.md mentions platform instructions",
         "Telegram" in loc_content and "WhatsApp" in loc_content)

if (REFERENCES_DIR / "platform-formatting.md").is_file():
    fmt_content = (REFERENCES_DIR / "platform-formatting.md").read_text()
    test("platform-formatting.md mentions no-tables rule", "DO NOT use markdown tables" in fmt_content)
    test("platform-formatting.md mentions map links", "Google Maps" in fmt_content and "Apple Maps" in fmt_content)

# ============================================================================
# Test: Frontmatter fields
# ============================================================================
print("\n\033[1m=== Frontmatter Fields ===\033[0m")

for skill in EXPECTED_SKILLS:
    skill_md = SKILLS_DIR / skill / "SKILL.md"
    if not skill_md.is_file():
        continue
    content = skill_md.read_text()
    fm = parse_frontmatter(content)

    test(f"{skill}: has 'name' field", "name" in fm)
    test(f"{skill}: name matches directory", fm.get("name") == skill,
         f"got '{fm.get('name')}', expected '{skill}'")
    test(f"{skill}: has 'description' field", "description" in fm)
    test(f"{skill}: has 'allowed-tools' field", "allowed-tools" in fm,
         "needed for permission-free invocation")
    test(f"{skill}: has 'argument-hint' field", "argument-hint" in fm,
         "improves autocomplete UX")
    test(f"{skill}: description is non-empty",
         len(fm.get("description", "")) > 20,
         f"description is only {len(fm.get('description', ''))} chars")

# ============================================================================
# Test: Description quality (pushiness)
# ============================================================================
print("\n\033[1m=== Description Quality ===\033[0m")

PUSHY_KEYWORDS = {
    "frame-tv": ["Samsung Frame", "art", "generate", "TV", "image", "wall art"],
    "fuel-pricing": ["filling up", "refuel", "servo", "petrol", "diesel", "gas station"],
    "beach-check": ["swim", "surf", "ocean", "Bondi", "water quality"],
    "air-quality": ["exercise", "run outside", "smoke", "haze", "pollution"],
    "sydney-commute": ["train", "bus", "ferry", "Opal", "how do I get"],
    "uv-sun": ["sunscreen", "sunburn", "outside", "outdoor", "beach", "picnic"],
    "park-alerts": ["bushwalk", "hike", "camping", "park open", "fire ban"],
    "speed-cameras": ["speed camera", "red light", "camera location"],
    "dam-levels": ["dam", "water storage", "Warragamba", "drought", "water supply"],
    "sydney-traffic": ["traffic", "road closure", "accident", "roadwork"],
    "sydney-tolls": ["toll", "M2", "harbour bridge", "E-Tag"],
    "rental-prices": ["rent", "rental", "affordable", "moving to Sydney", "apartment"],
}

for skill in EXPECTED_SKILLS:
    skill_md = SKILLS_DIR / skill / "SKILL.md"
    if not skill_md.is_file():
        continue
    fm = parse_frontmatter(skill_md.read_text())
    desc = fm.get("description", "").lower()
    keywords = PUSHY_KEYWORDS.get(skill, [])
    matches = [kw for kw in keywords if kw.lower() in desc]
    test(f"{skill}: description has ≥3 trigger keywords ({len(matches)}/{len(keywords)})",
         len(matches) >= 3,
         f"found: {matches}, missing: {[kw for kw in keywords if kw.lower() not in desc]}")

# ============================================================================
# Test: SKILL.md body length
# ============================================================================
print("\n\033[1m=== SKILL.md Length ===\033[0m")

for skill in EXPECTED_SKILLS:
    skill_md = SKILLS_DIR / skill / "SKILL.md"
    if not skill_md.is_file():
        continue
    content = skill_md.read_text()
    body = get_body(content)
    line_count = len(body.split("\n"))
    test(f"{skill}: SKILL.md body under {MAX_SKILL_LINES} lines ({line_count})",
         line_count < MAX_SKILL_LINES)

# ============================================================================
# Test: Location flow deduplication
# ============================================================================
print("\n\033[1m=== Location Flow Deduplication ===\033[0m")

for skill in LOCATION_SKILLS:
    skill_md = SKILLS_DIR / skill / "SKILL.md"
    if not skill_md.is_file():
        continue
    content = skill_md.read_text()
    body = get_body(content)
    # Should reference the shared file, not contain the full 4-step flow inline
    has_reference = "location-flow.md" in body
    has_inline_steps = all(f"**Step {i}" in body for i in range(1, 5))
    test(f"{skill}: references shared location-flow.md", has_reference,
         "still contains inline Location Flow steps" if has_inline_steps else "missing location reference")

# ============================================================================
# Test: Platform formatting deduplication
# ============================================================================
print("\n\033[1m=== Platform Formatting Deduplication ===\033[0m")

for skill in EXPECTED_SKILLS:
    skill_md = SKILLS_DIR / skill / "SKILL.md"
    if not skill_md.is_file():
        continue
    content = skill_md.read_text()
    body = get_body(content)
    has_reference = "platform-formatting.md" in body
    # Check for duplicated boilerplate
    has_inline_boilerplate = ("DO NOT use markdown tables" in body
                              and "WhatsApp, Signal, SMS" in body
                              and "hyperlinks" in body)
    test(f"{skill}: references shared platform-formatting.md", has_reference,
         "still contains inline platform formatting boilerplate" if has_inline_boilerplate else "")

# ============================================================================
# Test: Reference files exist for skills with reference data
# ============================================================================
print("\n\033[1m=== Reference Files ===\033[0m")

for skill in API_KEY_SKILLS:
    ref_dir = SKILLS_DIR / skill / "references"
    test(f"{skill}: has references/ directory", ref_dir.is_dir())
    test(f"{skill}: has references/api_upgrade.md",
         (ref_dir / "api_upgrade.md").is_file() if ref_dir.is_dir() else False)

# ============================================================================
# Test: Script file permissions (all should be executable)
# ============================================================================
print("\n\033[1m=== Script Permissions ===\033[0m")

for skill in EXPECTED_SKILLS:
    scripts_dir = SKILLS_DIR / skill / "scripts"
    if not scripts_dir.is_dir():
        continue
    for script in scripts_dir.glob("*.py"):
        is_exec = os.access(script, os.X_OK)
        test(f"{skill}/{script.name}: is executable", is_exec)

# ============================================================================
# Test: Script shebang lines
# ============================================================================
print("\n\033[1m=== Script Shebangs ===\033[0m")

for skill in EXPECTED_SKILLS:
    scripts_dir = SKILLS_DIR / skill / "scripts"
    if not scripts_dir.is_dir():
        continue
    for script in scripts_dir.glob("*.py"):
        first_line = script.read_text().split("\n")[0]
        test(f"{skill}/{script.name}: has uv shebang",
             first_line == "#!/usr/bin/env -S uv run --script")

# ============================================================================
# Test: Script PEP 723 metadata
# ============================================================================
print("\n\033[1m=== Script PEP 723 Metadata ===\033[0m")

for skill in EXPECTED_SKILLS:
    scripts_dir = SKILLS_DIR / skill / "scripts"
    if not scripts_dir.is_dir():
        continue
    for script in scripts_dir.glob("*.py"):
        content = script.read_text()
        test(f"{skill}/{script.name}: has PEP 723 script metadata",
             "# /// script" in content and "# ///" in content)
        test(f"{skill}/{script.name}: declares requires-python",
             "requires-python" in content)

# ============================================================================
# Test: Config directory consistency
# ============================================================================
print("\n\033[1m=== Config Directory Consistency ===\033[0m")

for skill in EXPECTED_SKILLS:
    skill_md = SKILLS_DIR / skill / "SKILL.md"
    if not skill_md.is_file():
        continue
    content = skill_md.read_text()
    # Check that skills reference their own config dir, not another skill's
    if skill == "sydney-traffic":
        # Traffic should use its own config dir, not commute's
        test(f"{skill}: uses own config directory",
             "~/.config/sydney-traffic/" in content or "sydney-traffic" in content,
             "references ~/.config/sydney-commute/ instead of its own directory")

# ============================================================================
# Test: Evals exist
# ============================================================================
print("\n\033[1m=== Eval Test Cases ===\033[0m")

for skill in EXPECTED_SKILLS:
    evals_file = SKILLS_DIR / skill / "evals" / "evals.json"
    test(f"{skill}: has evals/evals.json", evals_file.is_file())
    if evals_file.is_file():
        try:
            data = json.loads(evals_file.read_text())
            test(f"{skill}: evals.json has skill_name", "skill_name" in data)
            test(f"{skill}: evals.json has ≥1 eval case",
                 len(data.get("evals", [])) >= 1)
            for i, ev in enumerate(data.get("evals", [])):
                test(f"{skill}: eval[{i}] has prompt", "prompt" in ev)
                test(f"{skill}: eval[{i}] has expected_output", "expected_output" in ev)
        except json.JSONDecodeError:
            test(f"{skill}: evals.json is valid JSON", False, "parse error")

# ============================================================================
# Test: plugin.json validity
# ============================================================================
print("\n\033[1m=== Plugin Configuration ===\033[0m")

plugin_path = REPO_ROOT / ".claude-plugin" / "plugin.json"
if plugin_path.is_file():
    plugin = json.loads(plugin_path.read_text())
    test("plugin.json has name", "name" in plugin)
    test("plugin.json has description", "description" in plugin)
    test("plugin.json has version", "version" in plugin)
    test("plugin.json has repository", "repository" in plugin)
    # Check all skill names appear as keywords
    for skill in EXPECTED_SKILLS:
        test(f"plugin.json keywords include '{skill}' related term",
             any(skill.replace("-", "") in kw.replace("-", "") for kw in plugin.get("keywords", [])) or
             any(part in " ".join(plugin.get("keywords", [])) for part in skill.split("-")))

# ============================================================================
# Test: SKILL.md uses ${CLAUDE_SKILL_DIR} variable
# ============================================================================
print("\n\033[1m=== CLAUDE_SKILL_DIR Usage ===\033[0m")

for skill in EXPECTED_SKILLS:
    skill_md = SKILLS_DIR / skill / "SKILL.md"
    if not skill_md.is_file():
        continue
    content = skill_md.read_text()
    test(f"{skill}: uses ${{CLAUDE_SKILL_DIR}} in command template",
         "${CLAUDE_SKILL_DIR}" in content)

# ============================================================================
# Summary
# ============================================================================
print(f"\n\033[1m{'='*60}\033[0m")
print(f"\033[1mResults: \033[32m{passed} passed\033[0m, \033[31m{failed} failed\033[0m")
if errors:
    print(f"\n\033[31mFailed tests:\033[0m")
    for e in errors:
        print(f"  • {e}")
print(f"\033[1m{'='*60}\033[0m")

sys.exit(1 if failed else 0)
