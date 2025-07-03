#!/usr/bin/env python3
"""
Test sync with limited records
"""

import subprocess
import sys

def test_sync(limit=5):
    """Run sync with limited records for testing"""
    print(f"🧪 Testing sync with {limit} records per entity type...")
    print("=" * 50)
    
    try:
        result = subprocess.run([
            sys.executable, 'wrike_sync.py', str(limit)
        ], capture_output=False, text=True)
        
        if result.returncode == 0:
            print(f"\n✅ Test sync completed successfully!")
        else:
            print(f"\n❌ Test sync failed with return code: {result.returncode}")
            
    except Exception as e:
        print(f"❌ Error running test sync: {e}")

def main():
    """Main test function"""
    limit = 5  # Default test limit
    
    if len(sys.argv) > 1:
        try:
            limit = int(sys.argv[1])
        except ValueError:
            print("Usage: python test_sync.py [limit]")
            return
    
    test_sync(limit)

if __name__ == '__main__':
    main() 