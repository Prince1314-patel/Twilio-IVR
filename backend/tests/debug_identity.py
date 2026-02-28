
import sys
import os
sys.path.append(os.getcwd())

from app.database.session import SessionLocal
from app.core.identity import IdentityService

db = SessionLocal()
try:
    print("Testing get_or_create_user with +1234567890")
    user = IdentityService.get_or_create_user(db, "+1234567890")
    if user:
        print(f"Success: Found/Created user {user.id} - {user.full_name}")
    else:
        print("Failed: get_or_create_user returned None")
except Exception as e:
    print(f"Exception: {e}")
finally:
    db.close()
