---
name: transcribe
description: >-
  Transcribe audio or video files to text using OpenAI Whisper running entirely
  locally. Use this skill whenever the user asks to "transcribe", "get a
  transcript", "convert audio to text", "speech to text", "STT", or asks what
  someone said in an audio or video file. Also trigger when the user mentions
  Whisper, subtitles, captions, SRT, or VTT for a local media file. Supports
  common formats (mp3, m4a, wav, mp4, mov, flac, ogg, webm). Zero configuration
  — auto-installs Whisper on first run and downloads models automatically. Uses
  MLX acceleration on Apple Silicon for maximum speed; falls back to
  faster-whisper (CPU) on Intel Macs and Linux. No API keys, no cloud.
allowed-tools: Bash(uv run *), Read, Write
argument-hint: "[audio/video file path]"
---

# Transcribe Skill

Transcribe audio or video to text using OpenAI Whisper locally. Zero config, no API keys, no cloud.

## Install

```bash
npx skills add agairola/life-skills --skill transcribe
```

## When to Use

Trigger this skill when the user:

- Asks to transcribe an audio or video file
- Says "what did they say in this file", "get a transcript", "convert this to text"
- Mentions speech-to-text, STT, or Whisper
- Wants subtitles, captions, SRT, or VTT from a media file
- Provides a path or URL to an audio/video file and wants the spoken content

## Prerequisites

- **uv** — `brew install uv` (macOS) or `pip install uv`
- **ffmpeg** — only needed on Apple Silicon (MLX engine). `brew install ffmpeg`. The script auto-falls back to the CPU engine (no ffmpeg needed) if ffmpeg is missing.
- **Models** — auto-downloaded on first run (~800MB for the default `large-v3-turbo`, cached in `~/.cache/huggingface/`).
- **API keys** — none.
- **Dependencies** — declared inline (PEP 723), installed by `uv run`.

## Setup Status

!`command -v uv > /dev/null 2>&1 && echo "uv: installed" || echo "uv: NOT INSTALLED — run: brew install uv"`
!`command -v ffmpeg > /dev/null 2>&1 && echo "ffmpeg: installed (MLX engine available on Apple Silicon)" || echo "ffmpeg: not installed (will use CPU engine fallback; for best speed on Apple Silicon run: brew install ffmpeg)"`

## Command Template

```bash
uv run "${CLAUDE_SKILL_DIR}/scripts/transcribe.py" <INPUT> [OPTIONS]
```

### Options

| Flag | Values | Default | Purpose |
|------|--------|---------|---------|
| `input` | file path | required | Path to audio/video file |
| `--model` | tiny, base, small, medium, large-v3, large-v3-turbo, turbo | `large-v3-turbo` | Whisper model. `turbo` is the accuracy/speed sweet spot. |
| `--language` | ISO code (en, fr, de, …) or `auto` | `auto` | Spoken language. Auto-detect is reliable but slower. |
| `--format` | txt, srt, vtt, json | `txt` | Output format. `json` includes per-segment timestamps. |
| `--output` | file path | *(stdout)* | Write transcript to file instead of stdout. |
| `--word-timestamps` | flag | off | Include word-level timing (JSON format only). |
| `--engine` | auto, mlx, faster | `auto` | Force an engine. `auto` picks MLX on Apple Silicon, faster-whisper elsewhere. |
| `--translate` | flag | off | Translate to English instead of transcribing in source language. |
| `--json-summary` | flag | off | Print a JSON summary to stdout with file path + stats. |

The default prints the plain transcript to stdout. Use `--output` to save it, or `--json-summary` for structured metadata the agent can parse.

### Common Commands

