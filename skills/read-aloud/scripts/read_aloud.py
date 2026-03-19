#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "httpx>=0.27.0",
# ]
# ///
"""
Read Aloud — text-to-speech for markdown and text files using Kokoro TTS.

Zero-config: auto-installs Kokoro TTS and downloads models on first run.
Uses high-quality neural voices that run locally — no API keys, no cloud.

Usage:
    uv run read_aloud.py document.md                    # read markdown aloud
    uv run read_aloud.py notes.txt --voice am_michael   # male voice
    uv run read_aloud.py doc.md --speed 1.2             # faster
    uv run read_aloud.py doc.md --output speech.wav     # save to file
    echo "Hello world" | uv run read_aloud.py -         # read from stdin
    uv run read_aloud.py --list-voices                  # show available voices
"""

import argparse
import json
import os
import platform
import re
import signal
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

CONFIG_DIR = Path.home() / ".config" / "read-aloud"
MODELS_DIR = CONFIG_DIR / "models"
MODEL_FILE = MODELS_DIR / "kokoro-v1.0.onnx"
VOICES_FILE = MODELS_DIR / "voices-v1.0.bin"

MODEL_URL = "https://github.com/nazdridoy/kokoro-tts/releases/download/v1.0.0/kokoro-v1.0.onnx"
VOICES_URL = "https://github.com/nazdridoy/kokoro-tts/releases/download/v1.0.0/voices-v1.0.bin"

VOICES = {
    # American English — Female
    "af_alloy": "Alloy (American female)",
    "af_aoede": "Aoede (American female)",
    "af_bella": "Bella (American female)",
    "af_heart": "Heart (American female, default)",
    "af_jessica": "Jessica (American female)",
    "af_kore": "Kore (American female)",
    "af_nicole": "Nicole (American female)",
    "af_nova": "Nova (American female)",
    "af_river": "River (American female)",
    "af_sarah": "Sarah (American female)",
    "af_sky": "Sky (American female)",
    # American English — Male
    "am_adam": "Adam (American male)",
    "am_michael": "Michael (American male)",
    # British English — Female
    "bf_emma": "Emma (British female)",
    "bf_isabella": "Isabella (British female)",
    # British English — Male
    "bm_george": "George (British male)",
    "bm_lewis": "Lewis (British male)",
}

DEFAULT_VOICE = "af_heart"
DEFAULT_SPEED = 1.0


# ---------------------------------------------------------------------------
# Auto-setup
# ---------------------------------------------------------------------------

