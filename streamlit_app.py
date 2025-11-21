"""
Streamlit Healthcare AI Assistant
================================

This is the main Streamlit application that provides a web interface for
the Healthcare AI Assistant. It includes chat functionality and voice calling
capabilities similar to Amazon's call functionality.

Features:
- Real-time chat interface with AI assistant
- Voice call initiation button
- Session management
- Appointment scheduling through chat
- Modern, responsive UI

Author: Advanced AI Systems Team
Last Modified: 2025-01-27
"""

import streamlit as st
import requests
import json
import uuid
from datetime import datetime
import asyncio
import websockets
import threading
import time
from typing import Dict, List, Optional
import logging

# Configure logging - only show important messages
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

# Suppress noisy loggers
logging.getLogger('watchdog.observers.inotify_buffer').setLevel(logging.WARNING)
logging.getLogger('urllib3.connectionpool').setLevel(logging.WARNING)
logging.getLogger('streamlit').setLevel(logging.WARNING)
logging.getLogger('streamlit.runtime').setLevel(logging.WARNING)
logging.getLogger('streamlit.elements').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Configure Streamlit page
st.set_page_config(
    page_title="Healthcare AI Assistant",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API Configuration
API_BASE_URL = "http://localhost:8000"
WEBSOCKET_URL = "ws://localhost:8000/ws"

class HealthcareAIAssistant:
    """
    Main application class for the Healthcare AI Assistant Streamlit app.
    
    This class manages the chat interface, WebSocket connections, and
    voice calling functionality.
    """
    
    def __init__(self):
        """Initialize the Healthcare AI Assistant."""
        self.session_id = None
        self.websocket = None
        self.is_connected = False
        
    def initialize_session(self):
        """Initialize a new chat session."""
        if 'session_id' not in st.session_state:
            st.session_state.session_id = str(uuid.uuid4())
            st.session_state.messages = []
            st.session_state.call_status = "idle"
        
        self.session_id = st.session_state.session_id
    
    def send_chat_message(self, message: str) -> str:
        """
        Send a chat message to the AI assistant.
        
        Args:
            message (str): User message to send
            
        Returns:
            str: AI assistant response
        """
        try:
            logger.info(f"Sending chat message: {message[:50]}...")
            response = requests.post(
                f"{API_BASE_URL}/api/chat/message",
                json={
                    "content": message,
                    "session_id": self.session_id,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Chat response received: {result['content'][:50]}...")
                return result["content"]
            else:
                logger.error(f"Chat API error: {response.status_code} - {response.text}")
                return f"Error: {response.status_code} - {response.text}"
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Chat connection error: {str(e)}")
            return f"Connection error: {str(e)}"
    
    def initiate_voice_call(self, phone_number: str) -> Dict:
        """
        Initiate a voice call to the specified phone number.
        
        Args:
            phone_number (str): Phone number to call
            
        Returns:
            Dict: Call initiation response
        """
        try:
            logger.info(f"Initiating voice call to: {phone_number}")
            response = requests.post(
                f"{API_BASE_URL}/api/voice/initiate-call",
                json={
                    "phone_number": phone_number,
                    "message": "Healthcare AI Assistant calling"
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Voice call initiated successfully: {result.get('call_sid', 'N/A')}")
                return result
            else:
                logger.error(f"Voice call API error: {response.status_code} - {response.text}")
                return {"error": f"Error: {response.status_code} - {response.text}"}
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Voice call connection error: {str(e)}")
            return {"error": f"Connection error: {str(e)}"}
    
    def get_call_status(self, call_sid: str) -> Dict:
        """
        Get the status of a voice call.
        
        Args:
            call_sid (str): Twilio call SID
            
        Returns:
            Dict: Call status information
        """
        try:
            response = requests.get(
                f"{API_BASE_URL}/api/voice/call-status/{call_sid}"
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"Error: {response.status_code} - {response.text}"}
                
        except requests.exceptions.RequestException as e:
            return {"error": f"Connection error: {str(e)}"}

def main():
    """Main application function."""
    
    # Initialize the assistant
    assistant = HealthcareAIAssistant()
    assistant.initialize_session()
    
    # Custom CSS for better styling
    st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .chat-container {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 1rem;
        margin: 1rem 0;
    }
    .user-message {
        background-color: #007bff;
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 18px 18px 4px 18px;
        margin: 0.5rem 0;
        margin-left: 20%;
    }
    .ai-message {
        background-color: #e9ecef;
        color: #333;
        padding: 0.5rem 1rem;
        border-radius: 18px 18px 18px 4px;
        margin: 0.5rem 0;
        margin-right: 20%;
    }
    .call-button {
        background: linear-gradient(45deg, #28a745, #20c997);
        color: white;
        border: none;
        padding: 0.75rem 1.5rem;
        border-radius: 25px;
        font-size: 1.1rem;
        font-weight: bold;
        cursor: pointer;
        transition: all 0.3s ease;
    }
    .call-button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
    .status-indicator {
        display: inline-block;
        width: 10px;
        height: 10px;
        border-radius: 50%;
        margin-right: 8px;
    }
    .status-online {
        background-color: #28a745;
    }
    .status-offline {
        background-color: #dc3545;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Header
    st.markdown('<h1 class="main-header">🏥 Healthcare AI Assistant</h1>', unsafe_allow_html=True)
    
    # Top navigation bar for call functionality
    st.markdown("---")
    
    # Call section in main area
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.markdown("### 💬 Chat with AI Assistant")
    
    with col2:
        # Phone number input in a more prominent location
        phone_number = st.text_input(
            "📱 Your Phone Number",
            placeholder="+1234567890",
            help="Enter your phone number with country code to receive a call",
            key="phone_input"
        )
    
    with col3:
        # Call button - more prominent
        if st.button("📞 Get Voice Call", key="call_button", help="Click to receive a voice call on your phone", type="primary"):
            if phone_number:
                with st.spinner("🔄 Initiating call to your phone..."):
                    call_result = assistant.initiate_voice_call(phone_number)
                    
                    if "error" in call_result:
                        st.error(f"❌ Call failed: {call_result['error']}")
                    else:
                        st.success(f"✅ Call initiated! You should receive a call shortly.")
                        st.info(f"📞 Call ID: {call_result['call_sid']}")
                        st.session_state.call_sid = call_result['call_sid']
                        st.session_state.call_status = "initiated"
                        
                        # Show call instructions
                        st.markdown("""
                        **📞 Call Instructions:**
                        - Answer your phone when it rings
                        - The AI assistant will greet you
                        - You can speak naturally about appointments
                        - Say "book an appointment" to start scheduling
                        """)
            else:
                st.warning("⚠️ Please enter your phone number first")
    
    st.markdown("---")
    
    # Sidebar for call status and additional features
    with st.sidebar:
        st.markdown("## 📞 Call Status")
        st.markdown("---")
        
        if 'call_sid' in st.session_state:
            st.success("✅ Call Active")
            st.info(f"Call ID: {st.session_state.call_sid}")
            
            if st.button("📊 Check Status", key="status_button"):
                with st.spinner("Checking call status..."):
                    status = assistant.get_call_status(st.session_state.call_sid)
                    
                    if "error" in status:
                        st.error(f"❌ Status check failed: {status['error']}")
                    else:
                        st.info(f"📞 Status: {status['status']}")
                        if status.get('duration'):
                            st.info(f"⏱️ Duration: {status['duration']} seconds")
        else:
            st.info("📞 No active call")
        
        st.markdown("---")
        st.markdown("## ℹ️ About")
        st.markdown("""
        This AI assistant helps you:
        - 📅 Schedule appointments
        - 🔍 Check availability  
        - 📝 Update appointments
        - ❌ Cancel appointments
        - 📞 Voice calling support
        """)
        
        st.markdown("---")
        st.markdown("## 🚀 Quick Actions")
        
        if st.button("🔄 New Chat Session", key="new_session"):
            st.session_state.messages = []
            st.session_state.session_id = str(uuid.uuid4())
            st.rerun()
        
        if st.button("📋 View Chat History", key="view_history"):
            if st.session_state.messages:
                st.json([{"role": msg["role"], "content": msg["content"][:100] + "..." if len(msg["content"]) > 100 else msg["content"]} for msg in st.session_state.messages])
            else:
                st.info("No chat history yet")
        
        st.markdown("---")
        st.markdown("## 🔧 Debug Info")
        
        # Show important debug information
        if st.button("🔍 Show Debug Info", key="debug_info"):
            debug_info = {
                "Session ID": assistant.session_id,
                "API Base URL": API_BASE_URL,
                "Messages Count": len(st.session_state.messages),
                "Call Status": st.session_state.get('call_status', 'idle'),
                "Call SID": st.session_state.get('call_sid', 'None')
            }
            st.json(debug_info)
    
    # Display chat messages
    if st.session_state.messages:
        for message in st.session_state.messages:
            if message["role"] == "user":
                st.markdown(f'<div class="user-message">👤 You: {message["content"]}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="ai-message">🤖 Assistant: {message["content"]}</div>', unsafe_allow_html=True)
    
    # Chat input
    user_input = st.chat_input("Type your message here...")
    
    if user_input:
        # Add user message to session
        st.session_state.messages.append({
            "role": "user",
            "content": user_input,
            "timestamp": datetime.now().isoformat()
        })
        
        # Get AI response
        with st.spinner("AI is thinking..."):
            ai_response = assistant.send_chat_message(user_input)
        
        # Add AI response to session
        st.session_state.messages.append({
            "role": "assistant",
            "content": ai_response,
            "timestamp": datetime.now().isoformat()
        })
        
        # Rerun to display new messages
        st.rerun()
    
    # Footer
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown(
            '<p style="text-align: center; color: #666;">Healthcare AI Assistant v2.0 | Powered by FastAPI & Streamlit</p>',
            unsafe_allow_html=True
        )

if __name__ == "__main__":
    main()


