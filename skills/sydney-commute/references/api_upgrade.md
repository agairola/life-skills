# TfNSW API Key Setup

Get a free API key for real-time Sydney public transport data. Takes ~2 minutes.

## Steps

1. **Sign up** at [opendata.transport.nsw.gov.au](https://opendata.transport.nsw.gov.au)
   - Click "Sign Up" in the top right
   - Fill in name, email, password
   - Verify your email

2. **Create an application**
   - Log in → go to "My Account" → "Applications"
   - Click "Add new application"
   - Name: anything (e.g., "Commute Helper")
   - Description: anything

3. **Subscribe to Trip Planner APIs**
   - Go to "API Catalogue" or "Products"
   - Find "Trip Planner APIs" (free tier: 60,000 calls/day)
   - Click "Subscribe" → select your application → confirm

4. **Copy your API key**
   - Go back to "My Account" → "Applications" → click your app
   - Copy the "API Key" value

## Save credentials

```bash
mkdir -p ~/.config/sydney-commute
cat > ~/.config/sydney-commute/credentials.json << 'CREDS'
{
  "tfnsw_api_key": "<YOUR_API_KEY>"
}
CREDS
chmod 600 ~/.config/sydney-commute/credentials.json
```

Once saved, the commute skill will automatically use your key for real-time data.
