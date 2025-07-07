#!/bin/bash

# Deploy Full-Featured API Sync Monitor to Vercel

echo "🚀 Deploying Full-Featured API Sync Monitor to Vercel..."

# Check if Vercel CLI is installed
if ! command -v vercel &> /dev/null; then
    echo "❌ Vercel CLI is not installed. Please install it first:"
    echo "npm install -g vercel"
    exit 1
fi

# Check if git is clean
if [[ -n $(git status -s) ]]; then
    echo "⚠️  Warning: You have uncommitted changes. Consider committing them first."
    read -p "Do you want to continue anyway? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Deployment cancelled."
        exit 1
    fi
fi

# Check if required files exist
echo "📋 Checking required files..."
required_files=(
    "app_vercel_simple.py"
    "vercel.json"
    "requirements.txt"
    "templates/index_secure.html"
    "templates/error.html"
    "static/css/dashboard-animations.css"
    "static/js/dashboard-utils.js"
)

for file in "${required_files[@]}"; do
    if [[ ! -f "$file" ]]; then
        echo "❌ Required file missing: $file"
        exit 1
    fi
done

echo "✅ All required files found"

# Check environment variables
echo "🔐 Checking environment variables..."
required_env_vars=(
    "GOOGLE_CLIENT_ID"
    "GOOGLE_CLIENT_SECRET"
    "SECRET_KEY"
)

missing_vars=()
for var in "${required_env_vars[@]}"; do
    if [[ -z "${!var}" ]]; then
        missing_vars+=("$var")
    fi
done

if [[ ${#missing_vars[@]} -gt 0 ]]; then
    echo "⚠️  Warning: The following environment variables are not set locally:"
    printf '%s\n' "${missing_vars[@]}"
    echo ""
    echo "Make sure to set these in your Vercel dashboard:"
    echo "https://vercel.com/dashboard -> Your Project -> Settings -> Environment Variables"
    echo ""
    read -p "Continue with deployment? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Deployment cancelled."
        exit 1
    fi
fi

# Display deployment information
echo ""
echo "📊 Deployment Summary:"
echo "====================="
echo "App: Full-Featured API Sync Monitor"
echo "Main file: app_vercel_simple.py"
echo "Features:"
echo "  ✅ OAuth Authentication"
echo "  ✅ All Sync Operations"
echo "  ✅ Real-time Updates (EventSource)"
echo "  ✅ Static File Serving"
echo "  ✅ Complete API Endpoints"
echo "  ✅ Professional Dashboard"
echo ""

# Deploy to Vercel
echo "🚀 Starting deployment..."
vercel --prod

deployment_status=$?

if [[ $deployment_status -eq 0 ]]; then
    echo ""
    echo "🎉 Deployment successful!"
    echo ""
    echo "🔗 Your app should now be available at:"
    echo "   https://presh-api-dash.vercel.app"
    echo ""
    echo "📝 Post-deployment checklist:"
    echo "  1. Test OAuth login with your @preshmarketingsolutions.com email"
    echo "  2. Verify all sync operations are visible in the dashboard"
    echo "  3. Check that static files (CSS/JS) are loading properly"
    echo "  4. Test real-time updates with EventSource"
    echo "  5. Verify all API endpoints are working"
    echo ""
    echo "🐛 If you encounter issues:"
    echo "  - Check environment variables in Vercel dashboard"
    echo "  - Review function logs in Vercel dashboard"
    echo "  - Ensure all sync scripts are present in the project"
    echo ""
    echo "✨ Features now available:"
    echo "  - HubSpot sync operations (companies, contacts, deals, line items)"
    echo "  - Wrike sync operations (clients, projects, tasks, deliverables)"
    echo "  - Real-time dashboard updates"
    echo "  - Professional UI with animations"
    echo "  - Complete activity logging"
    echo ""
else
    echo ""
    echo "❌ Deployment failed!"
    echo "Please check the error messages above and try again."
    echo ""
    echo "Common issues:"
    echo "  - Missing environment variables"
    echo "  - Incorrect file permissions"
    echo "  - Network connectivity issues"
    echo "  - Vercel CLI authentication problems"
    echo ""
    echo "Try running: vercel login"
    exit 1
fi 