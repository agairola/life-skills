#!/usr/bin/env python3
"""
Script execution tests for life-skills.

Tests that all Python scripts:
1. Parse successfully (no syntax errors)
2. Respond to --help
3. Produce valid JSON output when run with embedded/offline data
4. Handle invalid arguments gracefully

Scripts with embedded data (dam-levels, speed-cameras, sydney-tolls, rental-prices)
get full integration tests. Network-dependent scripts get --help and syntax checks.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / "skills"

# Script paths mapped by skill name
SCRIPTS = {
    "air-quality": SKILLS_DIR / "air-quality" / "scripts" / "air_quality.py",
    "beach-check": SKILLS_DIR / "beach-check" / "scripts" / "beach_check.py",
    "dam-levels": SKILLS_DIR / "dam-levels" / "scripts" / "dam_levels.py",
    "fuel-pricing": SKILLS_DIR / "fuel-pricing" / "scripts" / "fuel_prices.py",
    "park-alerts": SKILLS_DIR / "park-alerts" / "scripts" / "park_alerts.py",
    "rental-prices": SKILLS_DIR / "rental-prices" / "scripts" / "rental_prices.py",
    "speed-cameras": SKILLS_DIR / "speed-cameras" / "scripts" / "speed_cameras.py",
    "sydney-commute": SKILLS_DIR / "sydney-commute" / "scripts" / "commute.py",
    "sydney-tolls": SKILLS_DIR / "sydney-tolls" / "scripts" / "tolls.py",
    "sydney-traffic": SKILLS_DIR / "sydney-traffic" / "scripts" / "traffic.py",
    "uv-sun": SKILLS_DIR / "uv-sun" / "scripts" / "uv_sun.py",
}

# Scripts that work fully offline with embedded data
OFFLINE_SCRIPTS = ["dam-levels", "speed-cameras", "sydney-tolls", "rental-prices"]

TIMEOUT = 120  # seconds — uv needs time to install deps on first run

passed = 0
failed = 0
skipped = 0
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


def skip(name, reason=""):
    global skipped
    skipped += 1
    detail = f" — {reason}" if reason else ""
    print(f"  \033[33m⊘\033[0m {name}{detail}")


def run_script(script_path, args=None, timeout=TIMEOUT):
    """Run a script with uv and return (returncode, stdout, stderr)."""
    cmd = ["uv", "run", "--script", str(script_path)]
    if args:
        cmd.extend(args)
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**os.environ, "NO_COLOR": "1"},
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "TIMEOUT"
    except Exception as e:
        return -1, "", str(e)


def check_uv_available():
    """Check if uv is installed."""
    try:
        result = subprocess.run(["uv", "--version"], capture_output=True, text=True, timeout=10)
        return result.returncode == 0
    except Exception:
        return False


# ============================================================================
# Pre-flight check
# ============================================================================
print("\n\033[1m=== Pre-flight Check ===\033[0m")

uv_available = check_uv_available()
test("uv is installed", uv_available)
if not uv_available:
    print("\033[31mFATAL: uv is not installed. Cannot run script execution tests.\033[0m")
    sys.exit(1)

# ============================================================================
# Test: Python syntax check (all scripts)
# ============================================================================
print("\n\033[1m=== Python Syntax Check ===\033[0m")

for skill, script in SCRIPTS.items():
    try:
        result = subprocess.run(
            [sys.executable, "-m", "py_compile", str(script)],
            capture_output=True, text=True, timeout=10,
        )
        test(f"{skill}: {script.name} compiles without syntax errors",
             result.returncode == 0,
             result.stderr.strip() if result.returncode != 0 else "")
    except Exception as e:
        test(f"{skill}: {script.name} compiles without syntax errors", False, str(e))

# ============================================================================
# Test: --help flag (all scripts)
# ============================================================================
print("\n\033[1m=== --help Flag ===\033[0m")

for skill, script in SCRIPTS.items():
    rc, stdout, stderr = run_script(script, ["--help"])
    test(f"{skill}: --help exits 0", rc == 0,
         f"exit code {rc}, stderr: {stderr[:200]}")
    test(f"{skill}: --help shows usage",
         "usage:" in stdout.lower() or "options:" in stdout.lower(),
         f"stdout: {stdout[:200]}")

# ============================================================================
# Test: Invalid argument handling (all scripts)
# ============================================================================
print("\n\033[1m=== Invalid Argument Handling ===\033[0m")

for skill, script in SCRIPTS.items():
    rc, stdout, stderr = run_script(script, ["--nonexistent-flag-xyz"])
    test(f"{skill}: rejects unknown flags (exit ≠ 0)", rc != 0,
         f"exit code {rc} — should have failed")

# ============================================================================
# Test: Offline execution with embedded data
# ============================================================================
print("\n\033[1m=== Offline Execution (Embedded Data) ===\033[0m")

# --- dam-levels: runs fully offline with fallback data ---
print("\n  \033[1m— dam-levels —\033[0m")
rc, stdout, stderr = run_script(SCRIPTS["dam-levels"], ["--dam", "Warragamba"])
test("dam-levels: exits 0 with --dam Warragamba", rc == 0,
     f"exit code {rc}, stderr: {stderr[:300]}")
if rc == 0 and stdout.strip():
    try:
        data = json.loads(stdout)
        test("dam-levels: output is valid JSON", True)
        test("dam-levels: has 'dams' key", "dams" in data)
        if "dams" in data:
            test("dam-levels: has at least 1 dam", len(data["dams"]) >= 1)
            dam = data["dams"][0]
            test("dam-levels: dam has 'name'", "name" in dam)
            test("dam-levels: dam has 'capacity_pct'", "capacity_pct" in dam)
            test("dam-levels: dam name contains 'Warragamba'",
                 "warragamba" in dam.get("name", "").lower())
            test("dam-levels: capacity_pct is a number",
                 isinstance(dam.get("capacity_pct"), (int, float)))
            test("dam-levels: capacity_pct in range 0-100",
                 0 <= dam.get("capacity_pct", -1) <= 100)
    except json.JSONDecodeError as e:
        test("dam-levels: output is valid JSON", False, str(e))
else:
    skip("dam-levels: JSON validation", "script did not produce output")

# dam-levels: all dams
rc, stdout, stderr = run_script(SCRIPTS["dam-levels"], ["--all"])
test("dam-levels: --all exits 0", rc == 0,
     f"exit code {rc}, stderr: {stderr[:300]}")
if rc == 0 and stdout.strip():
    try:
        data = json.loads(stdout)
        test("dam-levels: --all output is valid JSON", True)
        test("dam-levels: --all has multiple dams",
             len(data.get("dams", [])) >= 5,
             f"got {len(data.get('dams', []))} dams")
        test("dam-levels: --all has total_system",
             "total_system" in data or "total" in str(data).lower())
    except json.JSONDecodeError as e:
        test("dam-levels: --all output is valid JSON", False, str(e))
else:
    skip("dam-levels: --all JSON validation", "script did not produce output")

# --- sydney-tolls: fully embedded toll database ---
print("\n  \033[1m— sydney-tolls —\033[0m")
rc, stdout, stderr = run_script(SCRIPTS["sydney-tolls"], ["--road", "M2"])
test("sydney-tolls: exits 0 with --road M2", rc == 0,
     f"exit code {rc}, stderr: {stderr[:300]}")
if rc == 0 and stdout.strip():
    try:
        data = json.loads(stdout)
        test("sydney-tolls: output is valid JSON", True)
        has_roads = "toll_roads" in data or "roads" in data or "results" in data
        test("sydney-tolls: has toll road data", has_roads,
             f"keys: {list(data.keys())}")
    except json.JSONDecodeError as e:
        test("sydney-tolls: output is valid JSON", False, str(e))
else:
    skip("sydney-tolls: JSON validation", "script did not produce output")

# sydney-tolls: all roads
rc, stdout, stderr = run_script(SCRIPTS["sydney-tolls"], ["--all"])
test("sydney-tolls: --all exits 0", rc == 0,
     f"exit code {rc}, stderr: {stderr[:300]}")
if rc == 0 and stdout.strip():
    try:
        data = json.loads(stdout)
        test("sydney-tolls: --all output is valid JSON", True)
        # Check we get multiple toll roads (may be nested under results)
        results = data.get("results", data)
        roads = results.get("toll_roads", results.get("roads", []))
        if not isinstance(roads, list):
            roads = data.get("toll_roads", data.get("roads", []))
        test("sydney-tolls: --all has multiple toll roads",
             isinstance(roads, list) and len(roads) >= 10,
             f"got {len(roads) if isinstance(roads, list) else 'non-list'}")
    except json.JSONDecodeError as e:
        test("sydney-tolls: --all output is valid JSON", False, str(e))
else:
    skip("sydney-tolls: --all JSON validation", "script did not produce output")

# sydney-tolls: vehicle type
rc, stdout, stderr = run_script(SCRIPTS["sydney-tolls"], ["--road", "Harbour Bridge", "--vehicle", "motorcycle"])
test("sydney-tolls: exits 0 with --vehicle motorcycle", rc == 0,
     f"exit code {rc}, stderr: {stderr[:300]}")
if rc == 0 and stdout.strip():
    try:
        data = json.loads(stdout)
        test("sydney-tolls: motorcycle output is valid JSON", True)
    except json.JSONDecodeError as e:
        test("sydney-tolls: motorcycle output is valid JSON", False, str(e))

# --- rental-prices: fully embedded rental data ---
print("\n  \033[1m— rental-prices —\033[0m")
rc, stdout, stderr = run_script(SCRIPTS["rental-prices"], ["--suburb", "Newtown"])
test("rental-prices: exits 0 with --suburb Newtown", rc == 0,
     f"exit code {rc}, stderr: {stderr[:300]}")
if rc == 0 and stdout.strip():
    try:
        data = json.loads(stdout)
        test("rental-prices: output is valid JSON", True)
        has_results = "results" in data or "suburbs" in data or "rents" in data
        test("rental-prices: has result data", has_results,
             f"keys: {list(data.keys())}")
    except json.JSONDecodeError as e:
        test("rental-prices: output is valid JSON", False, str(e))
else:
    skip("rental-prices: JSON validation", "script did not produce output")

# rental-prices: budget search
rc, stdout, stderr = run_script(SCRIPTS["rental-prices"], ["--budget", "500", "--type", "unit", "--bedrooms", "2"])
test("rental-prices: exits 0 with --budget 500", rc == 0,
     f"exit code {rc}, stderr: {stderr[:300]}")
if rc == 0 and stdout.strip():
    try:
        data = json.loads(stdout)
        test("rental-prices: budget output is valid JSON", True)
    except json.JSONDecodeError as e:
        test("rental-prices: budget output is valid JSON", False, str(e))

# rental-prices: postcode search
rc, stdout, stderr = run_script(SCRIPTS["rental-prices"], ["--postcode", "2042"])
test("rental-prices: exits 0 with --postcode 2042", rc == 0,
     f"exit code {rc}, stderr: {stderr[:300]}")
if rc == 0 and stdout.strip():
    try:
        data = json.loads(stdout)
        test("rental-prices: postcode output is valid JSON", True)
    except json.JSONDecodeError as e:
        test("rental-prices: postcode output is valid JSON", False, str(e))

# --- speed-cameras: embedded camera database ---
print("\n  \033[1m— speed-cameras —\033[0m")
# speed-cameras needs lat/lng to avoid network geocoding
rc, stdout, stderr = run_script(SCRIPTS["speed-cameras"], ["--lat", "-33.87", "--lng", "151.08", "--radius", "10"])
test("speed-cameras: exits 0 with --lat/--lng", rc == 0,
     f"exit code {rc}, stderr: {stderr[:300]}")
if rc == 0 and stdout.strip():
    try:
        data = json.loads(stdout)
        test("speed-cameras: output is valid JSON", True)
        has_cameras = "cameras" in data or "results" in data
        test("speed-cameras: has camera data", has_cameras,
             f"keys: {list(data.keys())}")
        # cameras may be nested under results
        results = data.get("results", data)
        cameras = results.get("cameras", data.get("cameras", []))
        if isinstance(cameras, list) and len(cameras) > 0:
            cam = cameras[0]
            test("speed-cameras: camera has location fields",
                 "lat" in cam or "latitude" in cam or "road" in cam,
                 f"camera keys: {list(cam.keys())}")
            test("speed-cameras: camera has type",
                 "type" in cam or "camera_type" in cam,
                 f"camera keys: {list(cam.keys())}")
    except json.JSONDecodeError as e:
        test("speed-cameras: output is valid JSON", False, str(e))
else:
    skip("speed-cameras: JSON validation", "script did not produce output")

# speed-cameras: filter by type
rc, stdout, stderr = run_script(SCRIPTS["speed-cameras"], [
    "--lat", "-33.87", "--lng", "151.08", "--type", "red_light", "--radius", "50"
])
test("speed-cameras: exits 0 with --type red_light", rc == 0,
     f"exit code {rc}, stderr: {stderr[:300]}")
if rc == 0 and stdout.strip():
    try:
        data = json.loads(stdout)
        test("speed-cameras: type filter output is valid JSON", True)
    except json.JSONDecodeError as e:
        test("speed-cameras: type filter output is valid JSON", False, str(e))

# ============================================================================
# Test: Network-dependent scripts (zero-config/fallback mode)
# ============================================================================
print("\n\033[1m=== Network-Dependent Scripts (Fallback Mode) ===\033[0m")

# sydney-commute: should return fallback URLs without API key
print("\n  \033[1m— sydney-commute (no API key) —\033[0m")
rc, stdout, stderr = run_script(SCRIPTS["sydney-commute"],
    ["--from", "Central Station", "--to", "Bondi Junction"])
if rc == 0 and stdout.strip():
    try:
        data = json.loads(stdout)
        test("sydney-commute: output is valid JSON", True)
        # Without API key, should have fallback URLs
        raw = json.dumps(data).lower()
        has_fallback = ("google_maps" in raw or "transport_nsw" in raw or
                        "fallback" in raw or "api_key_configured" in raw or
                        "trips" in raw)
        test("sydney-commute: has trip data or fallback URLs", has_fallback,
             f"keys: {list(data.keys())}")
    except json.JSONDecodeError as e:
        test("sydney-commute: output is valid JSON", False, str(e))
elif rc == 0:
    skip("sydney-commute: JSON validation", "empty output")
else:
    # May fail due to network — that's OK, just log it
    skip("sydney-commute: execution", f"exit code {rc} (network may be unavailable)")

# sydney-traffic: should return fallback URLs without API key
print("\n  \033[1m— sydney-traffic (no API key) —\033[0m")
rc, stdout, stderr = run_script(SCRIPTS["sydney-traffic"],
    ["--location", "Sydney CBD"])
if rc == 0 and stdout.strip():
    try:
        data = json.loads(stdout)
        test("sydney-traffic: output is valid JSON", True)
        raw = json.dumps(data).lower()
        has_data = ("hazards" in raw or "fallback" in raw or
                    "api_key_configured" in raw or "livetraffic" in raw)
        test("sydney-traffic: has hazard data or fallback URLs", has_data,
             f"keys: {list(data.keys())}")
    except json.JSONDecodeError as e:
        test("sydney-traffic: output is valid JSON", False, str(e))
elif rc == 0:
    skip("sydney-traffic: JSON validation", "empty output")
else:
    skip("sydney-traffic: execution", f"exit code {rc} (network may be unavailable)")

# ============================================================================
# Summary
# ============================================================================
print(f"\n\033[1m{'='*60}\033[0m")
total = passed + failed
print(f"\033[1mResults: \033[32m{passed} passed\033[0m, \033[31m{failed} failed\033[0m, \033[33m{skipped} skipped\033[0m")
if errors:
    print(f"\n\033[31mFailed tests:\033[0m")
    for e in errors:
        print(f"  • {e}")
print(f"\033[1m{'='*60}\033[0m")

sys.exit(1 if failed else 0)
