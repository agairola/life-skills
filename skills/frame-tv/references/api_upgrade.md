# Setting Up the Gemini API Key

The Frame TV Art skill uses Google Gemini for AI image generation (nano-banana-2 style). A free API key is required for image generation. Resize-only mode works without an API key.

## Getting a Free API Key (~1 minute)

1. Go to [Google AI Studio](https://aistudio.google.com/apikey)
2. Sign in with your Google account
3. Click **"Create API key"**
4. Copy the key

## Configuring the Key

### Option 1: Environment variable (recommended)

Add to your shell profile (`~/.bashrc`, `~/.zshrc`, etc.):

```bash
export GEMINI_API_KEY="your-api-key-here"
```

### Option 2: nano-banana config file

If you already use nano-banana-2, the skill will pick up your existing key:

```bash
mkdir -p ~/.nano-banana
echo 'GEMINI_API_KEY=your-api-key-here' > ~/.nano-banana/.env
chmod 600 ~/.nano-banana/.env
```

### Option 3: frame-tv config file

```bash
mkdir -p ~/.config/frame-tv
echo 'GEMINI_API_KEY=your-api-key-here' > ~/.config/frame-tv/.env
chmod 600 ~/.config/frame-tv/.env
```

## Key Resolution Order

The skill checks for the API key in this order:

1. `GEMINI_API_KEY` environment variable
2. `GOOGLE_API_KEY` environment variable
3. `~/.nano-banana/.env`
4. `~/.config/frame-tv/.env`

## Free Tier Limits

The Gemini API free tier includes:
- 15 requests per minute
- 1,500 requests per day
- No credit card required

This is more than enough for generating Frame TV art.

## Cost

Image generation with Gemini Flash costs approximately **$0.04-0.07 per image**. The free tier covers most personal use.
