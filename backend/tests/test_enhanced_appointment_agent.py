"""
Enhanced Appointment Agent Tests
===============================

Unit tests for the enhanced appointment agent with intent-specific behavior.
Tests intent-specific prompt selection, confidence-based workflow decisions,
and specialized conversation flows.

Author: Advanced AI Systems Team
Last Modified: 2026-02-03
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
import sys
import app.ai.graph.nodes.appointment_agent_node
import app.ai.graph.nodes.appointment_pipeline.tool_executor_node  # ensure module is loaded
# Retrieve module reliably from sys.modules to avoid potential package attribute shadowing
agent_node_module = sys.modules['app.ai.graph.nodes.appointment_agent_node']
# Get the actual MODULE object (not the function re-exported from __init__.py)
tool_executor_module = sys.modules['app.ai.graph.nodes.appointment_pipeline.tool_executor_node']

from app.ai.graph.state import AgentState
from app.ai.prompts.appointment_prompts import (
    get_intent_specific_prompt,
    should_use_direct_flow,
    get_clarification_prompt,
    BOOKING_FOCUSED_PROMPT,
    CANCELLATION_FOCUSED_PROMPT,
    RESCHEDULING_FOCUSED_PROMPT,
    INQUIRY_FOCUSED_PROMPT,
    GREETING_FOCUSED_PROMPT,
    OUT_OF_SCOPE_FOCUSED_PROMPT,
    GENERAL_AGENT_PROMPT
)


class TestIntentSpecificPromptSelection(unittest.TestCase):
    """Test intent-specific prompt selection functionality."""
    
    def test_high_confidence_booking_prompt(self):
        """Test that high confidence booking intent returns booking-focused prompt."""
        prompt = get_intent_specific_prompt("booking", 0.9)
        self.assertEqual(prompt, BOOKING_FOCUSED_PROMPT)
    
    def test_high_confidence_cancellation_prompt(self):
        """Test that high confidence cancellation intent returns cancellation-focused prompt."""
        prompt = get_intent_specific_prompt("cancellation", 0.85)
        self.assertEqual(prompt, CANCELLATION_FOCUSED_PROMPT)
    
    def test_high_confidence_rescheduling_prompt(self):
        """Test that high confidence rescheduling intent returns rescheduling-focused prompt."""
        prompt = get_intent_specific_prompt("rescheduling", 0.95)
        self.assertEqual(prompt, RESCHEDULING_FOCUSED_PROMPT)
    
    def test_high_confidence_inquiry_prompt(self):
        """Test that high confidence inquiry intent returns inquiry-focused prompt."""
        prompt = get_intent_specific_prompt("inquiry", 0.82)
        self.assertEqual(prompt, INQUIRY_FOCUSED_PROMPT)
    
    def test_high_confidence_greeting_prompt(self):
        """Test that high confidence greeting intent returns greeting-focused prompt."""
        prompt = get_intent_specific_prompt("greeting", 0.88)
        self.assertEqual(prompt, GREETING_FOCUSED_PROMPT)
    
    def test_high_confidence_out_of_scope_prompt(self):
        """Test that high confidence out_of_scope intent returns out-of-scope-focused prompt."""
        prompt = get_intent_specific_prompt("out_of_scope", 0.92)
        self.assertEqual(prompt, OUT_OF_SCOPE_FOCUSED_PROMPT)
    
    def test_low_confidence_returns_general_prompt(self):
        """Test that low confidence intents return general prompt."""
        prompt = get_intent_specific_prompt("booking", 0.65)
        self.assertEqual(prompt, GENERAL_AGENT_PROMPT)
        
        prompt = get_intent_specific_prompt("cancellation", 0.6)
        self.assertEqual(prompt, GENERAL_AGENT_PROMPT)
    
    def test_unknown_intent_returns_general_prompt(self):
        """Test that unknown intents return general prompt."""
        prompt = get_intent_specific_prompt("unknown_intent", 0.9)
        self.assertEqual(prompt, GENERAL_AGENT_PROMPT)


class TestConfidenceBasedWorkflowDecisions(unittest.TestCase):
    """Test confidence-based workflow decision functionality."""
    
    def test_high_confidence_booking_uses_direct_flow(self):
        """Test that high confidence booking intent uses direct flow."""
        self.assertTrue(should_use_direct_flow("booking", 0.9))
        self.assertTrue(should_use_direct_flow("booking", 0.85))
    
    def test_low_confidence_booking_uses_clarification_flow(self):
        """Test that low confidence booking intent uses clarification flow."""
        self.assertFalse(should_use_direct_flow("booking", 0.7))
        self.assertFalse(should_use_direct_flow("booking", 0.5))
    
    def test_high_confidence_cancellation_uses_direct_flow(self):
        """Test that high confidence cancellation intent uses direct flow."""
        self.assertTrue(should_use_direct_flow("cancellation", 0.9))
        self.assertTrue(should_use_direct_flow("cancellation", 0.82))
    
    def test_high_confidence_rescheduling_uses_direct_flow(self):
        """Test that high confidence rescheduling intent uses direct flow."""
        self.assertTrue(should_use_direct_flow("rescheduling", 0.95))
        self.assertTrue(should_use_direct_flow("rescheduling", 0.81))
    
    def test_other_intents_use_clarification_flow(self):
        """Test that other intents use clarification flow regardless of confidence."""
        self.assertFalse(should_use_direct_flow("inquiry", 0.9))
        self.assertFalse(should_use_direct_flow("greeting", 0.95))
        self.assertFalse(should_use_direct_flow("out_of_scope", 0.88))
    
    def test_low_confidence_uses_clarification_flow(self):
        """Test that low confidence intents use clarification flow."""
        self.assertFalse(should_use_direct_flow("booking", 0.6))
        self.assertFalse(should_use_direct_flow("cancellation", 0.5))
        self.assertFalse(should_use_direct_flow("rescheduling", 0.4))


class TestClarificationPrompts(unittest.TestCase):
    """Test clarification prompt generation for low confidence intents."""
    
    def test_very_low_confidence_returns_clarification_prompt(self):
        """Test that very low confidence returns clarification prompt."""
        prompt = get_clarification_prompt("booking", 0.4)
        self.assertIn("NOTE: User intent is unclear", prompt)
    
    def test_medium_confidence_returns_intent_specific_prompt(self):
        """Test that clarification prompt function appends note."""
        prompt = get_clarification_prompt("booking", 0.7)
        self.assertIn("NOTE: User intent is unclear", prompt)
    
    def test_high_confidence_returns_intent_specific_prompt(self):
        """Test that clarification prompt function appends note even for high conf if called."""
        prompt = get_clarification_prompt("booking", 0.9)
        self.assertIn("NOTE: User intent is unclear", prompt)


class TestEnhancedAppointmentAgentNode(unittest.TestCase):
    """Test the enhanced appointment agent node with intent-specific behavior."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_state = {
            "messages": [
                SystemMessage(content="Current time: 2026-02-03 10:00:00"),
                HumanMessage(content="I want to book an appointment")
            ],
            "intent": "booking",
            "intent_confidence": 0.9,
            "user_id": 123,
            "user_profile": {"name": "Test User", "mobile_number": "+1234567890"},
            "needs_name_enrichment": False
        }

    def _make_mock_model(self, response_content="I'll help you book an appointment."):
        """Return a mock that satisfies model.bind_tools().invoke()."""
        mock_response = AIMessage(content=response_content)
        mock_response.tool_calls = []  # No tool calls → loop exits cleanly
        mock_bound = MagicMock()
        mock_bound.invoke.return_value = mock_response
        mock_model = MagicMock()
        mock_model.bind_tools.return_value = mock_bound
        return mock_model, mock_bound

    def test_intent_specific_agent_creation(self):
        """Test that the node selects the correct intent-specific prompt."""
        # The current implementation selects prompts via get_intent_specific_prompt().
        # High-confidence booking should use BOOKING_FOCUSED_PROMPT.
        prompt = get_intent_specific_prompt("booking", 0.9)
        self.assertEqual(prompt, BOOKING_FOCUSED_PROMPT)
        # General prompt is used below threshold
        prompt = get_intent_specific_prompt("booking", 0.5)
        self.assertEqual(prompt, GENERAL_AGENT_PROMPT)

    @patch.object(tool_executor_module, 'model')
    def test_appointment_agent_node_uses_intent_information(self, mock_model):
        """Test that appointment agent node uses intent information from state."""
        from app.ai.graph.nodes.appointment_agent_node import appointment_agent_node

        mock_model_inst, mock_bound = self._make_mock_model()
        mock_model.bind_tools.return_value = mock_bound

        result = appointment_agent_node(self.test_state)

        # Verify result contains messages
        self.assertIn("messages", result)
        self.assertGreater(len(result["messages"]), 0)

    @patch.object(tool_executor_module, 'model')
    def test_appointment_agent_node_handles_missing_intent(self, mock_model):
        """Test that appointment agent node handles missing intent gracefully."""
        from app.ai.graph.nodes.appointment_agent_node import appointment_agent_node

        mock_model_inst, mock_bound = self._make_mock_model("How can I help you today?")
        mock_model.bind_tools.return_value = mock_bound

        state_without_intent = {
            "messages": [HumanMessage(content="Hello")],
            "user_id": 123,
            "user_profile": {"name": "Test User", "mobile_number": "+1234567890"},
            "needs_name_enrichment": False
        }

        result = appointment_agent_node(state_without_intent)

        self.assertIn("messages", result)
        self.assertGreater(len(result["messages"]), 0)

    @patch.object(tool_executor_module, 'model')
    def test_appointment_agent_node_adds_intent_context(self, mock_model):
        """Test that appointment agent node injects ACTIVE INTENT into the system prompt."""
        from app.ai.graph.nodes.appointment_agent_node import appointment_agent_node

        captured_messages = []

        def capture_invoke(messages):
            captured_messages.extend(messages)
            response = AIMessage(content="I'll help you book.")
            response.tool_calls = []
            return response

        mock_bound = MagicMock()
        mock_bound.invoke.side_effect = capture_invoke
        mock_model.bind_tools.return_value = mock_bound

        appointment_agent_node(self.test_state)

        # The system message should contain ACTIVE INTENT
        system_contents = [
            m.content for m in captured_messages if isinstance(m, SystemMessage)
        ]
        combined = " ".join(system_contents)
        self.assertIn("ACTIVE INTENT", combined, "ACTIVE INTENT should be injected into system messages")
        self.assertIn("booking", combined.lower())

    @patch.object(tool_executor_module, 'model')
    def test_appointment_agent_node_error_handling(self, mock_model):
        """Test that appointment agent node handles LLM errors gracefully."""
        from app.ai.graph.nodes.appointment_agent_node import appointment_agent_node

        # Make model.bind_tools().invoke() raise an exception
        mock_bound = MagicMock()
        mock_bound.invoke.side_effect = Exception("LLM connection failed")
        mock_model.bind_tools.return_value = mock_bound

        result = appointment_agent_node(self.test_state)

        # Verify graceful error message is returned
        self.assertIn("messages", result)
        self.assertGreater(len(result["messages"]), 0)
        self.assertIsInstance(result["messages"][0], AIMessage)
        # Node returns an apology message on LLM failure, not an 'error' keyword
        content = result["messages"][0].content.lower()
        self.assertTrue(
            "apologize" in content or "trouble" in content or "sorry" in content,
            f"Expected apology/error message, got: {content}"
        )



