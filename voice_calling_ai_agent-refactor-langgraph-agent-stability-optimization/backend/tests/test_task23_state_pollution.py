"""
Task #23 — Fix ``collected_slots["flow_step"]`` state pollution
================================================================

Tests that verify the INVARIANT:

    ``collected_slots`` MUST contain ONLY user-provided slot data.

Specifically:
- ``valid_appointment_ids`` must NOT appear in ``collected_slots``
- ``valid_appointments`` must NOT appear in ``collected_slots``
- ``flow_step`` must NOT appear in ``collected_slots``
- All three are returned as dedicated top-level state fields by
  ``tool_executor_node`` and forwarded by ``appointment_agent_node``.

Author: Advanced AI Systems Team
Last Modified: 2026-02-26
"""

import json
import sys
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage


# ---------------------------------------------------------------------------
# Module references resolved at import time to avoid package-level shadowing.
# The package __init__.py re-exports the *function*, so we must obtain the
# actual *module* via importlib / sys.modules.
# ---------------------------------------------------------------------------

import importlib

# Force-import the sub-module (not the re-exported function from __init__)
_te_module = importlib.import_module(
    "app.ai.graph.nodes.appointment_pipeline.tool_executor_node"
)
_tool_executor_node_fn = _te_module.tool_executor_node


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_cancellation_state() -> dict:
    """Return a minimal state suitable for a cancellation turn."""
    return {
        "messages": [HumanMessage(content="Cancel my appointment")],
        "intent": "cancellation",
        "intent_confidence": 0.95,
        "active_intent": "cancellation",
        "intent_locked": True,
        "flow_step": "cancellation__appointment_id",
        "flow_completed": False,
        "collected_slots": {},
        # Task #23 — these live at the top level, not in collected_slots
        "valid_appointment_ids": [],
        "valid_appointments": [],
        "caller_mobile_number": "9999999999",
        "user_id": 1,
        "needs_name_enrichment": False,
        "safety_conflict_count": 0,
    }


def _make_pure_text_model():
    """Return a mock model whose LLM response has NO tool calls."""
    ai_msg = AIMessage(content="Let me look up your appointments.")
    ai_msg.tool_calls = []
    bound = MagicMock()
    bound.invoke.return_value = ai_msg
    model_mock = MagicMock()
    model_mock.bind_tools.return_value = bound
    return model_mock


_BANNED_KEYS = frozenset({"valid_appointment_ids", "valid_appointments", "flow_step"})


def _assert_collected_slots_clean(result: dict):
    slots = result.get("collected_slots", {})
    pollution = _BANNED_KEYS & set(slots.keys())
    assert not pollution, (
        f"collected_slots must NOT contain control-state keys; found: {pollution}. "
        f"Full collected_slots: {slots}"
    )


def _assert_top_level_ids_present(result: dict):
    assert "valid_appointment_ids" in result, (
        "tool_executor_node must return 'valid_appointment_ids' at the top level."
    )
    assert "valid_appointments" in result, (
        "tool_executor_node must return 'valid_appointments' at the top level."
    )


# ===========================================================================
# Test: AgentState schema declares valid_appointment_ids / valid_appointments
# ===========================================================================

class TestStateSchemaDeclaresSeparateVerificationFields:
    """AgentState must have valid_appointment_ids / valid_appointments at top level."""

    def test_agent_state_has_valid_appointment_ids_field(self):
        from app.ai.graph.state import BusinessState
        all_keys: set = set()
        for cls in BusinessState.__mro__:
            all_keys.update(getattr(cls, "__annotations__", {}).keys())
        assert "valid_appointment_ids" in all_keys, (
            "BusinessState must declare 'valid_appointment_ids' as a top-level field "
            "(task #23 — no longer stored inside collected_slots)."
        )

    def test_agent_state_has_valid_appointments_field(self):
        from app.ai.graph.state import BusinessState
        all_keys: set = set()
        for cls in BusinessState.__mro__:
            all_keys.update(getattr(cls, "__annotations__", {}).keys())
        assert "valid_appointments" in all_keys, (
            "BusinessState must declare 'valid_appointments' as a top-level field "
            "(task #23 — no longer stored inside collected_slots)."
        )


# ===========================================================================
# Test: tool_executor_node never writes control keys into collected_slots
# ===========================================================================

