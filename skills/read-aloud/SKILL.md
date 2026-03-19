---
name: read-aloud
description: >-
  Read markdown files, text files, or any document aloud using high-quality
  neural text-to-speech. Use this skill whenever the user asks to "read this
  aloud", "read this to me", "text to speech", "say this", "listen to this
  file", "convert to audio", "play this document", or wants to hear any text
  or file spoken. Also trigger when the user asks to generate an audio version
  of a document, wants to review content by listening, or mentions TTS. Zero
  configuration — auto-installs Kokoro TTS and downloads models on first run.
  Works on macOS and Linux with no API keys needed. Everything runs locally.
---

# Read Aloud Skill

Read any markdown or text file aloud using Kokoro TTS. Zero config — auto-installs on first use, no API keys, runs entirely locally.

## Install

```bash
npx skills add agairola/life-skills --skill read-aloud
```

## When to Use

Trigger this skill when the user:

- Asks to read a file aloud or "read this to me"
- Wants text-to-speech for a document
- Says "listen to this", "play this", "say this"
- Wants to convert text or markdown to audio
- Mentions TTS or text-to-speech
- Wants to review content by listening instead of reading
- Asks for an audio version of a document

## Prerequisites

- **uv** — `brew install uv` (macOS) or `pip install uv` (all platforms)
- **Kokoro TTS** — auto-installed on first run via `uv tool install kokoro-tts`
- **Models** — auto-downloaded on first run (~335MB total, stored in `~/.config/read-aloud/models/`)
- **API keys** — not needed. Everything runs locally.
- **Dependencies** — declared inline (PEP 723), installed automatically by `uv run`.

## Setup Status

!`command -v uv > /dev/null 2>&1 && echo "uv: installed" || echo "uv: NOT INSTALLED — run: brew install uv"`
!`command -v kokoro-tts > /dev/null 2>&1 && echo "kokoro-tts: installed" || echo "kokoro-tts: not installed (will auto-install on first use)"`
!`test -f ~/.config/read-aloud/models/kokoro-v1.0.onnx && echo "models: downloaded" || echo "models: not yet downloaded (will auto-download on first use, ~335MB)"`

## Command Template

```bash
uv run "${CLAUDE_SKILL_DIR}/scripts/read_aloud.py" <INPUT> [OPTIONS]
```

### Options

| Flag | Values | Default | Purpose |
|------|--------|---------|---------|
| `input` | file path or `-` | required | Path to .md or .txt file, or `-` for stdin |
| `--voice` | see voice list | `af_heart` | Voice to use |
| `--speed` | float | `1.0` | Speech speed (0.5 = slow, 1.5 = fast) |
| `--output` | file path | *(plays audio)* | Save to .wav file instead of playing |
| `--max-lines` | integer | `0` (all) | Only read the first N lines |
| `--max-time` | integer | `0` (no limit) | Stop playback after N seconds |
| `--no-play` | flag | off | Generate .wav without playing (use with `--output`) |
| `--list-voices` | flag | — | Print available voices as JSON and exit |

Only parse **stdout** (JSON). Stderr contains progress messages and diagnostics only.

### Common Commands

```bash
# Read a markdown file aloud
uv run "${CLAUDE_SKILL_DIR}/scripts/read_aloud.py" /path/to/document.md

# Use a male voice
uv run "${CLAUDE_SKILL_DIR}/scripts/read_aloud.py" /path/to/notes.md --voice am_adam

# Read faster
uv run "${CLAUDE_SKILL_DIR}/scripts/read_aloud.py" /path/to/doc.md --speed 1.3

# Save to file instead of playing
uv run "${CLAUDE_SKILL_DIR}/scripts/read_aloud.py" /path/to/doc.md --output ~/Desktop/speech.wav

# Read just the first 10 lines
uv run "${CLAUDE_SKILL_DIR}/scripts/read_aloud.py" /path/to/doc.md --max-lines 10

# Stop after 60 seconds
uv run "${CLAUDE_SKILL_DIR}/scripts/read_aloud.py" /path/to/doc.md --max-time 60

# Read from stdin
echo "Hello, this is a test" | uv run "${CLAUDE_SKILL_DIR}/scripts/read_aloud.py" -

# List available voices
uv run "${CLAUDE_SKILL_DIR}/scripts/read_aloud.py" --list-voices
```

## Presenting Results

### After Streaming Audio

The default mode streams audio — playback starts within seconds even for large files. Confirm and offer follow-up:

```
Reading "document.md" aloud (Heart voice, 1.0x speed).

Want me to:
- Read it again with a different voice?
- Save it as a .wav file? (use --output)
- Read a specific section?
```

### After Saving to File

When the user explicitly asks to save audio (using `--output`):

```
Saved audio to ~/Desktop/speech.wav (Heart voice, 1.0x speed, ~45 seconds).
```

### First Run

On first use, the setup takes 1-2 minutes (installing kokoro-tts + downloading ~335MB of models). Let the user know:

```
Setting up text-to-speech for the first time (downloading voice models, ~335MB). This only happens once.
```

After the first run, subsequent reads start in seconds.

## Handling Edge Cases

- **First run (no kokoro-tts, no models):** The script auto-installs everything. Tell the user it's a one-time setup taking 1-2 minutes.
- **Large files:** Kokoro processes in chunks. For very large files (>50KB of text), warn the user it may take a moment to generate.
- **No audio player (headless/remote):** The script auto-saves to a .wav file in the current directory and returns the path. Tell the user where the file is.
- **Unsupported file types:** The script reads any text file. For non-text files, suggest converting first.
- **Empty content:** If markdown stripping removes all content (e.g., a file with only code blocks), the script returns an error. Suggest the user try with a different file or pass specific text via stdin.
- **Chat platforms (Telegram, WhatsApp, etc.):** Audio playback only works in terminal environments. On chat platforms, use `--output` to save the file and tell the user where to find it.

## Voice Reference

### American English

| Voice ID | Name | Gender |
|----------|------|--------|
| `af_alloy` | Alloy | Female |
| `af_aoede` | Aoede | Female |
| `af_bella` | Bella | Female |
| **`af_heart`** | **Heart (default)** | **Female** |
| `af_jessica` | Jessica | Female |
| `af_kore` | Kore | Female |
| `af_nicole` | Nicole | Female |
| `af_nova` | Nova | Female |
| `af_river` | River | Female |
| `af_sarah` | Sarah | Female |
| `af_sky` | Sky | Female |
| `am_adam` | Adam | Male |
| `am_michael` | Michael | Male |

### British English

| Voice ID | Name | Gender |
|----------|------|--------|
| `bf_emma` | Emma | Female |
| `bf_isabella` | Isabella | Female |
| `bm_george` | George | Male |
| `bm_lewis` | Lewis | Male |
