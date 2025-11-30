import requests
import json

BASE_URL = "http://localhost:8001"

def test_incoming_call():
    print("Testing /incoming-call...")
    response = requests.post(f"{BASE_URL}/api/voice/incoming-call")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    if "<Record" in response.text and "action=\"/api/voice/handle-recording\"" in response.text:
        print("SUCCESS: Incoming call returns TwiML with <Record>.")
    else:
        print("FAILURE: Incoming call TwiML incorrect.")

def test_handle_recording_no_input():
    print("\nTesting /handle-recording (no input)...")
    data = {
        "CallSid": "test_call_sid",
        "RecordingUrl": ""
    }
    response = requests.post(f"{BASE_URL}/api/voice/handle-recording", data=data)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    if "<Record" in response.text:
        print("SUCCESS: Handle recording returns TwiML with <Record> (retry).")
    else:
        print("FAILURE: Handle recording TwiML incorrect.")

if __name__ == "__main__":
    try:
        test_incoming_call()
        test_handle_recording_no_input()
    except Exception as e:
        print(f"Error: {e}")
