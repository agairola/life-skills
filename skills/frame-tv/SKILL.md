---
name: frame-tv
description: >-
  Generate or resize art for Samsung Frame TV displays using AI image generation.
  Use this skill when the user asks to generate wall art, create art for their
  Samsung Frame TV, make TV art, generate an image for their Frame TV,
  resize an image for Frame TV, or wants AI-generated artwork for display.
  Powered by Google Gemini (nano-banana-2 style).
allowed-tools: Bash(uv run *), Read
argument-hint: "[prompt or image path]"
---

# Frame TV Art Skill

Generate AI artwork or resize existing images for Samsung Frame TV displays. Uses Google Gemini (nano-banana-2 style) for image generation and Pillow for precision resizing.

## Install

```bash
npx skills add agairola/life-skills --skill frame-tv
```

## When to Use

Trigger this skill when the user:

- Asks to generate art for a Samsung Frame TV
- Wants to create wall art or display art using AI
- Asks to resize an image for their Frame TV
- Mentions Samsung Frame TV art or TV art generation
- Wants AI-generated artwork for a specific TV size
- Asks about Frame TV resolutions or image sizing
- Wants to create gallery-quality images for display

## Prerequisites

- **uv** — `brew install uv` (macOS) or `pip install uv` (all platforms)
- **API keys** — `GEMINI_API_KEY` required for image generation (free at [Google AI Studio](https://aistudio.google.com/apikey)). Not needed for resize-only mode.
- **Dependencies** — declared inline (PEP 723), installed automatically by `uv run`.

See [references/api_upgrade.md](references/api_upgrade.md) for API key setup instructions.

## Setup Status

!`command -v uv > /dev/null 2>&1 && echo "uv: installed" || echo "uv: NOT INSTALLED"`
!`test -n "${GEMINI_API_KEY:-}" && echo "GEMINI_API_KEY: set" || (test -f ~/.nano-banana/.env && echo "GEMINI_API_KEY: found in ~/.nano-banana/.env") || echo "GEMINI_API_KEY: NOT SET (needed for generation, not resize)"`

## Command Template

```bash
uv run "${CLAUDE_SKILL_DIR}/scripts/frame_tv_art.py" [OPTIONS]
```

## Options

| Flag | Values | Default | Purpose |
|------|--------|---------|---------|
| `--prompt` / `-p` | text | *(none)* | Text prompt for AI image generation |
| `--resize` / `-r` | file path | *(none)* | Resize an existing image for Frame TV |
| `--input-image` / `-i` | file path(s) | *(none)* | Reference image(s) for generation (up to 14, repeatable) |
| `--tv` / `-t` | 32, 43, 50, 55, 65, 75, 85 | `55` | Samsung Frame TV size in inches |
| `--resolution` | 512px, 1K, 2K, 4K | `4K` | Generation resolution preset (auto-detected from input image if not set) |
| `--output-dir` / `-o` | directory path | `art` | Output directory |
| `--model` / `-m` | Gemini model ID | `gemini-3.1-flash-image-preview` | Gemini model to use |
| `--aspect` / `-a` | ratio (e.g., 16:9) | `16:9` | Aspect ratio (passed via API image_config) |
| `--api-key` | API key string | *(none)* | Gemini API key (overrides env vars) |
| `--preview` | *(flag)* | off | Generate a quick 512px preview (use --upscale to finalize) |
| `--upscale` | file path | *(none)* | Upscale a preview image to full 4K resolution |
| `--dry-run` | *(flag)* | off | Validate without API call |

Only parse **stdout** (JSON). Stderr contains diagnostics only.

## Common Commands

```bash
# Preview first, then upscale (RECOMMENDED workflow)
uv run "${CLAUDE_SKILL_DIR}/scripts/frame_tv_art.py" --prompt "calm ocean sunset, oil painting style" --preview
# → shows 512px preview, user reviews it
# → if approved, run the upscale_command from the JSON output:
uv run "${CLAUDE_SKILL_DIR}/scripts/frame_tv_art.py" --upscale art/frame_art_<timestamp>_raw.png

# Generate directly at 4K (skip preview)
uv run "${CLAUDE_SKILL_DIR}/scripts/frame_tv_art.py" --prompt "calm ocean sunset, oil painting style"

# Generate for a specific TV size
uv run "${CLAUDE_SKILL_DIR}/scripts/frame_tv_art.py" --prompt "Japanese garden in autumn" --tv 65

# Resize an existing image for Frame TV
uv run "${CLAUDE_SKILL_DIR}/scripts/frame_tv_art.py" --resize /path/to/image.jpg --tv 55

# Use a reference image for style/content guidance
uv run "${CLAUDE_SKILL_DIR}/scripts/frame_tv_art.py" --prompt "in this style but with autumn colors" --input-image ref.jpg

# Multiple reference images
uv run "${CLAUDE_SKILL_DIR}/scripts/frame_tv_art.py" --prompt "combine these styles" --input-image style1.jpg --input-image style2.jpg

# Square aspect ratio (for specific art styles)
uv run "${CLAUDE_SKILL_DIR}/scripts/frame_tv_art.py" --prompt "abstract geometric art" --aspect 1:1

# Specify resolution preset
uv run "${CLAUDE_SKILL_DIR}/scripts/frame_tv_art.py" --prompt "landscape painting" --resolution 2K

# Pass API key directly
uv run "${CLAUDE_SKILL_DIR}/scripts/frame_tv_art.py" --prompt "ocean sunset" --api-key "your-key-here"

# Dry run to check config
uv run "${CLAUDE_SKILL_DIR}/scripts/frame_tv_art.py" --prompt "test" --dry-run

# Resize for a smaller 32" TV (1080p)
uv run "${CLAUDE_SKILL_DIR}/scripts/frame_tv_art.py" --resize photo.jpg --tv 32
```

## Presenting Results

Follow the formatting rules in [../../references/platform-formatting.md](../../references/platform-formatting.md). Key skill-specific formatting below.

### Preview Mode (recommended default)

```
Frame TV Art Preview:

Prompt: "calm ocean sunset, oil painting style"
Preview: art/frame_art_20260319_143022_raw.png (512px)

Does this look good? If yes, I'll generate the full 4K version for your 55" TV.
```

When the user approves, run the `upscale_command` from the JSON output. After upscale:

```
Frame TV Art — Full Resolution:

Prompt: "calm ocean sunset, oil painting style"
TV Size: 55" (3840×2160)
Upscaled from preview → 3840×2160
Output: art/frame_art_55in_20260319_143122.jpg

Transfer tip: Copy to USB drive for best quality — avoids compression from phone/cloud transfer.
```

### Generate Mode (direct, no preview)

```
Frame TV Art Generated:

Prompt: "calm ocean sunset, oil painting style"
TV Size: 55" (3840×2160)
Generated: 1024×1024 → resized to 3840×2160
Output: art/frame_art_55in_20260319_143022.jpg

Transfer tip: Copy to USB drive for best quality — avoids compression from phone/cloud transfer.
```

### Resize Mode

```
Image Resized for Frame TV:

Input: vacation_photo.jpg (4000×3000)
TV Size: 55" (3840×2160)
Output: art/vacation_photo_frame_55in_20260319_143022.jpg (3840×2160)

Transfer tip: Copy to USB drive for best quality.
```

### Formatting Rules

- **Default to --preview mode** for generation — show the preview and ask the user before upscaling to 4K
- Always show the TV size and target resolution
- Show the resize dimensions (original → final)
- Include the output file path
- Always mention the USB transfer tip for best quality (after upscale/generate, not for previews)
- If API key is missing, show setup instructions from references/api_upgrade.md
- For resize-only mode, note that no API key is needed

## Handling Edge Cases

- **No API key** (generate mode): Show the error with setup instructions — "Set GEMINI_API_KEY or create ~/.nano-banana/.env. Get a free key at aistudio.google.com/apikey"
- **API key present but generation fails**: Show the error message from Gemini. Suggest trying a different prompt or checking API quota.
- **Resize input not found**: "File not found: [path]. Check the file path and try again."
- **No --prompt or --resize**: "Either --prompt or --resize is required. Use --prompt for AI generation or --resize to fit an existing image."
- **Unsupported TV size**: argparse handles this — shows valid choices (32, 43, 50, 55, 65, 75, 85).

## Reference

### Samsung Frame TV Resolutions

| TV Size | Resolution |
|---------|-----------|
| 32" | 1920×1080 (Full HD) |
| 43" | 3840×2160 (4K UHD) |
| 50" | 3840×2160 (4K UHD) |
| 55" | 3840×2160 (4K UHD) |
| 65" | 3840×2160 (4K UHD) |
| 75" | 3840×2160 (4K UHD) |
| 85" | 3840×2160 (4K UHD) |

### Art Style Tips

- **Oil paintings**: Rich textures, vibrant colors — great for living rooms
- **Watercolors**: Soft, light feel — works well in bedrooms
- **Photography**: Nature scenes, cityscapes — versatile for any room
- **Abstract**: Bold patterns and colors — modern/contemporary spaces
- Add "museum-quality" or "gallery-worthy" to prompts for higher quality results

### Image Transfer

For best quality on your Frame TV:
1. Save images to a USB drive (FAT32 or exFAT formatted)
2. Insert USB into TV's USB port
3. Open Art Mode → My Collection → USB
4. Select images to import

Avoid transferring via messaging apps (WhatsApp, iMessage) — they compress images significantly.

### Technology

Image generation uses Google Gemini (nano-banana-2 approach) with `gemini-3.1-flash-image-preview`. Aspect ratio and resolution are passed via `image_config` in the API config (not just prompt text). Supports reference/input images sent alongside the prompt. Handles multiple output images from a single generation. RGBA images are converted to RGB before JPEG saving. Images are resized to exact TV dimensions using Pillow's LANCZOS resampling. Output is high-quality JPEG (quality=92, no chroma subsampling).
