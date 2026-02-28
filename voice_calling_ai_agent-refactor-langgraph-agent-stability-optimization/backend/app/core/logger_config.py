"""
Logger Configuration
===================

This module provides centralized logging configuration for the Healthcare AI Assistant.
Sets up structured JSON logging, PII masking, and categorized log files.

Author: Advanced AI Systems Team
Last Modified: 2025-01-28
"""

import os
import logging
import logging.handlers
import time
import threading
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta

from .formatters import JSONFormatter, ConsoleFormatter
from .filters import PIIMaskingFilter, ErrorOnlyFilter, ContextFilter


class RetentionRotatingFileHandler(logging.handlers.RotatingFileHandler):
    """
    Enhanced RotatingFileHandler with automatic retention policy enforcement.
    
    This handler extends the standard RotatingFileHandler to automatically
    clean up old log files based on a retention policy (default 30 days).
    """
    
    def __init__(self, filename, mode='a', maxBytes=0, backupCount=0, 
                 encoding=None, delay=False, retention_days=30):
        """
        Initialize the handler with retention policy.
        
        Args:
            filename: Log file path
            mode: File open mode
            maxBytes: Maximum file size before rotation
            backupCount: Number of backup files to keep
            encoding: File encoding
            delay: Whether to delay file opening
            retention_days: Number of days to retain log files
        """
        super().__init__(filename, mode, maxBytes, backupCount, encoding, delay)
        self.retention_days = retention_days
        self._last_cleanup = 0
        self._cleanup_interval = 24 * 60 * 60  # Check once per day
    
    def doRollover(self):
        """
        Perform log rotation and cleanup old files.
        
        This method is called when the current log file exceeds maxBytes.
        It performs the standard rotation and then cleans up old files.
        """
        # Perform standard rotation
        super().doRollover()
        
        # Clean up old files after rotation
        self._cleanup_old_files()
    
    def emit(self, record):
        """
        Emit a log record, with periodic cleanup of old files.
        
        Args:
            record: LogRecord to emit
        """
        # Perform standard emission
        super().emit(record)
        
        # Periodically clean up old files (not on every emit for performance)
        current_time = time.time()
        if current_time - self._last_cleanup > self._cleanup_interval:
            self._cleanup_old_files()
            self._last_cleanup = current_time
    
    def _cleanup_old_files(self):
        """
        Clean up log files older than retention_days.
        
        This method removes backup log files that are older than the
        configured retention period.
        """
        try:
            log_dir = Path(self.baseFilename).parent
            base_name = Path(self.baseFilename).name
            
            # Find all related log files (including rotated ones)
            pattern = f"{base_name}.*"
            current_time = time.time()
            retention_seconds = self.retention_days * 24 * 60 * 60
            
            for log_file in log_dir.glob(pattern):
                try:
                    # Skip the current active log file
                    if log_file.name == base_name:
                        continue
                    
                    # Check file age
                    file_mtime = log_file.stat().st_mtime
                    file_age_seconds = current_time - file_mtime
                    
                    # Delete if older than retention period (with small buffer for precision)
                    if file_age_seconds > (retention_seconds + 1):
                        log_file.unlink()
                        
                except (OSError, IOError):
                    # Skip files that can't be processed
                    continue
                    
        except Exception:
            # Don't let cleanup errors affect logging
            pass


