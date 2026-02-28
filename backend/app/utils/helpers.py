"""
General-Purpose Utility Functions
=================================

This module contains general-purpose utility functions that can be used
across different components of the Healthcare AI Assistant application.

Author: Advanced AI Systems Team
Last Modified: 2025-01-28
"""

import re
import json
import uuid
import hashlib
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)


def generate_session_id() -> str:
    """
    Generate a unique session ID for tracking user sessions.
    
    Returns:
        str: A unique session identifier
    """
    return f"session_{uuid.uuid4().hex[:12]}"


def generate_request_id() -> str:
    """
    Generate a unique request ID for tracking individual requests.
    
    Returns:
        str: A unique request identifier
    """
    timestamp = int(datetime.now(timezone.utc).timestamp() * 1000)
    return f"req_{timestamp}_{uuid.uuid4().hex[:8]}"


def sanitize_phone_number(phone: str) -> Optional[str]:
    """
    Sanitize and validate a phone number.
    
    Args:
        phone (str): Raw phone number input
        
    Returns:
        Optional[str]: Sanitized phone number or None if invalid
    """
    if not phone:
        return None
        
    # Remove all non-digit characters except +
    cleaned = re.sub(r'[^\d+]', '', phone)
    
    # Basic validation - should start with + and have 10-15 digits
    if re.match(r'^\+\d{10,15}$', cleaned):
        return cleaned
    
    # Try to add + if missing and has 10-15 digits
    if re.match(r'^\d{10,15}$', cleaned):
        return f"+{cleaned}"
    
    return None


def validate_email(email: str) -> bool:
    """
    Validate an email address format.
    
    Args:
        email (str): Email address to validate
        
    Returns:
        bool: True if email format is valid
    """
    if not email:
        return False
        
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def safe_json_serialize(obj: Any) -> str:
    """
    Safely serialize an object to JSON, handling non-serializable objects.
    
    Args:
        obj: Object to serialize
        
    Returns:
        str: JSON string representation
    """
    def json_serializer(obj):
        """Custom JSON serializer for non-standard types."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif hasattr(obj, '__dict__'):
            return str(obj)
        else:
            return f"<non-serializable: {type(obj).__name__}>"
    
    try:
        return json.dumps(obj, default=json_serializer, ensure_ascii=False)
    except Exception as e:
        logger.warning(f"Failed to serialize object: {e}")
        return json.dumps({"error": "serialization_failed", "type": type(obj).__name__})


def truncate_string(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate a string to a maximum length with optional suffix.
    
    Args:
        text (str): Text to truncate
        max_length (int): Maximum length including suffix
        suffix (str): Suffix to add when truncating
        
    Returns:
        str: Truncated string
    """
    if not text or len(text) <= max_length:
        return text
        
    return text[:max_length - len(suffix)] + suffix


def extract_error_details(exception: Exception) -> Dict[str, Any]:
    """
    Extract structured error details from an exception.
    
    Args:
        exception (Exception): Exception to analyze
        
    Returns:
        Dict[str, Any]: Structured error information
    """
    return {
        "error_type": type(exception).__name__,
        "error_message": str(exception),
        "error_module": getattr(exception, '__module__', 'unknown'),
        "error_class": exception.__class__.__name__
    }


def hash_sensitive_data(data: str, salt: str = "") -> str:
    """
    Hash sensitive data for logging or storage.
    
    Args:
        data (str): Sensitive data to hash
        salt (str): Optional salt for hashing
        
    Returns:
        str: Hashed representation
    """
    if not data:
        return ""
        
    combined = f"{data}{salt}"
    return hashlib.sha256(combined.encode()).hexdigest()[:16]


def format_duration_ms(duration_ms: float) -> str:
    """
    Format duration in milliseconds to human-readable string.
    
    Args:
        duration_ms (float): Duration in milliseconds
        
    Returns:
        str: Formatted duration string
    """
    if duration_ms < 1000:
        return f"{duration_ms:.1f}ms"
    elif duration_ms < 60000:
        return f"{duration_ms/1000:.2f}s"
    else:
        minutes = int(duration_ms // 60000)
        seconds = (duration_ms % 60000) / 1000
        return f"{minutes}m {seconds:.1f}s"


def deep_merge_dicts(dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deep merge two dictionaries, with dict2 values taking precedence.
    
    Args:
        dict1 (Dict[str, Any]): Base dictionary
        dict2 (Dict[str, Any]): Dictionary to merge in
        
    Returns:
        Dict[str, Any]: Merged dictionary
    """
    result = dict1.copy()
    
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge_dicts(result[key], value)
        else:
            result[key] = value
            
    return result


def is_valid_session_id(session_id: str) -> bool:
    """
    Validate a session ID format.
    
    Args:
        session_id (str): Session ID to validate
        
    Returns:
        bool: True if session ID format is valid
    """
    if not session_id:
        return False
        
    # Should match the format generated by generate_session_id()
    pattern = r'^session_[a-f0-9]{12}$'
    return bool(re.match(pattern, session_id))


def clean_text_for_speech(text: str) -> str:
    """
    Clean text for text-to-speech processing by removing problematic characters.
    
    Args:
        text (str): Text to clean
        
    Returns:
        str: Cleaned text suitable for TTS
    """
    if not text:
        return ""
    
    # Remove markdown formatting
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)  # Bold
    text = re.sub(r'\*(.*?)\*', r'\1', text)      # Italic
    text = re.sub(r'`(.*?)`', r'\1', text)        # Code
    
    # Remove URLs
    text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
    
    # Clean up extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text


def extract_appointment_keywords(text: str) -> List[str]:
    """
    Extract appointment-related keywords from text.
    
    Args:
        text (str): Text to analyze
        
    Returns:
        List[str]: List of found appointment keywords
    """
    if not text:
        return []
    
    appointment_keywords = [
        'appointment', 'schedule', 'book', 'cancel', 'reschedule',
        'meeting', 'consultation', 'visit', 'checkup', 'exam',
        'doctor', 'clinic', 'hospital', 'medical', 'health'
    ]
    
    text_lower = text.lower()
    found_keywords = []
    
    for keyword in appointment_keywords:
        if keyword in text_lower:
            found_keywords.append(keyword)
    
    return found_keywords


def get_current_timestamp() -> str:
    """
    Get current timestamp in ISO format.
    
    Returns:
        str: Current timestamp in ISO format
    """
    return datetime.now(timezone.utc).isoformat()


def parse_time_duration(duration_str: str) -> Optional[int]:
    """
    Parse a time duration string into milliseconds.
    
    Args:
        duration_str (str): Duration string (e.g., "5s", "2m", "1h")
        
    Returns:
        Optional[int]: Duration in milliseconds, or None if invalid
    """
    if not duration_str:
        return None
    
    pattern = r'^(\d+(?:\.\d+)?)(ms|s|m|h)$'
    match = re.match(pattern, duration_str.lower().strip())
    
    if not match:
        return None
    
    value, unit = match.groups()
    value = float(value)
    
    multipliers = {
        'ms': 1,
        's': 1000,
        'm': 60000,
        'h': 3600000
    }
    
    return int(value * multipliers[unit])