"""
FastAPI Main Application
=======================

This is the main FastAPI application that serves as the backend for the
Healthcare AI Assistant. It provides REST API endpoints for chat functionality
and WebSocket support for real-time communication.

Features:
- Chat API endpoints
- WebSocket support for real-time communication
- Twilio voice integration
- Appointment scheduling functionality

Author: Advanced AI Systems Team
Last Modified: 2025-01-27
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from twilio.twiml.voice_response import VoiceResponse, Gather
import uvicorn
import json
import uuid
from typing import Dict, List
import logging

from app.routers import chat, voice, voice_stream
from app.core.config import settings
from app.core.websocket_manager import WebSocketManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Healthcare AI Assistant API",
    description="FastAPI backend for Healthcare AI Assistant with voice and chat capabilities",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize WebSocket manager
websocket_manager = WebSocketManager()

# Include routers
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(voice.router, prefix="/api/voice", tags=["voice"])
app.include_router(voice_stream.router, prefix="/api/voice", tags=["voice-stream"])

@app.get("/", response_class=HTMLResponse)
async def root():
    """
    Root endpoint that returns a simple HTML page indicating the server is running.
    
    Returns:
        HTMLResponse: Simple HTML page with server status
    """
    return HTMLResponse("""
    <html>
        <head>
            <title>Healthcare AI Assistant API</title>
        </head>
        <body>
            <h1>🏥 Healthcare AI Assistant API</h1>
            <p>Server is running successfully!</p>
            <p><a href="/docs">API Documentation</a></p>
        </body>
    </html>
    """)

@app.get("/health")
async def health_check():
    """
    Health check endpoint for monitoring and load balancers.
    
    Returns:
        dict: Server health status
    """
    return {
        "status": "healthy",
        "service": "Healthcare AI Assistant API",
        "version": "2.0.0"
    }

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time communication with the AI assistant.
    
    Args:
        websocket (WebSocket): WebSocket connection
        session_id (str): Unique session identifier
        
    This endpoint handles real-time chat communication and maintains
    conversation history for each session.
    """
    await websocket_manager.connect(websocket, session_id)
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # Process the message through the AI agent
            response = await process_chat_message(message_data, session_id)
            
            # Send response back to client
            await websocket_manager.send_personal_message(
                json.dumps({
                    "type": "ai_response",
                    "content": response,
                    "timestamp": message_data.get("timestamp")
                }), 
                websocket
            )
            
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket, session_id)
        logger.info(f"WebSocket disconnected for session: {session_id}")

async def process_chat_message(message_data: dict, session_id: str) -> str:
    """
    Process chat message through the AI agent.
    
    Args:
        message_data (dict): Message data from client
        session_id (str): Session identifier
        
    Returns:
        str: AI agent response
    """
    try:
        from agentic_graph.agent_graph import run_agentic_graph
        from langchain_core.messages import HumanMessage, AIMessage
        
        # Get or create conversation history for this session
        if session_id not in websocket_manager.conversation_history:
            websocket_manager.conversation_history[session_id] = []
        
        # Add user message to history
        user_message = HumanMessage(content=message_data["content"])
        websocket_manager.conversation_history[session_id].append(user_message)
        
        # Get AI response
        response = run_agentic_graph(
            websocket_manager.conversation_history[session_id],
            session_id
        )
        
        # Add AI response to history
        ai_message = AIMessage(content=response)
        websocket_manager.conversation_history[session_id].append(ai_message)
        
        return response
        
    except Exception as e:
        logger.error(f"Error processing chat message: {e}")
        return "I'm sorry, I encountered an error processing your request. Please try again."

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )


