"""
Result Validator Node
=====================

**Responsibility**: Evidence gate — block hallucinated confirmations.

This node MUST NOT call any LLM.  It reads the execution evidence flags set
by ``tool_executor_node`` (``_executor_*`` fields) and the last AI message
generated in the execution loop, then decides whether that message contains
hallucinated commitment language without supporting evidence.

If hallucination is detected, the message content is replaced with a safe
recovery response.  All other state fields pass through unchanged.

Coverage
--------
- Booking    — blocks "successfully booked / confirmed / scheduled" without
               ``appointment_created=True``.
- Cancellation — blocks "cancelled / cancellation confirmed" without
                 ``cancellation_cancelled=True``.
- Rescheduling — blocks "rescheduled / appointment updated" without
                 ``rescheduling_rescheduled=True``.

Outputs written to state
------------------------
- ``_validator_clean_content``  — the (possibly sanitised) response text
                                  consumed by response_generator_node.

Author: Advanced AI Systems Team  
Last Modified: 2026-02-25
"""

from app.ai.graph.state import AgentState
from app.ai.utils.text_processing import clean_agent_response
from app.core.logger_config import get_ai_agent_logger

logger = get_ai_agent_logger()

# ---------------------------------------------------------------------------
# Phrase lists per intent — same as the original node
# ---------------------------------------------------------------------------

_BOOKING_PHRASES = [
    "you're all set", "you are all set", "all set",
    "appointment is confirmed", "appointment confirmed", "confirmed your appointment",
    "successfully booked", "booking is confirmed",
    "have scheduled", "has been scheduled", "is scheduled",
]

_CANCEL_PHRASES = [
    "cancelled your appointment", "appointment has been cancelled",
    "appointment cancelled", "successfully cancelled",
    "cancellation is complete", "cancellation confirmed",
    "have cancelled", "has been cancelled",
]

_RESCHEDULE_PHRASES = [
    "rescheduled your appointment", "appointment has been rescheduled",
    "appointment rescheduled", "successfully rescheduled",
    "appointment has been updated", "appointment updated",
    "successfully updated", "rescheduling is complete",
    "have rescheduled", "has been rescheduled",
]

_RECOVERY_BOOKING = (
    "I have all the details I need. Just to confirm — shall I go ahead and book "
    "this appointment? Please say yes to confirm or no to make changes."
)
_RECOVERY_CANCEL = (
    "To confirm — shall I go ahead and cancel your appointment? "
    "Please say yes to confirm the cancellation, or no if you've changed your mind."
)
_RECOVERY_RESCHEDULE = (
    "To confirm — shall I go ahead and reschedule your appointment to the new time? "
    "Please say yes to confirm, or no if you'd like to choose a different time."
)
_RECOVERY_UNKNOWN = "I'm sorry, could you repeat that?"


# ---------------------------------------------------------------------------
# Public node function
# ---------------------------------------------------------------------------

def result_validator_node(state: AgentState) -> dict:
    """Evidence gate: scrub hallucinated confirmation language.

    Reads:   _executor_final_ai_message, _executor_appointment_created,
             _executor_cancellation_cancelled, _executor_rescheduling_rescheduled,
             _executor_initial_flow_completed, active_intent, flow_completed
    Writes:  _validator_clean_content
    """
    from langchain_core.messages import AIMessage  # local import avoids circularity

    final_msg = state.get("_executor_final_ai_message")
    appointment_created      = bool(state.get("_executor_appointment_created", False))
    cancellation_cancelled   = bool(state.get("_executor_cancellation_cancelled", False))
    rescheduling_rescheduled = bool(state.get("_executor_rescheduling_rescheduled", False))
    initial_flow_completed   = bool(state.get("_executor_initial_flow_completed", False))
    active_intent = state.get("active_intent")
    validation_failure_count = state.get("validation_failure_count", 0)

    # ------------------------------------------------------------------
    # Extract and clean raw content
    # ------------------------------------------------------------------
    if final_msg and isinstance(final_msg, AIMessage):
        raw = str(final_msg.content)
    else:
        raw = ""

    content = clean_agent_response(raw) if raw else _RECOVERY_UNKNOWN

    logger.debug("[RESULT VALIDATOR] raw content length=%d", len(content))

    # ------------------------------------------------------------------
    # Guard: booking hallucination
    # ------------------------------------------------------------------
    if active_intent == "booking" and not initial_flow_completed:
        if any(p in content.lower() for p in _BOOKING_PHRASES) and not appointment_created:
            logger.warning(
                "[RESULT VALIDATOR] Blocked booking hallucination. "
                "content snippet: '%.80s'", content,
            )
            validation_failure_count += 1
            content = _RECOVERY_BOOKING

    # ------------------------------------------------------------------
    # Guard: cancellation hallucination
    # ------------------------------------------------------------------
    if active_intent == "cancellation" and not initial_flow_completed:
        if any(p in content.lower() for p in _CANCEL_PHRASES) and not cancellation_cancelled:
            logger.warning(
                "[RESULT VALIDATOR] Blocked cancellation hallucination. "
                "content snippet: '%.80s'", content,
            )
            validation_failure_count += 1
            content = _RECOVERY_CANCEL

    # ------------------------------------------------------------------
    # Guard: rescheduling hallucination
    # ------------------------------------------------------------------
    if active_intent == "rescheduling" and not initial_flow_completed:
        if any(p in content.lower() for p in _RESCHEDULE_PHRASES) and not rescheduling_rescheduled:
            logger.warning(
                "[RESULT VALIDATOR] Blocked rescheduling hallucination. "
                "content snippet: '%.80s'", content,
            )
            validation_failure_count += 1
            content = _RECOVERY_RESCHEDULE

    logger.info("[RESULT VALIDATOR] Validated content length=%d", len(content))

    return {
        "_validator_clean_content": content,
        "validation_failure_count": validation_failure_count
    }
