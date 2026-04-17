#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "mlx-whisper>=0.4.3; sys_platform == 'darwin' and platform_machine == 'arm64'",
#   "faster-whisper>=1.2.0",
#   "huggingface-hub>=0.25.0",
# ]
# ///
"""
Transcribe — local speech-to-text via OpenAI Whisper.

Uses MLX acceleration on Apple Silicon (mlx-whisper) and falls back to
faster-whisper (CTranslate2, CPU) on Intel Macs and Linux. Zero-config:
models download on first use, no API keys.

Usage:
    uv run transcribe.py meeting.m4a
    uv run transcribe.py video.mp4 --format srt --output video.srt
    uv run transcribe.py clip.mp3 --model small --language en
    uv run transcribe.py foreign.mp3 --translate
    uv run transcribe.py lecture.mp3 --format json --word-timestamps
"""

import argparse
import json
import platform
import shutil
import sys
from pathlib import Path

MLX_MODELS = {
    "tiny": "mlx-community/whisper-tiny-mlx",
    "base": "mlx-community/whisper-base-mlx",
    "small": "mlx-community/whisper-small-mlx",
    "medium": "mlx-community/whisper-medium-mlx",
    "large-v3": "mlx-community/whisper-large-v3-mlx",
    "large-v3-turbo": "mlx-community/whisper-large-v3-turbo",
    "turbo": "mlx-community/whisper-large-v3-turbo",
}

# faster-whisper accepts these as built-in names
FW_MODELS = {
    "tiny", "base", "small", "medium",
    "large-v3", "large-v3-turbo", "turbo",
}

DEFAULT_MODEL = "large-v3-turbo"


def pick_engine(requested: str) -> str:
    """Choose transcription engine. Returns 'mlx' or 'faster'."""
    if requested == "mlx":
        return "mlx"
    if requested == "faster":
        return "faster"

    is_apple_silicon = (
        sys.platform == "darwin" and platform.machine() == "arm64"
    )
    if not is_apple_silicon:
        return "faster"

    # MLX needs ffmpeg for audio decoding; fall back if missing.
    if not shutil.which("ffmpeg"):
        print(
            "ffmpeg not found — falling back to CPU engine. "
            "For faster transcription on Apple Silicon, run: brew install ffmpeg",
            file=sys.stderr,
        )
        return "faster"

    try:
        import mlx_whisper  # noqa: F401
        return "mlx"
    except ImportError:
        return "faster"


def transcribe_mlx(audio_path: str, model: str, language: str | None, translate: bool, word_timestamps: bool):
    import mlx_whisper
    repo = MLX_MODELS.get(model, MLX_MODELS[DEFAULT_MODEL])
    kwargs = {
        "path_or_hf_repo": repo,
        "task": "translate" if translate else "transcribe",
        "word_timestamps": word_timestamps,
        "verbose": None,
    }
    if language and language != "auto":
        kwargs["language"] = language

    print(f"Transcribing with MLX Whisper ({model})...", file=sys.stderr)
    result = mlx_whisper.transcribe(audio_path, **kwargs)
    return {
        "text": result.get("text", "").strip(),
        "language": result.get("language"),
        "segments": result.get("segments", []),
    }


def transcribe_faster(audio_path: str, model: str, language: str | None, translate: bool, word_timestamps: bool):
    from faster_whisper import WhisperModel

    model_name = model if model in FW_MODELS else DEFAULT_MODEL
    print(f"Transcribing with faster-whisper ({model_name})...", file=sys.stderr)

    fw_model = WhisperModel(model_name, device="cpu", compute_type="int8")
    segments_iter, info = fw_model.transcribe(
        audio_path,
        language=None if not language or language == "auto" else language,
        task="translate" if translate else "transcribe",
        word_timestamps=word_timestamps,
        vad_filter=True,
    )

    segments = []
    text_parts = []
    for seg in segments_iter:
        seg_dict = {
            "id": seg.id,
            "start": seg.start,
            "end": seg.end,
            "text": seg.text,
        }
        if word_timestamps and seg.words:
            seg_dict["words"] = [
                {"word": w.word, "start": w.start, "end": w.end, "probability": w.probability}
                for w in seg.words
            ]
        segments.append(seg_dict)
        text_parts.append(seg.text)

    return {
        "text": "".join(text_parts).strip(),
        "language": info.language,
        "segments": segments,
    }


