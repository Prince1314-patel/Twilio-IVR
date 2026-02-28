#!/usr/bin/env python3
"""
Verification Script: Model Hardcoding Implementation
====================================================

This script verifies that all LLM model calls are properly hardcoded
and not using the old keyword-matching approach.

Run this after implementing model hardcoding to ensure correctness.
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def verify_model_functions():
    """Verify that all _get_model() functions return hardcoded models."""
    
    print("=" * 70)
    print("MODEL HARDCODING VERIFICATION")
    print("=" * 70)
    print()
    
    results = []
    
    # Test 1: Intent Detection Node
    print("1. Testing Intent Detection Node...")
    try:
        from app.ai.graph.nodes.intent_detection_node import _get_model
        model = _get_model()
        model_name = getattr(model, 'model_name', 'unknown')
        expected = "llama-3.1-8b-instant"
        
        if model_name == expected:
            print(f"   ✅ PASS: Uses {model_name}")
            results.append(("Intent Detection", True))
        else:
            print(f"   ❌ FAIL: Expected {expected}, got {model_name}")
            results.append(("Intent Detection", False))
    except Exception as e:
        print(f"   ❌ ERROR: {e}")
        results.append(("Intent Detection", False))
    
    print()
    
    # Test 2: Name Enrichment Node
    print("2. Testing Name Enrichment Node...")
    try:
        from app.ai.graph.nodes.name_enrichment_node import _get_model
        model = _get_model()
        model_name = getattr(model, 'model_name', 'unknown')
        expected = "llama-3.1-8b-instant"
        
        if model_name == expected:
            print(f"   ✅ PASS: Uses {model_name}")
            results.append(("Name Enrichment", True))
        else:
            print(f"   ❌ FAIL: Expected {expected}, got {model_name}")
            results.append(("Name Enrichment", False))
    except Exception as e:
        print(f"   ❌ ERROR: {e}")
        results.append(("Name Enrichment", False))
    
    print()
    
    # Test 3: Tool Executor Node - Slot Extraction
    print("3. Testing Tool Executor Node (Slot Extraction)...")
    try:
        from app.ai.graph.nodes.appointment_pipeline.tool_executor_node import _get_model
        model = _get_model()
        model_name = getattr(model, 'model_name', 'unknown')
        expected = "llama-3.1-8b-instant"
        
        if model_name == expected:
            print(f"   ✅ PASS: Uses {model_name}")
            results.append(("Slot Extraction", True))
        else:
            print(f"   ❌ FAIL: Expected {expected}, got {model_name}")
            results.append(("Slot Extraction", False))
    except Exception as e:
        print(f"   ❌ ERROR: {e}")
        results.append(("Slot Extraction", False))
    
    print()
    
    # Test 4: Tool Executor Node - Main Agent
    print("4. Testing Tool Executor Node (Main Agent)...")
    try:
        from app.ai.graph.nodes.appointment_pipeline.tool_executor_node import _get_agent_model
        model = _get_agent_model()
        model_name = getattr(model, 'model_name', 'unknown')
        expected = "moonshotai/kimi-k2-instruct-0905"
        
        if model_name == expected:
            print(f"   ✅ PASS: Uses {model_name}")
            results.append(("Main Agent", True))
        else:
            print(f"   ❌ FAIL: Expected {expected}, got {model_name}")
            results.append(("Main Agent", False))
    except Exception as e:
        print(f"   ❌ ERROR: {e}")
        results.append(("Main Agent", False))
    
    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")
    
    print()
    print(f"Total: {passed}/{total} tests passed")
    
    if passed == total:
        print()
        print("🎉 All model hardcoding verified successfully!")
        return 0
    else:
        print()
        print("⚠️  Some tests failed. Please review the implementation.")
        return 1


if __name__ == "__main__":
    sys.exit(verify_model_functions())
