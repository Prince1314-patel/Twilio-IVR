"""
Appointment API
==============

This module provides endpoints for managing appointments.
"""

from typing import List, Optional
from datetime import date, time, datetime
from fastapi import APIRouter, Depends, HTTPException, status, Path
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.services.appointments import AppointmentService
from app.core.logger_config import get_application_logger

router = APIRouter()
logger = get_application_logger()

class AppointmentResponse(BaseModel):
    id: int
    user_id: int
    appointment_type: str
    appointment_date: date
    appointment_time: time
    token_number: int
    status: str
    notes: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

class UpcomingAppointmentsResponse(BaseModel):
    user_id: int
    count: int
    appointments: List[AppointmentResponse]

@router.get("/user/{user_id}/upcoming", response_model=UpcomingAppointmentsResponse)
async def get_upcoming_appointments(
    user_id: int = Path(..., title="The ID of the user to get appointments for"),
    db: Session = Depends(get_db)
):
    """
    Get all upcoming appointments for a specific user.
    """
    try:
        appointments = AppointmentService.get_upcoming_appointments(db, user_id)
        
        logger.info(f"Retrieved {len(appointments)} upcoming appointments for user {user_id}")
        
        return UpcomingAppointmentsResponse(
            user_id=user_id,
            count=len(appointments),
            appointments=appointments
        )
        
    except Exception as e:
        logger.error(f"Error fetching upcoming appointments for user {user_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error fetching appointments"
        )

@router.post("/{appointment_id}/cancel", response_model=AppointmentResponse)
async def cancel_appointment(
    appointment_id: int = Path(..., title="The ID of the appointment to cancel"),
    db: Session = Depends(get_db)
):
    """
    Cancel an appointment.
    """
    try:
        updated_appointment = AppointmentService.cancel_appointment(db, appointment_id)
        
        if not updated_appointment:
            logger.warning(f"Appointment {appointment_id} not found for cancellation")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Appointment with ID {appointment_id} not found"
            )
            
        logger.info(f"Appointment {appointment_id} cancelled successfully")
        
        return updated_appointment
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling appointment {appointment_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error cancelling appointment"
        )

class RescheduleRequest(BaseModel):
    new_date: date
    new_time: time

@router.post("/{appointment_id}/reschedule", response_model=AppointmentResponse)
async def reschedule_appointment(
    request: RescheduleRequest,
    appointment_id: int = Path(..., title="The ID of the appointment to reschedule"),
    db: Session = Depends(get_db)
):
    """
    Reschedule an appointment.
    """
    try:
        updated_appointment = AppointmentService.reschedule_appointment(
            db, 
            appointment_id,
            request.new_date,
            request.new_time
        )
        
        if not updated_appointment:
            logger.warning(f"Appointment {appointment_id} not found for rescheduling")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Appointment with ID {appointment_id} not found"
            )
            
        logger.info(f"Appointment {appointment_id} rescheduled to {request.new_date} {request.new_time}")
        
        return updated_appointment
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rescheduling appointment {appointment_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error rescheduling appointment"
        )

class CreateAppointmentRequest(BaseModel):
    user_id: int
    appointment_type: str
    date: date
    time: time
    notes: Optional[str] = None

@router.post("/", response_model=AppointmentResponse)
async def create_appointment(
    request: CreateAppointmentRequest,
    db: Session = Depends(get_db)
):
    """
    Create a new appointment.
    """
    try:
        # Optional: check availability here explicitly if needed, but standard flow
        # implies user has already selected from available slots.
        
        new_appointment = AppointmentService.create_appointment(
            db,
            user_id=request.user_id,
            appointment_type=request.appointment_type,
            date=request.date,
            time=request.time,
            notes=request.notes
        )
        
        logger.info(f"Created appointment {new_appointment.id} for user {request.user_id}")
        
        return new_appointment
        
    except Exception as e:
        logger.error(f"Error creating appointment: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error creating appointment"
        )
