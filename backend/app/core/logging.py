"""
Simple Logging Interface
========================

This module provides a simple, easy-to-use interface for the application logging system.
It offers convenient import statements and common logging patterns for different module types.

Usage Examples:
    # For main application components
    from app.core.logging import get_app_logger
    logger = get_app_logger(__name__)
    
    # For AI agent components
    from app.core.logging import get_ai_logger
    logger = get_ai_logger(__name__)
    
    # For error logging
    from app.core.logging import log_error
    log_error("Something went wrong", exc_info=True)
    
    # Quick setup
    from app.core.logging import setup_app_logging
    setup_app_logging()

Author: Advanced AI Systems Team
Last Modified: 2025-01-28
"""

import logging
import os
from typing import Optional, Dict, Any, Union
from functools import wraps
import time
import asyncio
from contextlib import contextmanager

from .logger_config import (
    setup_logging as _setup_logging,
    get_application_logger as _get_application_logger,
    get_ai_agent_logger as _get_ai_agent_logger,
    get_error_logger as _get_error_logger
)


# Module-level convenience functions for easy imports
def setup_app_logging(environment: str = None, log_directory: str = "logs") -> None:
    """
    Quick setup for application logging.
    
    This is the simplest way to initialize the logging system.
    
    Args:
        environment: Environment mode (development/production)
        log_directory: Directory for log files
        
    Example:
        from app.core.logging import setup_app_logging
        setup_app_logging()
    """
    if environment is None:
        environment = os.getenv("ENVIRONMENT", "development")
    
    _setup_logging(environment=environment, log_directory=log_directory)


def get_app_logger(name: str = None) -> logging.Logger:
    """
    Get a logger for main application components.
    
    This logger is suitable for:
    - Main application logic
    - Chat functionality
    - Voice processing
    - Database operations
    - API endpoints
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        logging.Logger: Configured application logger
        
    Example:
        from app.core.logging import get_app_logger
        logger = get_app_logger(__name__)
        logger.info("Application started")
    """
    base_logger = _get_application_logger()
    
    if name:
        # Create a child logger with the specified name
        return logging.getLogger(f"app.{name}")
    
    return base_logger


def get_ai_logger(name: str = None) -> logging.Logger:
    """
    Get a logger for AI agent components.
    
    This logger is suitable for:
    - AI agent operations
    - External API calls (Sarvam, etc.)
    - Machine learning operations
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        logging.Logger: Configured AI agent logger
        
    Example:
        from app.core.logging import get_ai_logger
        logger = get_ai_logger(__name__)
        logger.info("AI processing started")
    """
    base_logger = _get_ai_agent_logger()
    
    if name:
        # Create a child logger with the specified name
        return logging.getLogger(f"agentic_graph.{name}")
    
    return base_logger


def get_error_logger() -> logging.Logger:
    """
    Get the error logger for logging errors from any component.
    
    This logger captures all errors regardless of source and writes
    them to the centralized error log file.
    
    Returns:
        logging.Logger: Configured error logger
        
    Example:
        from app.core.logging import get_error_logger
        error_logger = get_error_logger()
        error_logger.error("Critical error occurred")
    """
    return _get_error_logger()


def get_logger(component_type: str = "app", name: str = None) -> logging.Logger:
    """
    Get a logger based on component type.
    
    This is a unified interface that routes to the appropriate logger
    based on the component type.
    
    Args:
        component_type: Type of component ("app", "ai", "error")
        name: Logger name (typically __name__)
        
    Returns:
        logging.Logger: Configured logger for the component type
        
    Example:
        from app.core.logging import get_logger
        
        # For app components
        app_logger = get_logger("app", __name__)
        
        # For AI components
        ai_logger = get_logger("ai", __name__)
        
        # For errors
        error_logger = get_logger("error")
    """
    if component_type.lower() in ("app", "application", "main"):
        return get_app_logger(name)
    elif component_type.lower() in ("ai", "agent", "agentic"):
        return get_ai_logger(name)
    elif component_type.lower() in ("error", "err"):
        return get_error_logger()
    else:
        # Default to application logger
        return get_app_logger(name)


# Convenience functions for common logging patterns
def log_info(message: str, logger_name: str = None, **kwargs) -> None:
    """
    Quick info logging.
    
    Args:
        message: Log message
        logger_name: Logger name (defaults to application logger)
        **kwargs: Additional context fields
        
    Example:
        from app.core.logging import log_info
        log_info("User logged in", user_id="123", session_id="abc")
    """
    logger = get_app_logger(logger_name) if logger_name else get_app_logger()
    logger.info(message, extra=kwargs)


def log_error(message: str, exc_info: bool = False, logger_name: str = None, **kwargs) -> None:
    """
    Quick error logging.
    
    Args:
        message: Error message
        exc_info: Include exception information
        logger_name: Logger name (defaults to error logger)
        **kwargs: Additional context fields
        
    Example:
        from app.core.logging import log_error
        try:
            risky_operation()
        except Exception:
            log_error("Operation failed", exc_info=True, operation="risky_operation")
    """
    logger = get_error_logger()
    logger.error(message, exc_info=exc_info, extra=kwargs)


def log_warning(message: str, logger_name: str = None, **kwargs) -> None:
    """
    Quick warning logging.
    
    Args:
        message: Warning message
        logger_name: Logger name (defaults to application logger)
        **kwargs: Additional context fields
        
    Example:
        from app.core.logging import log_warning
        log_warning("Rate limit approaching", current_rate=95, limit=100)
    """
    logger = get_app_logger(logger_name) if logger_name else get_app_logger()
    logger.warning(message, extra=kwargs)


def log_debug(message: str, logger_name: str = None, **kwargs) -> None:
    """
    Quick debug logging.
    
    Args:
        message: Debug message
        logger_name: Logger name (defaults to application logger)
        **kwargs: Additional context fields
        
    Example:
        from app.core.logging import log_debug
        log_debug("Processing request", request_id="req123", user_id="user456")
    """
    logger = get_app_logger(logger_name) if logger_name else get_app_logger()
    logger.debug(message, extra=kwargs)


# Decorators for common logging patterns
def log_function_calls(logger: logging.Logger = None, level: str = "DEBUG"):
    """
    Decorator to log function calls with timing.
    
    Args:
        logger: Logger to use (defaults to application logger)
        level: Log level for the messages
        
    Example:
        from app.core.logging import log_function_calls, get_app_logger
        
        @log_function_calls(get_app_logger(__name__))
        def process_data(data):
            return processed_data
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if logger is None:
                log = get_app_logger()
            else:
                log = logger
            
            start_time = time.time()
            log_level = getattr(logging, level.upper(), logging.DEBUG)
            
            log.log(log_level, f"Calling {func.__name__}", extra={
                "function": func.__name__,
                "args_count": len(args),
                "kwargs_count": len(kwargs)
            })
            
            try:
                result = func(*args, **kwargs)
                duration_ms = int((time.time() - start_time) * 1000)
                
                log.log(log_level, f"Completed {func.__name__}", extra={
                    "function": func.__name__,
                    "duration_ms": duration_ms,
                    "status": "success"
                })
                
                return result
                
            except Exception as e:
                duration_ms = int((time.time() - start_time) * 1000)
                
                log.error(f"Failed {func.__name__}: {str(e)}", extra={
                    "function": func.__name__,
                    "duration_ms": duration_ms,
                    "status": "error",
                    "error_type": type(e).__name__
                }, exc_info=True)
                
                raise
        
        return wrapper
    return decorator


def log_async_function_calls(logger: logging.Logger = None, level: str = "DEBUG"):
    """
    Decorator to log async function calls with timing.
    
    Args:
        logger: Logger to use (defaults to application logger)
        level: Log level for the messages
        
    Example:
        from app.core.logging import log_async_function_calls, get_ai_logger
        
        @log_async_function_calls(get_ai_logger(__name__))
        async def process_ai_request(request):
            return await ai_processing(request)
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if logger is None:
                log = get_app_logger()
            else:
                log = logger
            
            start_time = time.time()
            log_level = getattr(logging, level.upper(), logging.DEBUG)
            
            log.log(log_level, f"Calling async {func.__name__}", extra={
                "function": func.__name__,
                "args_count": len(args),
                "kwargs_count": len(kwargs),
                "async": True
            })
            
            try:
                result = await func(*args, **kwargs)
                duration_ms = int((time.time() - start_time) * 1000)
                
                log.log(log_level, f"Completed async {func.__name__}", extra={
                    "function": func.__name__,
                    "duration_ms": duration_ms,
                    "status": "success",
                    "async": True
                })
                
                return result
                
            except Exception as e:
                duration_ms = int((time.time() - start_time) * 1000)
                
                log.error(f"Failed async {func.__name__}: {str(e)}", extra={
                    "function": func.__name__,
                    "duration_ms": duration_ms,
                    "status": "error",
                    "error_type": type(e).__name__,
                    "async": True
                }, exc_info=True)
                
                raise
        
        return wrapper
    return decorator


