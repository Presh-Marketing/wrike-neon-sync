# Vercel Deployment Fix Instructions

## What Was Wrong
- Port 5001 is for local development only - Vercel is serverless and doesn't use ports
- The `app_secure.py` was configured for traditional servers, not serverless
- OAuth redirect URIs need to match production domain exactly

## What I Fixed
1. Created `app_vercel.py` - a simplified version optimized for Vercel:
   - Removed threading (doesn't work in serverless)
   - Removed Talisman HTTPS forcing (Vercel handles this)
   - Fixed OAuth redirect URI handling for production
   - Added both `/callback` and `/oauth2callback` routes
   - Simplified to show login works but sync operations need a real server

2. Updated `vercel.json` to use `app_vercel.py` instead of `app_secure.py`

## Steps to Deploy

### 1. Update Google OAuth Settings
Go to [Google Cloud Console](https://console.cloud.google.com/) and add BOTH:
```
https://presh-api-dash.vercel.app/callback
https://presh-api-dash.vercel.app/oauth2callback
```

### 2. Deploy to Vercel
```bash
vercel --prod
```

### 3. Verify Environment Variables in Vercel Dashboard
Go to https://vercel.com/dashboard and check your project has:
- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- `SECRET_KEY`
- `REDIS_URL` (your Upstash Redis URL)
- `FLASK_ENV` = `production`
- All your Neon and Wrike variables

### 4. Test the Deployment
1. Visit https://presh-api-dash.vercel.app
2. Click "Sign in with Google"
3. Use your @preshmarketingsolutions.com email
4. You should see the dashboard (sync operations will show as unavailable on Vercel)

## Important Notes

### Why Sync Operations Don't Work on Vercel
- Vercel has a 10-second timeout (30s on Pro)
- Your sync operations take 1-5 minutes
- Vercel is serverless - no background processes

### For Full Functionality
Deploy `app_secure.py` (not the Vercel version) to:
- **Railway** (recommended) - Easy deployment with Redis included
- **Render** - Good free tier with background workers
- **DigitalOcean App Platform** - Simple deployment
- **Any VPS with Python** - Full control

### Local Development
For local testing with port 5001:
```bash
python app_secure.py
```
Visit http://localhost:5001

## Troubleshooting

### "redirect_uri_mismatch" Error
- Make sure you added BOTH callback URLs to Google OAuth
- Wait 1-2 minutes for Google to update
- Clear your browser cookies

### 500 Error
- Check Vercel Function logs: `vercel logs`
- Verify all environment variables are set
- Check Redis connection is working

### "Function timeout" Error
- This is expected for sync operations
- Use the deployment for authentication testing only
- Deploy to a real server for production use 