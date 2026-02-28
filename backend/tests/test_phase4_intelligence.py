"""
Phase 4 Verification Tests: Intent Identity Assertions
===================================================================

Tests to verify intent nodes block execution 
when identity is not established (enforcing identity-first architecture).

Author: Advanced AI Systems Team
Created: 2026-02-09
"""

import pytest
import sys
import os
from unittest.mock import patch, MagicMock
from app.ai.graph.state import StateInvariantError

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from app.ai.graph.nodes.intent_detection_node import intent_detection_node


@pytest.fixture
def valid_identity_state():
    """State with valid identity (user_id set, name collected)."""
    return {
        "messages": [HumanMessage(content="I want to book an appointment")],
        "user_id": 123,
        "caller_mobile_number": "+919876543210",
        "needs_name_enrichment": False,
        "user_profile": {"user_id": 123, "name": "Test User"},
        "name_collection_in_progress": False,
        "user_context_loaded": True,
        "name_prompt_level": 0
    }


@pytest.fixture
def invalid_user_id_state():
    """State with invalid user_id (identity not resolved)."""
    return {
        "messages": [HumanMessage(content="Hello")],
        "user_id": 0,  # Invalid - identity not resolved
        "caller_mobile_number": "+919876543210",
        "needs_name_enrichment": False,
        "user_profile": {},
        "name_collection_in_progress": False,
        "user_context_loaded": False,
        "name_prompt_level": 0
    }


@pytest.fixture
def name_not_collected_state():
    """State where name collection is still needed."""
    return {
        "messages": [HumanMessage(content="Hello")],
        "user_id": 456,  # Valid user_id
        "caller_mobile_number": "+919876543210",
        "needs_name_enrichment": True,  # Name gate has NOT passed
        "user_profile": {"user_id": 456, "name": None},
        "name_collection_in_progress": False,
        "user_context_loaded": True,
        "name_prompt_level": 0
    }


class TestIntentNodeAssertions:
    """Verify intent detection node Phase 4 safety assertions."""

    def test_intent_blocks_when_user_id_zero(self, invalid_user_id_state):
        """Verify intent node raises StateInvariantError when user_id=0."""
        with pytest.raises(StateInvariantError) as exc_info:
            intent_detection_node(invalid_user_id_state)
        
        error_message = str(exc_info.value)
        assert "CRITICAL" in error_message
        assert "intent_guard" in error_message
        assert "user_id=0" in error_message
        assert "Identity must be resolved" in error_message



    def test_intent_succeeds_with_valid_identity(self, valid_identity_state, monkeypatch):
        """Verify intent node runs successfully with valid identity."""
        # Mock the classifier to avoid LLM calls
        # Use sys.modules to get the actual module (not the re-exported function from __init__.py)
        from app.ai.intent.classifier import IntentCategory
        import sys
        
        intent_module = sys.modules['app.ai.graph.nodes.intent_detection_node']
        
        monkeypatch.setattr(
            intent_module,
            "classify_intent_sync",
            lambda text, model: (IntentCategory.BOOKING, 0.9)
        )
        
        try:
            result = intent_detection_node(valid_identity_state)
            # Should return valid result with intent
            assert result is not None
            assert "intent" in result
            assert "intent_confidence" in result
        except StateInvariantError:
            pytest.fail("Intent node should not raise StateInvariantError with valid identity")


class TestCrossNodeAssertions:
    """Tests for Phase 4 architecture enforcement."""

    def test_both_nodes_block_when_called_before_name_gate(self):
        """Verify intelligence nodes block when name gate hasn't passed."""
        # This simulates a graph misconfiguration where intelligence runs before name gate
        pre_name_gate_state = {
            "messages": [HumanMessage(content="Book appointment")],
            "user_id": 0,  # Not resolved
            "needs_name_enrichment": True,  # Name gate hasn't passed
            "user_profile": {},
            "name_collection_in_progress": False,
            "user_context_loaded": False,
            "caller_mobile_number": "+919876543210",
            "name_prompt_level": 0
        }
        
        with pytest.raises(StateInvariantError):
            intent_detection_node(pre_name_gate_state)

    def test_assertion_error_includes_debugging_info(self, invalid_user_id_state):
        """Verify assertion errors include helpful debugging information."""
        
        # Test intent node error includes state info
        with pytest.raises(StateInvariantError) as exc_info:
            intent_detection_node(invalid_user_id_state)
        
        error_msg = str(exc_info.value)
        assert "CRITICAL" in error_msg


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
