"""
Voice API Router
================

This module provides REST API endpoints for voice functionality including
Twilio webhook handling and voice call management.

Note: Real-time streaming is handled by voice_stream.py router.
This router maintains legacy endpoints for call management.

Author: Advanced AI Systems Team
Last Modified: 2025-01-27
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from twilio.twiml.voice_response import VoiceResponse
from pydantic import BaseModel
from typing import Optional
import logging
import time
from twilio.rest import Client

from app.core.config import settings

logger = logging.getLogger(__name__)

# Create router instance
router = APIRouter()

# Initialize Twilio client
twilio_client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

# In-memory stores (legacy, kept for compatibility)
call_sessions = {}


def retry_twilio_operation(operation_func, operation_name, *args, **kwargs):
    """
    Retry wrapper for Twilio operations with exponential backoff.
    
    Args:
        operation_func: The Twilio operation function to retry
        operation_name: Human-readable name for logging
        *args: Arguments to pass to the operation function
        **kwargs: Keyword arguments to pass to the operation function
        
    Returns:
        The result of the operation function
        
    Raises:
        Exception: If all retry attempts fail
    """
    max_retries = 3
    retry_delay = 2  # seconds
    
    for attempt in range(max_retries):
        try:
            return operation_func(*args, **kwargs)
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1} failed for {operation_name}: {e}")
            
            # If this is the last attempt, raise the error
            if attempt == max_retries - 1:
                logger.error(f"All {max_retries} attempts failed for {operation_name}: {e}")
                raise
            
            # Wait before retrying (exponential backoff)
            time.sleep(retry_delay * (attempt + 1))


class CallRequest(BaseModel):
    """
    Pydantic model for initiating voice calls.
    
    Attributes:
        phone_number (str): Phone number to call
        message (Optional[str]): Optional message to include in the call
    """
    phone_number: str
    message: Optional[str] = None

class CallResponse(BaseModel):
    """
    Pydantic model for call initiation responses.
    
    Attributes:
        call_sid (str): Twilio call SID
        status (str): Call status
        message (str): Response message
    """
    call_sid: str
    status: str
    message: str

@router.post("/initiate-call", response_model=CallResponse)
async def initiate_call(call_request: CallRequest):
    """
    Initiate a voice call to the specified phone number with retry logic for network issues.
    
    Args:
        call_request (CallRequest): Call request details
        
    Returns:
        CallResponse: Call initiation response
        
    Raises:
        HTTPException: If call initiation fails after retries
    """
    # Validate phone number format (basic validation)
    if not call_request.phone_number.startswith('+'):
        raise HTTPException(
            status_code=400,
            detail="Phone number must include country code (e.g., +1234567890)"
        )
    
    try:
        # Create Twilio call with retry logic
        call = retry_twilio_operation(
            twilio_client.calls.create,
            f"call initiation to {call_request.phone_number}",
            to=call_request.phone_number,
            from_=settings.TWILIO_PHONE_NUMBER,
            url=f"{settings.TWILIO_WEBHOOK_URL}/api/voice/incoming-call"
        )
        
        logger.info(f"Initiated call to {call_request.phone_number}: {call.sid}")
        
        return CallResponse(
            call_sid=call.sid,
            status=call.status,
            message=f"Call initiated successfully to {call_request.phone_number}"
        )
        
    except Exception as e:
        logger.error(f"Error initiating call to {call_request.phone_number}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initiate call: {str(e)}"
        )

@router.post("/incoming-call")
async def handle_incoming_call():
    """
    Handle incoming calls from Twilio and redirect to streaming endpoint.
    
    This endpoint now returns TwiML that connects to the Media Stream WebSocket
    for real-time bi-directional audio streaming.
    """
    response = VoiceResponse()
    
    # Convert HTTP/HTTPS URL to WSS (WebSocket Secure) for Media Streams
    # Twilio Media Streams require wss:// protocol
    webhook_url = settings.TWILIO_WEBHOOK_URL
    if not webhook_url:
        logger.error("TWILIO_WEBHOOK_URL is not set")
        response.say("Configuration error. Please contact support.", language='en-US')
        response.hangup()
        return HTMLResponse(content=str(response), media_type="application/xml")
    
    if webhook_url.startswith("https://"):
        stream_url = webhook_url.replace("https://", "wss://") + "/api/voice/stream"
    elif webhook_url.startswith("http://"):
        stream_url = webhook_url.replace("http://", "ws://") + "/api/voice/stream"
    elif webhook_url.startswith("wss://") or webhook_url.startswith("ws://"):
        stream_url = f"{webhook_url}/api/voice/stream"
    else:
        # If URL doesn't start with protocol, assume https and convert to wss
        stream_url = f"wss://{webhook_url}/api/voice/stream"
    
    logger.info(f"Connecting to Media Stream at: {stream_url}")
    
    # Connect to Media Stream WebSocket for real-time bi-directional audio
    # The stream will handle the greeting and all subsequent interactions
    connect = response.connect()
    connect.stream(url=stream_url)
    
    # Note: We don't use response.say() here because the greeting will be sent
    # through the Media Stream as audio (using Sarvam TTS) when the stream starts.
    # This ensures seamless transition and keeps the call active.
    
    return HTMLResponse(content=str(response), media_type="application/xml")

@router.get("/call-status/{call_sid}")
async def get_call_status(call_sid: str):
    """
    Get the status of a specific call with retry logic for network issues.
    
    Args:
        call_sid (str): Twilio call SID
        
    Returns:
        dict: Call status information
        
    Raises:
        HTTPException: If call not found after retries
    """
    try:
        # Fetch call with retry logic
        call = retry_twilio_operation(
            twilio_client.calls(call_sid).fetch,
            f"call status fetch for {call_sid}"
        )
        
        return {
            "call_sid": call.sid,
            "status": call.status,
            "direction": call.direction,
            "from": call.from_formatted,
            "to": call.to_formatted,
            "start_time": call.start_time,
            "end_time": call.end_time,
            "duration": call.duration
        }
        
    except Exception as e:
        logger.error(f"Error fetching call status for {call_sid}: {e}")
        raise HTTPException(
            status_code=404,
            detail=f"Call {call_sid} not found or unavailable"
        )

@router.get("/active-calls")
async def get_active_calls():
    """
    Get list of active call sessions.
    
    Returns:
        dict: List of active call sessions
    """
    return {
        "active_calls": len(call_sessions),
        "call_sessions": list(call_sessions.keys())
    }

