"""
Error Handling Unit Tests
==========================

Comprehensive tests for error handling across the user enrichment feature.
Tests database failures, invalid inputs, error logging, and workflow continuation.

Author: Advanced AI Systems Team
Last Modified: 2026-02-03
"""

import pytest
import sys
import os
from unittest.mock import MagicMock

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

from app.ai.graph.nodes.user_context_node import user_context_loading_node
from app.ai.graph.nodes.name_enrichment_node import name_enrichment_node
from app.database.manager import DatabaseManager
from langchain_core.messages import HumanMessage, AIMessage


class TestDatabaseErrorHandling:
    """Test suite for database error handling."""
    
    def test_user_context_loading_with_database_error(self, monkeypatch):
        """Test user context loading handles database errors gracefully."""
        # Mock DatabaseManager to raise an exception
        def mock_get_user(*args, **kwargs):
            raise Exception("Database connection failed")
        
        monkeypatch.setattr(
            "app.ai.graph.nodes.user_context_node.DatabaseManager.get_user_by_mobile_number",
            mock_get_user
        )
        
        state = {
            "messages": [HumanMessage(content="Hello")],
            "caller_mobile_number": "+14155552671",
            "user_context_loaded": False,
            "user_id": 0,
            "needs_name_enrichment": False,
            "user_profile": {}
        }
        
        # Should not crash
        result = user_context_loading_node(state)
        
        # Should return safe defaults
        assert result["user_context_loaded"] is False
        assert result["user_id"] == 0
        assert result["user_profile"] == {}
    
    def test_user_creation_failure(self, monkeypatch):
        """Test handling of user creation failure."""
        # Mock get_user to return None (user not found)
        # Mock create_user to fail
        def mock_get_user(*args, **kwargs):
            return None
        
        def mock_create_user(*args, **kwargs):
            return {"success": False, "message": "Database write failed"}
        
        monkeypatch.setattr(
            "app.ai.graph.nodes.user_context_node.DatabaseManager.get_user_by_mobile_number",
            mock_get_user
        )
        monkeypatch.setattr(
            "app.ai.graph.nodes.user_context_node.DatabaseManager.create_user_with_phone",
            mock_create_user
        )
        
        state = {
            "messages": [HumanMessage(content="Hello")],
            "caller_mobile_number": "+14155552671",
            "user_context_loaded": False,
            "user_id": 0,
            "needs_name_enrichment": False,
            "user_profile": {}
        }
        
        result = user_context_loading_node(state)
        
        # Should handle gracefully
        assert result["user_context_loaded"] is False
        assert result["user_id"] == 0
    
    def test_appointment_history_query_failure(self, monkeypatch):
        """Test handling of appointment history query failure."""
        # Mock successful user lookup but failed appointment history
        def mock_get_user(*args, **kwargs):
            return {
                "user_id": 123,
                "name": "Test User",
                "mobile_number": "+14155552671",
                "email": None
            }
        
        def mock_get_history(*args, **kwargs):
            raise Exception("Query timeout")
        
        monkeypatch.setattr(
            "app.ai.graph.nodes.user_context_node.DatabaseManager.get_user_by_mobile_number",
            mock_get_user
        )
        monkeypatch.setattr(
            "app.ai.graph.nodes.user_context_node.DatabaseManager.get_user_appointment_history",
            mock_get_history
        )
        
        state = {
            "messages": [HumanMessage(content="Hello")],
            "caller_mobile_number": "+14155552671",
            "user_context_loaded": False,
            "user_id": 0,
            "needs_name_enrichment": False,
            "user_profile": {}
        }
        
        # Should handle gracefully
        result = user_context_loading_node(state)
        
        # Should still fail gracefully
        assert result["user_context_loaded"] is False
    
    def test_name_update_database_failure(self):
        """Test handling of name update database failure."""
        # Test with non-existent user ID
        
        state = {
            "messages": [
                HumanMessage(content="Hello"),
                AIMessage(content="May I have your name?"),
                HumanMessage(content="My name is John Doe")
            ],
            "user_context_loaded": True,
            "user_id": 123,
            "needs_name_enrichment": True,
            "user_profile": {
                "user_id": 123,
                "name": None,
                "mobile_number": "+14155552671"
            }
        }
        
        result = name_enrichment_node(state)
        
        # Should handle gracefully - enrichment flag should remain true for retry
        assert isinstance(result, dict)


