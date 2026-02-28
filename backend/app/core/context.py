"""
Logging Context Management
=========================

This module provides utilities for managing contextual information in logs,
including session tracking, performance timing, and exception handling.

Author: Advanced AI Systems Team
Last Modified: 2025-01-28
"""

import time
import logging
import traceback
import contextvars
from typing import Optional, Dict, Any, Union
from contextlib import contextmanager
from functools import wraps


# Context variables for storing logging context across async operations
session_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar('session_id', default=None)
user_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar('user_id', default=None)
request_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar('request_id', default=None)
call_sid_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar('call_sid', default=None)
operation_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar('operation', default=None)


class LoggingContext:
    """
    Context manager for setting logging context information.
    
    This class provides a way to set contextual information that will be
    automatically included in all log messages within the context.
    """
    
    def __init__(self, 
                 session_id: Optional[str] = None,
                 user_id: Optional[str] = None,
                 request_id: Optional[str] = None,
                 call_sid: Optional[str] = None,
                 operation: Optional[str] = None):
        """
        Initialize logging context.
        
        Args:
            session_id: Session identifier
            user_id: User identifier
            request_id: Request identifier
            call_sid: Call session identifier (for voice calls)
            operation: Operation name being performed
        """
        self.session_id = session_id
        self.user_id = user_id
        self.request_id = request_id
        self.call_sid = call_sid
        self.operation = operation
        
        # Store previous values for restoration
        self._previous_values = {}
    
    def __enter__(self):
        """Enter the context and set context variables."""
        # Store previous values
        self._previous_values = {
            'session_id': session_id_var.get(),
            'user_id': user_id_var.get(),
            'request_id': request_id_var.get(),
            'call_sid': call_sid_var.get(),
            'operation': operation_var.get()
        }
        
        # Set new values
        if self.session_id is not None:
            session_id_var.set(self.session_id)
        if self.user_id is not None:
            user_id_var.set(self.user_id)
        if self.request_id is not None:
            request_id_var.set(self.request_id)
        if self.call_sid is not None:
            call_sid_var.set(self.call_sid)
        if self.operation is not None:
            operation_var.set(self.operation)
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the context and restore previous values."""
        # Restore previous values
        session_id_var.set(self._previous_values['session_id'])
        user_id_var.set(self._previous_values['user_id'])
        request_id_var.set(self._previous_values['request_id'])
        call_sid_var.set(self._previous_values['call_sid'])
        operation_var.set(self._previous_values['operation'])
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self.__enter__()
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        return self.__exit__(exc_type, exc_val, exc_tb)


class PerformanceTimer:
    """
    Context manager for timing operations and logging performance metrics.
    
    This class measures the duration of operations and automatically
    includes timing information in log messages.
    """
    
    def __init__(self, 
                 operation_name: str,
                 logger: Optional[logging.Logger] = None,
                 log_level: int = logging.INFO,
                 threshold_ms: Optional[float] = None):
        """
        Initialize performance timer.
        
        Args:
            operation_name: Name of the operation being timed
            logger: Logger to use for timing messages (optional)
            log_level: Log level for timing messages
            threshold_ms: Only log if duration exceeds this threshold (optional)
        """
        self.operation_name = operation_name
        self.logger = logger
        self.log_level = log_level
        self.threshold_ms = threshold_ms
        self.start_time = None
        self.end_time = None
        self.duration_ms = None
    
    def __enter__(self):
        """Start timing the operation."""
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """End timing and optionally log the duration."""
        self.end_time = time.time()
        self.duration_ms = (self.end_time - self.start_time) * 1000
        
        # Log timing information if logger is provided
        if self.logger and (self.threshold_ms is None or self.duration_ms >= self.threshold_ms):
            # Create log record with timing context
            extra_context = get_current_context()  # Start with current context
            
            # Add timing-specific context
            extra_context.update({
                'operation': self.operation_name,
                'duration_ms': round(self.duration_ms, 2)
            })
            
            message = f"Operation '{self.operation_name}' completed in {self.duration_ms:.2f}ms"
            
            if exc_type is not None:
                # Operation failed
                message = f"Operation '{self.operation_name}' failed after {self.duration_ms:.2f}ms"
                self.logger.log(logging.ERROR, message, extra=extra_context, exc_info=(exc_type, exc_val, exc_tb))
            else:
                # Operation succeeded
                self.logger.log(self.log_level, message, extra=extra_context)
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self.__enter__()
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        return self.__exit__(exc_type, exc_val, exc_tb)


def get_current_context() -> Dict[str, Any]:
    """
    Get the current logging context as a dictionary.
    
    Returns:
        dict: Current context variables
    """
    context = {}
    
    session_id = session_id_var.get()
    if session_id is not None:
        context['session_id'] = session_id
    
    user_id = user_id_var.get()
    if user_id is not None:
        context['user_id'] = user_id
    
    request_id = request_id_var.get()
    if request_id is not None:
        context['request_id'] = request_id
    
    call_sid = call_sid_var.get()
    if call_sid is not None:
        context['call_sid'] = call_sid
    
    operation = operation_var.get()
    if operation is not None:
        context['operation'] = operation
    
    return context


def add_context_to_record(record: logging.LogRecord) -> None:
    """
    Add current context variables to a log record.
    
    Args:
        record: Log record to enhance with context
    """
    context = get_current_context()
    for key, value in context.items():
        setattr(record, key, value)


def log_with_context(logger: logging.Logger, 
                    level: int, 
                    message: str, 
                    *args,
                    session_id: Optional[str] = None,
                    user_id: Optional[str] = None,
                    request_id: Optional[str] = None,
                    call_sid: Optional[str] = None,
                    operation: Optional[str] = None,
                    duration_ms: Optional[float] = None,
                    **kwargs) -> None:
    """
    Log a message with explicit context information.
    
    Args:
        logger: Logger to use
        level: Log level
        message: Log message
        *args: Message formatting arguments
        session_id: Session identifier
        user_id: User identifier
        request_id: Request identifier
        call_sid: Call session identifier
        operation: Operation name
        duration_ms: Operation duration in milliseconds
        **kwargs: Additional keyword arguments for logging
    """
    # Build extra context
    extra_context = get_current_context()  # Start with current context
    
    # Override with explicit parameters
    if session_id is not None:
        extra_context['session_id'] = session_id
    if user_id is not None:
        extra_context['user_id'] = user_id
    if request_id is not None:
        extra_context['request_id'] = request_id
    if call_sid is not None:
        extra_context['call_sid'] = call_sid
    if operation is not None:
        extra_context['operation'] = operation
    if duration_ms is not None:
        extra_context['duration_ms'] = duration_ms
    
    # Merge with any existing extra context
    if 'extra' in kwargs:
        extra_context.update(kwargs['extra'])
    kwargs['extra'] = extra_context
    
    # Log the message
    logger.log(level, message, *args, **kwargs)


def log_exception(logger: logging.Logger,
                 message: str,
                 exc_info: Optional[Union[bool, tuple]] = None,
                 level: int = logging.ERROR,
                 **context_kwargs) -> None:
    """
    Log an exception with proper formatting and context.
    
    Args:
        logger: Logger to use
        message: Error message
        exc_info: Exception information (True to capture current, tuple for specific)
        level: Log level (default ERROR)
        **context_kwargs: Additional context information
    """
    # If exc_info is True, capture current exception
    if exc_info is True:
        import sys
        exc_info = sys.exc_info()
    
    # Build context
    extra_context = get_current_context()
    extra_context.update(context_kwargs)
    
    # Log with exception information
    logger.log(level, message, exc_info=exc_info, extra=extra_context)


def timed_operation(operation_name: str,
                   logger: Optional[logging.Logger] = None,
                   log_level: int = logging.INFO,
                   threshold_ms: Optional[float] = None):
    """
    Decorator for timing function/method execution.
    
    Args:
        operation_name: Name of the operation being timed
        logger: Logger to use for timing messages
        log_level: Log level for timing messages
        threshold_ms: Only log if duration exceeds this threshold
    
    Returns:
        Decorator function
    """
    def decorator(func):
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            with PerformanceTimer(operation_name, logger, log_level, threshold_ms):
                return func(*args, **kwargs)
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            async with PerformanceTimer(operation_name, logger, log_level, threshold_ms):
                return await func(*args, **kwargs)
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoregularfunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


@contextmanager
def logging_context(session_id: Optional[str] = None,
                   user_id: Optional[str] = None,
                   request_id: Optional[str] = None,
                   call_sid: Optional[str] = None,
                   operation: Optional[str] = None):
    """
    Context manager for setting logging context (sync version).
    
    Args:
        session_id: Session identifier
        user_id: User identifier
        request_id: Request identifier
        call_sid: Call session identifier
        operation: Operation name
    """
    with LoggingContext(session_id, user_id, request_id, call_sid, operation):
        yield


async def async_logging_context(session_id: Optional[str] = None,
                              user_id: Optional[str] = None,
                              request_id: Optional[str] = None,
                              call_sid: Optional[str] = None,
                              operation: Optional[str] = None):
    """
    Async context manager for setting logging context.
    
    Args:
        session_id: Session identifier
        user_id: User identifier
        request_id: Request identifier
        call_sid: Call session identifier
        operation: Operation name
    """
    async with LoggingContext(session_id, user_id, request_id, call_sid, operation):
        yield


# Convenience functions for common logging patterns
def log_request_start(logger: logging.Logger, 
                     request_id: str,
                     endpoint: str,
                     method: str = "POST",
                     session_id: Optional[str] = None,
                     user_id: Optional[str] = None) -> None:
    """Log the start of a request."""
    log_with_context(
        logger, logging.INFO,
        f"Request started: {method} {endpoint}",
        request_id=request_id,
        session_id=session_id,
        user_id=user_id,
        operation=f"{method} {endpoint}"
    )


def log_request_end(logger: logging.Logger,
                   request_id: str,
                   endpoint: str,
                   status_code: int,
                   duration_ms: float,
                   method: str = "POST",
                   session_id: Optional[str] = None,
                   user_id: Optional[str] = None) -> None:
    """Log the end of a request."""
    log_with_context(
        logger, logging.INFO,
        f"Request completed: {method} {endpoint} - {status_code}",
        request_id=request_id,
        session_id=session_id,
        user_id=user_id,
        operation=f"{method} {endpoint}",
        duration_ms=duration_ms
    )


def log_websocket_event(logger: logging.Logger,
                       event: str,
                       session_id: str,
                       user_id: Optional[str] = None,
                       **extra_context) -> None:
    """Log WebSocket events."""
    # Build extra context properly
    context = {
        'session_id': session_id,
        'operation': f"websocket_{event}"
    }
    if user_id is not None:
        context['user_id'] = user_id
    
    # Add any additional context
    context.update(extra_context)
    
    logger.info(f"WebSocket event: {event}", extra=context)


def log_ai_operation(logger: logging.Logger,
                    operation: str,
                    session_id: Optional[str] = None,
                    user_id: Optional[str] = None,
                    duration_ms: Optional[float] = None,
                    **extra_context) -> None:
    """Log AI agent operations."""
    message = f"AI operation: {operation}"
    if duration_ms is not None:
        message += f" ({duration_ms:.2f}ms)"
    
    # Build extra context properly
    context = {'operation': operation}
    if session_id is not None:
        context['session_id'] = session_id
    if user_id is not None:
        context['user_id'] = user_id
    if duration_ms is not None:
        context['duration_ms'] = duration_ms
    
    # Add any additional context
    context.update(extra_context)
    
    logger.info(message, extra=context)


def log_database_operation(logger: logging.Logger,
                          operation: str,
                          table: Optional[str] = None,
                          duration_ms: Optional[float] = None,
                          rows_affected: Optional[int] = None,
                          session_id: Optional[str] = None,
                          **extra_context) -> None:
    """Log database operations."""
    message = f"Database operation: {operation}"
    if table:
        message += f" on {table}"
    if duration_ms is not None:
        message += f" ({duration_ms:.2f}ms)"
    if rows_affected is not None:
        message += f" - {rows_affected} rows affected"
    
    # Build extra context properly
    context = {'operation': f"db_{operation}"}
    if session_id is not None:
        context['session_id'] = session_id
    if table is not None:
        context['table'] = table
    if rows_affected is not None:
        context['rows_affected'] = rows_affected
    if duration_ms is not None:
        context['duration_ms'] = duration_ms
    
    # Add any additional context
    context.update(extra_context)
    
    logger.info(message, extra=context)