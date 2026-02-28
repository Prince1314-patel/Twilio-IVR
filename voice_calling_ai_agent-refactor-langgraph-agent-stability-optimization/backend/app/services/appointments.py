"""
Appointment Service
==================

This module provides services for managing appointments, including discovery and filtering.
"""

from datetime import date, datetime, time
from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.database.models import Appointment

class AppointmentService:
    """
    Service for handling appointment operations.
    """
    
    @staticmethod
    def get_upcoming_appointments(db: Session, user_id: int) -> List[Appointment]:
        """
        Fetch all upcoming appointments for a specific user.
        
        Upcoming means:
        1. Date is in the future (> today)
        2. OR Date is today AND time is in the future (> now)
        3. Status is 'scheduled'
        
        Args:
            db (Session): Database session
            user_id (int): ID of the user
            
        Returns:
            List[Appointment]: List of upcoming appointments sorted by date and time
        """
        now = datetime.now()
        today = now.date()
        current_time = now.time()
        
        # We want:
        # (date > today) OR (date == today AND time > current_time)
        # AND status == 'scheduled'
        # AND user_id == user_id
        
        upcoming_filter = or_(
            Appointment.appointment_date > today,
            and_(
                Appointment.appointment_date == today,
                Appointment.appointment_time > current_time
            )
        )
        
        appointments = db.query(Appointment).filter(
            and_(
                Appointment.user_id == user_id,
                Appointment.status == "scheduled",
                upcoming_filter
            )
        ).order_by(
            Appointment.appointment_date.asc(),
            Appointment.appointment_time.asc()
        ).all()
        
        return appointments

    @staticmethod
    def cancel_appointment(db: Session, appointment_id: int) -> Appointment | None:
        """
        Cancel an appointment by setting its status to 'cancelled'.
        
        Args:
            db (Session): Database session
            appointment_id (int): ID of the appointment to cancel
            
        Returns:
            Appointment | None: The updated appointment object if found, None otherwise
        """
        appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
        
        if appointment:
            appointment.status = "cancelled"
            db.commit()
            db.refresh(appointment)
            
        return appointment

    @staticmethod
    def reschedule_appointment(db: Session, appointment_id: int, new_date: date, new_time: time) -> Appointment | None:
        """
        Reschedule an appointment to a new date and time.
        
        Args:
            db (Session): Database session
            appointment_id (int): ID of the appointment to reschedule
            new_date (date): New date for the appointment
            new_time (time): New time for the appointment
            
        Returns:
            Appointment | None: The updated appointment object if found, None otherwise
        """
        appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
        
        if appointment:
            appointment.appointment_date = new_date
            appointment.appointment_time = new_time
            # If it was cancelled, we might want to set it back to scheduled.
            # Assuming rescheduling implies re-activating if it was cancelled, or moving if it was scheduled.
            appointment.status = "scheduled" 
            
            db.commit()
            db.refresh(appointment)
            
        return appointment

    @staticmethod
    def create_appointment(
        db: Session, 
        user_id: int, 
        appointment_type: str, 
        date: date, 
        time: time, 
        notes: str = None
    ) -> Appointment:
        """
        Create a new appointment.
        
        Args:
            db (Session): Database session
            user_id (int): User ID
            appointment_type (str): Type of appointment
            date (date): Date of appointment
            time (time): Time of appointment
            notes (str, optional): Additional notes
            
        Returns:
            Appointment: The created appointment object
        """
        # Note: We assume availability has been checked by the caller or prior to this call.
        # However, for robustness, we could integrate AvailabilityService here too.
        # Given the plan, we proceed with creation.
        
        # Simple token generation (could be enhanced)
        token_number = int(datetime.now().timestamp() % 10000)
        
        new_appointment = Appointment(
            user_id=user_id,
            appointment_type=appointment_type,
            appointment_date=date,
            appointment_time=time,
            token_number=token_number,
            status="scheduled",
            notes=notes
        )
        
        db.add(new_appointment)
        db.commit()
        db.refresh(new_appointment)
        
        return new_appointment
