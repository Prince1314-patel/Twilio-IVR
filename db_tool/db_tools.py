"""
Database Tools Module
===================

This module provides a high-level interface for database operations in the appointment system,
implementing the Tool pattern for seamless integration with LangChain's agent framework.
It wraps the DatabaseManager functionality in LangChain-compatible tools that can be
directly used by AI agents.

Features:
- Appointment availability checking
- Appointment creation
- Available time slots retrieval
- Error handling and user-friendly responses

The module serves as a bridge between the AI agents and the database layer,
ensuring type safety and proper error handling.

Dependencies:
    - langchain_core
    - db_manager (local module)

Author: Advanced AI Systems Team
Last Modified: 2025-06-05
"""

from db_tool.db_manager import DatabaseManager
from langchain_core.tools import tool
import datetime
from zoneinfo import ZoneInfo
import re
import logging

# Set up logging
logger = logging.getLogger("appointment_tools")
logger.setLevel(logging.INFO)
file_handler = logging.FileHandler("appointment_tools.log")
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
if not logger.hasHandlers():
    logger.addHandler(file_handler)

current_time = datetime.datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%H:%M:%S")
current_date = datetime.datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d")
# Initialize database manager as a singleton
db_manager = DatabaseManager()

def validate_date(date_str):
    """
    Validate that the date string is in YYYY-MM-DD format.

    Args:
        date_str (str): The date string to validate.

    Returns:
        Tuple[bool, str]: (True, "") if valid, (False, error message) otherwise.
    """
    try:
        datetime.datetime.strptime(date_str, "%Y-%m-%d")
        return True, ""
    except ValueError:
        return False, "Date must be in YYYY-MM-DD format."

def validate_time(time_str):
    """
    Validate that the time string is in HH:MM:SS format.

    Args:
        time_str (str): The time string to validate.

    Returns:
        Tuple[bool, str]: (True, "") if valid, (False, error message) otherwise.
    """
    try:
        datetime.datetime.strptime(time_str, "%H:%M:%S")
        return True, ""
    except ValueError:
        return False, "Time must be in HH:MM:SS format."

def validate_email(email):
    """
    Validate that the email is in a standard email format.

    Args:
        email (str): The email address to validate.

    Returns:
        Tuple[bool, str]: (True, "") if valid, (False, error message) otherwise.
    """
    pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    if re.match(pattern, email):
        return True, ""
    return False, "Invalid email format."

def validate_name(name):
    """
    Validate that the name contains only allowed characters.

    Args:
        name (str): The name to validate.

    Returns:
        Tuple[bool, str]: (True, "") if valid, (False, error message) otherwise.
    """
    # Allow letters, spaces, hyphens, apostrophes, and accented characters
    pattern = r"^[A-Za-zÀ-ÖØ-öø-ÿ'\- ]+$"
    if not name or not re.match(pattern, name):
        return False, "Name must only contain letters, spaces, hyphens, or apostrophes."
    return True, ""

def validate_appointment_type(appointment_type):
    """
    Validate that the appointment type is one of the allowed types.

    Args:
        appointment_type (str): The appointment type to validate.

    Returns:
        Tuple[bool, str]: (True, "") if valid, (False, error message) otherwise.
    """
    allowed_types = ["telephonic", "virtual"]
    if appointment_type.lower() in allowed_types:
        return True, ""
    return False, f"Appointment type must be one of: {', '.join(allowed_types)}."

def is_future_datetime(date_str, time_str):
    """
    Check if the given date and time are in the future (Asia/Kolkata timezone).

    Args:
        date_str (str): Date in YYYY-MM-DD format.
        time_str (str): Time in HH:MM:SS format.

    Returns:
        Tuple[bool, str]: (True, "") if in the future, (False, error message) otherwise.
    """
    try:
        date_str = str(date_str).strip()
        time_str = str(time_str).strip()
        logger.debug(f"is_future_datetime: date_str='{date_str}', time_str='{time_str}'")
        now = datetime.datetime.now(ZoneInfo("Asia/Kolkata"))
        input_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
        input_time = datetime.datetime.strptime(time_str, "%H:%M:%S").time()
        current_date = now.date()
        current_time = now.time()
        if input_date < current_date:
            return False, "Date is in the past."
        elif input_date == current_date:
            if input_time > current_time:
                return True, ""
            else:
                return False, "Time is in the past."
        else:  # input_date > current_date
            return True, ""
    except Exception as e:
        logger.error(f"is_future_datetime: Exception: {e} | date_str='{date_str}', time_str='{time_str}'")
        return False, "Invalid date or time."

