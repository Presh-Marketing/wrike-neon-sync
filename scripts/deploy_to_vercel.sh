#!/bin/bash

echo "🚀 Deploying presh-api-dash to Vercel"
echo "===================================="

# Extract Redis URL from the redis-cli format
REDIS_URL="rediss://default:AXWqAAIjcDFhOThmMDI3ZDBiOTA0ZmQyYjkwOTY2OWJhZGY5ZWZiOHAxMA@great-peacock-30122.upstash.io:6379"

echo ""
echo "📋 Environment variables you'll need:"
echo "------------------------------------"
echo "REDIS_URL=$REDIS_URL"
echo ""
echo "From your .env file, you'll also need:"
echo "- GOOGLE_CLIENT_ID"
echo "- GOOGLE_CLIENT_SECRET" 
echo "- NEON_HOST"
echo "- NEON_DATABASE"
echo "- NEON_USER"
echo "- NEON_PASSWORD"
echo "- WRIKE_API_TOKEN"
echo "- HUBSPOT_API_KEY (if using)"
echo ""
echo "Plus generate a SECRET_KEY:"
python scripts/generate_secret_key.py

echo ""
echo "📝 Deployment steps:"
echo "-------------------"
echo "1. Run: vercel --name presh-api-dash"
echo "2. When prompted for environment variables, add all the above"
echo "3. After deployment, update Google OAuth redirect URI to:"
echo "   https://presh-api-dash.vercel.app/callback"
echo ""
echo "Ready? Press Enter to see the Vercel deployment command..."
read

echo ""
echo "Run this command:"
echo "vercel --name presh-api-dash" 