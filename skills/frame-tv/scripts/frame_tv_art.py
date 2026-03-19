#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "google-genai>=1.0.0",
#   "pillow>=10.0.0",
# ]
# ///
"""
Frame TV Art — generate AI art sized for Samsung Frame TV displays.

Uses Google Gemini (nano-banana-2 style) for image generation and
Pillow for resizing to exact Frame TV resolutions.

Usage:
    uv run frame_tv_art.py --prompt "calm ocean sunset"           # generate for default 55" TV
    uv run frame_tv_art.py --prompt "Japanese garden" --tv 65     # generate for 65" TV
    uv run frame_tv_art.py --resize input.jpg                     # resize existing image
    uv run frame_tv_art.py --resize input.jpg --tv 43             # resize for 43" TV
    uv run frame_tv_art.py --prompt "test" --dry-run              # validate without API call
"""

import argparse
import base64
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Samsung Frame TV resolutions
# ---------------------------------------------------------------------------

TV_RESOLUTIONS: dict[int, tuple[int, int]] = {
    32: (1920, 1080),
    43: (3840, 2160),
    50: (3840, 2160),
    55: (3840, 2160),
    65: (3840, 2160),
    75: (3840, 2160),
    85: (3840, 2160),
}

DEFAULT_TV_SIZE = 55

# Gemini model for nano-banana-2 style generation
DEFAULT_MODEL = "gemini-2.0-flash-exp"

# ---------------------------------------------------------------------------
# Cache / config
# ---------------------------------------------------------------------------

CONFIG_DIR = Path.home() / ".config" / "frame-tv"
COSTS_FILE = CONFIG_DIR / "costs.json"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _err(message: str, **extra) -> None:
    """Print a JSON error to stdout and exit."""
    out = {"error": message}
    out.update(extra)
    print(json.dumps(out, indent=2))
    sys.exit(1)


def get_api_key() -> str | None:
    """Resolve Gemini API key from environment or config files."""
    # 1. Environment variable
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if key:
        return key

    # 2. ~/.nano-banana/.env
    env_file = Path.home() / ".nano-banana" / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line.startswith("GEMINI_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")

    # 3. ~/.config/frame-tv/.env
    env_file = CONFIG_DIR / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line.startswith("GEMINI_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")

    return None


def calc_fit_size(
    src_width: int, src_height: int, max_width: int, max_height: int
) -> tuple[int, int]:
    """Calculate dimensions to fit within bounds preserving aspect ratio."""
    ratio = min(max_width / src_width, max_height / src_height)
    return round(src_width * ratio), round(src_height * ratio)


