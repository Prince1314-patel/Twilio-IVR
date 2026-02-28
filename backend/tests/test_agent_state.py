"""
AgentState Unit Tests
======================

Unit tests for the AgentState TypedDict schema validation.
Tests initialization, backward compatibility, type validation, and state updates.

Author: Advanced AI Systems Team
Last Modified: 2026-02-03
"""

import pytest
import sys
import os
from typing import Dict, List

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

from app.ai.graph.state import AgentState
from langchain_core.messages import HumanMessage, AIMessage


class TestStateInitialization:
    """Test suite for AgentState initialization."""
    
    def test_initialize_with_all_fields(self):
        """Test initialization with all fields including new enrichment fields."""
        state: AgentState = {
            "messages": [HumanMessage(content="Hello")],
            "current_intent": "appointment_booking",
            "conversation_history": ["User: Hello"],
            "appointment_details": {"date": "2024-01-01"},
            "user_profile": {"user_id": 123, "name": "Test User"},
            "user_context_loaded": True,
            "caller_mobile_number": "+14155552671",
            "user_id": 123,
            "needs_name_enrichment": False
        }
        
        # Should not raise any errors
        assert isinstance(state, dict)
        assert len(state["messages"]) == 1
        assert state["user_id"] == 123
    
    def test_initialize_with_minimal_fields(self):
        """Test initialization with only required fields."""
        state: AgentState = {
            "messages": [HumanMessage(content="Hello")],
            "current_intent": "",
            "conversation_history": [],
            "appointment_details": {},
            "user_profile": {},
            "user_context_loaded": False,
            "caller_mobile_number": "",
            "user_id": 0,
            "needs_name_enrichment": False
        }
        
        assert isinstance(state, dict)
        assert state["user_context_loaded"] is False
        assert state["user_id"] == 0
    
    def test_default_values_for_new_fields(self):
        """Test that new enrichment fields have appropriate defaults."""
        state: AgentState = {
            "messages": [],
            "current_intent": "",
            "conversation_history": [],
            "appointment_details": {},
            "user_profile": {},
            "user_context_loaded": False,
            "caller_mobile_number": "",
            "user_id": 0,
            "needs_name_enrichment": False
        }
        
        # Verify defaults
        assert state["user_profile"] == {}
        assert state["user_context_loaded"] is False
        assert state["caller_mobile_number"] == ""
        assert state["user_id"] == 0
        assert state["needs_name_enrichment"] is False


class TestBackwardCompatibility:
    """Test suite for backward compatibility with existing fields."""
    
    def test_old_fields_still_work(self):
        """Test that all original fields still work correctly."""
        state: AgentState = {
            "messages": [HumanMessage(content="I need an appointment")],
            "current_intent": "appointment_booking",
            "conversation_history": ["User: I need an appointment"],
            "appointment_details": {"type": "consultation"},
            # New fields with defaults
            "user_profile": {},
            "user_context_loaded": False,
            "caller_mobile_number": "",
            "user_id": 0,
            "needs_name_enrichment": False
        }
        
        # Original fields should work as before
        assert state["current_intent"] == "appointment_booking"
        assert len(state["conversation_history"]) == 1
        assert "type" in state["appointment_details"]
    
    def test_state_with_only_old_fields_plus_defaults(self):
        """Test state with only original fields plus new field defaults."""
        state: AgentState = {
            "messages": [HumanMessage(content="Hello")],
            "current_intent": "",
            "conversation_history": [],
            "appointment_details": {},
            # New fields
            "user_profile": {},
            "user_context_loaded": False,
            "caller_mobile_number": "",
            "user_id": 0,
            "needs_name_enrichment": False
        }
        
        # Should work without issues
        assert isinstance(state, dict)
        assert "messages" in state