def ensure_kokoro_installed() -> str:
    """Ensure kokoro-tts CLI is installed. Returns path to executable."""
    kokoro_path = shutil.which("kokoro-tts")
    if kokoro_path:
        return kokoro_path

    print("Installing kokoro-tts (first-time setup)...", file=sys.stderr)
    result = subprocess.run(
        ["uv", "tool", "install", "kokoro-tts"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        # May already be installed but not on PATH yet
        if "already installed" in result.stderr.lower():
            pass
        else:
            print(f"Failed to install kokoro-tts: {result.stderr}", file=sys.stderr)
            sys.exit(1)

    # Re-check PATH after install
    kokoro_path = shutil.which("kokoro-tts")
    if not kokoro_path:
        # Try common uv tool locations
        candidates = [
            Path.home() / ".local" / "bin" / "kokoro-tts",
            Path.home() / ".cargo" / "bin" / "kokoro-tts",
        ]
        for c in candidates:
            if c.exists():
                kokoro_path = str(c)
                break

    if not kokoro_path:
        print("kokoro-tts installed but not found on PATH. Try restarting your shell.", file=sys.stderr)
        sys.exit(1)

    print("kokoro-tts installed successfully.", file=sys.stderr)
    return kokoro_path


def ensure_models_downloaded():
    """Download model and voice files if not present."""
    if MODEL_FILE.exists() and VOICES_FILE.exists():
        return

    import httpx

    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    downloads = []
    if not MODEL_FILE.exists():
        downloads.append((MODEL_URL, MODEL_FILE, "kokoro-v1.0.onnx (~310MB)"))
    if not VOICES_FILE.exists():
        downloads.append((VOICES_URL, VOICES_FILE, "voices-v1.0.bin (~25MB)"))

    for url, dest, label in downloads:
        print(f"Downloading {label}...", file=sys.stderr)
        with httpx.stream("GET", url, follow_redirects=True, timeout=300) as resp:
            resp.raise_for_status()
            total = int(resp.headers.get("content-length", 0))
            downloaded = 0
            with open(dest, "wb") as f:
                for chunk in resp.iter_bytes(chunk_size=1024 * 1024):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total:
                        pct = downloaded * 100 // total
                        print(f"\r  {pct}% ({downloaded // (1024*1024)}MB / {total // (1024*1024)}MB)", end="", file=sys.stderr)
            print(file=sys.stderr)

    print("Models ready.", file=sys.stderr)


# ---------------------------------------------------------------------------
# Markdown stripping
# ---------------------------------------------------------------------------

def strip_markdown(text: str) -> str:
    """Convert markdown to clean text suitable for TTS."""
    # Remove YAML frontmatter
    text = re.sub(r"^---\s*\n.*?\n---\s*\n", "", text, count=1, flags=re.DOTALL)

    # Remove code fences and their content
    text = re.sub(r"```[^\n]*\n.*?```", "", text, flags=re.DOTALL)

    # Remove inline code
    text = re.sub(r"`([^`]+)`", r"\1", text)

    # Remove HTML tags
    text = re.sub(r"<[^>]+>", "", text)

    # Remove HTML comments
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)

    # Convert headers to sentences (add period if not already punctuated)
    def header_to_sentence(m):
        title = m.group(2).strip()
        if title and title[-1] not in ".!?:":
            return f"{title}.\n\n"
        return f"{title}\n\n"
    text = re.sub(r"^(#{1,6})\s+(.+)$", header_to_sentence, text, flags=re.MULTILINE)

    # Convert links [text](url) to just text
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)

    # Convert wiki links [[text]] or [[text|display]]
    text = re.sub(r"\[\[([^|\]]+)\|([^\]]+)\]\]", r"\2", text)
    text = re.sub(r"\[\[([^\]]+)\]\]", r"\1", text)

    # Remove images ![alt](url)
    text = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", text)

    # Remove bold and italic markers
    text = re.sub(r"\*\*\*(.+?)\*\*\*", r"\1", text)
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"___(.+?)___", r"\1", text)
    text = re.sub(r"__(.+?)__", r"\1", text)
    text = re.sub(r"_(.+?)_", r"\1", text)

    # Remove strikethrough
    text = re.sub(r"~~(.+?)~~", r"\1", text)

    # Remove highlight markers
    text = re.sub(r"==(.+?)==", r"\1", text)

    # Convert blockquotes
    text = re.sub(r"^>\s*", "", text, flags=re.MULTILINE)

    # Remove Obsidian callout markers
    text = re.sub(r"^>\s*\[![^\]]*\].*$", "", text, flags=re.MULTILINE)

    # Convert unordered list items to sentences
    text = re.sub(r"^\s*[-*+]\s+", "", text, flags=re.MULTILINE)

    # Convert ordered list items
    text = re.sub(r"^\s*\d+\.\s+", "", text, flags=re.MULTILINE)

    # Convert markdown tables to readable text
    # Remove separator rows (|---|---|)
    text = re.sub(r"^\|[-:\s|]+\|$", "", text, flags=re.MULTILINE)
    # Convert table rows: | a | b | c | → a, b, c
    def table_row_to_text(m):
        cells = [c.strip() for c in m.group(0).strip("|").split("|") if c.strip()]
        return ", ".join(cells) + "."
    text = re.sub(r"^\|.+\|$", table_row_to_text, text, flags=re.MULTILINE)

    # Remove horizontal rules
    text = re.sub(r"^[-*_]{3,}\s*$", "", text, flags=re.MULTILINE)

    # Remove task list markers
    text = re.sub(r"\[[ x]\]\s*", "", text)

    # Collapse multiple blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


# ---------------------------------------------------------------------------
# Playback
# ---------------------------------------------------------------------------

