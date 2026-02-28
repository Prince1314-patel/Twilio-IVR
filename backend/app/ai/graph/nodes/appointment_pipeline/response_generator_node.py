"""
Response Generator Node
========================

**Responsibility**: Emit the final, validated AIMessage to the conversation
history.

This node's job is intentionally minimal:

1. Take ``_validator_clean_content`` (the text approved by the validator).
2. For the INQUIRY short-circuit path (``_planner_inquiry_short_circuit=True``),
   emit the deterministic redirect response instead.
3. Wrap the text in ``AIMessage`` and return it via ``messages``.

The LLM is NOT called again in this node — all generation happened inside
``tool_executor_node``.  The validator already cleaned the content.
This node is a pure data-formatting step.

Outputs written to state
------------------------
- ``messages`` — list containing exactly one ``AIMessage``

The node does NOT emit the private ``_validator_clean_content`` or
``_executor_*`` or ``_planner_*`` fields back to state — those are
ephemeral cross-node signals and should stay out of the persistent
LangGraph checkpoint.

Author: Advanced AI Systems Team
Last Modified: 2026-02-25
"""

from langchain_core.messages import AIMessage

from app.ai.graph.state import AgentState
from app.core.logger_config import get_ai_agent_logger

logger = get_ai_agent_logger()

_INQUIRY_REDIRECT = (
    "I'm sorry, I'm not able to provide that information right now "
    "as it's not within my knowledge base. "
    "However, if you have any inquiries or need assistance with an appointment, "
    "feel free to ask — I'm happy to help you book, cancel, or reschedule."
)

_GREETING_REDIRECT = (
    "Hello! Welcome to the clinic's voice assistant. "
    "I can help you book, cancel, or reschedule an appointment. "
    "How can I help you today?"
)

_OUT_OF_SCOPE_REDIRECT = (
    "I'm sorry, I can only help with booking, canceling, or rescheduling appointments. "
    "If you need medical advice or other assistance, please speak to a human representative."
)

_FALLBACK = "I'm sorry, could you repeat that?"


def response_generator_node(state: AgentState) -> dict:
    """Emit the final validated AIMessage.

    Reads:   _planner_inquiry_short_circuit, _validator_clean_content
    Writes:  messages (single AIMessage)
    """
    # Inquiry deterministic short-circuit
    if state.get("_planner_inquiry_short_circuit"):
        logger.info("[RESPONSE GENERATOR] Emitting deterministic inquiry redirect.")
        return {"messages": [AIMessage(content=_INQUIRY_REDIRECT)]}

    # Greeting deterministic short-circuit
    if state.get("_planner_greeting_short_circuit"):
        logger.info("[RESPONSE GENERATOR] Emitting deterministic greeting response.")
        return {"messages": [AIMessage(content=_GREETING_REDIRECT)]}

    # Out of scope deterministic short-circuit
    if state.get("_planner_out_of_scope_short_circuit"):
        logger.info("[RESPONSE GENERATOR] Emitting deterministic out-of-scope response.")
        return {"messages": [AIMessage(content=_OUT_OF_SCOPE_REDIRECT)]}

    content = state.get("_validator_clean_content") or _FALLBACK

    logger.info(
        "[RESPONSE GENERATOR] Emitting validated response (len=%d).", len(content)
    )
    return {"messages": [AIMessage(content=content)]}
