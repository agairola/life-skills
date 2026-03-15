# TfNSW API Key Setup (Traffic)

Get a free API key for real-time Sydney traffic incident data. Takes ~2 minutes.

## Steps

1. **Sign up** at [opendata.transport.nsw.gov.au](https://opendata.transport.nsw.gov.au)
   - Click "Sign Up" in the top right
   - Fill in name, email, password
   - Verify your email

2. **Create an application**
   - Log in → go to "My Account" → "Applications"
   - Click "Add new application"
   - Name: anything (e.g., "Traffic Helper")
   - Description: anything

3. **Subscribe to Traffic APIs**
   - Go to "API Catalogue" or "Products"
   - Find "Traffic" APIs (free tier)
   - Click "Subscribe" → select your application → confirm

4. **Copy your API key**
   - Go back to "My Account" → "Applications" → click your app
   - Copy the "API Key" value

## Save credentials

```bash
mkdir -p ~/.config/sydney-traffic
cat > ~/.config/sydney-traffic/credentials.json << 'CREDS'
{
  "tfnsw_api_key": "<YOUR_API_KEY>"
}
CREDS
chmod 600 ~/.config/sydney-traffic/credentials.json
```

Once saved, the traffic skill will automatically use your key for real-time incident data.