def is_within_business_hours(time_str, start_hour=9, end_hour=17):
    """
    Check if the time is within business hours.

    Args:
        time_str (str): Time in HH:MM:SS format.
        start_hour (int, optional): Start of business hours (24h). Defaults to 9.
        end_hour (int, optional): End of business hours (24h). Defaults to 17.

    Returns:
        Tuple[bool, str]: (True, "") if within business hours, (False, error message) otherwise.
    """
    try:
        t = datetime.datetime.strptime(time_str, "%H:%M:%S").time()
        return start_hour <= t.hour < end_hour, ""
    except Exception:
        return False, "Invalid time."

def is_slot_granular(time_str):
    """
    Check if the time is on the hour or half-hour (granular slot).

    Args:
        time_str (str): Time in HH:MM:SS format.

    Returns:
        Tuple[bool, str]: (True, "") if slot is granular, (False, error message) otherwise.
    """
    try:
        t = datetime.datetime.strptime(time_str, "%H:%M:%S").time()
        return t.minute in [0, 30], ""
    except Exception:
        return False, "Invalid time."

# Helper to get next closest available slots
def get_next_closest_slots(date, requested_time, max_slots=5):
    """
    Get the next closest available slots for a given date and requested time.

    Args:
        date (str): Date in YYYY-MM-DD format.
        requested_time (str): Requested time in HH:MM:SS format.
        max_slots (int, optional): Maximum number of slots to return. Defaults to 5.

    Returns:
        List[str]: List of closest available slot times as strings.
    """
    slots = db_manager.get_available_slots(date)
    # Convert requested_time and slots to datetime.time for comparison
    try:
        req_time = datetime.datetime.strptime(requested_time, "%H:%M:%S").time()
        slot_times = [(s, datetime.datetime.strptime(datetime.datetime.strptime(s, "%I:%M %p").strftime("%H:%M:%S"), "%H:%M:%S").time()) for s in slots]
        # Sort by time difference from requested_time
        slot_times.sort(key=lambda x: abs((datetime.datetime.combine(datetime.date.today(), x[1]) - datetime.datetime.combine(datetime.date.today(), req_time)).total_seconds()))
        return [s[0] for s in slot_times[:max_slots]]
    except Exception:
        return slots[:max_slots]

def mask_email(email):
    """
    Mask the email address for privacy, showing only the first and last character before the @.

    Args:
        email (str): The email address to mask.

    Returns:
        str: Masked email address.
    """
    if not email or '@' not in email:
        return email
    name, domain = email.split('@', 1)
    if len(name) <= 2:
        masked = name[0] + '*' * (len(name)-1)
    else:
        masked = name[0] + '*' * (len(name)-2) + name[-1]
    return masked + '@' + domain

@tool
def check_appointment_availability(date: str, time: str) -> str:
    """
    Check if an appointment slot is available for the given date and time.

    Args:
        date (str): Date to check in YYYY-MM-DD format.
        time (str): Time to check in HH:MM:SS format.

    Returns:
        str: Availability message or error message.
    """
    log_input = {'date': date, 'time': time}
    logger.info(f"Tool: check_appointment_availability | Input: {log_input}")
    # Input validation
    valid, msg = validate_date(date)
    if not valid:
        logger.warning(f"Tool: check_appointment_availability | Validation failed: {msg}")
        return msg
    valid, msg = validate_time(time)
    if not valid:
        logger.warning(f"Tool: check_appointment_availability | Validation failed: {msg}")
        return msg
    valid, msg = is_future_datetime(date, time)
    if not valid:
        logger.warning(f"Tool: check_appointment_availability | Validation failed: {msg}")
        return "Cannot check availability for a past date/time."
    valid, msg = is_within_business_hours(time)
    if not valid:
        logger.warning(f"Tool: check_appointment_availability | Validation failed: {msg}")
        return "Time must be within business hours (09:00 to 17:00)."
    valid, msg = is_slot_granular(time)
    if not valid:
        logger.warning(f"Tool: check_appointment_availability | Validation failed: {msg}")
        return "Appointments can only be booked on the hour or half-hour (e.g., 09:00:00, 09:30:00)."
    try:
        is_available = db_manager.check_availability(date, time)
        if is_available:
            result = f"Time slot {time} on {date} is available."
            logger.info(f"Tool: check_appointment_availability | Result: {result}")
            return result
        else:
            # Suggest next closest available slots
            alt_slots = get_next_closest_slots(date, time)
            if alt_slots:
                slots_str = ", ".join(alt_slots)
                result = f"Time slot {time} on {date} is not available. Closest available slots: {slots_str}"
                logger.info(f"Tool: check_appointment_availability | Result: {result}")
                return result
            else:
                result = f"Time slot {time} on {date} is not available. No available slots for this date."
                logger.info(f"Tool: check_appointment_availability | Result: {result}")
                return result
    except Exception as e:
        logger.error(f"Tool: check_appointment_availability | Exception: {str(e)}")
        return f"Error checking availability: {str(e)}"

