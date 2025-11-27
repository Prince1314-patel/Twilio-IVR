"""
Database Management Module
========================

This module provides a comprehensive database interface for managing appointments
in a SQLite database. It handles all CRUD operations for appointments including:
- Creating and initializing the database schema
- Checking appointment availability
- Managing time slots
- Creating new appointments

The module uses SQLite for persistence, which provides atomic transactions
and ACID compliance for reliable appointment management.

Dependencies:
    - sqlite3
    - datetime
    - typing

Author: Advanced AI Systems Team
Last Modified: 2025-06-05
"""

import sqlite3
import datetime
from typing import List, Dict

class DatabaseManager:
    """
    Manages all database operations for the appointment system.
    
    This class provides a clean interface for all appointment-related database
    operations, ensuring proper connection management and error handling.
    It implements the Repository pattern for data access abstraction.
    
    Attributes:
        db_path (str): Path to the SQLite database file
    
    Example:
        >>> db = DatabaseManager()
        >>> available = db.check_availability("2025-06-05", "14:30:00")
        >>> if available:
        ...     db.create_appointment("John Doe", "9876543210", 
        ...                          "regular", "2025-06-05", "14:30:00")
    """
    
    def __init__(self, db_path: str = "appointments.db"):
        """
        Initialize DatabaseManager with database path.
        
        Args:
            db_path (str): Path to SQLite database file. Defaults to 'appointments.db' in the current directory.
        """
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """
        Initialize the database schema.
        
        Creates the appointments table if it doesn't exist.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS appointments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                mobile_number TEXT NOT NULL,
                appointment_type TEXT NOT NULL,
                appointment_date DATE NOT NULL,
                appointment_time TIME NOT NULL,
                status TEXT DEFAULT 'scheduled',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                notes TEXT
            )
        ''')
        
        # Migration: Check if mobile_number column exists, if not add it
        cursor.execute("PRAGMA table_info(appointments)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'mobile_number' not in columns:
            try:
                cursor.execute('ALTER TABLE appointments ADD COLUMN mobile_number TEXT')
            except sqlite3.OperationalError:
                # Column addition failed, ignore
                pass
        
        conn.commit()
        conn.close()
    
    def check_availability(self, date: str, time: str) -> bool:
        """
        Check if a specific time slot is available for booking.
        
        Args:
            date (str): Date to check in YYYY-MM-DD format.
            time (str): Time to check in HH:MM:SS format.

        Returns:
            bool: True if the slot is available, False otherwise.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT COUNT(*) FROM appointments 
            WHERE appointment_date = ? AND appointment_time = ? AND status != 'cancelled'
        ''', (date, time))
        
        count = cursor.fetchone()[0]
        conn.close()
        
        return count == 0
    
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
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT appointment_time FROM appointments 
            WHERE appointment_date = ? AND status != 'cancelled'
        ''', (date,))
        
        booked_times = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        available_slots = []
        for hour in range(start_hour, end_hour):
            for minute in [0, 30]:
                time_slot = f"{hour:02d}:{minute:02d}:00"
                if time_slot not in booked_times:
                    readable_time = datetime.time(hour, minute).strftime("%I:%M %p")
                    available_slots.append(readable_time)
        
        return available_slots
    
    def create_appointment(self, name: str, mobile_number: str, appointment_type: str, 
                         date: str, time: str, notes: str = "") -> Dict:
        """
        Create a new appointment in the database.
        
        Args:
            name (str): Client's full name.
            mobile_number (str): Client's mobile number (10-digit Indian mobile number).
            appointment_type (str): Type of appointment (regular, emergency, or followup).
            date (str): Appointment date in YYYY-MM-DD format.
            time (str): Appointment time in HH:MM:SS format.
            notes (str, optional): Additional notes about the appointment.

        Returns:
            Dict: Response dictionary containing:
                - success (bool): Whether the operation was successful
                - appointment_id (int, optional): ID of created appointment
                - message (str): Success or error message
                - error (str, optional): Error details if operation failed
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO appointments (name, mobile_number, appointment_type, appointment_date, 
                                       appointment_time, notes)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (name, mobile_number, appointment_type, date, time, notes))
            
            appointment_id = cursor.lastrowid
            conn.commit()
            
            return {
                "success": True,
                "appointment_id": appointment_id,
                "message": "Appointment created successfully"
            }
        except Exception as e:
            conn.rollback()
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to create appointment"
            }
        finally:
            conn.close()
    
    def get_appointments_by_date(self, date: str) -> List[Dict]:
        """
        Get all appointments for a specific date.

        Args:
            date (str): Date to filter appointments (YYYY-MM-DD).

        Returns:
            List[Dict]: List of appointment records for the date.
        """
        conn = sqlite3.connect(self.db_path)
        # Use row_factory to get column names
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, name, mobile_number, appointment_type, appointment_date, 
                   appointment_time, status, created_at, notes
            FROM appointments 
            WHERE appointment_date = ? AND status != 'cancelled'
            ORDER BY appointment_time
        ''', (date,))
        
        appointments = []
        for row in cursor.fetchall():
            appointments.append({
                "id": row["id"],
                "name": row["name"],
                "mobile_number": row["mobile_number"],
                "appointment_type": row["appointment_type"],
                "appointment_date": row["appointment_date"],
                "appointment_time": row["appointment_time"],
                "status": row["status"],
                "created_at": row["created_at"],
                "notes": row["notes"] if row["notes"] else ""
            })
        
        conn.close()
        return appointments

    def update_appointment(self, appointment_id: int, **fields) -> Dict:
        """
        Update an existing appointment in the database.
        Args:
            appointment_id (int): The ID of the appointment to update.
            **fields: Fields to update (name, mobile_number, appointment_type, appointment_date, appointment_time, status, notes).
        Returns:
            Dict: Response dictionary containing:
                - success (bool): Whether the operation was successful
                - message (str): Success or error message
                - error (str, optional): Error details if operation failed
        """
        allowed_fields = {"name", "mobile_number", "appointment_type", "appointment_date", "appointment_time", "status", "notes"}
        update_fields = {k: v for k, v in fields.items() if k in allowed_fields}
        if not update_fields:
            return {"success": False, "message": "No valid fields to update."}
        set_clause = ", ".join([f"{k} = ?" for k in update_fields])
        values = list(update_fields.values())
        values.append(appointment_id)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute(f"""
                UPDATE appointments SET {set_clause} WHERE id = ?
            """, values)
            conn.commit()
            if cursor.rowcount == 0:
                return {"success": False, "message": "Appointment not found."}
            return {"success": True, "message": "Appointment updated successfully."}
        except Exception as e:
            conn.rollback()
            return {"success": False, "error": str(e), "message": "Failed to update appointment."}
        finally:
            conn.close()

    def cancel_appointment(self, appointment_id: int) -> Dict:
        """
        Cancel (soft-delete) an appointment by setting its status to 'cancelled'.
        Args:
            appointment_id (int): The ID of the appointment to cancel.
        Returns:
            Dict: Response dictionary containing:
                - success (bool): Whether the operation was successful
                - message (str): Success or error message
                - error (str, optional): Error details if operation failed
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE appointments SET status = 'cancelled' WHERE id = ?
            """, (appointment_id,))
            conn.commit()
            if cursor.rowcount == 0:
                return {"success": False, "message": "Appointment not found."}
            return {"success": True, "message": "Appointment cancelled successfully."}
        except Exception as e:
            conn.rollback()
            return {"success": False, "error": str(e), "message": "Failed to cancel appointment."}
        finally:
            conn.close()