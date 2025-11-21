"""
Voice API Router
================

This module provides REST API endpoints for voice functionality including
Twilio webhook handling and voice call management.

Author: Advanced AI Systems Team
Last Modified: 2025-01-27
"""

from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse
from twilio.twiml.voice_response import VoiceResponse, Gather
from pydantic import BaseModel
from typing import Optional
import logging
import os
import time
from twilio.rest import Client

from app.core.config import settings
from agentic_graph.agent_graph import run_agentic_graph
from langchain_core.messages import HumanMessage, AIMessage

logger = logging.getLogger(__name__)

# Create router instance
router = APIRouter()

# Initialize Twilio client
twilio_client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

# In-memory chat history per call session
# Note: For production, consider using a more persistent store like Redis.
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

# System message for the AI assistant (from working answer_phone.py)
SYSTEM_MESSAGE = """
You are an AI assistant whose sole purpose is to help users book appointments over the phone.

Your responsibilities:
- Assist users with scheduling, rescheduling, or canceling appointments.
- Provide information about available time slots and appointment status.
- Collect necessary details for bookings (name, email, appointment type, date, and time).
- Speak warmly, clearly, and keep responses short and conversational.

STRICT FACTUAL RULES:
- For any information about appointments, bookings, or time slots, NEVER guess or make up data. Only refer to information provided by the system or tools.
- If you do not know the answer, politely say you are unable to provide that information right now.

IMPORTANT:
- If a user asks about anything unrelated to appointments, politely explain that you can only assist with booking, rescheduling, or canceling appointments.
- Do not engage in general conversation or provide information outside of appointment scheduling.
"""

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
    Handle incoming calls from Twilio.
    
    This endpoint is called by Twilio when a call is received.
    It greets the user and starts the conversation loop.
    
    Returns:
        HTMLResponse: TwiML XML response for Twilio
    """
    response = VoiceResponse()
    
    # Start listening for the user's response using <Gather>.
    gather = response.gather(
        input='speech',
        action='/api/voice/handle-speech',
        speech_timeout='auto',
        speech_model='experimental_conversational',
        language='en-US'
    )
    
    # Nest the greeting inside the <Gather> verb. This is the prompt.
    gather.say(
        "Hello! Welcome to your personal AI booking assistant! How may I help you today?",
        voice='Polly.Salli'
    )
    
    # If the <Gather> finishes without any speech, Twilio will proceed to the next verb.
    # This provides a graceful exit instead of an abrupt hang-up.
    response.say("We didn't receive a response. Thank you for calling. Goodbye.", voice='Polly.Salli')
    response.hangup()
    
    return HTMLResponse(content=str(response), media_type="application/xml")

@router.post("/handle-speech")
async def handle_speech(request: Request):
    """
    Process speech input from the user and respond.
    
    This is the main conversational loop for voice interactions.
    
    Args:
        request (Request): FastAPI request object containing Twilio form data
        
    Returns:
        HTMLResponse: TwiML XML response for Twilio
    """
    # Parse the form data from Twilio's request
    form = await request.form()
    call_sid = form.get("CallSid")
    user_speech = form.get("SpeechResult", "").strip()
    
    response = VoiceResponse()

    if not call_sid:
        response.say("An application error occurred. Please call back later.", voice='Polly.Salli')
        response.hangup()
        return HTMLResponse(content=str(response), media_type="application/xml")

    # Initialize session if it's a new call
    if call_sid not in call_sessions:
        call_sessions[call_sid] = {'history': []}

    # Start the next <Gather> to continue the conversation loop.
    gather = response.gather(
        input='speech',
        action='/api/voice/handle-speech',
        timeout=15,
        speech_timeout='auto',
        speech_model='experimental_conversational',
        language='en-US'
    )

    # If the user said something, process it and say the response.
    if user_speech:
        print(f"[{call_sid}] User said: {user_speech}")
        from langchain_core.messages import HumanMessage, AIMessage
        call_sessions[call_sid]['history'].append(HumanMessage(content=user_speech))

        # Use the agentic graph for response generation
        llm_response_text = run_agentic_graph(
            [*call_sessions[call_sid]['history']],
            thread_id=call_sid
        )
        print(f"[{call_sid}] AI said: {llm_response_text}")

        call_sessions[call_sid]['history'].append(AIMessage(content=llm_response_text))
        # Nest the AI's response inside the new <Gather> as its prompt.
        gather.say(llm_response_text, voice='Polly.Salli')
    else:
        # If no speech was detected from the previous <Gather>, prompt the user again.
        print(f"[{call_sid}] No speech detected.")
        # Nest the re-prompt inside the new <Gather>.
        gather.say("I'm sorry, I didn't hear anything. Could you please say that again?", voice='Polly.Salli')

    # Add a fallback in case this new <Gather> also times out.
    response.say("It seems we've been disconnected. Thank you for calling. Goodbye.", voice='Polly.Salli')
    response.hangup()

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

