"""
Availability Service
===================

This module provides services for checking appointment availability.
"""

from datetime import date, time, datetime, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.database.models import Appointment
from app.core.config import settings

class AvailabilityService:
    """
    Service for handling availability checks.
    """
    
    SLOT_DURATION_MINUTES = 30
    
    @classmethod
    def generate_slots(cls) -> List[time]:
        """
        Generate all possible time slots based on business hours.
        """
        slots = []
        start_hour = settings.BUSINESS_START_HOUR
        end_hour = settings.BUSINESS_END_HOUR
        
        current_time = time(start_hour, 0)
        end_time = time(end_hour, 0)
        
        while current_time < end_time:
            slots.append(current_time)
            
            # Add duration
            dt = datetime.combine(date.today(), current_time) + timedelta(minutes=cls.SLOT_DURATION_MINUTES)
            current_time = dt.time()
            
        return slots
    
    @staticmethod
    def is_slot_available(db: Session, appointment_date: date, appointment_time: time) -> bool:
        """
        Check if a specific date and time slot is available.
        """
        existing_appointment = db.query(Appointment).filter(
            and_(
                Appointment.appointment_date == appointment_date,
                Appointment.appointment_time == appointment_time,
                Appointment.status != "cancelled"
            )
        ).first()
        
        return existing_appointment is None

    @classmethod
    def get_available_slots(cls, db: Session, appointment_date: date) -> List[time]:
        """
        Get list of all available slots for a given date.
        
        Args:
            db (Session): Database session
            appointment_date (date): Date to check
            
        Returns:
            List[time]: List of available time slots
        """
        all_slots = cls.generate_slots()
        
        # Get all booked slots for the day
        booked_appointments = db.query(Appointment).filter(
            and_(
                Appointment.appointment_date == appointment_date,
                Appointment.status != "cancelled"
            )
        ).all()
        
        booked_times = {appt.appointment_time for appt in booked_appointments}
        
        return [slot for slot in all_slots if slot not in booked_times]

    @classmethod
    def get_nearest_slot(cls, db: Session, appointment_date: date, target_time: time) -> Optional[time]:
        """
        Find the nearest available slot to the target time on the same date.
        
        Args:
            db (Session): Database session
            appointment_date (date): Date to check
            target_time (time): Desired time
            
        Returns:
            Optional[time]: Nearest available slot time, or None if no slots available
        """
        available_slots = cls.get_available_slots(db, appointment_date)
        
        if not available_slots:
            return None
            
        # Convert times to minutes from midnight for easy comparison
        target_minutes = target_time.hour * 60 + target_time.minute
        
        def time_diff(slot):
            slot_minutes = slot.hour * 60 + slot.minute
            return abs(slot_minutes - target_minutes)
            
        nearest = min(available_slots, key=time_diff)
        return nearest
