"""
Unit Tests for user_context_loading_node
=========================================

Tests for the user context loading node that orchestrates user lookup/creation
and sets up the user context for progressive enrichment.

Author: Advanced AI Systems Team
Last Modified: 2026-02-03
"""

import pytest
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

from app.ai.graph.nodes.user_context_node import user_context_loading_node
from app.ai.graph.state import AgentState
from app.database.manager import DatabaseManager
from langchain_core.messages import HumanMessage, AIMessage


@pytest.fixture(scope="function")
def db_manager():
    """Create a DatabaseManager instance for testing."""
    return DatabaseManager()


@pytest.fixture(scope="function")
def test_phone_numbers():
    """Generate unique test phone numbers for each test."""
    import random
    base = "+9198765" + f"{random.randint(10000, 99999):05d}"
    return {
        "primary": base,
        "secondary": base[:-1] + str((int(base[-1]) + 1) % 10),
    }


@pytest.fixture
def base_state():
    """Create a base AgentState for testing."""
    return {
        "messages": [HumanMessage(content="Hello")],
        "current_intent": "appointment_booking",
        "conversation_history": [],
        "appointment_details": {},
        "user_profile": {},
        "user_context_loaded": False,
        "caller_mobile_number": "",
        "user_id": 0,
        "needs_name_enrichment": False
    }


class TestNewUserFlow:
    """Test suite for new user scenarios."""
    
    def test_new_user_creation(self, base_state, test_phone_numbers, db_manager):
        """Test that a new user is created when phone number is not found."""
        phone = test_phone_numbers["primary"]
        state = base_state.copy()
        state["caller_mobile_number"] = phone
        
        # Run the node
        result = user_context_loading_node(state)
        
        # Assertions
        assert result["user_context_loaded"] is True
        assert result["user_id"] > 0
        assert result["needs_name_enrichment"] is True  # New user needs name
        assert result["user_profile"]["mobile_number"] == phone
        assert result["user_profile"]["name"] is None  # New user has no name
        
        # Verify user was actually created in database
        user_data = db_manager.get_user_by_mobile_number(phone)
        assert user_data is not None
        assert user_data["user_id"] == result["user_id"]
    
    def test_new_user_profile_structure(self, base_state, test_phone_numbers):
        """Test that the user profile has the correct structure for new users."""
        phone = test_phone_numbers["primary"]
        state = base_state.copy()
        state["caller_mobile_number"] = phone
        
        result = user_context_loading_node(state)
        
        # Check profile structure
        profile = result["user_profile"]
        assert "user_id" in profile
        assert "name" in profile
        assert "mobile_number" in profile
        assert "email" in profile
        assert "appointment_history" in profile  # Fixed: use appointment_history
        
        # New user should have empty appointments
        assert isinstance(profile["appointment_history"], list)
        assert len(profile["appointment_history"]) == 0


class TestExistingUserFlow:
    """Test suite for existing user scenarios."""
    
    def test_existing_user_with_name(self, base_state, test_phone_numbers, db_manager):
        """Test loading an existing user who has a name."""
        phone = test_phone_numbers["primary"]
        
        # Create user first
        create_result = db_manager.create_user_with_phone(phone, "Existing User")
        assert create_result["success"]
        
        # Run the node
        state = base_state.copy()
        state["caller_mobile_number"] = phone
        result = user_context_loading_node(state)
        
        # Assertions
        assert result["user_context_loaded"] is True
        assert result["user_id"] == create_result["user_id"]
        assert result["needs_name_enrichment"] is False  # Has name, no enrichment needed
        assert result["user_profile"]["name"] == "Existing User"
        assert result["user_profile"]["mobile_number"] == phone
    
    def test_existing_user_without_name(self, base_state, test_phone_numbers, db_manager):
        """Test loading an existing user who doesn't have a name (progressive enrichment)."""
        phone = test_phone_numbers["primary"]
        
        # Create user without name
        create_result = db_manager.create_user_with_phone(phone, name=None)
        assert create_result["success"]
        
        # Run the node
        state = base_state.copy()
        state["caller_mobile_number"] = phone
        result = user_context_loading_node(state)
        
        # Assertions
        assert result["user_context_loaded"] is True
        assert result["user_id"] == create_result["user_id"]
        assert result["needs_name_enrichment"] is True  # No name, needs enrichment
        assert result["user_profile"]["name"] is None
    
    def test_user_profile_includes_appointment_history(self, base_state, test_phone_numbers, db_manager):
        """Test that user profile includes appointment history."""
        phone = test_phone_numbers["primary"]
        
        # Create user
        create_result = db_manager.create_user_with_phone(phone, "Test User")
        assert create_result["success"]
        
        # Run the node
        state = base_state.copy()
        state["caller_mobile_number"] = phone
        result = user_context_loading_node(state)
        
        # Check that appointment_history is included (even if empty)
        assert "appointment_history" in result["user_profile"]
        assert isinstance(result["user_profile"]["appointment_history"], list)


