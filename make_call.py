from dotenv import load_dotenv
import os
from twilio.rest import Client

# 1. Load .env file (make sure this is at top)
load_dotenv()

# 2. Get Account SID and Auth Token using correct syntax
account_sid = os.getenv("TWILIO_ACCOUNT_SID")
auth_token = os.getenv("TWILIO_AUTH_TOKEN")

# 3. Validate that both are present
if not account_sid or not auth_token:
    raise EnvironmentError("Missing TWILIO_ACCOUNT_SID or TWILIO_AUTH_TOKEN in environment.")

client = Client(account_sid, auth_token)

call = client.calls.create(
    to="+918799472801",
    from_="+19122145317",
    url="https://6abb30eaa6e1.ngrok-free.app/incoming-call"
)

print(call.sid)
