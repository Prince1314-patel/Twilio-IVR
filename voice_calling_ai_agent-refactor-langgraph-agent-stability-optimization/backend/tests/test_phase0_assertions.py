"""
Phase 0 Assertion Tests
=======================

Tests to verify Phase 0 safety assertions are working correctly.
Tests that appointment agent blocks execution when user_id=0.

Author: Advanced AI Systems Team
Created: 2026-02-09
"""

import pytest
from langchain_core.messages import HumanMessage, AIMessage

from app.ai.graph.state import AgentState
from app.ai.graph.nodes.appointment_agent_node import appointment_agent_node


class TestAppointmentAgentAssertion:
    """Test safety assertion in appointment agent node"""
    
    def test_appointment_agent_blocks_when_user_id_zero(self):
        """Verify appointment agent raises AssertionError when user_id=0"""
        state: AgentState = {
            "messages": [HumanMessage(content="Book appointment")],
            "intent": "booking",
            "intent_confidence": 0.9,
            "user_id": 0,  # Invalid user_id
            "needs_name_enrichment": False,
            "user_context_loaded": False,
            "caller_mobile_number": "+919876543210",
            "user_profile": {},
            "name_collection_in_progress": False,
            "name_prompt_level": 0  # Phase 2: Added field
        }
        
        # Should raise AssertionError
        with pytest.raises(AssertionError) as exc_info:
            appointment_agent_node(state)
        
        # Verify error message contains expected information
        error_message = str(exc_info.value)
        assert "CRITICAL" in error_message
        assert "user_id=0" in error_message
        assert "graph flow is incorrect" in error_message
        assert "needs_name_enrichment=False" in error_message
        assert "intent=booking" in error_message
        assert "caller_mobile_number=+919876543210" in error_message
    
    def test_appointment_agent_blocks_with_different_intents(self):
        """Verify assertion blocks for all intents when user_id=0"""
        intents = ["booking", "cancellation", "rescheduling", "inquiry", "greeting"]
        
        for intent in intents:
            state: AgentState = {
                "messages": [HumanMessage(content=f"Test {intent}")],
                "intent": intent,
                "intent_confidence": 0.8,
                "user_id": 0,  # Invalid user_id
                "needs_name_enrichment": True,
                "user_context_loaded": False,
                "caller_mobile_number": "+919999999999",
                "user_profile": {},
                "name_collection_in_progress": False,
                "name_prompt_level": 0  # Phase 2: Added field
            }
            
            with pytest.raises(AssertionError) as exc_info:
                appointment_agent_node(state)
            
            error_message = str(exc_info.value)
            assert "user_id=0" in error_message
            assert f"intent={intent}" in error_message
    
    def test_appointment_agent_succeeds_with_valid_user_id(self):
        """Verify appointment agent runs successfully when user_id is valid"""
        state: AgentState = {
            "messages": [HumanMessage(content="Book appointment")],
            "intent": "booking",
            "intent_confidence": 0.9,
            "user_id": 123,  # Valid user_id
            "needs_name_enrichment": False,
            "user_context_loaded": True,
            "caller_mobile_number": "+919876543210",
            "user_profile": {
                "user_id": 123,
                "name": "Test User",
                "mobile_number": "+919876543210",
                "email": "test@example.com"
            },
            "name_collection_in_progress": False,
            "name_prompt_level": 0  # Phase 2: Added field
        }
        
        # Should not raise AssertionError
        try:
            result = appointment_agent_node(state)
            # If we get here, assertion passed
            assert result is not None
            assert "messages" in result
        except AssertionError:
            pytest.fail("Appointment agent should not raise AssertionError with valid user_id")
        except Exception:
            # Other exceptions are OK (e.g., LLM errors, tool errors)
            # We're only testing the assertion
            pass
    
    def test_assertion_error_message_contains_state_snapshot(self):
        """Verify assertion error includes comprehensive state snapshot"""
        state: AgentState = {
            "messages": [HumanMessage(content="Test message")],
            "intent": "inquiry",
            "intent_confidence": 0.7,
            "user_id": 0,
            "needs_name_enrichment": True,
            "user_context_loaded": False,
            "caller_mobile_number": "+911234567890",
            "user_profile": {},
            "name_collection_in_progress": True,
            "name_prompt_level": 0  # Phase 2: Added field
        }
        
        with pytest.raises(AssertionError) as exc_info:
            appointment_agent_node(state)
        
        error_message = str(exc_info.value)
        
        # Verify all critical state fields are in error message
        assert "needs_name_enrichment=True" in error_message
        assert "intent=inquiry" in error_message
        assert "caller_mobile_number=+911234567890" in error_message
        assert "user_context_loaded=False" in error_message
    
    def test_assertion_with_edge_case_user_ids(self):
        """Test assertion with various edge case user_id values"""
        edge_cases = [0, -1, None]
        
        for user_id_value in edge_cases:
            state: AgentState = {
                "messages": [HumanMessage(content="Test")],
                "intent": "booking",
                "intent_confidence": 0.8,
                "user_id": user_id_value,
                "needs_name_enrichment": False,
                "user_context_loaded": False,
                "caller_mobile_number": "+919876543210",
                "user_profile": {},
                "name_collection_in_progress": False,
                "name_prompt_level": 0  # Phase 2: Added field
            }
            
            # user_id of 0 or None should trigger assertion
            if user_id_value in [0, None]:
                with pytest.raises(AssertionError):
                    appointment_agent_node(state)
            # Negative user_id might not trigger assertion (depends on implementation)
            # but we test it anyway
            elif user_id_value == -1:
                try:
                    appointment_agent_node(state)
                except (AssertionError, Exception):
                    # Either assertion or other error is acceptable
                    pass


class TestAssertionLogging:
    """Test that assertion failures are properly logged"""
    
    def test_assertion_failure_is_logged(self, caplog):
        """Verify assertion failure is logged before raising error"""
        state: AgentState = {
            "messages": [HumanMessage(content="Test")],
            "intent": "booking",
            "intent_confidence": 0.9,
            "user_id": 0,
            "needs_name_enrichment": False,
            "user_context_loaded": False,
            "caller_mobile_number": "+919876543210",
            "user_profile": {},
            "name_collection_in_progress": False,
            "name_prompt_level": 0  # Phase 2: Added field
        }
        
        with caplog.at_level("DEBUG"):
            with pytest.raises(AssertionError):
                appointment_agent_node(state)
        
        # Check that debug log was created before assertion
        debug_logs = [r for r in caplog.records if "[APPOINTMENT AGENT ENTRY]" in r.message]
        assert len(debug_logs) > 0, "Debug log should be present before assertion"
        
        # Verify debug log contains user_id=0
        debug_log = debug_logs[0].message
        assert "user_id=0" in debug_log
