# Google OAuth Setup Guide

This guide will walk you through setting up Google OAuth for the Wrike-Neon sync application with domain restriction to @preshmarketingsolutions.com emails.

## Prerequisites

- Google account with access to Google Cloud Console
- Admin access to preshmarketingsolutions.com domain (for domain verification)

## Step 1: Access Google Cloud Console

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Sign in with your Google account

## Step 2: Create or Select a Project

1. Click the project dropdown at the top of the page
2. Click "NEW PROJECT"
3. Enter project details:
   - **Project name**: "Wrike-Neon Sync App" (or your preferred name)
   - **Organization**: Select your organization if available
4. Click "CREATE"

## Step 3: Enable Required APIs

1. In the left sidebar, go to **APIs & Services** → **Library**
2. Search for "Google+ API" and click on it
3. Click **ENABLE**

## Step 4: Configure OAuth Consent Screen

1. Go to **APIs & Services** → **OAuth consent screen**
2. Select **Internal** for user type (this restricts to your organization only)
3. Click **CREATE**
4. Fill in the application information:
   - **App name**: "Wrike-Neon Sync Dashboard"
   - **User support email**: Your email
   - **Authorized domains**: Add `preshmarketingsolutions.com`
   - **Developer contact information**: Your email
5. Click **SAVE AND CONTINUE**
6. On the Scopes page, click **ADD OR REMOVE SCOPES**
7. Select these scopes:
   - `openid`
   - `email`
   - `profile`
8. Click **UPDATE** and then **SAVE AND CONTINUE**
9. Review and click **BACK TO DASHBOARD**

## Step 5: Create OAuth 2.0 Credentials

1. Go to **APIs & Services** → **Credentials**
2. Click **+ CREATE CREDENTIALS** → **OAuth client ID**
3. Select **Web application** as the application type
4. Configure the client:
   - **Name**: "Wrike-Neon Sync Web Client"
   - **Authorized JavaScript origins**:
     - Add `http://localhost:5000` (for local development)
     - Add your production URL (e.g., `https://sync.preshmarketingsolutions.com`)
   - **Authorized redirect URIs**:
     - Add `http://localhost:5000/callback` (for local development only - safe to use)
     - Add your production URL + `/callback` (e.g., `https://sync.preshmarketingsolutions.com/callback`)
     
   **Security Note**: localhost redirects are safe! They only work on the user's own computer, not your server. See [OAuth Security Explained](./OAUTH_SECURITY_EXPLAINED.md) for details.
5. Click **CREATE**
6. A dialog will show your Client ID and Client Secret. **Save these securely!**

## Step 6: Set Up Environment Variables

1. Create a `.env` file in your project root:
   ```bash
   cp config.example .env
   ```

2. Edit the `.env` file and add your Google OAuth credentials:
   ```
   # Google OAuth Configuration
   GOOGLE_CLIENT_ID=your_client_id_here.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=your_client_secret_here
   
   # Generate a secure secret key
   SECRET_KEY=your_generated_secret_key_here
   
   # Update for production
   APP_URL=http://localhost:5000  # Change to your production URL when deploying
   ```

3. Generate a secure secret key (in Python):
   ```python
   import secrets
   print(secrets.token_urlsafe(32))
   ```

## Step 7: Install and Run Redis (for session storage)

### Local Development (macOS):
```bash
# Install Redis
brew install redis

# Start Redis
brew services start redis
```

### Local Development (Ubuntu/Debian):
```bash
# Install Redis
sudo apt-get update
sudo apt-get install redis-server

# Start Redis
sudo systemctl start redis
```

### Production:
Consider using a managed Redis service like:
- Redis Cloud
- AWS ElastiCache
- Google Cloud Memorystore
- Heroku Redis

Update your `.env` with the Redis URL:
```
REDIS_URL=redis://username:password@your-redis-host:6379
```

## Step 8: Test the Setup

1. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the secure version of the app:
   ```bash
   python app_secure.py
   ```

3. Navigate to `http://localhost:5000`
4. Click "Sign in with Google"
5. You should be redirected to Google's login page
6. Sign in with a @preshmarketingsolutions.com email
7. You should be redirected back to the dashboard

## Step 9: Troubleshooting

### Common Issues:

1. **"Access blocked" error**:
   - Ensure the OAuth consent screen is configured properly
   - Verify the authorized domains include preshmarketingsolutions.com

2. **"Redirect URI mismatch" error**:
   - Check that the redirect URI in your app matches exactly what's configured in Google Cloud Console
   - Include both http://localhost:5000/callback and your production URL

3. **"Invalid client" error**:
   - Verify your Client ID and Client Secret are correct in the .env file
   - Ensure there are no extra spaces or quotes

4. **Domain restriction not working**:
   - The app checks for @preshmarketingsolutions.com emails in the code
   - Check app_secure.py line ~285 for the domain verification logic

### Security Checklist:

- [ ] Never commit `.env` file to version control
- [ ] Use strong, unique SECRET_KEY
- [ ] Enable 2FA on Google Cloud Console account
- [ ] Regularly rotate OAuth credentials
- [ ] Monitor OAuth usage in Google Cloud Console
- [ ] Use HTTPS in production (required for OAuth)

## Step 10: Production Deployment

When deploying to production:

1. Update the OAuth credentials in Google Cloud Console:
   - Add your production domain to authorized JavaScript origins
   - Add your production callback URL to authorized redirect URIs

2. Update your production `.env`:
   ```
   FLASK_ENV=production
   APP_URL=https://your-production-domain.com
   ```

3. Ensure HTTPS is configured (required for Google OAuth in production)

4. Set up proper Redis instance (not local Redis)

## Additional Security Considerations

1. **Separate OAuth Apps**: Consider creating separate OAuth credentials for development and production:
   - Development OAuth: Includes localhost redirects
   - Production OAuth: Only production domain redirects
   - This way, you can remove localhost from production without affecting development

2. **API Quotas**: Monitor your API usage in Google Cloud Console
3. **Audit Logs**: Enable audit logging in Google Cloud Console
4. **Regular Reviews**: Periodically review authorized users and revoke access as needed
5. **Backup Authentication**: Consider implementing an admin bypass for emergencies

## Next Steps

After completing the Google OAuth setup:

1. Test with multiple @preshmarketingsolutions.com accounts
2. Set up monitoring and alerts
3. Document the login process for end users
4. Configure automated backups
5. Set up proper logging and error tracking

## Support

For issues with:
- Google OAuth setup: Check [Google Identity Platform docs](https://developers.google.com/identity/protocols/oauth2)
- Flask-Login: See [Flask-Login documentation](https://flask-login.readthedocs.io/)
- Our implementation: Check `app_secure.py` for the authentication logic 