import pytest
from langchain_core.messages import AIMessage

from app.ai.graph.nodes.appointment_pipeline.flow_planner_node import flow_planner_node
from app.ai.graph.nodes.appointment_pipeline.response_generator_node import response_generator_node

def test_greeting_short_circuit():
    """Test that a greeting intent triggers the greeting deterministic response."""
    # 1. Flow Planner
    state = {
        "user_id": 123,
        "needs_name_enrichment": False,
        "intent": "greeting",
        "intent_confidence": 0.9,
        "intent_locked": False,
        "messages": [],
    }
    
    planner_result = flow_planner_node(state)
    assert planner_result.get("_planner_greeting_short_circuit") is True
    assert planner_result.get("_planner_inquiry_short_circuit") is False
    assert planner_result.get("_planner_out_of_scope_short_circuit") is False
    
    # 2. Response Generator
    state_for_response = {"_planner_greeting_short_circuit": True}
    response = response_generator_node(state_for_response)
    
    assert "messages" in response
    assert len(response["messages"]) == 1
    assert isinstance(response["messages"][0], AIMessage)
    assert "Hello! Welcome to the clinic's voice assistant" in response["messages"][0].content


def test_out_of_scope_short_circuit():
    """Test that an out_of_scope intent triggers the out_of_scope deterministic response."""
    # 1. Flow Planner
    state = {
        "user_id": 123,
        "needs_name_enrichment": False,
        "intent": "out_of_scope",
        "intent_confidence": 0.9,
        "intent_locked": False,
        "messages": [],
    }
    
    planner_result = flow_planner_node(state)
    assert planner_result.get("_planner_out_of_scope_short_circuit") is True
    assert planner_result.get("_planner_inquiry_short_circuit") is False
    assert planner_result.get("_planner_greeting_short_circuit") is False
    
    # 2. Response Generator
    state_for_response = {"_planner_out_of_scope_short_circuit": True}
    response = response_generator_node(state_for_response)
    
    assert "messages" in response
    assert len(response["messages"]) == 1
    assert isinstance(response["messages"][0], AIMessage)
    assert "booking, canceling, or rescheduling appointments" in response["messages"][0].content
