
import sys
import os
import datetime
from zoneinfo import ZoneInfo
import logging

# Add backend directory to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.database.manager import DatabaseManager
from app.database.tools.appointment_tools import (
    update_appointment_in_db, 
    check_appointment_availability,
    get_upcoming_appointments
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_reschedule_flow():
    db_manager = DatabaseManager()
    
    # 1. Setup: Create a user and two appointments
    logger.info("--- Setup ---")
    mobile = "9998887776"
    name = "Test User Reschedule"
    
    # Ensure user expects
    user = db_manager.get_user_by_mobile_number(mobile)
    if not user:
        user = db_manager.create_user(mobile, name)
        logger.info(f"Created user: {user}")
    
    # Dates
    today = datetime.datetime.now(ZoneInfo("Asia/Kolkata")).date()
    tomorrow = today + datetime.timedelta(days=1)
    day_after = today + datetime.timedelta(days=2)
    
    # Create Appointment A (Tomorrow 10:00 AM)
    time_a = "10:00:00"
    appt_a = db_manager.create_appointment(
        name, mobile, "General Checkout", 
        tomorrow.strftime("%Y-%m-%d"), time_a
    )
    logger.info(f"Created Appointment A: {appt_a}")
    
    # Create Appointment B (Tomorrow 11:00 AM) - The timestamp we will try to steal
    time_b = "11:00:00"
    appt_b = db_manager.create_appointment(
        name, mobile, "General Checkout",
        tomorrow.strftime("%Y-%m-%d"), time_b
    )
    logger.info(f"Created Appointment B: {appt_b}")
    
    # Create Appointment C (Day After 10:00 AM) - A free slot
    time_c = "10:00:00"
    
    try:
        # 2. Test get_upcoming_appointments
        logger.info("\n--- Test 1: Get Upcoming Appointments ---")
        upcoming = get_upcoming_appointments.invoke({"mobile_number": mobile})
        logger.info(f"Upcoming Appointments Result:\n{upcoming}")
        assert "Your upcoming appointments:" in upcoming
        
        # 3. Test Reschedule to OCCUPIED slot (A -> B's time)
        logger.info("\n--- Test 2: Reschedule to Occupied Slot (Should Fail) ---")
        # Try to move A to 11:00 AM (which B has)
        result_fail = update_appointment_in_db.invoke({
            "appointment_id": appt_a['appointment_id'],
            "date": tomorrow.strftime("%Y-%m-%d"),
            "time": time_b
        })
        logger.info(f"Update Result (Expect Failure): {result_fail}")
        assert "already booked" in result_fail
        
        # 4. Test Reschedule to FREE slot (A -> Day After 10:00 AM)
        logger.info("\n--- Test 3: Reschedule to Free Slot (Should Success) ---")
        result_success = update_appointment_in_db.invoke({
            "appointment_id": appt_a['appointment_id'],
            "date": day_after.strftime("%Y-%m-%d"),
            "time": time_c
        })
        logger.info(f"Update Result (Expect Success): {result_success}")
        assert "Appointment updated successfully" in result_success
        
        # 5. Verify Update
        logger.info("\n--- Test 4: Verify Update in DB ---")
        # Re-fetch upcoming
        upcoming_new = get_upcoming_appointments.invoke({"mobile_number": mobile})
        logger.info(f"New Upcoming Appointments:\n{upcoming_new}")
        assert day_after.strftime("%Y-%m-%d") in upcoming_new
        
        logger.info("\n✅ RESCHEDULE FLOW TEST PASSED")
        
    except AssertionError as e:
        logger.error(f"\n❌ TEST FAILED: {e}")
    except Exception as e:
        logger.error(f"\n❌ TEST ERROR: {e}")
    finally:
        # Cleanup (Optional - currently using persistent DB, but good to know)
        pass

if __name__ == "__main__":
    test_reschedule_flow()
