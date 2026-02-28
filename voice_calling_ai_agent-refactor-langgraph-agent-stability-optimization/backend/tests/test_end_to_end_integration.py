"""
End-to-End Integration Test for Enhanced Appointment Agent
==========================================================

Integration test simulating the flow from intent detection to appointment agent.

Author: Advanced AI Systems Team
Last Modified: 2026-02-03
"""

import pytest
from unittest.mock import patch, MagicMock
from langchain_core.messages import HumanMessage, SystemMessage

from app.ai.graph.nodes.intent_detection_node import intent_detection_node
from app.ai.graph.nodes.appointment_agent_node import appointment_agent_node
from app.ai.intent.classifier import IntentCategory
    
import sys
import importlib

# Get actual modules
if "app.ai.graph.nodes.intent_detection_node" in sys.modules:
    intent_module = sys.modules["app.ai.graph.nodes.intent_detection_node"]
else:
    intent_module = importlib.import_module("app.ai.graph.nodes.intent_detection_node")

if "app.ai.graph.nodes.appointment_agent_node" in sys.modules:
    agent_module = sys.modules["app.ai.graph.nodes.appointment_agent_node"]
else:
    agent_module = importlib.import_module("app.ai.graph.nodes.appointment_agent_node")

class TestEndToEndFlow:
    
    def test_booking_flow_integration(self):
        """
        Test the flow: Message -> Intent Detection -> Appointment Agent (Booking)
        """
        # 1. Setup Mock for Intent Detection
        with patch.object(intent_module, "classify_intent_sync") as mock_classify, \
             patch.object(agent_module, "create_react_agent") as mock_create_agent:
            
            # Configure Intent Mock
            mock_classify.return_value = (IntentCategory.BOOKING, 0.95)
            
            # Configure Agent Mock
            mock_agent_instance = MagicMock()
            mock_create_agent.return_value = mock_agent_instance
            mock_agent_instance.invoke.return_value = {
                "messages": [
                    HumanMessage(content="I want to book"),
                    SystemMessage(content="context"), # Node adds this
                    MagicMock(content="What is your name?")  # Agent response
                ]
            }
            
            # 2. Initial State
            initial_state = {
                "messages": [HumanMessage(content="I want to book an appointment")]
            }
            
            # 3. Run Intent Detection Node
            state_after_intent = intent_detection_node(initial_state)
            
            # Verify State Update
            assert state_after_intent["intent"] == IntentCategory.BOOKING
            assert state_after_intent["intent_confidence"] == 0.95
            
            # Merge updates (simulating LangGraph behavior)
            current_state = {**initial_state, **state_after_intent}
            
            # 4. Run Appointment Agent Node
            final_result = appointment_agent_node(current_state)
            
            # 5. Verify Prompt Selection logic was triggered correctly
            args, kwargs = mock_create_agent.call_args
            prompt_used = kwargs.get("prompt")
            
            # Should use high-confidence booking prompt + direct instruction
            # Check for specific text from the BOOKING_FOCUSED_PROMPT
            assert "intent to BOOK a new appointment" in prompt_used
            # We check for the critical instruction added by direct flow
            assert "CRITICAL INSTRUCTION" in prompt_used
            
            # Verify final output
            assert len(final_result["messages"]) == 1
            assert "What is your name?" in str(final_result["messages"][0].content)

    def test_clarification_flow_integration(self):
        """
        Test the flow: Message -> Intent Detection (Low Conf) -> Appointment Agent (Clarification)
        """
        with patch.object(intent_module, "classify_intent_sync") as mock_classify, \
             patch.object(agent_module, "create_react_agent") as mock_create_agent:
            
            # Configure Intent Mock (Low Confidence)
            mock_classify.return_value = (IntentCategory.INQUIRY, 0.45)
             
            # Configure Agent Mock
            mock_agent_instance = MagicMock()
            mock_create_agent.return_value = mock_agent_instance
            mock_agent_instance.invoke.return_value = {
                "messages": [
                    HumanMessage(content="help me"),
                    MagicMock(content="Do you want to book or cancel?")
                ]
            }
            
            state = {
                "messages": [HumanMessage(content="help me")]
            }
            
            # Run Intent Node
            intent_result = intent_detection_node(state)
            assert intent_result["intent_confidence"] == 0.45
            
            state.update(intent_result)
            
            # Run Agent Node
            appointment_agent_node(state)
            
            # Verify Clarification Prompt used
            args, kwargs = mock_create_agent.call_args
            prompt_used = kwargs.get("prompt")
            assert "Ask clarifying questions" in prompt_used
