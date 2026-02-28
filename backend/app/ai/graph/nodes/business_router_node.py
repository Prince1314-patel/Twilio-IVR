"""
Business Router Node
====================

LangGraph node for routing confirmed intents to the appropriate handler.
This node acts as the traffic controller between intent detection and business logic.

Author: Advanced AI Systems Team
Last Modified: 2026-02-09
"""

from typing import Literal

from app.ai.graph.state import AgentState, validate_state_invariants
from app.core.logger_config import get_ai_agent_logger

logger = get_ai_agent_logger()

"""
MENTAL MODEL (Phase 5):
-----------------------
ROLE: Traffic Controller
Input: Validated Identity + Detected Intent
Output: Next Node to Execute

ASSUMPTIONS:
- User identity is fully resolved (user_id != 0)
- Name enrichment is complete (needs_name_enrichment = False)
- Intent has been classified (intent exists in state)

ROUTING LOGIC:
- Intent: booking -> appointment_agent
- Intent: cancellation -> appointment_agent (Future: cancellation_agent)
- Intent: rescheduling -> appointment_agent (Future: rescheduling_agent)
- Intent: inquiry -> appointment_agent (Future: inquiry_agent)
- ... others -> appointment_agent
"""


def business_router_node(state: AgentState) -> dict:
    """
    Route execution based on detected intent.
    
    This node does NOT modify state, it only makes a routing decision.
    Currently, all routes lead to appointment_agent, but this strict separation
    allow us to split the monolithic agent in future phases.
    
    Args:
        state: Current agent state with intent information
        
    Returns:
        Empty dict (state not modified, purely for routing edge)
    """

    # Phase 7: Centralized state validation
    validate_state_invariants(state, "business")
    
    user_id = state.get("user_id", 0)
    # needs_name_enrichment is not needed for logic, but might be used in logging or asserts if I kept them. 
    # But I am removing asserts. 
    # The logger uses user_id. 
    # The logger in lines 73-76 uses user_id.
    
    # Log valid entry
    intent = state.get("intent", "unknown")
    confidence = state.get("intent_confidence", 0.0)
    
    logger.info(
        f"[BUSINESS ROUTER] Routing intent '{intent}' (confidence: {confidence:.2f}) "
        f"for user_id={user_id}"
    )
    
    # Return nothing - the conditional edge logic handles the actual routing
    # based on the state we validated here.
    return {}


def route_by_intent(state: AgentState) -> Literal["appointment_agent"]:
    """
    Conditional edge function to determine the next node based on intent.
    
    Args:
        state: Current agent state
        
    Returns:
        Name of the next node to execute
    """
    # Prioritize active_intent (Phase 5+ Transactional Logic)
    active_intent = state.get("active_intent")
    
    if active_intent:
        intent = active_intent
        source = "active_intent"
    else:
        intent = state.get("intent", "inquiry")
        source = "latest_intent"
    
    # Future-proofing: Explicit routing map
    # Currently all map to appointment_agent, but ready for splitting
    
    if intent == "booking":
        destination = "appointment_agent"
    elif intent == "cancellation":
        destination = "appointment_agent"  # Future: cancellation_agent
    elif intent == "rescheduling":
        destination = "appointment_agent"  # Future: rescheduling_agent
    elif intent == "inquiry":
        destination = "appointment_agent"  # Future: inquiry_agent
    elif intent == "greeting":
        destination = "appointment_agent"  # Future: greeting_agent/response
    else:
        # Fallback / out_of_scope
        destination = "appointment_agent"
        
    logger.debug(f"[BUSINESS ROUTER DECISION] Source: {source}, Intent '{intent}' -> {destination}")
    return destination
