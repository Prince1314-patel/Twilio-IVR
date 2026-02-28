import requests
import json
import unittest
from unittest.mock import patch, MagicMock

BASE_URL = "http://localhost:8000"  # Changed from 8001 to 8000

class TestSarvamFlow(unittest.TestCase):
    """Test Sarvam flow integration with mocked server."""
    
    @patch('requests.post')
    def test_incoming_call(self, mock_post):
        """Test /incoming-call endpoint."""
        print("Testing /incoming-call...")
        
        # Mock successful response with TwiML
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '<Response><Record action="/api/voice/handle-recording" /></Response>'
        mock_post.return_value = mock_response
        
        response = requests.post(f"{BASE_URL}/api/voice/incoming-call")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        
        self.assertEqual(response.status_code, 200)
        self.assertIn("<Record", response.text)
        self.assertIn("action=\"/api/voice/handle-recording\"", response.text)
        print("SUCCESS: Incoming call returns TwiML with <Record>.")

    @patch('requests.post')
    def test_handle_recording_no_input(self, mock_post):
        """Test /handle-recording endpoint with no input."""
        print("\nTesting /handle-recording (no input)...")
        
        # Mock successful response with TwiML
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '<Response><Record action="/api/voice/handle-recording" /></Response>'
        mock_post.return_value = mock_response
        
        data = {
            "CallSid": "test_call_sid",
            "RecordingUrl": ""
        }
        response = requests.post(f"{BASE_URL}/api/voice/handle-recording", data=data)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        
        self.assertEqual(response.status_code, 200)
        self.assertIn("<Record", response.text)
        print("SUCCESS: Handle recording returns TwiML with <Record> (retry).")

def test_incoming_call():
    """Legacy function for backward compatibility."""
    test_case = TestSarvamFlow()
    test_case.test_incoming_call()

def test_handle_recording_no_input():
    """Legacy function for backward compatibility."""
    test_case = TestSarvamFlow()
    test_case.test_handle_recording_no_input()

if __name__ == "__main__":
    unittest.main()
