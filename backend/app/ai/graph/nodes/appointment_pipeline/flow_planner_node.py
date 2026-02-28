"""
Flow Planner Node
=================

**Responsibility**: Deterministic finite-state step progression.

This node MUST NOT call any LLM.  It is the sole authority on which
``flow_step`` is active and whether the flow has logically advanced.

Decision algorithm
------------------
1. If flow is already completed → return state unchanged.
2. If there is no active_intent → return state unchanged.
3. Initialise ``flow_step`` from ``FIRST_FLOW_STEP_BY_INTENT`` when it is
   missing and the intent is locked.
4. Handle explicit intent-override detection (keyword match + classifier
   confirmation) and reset flow when a confirmed override is detected.
5. **Confirmation detection** — when the current step ends in
   ``__confirmation`` and the user's last message is an affirmative
   (yes / yeah / ok / sure / confirm / …), set
   ``collected_slots["confirmed"] = "confirmed"`` deterministically.
   This is what allows the executor's Confirmation Guard to pass and
   the destructive tool call to proceed.
6. Advance ``flow_step`` as far as the collected slots allow (multi-step jump).
7. Detect the INQUIRY short-circuit and mark ``inquiry_short_circuit=True``
   in the returned state so that downstream nodes can skip everything.

Outputs written to state
------------------------
- ``flow_step``
- ``flow_completed``
- ``active_intent``
- ``intent_locked``
- ``collected_slots``  (updated with ``confirmed`` on affirmative turns;
                        cleared only on intent reset)
- ``intent``
- ``intent_confidence``
- ``_planner_inquiry_short_circuit`` (ephemeral bool, consumed by
  response_generator_node)

Author: Advanced AI Systems Team
Last Modified: 2026-02-26
"""

import json

from langchain_core.messages import HumanMessage, AIMessage

from app.ai.graph.state import (
    AgentState,
    validate_state_invariants,
    FIRST_FLOW_STEP_BY_INTENT,
    FLOW_DEFINITIONS,
)
from app.ai.graph.flow_manager import (
    should_advance_step,
    get_next_step,
)
from app.ai.intent.classifier import classify_intent_sync
from app.core.logger_config import get_ai_agent_logger

logger = get_ai_agent_logger()


# ---------------------------------------------------------------------------
# Intent override detection (no LLM — pure keyword heuristic)
# ---------------------------------------------------------------------------

_CANCEL_NEGATIONS = ("don't cancel", "do not cancel")
_RESCHEDULE_KW = (
    "reschedul", "reshcedul", "reshedul", "re-schedul",
    "postpone", "delay",
)
_CHANGE_ACTIONS = ("change", "move", "shift", "switch", "pick", "choose")
_TIME_OBJECTS = ("time", "date", "day", "slot", "appointment", "booking", "schedule")
_QUALIFIERS = ("different", "another", "other")
_NEW_RESCHEDULE = ("new time", "new date", "new day", "new slot")

# Words that count as an explicit confirmation when the step is *__confirmation
_CONFIRMATIONS = {"yes", "yeah", "yep", "ok", "okay", "sure", "fine"}

# Keywords that signal the user wants to VIEW their own appointments (inquiry sub-type)
_APPOINTMENT_LOOKUP_KW = (
    "my appointment",
    "show appointment",
    "upcoming appointment",
    "next appointment",
    "when is my",
    "when's my",
    "how many appointment",
    "do i have any appointment",
    "list appointment",
    "view appointment",
    "check my appointment",
    "what appointment",
    "my schedule",
    "my booking",
    "scheduled appointment",
    "what time is my",
    "see my appointment",
    "show my",
)
_CONFIRMATION_PHRASES = (
    "yes", "yeah", "yep", "ok", "okay", "sure", "fine",
    "confirm", "confirmed", "correct", "that's right", "thats right",
    "go ahead", "please proceed", "proceed", "sounds good", "looks good",
    "absolutely", "definitely", "of course", "do it",
)


