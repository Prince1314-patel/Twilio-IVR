"""
Log Formatters
==============

This module contains custom log formatters for structured logging output.
Provides JSON formatting with standardized fields and console formatting.

Author: Advanced AI Systems Team
Last Modified: 2025-01-28
"""

import json
import logging
import traceback
from datetime import datetime, timezone
from typing import Dict, Any, Optional


class JSONFormatter(logging.Formatter):
    """
    Custom JSON formatter that outputs structured log messages.
    
    Formats log records as JSON with standardized fields including:
    - timestamp (ISO 8601 format with timezone)
    - level (log level name)
    - logger (logger name)
    - message (log message)
    - module (source module name)
    - function (source function name)
    - line (source line number)
    - session_id (if available)
    - user_id (if available)
    - request_id (if available)
    - duration_ms (if available)
    - extra (additional custom fields)
    - exception (exception information if present)
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format a log record as JSON string.
        
        Args:
            record: The log record to format
            
        Returns:
            str: JSON formatted log message
        """
        # Create base log entry with required fields
        log_entry = {
            "timestamp": self._format_timestamp(record.created),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.filename,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add contextual information if available
        context = self._extract_context(record)
        if context:
            log_entry.update(context)
        
        # Add exception information if present
        if record.exc_info:
            log_entry["exception"] = self._format_exception(record.exc_info)
        
        # Add extra fields (excluding standard LogRecord attributes)
        extra_fields = self._extract_extra_fields(record)
        if extra_fields:
            log_entry["extra"] = extra_fields
        
        return json.dumps(log_entry, ensure_ascii=False, separators=(',', ':'))
    
    def _format_timestamp(self, created: float) -> str:
        """
        Format timestamp in ISO 8601 format with timezone.
        
        Args:
            created: Timestamp from log record
            
        Returns:
            str: ISO 8601 formatted timestamp
        """
        dt = datetime.fromtimestamp(created, tz=timezone.utc)
        return dt.isoformat()
    
    def _extract_context(self, record: logging.LogRecord) -> Dict[str, Any]:
        """
        Extract contextual information from log record.
        
        Args:
            record: The log record
            
        Returns:
            dict: Contextual information
        """
        context = {}
        
        # Extract common context fields from record attributes
        context_fields = [
            'session_id', 'user_id', 'request_id', 'call_sid',
            'operation', 'duration_ms'
        ]
        
        for field in context_fields:
            if hasattr(record, field) and getattr(record, field) is not None:
                context[field] = getattr(record, field)
        
        # If context fields are not in record, try to get them from context variables
        if not context:
            try:
                from .context import get_current_context
                context_vars = get_current_context()
                context.update(context_vars)
            except ImportError:
                # Context module not available, skip
                pass
        
        return context
    
    def _format_exception(self, exc_info) -> Dict[str, str]:
        """
        Format exception information.
        
        Args:
            exc_info: Exception information tuple
            
        Returns:
            dict: Formatted exception information
        """
        exc_type, exc_value, exc_traceback = exc_info
        
        return {
            "type": exc_type.__name__ if exc_type else "Unknown",
            "message": str(exc_value) if exc_value else "",
            "traceback": "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        }
    
    def _extract_extra_fields(self, record: logging.LogRecord) -> Dict[str, Any]:
        """
        Extract extra fields from log record, excluding standard attributes.
        
        Args:
            record: The log record
            
        Returns:
            dict: Extra fields
        """
        # Standard LogRecord attributes to exclude
        standard_attrs = {
            'name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 'filename',
            'module', 'lineno', 'funcName', 'created', 'msecs', 'relativeCreated',
            'thread', 'threadName', 'processName', 'process', 'getMessage',
            'exc_info', 'exc_text', 'stack_info', 'message'
        }
        
        # Context fields we handle separately
        context_attrs = {
            'session_id', 'user_id', 'request_id', 'call_sid',
            'operation', 'duration_ms'
        }
        
        extra = {}
        for key, value in record.__dict__.items():
            if key not in standard_attrs and key not in context_attrs:
                extra[key] = value
        
        return extra


class ConsoleFormatter(logging.Formatter):
    """
    Console formatter for development mode with colored output.
    
    Provides human-readable log output for development environments
    with optional color coding based on log levels.
    """
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
        'RESET': '\033[0m'      # Reset
    }
    
    def __init__(self, use_colors: bool = True):
        """
        Initialize console formatter.
        
        Args:
            use_colors: Whether to use ANSI color codes
        """
        super().__init__()
        self.use_colors = use_colors
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record for console output.
        
        Args:
            record: The log record to format
            
        Returns:
            str: Formatted log message
        """
        # Format timestamp
        timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')
        
        # Get color for level
        color = self.COLORS.get(record.levelname, '') if self.use_colors else ''
        reset = self.COLORS['RESET'] if self.use_colors else ''
        
        # Build base message
        message = f"{timestamp} {color}[{record.levelname}]{reset} {record.name}: {record.getMessage()}"
        
        # Add context if available
        context_parts = []
        if hasattr(record, 'session_id') and record.session_id:
            context_parts.append(f"session={record.session_id}")
        if hasattr(record, 'user_id') and record.user_id:
            context_parts.append(f"user={record.user_id}")
        if hasattr(record, 'duration_ms') and record.duration_ms:
            context_parts.append(f"duration={record.duration_ms}ms")
        
        if context_parts:
            message += f" [{', '.join(context_parts)}]"
        
        # Add exception if present
        if record.exc_info:
            message += "\n" + self.formatException(record.exc_info)
        
        return message