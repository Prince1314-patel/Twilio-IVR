"""
WebSocket Connection Manager
============================

This module manages WebSocket connections for real-time communication
between the frontend and the AI assistant. It handles connection lifecycle,
message routing, and conversation history management.

Author: Advanced AI Systems Team
Last Modified: 2025-01-27
"""

from fastapi import WebSocket
from typing import Dict, List
import json
import logging
from langchain_core.messages import HumanMessage, AIMessage

logger = logging.getLogger(__name__)

class WebSocketManager:
    """
    Manages WebSocket connections and conversation history.
    
    This class handles the lifecycle of WebSocket connections, maintains
    conversation history for each session, and provides methods for
    sending messages to connected clients.
    """
    
    def __init__(self):
        """
        Initialize the WebSocket manager.
        
        Creates empty dictionaries for active connections and conversation history.
        """
        self.active_connections: Dict[str, WebSocket] = {}
        self.conversation_history: Dict[str, List] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str):
        """
        Accept a new WebSocket connection and register it.
        
        Args:
            websocket (WebSocket): The WebSocket connection to accept
            session_id (str): Unique session identifier
        """
        await websocket.accept()
        self.active_connections[session_id] = websocket
        self.conversation_history[session_id] = []
        logger.info(f"WebSocket connected for session: {session_id}")
    
    def disconnect(self, websocket: WebSocket, session_id: str):
        """
        Remove a WebSocket connection and clean up session data.
        
        Args:
            websocket (WebSocket): The WebSocket connection to remove
            session_id (str): Session identifier to clean up
        """
        if session_id in self.active_connections:
            del self.active_connections[session_id]
        if session_id in self.conversation_history:
            del self.conversation_history[session_id]
        logger.info(f"WebSocket disconnected for session: {session_id}")
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        """
        Send a message to a specific WebSocket connection.
        
        Args:
            message (str): Message to send (should be JSON string)
            websocket (WebSocket): Target WebSocket connection
        """
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.error(f"Error sending message: {e}")
    
    async def send_to_session(self, message: str, session_id: str):
        """
        Send a message to a specific session.
        
        Args:
            message (str): Message to send (should be JSON string)
            session_id (str): Target session identifier
        """
        if session_id in self.active_connections:
            await self.send_personal_message(
                message, 
                self.active_connections[session_id]
            )
        else:
            logger.warning(f"No active connection for session: {session_id}")
    
    async def broadcast(self, message: str):
        """
        Broadcast a message to all active connections.
        
        Args:
            message (str): Message to broadcast (should be JSON string)
        """
        for session_id, websocket in self.active_connections.items():
            try:
                await self.send_personal_message(message, websocket)
            except Exception as e:
                logger.error(f"Error broadcasting to session {session_id}: {e}")
    
    def get_conversation_history(self, session_id: str) -> List:
        """
        Get conversation history for a specific session.
        
        Args:
            session_id (str): Session identifier
            
        Returns:
            List: Conversation history for the session
        """
        return self.conversation_history.get(session_id, [])
    
    def add_to_history(self, session_id: str, message):
        """
        Add a message to the conversation history.
        
        Args:
            session_id (str): Session identifier
            message: Message object to add to history
        """
        if session_id not in self.conversation_history:
            self.conversation_history[session_id] = []
        
        self.conversation_history[session_id].append(message)
    
    def clear_history(self, session_id: str):
        """
        Clear conversation history for a specific session.
        
        Args:
            session_id (str): Session identifier to clear
        """
        if session_id in self.conversation_history:
            self.conversation_history[session_id] = []
            logger.info(f"Cleared conversation history for session: {session_id}")
    
    def get_active_sessions(self) -> List[str]:
        """
        Get list of active session IDs.
        
        Returns:
            List[str]: List of active session identifiers
        """
        return list(self.active_connections.keys())
    
    def get_connection_count(self) -> int:
        """
        Get the number of active connections.
        
        Returns:
            int: Number of active WebSocket connections
        """
        return len(self.active_connections)


