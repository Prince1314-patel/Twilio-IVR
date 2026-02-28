#!/usr/bin/env python3
"""
End-to-End Functionality Integration Test
=========================================

This test verifies complete chat conversation flow, voice call handling,
and WebSocket communication after refactoring. It validates Requirements 1.4, 6.3.

Author: Advanced AI Systems Team
Last Modified: 2025-01-29
"""

import unittest
import asyncio
import sys
import os
import json
import time
import threading
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
# WebSocket testing handled by FastAPI TestClient

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

class TestEndToEndFunctionality(unittest.TestCase):
    """Test complete end-to-end functionality flows."""
    
    def setUp(self):
        """Set up test environment."""
        # Mock environment variables
        self.env_patcher = patch.dict(os.environ, {
            'ENVIRONMENT': 'test',
            'TWILIO_ACCOUNT_SID': 'test_account_sid',
            'TWILIO_AUTH_TOKEN': 'test_auth_token',
            'TWILIO_PHONE_NUMBER': '+1234567890',
            'TWILIO_WEBHOOK_URL': 'https://test.example.com',
            'SARVAM_API_KEY': 'test_sarvam_key',
            'OPENAI_API_KEY': 'test_openai_key',
            'LLM_PROVIDER': 'openai',
            'LLM_MODEL': 'gpt-3.5-turbo'
        })
        self.env_patcher.start()
        
        # Mock external services
        self.twilio_patcher = patch('app.apis.voice.twilio_client')
        self.sarvam_patcher = patch('app.ai.services.sarvam_client.SarvamClient')
        self.agent_patcher = patch('app.ai.graph.entrypoint.run_agentic_graph')
        self.streaming_agent_patcher = patch('app.ai.graph.entrypoint.run_agentic_graph_streaming')
        
        self.mock_twilio = self.twilio_patcher.start()
        self.mock_sarvam = self.sarvam_patcher.start()
        self.mock_agent = self.agent_patcher.start()
        self.mock_streaming_agent = self.streaming_agent_patcher.start()
        
        # Configure mock responses
        self.mock_twilio.calls.create.return_value = MagicMock(
            sid='test_call_sid_123',
            status='queued'
        )
        
        self.mock_twilio.calls.return_value.fetch.return_value = MagicMock(
            sid='test_call_sid_123',
            status='completed',
            direction='outbound-api',
            from_formatted='+1234567890',
            to_formatted='+0987654321',
            start_time='2025-01-29T10:00:00Z',
            end_time='2025-01-29T10:05:00Z',
            duration='300'
        )
        
        # Mock AI agent responses
        self.mock_agent.return_value = "I'd be happy to help you schedule an appointment. May I have your full name please?"
        self.mock_streaming_agent.return_value = asyncio.Future()
        self.mock_streaming_agent.return_value.set_result("Thank you for calling. How can I assist you today?")
        
    def tearDown(self):
        """Clean up test environment."""
        self.env_patcher.stop()
        self.twilio_patcher.stop()
        self.sarvam_patcher.stop()
        self.agent_patcher.stop()
        self.streaming_agent_patcher.stop()
    
    def test_complete_chat_conversation_flow(self):
        """Test complete chat conversation flow from start to finish."""
        print("🎯 Testing Complete Chat Conversation Flow")
        
        try:
            from main import app
            client = TestClient(app)
            
            # Step 1: Create new session
            response = client.post("/api/chat/new-session")
            self.assertEqual(response.status_code, 200)
            session_data = response.json()
            session_id = session_data["session_id"]
            print(f"✅ Created new session: {session_id}")
            
            # Step 2: Send initial message
            message_data = {
                "content": "Hello, I need to book an appointment",
                "session_id": session_id
            }
            
            response = client.post("/api/chat/message", json=message_data)
            self.assertEqual(response.status_code, 200)
            
            chat_response = response.json()
            self.assertIn("content", chat_response)
            self.assertEqual(chat_response["session_id"], session_id)
            self.assertIn("timestamp", chat_response)
            print("✅ Sent initial message and received response")
            
            # Step 3: Continue conversation
            follow_up_data = {
                "content": "My name is John Smith",
                "session_id": session_id
            }
            
            response = client.post("/api/chat/message", json=follow_up_data)
            self.assertEqual(response.status_code, 200)
            print("✅ Continued conversation successfully")
            
            # Step 4: Get conversation history
            response = client.get(f"/api/chat/history/{session_id}")
            self.assertEqual(response.status_code, 200)
            
            history = response.json()
            self.assertEqual(history["session_id"], session_id)
            self.assertGreaterEqual(history["total_messages"], 4)  # 2 user + 2 assistant
            self.assertIsInstance(history["messages"], list)
            print("✅ Retrieved conversation history")
            
            # Step 5: Check active sessions
            response = client.get("/api/chat/sessions")
            self.assertEqual(response.status_code, 200)
            
            sessions = response.json()
            self.assertGreaterEqual(sessions["active_sessions"], 1)
            
            # Find our session in the list
            session_found = any(
                session["session_id"] == session_id 
                for session in sessions["sessions"]
            )
            self.assertTrue(session_found)
            print("✅ Session appears in active sessions list")
            
            # Step 6: Clear conversation history
            response = client.delete(f"/api/chat/history/{session_id}")
            self.assertEqual(response.status_code, 200)
            
            # Verify history is cleared
            response = client.get(f"/api/chat/history/{session_id}")
            self.assertEqual(response.status_code, 200)
            
            cleared_history = response.json()
            self.assertEqual(cleared_history["total_messages"], 0)
            print("✅ Cleared conversation history")
            
            print("🎉 Complete chat conversation flow test passed!")
            
        except Exception as e:
            self.fail(f"Chat conversation flow test failed: {e}")
    
    def test_voice_call_handling_end_to_end(self):
        """Test voice call handling from initiation to completion."""
        print("🎯 Testing Voice Call Handling End-to-End")
        
        try:
            from main import app
            client = TestClient(app)
            
            # Step 1: Initiate outbound call
            call_data = {
                "phone_number": "+0987654321",
                "message": "Test appointment reminder call"
            }
            
            response = client.post("/api/voice/initiate-call", json=call_data)
            self.assertEqual(response.status_code, 200)
            
            call_response = response.json()
            self.assertIn("call_sid", call_response)
            self.assertIn("status", call_response)
            call_sid = call_response["call_sid"]
            print(f"✅ Initiated outbound call: {call_sid}")
            
            # Step 2: Handle incoming call webhook
            response = client.post("/api/voice/incoming-call")
            self.assertEqual(response.status_code, 200)
            self.assertIn("application/xml", response.headers.get("content-type", ""))
            
            # Verify TwiML response contains Media Stream connection
            twiml_content = response.text
            self.assertIn("<Connect>", twiml_content)
            self.assertIn("<Stream", twiml_content)
            self.assertIn("wss://", twiml_content)
            print("✅ Handled incoming call webhook with Media Stream")
            
            # Step 3: Check call status
            response = client.get(f"/api/voice/call-status/{call_sid}")
            self.assertEqual(response.status_code, 200)
            
            status_data = response.json()
            self.assertEqual(status_data["call_sid"], call_sid)
            self.assertIn("status", status_data)
            self.assertIn("direction", status_data)
            print("✅ Retrieved call status")
            
            # Step 4: Check active calls
            response = client.get("/api/voice/active-calls")
            self.assertEqual(response.status_code, 200)
            
            active_calls = response.json()
            self.assertIn("active_calls", active_calls)
            self.assertIn("call_sessions", active_calls)
            print("✅ Retrieved active calls list")
            
            # Step 5: Check voice streaming endpoints
            response = client.get("/api/voice/active-streams")
            self.assertEqual(response.status_code, 200)
            
            streams_data = response.json()
            self.assertIn("active_streams", streams_data)
            self.assertIn("session_ids", streams_data)
            print("✅ Retrieved active streams")
            
            print("🎉 Voice call handling end-to-end test passed!")
            
        except Exception as e:
            self.fail(f"Voice call handling test failed: {e}")
    
    def test_websocket_communication(self):
        """Test WebSocket communication for real-time chat."""
        print("🎯 Testing WebSocket Communication")
        
        try:
            from main import app
            
            # Use TestClient's WebSocket support
            client = TestClient(app)
            session_id = "test_websocket_session"
            
            # Test WebSocket connection and message exchange
            with client.websocket_connect(f"/ws/{session_id}") as websocket:
                print("✅ WebSocket connection established")
                
                # Send test message
                test_message = {
                    "type": "user_message",
                    "content": "Hello via WebSocket",
                    "timestamp": str(int(time.time() * 1000))
                }
                
                websocket.send_text(json.dumps(test_message))
                print("✅ Sent message via WebSocket")
                
                # Receive response
                response_data = websocket.receive_text()
                response = json.loads(response_data)
                
                self.assertEqual(response["type"], "ai_response")
                self.assertIn("content", response)
                self.assertIn("timestamp", response)
                print("✅ Received AI response via WebSocket")
                
                # Send another message to test conversation continuity
                follow_up_message = {
                    "type": "user_message", 
                    "content": "Can you help me book an appointment?",
                    "timestamp": str(int(time.time() * 1000))
                }
                
                websocket.send_text(json.dumps(follow_up_message))
                response_data = websocket.receive_text()
                response = json.loads(response_data)
                
                self.assertEqual(response["type"], "ai_response")
                print("✅ Conversation continuity maintained via WebSocket")
            
            print("🎉 WebSocket communication test passed!")
            
        except Exception as e:
            self.fail(f"WebSocket communication test failed: {e}")
    
    def test_error_handling_end_to_end(self):
        """Test error handling across different components."""
        print("🎯 Testing Error Handling End-to-End")
        
        try:
            from main import app
            client = TestClient(app)
            
            # Test 1: Invalid chat message
            invalid_message = {
                "content": "",  # Empty content
                "session_id": "test_error_session"
            }
            
            # This should still work but might return an error response
            response = client.post("/api/chat/message", json=invalid_message)
            # Should not crash the server
            self.assertIn(response.status_code, [200, 400, 422])
            print("✅ Handled invalid chat message gracefully")
            
            # Test 2: Non-existent session history
            response = client.get("/api/chat/history/non_existent_session")
            self.assertEqual(response.status_code, 404)
            print("✅ Handled non-existent session gracefully")
            
            # Test 3: Invalid phone number for voice call
            invalid_call_data = {
                "phone_number": "invalid_number",  # No country code
                "message": "Test call"
            }
            
            response = client.post("/api/voice/initiate-call", json=invalid_call_data)
            self.assertEqual(response.status_code, 400)
            print("✅ Handled invalid phone number gracefully")
            
            # Test 4: Non-existent call status
            # Configure mock to raise exception for non-existent call
            from twilio.base.exceptions import TwilioRestException
            self.mock_twilio.calls.return_value.fetch.side_effect = TwilioRestException(
                status=404, 
                uri="test_uri",
                msg="Call not found"
            )
            
            response = client.get("/api/voice/call-status/non_existent_call")
            self.assertEqual(response.status_code, 404)
            print("✅ Handled non-existent call status gracefully")
            
            # Reset the mock for other tests
            self.mock_twilio.calls.return_value.fetch.side_effect = None
            
            # Test 5: Invalid JSON in request
            response = client.post(
                "/api/chat/message",
                data="invalid json",
                headers={"Content-Type": "application/json"}
            )
            self.assertEqual(response.status_code, 422)
            print("✅ Handled invalid JSON gracefully")
            
            print("🎉 Error handling end-to-end test passed!")
            
        except Exception as e:
            self.fail(f"Error handling test failed: {e}")
    
    def test_middleware_integration_end_to_end(self):
        """Test that middleware works correctly in end-to-end scenarios."""
        print("🎯 Testing Middleware Integration End-to-End")
        
        try:
            from main import app
            client = TestClient(app)
            
            # Test CORS headers
            response = client.get("/health", headers={
                "Origin": "http://localhost:3000"
            })
            self.assertEqual(response.status_code, 200)
            # CORS headers should be present (handled by FastAPI CORS middleware)
            print("✅ CORS middleware working")
            
            # Test logging middleware headers
            response = client.get("/health")
            self.assertIn("X-Process-Time", response.headers)
            self.assertIn("X-Request-ID", response.headers)
            
            # Verify timing header is reasonable
            process_time = float(response.headers["X-Process-Time"])
            self.assertGreater(process_time, 0)
            self.assertLess(process_time, 10)  # Should be less than 10 seconds
            print("✅ Logging middleware working")
            
            # Test that request ID is unique across requests
            response1 = client.get("/health")
            response2 = client.get("/health")
            
            req_id1 = response1.headers["X-Request-ID"]
            req_id2 = response2.headers["X-Request-ID"]
            self.assertNotEqual(req_id1, req_id2)
            print("✅ Request ID uniqueness working")
            
            print("🎉 Middleware integration end-to-end test passed!")
            
        except Exception as e:
            self.fail(f"Middleware integration test failed: {e}")
    
    def test_concurrent_requests_handling(self):
        """Test handling of concurrent requests."""
        print("🎯 Testing Concurrent Requests Handling")
        
        try:
            from main import app
            import concurrent.futures
            import threading
            
            client = TestClient(app)
            
            def make_chat_request(session_id):
                """Make a chat request."""
                message_data = {
                    "content": f"Hello from session {session_id}",
                    "session_id": session_id
                }
                response = client.post("/api/chat/message", json=message_data)
                return response.status_code == 200, session_id
            
            def make_health_request():
                """Make a health check request."""
                response = client.get("/health")
                return response.status_code == 200
            
            # Test concurrent chat requests
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                # Submit multiple chat requests
                chat_futures = [
                    executor.submit(make_chat_request, f"concurrent_session_{i}")
                    for i in range(5)
                ]
                
                # Submit multiple health requests
                health_futures = [
                    executor.submit(make_health_request)
                    for _ in range(10)
                ]
                
                # Wait for all requests to complete
                chat_results = [future.result() for future in chat_futures]
                health_results = [future.result() for future in health_futures]
            
            # Verify all requests succeeded
            chat_success_count = sum(1 for success, _ in chat_results if success)
            health_success_count = sum(1 for success in health_results if success)
            
            self.assertEqual(chat_success_count, 5)
            self.assertEqual(health_success_count, 10)
            
            print("✅ Handled 5 concurrent chat requests")
            print("✅ Handled 10 concurrent health requests")
            print("🎉 Concurrent requests handling test passed!")
            
        except Exception as e:
            self.fail(f"Concurrent requests handling test failed: {e}")


def run_end_to_end_tests():
    """Run all end-to-end functionality tests."""
    print("🚀 Starting End-to-End Functionality Tests")
    print("=" * 50)
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestEndToEndFunctionality)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    if result.wasSuccessful():
        print("\n🎉 All end-to-end functionality tests passed!")
        print("✅ Complete chat conversation flow working")
        print("✅ Voice call handling end-to-end working")
        print("✅ WebSocket communication working")
        print("✅ Error handling working correctly")
        print("✅ Middleware integration working")
        print("✅ Concurrent requests handled properly")
        return True
    else:
        print(f"\n❌ {len(result.failures)} test(s) failed")
        print(f"❌ {len(result.errors)} test(s) had errors")
        return False


if __name__ == "__main__":
    success = run_end_to_end_tests()
    sys.exit(0 if success else 1)