class LoggerConfig:
    """
    Centralized logger configuration manager.
    
    Provides setup and management of all application loggers with
    consistent formatting, filtering, and file handling.
    """
    
    def __init__(self, log_directory: str = "logs", environment: str = "development"):
        """
        Initialize logger configuration.
        
        Args:
            log_directory: Directory for log files
            environment: Environment mode (development/production)
        """
        self.log_directory = Path(log_directory)
        self.environment = environment
        self.is_configured = False
        self.console_handler: Optional[logging.Handler] = None
        
        # Configure log levels from environment variables
        self.console_level = self._get_log_level_from_env("LOG_LEVEL_CONSOLE", "DEBUG" if environment == "development" else "INFO")
        self.app_level = self._get_log_level_from_env("LOG_LEVEL_APP", "DEBUG" if environment == "development" else "INFO")
        self.ai_level = self._get_log_level_from_env("LOG_LEVEL_AI", "DEBUG" if environment == "development" else "INFO")
        self.error_level = self._get_log_level_from_env("LOG_LEVEL_ERROR", "ERROR")
        self.root_level = self._get_log_level_from_env("LOG_LEVEL_ROOT", "DEBUG" if environment == "development" else "INFO")
        
        # Ensure log directory exists
        self._ensure_log_directory()
    
    def _get_log_level_from_env(self, env_var: str, default: str = "INFO") -> int:
        """
        Get log level from environment variable.
        
        Args:
            env_var: Environment variable name
            default: Default log level if not set
            
        Returns:
            int: Logging level constant
        """
        level_str = os.getenv(env_var, default).upper()
        
        # Map string to logging level
        level_map = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "WARN": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL,
            "FATAL": logging.CRITICAL
        }
        
        return level_map.get(level_str, logging.INFO)
    
    def _ensure_log_directory(self) -> None:
        """Create log directory if it doesn't exist."""
        try:
            self.log_directory.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            # Fallback to current directory if can't create logs directory
            print(f"Warning: Could not create log directory {self.log_directory}: {e}")
            self.log_directory = Path(".")
    
    def setup_logging(self) -> None:
        """
        Set up all logging components.
        
        Configures formatters, filters, handlers, and loggers for the application.
        """
        if self.is_configured:
            return
        
        # Create formatters
        json_formatter = JSONFormatter()
        console_formatter = ConsoleFormatter(use_colors=True)
        
        # Create filters
        pii_filter = PIIMaskingFilter()
        error_filter = ErrorOnlyFilter()
        context_filter = ContextFilter()
        
        # Set up handlers
        self._setup_file_handlers(json_formatter, pii_filter, error_filter, context_filter)
        
        # Set up console handler for development
        if self.environment == "development":
            self.console_handler = self._setup_console_handler(console_formatter, pii_filter, context_filter)
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(self.root_level)
        
        self.is_configured = True
    
    def _setup_file_handlers(self, json_formatter: JSONFormatter, 
                           pii_filter: PIIMaskingFilter, 
                           error_filter: ErrorOnlyFilter,
                           context_filter: ContextFilter) -> None:
        """
        Set up rotating file handlers for different log categories.
        
        Args:
            json_formatter: JSON formatter instance
            pii_filter: PII masking filter instance
            error_filter: Error-only filter instance
        """
        # Application log handler (main app, chat, voice, database)
        app_handler = RetentionRotatingFileHandler(
            filename=self.log_directory / "application.log",
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8',
            retention_days=30
        )
        app_handler.setFormatter(json_formatter)
        app_handler.addFilter(context_filter)
        app_handler.addFilter(pii_filter)
        app_handler.setLevel(self.app_level)
        
        # AI agent log handler (AI operations, external APIs)
        ai_handler = RetentionRotatingFileHandler(
            filename=self.log_directory / "ai_agent.log",
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8',
            retention_days=30
        )
        ai_handler.setFormatter(json_formatter)
        ai_handler.addFilter(context_filter)
        ai_handler.addFilter(pii_filter)
        ai_handler.setLevel(self.ai_level)
        
        # Error log handler (all errors from any component)
        error_handler = RetentionRotatingFileHandler(
            filename=self.log_directory / "error.log",
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=10,  # Keep more error logs
            encoding='utf-8',
            retention_days=30
        )
        error_handler.setFormatter(json_formatter)
        error_handler.addFilter(context_filter)
        error_handler.addFilter(pii_filter)
        error_handler.addFilter(error_filter)
        error_handler.setLevel(self.error_level)
        
        # Add handlers to appropriate loggers
        self._configure_logger_handlers(app_handler, ai_handler, error_handler)
        
        # Add error handler to root logger to capture ALL errors regardless of source
        # This ensures requirement 3.4: "WHEN any error occurs, THE System SHALL log it to error.log regardless of the source component"
        root_logger = logging.getLogger()
        
        # Avoid duplicate handlers on root logger
        for handler in root_logger.handlers[:]:
            if isinstance(handler, RetentionRotatingFileHandler) and "error.log" in str(handler.baseFilename):
                root_logger.removeHandler(handler)
                
        root_logger.addHandler(error_handler)
    
    def _setup_console_handler(self, console_formatter: ConsoleFormatter,
                             pii_filter: PIIMaskingFilter,
                             context_filter: ContextFilter) -> logging.Handler:
        """
        Set up console handler for development mode.
        
        Args:
            console_formatter: Console formatter instance
            pii_filter: PII masking filter instance
            
        Returns:
            logging.Handler: Configured console handler
        """
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(console_formatter)
        console_handler.addFilter(context_filter)
        console_handler.addFilter(pii_filter)
        console_handler.setLevel(self.console_level)
        
        # Add to root logger for all output
        root_logger = logging.getLogger()
        
        # Avoid duplicate console handlers
        for handler in root_logger.handlers[:]:
            if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler):
                root_logger.removeHandler(handler)
                
        root_logger.addHandler(console_handler)
        return console_handler
    
    def _configure_logger_handlers(self, app_handler: logging.Handler,
                                 ai_handler: logging.Handler,
                                 error_handler: logging.Handler) -> None:
        """
        Configure specific loggers with appropriate handlers.
        
        Args:
            app_handler: Application log handler
            ai_handler: AI agent log handler
            error_handler: Error log handler
        """
        # Application components
        app_loggers = [
            'app.main',
            'app.chat',
            'app.voice',
            'app.database',
            'app.routers',
            'app.apis',
            'app.core',
            'app.core.websocket_manager',
            'fastapi',
            'uvicorn',
            'uvicorn.error'
        ]
        
        for logger_name in app_loggers:
            logger = logging.getLogger(logger_name)
            
            # Clear existing handlers
            for handler in logger.handlers[:]:
                logger.removeHandler(handler)
                
            logger.addHandler(app_handler)
            # We don't add error_handler here because we use propagation
            # and the root logger already has error_handler.
            
            logger.setLevel(self.app_level)
            logger.propagate = True # Use propagation for terminal output
        
        # AI agent components
        ai_loggers = [
            'agentic_graph',
            'agentic_graph.agent_graph',
            'app.core.sarvam_client',
            'langchain',
            'langgraph',
            'openai',
            'groq'
        ]
        
        for logger_name in ai_loggers:
            logger = logging.getLogger(logger_name)
            
            # Clear existing handlers
            for handler in logger.handlers[:]:
                logger.removeHandler(handler)
                
            logger.addHandler(ai_handler)
            
            logger.setLevel(self.ai_level)
            logger.propagate = True # Use propagation for terminal output
        
        # Special handling for access logs to use our console formatter if desired
        access_logger = logging.getLogger('uvicorn.access')
        for handler in access_logger.handlers[:]:
            access_logger.removeHandler(handler)
        if self.console_handler:
            access_logger.addHandler(self.console_handler)
        access_logger.propagate = False # Don't propagate to root to avoid double logging
    
    def get_application_logger(self) -> logging.Logger:
        """
        Get logger for main application components.
        
        Returns:
            logging.Logger: Configured application logger
        """
        if not self.is_configured:
            self.setup_logging()
        return logging.getLogger('app.main')
    
    def get_ai_agent_logger(self) -> logging.Logger:
        """
        Get logger for AI agent components.
        
        Returns:
            logging.Logger: Configured AI agent logger
        """
        if not self.is_configured:
            self.setup_logging()
        return logging.getLogger('agentic_graph')
    
    def get_error_logger(self) -> logging.Logger:
        """
        Get logger specifically for errors.
        
        Returns:
            logging.Logger: Configured error logger
        """
        if not self.is_configured:
            self.setup_logging()
        return logging.getLogger('app.error')