def _detect_intent_override(user_text: str) -> str | None:
    """Heuristic keyword detection of explicit intent-switch requests.

    Returns the overriding intent string, or None.
    """
    if not user_text:
        return None
    text = user_text.lower()
    if text.strip() in _CONFIRMATIONS:
        return None

    if "cancel" in text and not any(p in text for p in _CANCEL_NEGATIONS):
        return "cancellation"

    if any(kw in text for kw in _RESCHEDULE_KW):
        return "rescheduling"

    has_time_obj = any(obj in text for obj in _TIME_OBJECTS)
    if has_time_obj:
        if any(act in text for act in _CHANGE_ACTIONS):
            return "rescheduling"
        if any(qual in text for qual in _QUALIFIERS):
            return "rescheduling"

    if any(p in text for p in _NEW_RESCHEDULE):
        return "rescheduling"

    if "earlier" in text or "later" in text:
        return "rescheduling"

    if "book" in text and "appointment" in text:
        return "booking"

    return None


def _get_last_user_text(messages: list) -> str:
    """Return the content of the most recent HumanMessage."""
    for msg in reversed(messages or []):
        if isinstance(msg, HumanMessage):
            return str(msg.content or "").strip()
        if isinstance(msg, dict) and msg.get("role") == "user":
            return str(msg.get("content", "")).strip()
    return ""


def _is_appointment_lookup(text: str) -> bool:
    """Return True when the user wants to VIEW their existing appointments.

    This is a sub-category of 'inquiry' that should call
    ``get_upcoming_appointments`` rather than emit the generic redirect.
    """
    if not text:
        return False
    lower = text.lower()
    return any(kw in lower for kw in _APPOINTMENT_LOOKUP_KW)


_NEGATION_PREFIXES = ("no", "don't", "do not", "cancel", "stop", "wait", "hold on", "never mind")


def _is_affirmative(text: str) -> bool:
    """Return True when the user's message is an unambiguous confirmation.

    Checks:
    1. Exact single-token matches ("yes", "ok", …)
    2. Any confirmation phrase appearing in the text
    3. NOT preceded by a negation ("no, wait" must not pass)
    """
    if not text:
        return False
    lower = text.lower().strip()

    # Reject obvious negations first
    if any(lower.startswith(neg) for neg in _NEGATION_PREFIXES):
        return False

    # Single-token exact match
    if lower in _CONFIRMATION_PHRASES:
        return True

    # Phrase contained in longer text
    for phrase in _CONFIRMATION_PHRASES:
        if phrase in lower:
            return True

    return False


# ---------------------------------------------------------------------------
# Public node function
# ---------------------------------------------------------------------------

