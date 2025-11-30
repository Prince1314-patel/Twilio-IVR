"""
Chat API Router
==============

This module provides REST API endpoints for chat functionality with the AI assistant.
It handles message processing, conversation management, and response generation.

Author: Advanced AI Systems Team
Last Modified: 2025-01-27
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
import uuid
import logging
from datetime import datetime

from app.core.config import settings
from agentic_graph.agent_graph import run_agentic_graph
from langchain_core.messages import HumanMessage, AIMessage

logger = logging.getLogger(__name__)

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
conversation_storage = {}

@router.post("/message", response_model=ChatResponse)
async def send_message(message: ChatMessage):
    """
    Send a message to the AI assistant and get a response.
    
    Args:
        message (ChatMessage): The chat message from the user
        
    Returns:
        ChatResponse: The AI assistant's response
        
    Raises:
        HTTPException: If there's an error processing the message
    """
    try:
        # Generate session ID if not provided
        session_id = message.session_id or str(uuid.uuid4())
        
        # Initialize conversation history if new session
        if session_id not in conversation_storage:
            conversation_storage[session_id] = []
        
        # Add user message to history
        user_message = HumanMessage(content=message.content)
        conversation_storage[session_id].append({
            "role": "user",
            "content": message.content,
            "timestamp": message.timestamp or datetime.now().isoformat()
        })
        
        # Get AI response using the agentic graph
        ai_response = run_agentic_graph(
            conversation_storage[session_id],
            session_id
        )
        
        # Add AI response to history
        conversation_storage[session_id].append({
            "role": "assistant",
            "content": ai_response,
            "timestamp": datetime.now().isoformat()
        })
        
        logger.info(f"Processed message for session {session_id}")
        
        return ChatResponse(
            content=ai_response,
            session_id=session_id,
            timestamp=datetime.now().isoformat(),
            message_type="ai_response"
        )
        
    except Exception as e:
        logger.error(f"Error processing chat message: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing message: {str(e)}"
        )

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
    
    messages = conversation_storage[session_id]
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
    
    conversation_storage[session_id] = []
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
    for session_id, messages in conversation_storage.items():
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
    conversation_storage[session_id] = []
    
    logger.info(f"Created new session: {session_id}")
    
    return {
        "session_id": session_id,
        "message": "New session created successfully"
    }


