"""
Identity Service
================

This module provides services for extracting phone numbers from request data
and resolving user identity from the database.
"""

from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.database.models import User, Appointment
from app.core.logger_config import get_application_logger

from app.core.logger_config import get_application_logger
from app.utils.validators import validate_and_normalize_mobile_number

logger = get_application_logger()

class IdentityService:
    """Service to handle identity resolution."""

    @staticmethod
    def extract_phone_number(form_data: Dict[str, Any]) -> Optional[str]:
        """
        Extract the phone number from Twilio webhook form data.
        
        Args:
            form_data: The parsed form data from the request.
            
        Returns:
            The extracted phone number (From or To), or None if not found.
        """
        # Check direction to determine which number is the user's
        direction = form_data.get("Direction", "")
        
        # For outbound calls (initiated via API), the user is the 'To' number
        if direction and direction.startswith("outbound"):
            phone_number = form_data.get("To")
        else:
            # For incoming calls, the user is the 'From' number
            phone_number = form_data.get("From")
        
        if not phone_number:
            # Fallback (though for incoming calls 'From' is standard)
            phone_number = form_data.get("Caller")
            
        return phone_number

    @staticmethod
    def resolve_user(db: Session, phone_number: str) -> Optional[User]:
        """
        Look up a user by their phone number.
        
        Args:
            db: Database session.
            phone_number: The phone number to search for.
            
        Returns:
            The User object if found, else None.
        """
        if not phone_number:
            return None
            
        # Normalize the phone number to ensure consistent lookup
        _, normalized_number, _ = validate_and_normalize_mobile_number(phone_number)
            
        try:
            return db.query(User).filter(User.mobile_number == normalized_number).first()
        except Exception as e:
            logger.error(f"Error resolving user for number {normalized_number}: {e}")
            return None

    @staticmethod
    def get_or_create_user(db: Session, phone_number: str, default_name: str = None) -> Optional[User]:
        """
        Get an existing user or create a new one if not found.
        Supports progressive enrichment by allowing nullable names.
        
        Args:
            db: Database session.
            phone_number: The user's phone number.
            default_name: Name to use if creating a new user (can be None for progressive enrichment).
            
        Returns:
            The User object, or None if creation fails.
        """
        if not phone_number:
            return None
            
        try:
            # 1. Try to find existing user
            user = IdentityService.resolve_user(db, phone_number)
            if user:
                return user
                
            # 2. Create new user with nullable name (progressive enrichment)
            # Ensure number is normalized before creating
            _, normalized_number, _ = validate_and_normalize_mobile_number(phone_number)
            
            logger.info(f"Creating new user for number: {normalized_number}")
            new_user = User(
                full_name=default_name,  # Can be None for progressive enrichment
                mobile_number=normalized_number
            )
            db.add(new_user)
            db.commit()
            db.refresh(new_user)
            return new_user
            
        except Exception as e:
            logger.error(f"Error creating user for number {phone_number}: {e}")
            db.rollback()
            return None

    @staticmethod
    def get_last_appointment(db: Session, user_id: int) -> Optional[Appointment]:
        """
        Get the user's most recent appointment.
        
        Args:
            db: Database session.
            user_id: The user ID.
            
        Returns:
            The most recent Appointment object, or None if no appointments found.
        """
        try:
            return db.query(Appointment).filter(
                Appointment.user_id == user_id,
                Appointment.status != 'cancelled'
            ).order_by(
                desc(Appointment.appointment_date),
                desc(Appointment.appointment_time)
            ).first()
        except Exception as e:
            logger.error(f"Error fetching last appointment for user {user_id}: {e}")
            return None

    @staticmethod
    def update_user_name(db: Session, user_id: int, full_name: str) -> Optional[User]:
        """
        Update a user's full name.
        
        Args:
            db: Database session.
            user_id: The user ID.
            full_name: The new full name.
            
        Returns:
            The updated User object, or None if not found/error.
        """
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                user.full_name = full_name
                db.commit()
                db.refresh(user)
                return user
            return None
        except Exception as e:
            logger.error(f"Error updating name for user {user_id}: {e}")
            db.rollback()
            return None
