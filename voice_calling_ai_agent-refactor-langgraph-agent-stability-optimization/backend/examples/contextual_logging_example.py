#!/usr/bin/env python3
"""
Contextual Logging Example
=========================

This example demonstrates how to use the contextual logging features
of the Healthcare AI Assistant logging system.

Run this example to see contextual logging in action.
"""

import asyncio
import logging
import sys
import tempfile
from pathlib import Path

# Add the parent directory to the path so we can import our modules
sys.path.append(str(Path(__file__).parent.parent))

from app.core.logger_config import setup_logging, get_application_logger, get_ai_agent_logger
from app.core.context import (
    LoggingContext, PerformanceTimer, timed_operation,
    log_request_start, log_request_end, log_websocket_event,
    log_ai_operation, log_database_operation, log_exception
)


def demonstrate_basic_contextual_logging():
    """Demonstrate basic contextual logging with session and user context."""
    print("=== Basic Contextual Logging ===")
    
    logger = get_application_logger()
    
    # Log without context
    logger.info("This is a log message without context")
    
    # Log with context using context manager
    with LoggingContext(session_id="session_123", user_id="user_456"):
        logger.info("This message includes session and user context")
        logger.warning("This warning also includes the context")
        
        # Nested context
        with LoggingContext(operation="user_profile_update"):
            logger.info("This message has session, user, and operation context")
    
    # Context is restored after exiting
    logger.info("Back to no context")


def demonstrate_performance_timing():
    """Demonstrate performance timing with contextual logging."""
    print("\n=== Performance Timing ===")
    
    logger = get_application_logger()
    
    # Manual timing with context
    with LoggingContext(session_id="perf_session", user_id="perf_user"):
        with PerformanceTimer("database_query", logger):
            # Simulate database work
            import time
            time.sleep(0.05)  # 50ms
        
        # Timing with threshold (only log if over threshold)
        with PerformanceTimer("fast_operation", logger, threshold_ms=100):
            time.sleep(0.01)  # 10ms - won't be logged due to threshold
        
        with PerformanceTimer("slow_operation", logger, threshold_ms=30):
            time.sleep(0.04)  # 40ms - will be logged


@timed_operation("decorated_function", get_application_logger())
def demonstrate_timed_decorator():
    """Demonstrate the timed operation decorator."""
    print("\n=== Timed Operation Decorator ===")
    
    with LoggingContext(session_id="decorator_session"):
        # Simulate some work
        import time
        time.sleep(0.03)  # 30ms
        return "Function completed successfully"


@timed_operation("async_decorated_function", get_ai_agent_logger())
async def demonstrate_async_timed_decorator():
    """Demonstrate the async timed operation decorator."""
    print("\n=== Async Timed Operation Decorator ===")
    
    with LoggingContext(session_id="async_session", operation="ai_processing"):
        # Simulate async work
        await asyncio.sleep(0.02)  # 20ms
        return "Async function completed successfully"


def demonstrate_convenience_functions():
    """Demonstrate convenience logging functions."""
    print("\n=== Convenience Logging Functions ===")
    
    app_logger = get_application_logger()
    ai_logger = get_ai_agent_logger()
    
    # Request logging
    log_request_start(
        app_logger, "req_789", "/api/chat/message", "POST",
        session_id="web_session_123", user_id="user_789"
    )
    
    # Simulate request processing
    import time
    start_time = time.time()
    time.sleep(0.025)  # 25ms
    duration_ms = (time.time() - start_time) * 1000
    
    log_request_end(
        app_logger, "req_789", "/api/chat/message", 200, duration_ms, "POST",
        session_id="web_session_123", user_id="user_789"
    )
    
    # WebSocket event logging
    log_websocket_event(
        app_logger, "connect", "ws_session_456",
        user_id="user_789", connection_count=3
    )
    
    # AI operation logging
    log_ai_operation(
        ai_logger, "intent_detection",
        session_id="ai_session_789", user_id="user_789",
        duration_ms=45.2, model="intent_v2", confidence=0.87
    )
    
    # Database operation logging
    log_database_operation(
        app_logger, "INSERT", "messages", 12.5, 1,
        session_id="db_session_101"
    )


def demonstrate_exception_logging():
    """Demonstrate exception logging with context."""
    print("\n=== Exception Logging ===")
    
    logger = get_application_logger()
    
    with LoggingContext(session_id="error_session", user_id="error_user"):
        try:
            # Simulate an error
            result = 10 / 0
        except ZeroDivisionError:
            log_exception(
                logger, "Division by zero error occurred during calculation",
                exc_info=True, operation="mathematical_calculation"
            )
        
        # Exception with performance timing
        try:
            with PerformanceTimer("failing_operation", logger):
                raise ValueError("Simulated processing error")
        except ValueError:
            pass  # Timer automatically logs the failure


def demonstrate_complex_scenario():
    """Demonstrate a complex real-world scenario."""
    print("\n=== Complex Real-World Scenario ===")
    
    app_logger = get_application_logger()
    ai_logger = get_ai_agent_logger()
    
    # Simulate a voice call processing scenario
    call_sid = "call_abc123"
    session_id = "voice_session_456"
    user_id = "caller_789"
    
    with LoggingContext(session_id=session_id, user_id=user_id, call_sid=call_sid):
        # Log call start
        app_logger.info("Voice call initiated", extra={'phone_number': '+1234567890'})
        
        # Process audio with timing
        with PerformanceTimer("audio_transcription", ai_logger):
            import time
            time.sleep(0.08)  # 80ms transcription
        
        # AI intent detection
        log_ai_operation(
            ai_logger, "intent_detection",
            duration_ms=35.7, intent="booking", confidence=0.92
        )
        
        # Database operations
        log_database_operation(
            app_logger, "INSERT", "call_logs", 8.2, 1
        )
        
        log_database_operation(
            app_logger, "UPDATE", "user_stats", 5.1, 1
        )
        
        # Log call completion
        app_logger.info("Voice call completed successfully", 
                       extra={'total_duration_seconds': 45.2, 'transcription_length': 156})


def main():
    """Main function to run all demonstrations."""
    print("Contextual Logging System Demonstration")
    print("=" * 50)
    
    # Set up logging with a temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        setup_logging(environment="development", log_directory=temp_dir)
        
        print(f"Logs will be written to: {temp_dir}")
        print("Check the log files to see the structured JSON output with context!\n")
        
        # Run demonstrations
        demonstrate_basic_contextual_logging()
        demonstrate_performance_timing()
        
        result = demonstrate_timed_decorator()
        print(f"Decorated function result: {result}")
        
        async_result = asyncio.run(demonstrate_async_timed_decorator())
        print(f"Async decorated function result: {async_result}")
        
        demonstrate_convenience_functions()
        demonstrate_exception_logging()
        demonstrate_complex_scenario()
        
        print(f"\n=== Log Files Created ===")
        log_dir = Path(temp_dir)
        for log_file in log_dir.glob("*.log"):
            print(f"- {log_file.name}: {log_file.stat().st_size} bytes")
        
        print(f"\nTo see the actual log content, check the files in: {temp_dir}")
        print("Each log entry is a JSON object with contextual information!")


if __name__ == "__main__":
    main()