# Global logger configuration instance
_logger_config: Optional[LoggerConfig] = None


def setup_logging(environment: str = None, log_directory: str = "logs") -> None:
    """
    Initialize global logging configuration.
    
    Args:
        environment: Environment mode (development/production)
        log_directory: Directory for log files
    """
    global _logger_config
    
    # If already configured, don't reconfigure unless it's a forced reset
    if _logger_config and _logger_config.is_configured:
        return
    
    if environment is None:
        environment = os.getenv("ENVIRONMENT", "development")
    
    # Create new config only if it doesn't exist
    if _logger_config is None:
        _logger_config = LoggerConfig(log_directory=log_directory, environment=environment)
    
    _logger_config.setup_logging()


def get_application_logger() -> logging.Logger:
    """
    Get application logger instance.
    
    Returns:
        logging.Logger: Configured application logger
    """
    if _logger_config is None:
        setup_logging()
    return _logger_config.get_application_logger()


def get_ai_agent_logger() -> logging.Logger:
    """
    Get AI agent logger instance.
    
    Returns:
        logging.Logger: Configured AI agent logger
    """
    if _logger_config is None:
        setup_logging()
    return _logger_config.get_ai_agent_logger()


def get_error_logger() -> logging.Logger:
    """
    Get error logger instance.
    
    Returns:
        logging.Logger: Configured error logger
    """
    if _logger_config is None:
        setup_logging()
    return _logger_config.get_error_logger()


