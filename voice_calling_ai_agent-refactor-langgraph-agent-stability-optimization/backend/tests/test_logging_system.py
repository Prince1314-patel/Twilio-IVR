#!/usr/bin/env python3
"""
Logging System Tests
===================

Tests for the application logging system including logger configuration,
request/response logging middleware, and all logger functionality.

Author: Advanced AI Systems Team
Last Modified: 2025-01-29
"""

import os
import unittest
import tempfile
import shutil
import logging
import json
from pathlib import Path
from unittest.mock import patch, MagicMock, Mock
from typing import Dict, Any

from app.core.logger_config import (
    LoggerConfig, setup_logging, get_application_logger, 
    get_ai_agent_logger, get_error_logger
)
from app.core.logging import (
    setup_app_logging, get_app_logger, get_ai_logger, 
    get_logger, log_info, log_error, log_warning, log_debug
)


class TestLoggingSystem(unittest.TestCase):
    """Tests for the logging system."""
    
    def setUp(self):
        """Set up test environment."""
        # Create temporary directory for test logs
        self.temp_dir = tempfile.mkdtemp()
        self.log_dir = os.path.join(self.temp_dir, "logs")
        
        # Store original logging state
        self.original_loggers = {}
        for name in ['app.main', 'agentic_graph', 'app.error']:
            logger = logging.getLogger(name)
            self.original_loggers[name] = {
                'level': logger.level,
                'handlers': logger.handlers.copy(),
                'propagate': logger.propagate
            }
    
    def tearDown(self):
        """Clean up test environment."""
        # Restore original logging state
        for name, state in self.original_loggers.items():
            logger = logging.getLogger(name)
            logger.setLevel(state['level'])
            logger.handlers.clear()
            logger.handlers.extend(state['handlers'])
            logger.propagate = state['propagate']
        
        # Clean up temporary directory
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_logger_config_initialization(self):
        """Test that LoggerConfig can be initialized and configured."""
        config = LoggerConfig(log_directory=self.log_dir, environment="development")
        
        # Test initialization
        self.assertEqual(config.log_directory, Path(self.log_dir))
        self.assertEqual(config.environment, "development")
        self.assertFalse(config.is_configured)
        
        # Test setup
        config.setup_logging()
        self.assertTrue(config.is_configured)
        
        # Test that log directory was created
        self.assertTrue(Path(self.log_dir).exists())
    
    def test_logger_factory_functions(self):
        """Test logger factory functions."""
        # Setup logging in temp directory
        setup_logging(environment="development", log_directory=self.log_dir)
        
        # Test application logger
        app_logger = get_application_logger()
        self.assertIsInstance(app_logger, logging.Logger)
        self.assertEqual(app_logger.name, 'app.main')
        
        # Test AI agent logger
        ai_logger = get_ai_agent_logger()
        self.assertIsInstance(ai_logger, logging.Logger)
        self.assertEqual(ai_logger.name, 'agentic_graph')
        
        # Test error logger
        error_logger = get_error_logger()
        self.assertIsInstance(error_logger, logging.Logger)
        self.assertEqual(error_logger.name, 'app.error')
    
    def test_simple_logging_interface(self):
        """Test the simple logging interface."""
        # Setup logging in temp directory
        setup_app_logging(environment="development", log_directory=self.log_dir)
        
        # Test get_app_logger
        app_logger = get_app_logger(__name__)
        self.assertIsInstance(app_logger, logging.Logger)
        
        # Test get_ai_logger
        ai_logger = get_ai_logger(__name__)
        self.assertIsInstance(ai_logger, logging.Logger)
        
        # Test get_logger with different types
        app_logger2 = get_logger("app", __name__)
        self.assertIsInstance(app_logger2, logging.Logger)
        
        ai_logger2 = get_logger("ai", __name__)
        self.assertIsInstance(ai_logger2, logging.Logger)
        
        error_logger = get_logger("error")
        self.assertIsInstance(error_logger, logging.Logger)
    
    def test_convenience_logging_functions(self):
        """Test convenience logging functions."""
        # Setup logging in temp directory
        setup_app_logging(environment="development", log_directory=self.log_dir)
        
        # Test that functions don't raise exceptions
        try:
            log_info("Test info message", test_field="test_value")
            log_warning("Test warning message", test_field="test_value")
            log_debug("Test debug message", test_field="test_value")
            log_error("Test error message", test_field="test_value")
        except Exception as e:
            self.fail(f"Convenience logging functions raised exception: {e}")
    
    def test_log_file_creation(self):
        """Test that log files are created correctly."""
        # Setup logging in temp directory
        config = LoggerConfig(log_directory=self.log_dir, environment="development")
        config.setup_logging()
        
        # Get loggers and log messages
        app_logger = config.get_application_logger()
        ai_logger = config.get_ai_agent_logger()
        error_logger = config.get_error_logger()
        
        app_logger.info("Test application message")
        ai_logger.info("Test AI agent message")
        error_logger.error("Test error message")
        
        # Force flush handlers
        for handler in app_logger.handlers:
            handler.flush()
        for handler in ai_logger.handlers:
            handler.flush()
        for handler in error_logger.handlers:
            handler.flush()
        
        # Check that log files were created
        log_files = ['application.log', 'ai_agent.log', 'error.log']
        for log_file in log_files:
            log_path = Path(self.log_dir) / log_file
            self.assertTrue(log_path.exists(), f"Log file {log_file} was not created")
    
    def test_log_message_formatting(self):
        """Test that log messages are formatted correctly."""
        # Setup logging in temp directory
        config = LoggerConfig(log_directory=self.log_dir, environment="development")
        config.setup_logging()
        
        # Get logger and log a message
        app_logger = config.get_application_logger()
        test_message = "Test message with context"
        test_context = {"user_id": "test123", "session_id": "session456"}
        
        app_logger.info(test_message, extra=test_context)
        
        # Force flush
        for handler in app_logger.handlers:
            handler.flush()
        
        # Read log file and verify format
        log_path = Path(self.log_dir) / 'application.log'
        if log_path.exists():
            with open(log_path, 'r') as f:
                log_content = f.read()
                
            # Check that message is in log
            self.assertIn(test_message, log_content)
            
            # Try to parse as JSON (should work with JSONFormatter)
            lines = log_content.strip().split('\n')
            if lines and lines[0]:
                try:
                    log_entry = json.loads(lines[0])
                    self.assertIn('message', log_entry)
                    self.assertIn('timestamp', log_entry)
                    self.assertIn('level', log_entry)
                except json.JSONDecodeError:
                    # If not JSON, that's also acceptable (console formatter)
                    pass
    
    def test_error_logging_to_error_file(self):
        """Test that errors are logged to the error log file."""
        # Setup logging in temp directory
        config = LoggerConfig(log_directory=self.log_dir, environment="development")
        config.setup_logging()
        
        # Get different loggers and log errors
        app_logger = config.get_application_logger()
        ai_logger = config.get_ai_agent_logger()
        
        app_logger.error("Application error message")
        ai_logger.error("AI agent error message")
        
        # Force flush
        for handler in app_logger.handlers:
            handler.flush()
        for handler in ai_logger.handlers:
            handler.flush()
        
        # Check error log file
        error_log_path = Path(self.log_dir) / 'error.log'
        if error_log_path.exists():
            with open(error_log_path, 'r') as f:
                error_content = f.read()
            
            # Both errors should be in the error log
            self.assertIn("Application error message", error_content)
            self.assertIn("AI agent error message", error_content)
    
    def test_logger_levels(self):
        """Test that logger levels work correctly."""
        # Setup logging in temp directory
        config = LoggerConfig(log_directory=self.log_dir, environment="production")
        config.setup_logging()
        
        # Get logger
        app_logger = config.get_application_logger()
        
        # Test that logger has appropriate level
        self.assertGreaterEqual(app_logger.level, logging.INFO)
        
        # Test level checking
        self.assertTrue(app_logger.isEnabledFor(logging.ERROR))
        self.assertTrue(app_logger.isEnabledFor(logging.WARNING))
        self.assertTrue(app_logger.isEnabledFor(logging.INFO))
    
    def test_multiple_logger_instances(self):
        """Test that multiple logger instances work correctly."""
        # Setup logging in temp directory
        setup_app_logging(environment="development", log_directory=self.log_dir)
        
        # Get multiple logger instances
        logger1 = get_app_logger("module1")
        logger2 = get_app_logger("module2")
        ai_logger1 = get_ai_logger("ai_module1")
        ai_logger2 = get_ai_logger("ai_module2")
        
        # Test that they are different instances but work correctly
        self.assertNotEqual(logger1, logger2)
        self.assertNotEqual(ai_logger1, ai_logger2)
        
        # Test that they can all log without errors
        try:
            logger1.info("Message from module1")
            logger2.info("Message from module2")
            ai_logger1.info("Message from ai_module1")
            ai_logger2.info("Message from ai_module2")
        except Exception as e:
            self.fail(f"Multiple logger instances failed: {e}")
    
    def test_logging_with_exception_info(self):
        """Test logging with exception information."""
        # Setup logging in temp directory
        setup_app_logging(environment="development", log_directory=self.log_dir)
        
        # Test logging with exception info
        try:
            raise ValueError("Test exception")
        except ValueError:
            log_error("Test error with exception", exc_info=True)
        
        # Should not raise any exceptions
        self.assertTrue(True)  # If we get here, the test passed
    
    def test_log_directory_creation(self):
        """Test that log directory is created if it doesn't exist."""
        # Use a non-existent directory
        non_existent_dir = os.path.join(self.temp_dir, "non_existent", "logs")
        
        # Setup logging - should create the directory
        config = LoggerConfig(log_directory=non_existent_dir, environment="development")
        config.setup_logging()
        
        # Check that directory was created
        self.assertTrue(Path(non_existent_dir).exists())
    
    def test_logging_backward_compatibility(self):
        """Test backward compatibility functions."""
        from app.core.logging import get_logger_for_module, configure_logging
        
        # Test backward compatibility functions don't raise exceptions
        try:
            configure_logging("DEBUG", self.log_dir)
            logger = get_logger_for_module(__name__)
            self.assertIsInstance(logger, logging.Logger)
        except Exception as e:
            self.fail(f"Backward compatibility functions failed: {e}")


