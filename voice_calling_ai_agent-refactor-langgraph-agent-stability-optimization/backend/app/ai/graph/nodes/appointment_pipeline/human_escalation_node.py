"""
Human Escalation Node
=====================

**Responsibility**: Emit a deterministic escalation message when safety limits are exceeded.

This node is triggered by `appointment_agent_node` when repeated safety conflicts
or validation failures occur during execution.

Author: Advanced AI Systems Team
Last Modified: 2026-02-26
"""

from langchain_core.messages import AIMessage
from app.ai.graph.state import AgentState
from app.core.logger_config import get_ai_agent_logger
from app.core.metrics import record_escalation

logger = get_ai_agent_logger()

_ESCALATION_MESSAGE = (
    "I'm sorry, but I'm having trouble processing your request securely right now. "
    "I'm escalating this to a human operator who will assist you shortly."
)

def human_escalation_node(state: AgentState) -> dict:
    """Trigger the deterministic escalation path."""
    safety_conflicts = state.get("safety_conflict_count", 0)
    validation_failures = state.get("validation_failure_count", 0)
    
    logger.critical(
        "[HUMAN ESCALATION] Route triggered. safety_conflicts=%d, validation_failures=%d",
        safety_conflicts,
        validation_failures
    )
    
    # Determine escalation reason
    if safety_conflicts >= 2:
        reason = "safety_conflicts"
    elif validation_failures >= 2:
        reason = "validation_failures"
    else:
        reason = "unknown"
    
    # Record escalation metric
    record_escalation(
        reason=reason,
        user_id=state.get("user_id"),
        session_id=state.get("session_id"),
        safety_conflict_count=safety_conflicts,
        validation_failure_count=validation_failures,
        active_intent=state.get("active_intent"),
        flow_step=state.get("flow_step")
    )
    
    return {
        "messages": [AIMessage(content=_ESCALATION_MESSAGE)],
        "escalation_triggered": True,
        # Clear out transactional intent to stop looping
        "flow_completed": True,
        "active_intent": None,
        "intent_locked": False,
        "conversation_mode": "idle"
    }

