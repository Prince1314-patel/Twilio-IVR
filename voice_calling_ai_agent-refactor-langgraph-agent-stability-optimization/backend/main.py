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
Last Modified: 2025-01-28
"""

import os
import time
import json
import uuid
from typing import Dict, List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from twilio.twiml.voice_response import VoiceResponse, Gather
import uvicorn

from app.apis import chat, voice, availability, appointments, metrics
from app.core.config import settings
from app.core.websocket_manager import WebSocketManager
from app.core.logger_config import setup_logging, get_application_logger, get_error_logger

# Initialize logging system
environment = os.getenv("ENVIRONMENT", "development")
setup_logging(environment=environment)

# Get loggers
logger = get_application_logger()
error_logger = get_error_logger()

# Log application startup
logger.info("Healthcare AI Assistant API starting up", extra={
    'environment': environment,
    'version': '2.0.0',
    'startup': True
}) 

# Initialize FastAPI app
app = FastAPI(
    title="Healthcare AI Assistant API",
    description="FastAPI backend for Healthcare AI Assistant with voice and chat capabilities",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")
cors_methods = os.getenv("CORS_ALLOW_METHODS", "GET,POST,PUT,DELETE,OPTIONS").split(",")
cors_headers = os.getenv("CORS_ALLOW_HEADERS", "*").split(",")
cors_credentials = os.getenv("CORS_ALLOW_CREDENTIALS", "true").lower() == "true"

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=cors_credentials,
    allow_methods=cors_methods,
    allow_headers=cors_headers,
)

# Initialize WebSocket manager
websocket_manager = WebSocketManager()

# Logging middleware for request/response tracking
@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """
    Middleware to log HTTP requests and responses with timing information.
    
    This middleware logs all incoming HTTP requests with method, path, and timing.
    It also logs response status codes and handles any errors that occur during processing.
    """
    start_time = time.time()
    request_id = f"req_{int(start_time * 1000)}_{uuid.uuid4().hex[:8]}"
    
    # Extract client information
    client_host = getattr(request.client, 'host', 'unknown') if request.client else 'unknown'
    user_agent = request.headers.get('user-agent', 'unknown')
    
    # Log incoming request
    logger.info(f"Incoming {request.method} request to {request.url.path}", extra={
        'request_id': request_id,
        'method': request.method,
        'path': str(request.url.path),
        'query_params': str(request.query_params) if request.query_params else None,
        'client_host': client_host,
        'user_agent': user_agent,
        'request_start': True
    })
    
    try:
        # Process the request
        response = await call_next(request)
        
        # Calculate processing time
        process_time = time.time() - start_time
        duration_ms = int(process_time * 1000)
        
        # Log successful response
        logger.info(f"Request completed: {request.method} {request.url.path} -> {response.status_code}", extra={
            'request_id': request_id,
            'method': request.method,
            'path': str(request.url.path),
            'status_code': response.status_code,
            'duration_ms': duration_ms,
            'request_complete': True
        })
        
        # Add timing header
        response.headers["X-Process-Time"] = str(process_time)
        response.headers["X-Request-ID"] = request_id
        
        return response
        
    except Exception as e:
        # Calculate processing time for error case
        process_time = time.time() - start_time
        duration_ms = int(process_time * 1000)
        
        # Log error
        error_logger.error(f"Request failed: {request.method} {request.url.path}", extra={
            'request_id': request_id,
            'method': request.method,
            'path': str(request.url.path),
            'duration_ms': duration_ms,
            'error_type': type(e).__name__,
            'error_message': str(e),
            'request_error': True
        }, exc_info=True)
        
        # Re-raise the exception to let FastAPI handle it
        raise

# Include routers
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(voice.router, prefix="/api/voice", tags=["voice"])
app.include_router(availability.router, prefix="/api/availability", tags=["availability"])
app.include_router(appointments.router, prefix="/api/appointments", tags=["appointments"])
app.include_router(metrics.router, prefix="/api", tags=["metrics"])

@app.get("/", response_class=HTMLResponse)
async def root():
    """
    Root endpoint that returns a simple HTML page indicating the server is running.
    
    Returns:
        HTMLResponse: Simple HTML page with server status
    """
    logger.info("Root endpoint accessed")
    
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
    logger.info("Health check endpoint accessed")
    
    return {
        "status": "healthy",
        "service": "Healthcare AI Assistant API",
        "version": "2.0.0",
        "timestamp": time.time()
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
    client_host = getattr(websocket.client, 'host', 'unknown') if websocket.client else 'unknown'
    
    # Log WebSocket connection attempt
    logger.info(f"WebSocket connection attempt from {client_host}", extra={
        'session_id': session_id,
        'client_host': client_host,
        'websocket_event': 'connection_attempt'
    })
    
    await websocket_manager.connect(websocket, session_id)
    
    # Log successful connection
    logger.info(f"WebSocket connected successfully", extra={
        'session_id': session_id,
        'client_host': client_host,
        'websocket_event': 'connected'
    })
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # Log incoming WebSocket message
            logger.info("WebSocket message received", extra={
                'session_id': session_id,
                'message_type': message_data.get('type', 'unknown'),
                'message_length': len(message_data.get('content', '')),
                'websocket_event': 'message_received'
            })
            
            # Process the message through the AI agent
            start_time = time.time()
            response = await process_chat_message(message_data, session_id)
            process_time = time.time() - start_time
            
            # Log message processing completion
            logger.info("WebSocket message processed", extra={
                'session_id': session_id,
                'processing_duration_ms': int(process_time * 1000),
                'response_length': len(response),
                'websocket_event': 'message_processed'
            })
            
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
        logger.info(f"WebSocket disconnected", extra={
            'session_id': session_id,
            'websocket_event': 'disconnected'
        })
    except Exception as e:
        # Log WebSocket error
        error_logger.error(f"WebSocket error for session {session_id}", extra={
            'session_id': session_id,
            'error_type': type(e).__name__,
            'error_message': str(e),
            'websocket_event': 'error'
        }, exc_info=True)
        
        # Disconnect on error
        websocket_manager.disconnect(websocket, session_id)

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
        from app.ai.graph.entrypoint import run_agentic_graph
        from langchain_core.messages import HumanMessage, AIMessage
        
        # Log AI processing start
        logger.info("Starting AI agent processing", extra={
            'session_id': session_id,
            'message_content_length': len(message_data.get("content", "")),
            'ai_processing': 'start'
        })
        
        # Get or create conversation history for this session
        if session_id not in websocket_manager.conversation_history:
            websocket_manager.conversation_history[session_id] = {
                "messages": []
            }
            
            logger.info("Created new conversation history", extra={
                'session_id': session_id,
                'conversation_event': 'history_created'
            })
        
        # Add user message to history
        user_message = HumanMessage(content=message_data["content"])
        websocket_manager.conversation_history[session_id]["messages"].append(user_message)
        
        # Get AI response
        start_time = time.time()
        response = run_agentic_graph(
            websocket_manager.conversation_history[session_id]["messages"],
            session_id
        )
        ai_process_time = time.time() - start_time
        
        # Log AI processing completion
        logger.info("AI agent processing completed", extra={
            'session_id': session_id,
            'ai_processing_duration_ms': int(ai_process_time * 1000),
            'response_length': len(response),
            'ai_processing': 'complete'
        })
        
        # Add AI response to history
        ai_message = AIMessage(content=response)
        websocket_manager.conversation_history[session_id]["messages"].append(ai_message)
        
        return response
        
    except Exception as e:
        error_message = f"Error processing chat message for session {session_id}: {e}"
        
        # Log AI processing error
        error_logger.error(error_message, extra={
            'session_id': session_id,
            'error_type': type(e).__name__,
            'error_message': str(e),
            'ai_processing': 'error'
        }, exc_info=True)
        
        return "I'm sorry, I encountered an error processing your request. Please try again."

# Application startup event
@app.on_event("startup")
async def startup_event():
    """
    Application startup event handler.
    
    Logs application startup and performs any necessary initialization.
    """
    logger.info("Healthcare AI Assistant API started successfully", extra={
        'environment': environment,
        'version': '2.0.0',
        'startup_complete': True,
        'host': settings.HOST,
        'port': settings.PORT
    })

# Application shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """
    Application shutdown event handler.
    
    Logs application shutdown and performs cleanup.
    """
    logger.info("Healthcare AI Assistant API shutting down", extra={
        'environment': environment,
        'version': '2.0.0',
        'shutdown': True
    })

if __name__ == "__main__":
    # Log server startup
    logger.info("Starting uvicorn server", extra={
        'host': "0.0.0.0",
        'port': 8000,
        'reload': True,
        'log_level': "info",
        'server_startup': True
    })
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )


