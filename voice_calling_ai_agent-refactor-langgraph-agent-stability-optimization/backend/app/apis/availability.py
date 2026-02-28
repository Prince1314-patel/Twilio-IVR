"""
Availability API
===============

This module provides endpoints for checking appointment availability.
"""

from datetime import date, time
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.services.availability import AvailabilityService
from app.core.logger_config import get_application_logger

router = APIRouter()
logger = get_application_logger()

class AvailabilityCheckRequest(BaseModel):
    date: date
    time: time

class AvailabilityCheckResponse(BaseModel):
    available: bool
    message: str
    nearest_slot: Optional[time] = None

class AvailableSlotsResponse(BaseModel):
    date: date
    slots: List[time]

@router.post("/check", response_model=AvailabilityCheckResponse)
async def check_availability(
    request: AvailabilityCheckRequest,
    db: Session = Depends(get_db)
):
    """
    Check if an appointment slot is available. 
    If not, suggests the nearest available slot.
    """
    try:
        is_available = AvailabilityService.is_slot_available(
            db, 
            request.date, 
            request.time
        )
        
        nearest_slot = None
        if is_available:
            message = "Slot is available"
        else:
            message = "Slot is already booked"
            # Find nearest slot
            nearest_slot = AvailabilityService.get_nearest_slot(
                db, 
                request.date, 
                request.time
            )
        
        logger.info(f"Availability check for {request.date} {request.time}: {is_available}")
        
        return AvailabilityCheckResponse(
            available=is_available,
            message=message,
            nearest_slot=nearest_slot
        )
        
    except Exception as e:
        logger.error(f"Error checking availability: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error checking availability"
        )

@router.get("/slots", response_model=AvailableSlotsResponse)
async def get_available_slots(
    date: date,
    db: Session = Depends(get_db)
):
    """
    Get all available appointment slots for a specific date.
    """
    try:
        slots = AvailabilityService.get_available_slots(db, date)
        
        return AvailableSlotsResponse(
            date=date,
            slots=slots
        )
        
    except Exception as e:
        logger.error(f"Error listing slots: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error listing slots"
        )
