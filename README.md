# life-skills

![tests: 436 passed](https://img.shields.io/badge/tests-436%20passed-brightgreen) ![skills: 14](https://img.shields.io/badge/skills-14-blue) ![scripts: 14](https://img.shields.io/badge/scripts-14%20verified-blue)

A collection of personal life skills for AI agents.

## Skills

| Skill | TLDR | API Key? |
|-------|------|----------|
| [fuel-pricing](#fuel-pricing) | Cheapest fuel prices near you across Australia | No |
| [beach-check](#beach-check) | Beach water quality & swimming safety for NSW | No |
| [air-quality](#air-quality) | Air quality & pollution levels at NSW stations | No |
| [sydney-commute](#sydney-commute) | Sydney public transport trips & real-time departures | Optional |
| [uv-sun](#uv-sun) | UV index & sun safety advice for Australian cities | No |
| [park-alerts](#park-alerts) | Alerts, closures & fire bans for NSW National Parks | No |
| [speed-cameras](#speed-cameras) | Speed & red light cameras near you in NSW | No |
| [dam-levels](#dam-levels) | Current dam levels & water storage for Greater Sydney | No |
| [sydney-traffic](#sydney-traffic) | Live traffic incidents, roadworks & hazards in Sydney | Optional |
| [sydney-tolls](#sydney-tolls) | Sydney toll road prices & route cost calculator | No |
| [rental-prices](#rental-prices) | Median rental prices for Sydney suburbs | No |
| [read-aloud](#read-aloud) | Read files aloud with neural text-to-speech (local) | No |
| [frame-tv](#frame-tv) | Generate or resize AI art for Samsung Frame TV | Yes (Gemini) |
| [youtube-transcript](#youtube-transcript) | Extract transcripts from YouTube videos | No |
| [transcribe](#transcribe) | Transcribe local audio/video with Whisper (local) | No |

### fuel-pricing

Find the cheapest fuel prices near you across Australia. Works in any chat platform — Telegram, WhatsApp, Signal, Discord, terminal.

```bash
npx skills add agairola/life-skills --skill fuel-pricing
```

Zero config — no API keys needed. Covers all Australian states with multiple data sources.

### beach-check

Check beach water quality and swimming safety at NSW beaches. Covers 200+ beaches with data from Beachwatch.

```bash
npx skills add agairola/life-skills --skill beach-check
```

Zero config — no API keys needed. Includes water quality ratings, pollution forecasts, and map links.

### air-quality

Check current air quality and pollution levels at NSW monitoring stations. Includes bushfire smoke detection.

```bash
npx skills add agairola/life-skills --skill air-quality
```

Zero config — no API keys needed. Shows AQI category, health advice, and exercise safety.

### sydney-commute

Plan trips, check real-time departures, and find stops on Sydney's public transport network.

```bash
npx skills add agairola/life-skills --skill sydney-commute
```

Works without API keys (provides Google Maps/TfNSW links). Register for a free TfNSW API key for real-time data.

### uv-sun

Check the current UV index and sun safety advice for Australian cities. Includes SPF recommendations and exercise safety.

```bash
npx skills add agairola/life-skills --skill uv-sun
```

Zero config — no API keys needed. Data from ARPANSA.

### park-alerts

Check alerts, closures, and fire bans for NSW National Parks.

```bash
npx skills add agairola/life-skills --skill park-alerts
```

Zero config — no API keys needed. Data from NSW National Parks RSS feed.

### speed-cameras

Find speed cameras and red light cameras near your location in NSW.

```bash
npx skills add agairola/life-skills --skill speed-cameras
```

Zero config — no API keys needed. Covers 70+ fixed camera locations across Sydney.

### dam-levels

Check current dam levels and water storage for Greater Sydney.

```bash
npx skills add agairola/life-skills --skill dam-levels
```

Zero config — no API keys needed. Data from WaterNSW.

### sydney-traffic

Check live traffic incidents, roadworks, and hazards in Sydney.

```bash
npx skills add agairola/life-skills --skill sydney-traffic
```

Works without API keys (provides Live Traffic NSW/Google Maps links). Register for a free TfNSW API key for real-time incident data.

### sydney-tolls

Check Sydney toll road prices and calculate route toll costs.

```bash
npx skills add agairola/life-skills --skill sydney-tolls
```

Zero config — no API keys needed. Covers all 13 Sydney toll roads with peak/off-peak/weekend pricing.

### rental-prices

Check median rental prices for Sydney suburbs. Find affordable areas within your budget.

```bash
npx skills add agairola/life-skills --skill rental-prices
```

Zero config — no API keys needed. Covers 100+ Sydney suburbs with data from NSW DCJ.

### read-aloud

Read any markdown or text file aloud using high-quality neural text-to-speech. Streams audio instantly — no waiting.

```bash
npx skills add agairola/life-skills --skill read-aloud
```

Zero config — auto-installs Kokoro TTS and downloads voice models on first use. 17 voices (American + British English). Runs entirely locally.

### frame-tv

Generate AI artwork or resize existing images for Samsung Frame TV displays. Powered by Google Gemini.

```bash
npx skills add agairola/life-skills --skill frame-tv
```

Requires a Google Gemini API key. Generates art in nano-banana-2 style and handles precision resizing for Frame TV resolution.

### youtube-transcript

Extract transcripts from YouTube videos. Supports any YouTube URL format and raw video IDs.

```bash
npx skills add agairola/life-skills --skill youtube-transcript
```

Zero config — no API keys needed. Outputs plain text or timestamped format. Fetches auto-generated or manual captions.

### transcribe

Transcribe audio or video files to text using OpenAI Whisper running entirely locally. Supports mp3, m4a, wav, mp4, mov, flac, ogg, webm. Outputs plain text, SRT, VTT, or JSON with per-segment/word timestamps.

```bash
npx skills add agairola/life-skills --skill transcribe
```

Zero config — auto-installs on first run and downloads the `large-v3-turbo` model (~800MB) to `~/.cache/huggingface/`. Uses MLX acceleration on Apple Silicon (requires `ffmpeg`) and falls back to `faster-whisper` (CPU) on Intel Macs and Linux. No API keys.

## License

Apache 2.0
