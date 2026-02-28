"""
Database Management Module
========================

This module provides a comprehensive database interface for managing appointments
using SQLAlchemy ORM. It handles all CRUD operations for appointments including:
- Checking appointment availability
- Managing time slots
- Creating new appointments (and users if needed)

Dependencies:
    - sqlalchemy
    - datetime
    - typing
    - app.database.models
    - app.database.session

Author: Advanced AI Systems Team
Last Modified: 2026-02-03
"""

import datetime
from typing import List, Dict, Optional
from sqlalchemy import and_, func, desc
from sqlalchemy.orm import Session
from zoneinfo import ZoneInfo

from app.database.session import SessionLocal
from app.database.models import User, Appointment
from app.utils.validators import validate_and_normalize_mobile_number

class DatabaseManager:
    """
    Manages all database operations for the appointment system using SQLAlchemy.
    
    This class uses a singleton pattern to avoid creating multiple instances
    and unnecessary connection overhead.
    """
    
    _instance = None
    
    def __new__(cls):
        """
        Implement singleton pattern to reuse the same DatabaseManager instance.
        This reduces connection setup overhead from ~10-50ms to near-zero.
        """
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """
        Initialize DatabaseManager.
        Note: Due to singleton pattern, this is only called once.
        """
        pass
    
    def get_db(self) -> Session:
        """Helper to get a new session."""
        return SessionLocal()

    def check_availability(self, date: str, time: str) -> bool:
        """
        Check if a specific time slot is available for booking.
        
        Args:
            date (str): Date to check in YYYY-MM-DD format.
            time (str): Time to check in HH:MM:SS format.

        Returns:
            bool: True if the slot is available, False otherwise.
        """
        db = self.get_db()
        try:
            # Parse inputs to python objects for safer comparison
            date_obj = datetime.datetime.strptime(date, "%Y-%m-%d").date()
            time_obj = datetime.datetime.strptime(time, "%H:%M:%S").time()

            count = db.query(Appointment).filter(
                Appointment.appointment_date == date_obj,
                Appointment.appointment_time == time_obj,
                Appointment.status != 'cancelled'
            ).count()
            
            return count == 0
        finally:
            db.close()
    
    def get_available_slots(self, date: str, start_hour: int = 9, end_hour: int = 17) -> List[str]:
        """
        Retrieve all available time slots for a given date.
        
        Args:
            date (str): Date to check in YYYY-MM-DD format.
            start_hour (int, optional): Start of business hours (24-hour format). Defaults to 9.
            end_hour (int, optional): End of business hours (24-hour format). Defaults to 17.

        Returns:
            List[str]: List of available time slots in 12-hour format (e.g., ["9:00 AM", "9:30 AM"])
        """
        db = self.get_db()
        try:
            date_obj = datetime.datetime.strptime(date, "%Y-%m-%d").date()

            booked_appointments = db.query(Appointment.appointment_time).filter(
                Appointment.appointment_date == date_obj,
                Appointment.status != 'cancelled'
            ).all()
            
            booked_times = [appt.appointment_time for appt in booked_appointments]
            
            available_slots = []
            for hour in range(start_hour, end_hour):
                for minute in [0, 30]:
                    time_slot = datetime.time(hour, minute)
                    if time_slot not in booked_times:
                        readable_time = time_slot.strftime("%I:%M %p")
                        available_slots.append(readable_time)
            
            return available_slots
        finally:
            db.close()
    
    def create_appointment(self, name: str, mobile_number: str, appointment_type: str, 
                         date: str, time: str, notes: str = "") -> Dict:
        """
        Create a new appointment in the database.
        Automatically creates a User if one does not exist for the mobile number.
        Generates a token number for the day.
        
        Args:
            name (str): Client's full name.
            mobile_number (str): Client's mobile number.
            appointment_type (str): Type of appointment.
            date (str): Appointment date in YYYY-MM-DD format.
            time (str): Appointment time in HH:MM:SS format.
            notes (str, optional): Additional notes.

        Returns:
            Dict: Response dictionary.
        """
        db = self.get_db()
        try:
            date_obj = datetime.datetime.strptime(date, "%Y-%m-%d").date()
            time_obj = datetime.datetime.strptime(time, "%H:%M:%S").time()

            # 1. Find or Create User
            # Normalize mobile number
            _, normalized_mobile, _ = validate_and_normalize_mobile_number(mobile_number)
            
            user = db.query(User).filter(User.mobile_number == normalized_mobile).first()
            if not user:
                user = User(
                    full_name=name,
                    mobile_number=normalized_mobile
                )
                db.add(user)
                db.flush() # Flush to get user.id
            
            # 2. Generate Token Number
            # Get max token number for this date
            max_token = db.query(func.max(Appointment.token_number)).filter(
                Appointment.appointment_date == date_obj
            ).scalar()
            
            next_token = (max_token or 0) + 1

            # 3. Create Appointment
            appointment = Appointment(
                user_id=user.id,
                appointment_type=appointment_type,
                appointment_date=date_obj,
                appointment_time=time_obj,
                token_number=next_token,
                status="scheduled",
                notes=notes
            )
            
            db.add(appointment)
            db.commit()
            db.refresh(appointment)
            
            return {
                "success": True,
                "appointment_id": appointment.id,
                "token_number": appointment.token_number,
                "message": "Appointment created successfully"
            }
        except Exception as e:
            db.rollback()
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to create appointment"
            }
        finally:
            db.close()
    
    def get_appointments_by_date(self, date: str) -> List[Dict]:
        """
        Get all appointments for a specific date.

        Args:
            date (str): Date to filter appointments (YYYY-MM-DD).

        Returns:
            List[Dict]: List of appointment records.
        """
        db = self.get_db()
        try:
            date_obj = datetime.datetime.strptime(date, "%Y-%m-%d").date()
            
            appointments = db.query(Appointment).filter(
                Appointment.appointment_date == date_obj,
                Appointment.status != 'cancelled'
            ).order_by(Appointment.appointment_time).all()
            
            result = []
            for appt in appointments:
                # Eager load user to get name/mobile if needed, 
                # but currently we just return flattened dict structure matching old API
                user = db.query(User).get(appt.user_id)
                
                result.append({
                    "id": appt.id,
                    "name": user.full_name if user else "Unknown",
                    "mobile_number": user.mobile_number if user else "",
                    "appointment_type": appt.appointment_type,
                    "appointment_date": appt.appointment_date.strftime("%Y-%m-%d"),
                    "appointment_time": appt.appointment_time.strftime("%H:%M:%S"),
                    "token_number": appt.token_number,
                    "status": appt.status,
                    "created_at": appt.created_at.isoformat() if appt.created_at else None,
                    "notes": appt.notes or ""
                })
            
            return result
        finally:
            db.close()

    def update_appointment(self, appointment_id: int, caller_mobile_number: str = None, **fields) -> Dict:
        """
        Update an existing appointment.
        """
        db = self.get_db()
        try:
            appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
            if not appointment:
                return {"success": False, "message": "Appointment not found."}
            
            # Ownership validation
            if caller_mobile_number is not None:
                _, normalized_caller_mobile, _ = validate_and_normalize_mobile_number(caller_mobile_number)
                user = db.query(User).filter(User.id == appointment.user_id).first()
                if not user or user.mobile_number != normalized_caller_mobile:
                    return {"success": False, "message": "Ownership validation failed: Appointment does not belong to the user."}

            
            # Map fields to model attributes
            allowed_fields = {"appointment_type", "appointment_date", "appointment_time", "status", "notes"}
            
            # Helper to parse dates/times if they are strings
            if "appointment_date" in fields and isinstance(fields["appointment_date"], str):
                fields["appointment_date"] = datetime.datetime.strptime(fields["appointment_date"], "%Y-%m-%d").date()
            if "appointment_time" in fields and isinstance(fields["appointment_time"], str):
                fields["appointment_time"] = datetime.datetime.strptime(fields["appointment_time"], "%H:%M:%S").time()

            # Check availability if date or time is being updated
            # Use new values if present, otherwise fall back to existing appointment values
            check_date = fields.get("appointment_date", appointment.appointment_date)
            # Ensure check_date is a string for check_availability if it's a date object
            if isinstance(check_date, datetime.date):
                check_date_str = check_date.strftime("%Y-%m-%d")
            else:
                check_date_str = str(check_date)

            check_time = fields.get("appointment_time", appointment.appointment_time)
             # Ensure check_time is a string for check_availability if it's a time object
            if isinstance(check_time, datetime.time):
                check_time_str = check_time.strftime("%H:%M:%S")
            else:
                check_time_str = str(check_time)
            
            # Only check if date or time is actually changing
            time_changing = "appointment_time" in fields and fields["appointment_time"] != appointment.appointment_time
            date_changing = "appointment_date" in fields and fields["appointment_date"] != appointment.appointment_date

            if time_changing or date_changing:
                # We need to check availability for the NEW slot
                # Note: We must release the DB connection from self.get_db() before calling check_availability 
                # if check_availability uses its own connection, OR just use the logic directly.
                # Since check_availability creates a new session, it's safe to call it here as long as we use string formats.
                # However, it might be more efficient to query using the existing 'db' session.
                
                # Let's use the existing session logic to avoid overhead/locking issues
                count = db.query(Appointment).filter(
                    Appointment.appointment_date == check_date,
                    Appointment.appointment_time == check_time,
                    Appointment.status != 'cancelled',
                    Appointment.id != appointment_id # Don't count self if we are just updating metadata but keeping slot (edge case)
                ).count()
                
                if count > 0:
                     return {
                        "success": False, 
                        "message": f"Time slot {check_time_str} on {check_date_str} is already booked. Please choose another time."
                    }

            # Handle User updates (name, mobile) separately as they belong to User model
            # This is a bit tricky: updating a user's name updates it for ALL their appointments.
            # For simplicity, we will update the associated user.
            user_fields_updated = False
            if "name" in fields or "mobile_number" in fields:
                user = db.query(User).get(appointment.user_id)
                if user:
                    if "name" in fields:
                        user.full_name = fields["name"]
                    if "mobile_number" in fields:
                        user.mobile_number = fields["mobile_number"]
                    user_fields_updated = True

            for key, value in fields.items():
                if key in allowed_fields:
                    setattr(appointment, key, value)
            
            db.commit()
            return {"success": True, "message": "Appointment updated successfully."}
        
        except Exception as e:
            db.rollback()
            return {"success": False, "error": str(e), "message": "Failed to update appointment."}
        finally:
            db.close()

    def cancel_appointment(self, appointment_id: int, reason: str = None, caller_mobile_number: str = None) -> Dict:
        """
        Cancel (soft-delete) an appointment.
        
        Args:
            appointment_id: ID of the appointment to cancel
            reason: Optional reason for cancellation (persisted for audit trail)
            caller_mobile_number: Optional mobile number of the user requesting the cancellation, for ownership validation.
        """
        db = self.get_db()
        try:
            appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
            if not appointment:
                return {"success": False, "message": "Appointment not found."}
            
            # Ownership validation
            if caller_mobile_number is not None:
                _, normalized_caller_mobile, _ = validate_and_normalize_mobile_number(caller_mobile_number)
                user = db.query(User).filter(User.id == appointment.user_id).first()
                if not user or user.mobile_number != normalized_caller_mobile:
                    return {"success": False, "message": "Ownership validation failed: Appointment does not belong to the user."}

            
            appointment.status = "cancelled"
            if reason:
                appointment.cancellation_reason = reason
            db.commit()
            return {"success": True, "message": "Appointment cancelled successfully."}
        except Exception as e:
            db.rollback()
            return {"success": False, "error": str(e), "message": "Failed to cancel appointment."}
        finally:
            db.close()
    
    # ========== Progressive User Enrichment Methods ==========
    
    def create_user(self, mobile_number: str, full_name: str = None) -> Optional[Dict]:
        """
        Create a new user.
        Args:
            mobile_number (str): The user's mobile number.
            full_name (str, optional): The user's full name.
        Returns:
            Dict: The created user dictionary, or None if creation failed.
        """
        db = self.get_db()
        try:
            # Normalize mobile number
            _, normalized_mobile, _ = validate_and_normalize_mobile_number(mobile_number)
            
            # Check if user already exists
            existing_user = db.query(User).filter(User.mobile_number == normalized_mobile).first()
            if existing_user:
                return {
                    "user_id": existing_user.id,
                    "mobile_number": existing_user.mobile_number,
                    "name": existing_user.full_name,
                    "created_at": existing_user.created_at
                }
            
            new_user = User(mobile_number=normalized_mobile, full_name=full_name)
            db.add(new_user)
            db.commit()
            db.refresh(new_user)
            return {
                "user_id": new_user.id,
                "mobile_number": new_user.mobile_number,
                "name": new_user.full_name,
                "created_at": new_user.created_at
            }
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating user: {e}")
            return None
        finally:
            db.close()

    def get_user_by_mobile_number(self, mobile_number: str) -> Optional[Dict]:
        """
        Retrieve user information by mobile number.
        
        Args:
            mobile_number: User's mobile number
            
        Returns:
            User information dict or None if not found
            
        Example return:
            {
                "user_id": 1,
                "name": "John Doe",
                "mobile_number": "+1234567890",
                "email": "john@example.com",
                "created_at": "2026-01-15T10:30:00"
            }
        """
        db = self.get_db()
        try:
            # Normalize mobile number
            _, normalized_mobile, _ = validate_and_normalize_mobile_number(mobile_number)
            
            user = db.query(User).filter(User.mobile_number == normalized_mobile).first()
            
            if not user:
                return None
            
            return {
                "user_id": user.id,
                "name": user.full_name,  # Can be None for new users
                "mobile_number": user.mobile_number,
                "email": user.email,
                "created_at": user.created_at.isoformat() if user.created_at else None
            }
        except Exception as e:
            # Log error but don't raise - graceful degradation
            from app.core.logger_config import get_application_logger
            logger = get_application_logger()
            from app.database.tools.appointment_tools import mask_mobile_number
            logger.error(f"Error fetching user by mobile number {mask_mobile_number(mobile_number)}: {e}")
            return None
        finally:
            db.close()
    
    def create_user_with_phone(self, mobile_number: str, name: Optional[str] = None) -> Dict:
        """
        Create a new user with mobile number (name is optional for progressive enrichment).
        
        Args:
            mobile_number: User's mobile number
            name: User's name (optional, can be None for progressive enrichment)
            
        Returns:
            Dict with success status and user_id
            
        Example return:
            {
                "success": True,
                "user_id": 42,
                "message": "User created successfully"
            }
        """
        db = self.get_db()
        try:
            # Normalize mobile number
            _, normalized_mobile, _ = validate_and_normalize_mobile_number(mobile_number)
            
            # Check if user already exists
            existing_user = db.query(User).filter(User.mobile_number == normalized_mobile).first()
            if existing_user:
                return {
                    "success": False,
                    "user_id": existing_user.id,
                    "message": "User already exists with this mobile number"
                }
            
            # Create new user
            new_user = User(
                mobile_number=normalized_mobile,
                full_name=name  # Can be None
            )
            db.add(new_user)
            db.commit()
            db.refresh(new_user)
            
            return {
                "success": True,
                "user_id": new_user.id,
                "message": "User created successfully"
            }
        except Exception as e:
            db.rollback()
            from app.core.logger_config import get_application_logger
            logger = get_application_logger()
            from app.database.tools.appointment_tools import mask_mobile_number
            logger.error(f"Error creating user with mobile number {mask_mobile_number(mobile_number)}: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to create user"
            }
        finally:
            db.close()
    
    def update_user_name(self, user_id: int, name: str) -> Dict:
        """
        Update user's name (progressive enrichment).
        
        Args:
            user_id: User's database ID
            name: User's full name
            
        Returns:
            Dict with success status
            
        Example return:
            {
                "success": True,
                "message": "User name updated successfully"
            }
        """
        db = self.get_db()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return {
                    "success": False,
                    "message": "User not found"
                }
            
            user.full_name = name
            db.commit()
            
            return {
                "success": True,
                "message": "User name updated successfully"
            }
        except Exception as e:
            db.rollback()
            from app.core.logger_config import get_application_logger
            logger = get_application_logger()
            logger.error(f"Error updating name for user {user_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to update user name"
            }
        finally:
            db.close()
    
    def get_user_appointment_history(self, user_id: int, limit: int = 5) -> List[Dict]:
        """
        Get recent appointment history for a user.
        
        Args:
            user_id: User's database ID
            limit: Maximum number of appointments to return (default: 5)
            
        Returns:
            List of recent appointments
            
        Example return:
            [
                {
                    "id": 101,
                    "appointment_type": "Consultation",
                    "appointment_date": "2026-01-15",
                    "appointment_time": "10:00:00",
                    "status": "completed",
                    "notes": "Follow-up needed"
                }
            ]
        """
        db = self.get_db()
        try:
            appointments = db.query(Appointment).filter(
                Appointment.user_id == user_id,
                Appointment.status != 'cancelled'
            ).order_by(
                desc(Appointment.appointment_date),
                desc(Appointment.appointment_time)
            ).limit(limit).all()
            
            result = []
            for appt in appointments:
                result.append({
                    "id": appt.id,
                    "appointment_type": appt.appointment_type,
                    "appointment_date": appt.appointment_date.strftime("%Y-%m-%d"),
                    "appointment_time": appt.appointment_time.strftime("%H:%M:%S"),
                    "status": appt.status,
                    "notes": appt.notes or ""
                })
            
            return result
        except Exception as e:
            from app.core.logger_config import get_application_logger
            logger = get_application_logger()
            logger.error(f"Error fetching appointment history for user {user_id}: {e}")
            return []
        finally:
            db.close()