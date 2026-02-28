"""
Phase 5 Verification Tests: Business Router
===========================================

Tests to verify:
1. Business Router Phase 4 safety assertions (blocks if identity/name missing)
2. Routing logic correctly maps intents to destinations
3. Fallback behavior for unknown intents

Author: Advanced AI Systems Team
Created: 2026-02-09
"""

import pytest
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

from app.ai.graph.nodes.business_router_node import business_router_node, route_by_intent
from app.ai.graph.state import StateInvariantError


@pytest.fixture
def valid_state():
    """State with valid identity and booking intent."""
    return {
        "user_id": 123,
        "needs_name_enrichment": False,
        "intent": "booking",
        "intent_confidence": 0.95
    }


@pytest.fixture
def invalid_identity_state():
    """State with invalid identity."""
    return {
        "user_id": 0,
        "needs_name_enrichment": False,
        "intent": "booking"
    }


@pytest.fixture
def name_needed_state():
    """State where name enrichment is still needed."""
    return {
        "user_id": 123,
        "needs_name_enrichment": True,
        "intent": "booking"
    }


class TestBusinessRouterAssertions:
    """Verify Phase 4 safety checks in business router."""

    def test_blocks_invalid_identity(self, invalid_identity_state):
        with pytest.raises(StateInvariantError) as exc:
            business_router_node(invalid_identity_state)
        assert "user_id=0" in str(exc.value)

    def test_blocks_name_needed(self, name_needed_state):
        with pytest.raises(StateInvariantError) as exc:
            business_router_node(name_needed_state)
        assert "needs_name_enrichment=True" in str(exc.value)

    def test_passes_valid_state(self, valid_state):
        try:
            result = business_router_node(valid_state)
            assert result == {}  # Should return empty dict
        except StateInvariantError:
            pytest.fail("Business router blocked valid state")


class TestRoutingLogic:
    """Verify conditional edge logic."""

    @pytest.mark.parametrize("intent,expected_destination", [
        ("booking", "appointment_agent"),
        ("cancellation", "appointment_agent"),
        ("rescheduling", "appointment_agent"),
        ("inquiry", "appointment_agent"),
        ("greeting", "appointment_agent"),
        ("out_of_scope", "appointment_agent"),
        ("unknown_weird_intent", "appointment_agent"),  # Fallback
    ])
    def test_route_by_intent(self, intent, expected_destination):
        state = {"intent": intent}
        destination = route_by_intent(state)
        assert destination == expected_destination

    def test_route_default_missing_intent(self):
        """Verify fallback when intent field is missing."""
        state = {}  # No intent field
        destination = route_by_intent(state)
        assert destination == "appointment_agent"  # Default fallback