class TestDataTypeValidation:
    """Test suite for data type validation of state fields."""
    
    def test_messages_is_list(self):
        """Test that messages field is a list."""
        state: AgentState = {
            "messages": [HumanMessage(content="Test"), AIMessage(content="Response")],
            "current_intent": "",
            "conversation_history": [],
            "appointment_details": {},
            "user_profile": {},
            "user_context_loaded": False,
            "caller_mobile_number": "",
            "user_id": 0,
            "needs_name_enrichment": False
        }
        
        assert isinstance(state["messages"], list)
        assert len(state["messages"]) == 2
    
    def test_user_profile_is_dict(self):
        """Test that user_profile field is a dict."""
        state: AgentState = {
            "messages": [],
            "current_intent": "",
            "conversation_history": [],
            "appointment_details": {},
            "user_profile": {"user_id": 123, "name": "Test"},
            "user_context_loaded": False,
            "caller_mobile_number": "",
            "user_id": 0,
            "needs_name_enrichment": False
        }
        
        assert isinstance(state["user_profile"], dict)
        assert "user_id" in state["user_profile"]
    
    def test_user_context_loaded_is_bool(self):
        """Test that user_context_loaded field is a boolean."""
        state: AgentState = {
            "messages": [],
            "current_intent": "",
            "conversation_history": [],
            "appointment_details": {},
            "user_profile": {},
            "user_context_loaded": True,
            "caller_mobile_number": "",
            "user_id": 0,
            "needs_name_enrichment": False
        }
        
        assert isinstance(state["user_context_loaded"], bool)
        assert state["user_context_loaded"] is True
    
    def test_caller_mobile_number_is_str(self):
        """Test that caller_mobile_number field is a string."""
        state: AgentState = {
            "messages": [],
            "current_intent": "",
            "conversation_history": [],
            "appointment_details": {},
            "user_profile": {},
            "user_context_loaded": False,
            "caller_mobile_number": "+14155552671",
            "user_id": 0,
            "needs_name_enrichment": False
        }
        
        assert isinstance(state["caller_mobile_number"], str)
        assert state["caller_mobile_number"].startswith("+")
    
    def test_user_id_is_int(self):
        """Test that user_id field is an integer."""
        state: AgentState = {
            "messages": [],
            "current_intent": "",
            "conversation_history": [],
            "appointment_details": {},
            "user_profile": {},
            "user_context_loaded": False,
            "caller_mobile_number": "",
            "user_id": 12345,
            "needs_name_enrichment": False
        }
        
        assert isinstance(state["user_id"], int)
        assert state["user_id"] == 12345
    
    def test_needs_name_enrichment_is_bool(self):
        """Test that needs_name_enrichment field is a boolean."""
        state: AgentState = {
            "messages": [],
            "current_intent": "",
            "conversation_history": [],
            "appointment_details": {},
            "user_profile": {},
            "user_context_loaded": False,
            "caller_mobile_number": "",
            "user_id": 0,
            "needs_name_enrichment": True
        }
        
        assert isinstance(state["needs_name_enrichment"], bool)
        assert state["needs_name_enrichment"] is True