@contextmanager
def log_operation(operation_name: str, logger: logging.Logger = None, **context):
    """
    Context manager for logging operations with timing.
    
    Args:
        operation_name: Name of the operation
        logger: Logger to use (defaults to application logger)
        **context: Additional context fields
        
    Example:
        from app.core.logging import log_operation, get_app_logger
        
        with log_operation("database_query", get_app_logger(__name__), query_type="SELECT"):
            result = database.execute(query)
    """
    if logger is None:
        logger = get_app_logger()
    
    start_time = time.time()
    
    logger.info(f"Starting {operation_name}", extra={
        "operation": operation_name,
        "status": "started",
        **context
    })
    
    try:
        yield
        
        duration_ms = int((time.time() - start_time) * 1000)
        logger.info(f"Completed {operation_name}", extra={
            "operation": operation_name,
            "status": "completed",
            "duration_ms": duration_ms,
            **context
        })
        
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        
        logger.error(f"Failed {operation_name}: {str(e)}", extra={
            "operation": operation_name,
            "status": "failed",
            "duration_ms": duration_ms,
            "error_type": type(e).__name__,
            **context
        }, exc_info=True)
        
        raise


# Backward compatibility aliases
def get_logger_for_module(module_name: str) -> logging.Logger:
    """
    Backward compatibility function for getting module-specific loggers.
    
    Args:
        module_name: Module name (typically __name__)
        
    Returns:
        logging.Logger: Configured logger
        
    Example:
        from app.core.logging import get_logger_for_module
        logger = get_logger_for_module(__name__)
    """
    return get_app_logger(module_name)


# Legacy support for existing patterns
def configure_logging(level: str = "INFO", log_dir: str = "logs") -> None:
    """
    Legacy function for configuring logging.
    
    Provides backward compatibility with existing configuration patterns.
    
    Args:
        level: Log level
        log_dir: Log directory
        
    Example:
        from app.core.logging import configure_logging
        configure_logging("DEBUG", "logs")
    """
    environment = "development" if level.upper() == "DEBUG" else "production"
    setup_app_logging(environment=environment, log_directory=log_dir)


# Export commonly used items for easy importing
__all__ = [
    # Setup functions
    'setup_app_logging',
    
    # Logger getters
    'get_app_logger',
    'get_ai_logger',
    'get_error_logger',
    'get_logger',
    
    # Convenience functions
    'log_info',
    'log_error',
    'log_warning',
    'log_debug',
    
    # Decorators
    'log_function_calls',
    'log_async_function_calls',
    
    # Context managers
    'log_operation',
    
    # Backward compatibility
    'get_logger_for_module',
    'configure_logging'
]