def fmt_timestamp(seconds: float, sep: str = ",") -> str:
    """Format seconds as HH:MM:SS,mmm (SRT) or HH:MM:SS.mmm (VTT)."""
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1_000)
    return f"{h:02d}:{m:02d}:{s:02d}{sep}{ms:03d}"


def render(result: dict, fmt: str) -> str:
    if fmt == "txt":
        return result["text"] + "\n"

    if fmt == "json":
        return json.dumps(result, indent=2, ensure_ascii=False) + "\n"

    if fmt == "srt":
        lines = []
        for i, seg in enumerate(result["segments"], 1):
            lines.append(str(i))
            lines.append(f"{fmt_timestamp(seg['start'])} --> {fmt_timestamp(seg['end'])}")
            lines.append(seg["text"].strip())
            lines.append("")
        return "\n".join(lines)

    if fmt == "vtt":
        lines = ["WEBVTT", ""]
        for seg in result["segments"]:
            lines.append(f"{fmt_timestamp(seg['start'], '.')} --> {fmt_timestamp(seg['end'], '.')}")
            lines.append(seg["text"].strip())
            lines.append("")
        return "\n".join(lines)

    raise ValueError(f"Unknown format: {fmt}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Transcribe audio/video locally using OpenAI Whisper.",
    )
    parser.add_argument("input", help="Path to audio or video file")
    parser.add_argument("--model", default=DEFAULT_MODEL,
                        choices=sorted(set(list(MLX_MODELS.keys()) + list(FW_MODELS))),
                        help=f"Whisper model (default: {DEFAULT_MODEL})")
    parser.add_argument("--language", default="auto",
                        help="ISO language code (e.g. 'en', 'fr'), or 'auto' to detect")
    parser.add_argument("--format", default="txt",
                        choices=["txt", "srt", "vtt", "json"],
                        help="Output format (default: txt)")
    parser.add_argument("--output", help="Write output to file instead of stdout")
    parser.add_argument("--word-timestamps", action="store_true",
                        help="Include word-level timing (JSON format only)")
    parser.add_argument("--engine", default="auto", choices=["auto", "mlx", "faster"],
                        help="Force an engine (default: auto)")
    parser.add_argument("--translate", action="store_true",
                        help="Translate to English instead of transcribing in source language")
    parser.add_argument("--json-summary", action="store_true",
                        help="Print a JSON summary (path, language, duration, word count) to stdout")

    args = parser.parse_args()

    audio_path = Path(args.input).expanduser().resolve()
    if not audio_path.exists():
        print(f"Error: file not found: {audio_path}", file=sys.stderr)
        return 1
    if not audio_path.is_file():
        print(f"Error: not a file: {audio_path}", file=sys.stderr)
        return 1

    engine = pick_engine(args.engine)

    try:
        if engine == "mlx":
            result = transcribe_mlx(
                str(audio_path), args.model, args.language,
                args.translate, args.word_timestamps,
            )
        else:
            result = transcribe_faster(
                str(audio_path), args.model, args.language,
                args.translate, args.word_timestamps,
            )
    except KeyboardInterrupt:
        print("\nCancelled.", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"Transcription failed: {e}", file=sys.stderr)
        return 1

    rendered = render(result, args.format)

    if args.output:
        out_path = Path(args.output).expanduser()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(rendered, encoding="utf-8")
        if not args.json_summary:
            print(f"Saved {args.format.upper()} transcript to {out_path}", file=sys.stderr)
    else:
        if not args.json_summary:
            sys.stdout.write(rendered)

    if args.json_summary:
        duration = 0.0
        if result["segments"]:
            duration = result["segments"][-1].get("end", 0.0)
        word_count = len(result["text"].split())
        summary = {
            "input": str(audio_path),
            "output": str(Path(args.output).expanduser()) if args.output else None,
            "engine": engine,
            "model": args.model,
            "language": result.get("language"),
            "duration_seconds": round(duration, 2),
            "word_count": word_count,
            "format": args.format,
        }
        json.dump(summary, sys.stdout, indent=2)
        sys.stdout.write("\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
