# Location Flow (IMPORTANT — follow this exactly)

Before running any location-based query, you MUST resolve the user's location. Follow these steps in order — do NOT skip ahead to IP fallback.

**Step 1: Check what the user already provided.**
- User shared a location pin (Telegram, WhatsApp, Signal, Discord)? Extract lat/lng → use `--lat` / `--lng`. Done.
- User mentioned a suburb, city, or address? → use `--location`. Done.
- User mentioned a postcode? → use `--postcode` (if supported). Done.

**Step 2: User said "near me" or "nearby" but gave no location.**
Ask them to share location. Tailor the ask to their platform:
- Telegram: "Tap the paperclip icon → Location → Send My Current Location"
- WhatsApp: "Tap the + button → Location → Send Your Current Location"
- Signal: "Tap the + button → Location"
- Discord/terminal: "What suburb or postcode are you near?"

Wait for their response. Do not proceed without it.

**Step 3: User can't or won't share location.**
Ask: "No worries — what suburb or postcode are you near?" Wait for response.

**Step 4: User refuses to give any location info.**
Only now fall back to auto-detect (no location args). This uses IP geolocation which is city-level only and often wrong. If the result comes back with `confidence: "low"`, tell the user: "I got an approximate location of [city] from your IP but it may not be accurate. Can you tell me your suburb or postcode for better results?"

**Never silently use IP geolocation when you can ask the user instead.**
