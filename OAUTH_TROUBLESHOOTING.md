# OAuth "Missing Code Parameter" Troubleshooting Guide

## The Problem
You're getting this error: `(missing_code) Missing code parameter in response.`

This means Google OAuth is not sending the authorization code back to your callback URL. This is typically a configuration issue.

## Immediate Diagnostics

### 1. Check OAuth Configuration Status
Visit: `https://presh-api-dash.vercel.app/debug/oauth`

This will show you:
- Whether your OAuth credentials are properly set in Vercel
- Current session state
- Environment variable status

### 2. Check Health Endpoint
Visit: `https://presh-api-dash.vercel.app/health`

Look for `oauth_configured: true` and check the `config_status` section.

## Most Likely Causes & Solutions

### 1. **Environment Variables Not Set in Vercel**
**Symptoms**: `/debug/oauth` shows `client_id_set: false` or `client_secret_set: false`

**Solution**:
1. Go to your Vercel project dashboard
2. Navigate to Settings → Environment Variables
3. Add these variables:
   ```
   GOOGLE_CLIENT_ID=your_client_id.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=your_client_secret
   SECRET_KEY=your_generated_secret_key
   FLASK_ENV=production
   ```
4. Redeploy your app

### 2. **Google Cloud Console Configuration Issues**
**Symptoms**: OAuth redirects to callback but without code parameter

**Solution**:
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Navigate to APIs & Services → Credentials
3. Find your OAuth 2.0 Client ID and click edit
4. Verify these exact settings:

   **Authorized JavaScript origins:**
   ```
   https://presh-api-dash.vercel.app
   ```

   **Authorized redirect URIs:**
   ```
   https://presh-api-dash.vercel.app/callback
   ```

   ⚠️ **Important**: No trailing slashes, must be exact match!

### 3. **Domain Restriction Issues**
**Symptoms**: OAuth works but redirects with error instead of code

**Solution**:
1. In Google Cloud Console, check if you have domain restrictions
2. Make sure `preshmarketingsolutions.com` is allowed
3. Or temporarily remove domain restrictions for testing

### 4. **App Not Verified with Google**
**Symptoms**: Google shows "This app isn't verified" warning

**Solution**:
1. For testing: Click "Advanced" → "Go to [your app] (unsafe)"
2. For production: Submit your app for verification in Google Cloud Console

## Step-by-Step Debugging

### Step 1: Verify Environment Variables
```bash
# Check if your variables are set
curl https://presh-api-dash.vercel.app/debug/oauth
```

Look for:
- `GOOGLE_CLIENT_ID: "SET"`
- `GOOGLE_CLIENT_SECRET: "SET"`
- `SECRET_KEY: "SET"`

### Step 2: Test OAuth Flow Manually
1. Go to `https://presh-api-dash.vercel.app/login`
2. Open browser dev tools (F12)
3. Watch the network tab during redirect
4. Check if you get redirected to Google
5. Check if Google redirects back with `code` parameter

### Step 3: Check Google Cloud Console Logs
1. Go to Google Cloud Console
2. Navigate to APIs & Services → Credentials
3. Check if your OAuth app is being used
4. Look for any error messages

### Step 4: Verify Redirect URI Exactly
The redirect URI in your Google Cloud Console MUST exactly match:
```
https://presh-api-dash.vercel.app/callback
```

Common mistakes:
- `http://` instead of `https://`
- Trailing slash: `https://presh-api-dash.vercel.app/callback/`
- Wrong domain or subdomain
- Missing `/callback` path

## Quick Test Commands

### Test 1: Check if app is running
```bash
curl https://presh-api-dash.vercel.app/health
```

### Test 2: Check OAuth configuration
```bash
curl https://presh-api-dash.vercel.app/debug/oauth
```

### Test 3: Check environment variables in Vercel
Go to Vercel dashboard → Your Project → Settings → Environment Variables

## If Still Not Working

### Enable Debug Mode
1. In Vercel, set environment variable: `FLASK_ENV=development`
2. Redeploy
3. Try the OAuth flow again
4. Check Vercel function logs for more detailed error messages

### Check Browser Console
1. Open browser dev tools (F12)
2. Go to Console tab
3. Try logging in
4. Look for any JavaScript errors

### Test with Different Browser
Try the OAuth flow in an incognito/private browsing window to rule out cookie/cache issues.

## Common Error Messages and Solutions

| Error | Cause | Solution |
|-------|-------|----------|
| `missing_code` | Google not sending code | Check redirect URI configuration |
| `invalid_client` | Wrong client ID/secret | Verify environment variables |
| `redirect_uri_mismatch` | Redirect URI doesn't match | Fix Google Cloud Console settings |
| `access_denied` | User denied access | Normal user behavior |
| `invalid_request` | Malformed OAuth request | Check OAuth configuration |

## Next Steps After Fixing
1. Test the OAuth flow end-to-end
2. Verify user can log in successfully
3. Check that sessions persist correctly
4. Test logout functionality

Let me know which diagnostic step reveals the issue! 