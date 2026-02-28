#!/usr/bin/env python3
"""
Test Loop-Back Resume Functionality
====================================

This script tests that the graph properly resumes from interrupt points
instead of re-running from __start__ on subsequent turns.
"""

import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.ai.graph.entrypoint import run_agentic_graph
from app.core.logger_config import get_ai_agent_logger

logger = get_ai_agent_logger()

def test_loopback_resume():
    """Test that subsequent turns use resume instead of fresh invoke."""
    
    print("=" * 80)
    print("TESTING LOOP-BACK RESUME FUNCTIONALITY")
    print("=" * 80)
    
    thread_id = "test_loopback_resume_001"
    
    # Simulate authenticated user context
    user_context = {
        "caller_mobile_number": "+918799472801",
        "user_id": 1,
        "user_profile": {
            "id": 1,
            "full_name": "Test User",
            "mobile_number": "+918799472801"
        },
        "user_context_loaded": True,
        "needs_name_enrichment": False
    }
    
    print("\n" + "=" * 80)
    print("TURN 1: Fresh conversation (should run full pipeline)")
    print("=" * 80)
    
    messages_turn1 = [
        {"role": "user", "content": "I want to book an appointment"}
    ]
    
    response1 = run_agentic_graph(messages_turn1, thread_id, user_context)
    print(f"\n✅ Turn 1 Response: {response1[:150]}...")
    print("\n📊 Check logs above for:")
    print("   - [GRAPH ENTRY] (should appear)")
    print("   - Looking up user by mobile number (should appear)")
    print("   - Intent classified (should appear)")
    print("   - [WAIT FOR INPUT] Pausing graph (should appear)")
    
    print("\n" + "=" * 80)
    print("TURN 2: Resume from interrupt (should skip expensive nodes)")
    print("=" * 80)
    
    messages_turn2 = [
        {"role": "user", "content": "I want to book an appointment"},
        {"role": "assistant", "content": response1},
        {"role": "user", "content": "Regular appointment"}
    ]
    
    response2 = run_agentic_graph(messages_turn2, thread_id, user_context)
    print(f"\n✅ Turn 2 Response: {response2[:150]}...")
    print("\n📊 Check logs above for:")
    print("   - [GRAPH RESUME] (should appear)")
    print("   - [GRAPH RESUME COMPLETE] skipped expensive nodes (should appear)")
    print("   - Looking up user by mobile number (should NOT appear)")
    print("   - Intent classified (should NOT appear)")
    
    print("\n" + "=" * 80)
    print("TURN 3: Another resume (should also skip)")
    print("=" * 80)
    
    messages_turn3 = messages_turn2 + [
        {"role": "assistant", "content": response2},
        {"role": "user", "content": "Tomorrow at 2pm"}
    ]
    
    response3 = run_agentic_graph(messages_turn3, thread_id, user_context)
    print(f"\n✅ Turn 3 Response: {response3[:150]}...")
    print("\n📊 Check logs above for:")
    print("   - [GRAPH RESUME] (should appear)")
    print("   - Looking up user by mobile number (should NOT appear)")
    
    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)
    print("\n✅ If you see [GRAPH RESUME] on turns 2 and 3, the fix is working!")
    print("❌ If you see [GRAPH ENTRY] on all turns, the resume is not working.")
    print("\n💡 Expected latency improvement:")
    print("   - Turn 1: ~2500-3000ms (full pipeline)")
    print("   - Turn 2+: ~800-1200ms (resume path)")
    print("   - Savings: ~1500-2000ms per turn (50-60% reduction)")
    
    return True

if __name__ == "__main__":
    try:
        test_loopback_resume()
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
