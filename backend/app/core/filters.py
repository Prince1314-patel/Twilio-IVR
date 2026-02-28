"""
Log Filters
===========

This module contains custom log filters for processing log records.
Provides PII masking and other filtering capabilities.

Author: Advanced AI Systems Team
Last Modified: 2025-01-28
"""

import re
import logging
from typing import Dict, Any, Union


class ContextFilter(logging.Filter):
    """
    Filter that automatically adds context variables to log records.
    
    This filter extracts context information from context variables
    and adds them to log records if they're not already present.
    """
    
    def filter(self, record: logging.LogRecord) -> bool:
        """
        Add context variables to log record if not already present.
        
        Args:
            record: Log record to enhance
            
        Returns:
            bool: Always True (record is kept and enhanced)
        """
        try:
            from .context import get_current_context
            context = get_current_context()
            
            # Add context variables to record if not already present
            for key, value in context.items():
                if not hasattr(record, key) or getattr(record, key) is None:
                    setattr(record, key, value)
        except ImportError:
            # Context module not available, skip
            pass
        
        return True


class PIIMaskingFilter(logging.Filter):
    """
    Filter that masks personally identifiable information (PII) in log messages.
    
    This filter processes log records to mask or remove sensitive information
    including phone numbers, API keys, and other sensitive data before logging.
    
    Masking Rules:
    - Phone numbers: Show first 2 and last 2 digits (e.g., +1234567890 -> +12****7890)
    - API keys: Complete removal
    - Passwords: Complete removal
    - Authentication tokens: Complete removal
    - Audio content: Metadata only, no actual content
    """
    
    # Regex patterns for PII detection
    PHONE_PATTERN = re.compile(r'(\+?1?[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})')
    API_KEY_PATTERN = re.compile(r'(api[_-]?key|token|secret|password|auth)["\s]*[:=]["\s]*([a-zA-Z0-9_\-\.]+)', re.IGNORECASE)
    
    # Sensitive field names to remove completely
    SENSITIVE_FIELDS = {
        'api_key', 'apikey', 'api-key',
        'password', 'passwd', 'pwd',
        'token', 'auth_token', 'access_token', 'refresh_token',
        'secret', 'client_secret', 'api_secret',
        'authorization', 'auth',
        'audio_content', 'audio_data', 'voice_data',
        'transcription_full', 'full_transcript'
    }
    
    def filter(self, record: logging.LogRecord) -> bool:
        """
        Filter and mask PII in log record.
        
        Args:
            record: The log record to filter
            
        Returns:
            bool: Always True (record is kept but modified)
        """
        # Mask PII in the main message
        if hasattr(record, 'msg') and isinstance(record.msg, str):
            record.msg = self._mask_message(record.msg)
        
        # Mask PII in record attributes
        self._mask_record_attributes(record)
        
        return True
    
    def _mask_message(self, message: str) -> str:
        """
        Mask PII in log message string.
        
        Args:
            message: Original log message
            
        Returns:
            str: Message with PII masked
        """
        # Mask phone numbers
        message = self._mask_phone_numbers(message)
        
        # Remove API keys and sensitive data
        message = self._remove_api_keys(message)
        
        return message
    
    def _mask_phone_numbers(self, text: str) -> str:
        """
        Mask phone numbers showing only first 2 and last 2 digits.
        
        Args:
            text: Text containing potential phone numbers
            
        Returns:
            str: Text with phone numbers masked
        """
        def mask_phone(match):
            full_match = match.group(0)
            # Extract just the digits
            digits = re.sub(r'[^\d]', '', full_match)
            
            if len(digits) >= 10:
                # For US numbers (10+ digits), show first 2 and last 2
                if len(digits) == 10:
                    masked = f"{digits[:2]}****{digits[-2:]}"
                else:
                    # For international numbers, show country code + first 2 and last 2
                    masked = f"{digits[:3]}****{digits[-2:]}"
                
                # Preserve original formatting structure
                if full_match.startswith('+'):
                    masked = '+' + masked
                
                return masked
            
            return full_match
        
        return self.PHONE_PATTERN.sub(mask_phone, text)
    
    def _remove_api_keys(self, text: str) -> str:
        """
        Remove API keys and sensitive data from text.
        
        Args:
            text: Text containing potential API keys
            
        Returns:
            str: Text with API keys removed
        """
        return self.API_KEY_PATTERN.sub(r'\1: [REDACTED]', text)
    
    def _mask_record_attributes(self, record: logging.LogRecord) -> None:
        """
        Mask PII in log record attributes.
        
        Args:
            record: Log record to modify
        """
        # Check all record attributes
        for attr_name in list(record.__dict__.keys()):
            attr_value = getattr(record, attr_name)
            
            # Remove sensitive fields completely
            if attr_name.lower() in self.SENSITIVE_FIELDS:
                setattr(record, attr_name, '[REDACTED]')
                continue
            
            # Mask PII in string attributes
            if isinstance(attr_value, str):
                masked_value = self._mask_message(attr_value)
                setattr(record, attr_name, masked_value)
            
            # Mask PII in dictionary attributes
            elif isinstance(attr_value, dict):
                try:
                    masked_dict = self._mask_dict(attr_value)
                    setattr(record, attr_name, masked_dict)
                except (RecursionError, ValueError):
                    # Handle circular references or other issues
                    setattr(record, attr_name, '[MASKING_ERROR]')
    
    def _mask_dict(self, data: Dict[str, Any], depth: int = 0) -> Dict[str, Any]:
        """
        Mask PII in dictionary data.
        
        Args:
            data: Dictionary to mask
            depth: Current recursion depth to prevent infinite recursion
            
        Returns:
            dict: Dictionary with PII masked
        """
        # Prevent infinite recursion
        if depth > 10:
            return {'[TRUNCATED]': 'Max depth reached'}
        
        masked_data = {}
        
        for key, value in data.items():
            # Remove sensitive keys completely
            if key.lower() in self.SENSITIVE_FIELDS:
                masked_data[key] = '[REDACTED]'
            elif isinstance(value, str):
                masked_data[key] = self._mask_message(value)
            elif isinstance(value, dict):
                # Check for circular reference
                if id(value) == id(data):
                    masked_data[key] = '[CIRCULAR_REFERENCE]'
                else:
                    masked_data[key] = self._mask_dict(value, depth + 1)
            else:
                masked_data[key] = value
        
        return masked_data


class LevelFilter(logging.Filter):
    """
    Filter that allows only specific log levels.
    
    Useful for creating handlers that only process certain log levels,
    such as error-only handlers.
    """
    
    def __init__(self, level: Union[int, str]):
        """
        Initialize level filter.
        
        Args:
            level: Minimum log level to allow (int or string)
        """
        super().__init__()
        if isinstance(level, str):
            level = getattr(logging, level.upper())
        self.level = level
    
    def filter(self, record: logging.LogRecord) -> bool:
        """
        Filter records by level.
        
        Args:
            record: Log record to check
            
        Returns:
            bool: True if record should be logged
        """
        return record.levelno >= self.level


class ErrorOnlyFilter(logging.Filter):
    """
    Filter that only allows ERROR and CRITICAL level messages.
    
    Used for error-specific log files.
    """
    
    def filter(self, record: logging.LogRecord) -> bool:
        """
        Filter to allow only error-level messages.
        
        Args:
            record: Log record to check
            
        Returns:
            bool: True if record is ERROR or CRITICAL level
        """
        return record.levelno >= logging.ERROR