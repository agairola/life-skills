#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "google-genai>=1.65.0",
#   "pillow>=12.1.1",
# ]
# ///
"""
Frame TV Art — generate AI art sized for Samsung Frame TV displays.

Uses Google Gemini (nano-banana-2 style) for image generation and
Pillow for resizing to exact Frame TV resolutions.

Usage:
    uv run frame_tv_art.py --prompt "calm ocean sunset"           # generate for default 55" TV
    uv run frame_tv_art.py --prompt "Japanese garden" --tv 65     # generate for 65" TV
    uv run frame_tv_art.py --prompt "in this style" --input-image ref.jpg  # use reference image
    uv run frame_tv_art.py --resize input.jpg                     # resize existing image
    uv run frame_tv_art.py --resize input.jpg --tv 43             # resize for 43" TV
    uv run frame_tv_art.py --prompt "sunset" --preview             # quick 512px preview first
    uv run frame_tv_art.py --upscale art/frame_art_preview_20260319.png  # upscale approved preview to 4K
    uv run frame_tv_art.py --prompt "test" --dry-run              # validate without API call
"""

import argparse
import json
import os
import sys
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
DEFAULT_MODEL = "gemini-3.1-flash-image-preview"

# Resolution presets matching nano-banana-2
RESOLUTION_PRESETS: dict[str, str] = {
    "512px": "512x512",
    "1K": "1024x1024",
    "2K": "2048x2048",
    "4K": "4096x4096",
}

DEFAULT_RESOLUTION = "4K"
PREVIEW_RESOLUTION = "512px"

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


def get_api_key(cli_key: str | None = None) -> str | None:
    """Resolve Gemini API key from CLI flag, environment, or config files."""
    # 0. Direct CLI flag (--api-key)
    if cli_key:
        return cli_key

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


def detect_resolution_from_image(img_path: str) -> str:
    """Auto-detect resolution preset from input image dimensions."""
    from PIL import Image

    img = Image.open(img_path)
    w, h = img.size
    max_dim = max(w, h)

    if max_dim <= 600:
        return "512px"
    elif max_dim <= 1200:
        return "1K"
    elif max_dim <= 2500:
        return "2K"
    else:
        return "4K"


def load_input_images(paths: list[str]) -> list:
    """Load input/reference images as PIL Image objects for the API."""
    from PIL import Image

    images = []
    for p in paths:
        path = Path(p)
        if not path.exists():
            _err(f"Input image not found: {p}")
        images.append(Image.open(path))
    return images


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


def save_preview_metadata(preview_path: str, prompt: str, aspect: str, model: str,
                          input_images: list[str] | None, tv_size: int) -> None:
    """Save generation metadata alongside preview image for upscale later."""
    meta_path = Path(preview_path).with_suffix(".json")
    meta = {
        "prompt": prompt,
        "aspect": aspect,
        "model": model,
        "input_images": input_images,
        "tv_size": tv_size,
        "preview_path": preview_path,
        "created": datetime.now().isoformat(),
    }
    meta_path.write_text(json.dumps(meta, indent=2))


def load_preview_metadata(preview_path: str) -> dict:
    """Load generation metadata saved alongside a preview image."""
    meta_path = Path(preview_path).with_suffix(".json")
    if not meta_path.exists():
        _err(
            f"Preview metadata not found: {meta_path}",
            hint="The --upscale flag requires a preview image generated with --preview. "
                 "The .json metadata file must exist next to the preview image.",
        )
    return json.loads(meta_path.read_text())


# ---------------------------------------------------------------------------
# Image generation via Gemini (nano-banana-2 approach)
# ---------------------------------------------------------------------------


def generate_image(
    prompt: str,
    api_key: str,
    model: str = DEFAULT_MODEL,
    aspect: str | None = None,
    resolution: str = DEFAULT_RESOLUTION,
    input_images: list | None = None,
) -> list[bytes]:
    """Generate image(s) using Google Gemini and return list of raw image bytes."""
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)

    # Build config with image_config for aspect ratio and resolution (nano-banana-2 style)
    image_config_kwargs = {}
    if resolution:
        image_config_kwargs["image_size"] = resolution
    if aspect:
        image_config_kwargs["aspect_ratio"] = aspect

    config = types.GenerateContentConfig(
        response_modalities=["IMAGE", "TEXT"],
        image_config=types.ImageConfig(**image_config_kwargs) if image_config_kwargs else None,
    )

    # Enhance prompt for Frame TV art style
    full_prompt = (
        f"{prompt}. High resolution, museum-quality artwork suitable for "
        f"display on a wall-mounted Samsung Frame TV."
    )

    # Build contents: prompt + optional reference images (nano-banana-2 style)
    contents: list = [full_prompt]
    if input_images:
        contents = [full_prompt, *input_images]

    print(f"Generating with {model}...", file=sys.stderr)
    print(f"Prompt: {full_prompt[:120]}...", file=sys.stderr)
    if input_images:
        print(f"Reference images: {len(input_images)}", file=sys.stderr)
    print(f"Resolution: {resolution}, Aspect: {aspect or 'default'}", file=sys.stderr)

    response = client.models.generate_content(
        model=model,
        contents=contents,
        config=config,
    )

    # Extract image data from response — handle multiple output images
    result_images: list[bytes] = []
    if response.candidates:
        for part in response.candidates[0].content.parts:
            if part.inline_data and part.inline_data.data:
                data = part.inline_data.data
                # google-genai >= 1.65 returns raw bytes; older versions return base64 string
                if isinstance(data, str):
                    import base64
                    result_images.append(base64.b64decode(data))
                else:
                    result_images.append(bytes(data))

    if not result_images:
        raise RuntimeError("Gemini returned no image data in response")

    return result_images


