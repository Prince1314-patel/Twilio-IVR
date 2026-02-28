#!/usr/bin/env python3
"""
Unit Tests for Intent Detection Node
===================================

Comprehensive unit tests for the intent detection node including
message processing, state updates, message history preservation,
and error handling.

Author: Advanced AI Systems Team
Last Modified: 2026-02-03
"""

import pytest
import sys
from unittest.mock import Mock, MagicMock
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

# Import the module directly to avoid name collision with the function
import app.ai.graph.nodes.intent_detection_node
from app.ai.graph.nodes.intent_detection_node import intent_detection_node
from app.ai.graph.state import AgentState
from app.ai.intent.classifier import IntentCategory

# Get reference to the actual module
node_module = sys.modules['app.ai.graph.nodes.intent_detection_node']


@pytest.fixture(autouse=True)
def mock_validation(monkeypatch):
    """Mock state validation to avoid user_id requirements in unit tests."""
    mock_validate = Mock()
    monkeypatch.setattr(node_module, "validate_state_invariants", mock_validate)
    return mock_validate


class TestIntentDetectionNode:
    """Test the intent detection node functionality."""
    
    def test_node_processes_human_message_correctly(self, monkeypatch):
        """Test that the node correctly extracts and processes human messages."""
        # Arrange
        test_message = "I need to book an appointment for tomorrow"
        state = {
            "messages": [
                SystemMessage(content="System context"),
                HumanMessage(content=test_message),
                AIMessage(content="Previous response")
            ],
        }
        
        # Mock the classify_intent_sync function - patch the module object directly
        mock_classify = Mock(return_value=("booking", 0.90))
        monkeypatch.setattr(node_module, "classify_intent_sync", mock_classify)
        
        # Act
        result = intent_detection_node(state)
        
        # Assert
        assert result["intent"] == "booking"
        assert result["intent_confidence"] == 0.90
        mock_classify.assert_called_once()
        # Verify the correct message and model were passed
        call_args = mock_classify.call_args[0]
        assert call_args[0] == test_message
        # Second argument should be the model
        assert call_args[1] is not None
    
    def test_node_extracts_last_human_message(self, monkeypatch):
        """Test that the node extracts the most recent human message."""
        # Arrange
        state = {
            "messages": [
                HumanMessage(content="First message"),
                AIMessage(content="AI response"),
                HumanMessage(content="Second message"),
                SystemMessage(content="System message"),
                HumanMessage(content="Latest message")
            ]
        }
        
        # Mock the classify_intent_sync function - patch the module object directly
        mock_classify = Mock(return_value=("inquiry", 0.75))
        monkeypatch.setattr(node_module, "classify_intent_sync", mock_classify)
        
        # Act
        intent_detection_node(state)
        
        # Assert
        mock_classify.assert_called_once()
        call_args = mock_classify.call_args[0]
        assert call_args[0] == "Latest message"
    
    def test_node_handles_dict_message_format(self, monkeypatch):
        """Test that the node handles dictionary-format messages."""
        # Arrange
        state = {
            "messages": [
                {"role": "system", "content": "System context"},
                {"role": "user", "content": "I want to cancel my appointment"},
                {"role": "assistant", "content": "AI response"}
            ]
        }
        
        # Mock the classify_intent_sync function - patch the module object directly
        mock_classify = Mock(return_value=("cancellation", 0.85))
        monkeypatch.setattr(node_module, "classify_intent_sync", mock_classify)
        
        # Act
        result = intent_detection_node(state)
        
        # Assert
        assert result["intent"] == "cancellation"
        assert result["intent_confidence"] == 0.85
        mock_classify.assert_called_once()
        call_args = mock_classify.call_args[0]
        assert call_args[0] == "I want to cancel my appointment"
    
    def test_node_updates_state_with_intent_information(self, monkeypatch):
        """Test that the node correctly updates state with intent and confidence."""
        # Arrange
        state = {
            "messages": [HumanMessage(content="Can I reschedule my appointment?")],
        }
        
        # Mock the classify_intent_sync function - patch the module object directly
        mock_classify = Mock(return_value=("rescheduling", 0.88))
        monkeypatch.setattr(node_module, "classify_intent_sync", mock_classify)
        
        # Act
        result = intent_detection_node(state)
        
        # Assert
        assert "intent" in result
        assert "intent_confidence" in result
        assert result["intent"] == "rescheduling"
        assert result["intent-confidence"] == 0.88 if "intent-confidence" in result else result["intent_confidence"] == 0.88
        # Check for new fields
        assert "active_intent" in result
        assert "intent_locked" in result
        assert "conversation_mode" in result
        
        # Verify that messages are not modified by this node
        assert "messages" not in result
    
    def test_message_history_preservation(self, monkeypatch):
        """Test that all existing messages in conversation history remain unchanged."""
        # Arrange
        original_messages = [
            SystemMessage(content="System context"),
            HumanMessage(content="Hello"),
            AIMessage(content="Hi there!"),
            HumanMessage(content="I need help with booking")
        ]
        state = {
            "messages": original_messages.copy(),
        }
        
        # Mock the classify_intent_sync function - patch the module object directly
        mock_classify = Mock(return_value=("booking", 0.92))
        monkeypatch.setattr(node_module, "classify_intent_sync", mock_classify)
        
        # Act
        result = intent_detection_node(state)
        
        # Assert
        # The node should not modify messages - they should remain in original state
        assert "messages" not in result  # Node doesn't return messages
        # Original state messages should be unchanged
        assert state["messages"] == original_messages
    
    def test_error_handling_with_classification_failure(self, monkeypatch):
        """Test graceful error handling when intent classification fails."""
        # Arrange
        state = {
            "messages": [HumanMessage(content="Test message")]
        }
        
        # Mock the classify_intent_sync function to raise an exception
        mock_classify = Mock(side_effect=Exception("Classification service unavailable"))
        monkeypatch.setattr(node_module, "classify_intent_sync", mock_classify)
        
        # Act
        result = intent_detection_node(state)
        
        # Assert - should fallback to inquiry with 0.5 confidence
        assert result["intent"] == IntentCategory.INQUIRY
        assert result["intent_confidence"] == 0.5
    
    def test_fallback_behavior_with_no_user_message(self):
        """Test fallback behavior when no user message is found."""
        # Arrange
        state = {
            "messages": [
                SystemMessage(content="System only"),
                AIMessage(content="AI only")
            ]
        }
        
        # Act
        result = intent_detection_node(state)
        
        # Assert - should default to greeting
        assert result["intent"] == IntentCategory.GREETING
        assert result["intent_confidence"] == 0.5
    
    def test_fallback_behavior_with_empty_messages(self):
        """Test fallback behavior when messages list is empty."""
        # Arrange
        state = {"messages": []}
        
        # Act
        result = intent_detection_node(state)
        
        # Assert - should default to greeting
        assert result["intent"] == IntentCategory.GREETING
        assert result["intent_confidence"] == 0.5
    
    def test_fallback_behavior_with_no_messages_key(self):
        """Test fallback behavior when messages key is missing from state."""
        # Arrange
        state = {}
        
        # Act
        result = intent_detection_node(state)
        
        # Assert - should default to greeting
        assert result["intent"] == IntentCategory.GREETING
        assert result["intent_confidence"] == 0.5
    
    def test_all_intent_categories_processing(self, monkeypatch):
        """Test that the node can process all intent categories correctly."""
        # Test cases for all intent categories
        test_cases = [
            ("I want to book an appointment", "booking", 0.90),
            ("Cancel my appointment please", "cancellation", 0.85),
            ("Can I reschedule for next week?", "rescheduling", 0.88),
            ("What are your office hours?", "inquiry", 0.82),
            ("Hello, good morning", "greeting", 0.95),
            ("What's the weather like?", "out_of_scope", 0.92)
        ]
        
        for message, expected_intent, expected_confidence in test_cases:
            # Arrange
            state = {"messages": [HumanMessage(content=message)]}
            
            # Mock the classify_intent_sync function - patch the module object directly
            mock_classify = Mock(return_value=(expected_intent, expected_confidence))
            monkeypatch.setattr(node_module, "classify_intent_sync", mock_classify)
            
            # Act
            result = intent_detection_node(state)
            
            # Assert
            assert result["intent"] == expected_intent
            assert result["intent_confidence"] == expected_confidence
    
    def test_confidence_score_validation(self, monkeypatch):
        """Test that confidence scores are properly validated."""
        # Arrange
        state = {"messages": [HumanMessage(content="Test message")]}
        
        # Test various confidence scores
        test_scores = [0.0, 0.5, 1.0, 0.85]
        
        for score in test_scores:
            # Mock the classify_intent_sync function - patch the module object directly
            mock_classify = Mock(return_value=("booking", score))
            monkeypatch.setattr(node_module, "classify_intent_sync", mock_classify)
            
            # Act
            result = intent_detection_node(state)
            
            # Assert
            assert result["intent_confidence"] == score
            assert 0.0 <= result["intent_confidence"] <= 1.0
    
    def test_node_preserves_existing_state_fields(self, monkeypatch):
        """Test that the node preserves existing state fields."""
        # Arrange
        state = {
            "messages": [HumanMessage(content="Test message")],
            "custom_field": "custom_value"
        }
        
        # Mock the classify_intent_sync function - patch the module object directly
        mock_classify = Mock(return_value=("booking", 0.90))
        monkeypatch.setattr(node_module, "classify_intent_sync", mock_classify)
        
        # Act
        result = intent_detection_node(state)
        
        # Assert
        # Node should only return intent fields, not modify existing ones
        assert "intent" in result
        assert "intent_confidence" in result
        # Check for new fields
        assert "active_intent" in result
        assert "intent_locked" in result
        assert "conversation_mode" in result
        
        # Original state should be unchanged
        assert state["custom_field"] == "custom_value"
    
    def test_logging_behavior(self, monkeypatch):
        """Test that the node logs appropriate information."""
        # Arrange
        state = {"messages": [HumanMessage(content="I need to book an appointment")]}
        
        # Mock the classify_intent_sync function - patch the module object directly
        mock_classify = Mock(return_value=("booking", 0.90))
        monkeypatch.setattr(node_module, "classify_intent_sync", mock_classify)
        
        # Mock the logger
        mock_logger = Mock()
        monkeypatch.setattr(node_module, "logger", mock_logger)
        
        # Act
        intent_detection_node(state)
        
        # Assert
        assert mock_logger.info.call_count >= 1
        log_calls = [call[0][0] for call in mock_logger.info.call_args_list]
        classification_log = next(log for log in log_calls if "Intent classified: booking" in log)
        assert "confidence: 0.90" in classification_log
    
    def test_error_logging_behavior(self, monkeypatch):
        """Test that the node logs errors appropriately."""
        # Arrange
        state = {"messages": [HumanMessage(content="Test message")]}
        
        # Mock the classify_intent_sync function to raise an exception
        mock_classify = Mock(side_effect=Exception("Test error"))
        monkeypatch.setattr(node_module, "classify_intent_sync", mock_classify)
        
        # Mock the logger
        mock_logger = Mock()
        monkeypatch.setattr(node_module, "logger", mock_logger)
        
        # Act
        intent_detection_node(state)
        
        # Assert
        mock_logger.warning.assert_called_once()
        log_call = mock_logger.warning.call_args[0][0]
        assert "Intent classification failed" in log_call
        assert "using fallback" in log_call


if __name__ == "__main__":
    pytest.main([__file__, "-v"])