"""
Tests for contextual logging utilities.

These tests verify that the context management utilities work correctly
with the logging system.
"""

import json
import logging
import tempfile
import unittest
import asyncio
from pathlib import Path
from unittest.mock import Mock, patch

# Import the context utilities
import sys
sys.path.append(str(Path(__file__).parent.parent))

from app.core.context import (
    LoggingContext, PerformanceTimer, get_current_context,
    log_with_context, log_exception, timed_operation,
    logging_context, log_request_start, log_request_end,
    log_websocket_event, log_ai_operation, log_database_operation
)
from app.core.formatters import JSONFormatter
from app.core.filters import ContextFilter
from app.core.logger_config import LoggerConfig


class TestContextUtilities(unittest.TestCase):
    """Test contextual logging utilities."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.json_formatter = JSONFormatter()
        self.context_filter = ContextFilter()
        
        # Create a test logger with memory handler
        self.test_logger = logging.getLogger('test.context')
        self.test_logger.setLevel(logging.DEBUG)
        
        # Clear any existing handlers
        self.test_logger.handlers.clear()
        
        # Create memory handler for capturing log output
        self.log_records = []
        self.memory_handler = logging.Handler()
        self.memory_handler.emit = lambda record: self.log_records.append(record)
        self.memory_handler.addFilter(self.context_filter)  # Add context filter
        self.test_logger.addHandler(self.memory_handler)
    
    def tearDown(self):
        """Clean up after tests."""
        self.test_logger.handlers.clear()
        self.log_records.clear()
    
    def test_logging_context_manager(self):
        """Test that LoggingContext properly sets and restores context variables."""
        # Test initial state
        initial_context = get_current_context()
        self.assertEqual(initial_context, {})
        
        # Test context setting
        with LoggingContext(session_id="test_session", user_id="test_user", operation="test_op"):
            context_in_block = get_current_context()
            self.assertEqual(context_in_block['session_id'], "test_session")
            self.assertEqual(context_in_block['user_id'], "test_user")
            self.assertEqual(context_in_block['operation'], "test_op")
        
        # Test context restoration
        final_context = get_current_context()
        self.assertEqual(final_context, initial_context)
    
    def test_nested_logging_context(self):
        """Test that nested contexts work correctly."""
        with LoggingContext(session_id="outer_session", user_id="outer_user"):
            outer_context = get_current_context()
            self.assertEqual(outer_context['session_id'], "outer_session")
            self.assertEqual(outer_context['user_id'], "outer_user")
            
            with LoggingContext(session_id="inner_session", operation="inner_op"):
                inner_context = get_current_context()
                self.assertEqual(inner_context['session_id'], "inner_session")
                self.assertEqual(inner_context['user_id'], "outer_user")  # Should inherit
                self.assertEqual(inner_context['operation'], "inner_op")
            
            # Should restore to outer context
            restored_context = get_current_context()
            self.assertEqual(restored_context['session_id'], "outer_session")
            self.assertEqual(restored_context['user_id'], "outer_user")
            self.assertNotIn('operation', restored_context)
    
    def test_performance_timer(self):
        """Test PerformanceTimer context manager."""
        with PerformanceTimer("test_operation", self.test_logger) as timer:
            # Simulate some work
            import time
            time.sleep(0.01)  # 10ms
        
        # Check that timing was recorded
        self.assertIsNotNone(timer.duration_ms)
        self.assertGreater(timer.duration_ms, 5)  # Should be at least 5ms
        
        # Check that log was created
        self.assertEqual(len(self.log_records), 1)
        record = self.log_records[0]
        self.assertIn("test_operation", record.getMessage())
        self.assertIn("completed", record.getMessage())
        self.assertTrue(hasattr(record, 'operation'))
        self.assertTrue(hasattr(record, 'duration_ms'))
        self.assertEqual(record.operation, "test_operation")
    
    def test_performance_timer_with_exception(self):
        """Test PerformanceTimer handles exceptions correctly."""
        try:
            with PerformanceTimer("failing_operation", self.test_logger):
                raise ValueError("Test exception")
        except ValueError:
            pass  # Expected
        
        # Check that error log was created
        self.assertEqual(len(self.log_records), 1)
        record = self.log_records[0]
        self.assertIn("failing_operation", record.getMessage())
        self.assertIn("failed", record.getMessage())
        self.assertEqual(record.levelno, logging.ERROR)
        self.assertIsNotNone(record.exc_info)
    
    def test_log_with_context(self):
        """Test log_with_context function."""
        log_with_context(
            self.test_logger, logging.INFO, "Test message",
            session_id="test_session",
            user_id="test_user",
            duration_ms=123.45
        )
        
        # Check log record
        self.assertEqual(len(self.log_records), 1)
        record = self.log_records[0]
        self.assertEqual(record.getMessage(), "Test message")
        self.assertEqual(record.session_id, "test_session")
        self.assertEqual(record.user_id, "test_user")
        self.assertEqual(record.duration_ms, 123.45)
    
    def test_log_exception(self):
        """Test log_exception function."""
        try:
            raise RuntimeError("Test runtime error")
        except RuntimeError:
            log_exception(
                self.test_logger, "An error occurred",
                exc_info=True,
                session_id="error_session"
            )
        
        # Check log record
        self.assertEqual(len(self.log_records), 1)
        record = self.log_records[0]
        self.assertEqual(record.getMessage(), "An error occurred")
        self.assertEqual(record.levelno, logging.ERROR)
        self.assertEqual(record.session_id, "error_session")
        self.assertIsNotNone(record.exc_info)
    
    def test_timed_operation_decorator(self):
        """Test timed_operation decorator."""
        @timed_operation("decorated_operation", self.test_logger)
        def test_function():
            import time
            time.sleep(0.01)
            return "result"
        
        result = test_function()
        self.assertEqual(result, "result")
        
        # Check that timing log was created
        self.assertEqual(len(self.log_records), 1)
        record = self.log_records[0]
        self.assertIn("decorated_operation", record.getMessage())
        self.assertTrue(hasattr(record, 'duration_ms'))
    
    def test_async_timed_operation_decorator(self):
        """Test timed_operation decorator with async function."""
        @timed_operation("async_decorated_operation", self.test_logger)
        async def async_test_function():
            await asyncio.sleep(0.01)
            return "async_result"
        
        async def run_test():
            result = await async_test_function()
            self.assertEqual(result, "async_result")
            
            # Check that timing log was created
            self.assertEqual(len(self.log_records), 1)
            record = self.log_records[0]
            self.assertIn("async_decorated_operation", record.getMessage())
            self.assertTrue(hasattr(record, 'duration_ms'))
        
        # Run the async test
        asyncio.run(run_test())
    
    def test_convenience_logging_functions(self):
        """Test convenience logging functions."""
        # Test request logging
        log_request_start(
            self.test_logger, "req_123", "/api/test", "GET",
            session_id="session_123", user_id="user_456"
        )
        
        log_request_end(
            self.test_logger, "req_123", "/api/test", 200, 150.5, "GET",
            session_id="session_123", user_id="user_456"
        )
        
        # Test WebSocket logging
        log_websocket_event(
            self.test_logger, "connect", "ws_session_789",
            user_id="user_456", connection_count=5
        )
        
        # Test AI operation logging
        log_ai_operation(
            self.test_logger, "intent_detection",
            session_id="ai_session_101", duration_ms=75.2,
            model="intent_v1", confidence=0.95
        )
        
        # Test database operation logging
        log_database_operation(
            self.test_logger, "SELECT", "users", 25.3, 10,
            session_id="db_session_202"
        )
        
        # Verify all logs were created
        self.assertEqual(len(self.log_records), 5)
        
        # Check request start log
        start_record = self.log_records[0]
        self.assertIn("Request started", start_record.getMessage())
        self.assertEqual(start_record.request_id, "req_123")
        self.assertEqual(start_record.session_id, "session_123")
        
        # Check request end log
        end_record = self.log_records[1]
        self.assertIn("Request completed", end_record.getMessage())
        self.assertEqual(end_record.duration_ms, 150.5)
        
        # Check WebSocket log
        ws_record = self.log_records[2]
        self.assertIn("WebSocket event", ws_record.getMessage())
        self.assertEqual(ws_record.session_id, "ws_session_789")
        self.assertEqual(ws_record.connection_count, 5)
        
        # Check AI operation log
        ai_record = self.log_records[3]
        self.assertIn("AI operation", ai_record.getMessage())
        self.assertEqual(ai_record.duration_ms, 75.2)
        self.assertEqual(ai_record.confidence, 0.95)
        
        # Check database operation log
        db_record = self.log_records[4]
        self.assertIn("Database operation", db_record.getMessage())
        self.assertEqual(db_record.table, "users")
        self.assertEqual(db_record.rows_affected, 10)
    
    def test_context_integration_with_json_formatter(self):
        """Test that context integrates properly with JSON formatter."""
        with LoggingContext(session_id="json_session", user_id="json_user"):
            # Log a message within context
            self.test_logger.info("Test message in context")
        
        # Get the log record and format it
        record = self.log_records[0]
        formatted_json = self.json_formatter.format(record)
        parsed = json.loads(formatted_json)
        
        # Check that context was included
        self.assertEqual(parsed['session_id'], "json_session")
        self.assertEqual(parsed['user_id'], "json_user")
        self.assertEqual(parsed['message'], "Test message in context")
    
    def test_context_with_performance_timing(self):
        """Test context and performance timing together."""
        with LoggingContext(session_id="perf_session", operation="complex_task"):
            with PerformanceTimer("subtask", self.test_logger):
                import time
                time.sleep(0.01)
        
        # Check the timing log includes context
        record = self.log_records[0]
        formatted_json = self.json_formatter.format(record)
        parsed = json.loads(formatted_json)
        
        self.assertEqual(parsed['session_id'], "perf_session")
        self.assertEqual(parsed['operation'], "subtask")  # Timer operation overrides context operation
        self.assertIn('duration_ms', parsed)
        self.assertGreater(parsed['duration_ms'], 5)


if __name__ == '__main__':
    unittest.main()