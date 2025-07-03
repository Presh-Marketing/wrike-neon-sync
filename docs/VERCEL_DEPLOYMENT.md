# Quick Vercel Deployment Guide (5-10 minutes)

## Option 1: Deploy with Upstash Redis (Recommended - 5 min) ✅

### Step 1: Set up Upstash Redis (Free tier available)
1. Go to [Upstash Console](https://console.upstash.com/)
2. Sign up/Login
3. Click "Create Database"
4. Select your region
5. Copy the **Redis URL** (looks like: `redis://default:xxxxx@us1-xxx.upstash.io:6379`)

### Step 2: Prepare for Vercel
1. Create `vercel.json` in your project root:
```json
{
  "version": 2,
  "builds": [
    {
      "src": "app_secure.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "app_secure.py"
    }
  ]
}
```

2. Create `requirements.txt` if not exists (already done ✓)

### Step 3: Deploy to Vercel
```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
vercel

# When prompted, add these environment variables:
# - GOOGLE_CLIENT_ID (your ID)
# - GOOGLE_CLIENT_SECRET (your secret)
# - SECRET_KEY (generate with: python -c "import secrets; print(secrets.token_urlsafe(32))")
# - REDIS_URL (from Upstash)
# - FLASK_ENV=production
```

### Step 4: Update Google OAuth
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Add your Vercel URL to authorized redirects:
   - `https://your-app.vercel.app/callback`

## Option 2: Deploy WITHOUT Redis (More Work) 🔧

If you really don't want Redis, you'll need to modify the app to use JWT tokens:

```python
# Create app_vercel.py (simplified version)
# This removes Redis dependency but requires code changes
# Contact me if you want this approach
```

## Option 3: Alternative Platforms (Easier) 🚀

These platforms support Redis natively:

### Railway (Recommended Alternative)
```bash
# One-click deploy with Redis included
railway login
railway init
railway add redis
railway up
```

### Render
- Supports Redis
- Free tier available
- Simple deployment

### Heroku
- Full Redis support
- Well-documented

## Quick Security Checklist for Vercel

- [x] HTTPS enabled by default ✅
- [x] Environment variables encrypted ✅
- [ ] Add production domain to Google OAuth
- [ ] Remove localhost from Google OAuth redirects
- [ ] Set FLASK_ENV=production

## Vercel Environment Variables

Add these in Vercel Dashboard → Settings → Environment Variables:

```
GOOGLE_CLIENT_ID=your_id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your_secret
SECRET_KEY=generate_this_value
REDIS_URL=redis://default:xxx@us1-xxx.upstash.io:6379
FLASK_ENV=production

# Your existing Neon/Wrike variables
NEON_HOST=xxx
NEON_DATABASE=xxx
NEON_USER=xxx
NEON_PASSWORD=xxx
WRIKE_API_TOKEN=xxx
```

## Troubleshooting

### "Function timeout" error
- Vercel has 10s timeout for free tier
- Upgrade to Pro for 60s timeout
- Or use Edge Functions

### "Module not found" error
- Make sure all imports are in requirements.txt
- Vercel uses Python 3.9 by default

### Redis connection issues
- Double-check Upstash Redis URL
- Ensure it includes password

## Done! 🎉

Your app should now be live at `https://your-app.vercel.app`

Total time: ~5-10 minutes with Upstash Redis 