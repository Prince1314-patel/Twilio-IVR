"""
Enhanced Make Call Script
========================

This script enhances the original make_call.py functionality to work with
the new FastAPI architecture while preserving the working patterns.

Author: Advanced AI Systems Team
Last Modified: 2025-01-27
"""

from dotenv import load_dotenv
import os
import sys
import requests
from twilio.rest import Client

# Load environment variables
load_dotenv()

def get_twilio_client():
    """Get Twilio client with proper error handling."""
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    
    if not account_sid or not auth_token:
        raise EnvironmentError("Missing TWILIO_ACCOUNT_SID or TWILIO_AUTH_TOKEN in environment.")
    
    return Client(account_sid, auth_token)

def make_call_via_api(phone_number: str, webhook_url: str = None):
    """
    Make a call using the FastAPI backend.
    
    Args:
        phone_number (str): Phone number to call
        webhook_url (str, optional): Custom webhook URL
        
    Returns:
        dict: Call result
    """
    try:
        # Use the FastAPI endpoint
        response = requests.post(
            "http://localhost:8000/api/voice/initiate-call",
            json={
                "phone_number": phone_number,
                "message": "Healthcare AI Assistant calling"
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Call initiated successfully!")
            print(f"📞 Call SID: {result['call_sid']}")
            print(f"📱 Status: {result['status']}")
            print(f"💬 Message: {result['message']}")
            return result
        else:
            print(f"❌ API Error: {response.status_code} - {response.text}")
            return {"error": f"API Error: {response.status_code}"}
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Connection Error: {e}")
        return {"error": f"Connection Error: {e}"}

def make_call_direct(phone_number: str, webhook_url: str):
    """
    Make a call directly using Twilio (legacy method).
    
    Args:
        phone_number (str): Phone number to call
        webhook_url (str): Webhook URL for call handling
        
    Returns:
        dict: Call result
    """
    try:
        client = get_twilio_client()
        
        call = client.calls.create(
            to=phone_number,
            from_=os.getenv("TWILIO_PHONE_NUMBER"),
            url=webhook_url
        )
        
        print(f"✅ Call initiated successfully!")
        print(f"📞 Call SID: {call.sid}")
        print(f"📱 Status: {call.status}")
        return {"call_sid": call.sid, "status": call.status}
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return {"error": str(e)}

def main():
    """Main function to initiate a call."""
    print("🏥 Healthcare AI Assistant - Make Call")
    print("=" * 40)
    
    # Get phone number from command line or prompt
    if len(sys.argv) > 1:
        phone_number = sys.argv[1]
    else:
        phone_number = input("Enter phone number (with country code, e.g., +1234567890): ").strip()
    
    if not phone_number:
        print("❌ No phone number provided")
        return
    
    # Validate phone number format
    if not phone_number.startswith('+'):
        print("❌ Phone number must include country code (e.g., +1234567890)")
        return
    
    print(f"\n📞 Calling: {phone_number}")
    print("🔄 Choose call method:")
    print("1. Use FastAPI backend (recommended)")
    print("2. Use direct Twilio (legacy)")
    
    choice = input("Enter choice (1 or 2): ").strip()
    
    if choice == "1":
        # Use FastAPI backend
        print("\n🚀 Using FastAPI backend...")
        result = make_call_via_api(phone_number)
        
        if "error" in result:
            print(f"\n❌ Failed: {result['error']}")
            print("💡 Make sure the FastAPI server is running on http://localhost:8000")
        else:
            print(f"\n✅ Success! Call initiated via FastAPI backend")
            
    elif choice == "2":
        # Use direct Twilio
        webhook_url = input("Enter webhook URL (e.g., https://your-domain.com/api/voice/incoming-call): ").strip()
        if not webhook_url:
            print("❌ Webhook URL is required for direct Twilio calls")
            return
            
        print("\n🚀 Using direct Twilio...")
        result = make_call_direct(phone_number, webhook_url)
        
        if "error" in result:
            print(f"\n❌ Failed: {result['error']}")
        else:
            print(f"\n✅ Success! Call initiated directly via Twilio")
    else:
        print("❌ Invalid choice")
        return
    
    print("\n💡 Tips:")
    print("• Check your Twilio console for call logs")
    print("• Ensure your webhook URL is publicly accessible")
    print("• Use ngrok for local development: ngrok http 8000")

if __name__ == "__main__":
    main()