# ---------------------------------------------------------------------------
# Image resizing
# ---------------------------------------------------------------------------


def convert_rgba_to_rgb(img):
    """Convert RGBA image to RGB with white background for JPEG saving."""
    if img.mode == "RGBA":
        from PIL import Image
        background = Image.new("RGB", img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[3])
        return background
    return img


def resize_image(
    input_path: str,
    tv_size: int,
    output_dir: str,
) -> str:
    """Resize an existing image to fit the target Frame TV resolution."""
    from PIL import Image

    target_w, target_h = TV_RESOLUTIONS[tv_size]

    img = Image.open(input_path)
    img = convert_rgba_to_rgb(img)
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
        "--input-image", "-i",
        action="append",
        default=[],
        help="Reference/input image(s) for generation (can be repeated, up to 14)",
    )
    parser.add_argument(
        "--tv", "-t",
        type=int,
        default=DEFAULT_TV_SIZE,
        choices=sorted(TV_RESOLUTIONS.keys()),
        help=f"Samsung Frame TV size in inches (default: {DEFAULT_TV_SIZE})",
    )
    parser.add_argument(
        "--resolution",
        default=None,
        choices=list(RESOLUTION_PRESETS.keys()),
        help=f"Generation resolution preset (default: {DEFAULT_RESOLUTION}, or auto-detected from input image)",
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
        "--api-key",
        default=None,
        help="Gemini API key (overrides env vars and config files)",
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Generate a quick 512px preview first (use --upscale to finalize at 4K)",
    )
    parser.add_argument(
        "--upscale",
        default=None,
        help="Path to a preview image to upscale to full resolution (reads prompt from saved metadata)",
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

    if not args.prompt and not args.resize and not args.upscale:
        _err(
            "Either --prompt, --resize, or --upscale is required.",
            hint="Use --prompt to generate new art, --resize to resize an existing image, or --upscale to finalize a preview.",
        )

    if args.input_image and len(args.input_image) > 14:
        _err("Maximum 14 input images supported.")

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
            "api_key_configured": bool(get_api_key(args.api_key)) if args.prompt else None,
            "prompt": args.prompt,
            "input_images": args.input_image or None,
            "resolution": args.resolution or DEFAULT_RESOLUTION,
            "resize_input": args.resize,
            "output_dir": args.output_dir,
        }
        print(json.dumps(result, indent=2))
        return

    # --- Upscale mode (finalize a preview at full resolution) ---
    if args.upscale:
        preview_path = args.upscale
        if not Path(preview_path).exists():
            _err(f"Preview image not found: {preview_path}")

        meta = load_preview_metadata(preview_path)
        api_key = get_api_key(args.api_key)
        if not api_key:
            _err(
                "Gemini API key not found.",
                hint="Set GEMINI_API_KEY environment variable, pass --api-key, or create ~/.nano-banana/.env with GEMINI_API_KEY=your_key",
                setup_url="https://aistudio.google.com/apikey",
            )

        upscale_tv = meta.get("tv_size", tv_size)
        up_target_w, up_target_h = TV_RESOLUTIONS[upscale_tv]
        upscale_resolution = args.resolution or DEFAULT_RESOLUTION
        upscale_aspect = meta.get("aspect", "16:9")
        upscale_model = meta.get("model", args.model)
        upscale_prompt = meta["prompt"]

        # Load reference images from original generation if any
        upscale_input_images = None
        if meta.get("input_images"):
            upscale_input_images = load_input_images(meta["input_images"])

        # Also pass the preview image itself as a reference
        preview_images = load_input_images([preview_path])
        all_refs = preview_images + (upscale_input_images or [])

        print(f"Upscaling preview to {upscale_resolution}...", file=sys.stderr)

        try:
            image_list = generate_image(
                upscale_prompt, api_key, upscale_model, upscale_aspect,
                upscale_resolution, all_refs,
            )
        except Exception as e:
            _err(f"Upscale generation failed: {e}")

        out_dir = Path(args.output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        from PIL import Image
        import io

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        image_bytes = image_list[0]

        raw_path = out_dir / f"frame_art_{ts}_upscaled_raw.png"
        raw_path.write_bytes(image_bytes)

        img = Image.open(io.BytesIO(image_bytes))
        img = convert_rgba_to_rgb(img)
        src_w, src_h = img.size
        fit_w, fit_h = calc_fit_size(src_w, src_h, up_target_w, up_target_h)
        resized = img.resize((fit_w, fit_h), Image.LANCZOS)

        final_path = out_dir / f"frame_art_{upscale_tv}in_{ts}.jpg"
        resized.save(str(final_path), "JPEG", quality=92, subsampling=0)
        print(f"Upscaled {src_w}x{src_h} → {fit_w}x{fit_h} for {upscale_tv}\" TV", file=sys.stderr)

        try:
            log_cost(upscale_model, upscale_prompt, str(final_path))
        except Exception:
            pass

        result = {
            "mode": "upscale",
            "preview_source": preview_path,
            "prompt": upscale_prompt,
            "model": upscale_model,
            "resolution": upscale_resolution,
            "tv_size": upscale_tv,
            "target_resolution": f"{up_target_w}x{up_target_h}",
            "generated_resolution": f"{src_w}x{src_h}",
            "final_resolution": f"{fit_w}x{fit_h}",
            "raw_image": str(raw_path),
            "output": str(final_path),
            "output_dir": str(out_dir),
            "transfer_tip": "Copy to USB drive for best quality — avoids compression from phone/cloud transfer.",
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
    api_key = get_api_key(args.api_key)
    if not api_key:
        _err(
            "Gemini API key not found.",
            hint="Set GEMINI_API_KEY environment variable, pass --api-key, or create ~/.nano-banana/.env with GEMINI_API_KEY=your_key",
            setup_url="https://aistudio.google.com/apikey",
        )

    prompt = args.prompt
    aspect = args.aspect or "16:9"  # Default landscape for TV
    is_preview = args.preview

    # Determine resolution: preview mode forces 512px, else explicit flag > auto-detect > default
    if is_preview:
        resolution = PREVIEW_RESOLUTION
        print("Preview mode: generating at 512px for quick review...", file=sys.stderr)
    else:
        resolution = args.resolution
        if not resolution and args.input_image:
            resolution = detect_resolution_from_image(args.input_image[0])
            print(f"Auto-detected resolution: {resolution} (from input image)", file=sys.stderr)
        if not resolution:
            resolution = DEFAULT_RESOLUTION

    # Load reference images if provided
    input_images = None
    if args.input_image:
        input_images = load_input_images(args.input_image)

    try:
        image_list = generate_image(prompt, api_key, args.model, aspect, resolution, input_images)
    except Exception as e:
        _err(f"Image generation failed: {e}")

    # Save all generated images
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    from PIL import Image
    import io

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    outputs = []

    for idx, image_bytes in enumerate(image_list):
        suffix = f"_{idx + 1}" if len(image_list) > 1 else ""

        # Save raw generated image
        raw_path = out_dir / f"frame_art_{ts}{suffix}_raw.png"
        raw_path.write_bytes(image_bytes)
        print(f"Saved raw image: {raw_path}", file=sys.stderr)

        # Resize to exact TV resolution
        img = Image.open(io.BytesIO(image_bytes))
        img = convert_rgba_to_rgb(img)
        src_w, src_h = img.size
        fit_w, fit_h = calc_fit_size(src_w, src_h, target_w, target_h)
        resized = img.resize((fit_w, fit_h), Image.LANCZOS)

        final_path = out_dir / f"frame_art_{tv_size}in_{ts}{suffix}.jpg"
        resized.save(str(final_path), "JPEG", quality=92, subsampling=0)
        print(f"Resized {src_w}x{src_h} → {fit_w}x{fit_h} for {tv_size}\" TV", file=sys.stderr)

        outputs.append({
            "raw_image": str(raw_path),
            "output": str(final_path),
            "generated_resolution": f"{src_w}x{src_h}",
            "final_resolution": f"{fit_w}x{fit_h}",
        })

    # Save preview metadata for upscale later
    if is_preview:
        save_preview_metadata(
            outputs[0]["raw_image"], prompt, aspect, args.model,
            args.input_image or None, tv_size,
        )

    # Log cost
    try:
        log_cost(args.model, prompt, str(outputs[0]["output"]))
    except Exception:
        pass

    result = {
        "mode": "preview" if is_preview else "generate",
        "prompt": prompt,
        "model": args.model,
        "resolution": resolution,
        "aspect_ratio": aspect,
        "tv_size": tv_size,
        "target_resolution": f"{target_w}x{target_h}",
        "images_generated": len(outputs),
        "images": outputs if len(outputs) > 1 else None,
        "raw_image": outputs[0]["raw_image"],
        "output": outputs[0]["output"],
        "generated_resolution": outputs[0]["generated_resolution"],
        "final_resolution": outputs[0]["final_resolution"],
        "output_dir": str(out_dir),
        "input_images": args.input_image or None,
    }

    if is_preview:
        result["preview"] = True
        result["upscale_command"] = (
            f"uv run frame_tv_art.py --upscale {outputs[0]['raw_image']}"
        )
        result["next_step"] = "Review the preview image. If you like it, run the upscale_command to generate the full 4K version."
    else:
        result["transfer_tip"] = "Copy to USB drive for best quality — avoids compression from phone/cloud transfer."

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