def cleanup_old_logs(log_directory: str = "logs", retention_days: int = 30) -> int:
    """
    Manually clean up old log files.
    
    This function can be called to immediately clean up log files older
    than the specified retention period. Useful for maintenance scripts
    or manual cleanup operations.
    
    Args:
        log_directory: Directory containing log files
        retention_days: Number of days to retain files
        
    Returns:
        int: Number of files deleted
    """
    deleted_count = 0
    log_dir = Path(log_directory)
    
    if not log_dir.exists():
        return deleted_count
    
    current_time = time.time()
    retention_seconds = retention_days * 24 * 60 * 60
    
    # Find all log files (*.log and *.log.*)
    for log_file in log_dir.glob("*.log*"):
        try:
            file_mtime = log_file.stat().st_mtime
            file_age_seconds = current_time - file_mtime
            
            # Delete if older than retention period (with small buffer for precision)
            if file_age_seconds > (retention_seconds + 1):
                log_file.unlink()
                deleted_count += 1
                
        except (OSError, IOError):
            # Skip files that can't be processed
            continue
    
    return deleted_count


def get_log_file_info(log_directory: str = "logs") -> dict:
    """
    Get information about log files in the directory.
    
    Args:
        log_directory: Directory containing log files
        
    Returns:
        dict: Information about log files including sizes, ages, and counts
    """
    log_dir = Path(log_directory)
    info = {
        'total_files': 0,
        'total_size_bytes': 0,
        'files': [],
        'oldest_file_days': 0,
        'newest_file_days': 0
    }
    
    if not log_dir.exists():
        return info
    
    current_time = time.time()
    oldest_time = current_time
    newest_time = 0
    
    for log_file in log_dir.glob("*.log*"):
        try:
            stat = log_file.stat()
            file_age_seconds = current_time - stat.st_mtime
            file_age_days = file_age_seconds / (24 * 60 * 60)
            
            info['files'].append({
                'name': log_file.name,
                'size_bytes': stat.st_size,
                'age_days': file_age_days,
                'modified_time': datetime.fromtimestamp(stat.st_mtime).isoformat()
            })
            
            info['total_files'] += 1
            info['total_size_bytes'] += stat.st_size
            
            if stat.st_mtime < oldest_time:
                oldest_time = stat.st_mtime
            if stat.st_mtime > newest_time:
                newest_time = stat.st_mtime
                
        except (OSError, IOError):
            continue
    
    if info['total_files'] > 0:
        info['oldest_file_days'] = (current_time - oldest_time) / (24 * 60 * 60)
        info['newest_file_days'] = (current_time - newest_time) / (24 * 60 * 60)
    
    return info