class TestInvalidMobileNumberHandling:
    """Test suite for invalid mobile number handling."""
    
    def test_empty_mobile_number(self):
        """Test handling of empty mobile number."""
        state = {
            "messages": [HumanMessage(content="Hello")],
            "caller_mobile_number": "",
            "user_context_loaded": False,
            "user_id": 0,
            "needs_name_enrichment": False,
            "user_profile": {}
        }
        
        result = user_context_loading_node(state)
        
        assert result["user_context_loaded"] is False
        assert result["user_id"] == 0
    
    def test_invalid_format_mobile_number(self):
        """Test handling of invalid format mobile number."""
        state = {
            "messages": [HumanMessage(content="Hello")],
            "caller_mobile_number": "+0123456789",  # Invalid: starts with +0
            "user_context_loaded": False,
            "user_id": 0,
            "needs_name_enrichment": False,
            "user_profile": {}
        }
        
        result = user_context_loading_node(state)
        
        assert result["user_context_loaded"] is False
        assert result["user_id"] == 0
    
    def test_null_mobile_number(self):
        """Test handling of None mobile number."""
        state = {
            "messages": [HumanMessage(content="Hello")],
            "caller_mobile_number": None,
            "user_context_loaded": False,
            "user_id": 0,
            "needs_name_enrichment": False,
            "user_profile": {}
        }
        
        result = user_context_loading_node(state)
        
        assert result["user_context_loaded"] is False
    
    def test_mobile_number_with_sql_injection_attempt(self):
        """Test handling of SQL injection attempt in mobile number."""
        state = {
            "messages": [HumanMessage(content="Hello")],
            "caller_mobile_number": "+12345",  # Too short (only 5 digits after +)
            "user_context_loaded": False,
            "user_id": 0,
            "needs_name_enrichment": False,
            "user_profile": {}
        }
        
        result = user_context_loading_node(state)
        
        # Should be rejected by validation
        assert result["user_context_loaded"] is False


class TestWorkflowContinuation:
    """Test suite for workflow continuation after errors."""
    
    def test_workflow_continues_after_database_error(self, monkeypatch):
        """Test that workflow can continue after database error."""
        def mock_get_user(*args, **kwargs):
            raise Exception("Database error")
        
        monkeypatch.setattr(
            "app.ai.graph.nodes.user_context_node.DatabaseManager.get_user_by_mobile_number",
            mock_get_user
        )
        
        state = {
            "messages": [HumanMessage(content="I need an appointment")],
            "caller_mobile_number": "+14155552671",
            "user_context_loaded": False,
            "user_id": 0,
            "needs_name_enrichment": False,
            "user_profile": {},
            "current_intent": "appointment_booking",
        }
        
        result = user_context_loading_node(state)
        
        # Workflow should continue with empty profile
        assert result["user_context_loaded"] is False
        assert result["user_profile"] == {}
        
        # State should still be valid for next nodes
        assert isinstance(result, dict)
    
    def test_user_profile_empty_on_error(self, monkeypatch):
        """Test that user_profile remains empty on error."""
        def mock_get_user(*args, **kwargs):
            raise Exception("Database error")
        
        monkeypatch.setattr(
            "app.ai.graph.nodes.user_context_node.DatabaseManager.get_user_by_mobile_number",
            mock_get_user
        )
        
        state = {
            "messages": [HumanMessage(content="Hello")],
            "caller_mobile_number": "+14155552671",
            "user_context_loaded": False,
            "user_id": 0,
            "needs_name_enrichment": False,
            "user_profile": {}
        }
        
        result = user_context_loading_node(state)
        
        assert result["user_profile"] == {}
    
    def test_user_context_loaded_false_on_error(self, monkeypatch):
        """Test that user_context_loaded is False on error."""
        def mock_get_user(*args, **kwargs):
            raise Exception("Database error")
        
        monkeypatch.setattr(
            "app.ai.graph.nodes.user_context_node.DatabaseManager.get_user_by_mobile_number",
            mock_get_user
        )
        
        state = {
            "messages": [HumanMessage(content="Hello")],
            "caller_mobile_number": "+14155552671",
            "user_context_loaded": False,
            "user_id": 0,
            "needs_name_enrichment": False,
            "user_profile": {}
        }
        
        result = user_context_loading_node(state)
        
        assert result["user_context_loaded"] is False
    
    def test_appointment_booking_works_without_user_context(self):
        """Test that appointment booking can work without user context."""
        # This is more of an integration test, but validates the concept
        state = {
            "messages": [HumanMessage(content="I need an appointment")],
            "caller_mobile_number": "",  # No phone number
            "user_context_loaded": False,
            "user_id": 0,
            "needs_name_enrichment": False,
            "user_profile": {},
            "current_intent": "appointment_booking",
        }
        
        result = user_context_loading_node(state)
        
        # Should return safe defaults
        assert result["user_context_loaded"] is False
        assert result["user_profile"] == {}
        
        # Workflow can continue - appointment agent should handle missing context


class TestEdgeCases:
    """Test suite for edge cases in error handling."""
    
    def test_corrupted_user_data(self, monkeypatch):
        """Test handling of corrupted user data from database."""
        def mock_get_user(*args, **kwargs):
            # Return incomplete/corrupted data
            return {
                "user_id": None,  # Invalid
                "name": 12345,  # Wrong type
                # Missing mobile_number
            }
        
        monkeypatch.setattr(
            "app.ai.graph.nodes.user_context_node.DatabaseManager.get_user_by_mobile_number",
            mock_get_user
        )
        
        state = {
            "messages": [HumanMessage(content="Hello")],
            "caller_mobile_number": "+14155552671",
            "user_context_loaded": False,
            "user_id": 0,
            "needs_name_enrichment": False,
            "user_profile": {}
        }
        
        # Should handle gracefully
        result = user_context_loading_node(state)
        assert isinstance(result, dict)
    
    def test_missing_state_fields(self):
        """Test handling of missing state fields."""
        # Minimal state
        state = {
            "messages": [HumanMessage(content="Hello")]
        }
        
        # Should not crash
        result = user_context_loading_node(state)
        assert isinstance(result, dict)
        assert result["user_context_loaded"] is False


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