class TestEdgeCases:
    """Test suite for edge cases and error scenarios."""
    
    def test_empty_phone_number(self, base_state):
        """Test handling of empty phone number."""
        state = base_state.copy()
        state["caller_mobile_number"] = ""
        
        result = user_context_loading_node(state)
        
        # Should handle gracefully
        assert result["user_context_loaded"] is False
        assert result["user_profile"] == {}
        assert result["user_id"] == 0
    
    def test_missing_phone_number_field(self, base_state):
        """Test handling when caller_mobile_number field is missing."""
        state = base_state.copy()
        # Don't set caller_mobile_number
        
        result = user_context_loading_node(state)
        
        # Should handle gracefully
        assert result["user_context_loaded"] is False
        assert result["user_profile"] == {}
    
    def test_state_preservation(self, base_state, test_phone_numbers):
        """Test that other state fields are preserved."""
        phone = test_phone_numbers["primary"]
        state = base_state.copy()
        state["caller_mobile_number"] = phone
        state["current_intent"] = "appointment_booking"
        
        result = user_context_loading_node(state)
        
        # Original state should be preserved (node only returns updates)
        # The actual state merging happens in LangGraph
        assert "user_context_loaded" in result
        assert "user_profile" in result
        assert "user_id" in result
        assert "needs_name_enrichment" in result


class TestUserIdPopulation:
    """Test suite for user_id field population."""
    
    def test_user_id_set_for_new_user(self, base_state, test_phone_numbers):
        """Test that user_id is set when creating a new user."""
        phone = test_phone_numbers["primary"]
        state = base_state.copy()
        state["caller_mobile_number"] = phone
        
        result = user_context_loading_node(state)
        
        assert result["user_id"] > 0
        assert result["user_profile"]["user_id"] == result["user_id"]
    
    def test_user_id_set_for_existing_user(self, base_state, test_phone_numbers, db_manager):
        """Test that user_id is set when loading an existing user."""
        phone = test_phone_numbers["primary"]
        
        # Create user first
        create_result = db_manager.create_user_with_phone(phone, "Test User")
        expected_user_id = create_result["user_id"]
        
        # Run the node
        state = base_state.copy()
        state["caller_mobile_number"] = phone
        result = user_context_loading_node(state)
        
        assert result["user_id"] == expected_user_id
        assert result["user_profile"]["user_id"] == expected_user_id


class TestNameEnrichmentFlag:
    """Test suite for needs_name_enrichment flag logic."""
    
    def test_flag_true_for_new_user(self, base_state, test_phone_numbers):
        """Test that needs_name_enrichment is True for new users."""
        phone = test_phone_numbers["primary"]
        state = base_state.copy()
        state["caller_mobile_number"] = phone
        
        result = user_context_loading_node(state)
        
        assert result["needs_name_enrichment"] is True
    
    def test_flag_true_for_user_without_name(self, base_state, test_phone_numbers, db_manager):
        """Test that needs_name_enrichment is True for users without names."""
        phone = test_phone_numbers["primary"]
        
        # Create user without name
        db_manager.create_user_with_phone(phone, name=None)
        
        state = base_state.copy()
        state["caller_mobile_number"] = phone
        result = user_context_loading_node(state)
        
        assert result["needs_name_enrichment"] is True
    
    def test_flag_false_for_user_with_name(self, base_state, test_phone_numbers, db_manager):
        """Test that needs_name_enrichment is False for users with names."""
        phone = test_phone_numbers["primary"]
        
        # Create user with name
        db_manager.create_user_with_phone(phone, "Complete User")
        
        state = base_state.copy()
        state["caller_mobile_number"] = phone
        result = user_context_loading_node(state)
        
        assert result["needs_name_enrichment"] is False
    
    def test_flag_false_on_error(self, base_state):
        """Test that needs_name_enrichment is False when there's an error."""
        state = base_state.copy()
        state["caller_mobile_number"] = ""  # Invalid phone
        
        result = user_context_loading_node(state)
        
        assert result["needs_name_enrichment"] is False


class TestIntegrationScenarios:
    """Integration tests for complete user context loading flows."""
    
    def test_complete_new_user_flow(self, base_state, test_phone_numbers, db_manager):
        """Test complete flow for a brand new user."""
        phone = test_phone_numbers["primary"]
        
        # Ensure user doesn't exist
        existing = db_manager.get_user_by_mobile_number(phone)
        assert existing is None
        
        # Run the node
        state = base_state.copy()
        state["caller_mobile_number"] = phone
        result = user_context_loading_node(state)
        
        # Verify complete flow
        assert result["user_context_loaded"] is True
        assert result["user_id"] > 0
        assert result["needs_name_enrichment"] is True
        assert result["user_profile"]["name"] is None
        assert result["user_profile"]["mobile_number"] == phone
        assert len(result["user_profile"]["appointment_history"]) == 0  # Fixed
        
        # Verify in database
        user_in_db = db_manager.get_user_by_mobile_number(phone)
        assert user_in_db is not None
        assert user_in_db["user_id"] == result["user_id"]
    
    def test_complete_existing_user_flow(self, base_state, test_phone_numbers, db_manager):
        """Test complete flow for an existing user with full profile."""
        phone = test_phone_numbers["primary"]
        
        # Create user with complete profile
        create_result = db_manager.create_user_with_phone(phone, "John Doe")
        
        # Run the node
        state = base_state.copy()
        state["caller_mobile_number"] = phone
        result = user_context_loading_node(state)
        
        # Verify complete flow
        assert result["user_context_loaded"] is True
        assert result["user_id"] == create_result["user_id"]
        assert result["needs_name_enrichment"] is False
        assert result["user_profile"]["name"] == "John Doe"
        assert result["user_profile"]["mobile_number"] == phone


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
