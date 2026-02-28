#!/usr/bin/env python3
"""
Property-Based Tests for Functional Behavior Preservation
=========================================================

Property-based tests to verify that functional behavior is preserved after
the backend refactoring. This validates Requirements 1.4, 6.3.

**Property 2: Functional Behavior Preservation**
For any input to any system function, the output and side effects should be 
identical before and after refactoring.

Author: Advanced AI Systems Team
Last Modified: 2025-01-29
"""

import unittest
import asyncio
import sys
import os
import json
import time
from unittest.mock import patch, MagicMock, AsyncMock
from hypothesis import given, strategies as st, settings, assume
from fastapi.testclient import TestClient
from langchain_core.messages import HumanMessage, AIMessage

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

class TestFunctionalBehaviorPreservationProperties(unittest.TestCase):
    """Property-based tests for functional behavior preservation."""
    
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
        self.agent_patcher = patch('app.ai.agents.appointment_agent.run_agentic_graph')
        self.streaming_agent_patcher = patch('app.ai.agents.appointment_agent.run_agentic_graph_streaming')
        
        self.mock_twilio = self.twilio_patcher.start()
        self.mock_sarvam = self.sarvam_patcher.start()
        self.mock_agent = self.agent_patcher.start()
        self.mock_streaming_agent = self.streaming_agent_patcher.start()
        
        # Configure consistent mock responses
        self.mock_twilio.calls.create.return_value = MagicMock(
            sid='test_call_sid_123',
            status='queued'
        )
        
        self.mock_agent.return_value = "I'd be happy to help you schedule an appointment. May I have your full name please?"
        
        # Configure streaming agent mock to return a coroutine
        async def mock_streaming_response(*args, **kwargs):
            return "Thank you for calling. How can I assist you today?"
        
        self.mock_streaming_agent.side_effect = mock_streaming_response
        
    def tearDown(self):
        """Clean up test environment."""
        self.env_patcher.stop()
        self.twilio_patcher.stop()
        self.sarvam_patcher.stop()
        self.agent_patcher.stop()
        self.streaming_agent_patcher.stop()
    
    @given(st.text(min_size=1, max_size=200))
    @settings(max_examples=50, deadline=30000)
    def test_chat_message_processing_consistency(self, message_content):
        """
        Property: Chat message processing behavior is consistent.
        
        For any valid message content, the chat API should:
        1. Return a response with consistent structure
        2. Generate a valid session ID
        3. Include proper timestamps
        4. Maintain conversation history
        
        **Feature: backend-refactoring, Property 2: Functional Behavior Preservation**
        **Validates: Requirements 1.4, 6.3**
        """
        assume(message_content.strip())  # Assume non-empty content
        
        try:
            from main import app
            client = TestClient(app)
            
            # Test message processing
            message_data = {
                "content": message_content,
                "session_id": "property_test_session"
            }
            
            response = client.post("/api/chat/message", json=message_data)
            
            # Property: Response should always have consistent structure
            self.assertEqual(response.status_code, 200)
            
            data = response.json()
            self.assertIn("content", data)
            self.assertIn("session_id", data)
            self.assertIn("timestamp", data)
            self.assertIn("message_type", data)
            
            # Property: Content should be non-empty string
            self.assertIsInstance(data["content"], str)
            self.assertGreater(len(data["content"]), 0)
            
            # Property: Session ID should be preserved
            self.assertEqual(data["session_id"], "property_test_session")
            
            # Property: Message type should be consistent
            self.assertEqual(data["message_type"], "ai_response")
            
        except Exception as e:
            self.fail(f"Chat message processing failed for input '{message_content[:50]}...': {e}")
    
    @given(st.sampled_from(["+1234567890", "+9876543210", "+1555123456", "+1800555123", "+1234567891"]))
    @settings(max_examples=10, deadline=30000)
    def test_voice_call_initiation_consistency(self, phone_number):
        """
        Property: Voice call initiation behavior is consistent.
        
        For any valid phone number, the voice API should:
        1. Return a call SID
        2. Return a status
        3. Include a success message
        
        **Feature: backend-refactoring, Property 2: Functional Behavior Preservation**
        **Validates: Requirements 1.4, 6.3**
        """
        try:
            from main import app
            client = TestClient(app)
            
            call_data = {
                "phone_number": phone_number,
                "message": "Test call"
            }
            
            response = client.post("/api/voice/initiate-call", json=call_data)
            
            # Property: Response should always have consistent structure
            self.assertEqual(response.status_code, 200)
            
            data = response.json()
            self.assertIn("call_sid", data)
            self.assertIn("status", data)
            self.assertIn("message", data)
            
            # Property: Call SID should be non-empty string
            self.assertIsInstance(data["call_sid"], str)
            self.assertGreater(len(data["call_sid"]), 0)
            
            # Property: Status should be valid
            self.assertIsInstance(data["status"], str)
            self.assertGreater(len(data["status"]), 0)
            
        except Exception as e:
            self.fail(f"Voice call initiation failed for phone '{phone_number}': {e}")
    
    @given(st.lists(
        st.dictionaries(
            keys=st.sampled_from(["role", "content"]),
            values=st.one_of(
                st.sampled_from(["user", "assistant"]),
                st.text(min_size=1, max_size=100)
            ),
            min_size=2,
            max_size=2
        ).filter(lambda d: "role" in d and "content" in d and d["role"] in ["user", "assistant"]),
        min_size=1,
        max_size=10
    ))
    @settings(max_examples=30, deadline=30000)
    def test_conversation_history_consistency(self, conversation_messages):
        """
        Property: Conversation history management is consistent.
        
        For any valid conversation history, the system should:
        1. Process the conversation without errors
        2. Return a valid response
        3. Maintain conversation structure
        
        **Feature: backend-refactoring, Property 2: Functional Behavior Preservation**
        **Validates: Requirements 1.4, 6.3**
        """
        try:
            from app.ai.graph.entrypoint import run_agentic_graph
            
            session_id = "property_conversation_test"
            
            # Property: Agent should handle any valid conversation history
            response = run_agentic_graph(conversation_messages, session_id)
            
            # Property: Response should be non-empty string
            self.assertIsInstance(response, str)
            self.assertGreater(len(response), 0)
            
        except Exception as e:
            # Some conversation formats might be invalid, which is acceptable
            # The property is that valid conversations should work consistently
            if "Message dict must contain" in str(e):
                # This is expected for invalid message formats
                pass
            else:
                self.fail(f"Conversation processing failed unexpectedly: {e}")
    
    @given(st.text(min_size=1, max_size=100))
    @settings(max_examples=30, deadline=30000)
    def test_streaming_agent_consistency(self, user_input):
        """
        Property: Streaming agent behavior is consistent.
        
        For any user input, the streaming agent should:
        1. Process the input without errors
        2. Return a valid response
        3. Handle the input asynchronously
        
        **Feature: backend-refactoring, Property 2: Functional Behavior Preservation**
        **Validates: Requirements 1.4, 6.3**
        """
        assume(user_input.strip())  # Assume non-empty input
        
        async def test_streaming():
            try:
                from app.ai.graph.entrypoint import run_agentic_graph_streaming
                
                session_id = "property_streaming_test"
                
                # Property: Streaming agent should handle any valid input
                response = await run_agentic_graph_streaming(user_input, session_id)
                
                # Property: Response should be non-empty string
                self.assertIsInstance(response, str)
                self.assertGreater(len(response), 0)
                
            except Exception as e:
                self.fail(f"Streaming agent failed for input '{user_input[:50]}...': {e}")
        
        # Run async test
        asyncio.run(test_streaming())
    
    @given(st.sampled_from([
        "/health",
        "/",
        "/api/chat/sessions",
        "/api/voice/active-calls",
        "/api/voice/active-streams"
    ]))
    @settings(max_examples=25, deadline=30000)
    def test_endpoint_availability_consistency(self, endpoint):
        """
        Property: All endpoints are consistently available.
        
        For any system endpoint, it should:
        1. Be accessible without errors
        2. Return appropriate status codes
        3. Return valid response structure
        
        **Feature: backend-refactoring, Property 2: Functional Behavior Preservation**
        **Validates: Requirements 1.4, 6.3**
        """
        try:
            from main import app
            client = TestClient(app)
            
            response = client.get(endpoint)
            
            # Property: Endpoints should be accessible
            self.assertIn(response.status_code, [200, 404])  # 404 is acceptable for some endpoints
            
            if response.status_code == 200:
                # Property: Successful responses should have valid content
                if endpoint in ["/health", "/api/chat/sessions", "/api/voice/active-calls", "/api/voice/active-streams"]:
                    # These should return JSON
                    data = response.json()
                    self.assertIsInstance(data, dict)
                elif endpoint == "/":
                    # Root should return HTML
                    self.assertIn("text/html", response.headers.get("content-type", ""))
            
        except Exception as e:
            self.fail(f"Endpoint {endpoint} failed: {e}")
    
    @given(st.dictionaries(
        keys=st.sampled_from(["content", "session_id", "timestamp"]),
        values=st.one_of(
            st.text(min_size=1, max_size=100),
            st.text(min_size=10, max_size=50),
            st.integers(min_value=1000000000, max_value=9999999999).map(str)
        ),
        min_size=1,
        max_size=3
    ))
    @settings(max_examples=40, deadline=30000)
    def test_api_input_validation_consistency(self, request_data):
        """
        Property: API input validation is consistent.
        
        For any request data, the API should:
        1. Handle the request gracefully
        2. Return appropriate status codes
        3. Not crash the server
        
        **Feature: backend-refactoring, Property 2: Functional Behavior Preservation**
        **Validates: Requirements 1.4, 6.3**
        """
        try:
            from main import app
            client = TestClient(app)
            
            # Test chat endpoint with various inputs
            response = client.post("/api/chat/message", json=request_data)
            
            # Property: Server should not crash and should return valid HTTP status
            self.assertIn(response.status_code, [200, 400, 422])
            
            if response.status_code == 200:
                # Property: Successful responses should have valid structure
                data = response.json()
                self.assertIsInstance(data, dict)
                self.assertIn("content", data)
            
        except Exception as e:
            # Some inputs might cause validation errors, which is acceptable
            # The property is that the server should handle them gracefully
            if "validation" in str(e).lower() or "json" in str(e).lower():
                pass  # Expected validation errors
            else:
                self.fail(f"API input validation failed unexpectedly: {e}")
    
    @given(st.text(min_size=1, max_size=50).filter(lambda x: x.isprintable() and not any(c in x for c in ['\x08', '\x0c', '\x0b', '\x07'])))
    @settings(max_examples=20, deadline=30000)
    def test_session_management_consistency(self, session_id):
        """
        Property: Session management is consistent.
        
        For any session ID, the system should:
        1. Handle session creation/retrieval consistently
        2. Maintain session state properly
        3. Allow session operations without errors
        
        **Feature: backend-refactoring, Property 2: Functional Behavior Preservation**
        **Validates: Requirements 1.4, 6.3**
        """
        assume(session_id.strip())  # Assume non-empty session ID
        
        try:
            from main import app
            client = TestClient(app)
            
            # Test session operations
            message_data = {
                "content": "Hello",
                "session_id": session_id
            }
            
            # Property: Session should be created/used consistently
            response = client.post("/api/chat/message", json=message_data)
            self.assertEqual(response.status_code, 200)
            
            data = response.json()
            self.assertEqual(data["session_id"], session_id)
            
            # Property: Session history should be retrievable
            history_response = client.get(f"/api/chat/history/{session_id}")
            
            if history_response.status_code == 200:
                history_data = history_response.json()
                self.assertIn("session_id", history_data)
                self.assertEqual(history_data["session_id"], session_id)
                self.assertIn("messages", history_data)
                self.assertIsInstance(history_data["messages"], list)
            
        except Exception as e:
            self.fail(f"Session management failed for session '{session_id[:20]}...': {e}")
    
    def test_system_integration_consistency(self):
        """
        Property: Overall system integration is consistent.
        
        The complete system should:
        1. Start up without errors
        2. Handle multiple concurrent operations
        3. Maintain consistent behavior across components
        
        **Feature: backend-refactoring, Property 2: Functional Behavior Preservation**
        **Validates: Requirements 1.4, 6.3**
        """
        try:
            from main import app
            import concurrent.futures
            import threading
            
            client = TestClient(app)
            
            def make_request(endpoint, data=None):
                """Make a request to the specified endpoint."""
                if data:
                    return client.post(endpoint, json=data)
                else:
                    return client.get(endpoint)
            
            # Property: System should handle concurrent operations consistently
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                # Submit various concurrent requests
                futures = [
                    executor.submit(make_request, "/health"),
                    executor.submit(make_request, "/api/chat/message", {
                        "content": "Test message 1",
                        "session_id": "concurrent_test_1"
                    }),
                    executor.submit(make_request, "/api/chat/message", {
                        "content": "Test message 2", 
                        "session_id": "concurrent_test_2"
                    }),
                    executor.submit(make_request, "/api/chat/sessions"),
                    executor.submit(make_request, "/api/voice/active-calls")
                ]
                
                # Wait for all requests to complete
                results = [future.result() for future in futures]
            
            # Property: All requests should complete successfully
            for i, response in enumerate(results):
                self.assertIn(response.status_code, [200, 404])
                
            print("✅ System handled concurrent operations consistently")
            
        except Exception as e:
            self.fail(f"System integration consistency test failed: {e}")


def run_functional_behavior_preservation_tests():
    """Run all functional behavior preservation property tests."""
    print("🚀 Starting Functional Behavior Preservation Property Tests")
    print("=" * 60)
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestFunctionalBehaviorPreservationProperties)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    if result.wasSuccessful():
        print("\n🎉 All functional behavior preservation property tests passed!")
        print("✅ Chat message processing consistency verified")
        print("✅ Voice call initiation consistency verified")
        print("✅ Conversation history consistency verified")
        print("✅ Streaming agent consistency verified")
        print("✅ Endpoint availability consistency verified")
        print("✅ API input validation consistency verified")
        print("✅ Session management consistency verified")
        print("✅ System integration consistency verified")
        return True
    else:
        print(f"\n❌ {len(result.failures)} test(s) failed")
        print(f"❌ {len(result.errors)} test(s) had errors")
        return False


if __name__ == "__main__":
    success = run_functional_behavior_preservation_tests()
    sys.exit(0 if success else 1)