class TestStateUpdates:
    """Test suite for state updates (simulating LangGraph behavior)."""
    
    def test_update_user_profile(self):
        """Test updating user_profile field."""
        state: AgentState = {
            "messages": [],
            "current_intent": "",
            "conversation_history": [],
            "appointment_details": {},
            "user_profile": {},
            "user_context_loaded": False,
            "caller_mobile_number": "",
            "user_id": 0,
            "needs_name_enrichment": False
        }
        
        # Update user profile
        state["user_profile"] = {
            "user_id": 123,
            "name": "John Doe",
            "mobile_number": "+14155552671"
        }
        
        assert state["user_profile"]["name"] == "John Doe"
        assert state["user_profile"]["user_id"] == 123
    
    def test_toggle_flags(self):
        """Test toggling boolean flags."""
        state: AgentState = {
            "messages": [],
            "current_intent": "",
            "conversation_history": [],
            "appointment_details": {},
            "user_profile": {},
            "user_context_loaded": False,
            "caller_mobile_number": "",
            "user_id": 0,
            "needs_name_enrichment": False
        }
        
        # Toggle flags
        state["user_context_loaded"] = True
        state["needs_name_enrichment"] = True
        
        assert state["user_context_loaded"] is True
        assert state["needs_name_enrichment"] is True
    
    def test_merge_state_updates(self):
        """Test merging state updates (simulating LangGraph node returns)."""
        base_state: AgentState = {
            "messages": [HumanMessage(content="Hello")],
            "current_intent": "",
            "conversation_history": [],
            "appointment_details": {},
            "user_profile": {},
            "user_context_loaded": False,
            "caller_mobile_number": "+14155552671",
            "user_id": 0,
            "needs_name_enrichment": False
        }
        
        # Simulate node return (partial update)
        update = {
            "user_profile": {"user_id": 123, "name": "Test User"},
            "user_context_loaded": True,
            "user_id": 123,
            "needs_name_enrichment": True
        }
        
        # Merge update into base state
        merged_state = {**base_state, **update}
        
        # Verify merge
        assert merged_state["user_id"] == 123
        assert merged_state["user_context_loaded"] is True
        assert merged_state["user_profile"]["name"] == "Test User"
        # Original fields preserved
        assert len(merged_state["messages"]) == 1
        assert merged_state["caller_mobile_number"] == "+14155552671"
    
    def test_append_messages(self):
        """Test appending messages to state."""
        state: AgentState = {
            "messages": [HumanMessage(content="Hello")],
            "current_intent": "",
            "conversation_history": [],
            "appointment_details": {},
            "user_profile": {},
            "user_context_loaded": False,
            "caller_mobile_number": "",
            "user_id": 0,
            "needs_name_enrichment": False
        }
        
        # Append message
        state["messages"].append(AIMessage(content="Hi there!"))
        
        assert len(state["messages"]) == 2
        assert isinstance(state["messages"][1], AIMessage)


class TestCompleteUserEnrichmentFlow:
    """Test suite for complete user enrichment flow state transitions."""
    
    def test_new_user_state_progression(self):
        """Test state progression for a new user through enrichment."""
        # Initial state
        state: AgentState = {
            "messages": [HumanMessage(content="I need an appointment")],
            "current_intent": "appointment_booking",
            "conversation_history": [],
            "appointment_details": {},
            "user_profile": {},
            "user_context_loaded": False,
            "caller_mobile_number": "+14155552671",
            "user_id": 0,
            "needs_name_enrichment": False
        }
        
        # After user_context_loading_node (new user created)
        state.update({
            "user_profile": {
                "user_id": 123,
                "name": None,
                "mobile_number": "+14155552671",
                "is_new_user": True
            },
            "user_context_loaded": True,
            "user_id": 123,
            "needs_name_enrichment": True
        })
        
        assert state["user_id"] == 123
        assert state["needs_name_enrichment"] is True
        
        # After name_enrichment_node (name captured)
        state.update({
            "user_profile": {
                **state["user_profile"],
                "name": "John Doe"
            },
            "needs_name_enrichment": False
        })
        
        assert state["user_profile"]["name"] == "John Doe"
        assert state["needs_name_enrichment"] is False
    
    def test_existing_user_state_progression(self):
        """Test state progression for an existing user."""
        # Initial state
        state: AgentState = {
            "messages": [HumanMessage(content="I need an appointment")],
            "current_intent": "appointment_booking",
            "conversation_history": [],
            "appointment_details": {},
            "user_profile": {},
            "user_context_loaded": False,
            "caller_mobile_number": "+14155552671",
            "user_id": 0,
            "needs_name_enrichment": False
        }
        
        # After user_context_loading_node (existing user found)
        state.update({
            "user_profile": {
                "user_id": 123,
                "name": "John Doe",
                "mobile_number": "+14155552671",
                "is_new_user": False,
                "appointment_history": []
            },
            "user_context_loaded": True,
            "user_id": 123,
            "needs_name_enrichment": False  # Already has name
        })
        
        assert state["user_id"] == 123
        assert state["user_profile"]["name"] == "John Doe"
        assert state["needs_name_enrichment"] is False


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