def get_audio_player() -> list[str] | None:
    """Return the system audio player command, or None."""
    system = platform.system()
    if system == "Darwin":
        if shutil.which("afplay"):
            return ["afplay"]
    elif system == "Linux":
        for player in ["aplay", "paplay", "mpv", "ffplay"]:
            if shutil.which(player):
                if player == "ffplay":
                    return ["ffplay", "-nodisp", "-autoexit"]
                return [player]
    return None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Read markdown and text files aloud using Kokoro TTS.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "input",
        nargs="?",
        help="Path to .md or .txt file, or '-' for stdin",
    )
    parser.add_argument(
        "--voice",
        default=DEFAULT_VOICE,
        help=f"Voice to use (default: {DEFAULT_VOICE}). Use --list-voices to see options.",
    )
    parser.add_argument(
        "--speed",
        type=float,
        default=DEFAULT_SPEED,
        help=f"Speech speed multiplier (default: {DEFAULT_SPEED})",
    )
    parser.add_argument(
        "--output",
        help="Save audio to this file instead of playing",
    )
    parser.add_argument(
        "--no-play",
        action="store_true",
        help="Generate audio file but don't play it",
    )
    parser.add_argument(
        "--max-lines",
        type=int,
        default=0,
        help="Only read the first N lines (0 = all)",
    )
    parser.add_argument(
        "--max-time",
        type=int,
        default=0,
        help="Stop after N seconds (0 = no limit)",
    )
    parser.add_argument(
        "--list-voices",
        action="store_true",
        help="List available voices and exit",
    )

    args = parser.parse_args()

    # List voices
    if args.list_voices:
        voice_list = [{"id": k, "description": v} for k, v in VOICES.items()]
        json.dump({"voices": voice_list}, sys.stdout, indent=2)
        print()
        return

    # Validate input
    if not args.input:
        parser.error("input file is required (use '-' for stdin)")

    # Read input
    if args.input == "-":
        text = sys.stdin.read()
        input_name = "stdin"
    else:
        input_path = Path(args.input).expanduser()
        if not input_path.exists():
            print(json.dumps({"error": f"File not found: {args.input}"}))
            sys.exit(1)
        text = input_path.read_text(encoding="utf-8")
        input_name = input_path.name

    # Strip markdown if it looks like markdown
    if input_name.endswith(".md") or args.input == "-":
        clean_text = strip_markdown(text)
    else:
        clean_text = text

    if not clean_text.strip():
        print(json.dumps({"error": "No readable text found in file"}))
        sys.exit(1)

    # Apply line limit
    if args.max_lines > 0:
        lines = clean_text.splitlines()
        clean_text = "\n".join(lines[:args.max_lines])

    # Validate voice
    if args.voice not in VOICES:
        print(json.dumps({
            "error": f"Unknown voice: {args.voice}",
            "available": list(VOICES.keys()),
        }))
        sys.exit(1)

    # Ensure kokoro-tts is installed and models are downloaded
    kokoro_path = ensure_kokoro_installed()
    ensure_models_downloaded()

    # Write cleaned text to temp file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as tmp_in:
        tmp_in.write(clean_text)
        tmp_input = tmp_in.name

    try:
        if args.output or args.no_play:
            # Save mode: generate full wav file
            wav_path = str(Path(args.output).expanduser()) if args.output else str(
                Path.cwd() / f"{Path(input_name).stem}_speech.wav"
            )

            cmd = [
                kokoro_path,
                tmp_input,
                wav_path,
                "--model", str(MODEL_FILE),
                "--voices", str(VOICES_FILE),
                "--voice", args.voice,
                "--speed", str(args.speed),
            ]

            print(f"Generating speech ({args.voice}, {args.speed}x)...", file=sys.stderr)
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                print(json.dumps({"error": f"kokoro-tts failed: {result.stderr.strip()}"}))
                sys.exit(1)

            wav_size = os.path.getsize(wav_path)
            duration_seconds = round(wav_size / 48000, 1)

            print(json.dumps({
                "status": "ok",
                "action": "saved" if args.output else "generated",
                "file": wav_path,
                "voice": args.voice,
                "speed": args.speed,
                "duration_seconds": duration_seconds,
                "input": input_name,
            }))
        else:
            # Stream mode: play audio as it generates (no waiting)
            cmd = [
                kokoro_path,
                tmp_input,
                "--stream",
                "--model", str(MODEL_FILE),
                "--voices", str(VOICES_FILE),
                "--voice", args.voice,
                "--speed", str(args.speed),
            ]

            print(f"Streaming speech ({args.voice}, {args.speed}x)...", file=sys.stderr)
            if args.max_time > 0:
                print(f"Will stop after {args.max_time} seconds.", file=sys.stderr)

            stopped_early = False
            proc = subprocess.Popen(cmd, stderr=subprocess.PIPE)

            try:
                timeout = args.max_time if args.max_time > 0 else None
                proc.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                stopped_early = True
                print(f"\nStopped after {args.max_time} seconds.", file=sys.stderr)
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()
            except KeyboardInterrupt:
                stopped_early = True
                print("\nStopped.", file=sys.stderr)
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()

            if proc.returncode not in (0, None, -signal.SIGTERM):
                if not stopped_early:
                    print(json.dumps({"error": "kokoro-tts streaming failed"}))
                    sys.exit(1)

            print(json.dumps({
                "status": "ok",
                "action": "stopped" if stopped_early else "streamed",
                "voice": args.voice,
                "speed": args.speed,
                "input": input_name,
                **({"stopped_after_seconds": args.max_time} if stopped_early and args.max_time > 0 else {}),
            }))

    finally:
        try:
            os.unlink(tmp_input)
        except OSError:
            pass


if __name__ == "__main__":
    main()
