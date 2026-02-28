"""
Chat API Router
==============

This module provides REST API endpoints for chat functionality with the AI assistant.
It handles message processing, conversation management, and response generation.

Author: Advanced AI Systems Team
Last Modified: 2025-01-28
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
import uuid
import json
from datetime import datetime

from sqlalchemy.orm import Session
from app.database.session import get_db
from app.core.config import settings
from app.ai.graph.entrypoint import run_agentic_graph, run_agentic_graph_stream
from langchain_core.messages import HumanMessage, AIMessage
from app.core.logger_config import get_application_logger, get_error_logger

logger = get_application_logger()
error_logger = get_error_logger()

# Create router instance
router = APIRouter()

class ChatMessage(BaseModel):
    """
    Pydantic model for chat message requests.
    
    Attributes:
        content (str): The message content from the user
        session_id (Optional[str]): Session identifier for conversation continuity
        timestamp (Optional[str]): Message timestamp
    """
    content: str
    session_id: Optional[str] = None
    timestamp: Optional[str] = None

class ChatResponse(BaseModel):
    """
    Pydantic model for chat message responses.
    
    Attributes:
        content (str): The AI assistant's response
        session_id (str): Session identifier
        timestamp (str): Response timestamp
        message_type (str): Type of message (ai_response, error, etc.)
    """
    content: str
    session_id: str
    timestamp: str
    message_type: str = "ai_response"

class ConversationHistory(BaseModel):
    """
    Pydantic model for conversation history.
    
    Attributes:
        session_id (str): Session identifier
        messages (List[dict]): List of conversation messages
        total_messages (int): Total number of messages in conversation
    """
    session_id: str
    messages: List[dict]
    total_messages: int

# In-memory storage for conversation history
# In production, consider using Redis or a database
# Format: {session_id: {"messages": [messages]}}
conversation_storage = {}

@router.post("/message")
async def send_message(message: ChatMessage, db: Session = Depends(get_db)):
    """
    Send a message to the AI assistant and get streaming response.
    
    Returns tokens in real-time as NDJSON (newline-delimited JSON).
    Each line contains: {"token": "word "}
    
    Args:
        message (ChatMessage): The chat message from the user
        db (Session): Database session
        
    Returns:
        StreamingResponse: Token stream in NDJSON format
    """
    from fastapi.responses import StreamingResponse
    
    try:
        from app.core.identity import IdentityService
        
        base_session_id = message.session_id or str(uuid.uuid4())
        
        if base_session_id not in conversation_storage:
            conversation_storage[base_session_id] = {
                "messages": [],
                "auth_state": {
                    "authenticated": False,
                    "phone_number": None,
                    "user_details": None
                }
            }
        
        session_data = conversation_storage[base_session_id]
        
        current_user_id = session_data.get("auth_state", {}).get("user_details", {}).get("id")
        if session_data.get("auth_state", {}).get("authenticated") and current_user_id:
            stored_user_id = session_data.get("_last_user_id")
            if stored_user_id and stored_user_id != current_user_id:
                logger.warning(
                    f"[SECURITY] User switch detected in session {base_session_id}: "
                    f"user {stored_user_id} → {current_user_id}. Clearing conversation history."
                )
                conversation_storage[base_session_id]["messages"] = []
            
            conversation_storage[base_session_id]["_last_user_id"] = current_user_id
        
        conversation_storage[base_session_id]["messages"].append({
            "role": "user",
            "content": message.content,
            "timestamp": message.timestamp or datetime.now().isoformat()
        })
        
        user_context = {}
        thread_id = base_session_id
        
        if session_data.get("auth_state", {}).get("authenticated"):
            user_id = session_data["auth_state"]["user_details"]["id"]
            user_context = {
                "caller_mobile_number": session_data["auth_state"]["phone_number"],
                "user_id": user_id,
                "user_profile": session_data["auth_state"]["user_details"],
                "user_context_loaded": True
            }
            thread_id = f"{base_session_id}_user_{user_id}"
        
        # Generator function for streaming
        async def generate():
            full_response = ""
            token_count = 0
            try:
                logger.info(f"[API STREAM] Starting to stream tokens for session={base_session_id}")
                for token in run_agentic_graph_stream(
                    conversation_storage[base_session_id]["messages"],
                    thread_id,
                    user_context=user_context
                ):
                    token_count += 1
                    full_response += token
                    # Yield token as NDJSON
                    yield f'{{"token": {json.dumps(token)}}}\n'
                    logger.info(f"[TOKEN {token_count}] {token!r}")
                
                # Store full response in conversation
                conversation_storage[base_session_id]["messages"].append({
                    "role": "assistant",
                    "content": full_response,
                    "timestamp": datetime.now().isoformat()
                })
                
                logger.info(f"[API STREAM COMPLETE] session={base_session_id}, tokens_sent={token_count}")
                logger.info(f"AI response: {full_response[:200]}{'...' if len(full_response) > 200 else ''}")
                
            except Exception as e:
                logger.error(f"Error in streaming: {e}")
                yield f'{{"error": {json.dumps(str(e))}}}\n'
        
        return StreamingResponse(generate(), media_type="application/x-ndjson")
        
    except Exception as e:
        logger.error(f"Error in send_message: {e}")
        raise HTTPException(status_code=500, detail=str(e))
        

class IdentifyRequest(BaseModel):
    phone_number: str
    session_id: str

@router.post("/identify")
async def identify_user(request: IdentifyRequest, db: Session = Depends(get_db)):
    """
    Identify user by phone number and associate with session.
    """
    try:
        from app.core.identity import IdentityService
        
        # Clean number
        potential_number = request.phone_number.strip()
        clean_number = "".join(c for c in potential_number if c.isdigit() or c == '+')
        
        if not clean_number or len(clean_number) < 10:
            raise HTTPException(status_code=400, detail="Invalid phone number: must be at least 10 digits")

        user = IdentityService.get_or_create_user(db, clean_number)
        if not user:
             raise HTTPException(status_code=400, detail="Could not verify or create user")

        # Initialize session if needed
        if request.session_id not in conversation_storage:
            conversation_storage[request.session_id] = {
                "messages": []
            }
            
        # Update auth state
        conversation_storage[request.session_id]["auth_state"] = {
            "authenticated": True,
            "phone_number": user.mobile_number,
            "user_details": {
                "id": user.id,
                "full_name": user.full_name,
                "mobile_number": user.mobile_number
            }
        }
        
        return {
            "message": "User identified successfully",
            "user": {
                "id": user.id,
                "full_name": user.full_name,
                "mobile_number": user.mobile_number
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error identifying user: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{session_id}", response_model=ConversationHistory)
async def get_conversation_history(session_id: str):
    """
    Get conversation history for a specific session.
    
    Args:
        session_id (str): Session identifier
        
    Returns:
        ConversationHistory: Conversation history for the session
        
    Raises:
        HTTPException: If session not found
    """
    if session_id not in conversation_storage:
        raise HTTPException(
            status_code=404,
            detail=f"Session {session_id} not found"
        )
    
    messages = conversation_storage[session_id].get("messages", [])
    return ConversationHistory(
        session_id=session_id,
        messages=messages,
        total_messages=len(messages)
    )

@router.delete("/history/{session_id}")
async def clear_conversation_history(session_id: str):
    """
    Clear conversation history for a specific session.
    
    Args:
        session_id (str): Session identifier to clear
        
    Returns:
        dict: Success message
        
    Raises:
        HTTPException: If session not found
    """
    if session_id not in conversation_storage:
        raise HTTPException(
            status_code=404,
            detail=f"Session {session_id} not found"
        )
    
    conversation_storage[session_id] = {
        "messages": []
    }
    logger.info(f"Cleared conversation history for session: {session_id}")
    
    return {"message": f"Conversation history cleared for session {session_id}"}

@router.get("/sessions")
async def get_active_sessions():
    """
    Get list of active conversation sessions.
    
    Returns:
        dict: List of active session IDs and their message counts
    """
    sessions = []
    for session_id, session_data in conversation_storage.items():
        messages = session_data.get("messages", [])
        sessions.append({
            "session_id": session_id,
            "message_count": len(messages),
            "last_activity": messages[-1]["timestamp"] if messages else None
        })
    
    return {
        "active_sessions": len(sessions),
        "sessions": sessions
    }

@router.post("/new-session")
async def create_new_session():
    """
    Create a new conversation session.
    
    Returns:
        dict: New session information
    """
    session_id = str(uuid.uuid4())
    conversation_storage[session_id] = {
        "messages": []
    }
    
    logger.info(f"Created new session: {session_id}")
    
    return {
        "session_id": session_id,
        "message": "New session created successfully"
    }

class UserLookupRequest(BaseModel):
    """
    Pydantic model for user lookup request.
    
    Attributes:
        phone_number (str): The phone number to look up.
    """
    phone_number: str

@router.post("/user-lookup")
async def lookup_user(request: UserLookupRequest, db: Session = Depends(get_db)):
    """
    Look up a user by their phone number.
    
    Args:
        request (UserLookupRequest): The lookup request containing the phone number.
        db (Session): Database session.
        
    Returns:
        dict: User details if found.
        
    Raises:
        HTTPException: If user is not found.
    """
    try:
        from app.core.identity import IdentityService
        
        user = IdentityService.resolve_user(db, request.phone_number)
        
        if not user:
            raise HTTPException(
                status_code=404,
                detail=f"User with number {request.phone_number} not found"
            )
            
        return {
            "id": user.id,
            "full_name": user.full_name,
            "mobile_number": user.mobile_number,
            "created_at": user.created_at.isoformat() if user.created_at else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error looking up user: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error performing user lookup: {str(e)}"
        )