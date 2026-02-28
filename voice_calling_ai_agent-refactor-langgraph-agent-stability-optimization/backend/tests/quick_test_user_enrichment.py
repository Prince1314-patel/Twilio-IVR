"""
Quick Verification Test for Progressive User Enrichment
========================================================

This script tests the core functionality of the progressive user enrichment feature:
1. User creation with nullable name
2. User lookup by mobile number
3. Name update (progressive enrichment)
4. Appointment history retrieval

Run this to verify the implementation works before writing comprehensive unit tests.
"""

import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from app.database.manager import DatabaseManager
from app.database.models import Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

def test_progressive_enrichment():
    """Test progressive user enrichment flow."""
    print("=" * 60)
    print("Progressive User Enrichment - Quick Verification Test")
    print("=" * 60)
    
    # Initialize database manager
    db_manager = DatabaseManager()
    
    test_phone = "+1234567890"
    
    print(f"\n1. Testing user creation with nullable name...")
    print(f"   Phone: {test_phone}")
    
    # Create user without name
    result = db_manager.create_user_with_phone(test_phone, name=None)
    print(f"   Result: {result}")
    
    if result.get("success"):
        user_id = result["user_id"]
        print(f"   ✓ User created successfully with ID: {user_id}")
    else:
        print(f"   ✗ Failed to create user: {result.get('message')}")
        return False
    
    print(f"\n2. Testing user lookup by mobile number...")
    user_data = db_manager.get_user_by_mobile_number(test_phone)
    print(f"   Result: {user_data}")
    
    if user_data:
        print(f"   ✓ User found: ID={user_data['user_id']}, Name={user_data.get('name')}")
        if user_data.get('name') is None:
            print(f"   ✓ Name is NULL as expected (progressive enrichment)")
    else:
        print(f"   ✗ User not found")
        return False
    
    print(f"\n3. Testing name update (progressive enrichment)...")
    update_result = db_manager.update_user_name(user_id, "John Doe")
    print(f"   Result: {update_result}")
    
    if update_result.get("success"):
        print(f"   ✓ Name updated successfully")
    else:
        print(f"   ✗ Failed to update name: {update_result.get('message')}")
        return False
    
    print(f"\n4. Verifying name update...")
    updated_user = db_manager.get_user_by_mobile_number(test_phone)
    print(f"   Result: {updated_user}")
    
    if updated_user and updated_user.get('name') == "John Doe":
        print(f"   ✓ Name updated correctly: {updated_user.get('name')}")
    else:
        print(f"   ✗ Name not updated correctly")
        return False
    
    print(f"\n5. Testing appointment history retrieval...")
    history = db_manager.get_user_appointment_history(user_id, limit=5)
    print(f"   Result: {history}")
    print(f"   ✓ Appointment history retrieved (empty for new user): {len(history)} appointments")
    
    print(f"\n6. Testing duplicate user creation...")
    duplicate_result = db_manager.create_user_with_phone(test_phone, name="Jane Doe")
    print(f"   Result: {duplicate_result}")
    
    if not duplicate_result.get("success"):
        print(f"   ✓ Duplicate creation prevented: {duplicate_result.get('message')}")
    else:
        print(f"   ✗ Duplicate user was created (should have been prevented)")
        return False
    
    print("\n" + "=" * 60)
    print("✓ ALL TESTS PASSED!")
    print("=" * 60)
    print("\nProgressive User Enrichment Flow Verified:")
    print("  1. User created with phone number only (name=NULL)")
    print("  2. User lookup works correctly")
    print("  3. Name can be updated progressively")
    print("  4. Duplicate prevention works")
    print("  5. Appointment history retrieval works")
    print("\nNext Steps:")
    print("  - Write comprehensive unit tests")
    print("  - Test workflow integration")
    print("  - Test end-to-end with voice stream")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    try:
        success = test_progressive_enrichment()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ TEST FAILED WITH ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
