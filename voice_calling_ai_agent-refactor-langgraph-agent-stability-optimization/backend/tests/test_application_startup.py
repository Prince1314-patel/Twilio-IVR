#!/usr/bin/env python3
"""
Application Startup Integration Test
===================================

This test verifies that the FastAPI application starts correctly after refactoring
and that all endpoints are accessible. It validates Requirements 6.5.

Author: Advanced AI Systems Team
Last Modified: 2025-01-29
"""

import unittest
import asyncio
import sys
import os
import time
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

class TestApplicationStartup(unittest.TestCase):
    """Test complete application startup and endpoint accessibility."""
    
    def setUp(self):
        """Set up test environment."""
        # Mock environment variables to avoid external dependencies
        self.env_patcher = patch.dict(os.environ, {
            'ENVIRONMENT': 'test',
            'TWILIO_ACCOUNT_SID': 'test_account_sid',
            'TWILIO_AUTH_TOKEN': 'test_auth_token',
            'TWILIO_PHONE_NUMBER': '+1234567890',
            'TWILIO_WEBHOOK_URL': 'https://test.example.com',
            'SARVAM_API_KEY': 'test_sarvam_key',
            'OPENAI_API_KEY': 'test_openai_key',
            'ANTHROPIC_API_KEY': 'test_anthropic_key',
            'GROQ_API_KEY': 'test_groq_key',
            'LLM_PROVIDER': 'openai',
            'LLM_MODEL': 'gpt-3.5-turbo',
            'HOST': '0.0.0.0',
            'PORT': '8000'
        })
        self.env_patcher.start()
        
        # Mock external service clients to avoid actual API calls
        self.twilio_patcher = patch('app.apis.voice.twilio_client')
        self.sarvam_patcher = patch('app.ai.services.sarvam_client.SarvamClient')
        
        self.mock_twilio = self.twilio_patcher.start()
        self.mock_sarvam = self.sarvam_patcher.start()
        
        # Configure mock responses
        self.mock_twilio.calls.create.return_value = MagicMock(
            sid='test_call_sid',
            status='queued'
        )
        
    def tearDown(self):
        """Clean up test environment."""
        self.env_patcher.stop()
        self.twilio_patcher.stop()
        self.sarvam_patcher.stop()
    
    def test_application_imports_successfully(self):
        """Test that the application can be imported without errors."""
        try:
            from main import app
            self.assertIsNotNone(app)
            print("✅ Application imported successfully")
        except Exception as e:
            self.fail(f"Failed to import application: {e}")
    
    def test_application_startup(self):
        """Test that the FastAPI application starts without errors."""
        try:
            from main import app
            
            # Create test client (this tests app initialization)
            client = TestClient(app)
            self.assertIsNotNone(client)
            print("✅ FastAPI application started successfully")
            
        except Exception as e:
            self.fail(f"Failed to start FastAPI application: {e}")
    
    def test_root_endpoint_accessible(self):
        """Test that the root endpoint is accessible."""
        try:
            from main import app
            client = TestClient(app)
            
            response = client.get("/")
            self.assertEqual(response.status_code, 200)
            self.assertIn("Healthcare AI Assistant API", response.text)
            print("✅ Root endpoint accessible")
            
        except Exception as e:
            self.fail(f"Root endpoint not accessible: {e}")
    
    def test_health_endpoint_accessible(self):
        """Test that the health check endpoint is accessible."""
        try:
            from main import app
            client = TestClient(app)
            
            response = client.get("/health")
            self.assertEqual(response.status_code, 200)
            
            data = response.json()
            self.assertEqual(data["status"], "healthy")
            self.assertEqual(data["service"], "Healthcare AI Assistant API")
            self.assertEqual(data["version"], "2.0.0")
            self.assertIn("timestamp", data)
            print("✅ Health endpoint accessible")
            
        except Exception as e:
            self.fail(f"Health endpoint not accessible: {e}")
    
    def test_api_documentation_accessible(self):
        """Test that API documentation endpoints are accessible."""
        try:
            from main import app
            client = TestClient(app)
            
            # Test OpenAPI docs
            docs_response = client.get("/docs")
            self.assertEqual(docs_response.status_code, 200)
            print("✅ OpenAPI docs accessible")
            
            # Test ReDoc
            redoc_response = client.get("/redoc")
            self.assertEqual(redoc_response.status_code, 200)
            print("✅ ReDoc documentation accessible")
            
            # Test OpenAPI JSON schema
            openapi_response = client.get("/openapi.json")
            self.assertEqual(openapi_response.status_code, 200)
            
            openapi_data = openapi_response.json()
            self.assertEqual(openapi_data["info"]["title"], "Healthcare AI Assistant API")
            self.assertEqual(openapi_data["info"]["version"], "2.0.0")
            print("✅ OpenAPI schema accessible")
            
        except Exception as e:
            self.fail(f"API documentation not accessible: {e}")
    
    def test_chat_endpoints_accessible(self):
        """Test that chat API endpoints are accessible."""
        try:
            from main import app
            client = TestClient(app)
            
            # Test chat message endpoint (POST)
            chat_data = {
                "content": "Hello, test message",
                "session_id": "test_session"
            }
            
            with patch('app.ai.graph.entrypoint.run_agentic_graph') as mock_agent:
                mock_agent.return_value = "Test response"
                
                response = client.post("/api/chat/message", json=chat_data)
                self.assertEqual(response.status_code, 200)
                
                data = response.json()
                self.assertIn("content", data)
                self.assertIn("session_id", data)
                self.assertIn("timestamp", data)
                print("✅ Chat message endpoint accessible")
            
            # Test new session endpoint
            response = client.post("/api/chat/new-session")
            self.assertEqual(response.status_code, 200)
            
            data = response.json()
            self.assertIn("session_id", data)
            print("✅ New session endpoint accessible")
            
            # Test sessions list endpoint
            response = client.get("/api/chat/sessions")
            self.assertEqual(response.status_code, 200)
            
            data = response.json()
            self.assertIn("active_sessions", data)
            self.assertIn("sessions", data)
            print("✅ Sessions list endpoint accessible")
            
        except Exception as e:
            self.fail(f"Chat endpoints not accessible: {e}")
    
    def test_voice_endpoints_accessible(self):
        """Test that voice API endpoints are accessible."""
        try:
            from main import app
            client = TestClient(app)
            
            # Test call initiation endpoint
            call_data = {
                "phone_number": "+1234567890",
                "message": "Test call"
            }
            
            response = client.post("/api/voice/initiate-call", json=call_data)
            self.assertEqual(response.status_code, 200)
            
            data = response.json()
            self.assertIn("call_sid", data)
            self.assertIn("status", data)
            print("✅ Call initiation endpoint accessible")
            
            # Test incoming call webhook
            response = client.post("/api/voice/incoming-call")
            self.assertEqual(response.status_code, 200)
            self.assertIn("application/xml", response.headers.get("content-type", ""))
            print("✅ Incoming call webhook accessible")
            
            # Test call status endpoint
            response = client.get("/api/voice/call-status/test_call_sid")
            # This might return 404 for non-existent call, which is expected
            self.assertIn(response.status_code, [200, 404])
            print("✅ Call status endpoint accessible")
            
            # Test active calls endpoint
            response = client.get("/api/voice/active-calls")
            self.assertEqual(response.status_code, 200)
            
            data = response.json()
            self.assertIn("active_calls", data)
            print("✅ Active calls endpoint accessible")
            
        except Exception as e:
            self.fail(f"Voice endpoints not accessible: {e}")
    
    def test_voice_stream_endpoints_accessible(self):
        """Test that voice streaming endpoints are accessible."""
        try:
            from main import app
            client = TestClient(app)
            
            # Test active streams endpoint
            response = client.get("/api/voice/active-streams")
            self.assertEqual(response.status_code, 200)
            
            data = response.json()
            self.assertIn("active_streams", data)
            self.assertIn("session_ids", data)
            print("✅ Active streams endpoint accessible")
            
            # Test session metrics endpoint
            response = client.get("/api/voice/session-metrics/test_session")
            self.assertEqual(response.status_code, 200)
            
            data = response.json()
            # Should return error for non-existent session
            self.assertIn("error", data)
            print("✅ Session metrics endpoint accessible")
            
        except Exception as e:
            self.fail(f"Voice stream endpoints not accessible: {e}")
    
    def test_cors_middleware_configured(self):
        """Test that CORS middleware is properly configured."""
        try:
            from main import app
            client = TestClient(app)
            
            # Test preflight request
            response = client.options("/api/chat/message", headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type"
            })
            
            # Should not return 405 Method Not Allowed
            self.assertNotEqual(response.status_code, 405)
            print("✅ CORS middleware configured")
            
        except Exception as e:
            self.fail(f"CORS middleware not properly configured: {e}")
    
    def test_logging_middleware_configured(self):
        """Test that logging middleware is properly configured."""
        try:
            from main import app
            client = TestClient(app)
            
            # Make a request and check that response headers are added
            response = client.get("/health")
            self.assertEqual(response.status_code, 200)
            
            # Check for custom headers added by logging middleware
            self.assertIn("X-Process-Time", response.headers)
            self.assertIn("X-Request-ID", response.headers)
            print("✅ Logging middleware configured")
            
        except Exception as e:
            self.fail(f"Logging middleware not properly configured: {e}")
    
    def test_router_inclusion(self):
        """Test that all routers are properly included."""
        try:
            from main import app
            
            # Check that routes are registered
            routes = [route.path for route in app.routes]
            
            # Check for expected route patterns
            expected_patterns = [
                "/api/chat/message",
                "/api/chat/history/{session_id}",
                "/api/voice/initiate-call",
                "/api/voice/incoming-call",
                "/api/voice/stream"
            ]
            
            for pattern in expected_patterns:
                # Check if any route matches the pattern (accounting for path parameters)
                pattern_found = any(
                    pattern.replace("{session_id}", "").replace("{call_sid}", "") in route
                    for route in routes
                )
                self.assertTrue(pattern_found, f"Route pattern {pattern} not found")
            
            print("✅ All routers properly included")
            
        except Exception as e:
            self.fail(f"Router inclusion failed: {e}")


def run_startup_tests():
    """Run all application startup tests."""
    print("🚀 Starting Application Startup Tests")
    print("=" * 50)
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestApplicationStartup)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    if result.wasSuccessful():
        print("\n🎉 All application startup tests passed!")
        print("✅ FastAPI application starts without errors")
        print("✅ All endpoints are accessible")
        print("✅ Middleware is properly configured")
        print("✅ Routers are properly included")
        return True
    else:
        print(f"\n❌ {len(result.failures)} test(s) failed")
        print(f"❌ {len(result.errors)} test(s) had errors")
        return False


if __name__ == "__main__":
    success = run_startup_tests()
    sys.exit(0 if success else 1)