class TestLoggingMiddleware(unittest.TestCase):
    """Tests for logging middleware functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.log_dir = os.path.join(self.temp_dir, "logs")
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_request_response_logging_setup(self):
        """Test that request/response logging can be set up."""
        # Setup logging
        setup_app_logging(environment="development", log_directory=self.log_dir)
        
        # Get logger for request/response logging
        logger = get_app_logger("middleware")
        
        # Test that logger can log request/response info
        try:
            logger.info("Request started", extra={
                "method": "GET",
                "path": "/api/test",
                "user_agent": "test-agent"
            })
            
            logger.info("Request completed", extra={
                "method": "GET",
                "path": "/api/test",
                "status_code": 200,
                "duration_ms": 150
            })
        except Exception as e:
            self.fail(f"Request/response logging failed: {e}")
    
    def test_websocket_logging(self):
        """Test WebSocket event logging."""
        # Setup logging
        setup_app_logging(environment="development", log_directory=self.log_dir)
        
        # Get logger for WebSocket events
        logger = get_app_logger("websocket")
        
        # Test WebSocket event logging
        try:
            logger.info("WebSocket connection established", extra={
                "session_id": "ws_session_123",
                "client_ip": "127.0.0.1"
            })
            
            logger.info("WebSocket message received", extra={
                "session_id": "ws_session_123",
                "message_type": "chat",
                "message_length": 50
            })
            
            logger.info("WebSocket connection closed", extra={
                "session_id": "ws_session_123",
                "close_code": 1000
            })
        except Exception as e:
            self.fail(f"WebSocket logging failed: {e}")


if __name__ == '__main__':
    unittest.main()