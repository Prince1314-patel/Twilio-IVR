"""
Verification Tests for Phase 3: Name Enrichment as a True Gate
==============================================================

Tests to verify:
1. NameGate strict blocking (returns name_collection_in_progress=True)
2. NameGate strict passing (returns name_collection_in_progress=False)
3. Appointment Agent pure business logic (no onboarding greeting)

Author: Advanced AI Systems Team
Last Modified: 2026-02-09
"""

import pytest
import sys
import os
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

from app.ai.graph.nodes.name_enrichment_node import name_enrichment_node
# Import module to avoid shadowing by function in __init__
from app.ai.graph.nodes import appointment_agent_node as agent_module_object
from app.ai.graph.nodes.appointment_agent_node import appointment_agent_node
import app.ai.graph.nodes.appointment_pipeline.tool_executor_node  # ensure module is loaded
import sys
# Get the actual MODULE object (not the function re-exported by __init__.py)
tool_executor_module = sys.modules['app.ai.graph.nodes.appointment_pipeline.tool_executor_node']
pass
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

@pytest.fixture
def base_state_no_name():
    """State for a user without a name (needs enrichment)."""
    return {
        "messages": [HumanMessage(content="Hello")],
        "user_id": 123,
        "caller_mobile_number": "+15550001234",
        "needs_name_enrichment": True,
        "user_profile": {"user_id": 123, "name": None},
        "name_collection_in_progress": False
    }

@pytest.fixture
def base_state_with_name():
    """State for a user with a name (no enrichment needed)."""
    return {
        "messages": [HumanMessage(content="Book appointment")],
        "user_id": 456,
        "caller_mobile_number": "+15550005678",
        "needs_name_enrichment": False,
        "user_profile": {"user_id": 456, "name": "Test User"},
        "name_collection_in_progress": False,
        "intent": "appointment_booking",
        "intent_confidence": 0.95
    }

class TestNameGateLogic:
    """Verify NameGate (name_enrichment_node) strict blocking/passing."""

    def test_name_gate_blocks_new_user(self, base_state_no_name):
        """Verify NameGate blocks and asks for name when needs_enrichment is True."""
        result = name_enrichment_node(base_state_no_name)
        
        # Must return blocking signal
        assert result.get("name_collection_in_progress") is True
        # Must return a message asking for name
        assert "messages" in result
        assert len(result["messages"]) == 1
        assert "name" in result["messages"][0].content.lower()

    def test_name_gate_passes_existing_user(self, base_state_with_name):
        """Verify NameGate passes when needs_enrichment is False."""
        result = name_enrichment_node(base_state_with_name)
        
        # Must return passing signal - strictly False or empty dict in legacy, but we enforced False
        # Our update made it return {"name_collection_in_progress": False}
        assert result == {"name_collection_in_progress": False} or result == {}

class TestAppointmentAgentPureLogic:
    """Verify Appointment Agent removed greeting logic."""

    def test_appointment_agent_no_greeting(self, base_state_with_name):
        """Verify agent does NOT prepend a 'Hello [Name]' instruction even if name was just collected."""

        module_name = 'app.ai.graph.nodes.appointment_agent_node'
        if module_name not in sys.modules:
            import importlib
            importlib.import_module(module_name)

        real_module = sys.modules[module_name]

        captured_messages = []

        def fake_invoke(messages):
            captured_messages.extend(messages)
            response = AIMessage(content="Sure, I can help.")
            response.tool_calls = []
            return response

        mock_bound = MagicMock()
        mock_bound.invoke.side_effect = fake_invoke
        mock_model = MagicMock()
        mock_model.bind_tools.return_value = mock_bound

        with patch.object(tool_executor_module, "model", mock_model):
            state = base_state_with_name.copy()
            state["messages"] = [
                AIMessage(content="May I have your name?"),
                HumanMessage(content="Test User")
            ]

            result = appointment_agent_node(state)

        # Verify NO SystemMessage with "GREETING INSTRUCTION"
        has_greeting_instruction = any(
            isinstance(m, SystemMessage) and "GREETING INSTRUCTION" in m.content
            for m in captured_messages
        )

        assert not has_greeting_instruction, "Appointment Agent should NOT add greeting instruction in Phase 3"


