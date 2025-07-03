# Vercel Deployment Steps for presh-api-dash

## ✅ What you have ready:
- Google OAuth configured ✓
- Redis URL from Upstash ✓  
- Environment variables in .env ✓

## 🚀 Step 1: Deploy to Vercel

Run this command:
```bash
vercel
```

When prompted:
- **Set up and deploy?** → Yes
- **Which scope?** → Select your account
- **Link to existing project?** → No
- **What's your project's name?** → `presh-api-dash`
- **In which directory is your code located?** → `./` (just press Enter)
- **Want to modify settings?** → No

## 📋 Step 2: Add Environment Variables

When Vercel prompts you, add these environment variables:

### Redis & Security:
```
REDIS_URL=rediss://default:AXWqAAIjcDFhOThmMDI3ZDBiOTA0ZmQyYjkwOTY2OWJhZGY5ZWZiOHAxMA@great-peacock-30122.upstash.io:6379
SECRET_KEY=5_Ej_kzEWx_mSDKmHvyQBwWbBZf1ldrBUS8iNnSDJ5g
FLASK_ENV=production
```

### From your .env file, copy these:
```
GOOGLE_CLIENT_ID=your_value_from_env
GOOGLE_CLIENT_SECRET=your_value_from_env
NEON_HOST=your_value_from_env
NEON_DATABASE=your_value_from_env
NEON_USER=your_value_from_env
NEON_PASSWORD=your_value_from_env
NEON_PORT=5432
WRIKE_API_TOKEN=your_value_from_env
```

### Optional (if using HubSpot):
```
HUBSPOT_API_KEY=your_value_from_env
```

## 🔧 Step 3: Update Google OAuth

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Navigate to APIs & Services → Credentials
3. Click on your OAuth 2.0 Client ID
4. Add to Authorized redirect URIs:
   ```
   https://presh-api-dash.vercel.app/callback
   ```
5. Click "SAVE"

## 🎯 Step 4: Test Your Deployment

1. Visit: https://presh-api-dash.vercel.app
2. Click "Sign in with Google"
3. Sign in with a @preshmarketingsolutions.com email
4. You should see your dashboard!

## 🔍 Troubleshooting

### If you get CSP errors (Content Security Policy):
- The fix has been applied! Just redeploy:
  ```bash
  vercel --prod
  ```

### If you get "redirect_uri_mismatch":
- Make sure you added the EXACT URL to Google OAuth
- Wait 1-2 minutes for Google to update

### If you get Redis connection error:
- Note: Your Redis URL uses TLS (rediss:// with double 's')
- Make sure you copied it exactly
- Check all environment variables are set in Vercel dashboard

### If you get 500 error on first load:
- Check Vercel Functions logs: `vercel logs`
- Ensure ALL environment variables are set correctly
- Missing GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET will cause this

### If login works but syncs timeout:
- Vercel free tier has 10s limit
- Consider upgrading to Pro (60s limit)
- Or use Railway/Render for long-running syncs

## ✅ Success!

Your secure dashboard will be live at:
**https://presh-api-dash.vercel.app**

Need help? The app is configured with:
- ✅ Google Sign-In (domain restricted)
- ✅ Secure sessions (Redis)
- ✅ HTTPS automatic
- ✅ All security features enabled 