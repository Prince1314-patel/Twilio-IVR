
import sys
import os
import datetime
from zoneinfo import ZoneInfo
import logging

# Add backend directory to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.database.manager import DatabaseManager
from app.database.tools.appointment_tools import (
    create_appointment_in_db,
    check_appointment_availability,
    get_available_slots_for_date,
    update_appointment_in_db,
    cancel_appointment_in_db,
    get_upcoming_appointments
)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_all_tools():
    logger.info("Starting comprehensive tool test...")
    
    # Setup
    mobile = "5550005555"
    name = "Tool Tester"
    date_str = (datetime.datetime.now(ZoneInfo("Asia/Kolkata")) + datetime.timedelta(days=5)).strftime("%Y-%m-%d")
    time_slot_1 = "14:00:00"
    time_slot_2 = "15:00:00"
    
    logger.info(f"Test Context: User={name} ({mobile}), Date={date_str}")

    try:
        # 1. Test Availability Check (Before Booking)
        logger.info("\n[1] Testing check_appointment_availability...")
        avail_msg = check_appointment_availability.invoke({"date": date_str, "time": time_slot_1})
        logger.info(f"Result: {avail_msg}")
        
        # 2. Test Create Appointment
        logger.info("\n[2] Testing create_appointment_in_db...")
        create_msg = create_appointment_in_db.invoke({
            "name": name,
            "mobile_number": mobile,
            "appointment_type": "General",
            "date": date_str,
            "time": time_slot_1,
            "notes": "Testing tools"
        })
        logger.info(f"Result: {create_msg}")
        assert "Appointment created successfully" in create_msg
        
        # 3. Test Availability Check (After Booking - Should be False/Warn)
        logger.info("\n[3] Testing check_appointment_availability (Occupied Slot)...")
        avail_msg_occupied = check_appointment_availability.invoke({"date": date_str, "time": time_slot_1})
        logger.info(f"Result: {avail_msg_occupied}")
        # Note: The tool usually returns a string message, we check content
        assert "not available" in avail_msg_occupied.lower() or "false" in avail_msg_occupied.lower()

        # 4. Test Get Upcoming Appointments
        logger.info("\n[4] Testing get_upcoming_appointments...")
        upcoming_msg = get_upcoming_appointments.invoke({"mobile_number": mobile})
        logger.info(f"Result: {upcoming_msg}")
        assert time_slot_1 in upcoming_msg or "14:00" in upcoming_msg or "02:00" in upcoming_msg

        # Extract ID (Lazy parsing for test)
        # assuming format "- ID: <id> ..."
        import re
        match = re.search(r"ID: (\d+)", upcoming_msg)
        if not match:
            raise ValueError("Could not parse Appointment ID from upcoming list")
        appt_id = int(match.group(1))
        logger.info(f"Captured Appointment ID: {appt_id}")

        # 5. Test Update Appointment (Reschedule to new slot)
        logger.info("\n[5] Testing update_appointment_in_db...")
        update_msg = update_appointment_in_db.invoke({
            "appointment_id": appt_id,
            "date": date_str,
            "time": time_slot_2
        })
        logger.info(f"Result: {update_msg}")
        assert "updated successfully" in update_msg

        # 6. Test Get Available Slots
        logger.info("\n[6] Testing get_available_slots_for_date...")
        slots_msg = get_available_slots_for_date.invoke({"date": date_str})
        logger.info(f"Result: {slots_msg}")
        assert "Available slots" in slots_msg

        # 7. Test Cancel Appointment
        logger.info("\n[7] Testing cancel_appointment_in_db...")
        cancel_msg = cancel_appointment_in_db.invoke({"appointment_id": appt_id})
        logger.info(f"Result: {cancel_msg}")
        assert "cancelled successfully" in cancel_msg

        logger.info("\n✅ ALL TOOL TESTS PASSED")

    except AssertionError as e:
        logger.error(f"\n❌ ASSERTION FAILED: {e}")
    except Exception as e:
        logger.error(f"\n❌ EXCEPTION WRAPPER: {e}")

if __name__ == "__main__":
    test_all_tools()
