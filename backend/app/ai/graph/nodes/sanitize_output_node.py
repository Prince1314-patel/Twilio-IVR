"""
Sanitize Output Node
====================

Final graph node that strips internal context from state["messages"]
before the response reaches LiveKit's TTS pipeline.

This node acts as a last-line defense against context leakage:
it keeps ONLY the last AIMessage and discards all SystemMessage,
ToolMessage, HumanMessage, and any other internal artifacts.

IMPORTANT:
- This node MUST be placed immediately before END in the graph.
- It does NOT modify any state fields except "messages".
- It is safe and idempotent.

Author: Advanced AI Systems Team
Last Modified: 2026-02-17
"""

from langchain_core.messages import AIMessage

from app.ai.graph.state import AgentState
from app.core.logger_config import get_ai_agent_logger

logger = get_ai_agent_logger()


def sanitize_output_node(state: AgentState) -> AgentState:
    """
    Sanitize the output messages to prevent internal context from
    leaking to LiveKit's TTS engine.

    Strategy:
    - Walk state["messages"] in reverse.
    - Find the last AIMessage.
    - Return ONLY that single AIMessage as the new messages list.
    - If no AIMessage is found, return a safe fallback.

    This guarantees that LiveKit never receives SystemMessage,
    ToolMessage, or any other internal-only message types.
    """
    messages = state.get("messages", [])
    last_ai_message = None

    for msg in reversed(messages):
        if isinstance(msg, AIMessage):
            last_ai_message = msg
            break

    if last_ai_message is None:
        logger.warning(
            "[SANITIZE OUTPUT] No AIMessage found in state. "
            "Returning fallback message."
        )
        last_ai_message = AIMessage(
            content="I'm sorry, could you repeat that?"
        )

    logger.debug(
        f"[SANITIZE OUTPUT] Passing through AIMessage: "
        f"{str(last_ai_message.content)[:80]}..."
    )

    # Return only the sanitized messages field.
    # All other state fields pass through unchanged via the graph reducer.
    return {
        "messages": [last_ai_message],
    }
