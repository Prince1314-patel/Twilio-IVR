"""
Tests for Performance Monitoring and Integration
================================================

Tests for the performance monitor utility and integration capabilities.

Author: Advanced AI Systems Team
Last Modified: 2026-02-03
"""

import pytest
import time
from unittest.mock import patch, MagicMock

from app.core.performance_monitor import performance_monitor
from app.ai.graph.nodes.intent_detection_node import intent_detection_node
from app.ai.intent.classifier import IntentCategory
# Use importlib to bypass shadowing
import sys
import importlib
if "app.ai.graph.nodes.intent_detection_node" in sys.modules:
    intent_module_real = sys.modules["app.ai.graph.nodes.intent_detection_node"]
else:
    intent_module_real = importlib.import_module("app.ai.graph.nodes.intent_detection_node")

class TestPerformanceMonitor:
    
    @patch("app.core.performance_monitor.logger")
    def test_performance_monitor_logging(self, mock_logger):
        """Test that performance monitor logs execution time."""
        
        with performance_monitor("test_operation"):
            time.sleep(0.01)
            
        # Verify logger was called
        mock_logger.info.assert_called_once()
        log_message = mock_logger.info.call_args[0][0]
        assert "PERFORMANCE: test_operation took" in log_message
        
    def test_performance_monitor_exception_propagation(self):
        """Test that exceptions propagate through the monitor."""
        
        with pytest.raises(ValueError):
            with performance_monitor("failed_operation"):
                raise ValueError("Test error")

class TestIntentNodeIntegration:
    
    def test_intent_node_with_monitor(self):
        """Test intent node uses performance monitor."""
        with patch.object(intent_module_real, "classify_intent_sync") as mock_classify, \
             patch.object(intent_module_real, "performance_monitor") as mock_monitor:
            
            mock_classify.return_value = (IntentCategory.BOOKING, 0.95)
            
            state = {
                "messages": [{"role": "user", "content": "I want to book"}]
            }
            
            intent_detection_node(state)
            
            # Check context manager usage
            mock_monitor.assert_called_with("intent_classification")
        
    def test_intent_node_fallback(self):
        """Test graceful degradation when classification fails."""
        with patch.object(intent_module_real, "classify_intent_sync") as mock_classify:
            mock_classify.side_effect = Exception("Service timeout")
            
            state = {
                "messages": [{"role": "user", "content": "I want to book"}]
            }
            
            result = intent_detection_node(state)
            
            # Should fallback to inquiry/0.5
            assert result["intent"] == IntentCategory.INQUIRY
            assert result["intent_confidence"] == 0.5
