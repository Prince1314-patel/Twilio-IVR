import os
import sys
from dotenv import load_dotenv
from livekit import api

# Load env vars from backend/.env
# We assume this script is run from the project root or we fix the path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
env_path = os.path.join(project_root, "backend", ".env")
load_dotenv(env_path)

LIVEKIT_URL = os.getenv("LIVEKIT_URL")
API_KEY = os.getenv("LIVEKIT_API_KEY")
API_SECRET = os.getenv("LIVEKIT_API_SECRET")

if not API_KEY or not API_SECRET:
    print("Error: LIVEKIT_API_KEY and LIVEKIT_API_SECRET must be set in backend/.env")
    sys.exit(1)

# Create a token for the user/browser to connect to the "playground" room
grant = api.VideoGrants(
    room_join=True,
    room="playground",
    can_publish=True,
    can_subscribe=True,
    can_publish_data=True,
)

token = api.AccessToken(API_KEY, API_SECRET)
token.with_grants(grant)
token.identity = "human_user"
token.name = "Human User"
jwt_token = token.to_jwt()

print("\n=== LiveKit Dev Token ===")
print(f"URL:   {LIVEKIT_URL}")
print(f"Room:  playground")
print(f"Token: {jwt_token}")
print("=========================\n")
print("USAGE:")
print("1. Go to https://agents-playground.livekit.io/")
print("2. Click 'Settings' (gear icon) or 'Connect'")
print("3. Enter the URL and Token above")
print("4. Click 'Connect'\n")