@tool
def create_appointment_in_db(name: str, email: str, appointment_type: str, 
                           date: str, time: str, notes: str = "") -> str:
    """
    Create a new appointment in the database with the provided details.

    Args:
        name (str): Client's full name.
        email (str): Client's email address.
        appointment_type (str): Type of appointment (e.g., telephonic, virtual).
        date (str): Appointment date in YYYY-MM-DD format.
        time (str): Appointment time in HH:MM:SS format.
        notes (str, optional): Additional notes about the appointment.

    Returns:
        str: Success or error message.
    """
    log_input = {'name': name, 'email': mask_email(email), 'appointment_type': appointment_type, 'date': date, 'time': time, 'notes': notes}
    logger.info(f"Tool: create_appointment_in_db | Input: {log_input}")
    # Input validation
    valid, msg = validate_name(name)
    if not valid:
        logger.warning(f"Tool: create_appointment_in_db | Validation failed: {msg}")
        return msg
    valid, msg = validate_email(email)
    if not valid:
        logger.warning(f"Tool: create_appointment_in_db | Validation failed: {msg}")
        return msg
    valid, msg = validate_appointment_type(appointment_type)
    if not valid:
        logger.warning(f"Tool: create_appointment_in_db | Validation failed: {msg}")
        return msg
    valid, msg = validate_date(date)
    if not valid:
        logger.warning(f"Tool: create_appointment_in_db | Validation failed: {msg}")
        return msg
    valid, msg = validate_time(time)
    if not valid:
        logger.warning(f"Tool: create_appointment_in_db | Validation failed: {msg}")
        return msg
    valid, msg = is_future_datetime(date, time)
    if not valid:
        logger.warning(f"Tool: create_appointment_in_db | Validation failed: {msg}")
        return "Cannot book an appointment in the past."
    valid, msg = is_within_business_hours(time)
    if not valid:
        logger.warning(f"Tool: create_appointment_in_db | Validation failed: {msg}")
        return "Time must be within business hours (09:00 to 17:00)."
    valid, msg = is_slot_granular(time)
    if not valid:
        logger.warning(f"Tool: create_appointment_in_db | Validation failed: {msg}")
        return "Appointments can only be booked on the hour or half-hour (e.g., 09:00:00, 09:30:00)."
    # Double booking check
    if not db_manager.check_availability(date, time):
        # Suggest next closest available slots
        alt_slots = get_next_closest_slots(date, time)
        if alt_slots:
            slots_str = ", ".join(alt_slots)
            result = f"Time slot {time} on {date} is not available. Closest available slots: {slots_str}"
            logger.info(f"Tool: create_appointment_in_db | Result: {result}")
            return result
        else:
            result = f"Time slot {time} on {date} is not available. No available slots for this date."
            logger.info(f"Tool: create_appointment_in_db | Result: {result}")
            return result
    try:
        result = db_manager.create_appointment(name, email, appointment_type, date, time, notes)
        if result["success"]:
            msg = f"Appointment created successfully with ID: {result['appointment_id']}"
            logger.info(f"Tool: create_appointment_in_db | Result: {msg}")
            return msg
        else:
            msg = f"Failed to create appointment: {result['message']}"
            logger.warning(f"Tool: create_appointment_in_db | Result: {msg}")
            return msg
    except Exception as e:
        logger.error(f"Tool: create_appointment_in_db | Exception: {str(e)}")
        return f"Error creating appointment: {str(e)}"

@tool
def get_available_slots_for_date(date: str) -> str:
    """
    Get all available appointment slots for a specific date.

    Args:
        date (str): Date to check in YYYY-MM-DD format.

    Returns:
        str: Comma-separated list of available slots or error message.
    """
    log_input = {'date': date}
    logger.info(f"Tool: get_available_slots_for_date | Input: {log_input}")
    valid, msg = validate_date(date)
    if not valid:
        logger.warning(f"Tool: get_available_slots_for_date | Validation failed: {msg}")
        return msg
    try:
        slots = db_manager.get_available_slots(date)
        # For today, filter out slots that are already in the past
        today = datetime.datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d")
        if date == today:
            now = datetime.datetime.now(ZoneInfo("Asia/Kolkata")).time()
            filtered_slots = []
            for s in slots:
                slot_time = datetime.datetime.strptime(datetime.datetime.strptime(s, "%I:%M %p").strftime("%H:%M:%S"), "%H:%M:%S").time()
                if slot_time > now:
                    filtered_slots.append(s)
            slots = filtered_slots
        if slots:
            result = f"Available slots for {date}: {', '.join(slots)}"
            logger.info(f"Tool: get_available_slots_for_date | Result: {result}")
            return result
        else:
            result = f"No available slots for {date}"
            logger.info(f"Tool: get_available_slots_for_date | Result: {result}")
            return result
    except Exception as e:
        logger.error(f"Tool: get_available_slots_for_date | Exception: {str(e)}")
        return f"Error getting available slots: {str(e)}"