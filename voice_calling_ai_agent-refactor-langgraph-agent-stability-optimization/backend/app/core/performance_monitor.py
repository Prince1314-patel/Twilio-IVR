"""
Performance Monitor Utilities
=============================

Utilities for monitoring performance and latency of AI components.

Author: Advanced AI Systems Team
Last Modified: 2026-02-03
"""

import time
import contextlib
from typing import Generator, Optional
from app.core.logger_config import get_ai_agent_logger

logger = get_ai_agent_logger()

@contextlib.contextmanager
def performance_monitor(operation_name: str, log_threshold_ms: float = 100.0) -> Generator[None, None, None]:
    """
    Context manager to measure and log the execution time of an operation.
    
    Args:
        operation_name: Name of the operation being monitored
        log_threshold_ms: Threshold in milliseconds; only log if duration exceeds this (optional, currently logs all)
    """
    start_time = time.perf_counter()
    try:
        yield
    finally:
        end_time = time.perf_counter()
        duration_ms = (end_time - start_time) * 1000
        
        # Log performance metric
        logger.info(f"PERFORMANCE: {operation_name} took {duration_ms:.2f}ms")
        
        # We could add integration with external monitoring systems here in the future
