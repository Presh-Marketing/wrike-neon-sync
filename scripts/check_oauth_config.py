#!/usr/bin/env python3
"""
OAuth Configuration Checker
This script helps verify that your Google OAuth configuration is set up correctly.
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

def check_config():
    """Check OAuth configuration and provide feedback"""
    print("=" * 50)
    print("Google OAuth Configuration Checker")
    print("=" * 50)
    
    issues = []
    
    # Check Google Client ID
    client_id = os.environ.get('GOOGLE_CLIENT_ID')
    if not client_id:
        issues.append("❌ GOOGLE_CLIENT_ID is not set")
    elif not client_id.endswith('.apps.googleusercontent.com'):
        issues.append("⚠️  GOOGLE_CLIENT_ID doesn't look like a valid Google Client ID")
    else:
        print(f"✅ GOOGLE_CLIENT_ID: {client_id[:20]}...")
    
    # Check Google Client Secret
    client_secret = os.environ.get('GOOGLE_CLIENT_SECRET')
    if not client_secret:
        issues.append("❌ GOOGLE_CLIENT_SECRET is not set")
    elif len(client_secret) < 20:
        issues.append("⚠️  GOOGLE_CLIENT_SECRET seems too short")
    else:
        print(f"✅ GOOGLE_CLIENT_SECRET: {'*' * 20}...")
    
    # Check Secret Key
    secret_key = os.environ.get('SECRET_KEY')
    if not secret_key:
        issues.append("❌ SECRET_KEY is not set")
    elif secret_key == 'dev-secret-key':
        issues.append("⚠️  SECRET_KEY is using the default value - please change it")
    elif len(secret_key) < 32:
        issues.append("⚠️  SECRET_KEY should be at least 32 characters long")
    else:
        print(f"✅ SECRET_KEY: {'*' * 20}...")
    
    # Check Flask Environment
    flask_env = os.environ.get('FLASK_ENV')
    if flask_env:
        print(f"✅ FLASK_ENV: {flask_env}")
    else:
        issues.append("⚠️  FLASK_ENV is not set (recommended: 'production')")
    
    print("\n" + "=" * 50)
    
    if issues:
        print("Issues found:")
        for issue in issues:
            print(f"  {issue}")
        print("\nTo fix these issues:")
        print("1. Make sure you have a .env file with your configuration")
        print("2. Set up Google OAuth credentials in Google Cloud Console")
        print("3. Add your domain to authorized origins and redirect URIs")
        print("4. Generate a strong SECRET_KEY")
        return False
    else:
        print("✅ All configuration looks good!")
        return True

def show_oauth_setup_instructions():
    """Show Google OAuth setup instructions"""
    print("\n" + "=" * 50)
    print("Google OAuth Setup Instructions")
    print("=" * 50)
    print("1. Go to Google Cloud Console: https://console.cloud.google.com/")
    print("2. Create a new project or select an existing one")
    print("3. Enable the Google+ API")
    print("4. Go to 'Credentials' → 'Create Credentials' → 'OAuth 2.0 Client IDs'")
    print("5. Set Application Type to 'Web application'")
    print("6. Add authorized origins:")
    print("   - https://presh-api-dash.vercel.app")
    print("7. Add authorized redirect URIs:")
    print("   - https://presh-api-dash.vercel.app/callback")
    print("8. Copy the Client ID and Client Secret to your .env file")
    print("\nExample .env file:")
    print("GOOGLE_CLIENT_ID=your_client_id.apps.googleusercontent.com")
    print("GOOGLE_CLIENT_SECRET=your_client_secret")
    print("SECRET_KEY=your_generated_secret_key")
    print("FLASK_ENV=production")

if __name__ == "__main__":
    if not check_config():
        show_oauth_setup_instructions()
        sys.exit(1)
    else:
        print("\n🎉 Your OAuth configuration is ready!")
        print("You can now deploy your app to Vercel.") 