def flow_planner_node(state: AgentState) -> dict:
    """Deterministic FSM step planner.

    Reads:   intent, active_intent, intent_locked, flow_step,
             flow_completed, collected_slots, messages
    Writes:  flow_step, active_intent, intent_locked, flow_completed,
             collected_slots (including ``confirmed`` on affirmative turns),
             intent, intent_confidence, _planner_inquiry_short_circuit
    """
    # Pull current-turn scalars
    intent = state.get("intent", "inquiry")
    intent_confidence = state.get("intent_confidence", 0.5)
    active_intent = state.get("active_intent") or intent
    intent_locked = bool(state.get("intent_locked", False))
    flow_step = state.get("flow_step")
    flow_completed = bool(state.get("flow_completed", False))
    collected_slots = dict(state.get("collected_slots") or {})
    messages = state.get("messages", [])
    last_user_text = _get_last_user_text(messages)

    # Validate identity-first invariant
    validate_state_invariants(state, "business")

    logger.info(
        "[FLOW PLANNER] intent=%s (%.2f) active=%s locked=%s step=%s completed=%s",
        intent, intent_confidence, active_intent, intent_locked, flow_step, flow_completed,
    )

    # ------------------------------------------------------------------
    # Short-circuit 1: INQUIRY with no locked transactional intent
    # Exception: appointment-lookup queries ("show my appointments", etc.)
    # must NOT short-circuit — they fall through so the executor can call
    # get_upcoming_appointments and the LLM can format the result.
    # ------------------------------------------------------------------
    if intent == "inquiry" and not intent_locked:
        if _is_appointment_lookup(last_user_text):
            logger.info(
                "[FLOW PLANNER] Appointment lookup detected — bypassing inquiry short-circuit."
            )
            # Fall through to normal processing; no FSM steps needed.
            # We skip the advance loop entirely and return without short-circuiting.
            return {
                "intent": intent,
                "intent_confidence": intent_confidence,
                "active_intent": active_intent,
                "intent_locked": intent_locked,
                "flow_step": flow_step,
                "flow_completed": flow_completed,
                "collected_slots": collected_slots,
                "_planner_inquiry_short_circuit": False,
                "_planner_greeting_short_circuit": False,
                "_planner_out_of_scope_short_circuit": False,
                "_planner_appointment_lookup": True,
            }
        logger.info("[FLOW PLANNER] Inquiry short-circuit — no FSM work needed.")
        return {
            "intent": intent,
            "intent_confidence": intent_confidence,
            "active_intent": active_intent,
            "intent_locked": intent_locked,
            "flow_step": flow_step,
            "flow_completed": flow_completed,
            "collected_slots": collected_slots,
            "_planner_inquiry_short_circuit": True,
            "_planner_greeting_short_circuit": False,
            "_planner_out_of_scope_short_circuit": False,
            "_planner_appointment_lookup": False,
        }

    # ------------------------------------------------------------------
    # Short-circuit 1.1: GREETING with no locked transactional intent
    # ------------------------------------------------------------------
    if intent == "greeting" and not intent_locked:
        logger.info("[FLOW PLANNER] Greeting short-circuit — no FSM work needed.")
        return {
            "intent": intent,
            "intent_confidence": intent_confidence,
            "active_intent": active_intent,
            "intent_locked": intent_locked,
            "flow_step": flow_step,
            "flow_completed": flow_completed,
            "collected_slots": collected_slots,
            "_planner_inquiry_short_circuit": False,
            "_planner_greeting_short_circuit": True,
            "_planner_out_of_scope_short_circuit": False,
        }

    # ------------------------------------------------------------------
    # Short-circuit 1.2: OUT_OF_SCOPE with no locked transactional intent
    # ------------------------------------------------------------------
    if intent == "out_of_scope" and not intent_locked:
        logger.info("[FLOW PLANNER] Out-of-scope short-circuit — no FSM work needed.")
        return {
            "intent": intent,
            "intent_confidence": intent_confidence,
            "active_intent": active_intent,
            "intent_locked": intent_locked,
            "flow_step": flow_step,
            "flow_completed": flow_completed,
            "collected_slots": collected_slots,
            "_planner_inquiry_short_circuit": False,
            "_planner_greeting_short_circuit": False,
            "_planner_out_of_scope_short_circuit": True,
        }


    # ------------------------------------------------------------------
    # Short-circuit 2: Flow already completed
    # ------------------------------------------------------------------
    if flow_completed:
        logger.info("[FLOW PLANNER] Flow already completed — no FSM work needed.")
        return {
            "intent": intent,
            "intent_confidence": intent_confidence,
            "active_intent": active_intent,
            "intent_locked": intent_locked,
            "flow_step": flow_step,
            "flow_completed": flow_completed,
            "collected_slots": collected_slots,
            "_planner_inquiry_short_circuit": False,
            "_planner_greeting_short_circuit": False,
            "_planner_out_of_scope_short_circuit": False,
        }

    # ------------------------------------------------------------------
    # Intent override detection (only when locked)
    # ------------------------------------------------------------------
    if intent_locked and last_user_text:
        override_candidate = _detect_intent_override(last_user_text)
        if override_candidate and override_candidate != active_intent:
            logger.info(
                "[FLOW PLANNER] Override candidate %s → %s. Confirming with classifier.",
                active_intent, override_candidate,
            )
            try:
                # Import here to avoid circular at module level
                from app.ai.llm.client_factory import create_llm_model
                _clf_model = create_llm_model(temperature=0.0, purpose="intent")
                clf_intent, clf_conf = classify_intent_sync(last_user_text, _clf_model)
            except Exception as exc:
                logger.warning("[FLOW PLANNER] Classifier failed during override check: %s", exc)
                clf_intent, clf_conf = None, 0.0

            if clf_intent == override_candidate and clf_conf >= 0.7:
                logger.info(
                    "[FLOW PLANNER] Override confirmed: %s → %s (conf=%.2f)",
                    active_intent, override_candidate, clf_conf,
                )
                active_intent = override_candidate
                intent = override_candidate
                intent_confidence = clf_conf
                flow_step = FIRST_FLOW_STEP_BY_INTENT.get(override_candidate)
                intent_locked = True
                collected_slots = {}
            else:
                logger.info("[FLOW PLANNER] Override rejected — keeping %s.", active_intent)

    # ------------------------------------------------------------------
    # Bootstrap flow_step if missing
    # ------------------------------------------------------------------
    if intent_locked and not flow_step and active_intent:
        flow_step = FIRST_FLOW_STEP_BY_INTENT.get(active_intent)
        logger.debug("[FLOW PLANNER] Bootstrapped flow_step=%s", flow_step)

    # ------------------------------------------------------------------
    # Multi-step advance loop
    # ------------------------------------------------------------------
    if not flow_completed and active_intent and flow_step:
        max_advances = len(FLOW_DEFINITIONS.get(active_intent, []))
        for _ in range(max_advances):
            if should_advance_step(flow_step, collected_slots, active_intent):
                next_step = get_next_step(active_intent, flow_step)
                if next_step:
                    logger.info("[FLOW PLANNER] Advance: %s → %s", flow_step, next_step)
                    flow_step = next_step
                else:
                    break
            else:
                break

    # ------------------------------------------------------------------
    # Confirmation detection (deterministic — no LLM)
    # Runs AFTER the advance loop so that we check the FINAL flow_step.
    # Example: the advance moves from "cancellation__reason" →
    # "cancellation__confirmation" in the same turn. The user's affirmative
    # message ("yes") then stamps confirmed='confirmed' on the new step so
    # the executor's Confirmation Guard passes on the very next LLM attempt.
    # ------------------------------------------------------------------
    if (
        flow_step
        and flow_step.endswith("__confirmation")
        and last_user_text
    ):
        if _is_affirmative(last_user_text) and not collected_slots.get("confirmed"):
            collected_slots["confirmed"] = "confirmed"
            logger.info(
                "[FLOW PLANNER] Confirmation detected at step=%s — set confirmed='confirmed'",
                flow_step,
            )
        elif not _is_affirmative(last_user_text):
            # Explicit denial / changed mind — clear any previously set confirmed
            lower = last_user_text.lower()
            if any(lower.startswith(neg) for neg in _NEGATION_PREFIXES):
                collected_slots.pop("confirmed", None)
                logger.info(
                    "[FLOW PLANNER] Denial detected at step=%s — cleared confirmed slot",
                    flow_step,
                )

    logger.info(
        "[FLOW PLANNER] DONE — active=%s step=%s completed=%s",
        active_intent, flow_step, flow_completed,
    )

    return {
        "intent": intent,
        "intent_confidence": intent_confidence,
        "active_intent": active_intent,
        "intent_locked": intent_locked,
        "flow_step": flow_step,
        "flow_completed": flow_completed,
        "collected_slots": collected_slots,
        "_planner_inquiry_short_circuit": False,
        "_planner_greeting_short_circuit": False,
        "_planner_out_of_scope_short_circuit": False,
    }
