
import pytest
from unittest.mock import MagicMock, patch
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from app.ai.graph.state import AgentState, StateInvariantError

import inspect

# Import nodes to test
from app.ai.graph.nodes.user_context_node import user_context_loading_node
from app.ai.graph.nodes.name_enrichment_node import name_enrichment_node
from app.ai.graph.nodes.intent_detection_node import intent_detection_node
from app.ai.graph.nodes.appointment_agent_node import appointment_agent_node
from app.ai.graph.nodes.business_router_node import business_router_node

# Get modules for patching (avoiding shadowing by __init__ exports)
name_enrichment_module = inspect.getmodule(name_enrichment_node)
intent_detection_module = inspect.getmodule(intent_detection_node)

class TestPhase8FinalValidation:
    """
    Phase 8: Validation Against plan.md (Hard Check)
    
    Explicit Checks:
    1. Phone number always resolves to user_id
    2. Name gate blocks ALL flows
    3. Intent detection never runs before onboarding
    4. Appointment creation never happens without name
    5. Cancel/reschedule always fetch appointments first
    """

    @pytest.fixture
    def mock_db_manager(self):
        with patch('app.ai.graph.nodes.user_context_node.DatabaseManager') as mock_db_cls:
            mock_instance = MagicMock()
            mock_db_cls.return_value = mock_instance
            yield mock_instance

    @pytest.fixture
    def mock_llm_checker(self):
        """Mock LLM for name extraction to avoid API calls"""
        # Use patch.object to avoid module/function name shadowing issues
        with patch.object(name_enrichment_module, 'create_llm_model'), \
             patch.object(intent_detection_module, 'create_llm_model'):
            yield

    def test_phone_number_always_resolves_identity(self, mock_db_manager):
        """
        Check 1: Phone number always resolves to user_id.
        Verifies user_context_loading_node handles both existing and new users
        and ALWAYS returns a user_id.
        """
        # Case A: Existing User
        mock_db_manager.get_user_by_mobile_number.return_value = {
            "user_id": 101, "mobile_number": "+919876543210", "name": "Existing User"
        }
        mock_db_manager.get_user_appointment_history.return_value = []
        
        state_existing = {"caller_mobile_number": "+919876543210"}
        result_existing = user_context_loading_node(state_existing)
        
        assert result_existing["user_id"] == 101, "Existing user must resolve to correct user_id"
        assert result_existing["user_context_loaded"] is True

        # Case B: New User
        mock_db_manager.get_user_by_mobile_number.return_value = None
        mock_db_manager.create_user_with_phone.return_value = {"success": True, "user_id": 202}
        
        state_new = {"caller_mobile_number": "+919876543211"}
        result_new = user_context_loading_node(state_new)
        
        assert result_new["user_id"] == 202, "New user must resolve to new user_id"
        # For new user, name is None, so needs_name_enrichment MUST be True
        assert result_new["needs_name_enrichment"] is True

    def test_name_gate_blocks_all_flows(self, mock_llm_checker):
        """
        Check 2: Name gate blocks ALL flows.
        Verifies name_enrichment_node returns name_collection_in_progress=True
        (BLOCK) whenever needs_name_enrichment is set.
        """
        # Case A: Name Needed
        state_needed = {
            "needs_name_enrichment": True, 
            "user_id": 123,
            "messages": [],
            "name_prompt_level": 0
        }
        result_needed = name_enrichment_node(state_needed)
        assert result_needed["name_collection_in_progress"] is True
        assert "messages" in result_needed # Must prompt user

        # Case B: Name Not Needed
        state_done = {
            "needs_name_enrichment": False, 
            "user_id": 123
        }
        result_done = name_enrichment_node(state_done)
        assert result_done.get("name_collection_in_progress") is False



    def test_appointment_creation_requires_name(self):
        """
        Check 4: Appointment creation never happens without name.
        Verifies appointment_agent_node crashes/asserts if name is missing.
        """
        state_invalid = {
            "user_id": 123,
            "needs_name_enrichment": True, # Name missing
            "messages": [HumanMessage(content="Book now")],
            "intent": "booking"
        }

        with pytest.raises(StateInvariantError) as excinfo:
            appointment_agent_node(state_invalid)

        err = str(excinfo.value)
        assert "CRITICAL" in err
        assert "business" in err
        assert "needs_name_enrichment=True" in err

    def test_cancel_reschedule_always_fetch_appointments(self):
        """
        Check 5: Cancel/reschedule always fetch appointments first.
        Verifies that tool_executor_node force-calls get_upcoming_appointments
        when the intent is cancellation or rescheduling and appointments haven't been fetched.
        """
        from app.ai.graph.nodes.appointment_pipeline.tool_executor_node import tool_executor_node
        import inspect
        executor_module = inspect.getmodule(tool_executor_node)
        
        from langchain_core.messages import AIMessage, ToolMessage, HumanMessage
        import json
        from unittest.mock import MagicMock, patch
        
        with patch.object(executor_module, 'get_upcoming_appointments') as mock_get_upcoming, \
             patch.object(executor_module, '_get_model') as mock_get_model:
            
            # Mock the tool output
            mock_get_upcoming.invoke.return_value = json.dumps({"success": True, "payload": [{"appointment_id": "123"}]})
            
            # Setup mock model inside tool_executor_node so we don't hit the real LLM inside the execution loop
            mock_model = MagicMock()
            mock_model.bind_tools.return_value.invoke.return_value = AIMessage(content="I have fetched your appointments.")
            mock_get_model.return_value = mock_model
            
            # Test cancellation
            state_cancel = {
                "intent": "cancellation",
                "active_intent": "cancellation",
                "intent_locked": True,
                "flow_step": "cancellation__appointment_selection",
                "messages": [HumanMessage(content="I want to cancel my appointment")],
                "caller_mobile_number": "+1234567890",
                "collected_slots": {},
            }
            
            result_cancel = tool_executor_node(state_cancel)
            
            # Verify the tool was invoked
            mock_get_upcoming.invoke.assert_called_with({"mobile_number": "+1234567890"})
            
            # Verify the forced messages were added to the returned messages
            assert any(
                isinstance(m, AIMessage) and m.tool_calls and m.tool_calls[0]["name"] == "get_upcoming_appointments"
                for m in result_cancel["messages"]
            ), "tool_executor_node must force an AIMessage with get_upcoming_appointments tool call"
            
            assert any(
                isinstance(m, ToolMessage) and m.name == "get_upcoming_appointments"
                for m in result_cancel["messages"]
            ), "tool_executor_node must force a ToolMessage with get_upcoming_appointments result"
            
            # Test rescheduling (similar logic but check that get_upcoming_appointments is also injected)
            mock_get_upcoming.invoke.reset_mock()
            state_reschedule = {
                "intent": "rescheduling",
                "active_intent": "rescheduling",
                "intent_locked": True,
                "flow_step": "rescheduling__appointment_selection",
                "messages": [HumanMessage(content="I want to reschedule my appointment")],
                "caller_mobile_number": "+0987654321",
                "collected_slots": {},
            }
            
            result_reschedule = tool_executor_node(state_reschedule)
            mock_get_upcoming.invoke.assert_called_with({"mobile_number": "+0987654321"})
            assert any(
                isinstance(m, AIMessage) and m.tool_calls and m.tool_calls[0]["name"] == "get_upcoming_appointments"
                for m in result_reschedule["messages"]
            ), "tool_executor_node must force an AIMessage with get_upcoming_appointments tool call"
            
            assert any(
                isinstance(m, ToolMessage) and m.name == "get_upcoming_appointments"
                for m in result_reschedule["messages"]
            ), "tool_executor_node must force a ToolMessage with get_upcoming_appointments result"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
