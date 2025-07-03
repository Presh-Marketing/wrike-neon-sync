#!/usr/bin/env python3
"""
Test script to verify Wrike API and Neon database connectivity
"""

import os
import requests
import psycopg2

# Try to load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

def test_wrike_api():
    """Test Wrike API connectivity"""
    print("🔍 Testing Wrike API connection...")
    
    token = os.getenv('WRIKE_API_TOKEN')
    if not token:
        print("❌ WRIKE_API_TOKEN not set")
        return False
    
    try:
        headers = {
            'Authorization': f'bearer {token}',
            'Content-Type': 'application/json'
        }
        
        response = requests.get(
            'https://www.wrike.com/api/v4/spaces',
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            spaces = data.get('data', [])
            print(f"✅ Connected to Wrike API")
            print(f"   Found {len(spaces)} spaces")
            
            # Check for Production space
            production_space = None
            for space in spaces:
                if space.get('title') == 'Production':
                    production_space = space
                    break
            
            if production_space:
                print(f"✅ Found Production space: {production_space.get('id')}")
            else:
                print("⚠️  Production space not found")
                print("   Available spaces:")
                for space in spaces[:5]:  # Show first 5 spaces
                    print(f"   - {space.get('title')} ({space.get('id')})")
            
            return True
        else:
            print(f"❌ Wrike API error: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error connecting to Wrike: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_database():
    """Test Neon database connectivity"""
    print("\n🔍 Testing Neon database connection...")
    
    required_vars = ['NEON_HOST', 'NEON_DATABASE', 'NEON_USER', 'NEON_PASSWORD']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Missing database environment variables: {missing_vars}")
        return False
    
    db_config = {
        'host': os.getenv('NEON_HOST'),
        'database': os.getenv('NEON_DATABASE'),
        'user': os.getenv('NEON_USER'),
        'password': os.getenv('NEON_PASSWORD'),
        'port': os.getenv('NEON_PORT', 5432),
        'sslmode': 'require'
    }
    
    try:
        conn = psycopg2.connect(**db_config)
        print("✅ Connected to Neon database")
        
        # Test basic query
        with conn.cursor() as cursor:
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]
            print(f"   Database version: {version.split(',')[0]}")
        
        # Check if required schemas/tables exist
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'projects'
                ORDER BY table_name;
            """)
            tables = [row[0] for row in cursor.fetchall()]
            
            expected_tables = ['clients', 'parentprojects', 'childprojects', 'tasks', 'deliverables']
            
            print(f"   Found {len(tables)} tables in projects schema:")
            for table in tables:
                if table in expected_tables:
                    print(f"   ✅ {table}")
                else:
                    print(f"   📋 {table}")
            
            missing_tables = [t for t in expected_tables if t not in tables]
            if missing_tables:
                print(f"   ⚠️  Missing expected tables: {missing_tables}")
        
        conn.close()
        return True
        
    except psycopg2.Error as e:
        print(f"❌ Database error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Connection Test Suite")
    print("=" * 40)
    
    wrike_ok = test_wrike_api()
    db_ok = test_database()
    
    print("\n" + "=" * 40)
    if wrike_ok and db_ok:
        print("✅ All tests passed! You're ready to run the sync.")
    else:
        print("❌ Some tests failed. Please check your configuration.")
        if not wrike_ok:
            print("   - Check your WRIKE_API_TOKEN")
        if not db_ok:
            print("   - Check your Neon database credentials")
    
    print("\n💡 To run the full sync: python wrike_sync.py")

if __name__ == '__main__':
    main() 