```bash
# Transcribe an audio file (prints plain text)
uv run "${CLAUDE_SKILL_DIR}/scripts/transcribe.py" ~/Downloads/meeting.m4a

# Save as SRT subtitles
uv run "${CLAUDE_SKILL_DIR}/scripts/transcribe.py" video.mp4 --format srt --output video.srt

# Fast preview with a smaller model
uv run "${CLAUDE_SKILL_DIR}/scripts/transcribe.py" interview.mp3 --model small

# Transcribe a non-English file with explicit language
uv run "${CLAUDE_SKILL_DIR}/scripts/transcribe.py" hindi.m4a --language hi

# Translate any language to English
uv run "${CLAUDE_SKILL_DIR}/scripts/transcribe.py" french.mp3 --translate

# JSON with per-segment timestamps (for further processing)
uv run "${CLAUDE_SKILL_DIR}/scripts/transcribe.py" lecture.mp3 --format json --output lecture.json

# JSON summary to stdout (file path, duration, word count)
uv run "${CLAUDE_SKILL_DIR}/scripts/transcribe.py" clip.wav --output clip.txt --json-summary
```

## Presenting Results

Follow the shared formatting rules in [../../references/platform-formatting.md](../../references/platform-formatting.md) when showing the transcript in chat platforms (no markdown tables, end with a follow-up prompt).

### Short transcripts (< ~1000 words)

Show the transcript inline:

```
Here's the transcript of meeting.m4a (3m 24s, English, large-v3-turbo):

[transcript body]

Want me to save it as SRT/VTT subtitles, or translate to another language?
```

### Long transcripts

Save to file and show a preview:

```
Transcribed lecture.mp3 (47m, English). Saved full transcript to lecture.txt.

Preview:
[first ~200 words]

Want me to summarize it, extract key points, or generate subtitles?
```

### With timestamps (SRT / VTT)

Save to file and confirm:

```
Generated SRT subtitles for video.mp4 (12 segments). Saved to video.srt.
```

## Handling Edge Cases

- **First run (no models):** The default model (`large-v3-turbo`, ~800MB) auto-downloads. Tell the user "Downloading the Whisper model (~800MB), this is a one-time setup." Subsequent runs start in seconds.
- **ffmpeg missing on Apple Silicon:** The script auto-falls back to faster-whisper (CPU). Mention this and suggest `brew install ffmpeg` for faster transcription next time.
- **Very large files (> 1 hour):** Warn the user transcription may take several minutes. `large-v3-turbo` on MLX processes ~10 min audio in under a minute on M-series; on CPU expect roughly real-time.
- **Unsupported format:** If ffmpeg is present, most formats work (mp3, m4a, wav, mp4, mov, flac, ogg, webm, opus). Without ffmpeg, faster-whisper's PyAV backend still handles most common formats.
- **Very short clips (< 5 seconds):** Whisper may hallucinate. Suggest `--model small` for short snippets — it's less prone to this.
- **Accuracy-critical work:** Suggest `--model large-v3` (non-turbo) for best accuracy. Turbo trades a small accuracy drop for ~5x speed.
- **Non-English audio:** Auto-detect is reliable; passing `--language` skips detection and is slightly faster. For mixed-language audio, let auto-detect run.
- **Noisy or low-quality audio:** Suggest `--model large-v3` for noisy recordings; `turbo` and smaller models degrade faster on noisy inputs.

## Model Reference

| Model | Size | Speed (M-series, MLX) | Accuracy | When to use |
|-------|------|-----------------------|----------|-------------|
| `tiny` | ~75MB | Fastest | Lowest | Quick drafts, clear speech |
| `base` | ~140MB | Very fast | Low-ish | Simple English audio |
| `small` | ~465MB | Fast | Good | Everyday use, short clips |
| `medium` | ~1.5GB | Moderate | Better | Quality bump over small |
| **`large-v3-turbo`** | **~800MB** | **Fast (default)** | **Near large-v3** | **Default — best balance** |
| `large-v3` | ~3GB | Slower | Best | Accuracy-critical, noisy audio |

Turbo has fewer decoder layers than `large-v3` but retains the same encoder — it's specifically designed as the accuracy-for-speed tradeoff point and is the right default for almost all use cases.
