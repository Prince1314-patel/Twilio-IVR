"""
WebSocket Connection Manager
============================

This module manages WebSocket connections for real-time communication
between the frontend and the AI assistant. It handles connection lifecycle,
message routing, and conversation history management with comprehensive logging.

Author: Advanced AI Systems Team
Last Modified: 2025-01-28
"""

from fastapi import WebSocket
from typing import Dict, List
import json
import time
import uuid
from langchain_core.messages import HumanMessage, AIMessage
from app.core.logger_config import get_application_logger, get_error_logger

logger = get_application_logger()
error_logger = get_error_logger()

class WebSocketManager:
    """
    Manages WebSocket connections and conversation history with comprehensive logging.
    
    This class handles the lifecycle of WebSocket connections, maintains
    conversation history for each session, provides methods for sending messages
    to connected clients, and logs all WebSocket events with performance metrics.
    """
    
    def __init__(self):
        """
        Initialize the WebSocket manager.
        
        Creates empty dictionaries for active connections, conversation history,
        and session metrics tracking.
        """
        self.active_connections: Dict[str, WebSocket] = {}
        self.conversation_history: Dict[str, dict] = {}
        self.session_metrics: Dict[str, dict] = {}  # Track session performance metrics
        
        logger.info("WebSocket Manager initialized", extra={
            'websocket_event': 'manager_initialized',
            'component': 'websocket_manager'
        })
    
    async def connect(self, websocket: WebSocket, session_id: str):
        """
        Accept a new WebSocket connection and register it with comprehensive logging.
        
        Args:
            websocket (WebSocket): The WebSocket connection to accept
            session_id (str): Unique session identifier
        """
        connection_start_time = time.time()
        client_host = getattr(websocket.client, 'host', 'unknown') if websocket.client else 'unknown'
        
        # Log connection attempt
        logger.info("WebSocket connection attempt", extra={
            'session_id': session_id,
            'client_host': client_host,
            'websocket_event': 'connection_attempt',
            'component': 'websocket_manager'
        })
        
        try:
            await websocket.accept()
            connection_time = time.time() - connection_start_time
            
            # Register connection
            self.active_connections[session_id] = websocket
            self.conversation_history[session_id] = {
                "messages": []
            }
            
            # Initialize session metrics
            self.session_metrics[session_id] = {
                'connection_time': time.time(),
                'connection_duration_ms': int(connection_time * 1000),
                'messages_sent': 0,
                'messages_received': 0,
                'total_message_processing_time_ms': 0,
                'client_host': client_host,
                'last_activity_time': time.time()
            }
            
            # Log successful connection with metrics
            logger.info("WebSocket connected successfully", extra={
                'session_id': session_id,
                'client_host': client_host,
                'connection_duration_ms': int(connection_time * 1000),
                'total_active_connections': len(self.active_connections),
                'websocket_event': 'connected',
                'component': 'websocket_manager'
            })
            
        except Exception as e:
            connection_time = time.time() - connection_start_time
            error_logger.error("WebSocket connection failed", extra={
                'session_id': session_id,
                'client_host': client_host,
                'connection_duration_ms': int(connection_time * 1000),
                'error_type': type(e).__name__,
                'error_message': str(e),
                'websocket_event': 'connection_failed',
                'component': 'websocket_manager'
            }, exc_info=True)
            raise
    
    def disconnect(self, websocket: WebSocket, session_id: str):
        """
        Remove a WebSocket connection and clean up session data with comprehensive logging.
        
        Args:
            websocket (WebSocket): The WebSocket connection to remove
            session_id (str): Session identifier to clean up
        """
        disconnect_start_time = time.time()
        
        # Get session metrics before cleanup
        session_metrics = self.session_metrics.get(session_id, {})
        connection_time = session_metrics.get('connection_time', disconnect_start_time)
        session_duration_ms = int((disconnect_start_time - connection_time) * 1000)
        
        # Clean up connection and history
        if session_id in self.active_connections:
            del self.active_connections[session_id]
        if session_id in self.conversation_history:
            del self.conversation_history[session_id]
        
        # Log disconnection with session metrics
        logger.info("WebSocket disconnected", extra={
            'session_id': session_id,
            'session_duration_ms': session_duration_ms,
            'messages_sent': session_metrics.get('messages_sent', 0),
            'messages_received': session_metrics.get('messages_received', 0),
            'total_message_processing_time_ms': session_metrics.get('total_message_processing_time_ms', 0),
            'client_host': session_metrics.get('client_host', 'unknown'),
            'remaining_active_connections': len(self.active_connections),
            'websocket_event': 'disconnected',
            'component': 'websocket_manager'
        })
        
        # Clean up metrics
        if session_id in self.session_metrics:
            del self.session_metrics[session_id]
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        """
        Send a message to a specific WebSocket connection with performance logging.
        
        Args:
            message (str): Message to send (should be JSON string)
            websocket (WebSocket): Target WebSocket connection
        """
        send_start_time = time.time()
        message_size = len(message.encode('utf-8'))
        
        try:
            await websocket.send_text(message)
            send_duration_ms = int((time.time() - send_start_time) * 1000)
            
            # Log successful message send
            logger.debug("WebSocket message sent", extra={
                'message_size_bytes': message_size,
                'send_duration_ms': send_duration_ms,
                'websocket_event': 'message_sent',
                'component': 'websocket_manager'
            })
            
        except Exception as e:
            send_duration_ms = int((time.time() - send_start_time) * 1000)
            error_logger.error("Error sending WebSocket message", extra={
                'message_size_bytes': message_size,
                'send_duration_ms': send_duration_ms,
                'error_type': type(e).__name__,
                'error_message': str(e),
                'websocket_event': 'message_send_failed',
                'component': 'websocket_manager'
            }, exc_info=True)
            raise
    
    async def send_to_session(self, message: str, session_id: str):
        """
        Send a message to a specific session with session tracking.
        
        Args:
            message (str): Message to send (should be JSON string)
            session_id (str): Target session identifier
        """
        send_start_time = time.time()
        
        if session_id in self.active_connections:
            try:
                await self.send_personal_message(
                    message, 
                    self.active_connections[session_id]
                )
                
                # Update session metrics
                if session_id in self.session_metrics:
                    self.session_metrics[session_id]['messages_sent'] += 1
                    self.session_metrics[session_id]['last_activity_time'] = time.time()
                
                send_duration_ms = int((time.time() - send_start_time) * 1000)
                
                logger.debug("Message sent to session", extra={
                    'session_id': session_id,
                    'message_size_bytes': len(message.encode('utf-8')),
                    'send_duration_ms': send_duration_ms,
                    'websocket_event': 'session_message_sent',
                    'component': 'websocket_manager'
                })
                
            except Exception as e:
                send_duration_ms = int((time.time() - send_start_time) * 1000)
                error_logger.error("Failed to send message to session", extra={
                    'session_id': session_id,
                    'send_duration_ms': send_duration_ms,
                    'error_type': type(e).__name__,
                    'error_message': str(e),
                    'websocket_event': 'session_message_failed',
                    'component': 'websocket_manager'
                }, exc_info=True)
                raise
        else:
            logger.warning("No active connection for session", extra={
                'session_id': session_id,
                'active_sessions': list(self.active_connections.keys()),
                'websocket_event': 'session_not_found',
                'component': 'websocket_manager'
            })
    
    async def broadcast(self, message: str):
        """
        Broadcast a message to all active connections with performance metrics.
        
        Args:
            message (str): Message to broadcast (should be JSON string)
        """
        broadcast_start_time = time.time()
        total_connections = len(self.active_connections)
        successful_sends = 0
        failed_sends = 0
        
        logger.info("Broadcasting message to all connections", extra={
            'total_connections': total_connections,
            'message_size_bytes': len(message.encode('utf-8')),
            'websocket_event': 'broadcast_start',
            'component': 'websocket_manager'
        })
        
        for session_id, websocket in self.active_connections.items():
            try:
                await self.send_personal_message(message, websocket)
                successful_sends += 1
                
                # Update session metrics
                if session_id in self.session_metrics:
                    self.session_metrics[session_id]['messages_sent'] += 1
                    self.session_metrics[session_id]['last_activity_time'] = time.time()
                    
            except Exception as e:
                failed_sends += 1
                error_logger.error("Error broadcasting to session", extra={
                    'session_id': session_id,
                    'error_type': type(e).__name__,
                    'error_message': str(e),
                    'websocket_event': 'broadcast_session_failed',
                    'component': 'websocket_manager'
                }, exc_info=True)
        
        broadcast_duration_ms = int((time.time() - broadcast_start_time) * 1000)
        
        logger.info("Broadcast completed", extra={
            'total_connections': total_connections,
            'successful_sends': successful_sends,
            'failed_sends': failed_sends,
            'broadcast_duration_ms': broadcast_duration_ms,
            'websocket_event': 'broadcast_complete',
            'component': 'websocket_manager'
        })
    
    def get_conversation_history(self, session_id: str) -> List:
        """
        Get conversation history for a specific session with access logging.
        
        Args:
            session_id (str): Session identifier
            
        Returns:
            List: Conversation history for the session
        """
        session_data = self.conversation_history.get(session_id, {"messages": []})
        history = session_data.get("messages", [])
        
        logger.debug("Conversation history accessed", extra={
            'session_id': session_id,
            'history_length': len(history),
            'websocket_event': 'history_accessed',
            'component': 'websocket_manager'
        })
        
        return history
    
    def add_to_history(self, session_id: str, message):
        """
        Add a message to the conversation history with logging.
        
        Args:
            session_id (str): Session identifier
            message: Message object to add to history
        """
        if session_id not in self.conversation_history:
            self.conversation_history[session_id] = {
                "messages": []
            }
            
            logger.debug("Created new conversation history", extra={
                'session_id': session_id,
                'websocket_event': 'history_created',
                'component': 'websocket_manager'
            })
        
        self.conversation_history[session_id]["messages"].append(message)
        
        # Update session metrics
        if session_id in self.session_metrics:
            self.session_metrics[session_id]['messages_received'] += 1
            self.session_metrics[session_id]['last_activity_time'] = time.time()
        
        logger.debug("Message added to history", extra={
            'session_id': session_id,
            'history_length': len(self.conversation_history[session_id]["messages"]),
            'message_type': type(message).__name__,
            'websocket_event': 'message_added_to_history',
            'component': 'websocket_manager'
        })
    
    def clear_history(self, session_id: str):
        """
        Clear conversation history for a specific session with logging.
        
        Args:
            session_id (str): Session identifier to clear
        """
        if session_id in self.conversation_history:
            old_length = len(self.conversation_history[session_id]["messages"])
            self.conversation_history[session_id] = {
                "messages": []
            }
            
            logger.info("Conversation history cleared", extra={
                'session_id': session_id,
                'previous_history_length': old_length,
                'websocket_event': 'history_cleared',
                'component': 'websocket_manager'
            })
    
    def get_active_sessions(self) -> List[str]:
        """
        Get list of active session IDs with metrics logging.
        
        Returns:
            List[str]: List of active session identifiers
        """
        active_sessions = list(self.active_connections.keys())
        
        logger.debug("Active sessions requested", extra={
            'active_session_count': len(active_sessions),
            'websocket_event': 'active_sessions_requested',
            'component': 'websocket_manager'
        })
        
        return active_sessions
    
    def get_connection_count(self) -> int:
        """
        Get the number of active connections with logging.
        
        Returns:
            int: Number of active WebSocket connections
        """
        count = len(self.active_connections)
        
        logger.debug("Connection count requested", extra={
            'active_connection_count': count,
            'websocket_event': 'connection_count_requested',
            'component': 'websocket_manager'
        })
        
        return count
    
    def get_session_metrics(self, session_id: str) -> dict:
        """
        Get performance metrics for a specific session.
        
        Args:
            session_id (str): Session identifier
            
        Returns:
            dict: Session performance metrics
        """
        metrics = self.session_metrics.get(session_id, {})
        
        if metrics:
            # Calculate current session duration
            current_time = time.time()
            connection_time = metrics.get('connection_time', current_time)
            metrics['current_session_duration_ms'] = int((current_time - connection_time) * 1000)
            
            # Calculate time since last activity
            last_activity = metrics.get('last_activity_time', current_time)
            metrics['time_since_last_activity_ms'] = int((current_time - last_activity) * 1000)
        
        logger.debug("Session metrics requested", extra={
            'session_id': session_id,
            'metrics_available': bool(metrics),
            'websocket_event': 'session_metrics_requested',
            'component': 'websocket_manager'
        })
        
        return metrics
    
    def get_all_session_metrics(self) -> dict:
        """
        Get performance metrics for all active sessions.
        
        Returns:
            dict: All session performance metrics
        """
        all_metrics = {}
        current_time = time.time()
        
        for session_id, metrics in self.session_metrics.items():
            session_metrics = metrics.copy()
            
            # Calculate current session duration
            connection_time = metrics.get('connection_time', current_time)
            session_metrics['current_session_duration_ms'] = int((current_time - connection_time) * 1000)
            
            # Calculate time since last activity
            last_activity = metrics.get('last_activity_time', current_time)
            session_metrics['time_since_last_activity_ms'] = int((current_time - last_activity) * 1000)
            
            all_metrics[session_id] = session_metrics
        
        logger.debug("All session metrics requested", extra={
            'total_sessions_with_metrics': len(all_metrics),
            'websocket_event': 'all_session_metrics_requested',
            'component': 'websocket_manager'
        })
        
        return all_metrics