class TestSpecializedConversationFlows(unittest.TestCase):
    """Test specialized conversation flows for different intents."""
    
    
    def test_booking_prompt_contains_booking_specific_content(self):
        """Test that booking prompt contains booking-specific guidance."""
        self.assertIn("INTENT: BOOKING", BOOKING_FOCUSED_PROMPT)
        self.assertIn("STEP 1: Call `check_appointment_availability`", BOOKING_FOCUSED_PROMPT)
        self.assertIn("DO NOT HALLUCINATE AVAILABILITY", BOOKING_FOCUSED_PROMPT)
    
    def test_cancellation_prompt_contains_cancellation_specific_content(self):
        """Test that cancellation prompt contains cancellation-specific guidance."""
        self.assertIn("INTENT: CANCELLATION", CANCELLATION_FOCUSED_PROMPT)
        self.assertIn("STEP 1: Call `get_upcoming_appointments` IMMEDIATELY", CANCELLATION_FOCUSED_PROMPT)
        self.assertIn("DO NOT INVENT APPOINTMENTS", CANCELLATION_FOCUSED_PROMPT)
    
    def test_rescheduling_prompt_contains_rescheduling_specific_content(self):
        """Test that rescheduling prompt contains rescheduling-specific guidance."""
        self.assertIn("INTENT: RESCHEDULING", RESCHEDULING_FOCUSED_PROMPT)
        self.assertIn("STEP 1: Call `get_upcoming_appointments` IMMEDIATELY", RESCHEDULING_FOCUSED_PROMPT)
        self.assertIn("DO NOT INVENT APPOINTMENTS", RESCHEDULING_FOCUSED_PROMPT)
    
    def test_inquiry_prompt_contains_inquiry_specific_content(self):
        """Test that inquiry prompt contains inquiry-specific guidance."""
        self.assertIn("INTENT: INQUIRY", INQUIRY_FOCUSED_PROMPT)
        self.assertIn("REDIRECTION SCRIPT", INQUIRY_FOCUSED_PROMPT)
    
    def test_greeting_prompt_contains_greeting_specific_content(self):
        """Test that greeting prompt contains greeting-specific guidance."""
        self.assertIn("INTENT: GREETING", GREETING_FOCUSED_PROMPT)
        self.assertIn("warmly", GREETING_FOCUSED_PROMPT)
    
    def test_out_of_scope_prompt_contains_redirect_content(self):
        """Test that out-of-scope prompt contains redirect guidance."""
        self.assertIn("INTENT: OUT OF SCOPE", OUT_OF_SCOPE_FOCUSED_PROMPT)
        self.assertIn("only handle appointments", OUT_OF_SCOPE_FOCUSED_PROMPT)


if __name__ == '__main__':
    unittest.main()