class TestToolExecutorCollectedSlotsInvariant:
    """tool_executor_node must keep collected_slots free of control-state keys."""

    def test_force_tool_does_not_pollute_collected_slots(self):
        """Force-call of get_upcoming_appointments must never write into collected_slots."""
        appts = [{"appointment_id": 7, "date": "2026-03-01", "time": "10:00"}]
        raw = json.dumps({"success": True, "payload": appts})

        mock_get_upcoming = MagicMock()
        mock_get_upcoming.invoke.return_value = raw

        model_mock = _make_pure_text_model()
        state = _make_cancellation_state()

        with (
            patch.object(_te_module, "get_upcoming_appointments", mock_get_upcoming),
            patch.object(_te_module, "model", model_mock),
        ):
            result = _tool_executor_node_fn(state)

        _assert_collected_slots_clean(result)
        _assert_top_level_ids_present(result)

        # Verification data must be at the top level
        assert result["valid_appointment_ids"] == [7], (
            "valid_appointment_ids should be [7] after force-fetching one appointment."
        )
        assert result["valid_appointments"] == appts

    def test_post_execution_id_resolution_uses_top_level_vars(self):
        """
        When verification data is already loaded from a previous turn, the node
        must read it from top-level state and NOT from collected_slots.
        """
        appts = [{"appointment_id": 99, "date": "2026-04-01", "time": "14:00"}]

        # Inject a prior ToolMessage so the force-call block is skipped
        pre_tool_msg = ToolMessage(
            content="already fetched",
            tool_call_id="tc0",
            name="get_upcoming_appointments",
        )

        ai_msg = AIMessage(content="I found one appointment.")
        ai_msg.tool_calls = []
        bound = MagicMock()
        bound.invoke.return_value = ai_msg
        model_mock = MagicMock()
        model_mock.bind_tools.return_value = bound

        state = _make_cancellation_state()
        state["messages"] = [
            HumanMessage(content="Cancel my appointment"),
            pre_tool_msg,
        ]
        # Verification metadata was loaded in the previous turn at the top level
        state["valid_appointment_ids"] = [99]
        state["valid_appointments"] = appts

        with patch.object(_te_module, "model", model_mock):
            result = _tool_executor_node_fn(state)

        _assert_collected_slots_clean(result)
        _assert_top_level_ids_present(result)

    def test_inquiry_short_circuit_returns_clean_collected_slots(self):
        """Inquiry short-circuit must not add any control keys to collected_slots."""
        state = {
            "messages": [HumanMessage(content="What are your hours?")],
            "intent": "inquiry",
            "intent_confidence": 0.9,
            "active_intent": "inquiry",
            "intent_locked": False,
            "flow_step": None,
            "flow_completed": False,
            "collected_slots": {},
            "valid_appointment_ids": [],
            "valid_appointments": [],
            "caller_mobile_number": "9999999999",
            "user_id": 1,
            "needs_name_enrichment": False,
            "safety_conflict_count": 0,
        }

        result = _tool_executor_node_fn(state)

        _assert_collected_slots_clean(result)
        # Top-level fields must be present (passed through)
        assert "valid_appointment_ids" in result
        assert "valid_appointments" in result

    def test_transaction_completion_resets_verification_metadata(self):
        """On a successful destructive tool call, verification metadata is cleared."""
        appts = [{"appointment_id": 7, "date": "2026-03-01", "time": "10:00"}]
        raw_appts = json.dumps({"success": True, "payload": appts})
        raw_cancel = json.dumps({"success": True, "payload": {"message": "Cancelled."}})

        # LLM will call cancel_appointment_in_db on turn 1
        cancel_tool_call = {
            "name": "cancel_appointment_in_db",
            "args": {"appointment_id": 7, "reason": "Out of town"},
            "id": "tc_cancel",
        }
        ai_with_tool = AIMessage(content="")
        ai_with_tool.tool_calls = [cancel_tool_call]

        ai_final = AIMessage(content="Your appointment has been cancelled.")
        ai_final.tool_calls = []

        bound = MagicMock()
        bound.invoke.side_effect = [ai_with_tool, ai_final]
        model_mock = MagicMock()
        model_mock.bind_tools.return_value = bound

        # The executor calls via _tool_map[name].invoke(), so patch the map entry.
        mock_cancel_fn = MagicMock()
        mock_cancel_fn.invoke.return_value = raw_cancel

        state = _make_cancellation_state()
        # Simulate that the appointment was already verified (top-level, not in slots)
        state["valid_appointment_ids"] = [7]
        state["valid_appointments"] = appts
        state["collected_slots"] = {
            "appointment_id": 7,
            "reason": "Out of town",
            "confirmed": "confirmed",
        }
        # Inject a prior ToolMessage so the force-call block is skipped
        pre_tool_msg = ToolMessage(
            content=raw_appts,
            tool_call_id="tc0",
            name="get_upcoming_appointments",
        )
        state["messages"] = [
            HumanMessage(content="Yes, cancel it."),
            pre_tool_msg,
        ]
        state["flow_step"] = "cancellation__confirmation"

        with (
            patch.object(_te_module, "model", model_mock),
            patch.dict(_te_module._tool_map, {"cancel_appointment_in_db": mock_cancel_fn}),
        ):
            result = _tool_executor_node_fn(state)

        # After a successful commit, verification metadata should be reset to empty lists
        assert result["valid_appointment_ids"] == []
        assert result["valid_appointments"] == []
        # And collected_slots should also be empty (flow reset)
        assert result.get("collected_slots") == {}
        _assert_collected_slots_clean(result)


# ===========================================================================
# Test: appointment_agent_node forwards verification fields at the top level
# ===========================================================================

class TestAppointmentAgentNodeForwardsVerificationFields:
    """appointment_agent_node must surface valid_appointment_ids / valid_appointments."""

    def test_orchestrator_returns_top_level_verification_fields(self):
        """The orchestrator's return dict must include the top-level verification metadata."""
        from app.ai.graph.nodes.appointment_agent_node import appointment_agent_node

        appts = [{"appointment_id": 55, "date": "2026-05-01", "time": "09:00"}]
        raw = json.dumps({"success": True, "payload": appts})

        mock_get_upcoming = MagicMock()
        mock_get_upcoming.invoke.return_value = raw
        model_mock = _make_pure_text_model()
        state = _make_cancellation_state()

        with (
            patch.object(_te_module, "get_upcoming_appointments", mock_get_upcoming),
            patch.object(_te_module, "model", model_mock),
        ):
            result = appointment_agent_node(state)

        assert "valid_appointment_ids" in result, (
            "appointment_agent_node must return 'valid_appointment_ids' as a top-level key."
        )
        assert "valid_appointments" in result, (
            "appointment_agent_node must return 'valid_appointments' as a top-level key."
        )

        # collected_slots must be clean
        _assert_collected_slots_clean(result)
