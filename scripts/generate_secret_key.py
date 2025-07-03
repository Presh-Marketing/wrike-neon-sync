#!/usr/bin/env python3
"""Generate a secure secret key for Flask"""

import secrets

print("\n🔐 Your SECRET_KEY for Vercel deployment:")
print("=" * 50)
print(secrets.token_urlsafe(32))
print("=" * 50)
print("\nCopy this value and add it to your Vercel environment variables!")
print("Never share this key or commit it to version control.\n") 