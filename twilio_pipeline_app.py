"""
Twilio Pipeline Streamlit App
==============================

A comprehensive Streamlit application for managing and monitoring the Twilio voice pipeline.
This app provides a complete interface for initiating calls, monitoring call status,
tracking active streams, and visualizing call data.

Features:
- Call initiation with phone number validation
- Real-time call status monitoring
- Active calls and streams dashboard
- Call history and logs
- Auto-refresh for live updates
- Visual indicators and metrics

Author: Advanced AI Systems Team
Last Modified: 2025-01-27
"""

import streamlit as st
import requests
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import time
import logging
from collections import deque

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configure Streamlit page
st.set_page_config(
    page_title="Twilio Pipeline Dashboard",
    page_icon="📞",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API Configuration
try:
    API_BASE_URL = st.secrets.get("API_BASE_URL", "http://localhost:8000")
except (AttributeError, FileNotFoundError, Exception):
    # Fallback to default if secrets not available
    API_BASE_URL = "http://localhost:8000"

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
    }
    .metric-card {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #007bff;
        margin: 0.5rem 0;
    }
    .status-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 12px;
        font-size: 0.875rem;
        font-weight: 500;
    }
    .status-initiated {
        background-color: #d1ecf1;
        color: #0c5460;
    }
    .status-ringing {
        background-color: #fff3cd;
        color: #856404;
    }
    .status-in-progress {
        background-color: #d4edda;
        color: #155724;
    }
    .status-completed {
        background-color: #e2e3e5;
        color: #383d41;
    }
    .status-failed {
        background-color: #f8d7da;
        color: #721c24;
    }
    .call-card {
        background-color: white;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #dee2e6;
        margin: 0.5rem 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .pipeline-step {
        display: flex;
        align-items: center;
        padding: 0.5rem;
        margin: 0.25rem 0;
        border-radius: 4px;
    }
    .step-active {
        background-color: #d4edda;
        color: #155724;
    }
    .step-inactive {
        background-color: #e9ecef;
        color: #6c757d;
    }
</style>
""", unsafe_allow_html=True)


class TwilioPipelineManager:
    """
    Manager class for Twilio pipeline operations.
    
    This class handles all interactions with the Twilio API endpoints including
    call initiation, status checking, and monitoring.
    """
    
    def __init__(self, api_base_url: str):
        """
        Initialize the Twilio Pipeline Manager.
        
        Args:
            api_base_url (str): Base URL for the FastAPI backend
        """
        self.api_base_url = api_base_url
        self.session_id = None
        
    def initiate_call(self, phone_number: str, message: Optional[str] = None) -> Dict:
        """
        Initiate a voice call to the specified phone number.
        
        Args:
            phone_number (str): Phone number to call (must include country code)
            message (Optional[str]): Optional message for the call
            
        Returns:
            Dict: Call initiation response with call_sid and status
        """
        try:
            logger.info(f"Initiating call to: {phone_number}")
            response = requests.post(
                f"{self.api_base_url}/api/voice/initiate-call",
                json={
                    "phone_number": phone_number,
                    "message": message or "Healthcare AI Assistant calling"
                },
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Call initiated: {result.get('call_sid', 'N/A')}")
                return {"success": True, **result}
            else:
                error_msg = f"API Error {response.status_code}: {response.text}"
                logger.error(error_msg)
                return {"success": False, "error": error_msg}
                
        except requests.exceptions.RequestException as e:
            error_msg = f"Connection error: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    def get_call_status(self, call_sid: str) -> Dict:
        """
        Get the status of a specific call.
        
        Args:
            call_sid (str): Twilio call SID
            
        Returns:
            Dict: Call status information
        """
        try:
            response = requests.get(
                f"{self.api_base_url}/api/voice/call-status/{call_sid}",
                timeout=5
            )
            
            if response.status_code == 200:
                return {"success": True, **response.json()}
            else:
                return {"success": False, "error": f"Status {response.status_code}: {response.text}"}
                
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": f"Connection error: {str(e)}"}
    
    def get_active_calls(self) -> Dict:
        """
        Get list of active call sessions.
        
        Returns:
            Dict: Active calls information
        """
        try:
            response = requests.get(
                f"{self.api_base_url}/api/voice/active-calls",
                timeout=5
            )
            
            if response.status_code == 200:
                return {"success": True, **response.json()}
            else:
                return {"success": False, "error": f"Status {response.status_code}: {response.text}"}
                
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": f"Connection error: {str(e)}"}
    
    def get_active_streams(self) -> Dict:
        """
        Get list of active streaming sessions.
        
        Returns:
            Dict: Active streams information
        """
        try:
            response = requests.get(
                f"{self.api_base_url}/api/voice/active-streams",
                timeout=5
            )
            
            if response.status_code == 200:
                return {"success": True, **response.json()}
            else:
                return {"success": False, "error": f"Status {response.status_code}: {response.text}"}
                
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": f"Connection error: {str(e)}"}


def initialize_session_state():
    """Initialize session state variables."""
    if 'call_history' not in st.session_state:
        st.session_state.call_history = deque(maxlen=100)  # Keep last 100 calls
    
    if 'auto_refresh' not in st.session_state:
        st.session_state.auto_refresh = False
    
    if 'refresh_interval' not in st.session_state:
        st.session_state.refresh_interval = 5  # seconds
    
    if 'monitored_calls' not in st.session_state:
        st.session_state.monitored_calls = {}  # {call_sid: last_status}


def validate_phone_number(phone_number: str) -> tuple[bool, str]:
    """
    Validate phone number format.
    
    Args:
        phone_number (str): Phone number to validate
        
    Returns:
        tuple: (is_valid, error_message)
    """
    if not phone_number:
        return False, "Phone number cannot be empty"
    
    # Remove spaces and dashes
    cleaned = phone_number.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    
    # Check if starts with +
    if not cleaned.startswith("+"):
        return False, "Phone number must include country code (e.g., +1234567890)"
    
    # Check if contains only digits after +
    if not cleaned[1:].isdigit():
        return False, "Phone number must contain only digits after country code"
    
    # Check minimum length (country code + at least 7 digits)
    if len(cleaned) < 8:
        return False, "Phone number is too short"
    
    # Check maximum length (country code + 15 digits max)
    if len(cleaned) > 16:
        return False, "Phone number is too long"
    
    return True, ""


def format_call_status(status: str) -> str:
    """
    Format call status for display.
    
    Args:
        status (str): Raw call status
        
    Returns:
        str: Formatted status with emoji
    """
    status_map = {
        "initiated": "🔄 Initiated",
        "ringing": "📞 Ringing",
        "in-progress": "✅ In Progress",
        "completed": "✓ Completed",
        "busy": "📵 Busy",
        "failed": "❌ Failed",
        "no-answer": "📴 No Answer",
        "canceled": "🚫 Canceled"
    }
    return status_map.get(status.lower(), f"❓ {status}")


def get_status_badge_class(status: str) -> str:
    """
    Get CSS class for status badge.
    
    Args:
        status (str): Call status
        
    Returns:
        str: CSS class name
    """
    status_lower = status.lower()
    if status_lower in ["initiated"]:
        return "status-initiated"
    elif status_lower in ["ringing"]:
        return "status-ringing"
    elif status_lower in ["in-progress", "in_progress"]:
        return "status-in-progress"
    elif status_lower in ["completed"]:
        return "status-completed"
    elif status_lower in ["failed", "busy", "no-answer", "canceled"]:
        return "status-failed"
    else:
        return "status-initiated"


def display_call_card(call_data: Dict, manager: TwilioPipelineManager):
    """
    Display a call card with status and actions.
    
    Args:
        call_data (Dict): Call data dictionary
        manager (TwilioPipelineManager): Pipeline manager instance
    """
    call_sid = call_data.get("call_sid", "Unknown")
    status = call_data.get("status", "unknown")
    phone_number = call_data.get("to", call_data.get("phone_number", "Unknown"))
    
    st.markdown(f"""
    <div class="call-card">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <strong>📞 {phone_number}</strong><br>
                <small>Call SID: {call_sid[:20]}...</small>
            </div>
            <span class="status-badge {get_status_badge_class(status)}">
                {format_call_status(status)}
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Action buttons
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("🔄 Refresh Status", key=f"refresh_{call_sid}"):
            with st.spinner("Checking status..."):
                status_result = manager.get_call_status(call_sid)
                if status_result.get("success"):
                    st.session_state.monitored_calls[call_sid] = status_result
                    st.rerun()
                else:
                    st.error(f"Error: {status_result.get('error', 'Unknown error')}")
    
    with col2:
        if st.button("📊 View Details", key=f"details_{call_sid}"):
            with st.expander(f"Call Details: {call_sid}"):
                st.json(call_data)


def display_pipeline_steps(call_status: str):
    """
    Display Twilio pipeline steps with visual indicators.
    
    Args:
        call_status (str): Current call status
    """
    steps = [
        ("1", "Call Initiated", "initiated"),
        ("2", "Ringing", "ringing"),
        ("3", "In Progress", "in-progress"),
        ("4", "Streaming Audio", "streaming"),
        ("5", "Completed", "completed")
    ]
    
    st.markdown("### 🔄 Pipeline Status")
    
    for step_num, step_name, step_key in steps:
        is_active = (
            (call_status.lower() == step_key) or
            (step_key == "streaming" and call_status.lower() == "in-progress")
        )
        
        step_class = "step-active" if is_active else "step-inactive"
        icon = "✓" if is_active else "○"
        
        st.markdown(f"""
        <div class="pipeline-step {step_class}">
            <strong>{icon} Step {step_num}:</strong> {step_name}
        </div>
        """, unsafe_allow_html=True)


def main():
    """Main application function."""
    
    # Initialize session state
    initialize_session_state()
    
    # Initialize pipeline manager
    manager = TwilioPipelineManager(API_BASE_URL)
    
    # Header
    st.markdown('<h1 class="main-header">📞 Twilio Pipeline Dashboard</h1>', unsafe_allow_html=True)
    
    # Sidebar configuration
    with st.sidebar:
        st.markdown("## ⚙️ Configuration")
        st.markdown("---")
        
        # API URL configuration
        api_url = st.text_input(
            "API Base URL",
            value=API_BASE_URL,
            help="Base URL for the FastAPI backend"
        )
        if api_url != API_BASE_URL:
            manager.api_base_url = api_url
        
        st.markdown("---")
        st.markdown("## 🔄 Auto Refresh")
        
        auto_refresh = st.checkbox(
            "Enable Auto Refresh",
            value=st.session_state.auto_refresh,
            help="Automatically refresh call statuses"
        )
        st.session_state.auto_refresh = auto_refresh
        
        if auto_refresh:
            refresh_interval = st.slider(
                "Refresh Interval (seconds)",
                min_value=2,
                max_value=30,
                value=st.session_state.refresh_interval,
                step=1
            )
            st.session_state.refresh_interval = refresh_interval
        
        st.markdown("---")
        st.markdown("## 📊 Quick Stats")
        
        # Get active calls and streams
        active_calls_result = manager.get_active_calls()
        active_streams_result = manager.get_active_streams()
        
        if active_calls_result.get("success"):
            st.metric("Active Calls", active_calls_result.get("active_calls", 0))
        else:
            st.metric("Active Calls", "Error")
        
        if active_streams_result.get("success"):
            st.metric("Active Streams", active_streams_result.get("active_streams", 0))
        else:
            st.metric("Active Streams", "Error")
        
        st.markdown("---")
        st.markdown("## 🎯 Quick Actions")
        
        if st.button("🔄 Refresh All", use_container_width=True):
            st.rerun()
        
        if st.button("🗑️ Clear History", use_container_width=True):
            st.session_state.call_history.clear()
            st.session_state.monitored_calls.clear()
            st.rerun()
    
    # Main content area with tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "📞 Initiate Call",
        "📊 Active Calls",
        "📈 Call History",
        "🔍 Monitor Calls"
    ])
    
    # Tab 1: Initiate Call
    with tab1:
        st.markdown("### 📞 Initiate New Call")
        st.markdown("Enter a phone number to initiate a voice call through the Twilio pipeline.")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            phone_number = st.text_input(
                "Phone Number",
                placeholder="+1234567890",
                help="Enter phone number with country code (e.g., +1234567890)"
            )
        
        with col2:
            st.markdown("<br>", unsafe_allow_html=True)
            initiate_button = st.button("📞 Initiate Call", type="primary", use_container_width=True)
        
        # Optional message
        message = st.text_area(
            "Optional Message",
            placeholder="Optional message for the call",
            help="Optional message to include with the call",
            height=100
        )
        
        # Phone number validation
        if phone_number:
            is_valid, error_msg = validate_phone_number(phone_number)
            if not is_valid:
                st.warning(f"⚠️ {error_msg}")
        
        # Initiate call
        if initiate_button:
            if not phone_number:
                st.error("❌ Please enter a phone number")
            else:
                is_valid, error_msg = validate_phone_number(phone_number)
                if not is_valid:
                    st.error(f"❌ {error_msg}")
                else:
                    with st.spinner("🔄 Initiating call..."):
                        result = manager.initiate_call(phone_number, message if message else None)
                        
                        if result.get("success"):
                            call_sid = result.get("call_sid")
                            status = result.get("status", "unknown")
                            
                            st.success(f"✅ Call initiated successfully!")
                            
                            # Add to call history
                            call_record = {
                                "call_sid": call_sid,
                                "phone_number": phone_number,
                                "status": status,
                                "timestamp": datetime.now().isoformat(),
                                "message": message if message else None
                            }
                            st.session_state.call_history.append(call_record)
                            st.session_state.monitored_calls[call_sid] = result
                            
                            # Display call information
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("Call SID", call_sid[:20] + "...")
                            with col2:
                                st.metric("Status", format_call_status(status))
                            with col3:
                                st.metric("Phone", phone_number)
                            
                            # Display pipeline steps
                            display_pipeline_steps(status)
                            
                        else:
                            st.error(f"❌ Failed to initiate call: {result.get('error', 'Unknown error')}")
        
        st.markdown("---")
        st.markdown("### 📝 Instructions")
        st.info("""
        **How to initiate a call:**
        1. Enter a phone number with country code (e.g., +1234567890)
        2. Optionally add a message
        3. Click "Initiate Call"
        4. Monitor the call status in the "Active Calls" or "Monitor Calls" tabs
        
        **Phone Number Format:**
        - Must start with + (country code)
        - Followed by digits only
        - Example: +1234567890, +918200467191
        """)
    
    # Tab 2: Active Calls
    with tab2:
        st.markdown("### 📊 Active Calls Dashboard")
        
        # Refresh button
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("🔄 Refresh", key="refresh_active"):
                st.rerun()
        
        # Get active calls
        active_calls_result = manager.get_active_calls()
        
        if active_calls_result.get("success"):
            active_calls_count = active_calls_result.get("active_calls", 0)
            call_sessions = active_calls_result.get("call_sessions", [])
            
            if active_calls_count == 0:
                st.info("📭 No active calls at the moment")
            else:
                st.success(f"📞 Found {active_calls_count} active call(s)")
                
                # Display metrics
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Active Calls", active_calls_count)
                with col2:
                    st.metric("Call Sessions", len(call_sessions))
                with col3:
                    st.metric("Monitored", len(st.session_state.monitored_calls))
                
                # Display active call sessions
                if call_sessions:
                    st.markdown("#### 📋 Active Call Sessions")
                    for session_id in call_sessions:
                        st.code(f"Session ID: {session_id}")
        else:
            st.error(f"❌ Error fetching active calls: {active_calls_result.get('error', 'Unknown error')}")
        
        st.markdown("---")
        
        # Get active streams
        st.markdown("### 🎙️ Active Streams")
        active_streams_result = manager.get_active_streams()
        
        if active_streams_result.get("success"):
            active_streams_count = active_streams_result.get("active_streams", 0)
            stream_sessions = active_streams_result.get("session_ids", [])
            
            if active_streams_count == 0:
                st.info("📭 No active streams at the moment")
            else:
                st.success(f"🎙️ Found {active_streams_count} active stream(s)")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Active Streams", active_streams_count)
                with col2:
                    st.metric("Stream Sessions", len(stream_sessions))
                
                if stream_sessions:
                    st.markdown("#### 📋 Active Stream Sessions")
                    for session_id in stream_sessions:
                        st.code(f"Session ID: {session_id}")
        else:
            st.error(f"❌ Error fetching active streams: {active_streams_result.get('error', 'Unknown error')}")
    
    # Tab 3: Call History
    with tab3:
        st.markdown("### 📈 Call History")
        
        if not st.session_state.call_history:
            st.info("📭 No call history yet. Initiate a call to see history here.")
        else:
            # Display statistics
            total_calls = len(st.session_state.call_history)
            st.metric("Total Calls", total_calls)
            
            # Filter options
            col1, col2 = st.columns(2)
            with col1:
                show_all = st.checkbox("Show All Calls", value=True)
            with col2:
                if st.button("🗑️ Clear History"):
                    st.session_state.call_history.clear()
                    st.rerun()
            
            # Display call history
            st.markdown("#### 📋 Recent Calls")
            
            # Convert deque to list for display
            history_list = list(st.session_state.call_history)
            
            # Display in reverse order (newest first)
            for idx, call_record in enumerate(reversed(history_list)):
                call_sid = call_record.get("call_sid", "Unknown")
                phone_number = call_record.get("phone_number", "Unknown")
                status = call_record.get("status", "unknown")
                timestamp = call_record.get("timestamp", "")
                
                # Parse timestamp
                try:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    time_str = dt.strftime("%Y-%m-%d %H:%M:%S")
                except:
                    time_str = timestamp
                
                with st.expander(f"📞 {phone_number} - {format_call_status(status)} ({time_str})"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Call SID:** {call_sid}")
                        st.write(f"**Phone:** {phone_number}")
                    with col2:
                        st.write(f"**Status:** {format_call_status(status)}")
                        st.write(f"**Time:** {time_str}")
                    
                    if call_record.get("message"):
                        st.write(f"**Message:** {call_record['message']}")
                    
                    # Action buttons
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("🔄 Check Status", key=f"check_{call_sid}_{idx}"):
                            with st.spinner("Checking..."):
                                status_result = manager.get_call_status(call_sid)
                                if status_result.get("success"):
                                    st.json(status_result)
                                else:
                                    st.error(status_result.get("error", "Unknown error"))
    
    # Tab 4: Monitor Calls
    with tab4:
        st.markdown("### 🔍 Monitor Calls")
        st.markdown("Monitor specific calls and track their status in real-time.")
        
        # Add call to monitor
        st.markdown("#### ➕ Add Call to Monitor")
        monitor_call_sid = st.text_input(
            "Call SID",
            placeholder="CAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
            help="Enter a Call SID to monitor"
        )
        
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("➕ Add", key="add_monitor"):
                if monitor_call_sid:
                    with st.spinner("Fetching call status..."):
                        status_result = manager.get_call_status(monitor_call_sid)
                        if status_result.get("success"):
                            st.session_state.monitored_calls[monitor_call_sid] = status_result
                            st.success(f"✅ Added {monitor_call_sid} to monitoring")
                            st.rerun()
                        else:
                            st.error(f"❌ Error: {status_result.get('error', 'Unknown error')}")
                else:
                    st.warning("⚠️ Please enter a Call SID")
        
        st.markdown("---")
        
        # Display monitored calls
        if not st.session_state.monitored_calls:
            st.info("📭 No calls being monitored. Add a Call SID above to start monitoring.")
        else:
            st.markdown(f"#### 📊 Monitoring {len(st.session_state.monitored_calls)} Call(s)")
            
            # Auto-refresh logic
            if st.session_state.auto_refresh:
                time.sleep(st.session_state.refresh_interval)
                # Refresh all monitored calls
                for call_sid in list(st.session_state.monitored_calls.keys()):
                    status_result = manager.get_call_status(call_sid)
                    if status_result.get("success"):
                        st.session_state.monitored_calls[call_sid] = status_result
                
                # Rerun to update display
                st.rerun()
            
            # Display each monitored call
            for call_sid, call_data in st.session_state.monitored_calls.items():
                display_call_card(call_data, manager)
                
                # Remove button
                if st.button("❌ Remove from Monitor", key=f"remove_{call_sid}"):
                    del st.session_state.monitored_calls[call_sid]
                    st.rerun()
    
    # Footer
    st.markdown("---")
    st.markdown(
        '<p style="text-align: center; color: #666; font-size: 0.875rem;">'
        'Twilio Pipeline Dashboard | Real-time Call Management & Monitoring'
        '</p>',
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()

