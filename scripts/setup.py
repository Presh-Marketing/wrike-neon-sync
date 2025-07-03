#!/usr/bin/env python3
"""
Setup script for Wrike to Neon sync
"""

import os
import sys
import subprocess

def check_python_version():
    """Check if Python version is 3.7+"""
    if sys.version_info < (3, 7):
        print("❌ Python 3.7 or higher is required")
        print(f"   Current version: {sys.version}")
        return False
    print(f"✅ Python version: {sys.version.split()[0]}")
    return True

def install_requirements():
    """Install required packages"""
    print("\n📦 Installing required packages...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Requirements installed successfully")
        return True
    except subprocess.CalledProcessError:
        print("❌ Failed to install requirements")
        return False

def create_env_file():
    """Create .env file from template if it doesn't exist"""
    if os.path.exists('.env'):
        print("✅ .env file already exists")
        return True
    
    if os.path.exists('config.example'):
        print("\n📝 Creating .env file from template...")
        try:
            with open('config.example', 'r') as source:
                content = source.read()
            
            with open('.env', 'w') as target:
                target.write(content)
            
            print("✅ .env file created")
            print("⚠️  Please edit .env with your actual credentials before running the sync")
            return True
        except Exception as e:
            print(f"❌ Failed to create .env file: {e}")
            return False
    else:
        print("❌ config.example file not found")
        return False

def check_env_variables():
    """Check if required environment variables are set"""
    print("\n🔍 Checking environment variables...")
    
    # Try to load from .env file
    if os.path.exists('.env'):
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            print("   Note: python-dotenv not installed, checking system environment only")
    
    required_vars = [
        'WRIKE_API_TOKEN',
        'NEON_HOST',
        'NEON_DATABASE',
        'NEON_USER',
        'NEON_PASSWORD'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\n💡 Please edit your .env file with the correct values")
        return False
    else:
        print("✅ All required environment variables are set")
        return True

def test_imports():
    """Test if all required modules can be imported"""
    print("\n🔍 Testing imports...")
    
    modules = ['requests', 'psycopg2']
    failed_imports = []
    
    for module in modules:
        try:
            __import__(module)
            print(f"✅ {module}")
        except ImportError:
            failed_imports.append(module)
            print(f"❌ {module}")
    
    if failed_imports:
        print(f"\n❌ Failed to import: {', '.join(failed_imports)}")
        print("   Try running: pip install -r requirements.txt")
        return False
    
    return True

def main():
    """Main setup function"""
    print("🚀 Wrike to Neon Sync Setup")
    print("=" * 40)
    
    # Check Python version
    if not check_python_version():
        return False
    
    # Install requirements
    if not install_requirements():
        return False
    
    # Test imports
    if not test_imports():
        return False
    
    # Create .env file
    if not create_env_file():
        return False
    
    # Check environment variables
    env_check = check_env_variables()
    
    print("\n" + "=" * 40)
    if env_check:
        print("✅ Setup complete! You can now run: python wrike_sync.py")
    else:
        print("⚠️  Setup mostly complete. Please update your .env file and run setup again.")
    
    print("\n📖 For more information, see README.md")
    
    return env_check

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1) 