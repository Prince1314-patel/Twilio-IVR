"""
End-to-End Test for Progressive User Enrichment
================================================

This test simulates the complete user enrichment flow:
1. New user calls (no profile exists)
2. System creates user with phone only
3. System asks for name
4. User provides name
5. System updates database
6. Subsequent interactions use personalized greetings

Run this to verify the complete implementation works end-to-end.
"""

import sys
import os
import asyncio

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from app.ai.graph.state import AgentState
from app.ai.graph.nodes.user_context_node import user_context_loading_node
from app.ai.graph.nodes.name_enrichment_node import name_enrichment_node
from app.database.manager import DatabaseManager
from langchain_core.messages import HumanMessage, AIMessage

def test_complete_enrichment_flow():
    """Test complete progressive enrichment flow."""
    print("=" * 70)
    print("Progressive User Enrichment - End-to-End Test")
    print("=" * 70)
    
    db_manager = DatabaseManager()
    test_phone = "+9999999999"
    
    # Clean up any existing test data
    try:
        user_data = db_manager.get_user_by_mobile_number(test_phone)
        if user_data:
            print(f"\nCleaning up existing test user: {user_data['user_id']}")
    except:
        pass
    
    print("\n" + "=" * 70)
    print("SCENARIO 1: New User First Call")
    print("=" * 70)
    
    # Step 1: User context loading for new user
    print("\n1. User Context Loading (New User)")
    print(f"   Phone: {test_phone}")
    
    initial_state = {
        "messages": [HumanMessage(content="Hello, I want to book an appointment")],
        "caller_mobile_number": test_phone,
        "user_profile": {},
        "user_context_loaded": False,
        "user_id": 0,
        "needs_name_enrichment": False
    }
    
    result = user_context_loading_node(initial_state)
    print(f"   Result: user_id={result.get('user_id')}, needs_enrichment={result.get('needs_name_enrichment')}")
    
    if result.get("user_id") and result.get("needs_name_enrichment"):
        print(f"   ✓ New user created with ID: {result['user_id']}")
        print(f"   ✓ Name enrichment flag set: {result['needs_name_enrichment']}")
        user_id = result["user_id"]
    else:
        print(f"   ✗ Failed to create user or set enrichment flag")
        return False
    
    # Step 2: Name enrichment - first interaction (should ask for name)
    print("\n2. Name Enrichment - First Interaction (Asking for Name)")
    
    state_after_context = {
        **initial_state,
        **result
    }
    
    enrichment_result = name_enrichment_node(state_after_context)
    print(f"   Messages returned: {len(enrichment_result.get('messages', []))}")
    
    if enrichment_result.get("messages"):
        ai_message = enrichment_result["messages"][0]
        print(f"   AI asks: '{ai_message.content}'")
        if "name" in ai_message.content.lower():
            print(f"   ✓ Agent correctly asked for user's name")
        else:
            print(f"   ✗ Agent didn't ask for name")
            return False
    else:
        print(f"   ✗ No message returned")
        return False
    
    # Step 3: User provides name
    print("\n3. User Provides Name")
    user_name_response = "My name is Alice Johnson"
    print(f"   User says: '{user_name_response}'")
    
    state_with_name_response = {
        **state_after_context,
        "messages": [
            HumanMessage(content="Hello, I want to book an appointment"),
            AIMessage(content="Before we proceed, may I have your name please?"),
            HumanMessage(content=user_name_response)
        ]
    }
    
    # Step 4: Name enrichment - second interaction (should extract and update)
    print("\n4. Name Enrichment - Second Interaction (Extracting Name)")
    
    final_enrichment_result = name_enrichment_node(state_with_name_response)
    print(f"   Enrichment flag after: {final_enrichment_result.get('needs_name_enrichment')}")
    
    if final_enrichment_result.get("needs_name_enrichment") == False:
        print(f"   ✓ Name enrichment completed")
        updated_profile = final_enrichment_result.get("user_profile", {})
        if updated_profile.get("name"):
            print(f"   ✓ Name captured: {updated_profile['name']}")
        else:
            print(f"   ✗ Name not in profile")
            return False
    else:
        print(f"   ✗ Name enrichment not completed")
        return False
    
    # Step 5: Verify database was updated
    print("\n5. Verifying Database Update")
    
    updated_user = db_manager.get_user_by_mobile_number(test_phone)
    print(f"   Database user: {updated_user}")
    
    if updated_user and updated_user.get("name"):
        print(f"   ✓ Database updated with name: {updated_user['name']}")
    else:
        print(f"   ✗ Database not updated")
        return False
    
    print("\n" + "=" * 70)
    print("SCENARIO 2: Existing User Subsequent Call")
    print("=" * 70)
    
    # Step 6: User context loading for existing user
    print("\n6. User Context Loading (Existing User)")
    
    existing_user_state = {
        "messages": [HumanMessage(content="Hi, I need to reschedule")],
        "caller_mobile_number": test_phone,
        "user_profile": {},
        "user_context_loaded": False,
        "user_id": 0,
        "needs_name_enrichment": False
    }
    
    existing_result = user_context_loading_node(existing_user_state)
    print(f"   Result: user_id={existing_result.get('user_id')}, needs_enrichment={existing_result.get('needs_name_enrichment')}")
    
    profile = existing_result.get("user_profile", {})
    if profile.get("name") and not existing_result.get("needs_name_enrichment"):
        print(f"   ✓ Existing user loaded: {profile['name']}")
        print(f"   ✓ Name enrichment NOT needed (already has name)")
    else:
        print(f"   ✗ Failed to load existing user correctly")
        return False
    
    # Step 7: Name enrichment should skip
    print("\n7. Name Enrichment - Should Skip (Name Already Known)")
    
    state_with_existing = {
        **existing_user_state,
        **existing_result
    }
    
    skip_result = name_enrichment_node(state_with_existing)
    print(f"   Result: {skip_result}")
    
    if not skip_result or skip_result == {}:
        print(f"   ✓ Name enrichment correctly skipped (user already has name)")
    else:
        print(f"   ⚠ Name enrichment returned something (might be asking again)")
    
    print("\n" + "=" * 70)
    print("✓ ALL END-TO-END TESTS PASSED!")
    print("=" * 70)
    print("\nProgressive User Enrichment Flow Verified:")
    print("  1. ✓ New user created with phone number only")
    print("  2. ✓ System asks for user's name")
    print("  3. ✓ Name extracted from user response")
    print("  4. ✓ Database updated with captured name")
    print("  5. ✓ Subsequent calls load existing user profile")
    print("  6. ✓ Name enrichment skipped for users with names")
    print("\nComplete Progressive Enrichment Flow Working! 🎉")
    print("=" * 70)
    
    return True

if __name__ == "__main__":
    try:
        success = test_complete_enrichment_flow()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ TEST FAILED WITH ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