def log_cost(model: str, prompt: str, output_file: str) -> None:
    """Log generation to cost tracking file."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    entries = []
    if COSTS_FILE.exists():
        try:
            entries = json.loads(COSTS_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    entries.append({
        "timestamp": datetime.now().isoformat(),
        "model": model,
        "prompt": prompt[:100],
        "output_file": str(output_file),
    })
    COSTS_FILE.write_text(json.dumps(entries, indent=2))


# ---------------------------------------------------------------------------
# Image generation via Gemini (nano-banana-2 approach)
# ---------------------------------------------------------------------------


def generate_image(
    prompt: str,
    api_key: str,
    model: str = DEFAULT_MODEL,
    aspect: str | None = None,
) -> bytes:
    """Generate an image using Google Gemini and return raw PNG bytes."""
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)

    # Build config for image generation
    config = types.GenerateContentConfig(
        response_modalities=["IMAGE", "TEXT"],
    )

    # Enhance prompt for Frame TV art style
    full_prompt = (
        f"{prompt}. High resolution, museum-quality artwork suitable for "
        f"display on a wall-mounted Samsung Frame TV."
    )
    if aspect:
        full_prompt += f" Aspect ratio: {aspect}."

    print(f"Generating with {model}...", file=sys.stderr)
    print(f"Prompt: {full_prompt[:120]}...", file=sys.stderr)

    response = client.models.generate_content(
        model=model,
        contents=full_prompt,
        config=config,
    )

    # Extract image data from response
    if response.candidates:
        for part in response.candidates[0].content.parts:
            if part.inline_data and part.inline_data.data:
                return base64.b64decode(part.inline_data.data)

    raise RuntimeError("Gemini returned no image data in response")


# ---------------------------------------------------------------------------
# Image resizing
# ---------------------------------------------------------------------------


def resize_image(
    input_path: str,
    tv_size: int,
    output_dir: str,
) -> str:
    """Resize an existing image to fit the target Frame TV resolution."""
    from PIL import Image

    target_w, target_h = TV_RESOLUTIONS[tv_size]

    img = Image.open(input_path)
    src_w, src_h = img.size

    fit_w, fit_h = calc_fit_size(src_w, src_h, target_w, target_h)
    resized = img.resize((fit_w, fit_h), Image.LANCZOS)

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    stem = Path(input_path).stem
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = out_dir / f"{stem}_frame_{tv_size}in_{ts}.jpg"

    resized.save(str(out_path), "JPEG", quality=92, subsampling=0)
    print(f"Resized {src_w}x{src_h} → {fit_w}x{fit_h} for {tv_size}\" TV", file=sys.stderr)

    return str(out_path)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate or resize art for Samsung Frame TV displays"
    )
    parser.add_argument(
        "--prompt", "-p",
        help="Text prompt for AI image generation (uses Gemini / nano-banana-2)",
    )
    parser.add_argument(
        "--resize", "-r",
        help="Path to an existing image to resize for Frame TV",
    )
    parser.add_argument(
        "--tv", "-t",
        type=int,
        default=DEFAULT_TV_SIZE,
        choices=sorted(TV_RESOLUTIONS.keys()),
        help=f"Samsung Frame TV size in inches (default: {DEFAULT_TV_SIZE})",
    )
    parser.add_argument(
        "--output-dir", "-o",
        default="art",
        help="Output directory for generated/resized images (default: art)",
    )
    parser.add_argument(
        "--model", "-m",
        default=DEFAULT_MODEL,
        help=f"Gemini model to use (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--aspect", "-a",
        default=None,
        help="Aspect ratio hint (e.g., 16:9, 1:1). Default: landscape for TV",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate inputs without making API calls or generating images",
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    args = parse_args()

    if not args.prompt and not args.resize:
        _err(
            "Either --prompt or --resize is required.",
            hint="Use --prompt to generate new art, or --resize to resize an existing image.",
        )

    tv_size = args.tv
    target_w, target_h = TV_RESOLUTIONS[tv_size]

    # --- Dry run mode ---
    if args.dry_run:
        result: dict = {
            "dry_run": True,
            "tv_size": tv_size,
            "target_resolution": f"{target_w}x{target_h}",
            "mode": "generate" if args.prompt else "resize",
            "model": args.model if args.prompt else None,
            "api_key_configured": bool(get_api_key()) if args.prompt else None,
            "prompt": args.prompt,
            "resize_input": args.resize,
            "output_dir": args.output_dir,
        }
        print(json.dumps(result, indent=2))
        return

    # --- Resize mode ---
    if args.resize:
        input_path = args.resize
        if not Path(input_path).exists():
            _err(f"Input file not found: {input_path}")

        out_path = resize_image(input_path, tv_size, args.output_dir)
        result = {
            "mode": "resize",
            "input": input_path,
            "output": out_path,
            "tv_size": tv_size,
            "target_resolution": f"{target_w}x{target_h}",
        }
        print(json.dumps(result, indent=2))
        return

    # --- Generate mode ---
    api_key = get_api_key()
    if not api_key:
        _err(
            "Gemini API key not found.",
            hint="Set GEMINI_API_KEY environment variable, or create ~/.nano-banana/.env with GEMINI_API_KEY=your_key",
            setup_url="https://aistudio.google.com/apikey",
        )

    prompt = args.prompt
    aspect = args.aspect or "16:9"  # Default landscape for TV

    try:
        image_bytes = generate_image(prompt, api_key, args.model, aspect)
    except Exception as e:
        _err(f"Image generation failed: {e}")

    # Save the raw generated image
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    raw_path = out_dir / f"frame_art_{ts}_raw.png"
    raw_path.write_bytes(image_bytes)
    print(f"Saved raw image: {raw_path}", file=sys.stderr)

    # Resize to exact TV resolution using Pillow
    from PIL import Image
    import io

    img = Image.open(io.BytesIO(image_bytes))
    src_w, src_h = img.size
    fit_w, fit_h = calc_fit_size(src_w, src_h, target_w, target_h)
    resized = img.resize((fit_w, fit_h), Image.LANCZOS)

    final_path = out_dir / f"frame_art_{tv_size}in_{ts}.jpg"
    resized.save(str(final_path), "JPEG", quality=92, subsampling=0)
    print(f"Resized {src_w}x{src_h} → {fit_w}x{fit_h} for {tv_size}\" TV", file=sys.stderr)

    # Log cost
    try:
        log_cost(args.model, prompt, str(final_path))
    except Exception:
        pass

    result = {
        "mode": "generate",
        "prompt": prompt,
        "model": args.model,
        "tv_size": tv_size,
        "target_resolution": f"{target_w}x{target_h}",
        "generated_resolution": f"{src_w}x{src_h}",
        "final_resolution": f"{fit_w}x{fit_h}",
        "raw_image": str(raw_path),
        "output": str(final_path),
        "output_dir": str(out_dir),
        "transfer_tip": "Copy to USB drive for best quality — avoids compression from phone/cloud transfer.",
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
