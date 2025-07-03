#!/usr/bin/env python3
"""
Test script for Google OAuth configuration
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

# Try to load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("Note: python-dotenv not installed. Make sure environment variables are set.")

def test_google_oauth_config():
    """Test Google OAuth configuration"""
    print("Google OAuth Configuration Test")
    print("=" * 50)
    
    # Check required environment variables
    required_vars = {
        'GOOGLE_CLIENT_ID': 'Google Client ID',
        'GOOGLE_CLIENT_SECRET': 'Google Client Secret',
        'SECRET_KEY': 'Flask Secret Key',
        'REDIS_URL': 'Redis URL'
    }
    
    missing_vars = []
    configured_vars = []
    
    for var, description in required_vars.items():
        value = os.environ.get(var)
        if not value:
            missing_vars.append(f"- {var} ({description})")
        else:
            # Mask sensitive values for display
            if var == 'GOOGLE_CLIENT_SECRET' or var == 'SECRET_KEY':
                display_value = value[:4] + '...' + value[-4:] if len(value) > 8 else '***'
            elif var == 'GOOGLE_CLIENT_ID':
                display_value = value.split('.')[0] + '.apps.googleusercontent.com' if '.apps.googleusercontent.com' in value else value
            else:
                display_value = value
            configured_vars.append(f"✓ {var}: {display_value}")
    
    # Display results
    if configured_vars:
        print("\nConfigured variables:")
        for var in configured_vars:
            print(var)
    
    if missing_vars:
        print("\n❌ Missing required variables:")
        for var in missing_vars:
            print(var)
        print("\nPlease set these in your .env file or environment.")
        return False
    
    # Validate Google Client ID format
    client_id = os.environ.get('GOOGLE_CLIENT_ID', '')
    if not client_id.endswith('.apps.googleusercontent.com'):
        print("\n⚠️  Warning: GOOGLE_CLIENT_ID should end with '.apps.googleusercontent.com'")
        print(f"   Current value: {client_id}")
    
    # Test Redis connection
    print("\nTesting Redis connection...")
    try:
        import redis
        redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379')
        r = redis.from_url(redis_url)
        r.ping()
        print("✓ Redis connection successful")
    except ImportError:
        print("❌ Redis package not installed. Run: pip install redis")
        return False
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        print("   Make sure Redis is running.")
        return False
    
    # Check for .env file
    if os.path.exists('.env'):
        print("\n✓ .env file found")
    else:
        print("\n⚠️  No .env file found. Create one from config.example:")
        print("   cp config.example .env")
    
    # Check Flask environment
    flask_env = os.environ.get('FLASK_ENV', 'production')
    print(f"\nFlask environment: {flask_env}")
    
    if flask_env == 'development':
        print("⚠️  Running in development mode. Set FLASK_ENV=production for deployment.")
    
    print("\n" + "=" * 50)
    print("✓ Google OAuth configuration test complete!")
    print("\nNext steps:")
    print("1. Run the secure app: python app_secure.py")
    print("2. Navigate to http://localhost:5000")
    print("3. Click 'Sign in with Google'")
    print("4. Test with a @preshmarketingsolutions.com email")
    
    return True

if __name__ == '__main__':
    success = test_google_oauth_config()
    sys.exit(0 if success else 1) 