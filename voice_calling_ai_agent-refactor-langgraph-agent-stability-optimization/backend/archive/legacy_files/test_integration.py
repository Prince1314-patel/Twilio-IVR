"""
Integration Test Script
======================

This script tests the streamlined workflow:
1. Chat with agent (like run_agent_cli.py)
2. Initiate voice call (like make_call.py)
3. Handle voice call (like answer_phone.py)

Author: Advanced AI Systems Team
Last Modified: 2025-01-27
"""

import requests
import json
import time
from datetime import datetime

def test_chat_functionality():
    """Test chat functionality (like run_agent_cli.py)."""
    print("🧪 Testing Chat Functionality...")
    print("=" * 40)
    
    try:
        # Test chat endpoint
        response = requests.post(
            "http://localhost:8000/api/chat/message",
            json={
                "content": "Hello, I want to book an appointment",
                "session_id": "test_session_123",
                "timestamp": datetime.now().isoformat()
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Chat test successful!")
            print(f"🤖 AI Response: {result['content']}")
            return True
        else:
            print(f"❌ Chat test failed: {response.status_code} - {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Chat test failed: {e}")
        return False

def test_voice_call_functionality():
    """Test voice call functionality (like make_call.py)."""
    print("\n🧪 Testing Voice Call Functionality...")
    print("=" * 40)
    
    try:
        # Test voice call endpoint
        response = requests.post(
            "http://localhost:8000/api/voice/initiate-call",
            json={
                "phone_number": "+1234567890",  # Test number
                "message": "Test call from Healthcare AI Assistant"
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Voice call test successful!")
            print(f"📞 Call SID: {result['call_sid']}")
            print(f"📱 Status: {result['status']}")
            return result['call_sid']
        else:
            print(f"❌ Voice call test failed: {response.status_code} - {response.text}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Voice call test failed: {e}")
        return None

def test_call_status(call_sid):
    """Test call status functionality."""
    if not call_sid:
        return
        
    print(f"\n🧪 Testing Call Status for {call_sid}...")
    print("=" * 40)
    
    try:
        response = requests.get(f"http://localhost:8000/api/voice/call-status/{call_sid}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Call status test successful!")
            print(f"📞 Status: {result['status']}")
            print(f"📱 From: {result.get('from', 'N/A')}")
            print(f"📱 To: {result.get('to', 'N/A')}")
        else:
            print(f"❌ Call status test failed: {response.status_code} - {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Call status test failed: {e}")

def test_health_check():
    """Test if the FastAPI server is running."""
    print("🧪 Testing Server Health...")
    print("=" * 40)
    
    try:
        response = requests.get("http://localhost:8000/health")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Server is healthy!")
            print(f"🏥 Service: {result['service']}")
            print(f"📊 Status: {result['status']}")
            print(f"🔢 Version: {result['version']}")
            return True
        else:
            print(f"❌ Server health check failed: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Server health check failed: {e}")
        return False

def main():
    """Run all integration tests."""
    print("🏥 Healthcare AI Assistant - Integration Test")
    print("=" * 50)
    
    # Test 1: Health check
    if not test_health_check():
        print("\n❌ Server is not running. Please start the FastAPI server first:")
        print("   python start_app.py")
        return
    
    # Test 2: Chat functionality
    chat_success = test_chat_functionality()
    
    # Test 3: Voice call functionality
    call_sid = test_voice_call_functionality()
    
    # Test 4: Call status (if call was successful)
    if call_sid:
        test_call_status(call_sid)
    
    # Summary
    print("\n📊 Test Summary")
    print("=" * 30)
    print(f"✅ Server Health: {'PASS' if True else 'FAIL'}")
    print(f"✅ Chat Functionality: {'PASS' if chat_success else 'FAIL'}")
    print(f"✅ Voice Call: {'PASS' if call_sid else 'FAIL'}")
    
    if chat_success and call_sid:
        print("\n🎉 All tests passed! The integration is working correctly.")
        print("\n💡 Next steps:")
        print("   1. Start the Streamlit app: streamlit run streamlit_app.py")
        print("   2. Open http://localhost:8501 in your browser")
        print("   3. Chat with the AI assistant")
        print("   4. Click 'Get Voice Call' to test voice functionality")
    else:
        print("\n❌ Some tests failed. Please check the error messages above.")

if __name__ == "__main__":
    main()
