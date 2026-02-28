"""
Intent Detection Node
=====================

LangGraph node for classifying user intent from conversation messages.

Author: Advanced AI Systems Team
Last Modified: 2026-02-03
"""

from langchain_core.messages import HumanMessage, AIMessage

from app.ai.graph.state import AgentState, validate_state_invariants, FIRST_FLOW_STEP_BY_INTENT
from app.ai.intent.classifier import classify_intent_sync, IntentCategory
from app.ai.llm.client_factory import create_llm_model
from app.ai.graph.nodes.appointment_pipeline.flow_planner_node import _detect_intent_override
from app.core.logger_config import get_ai_agent_logger


logger = get_ai_agent_logger()

# Default module-level variable for test mocking
model = None

def _get_model():
    """Return Llama model for intent classification (fast and accurate).
    
    Hardcoded to use llama-3.1-8b-instant for intent classification.
    """
    import sys
    mod = sys.modules[__name__]
    if mod.model is not None:
        return mod.model
    
    # Hardcoded: Use Llama for intent classification (fast and accurate)
    from langchain_groq import ChatGroq
    from app.core.config import settings
    
    return ChatGroq(
        model="llama-3.1-8b-instant",
        temperature=0.0,
        api_key=settings.GROQ_API_KEY
    )

from app.core.performance_monitor import performance_monitor


def intent_detection_node(state: AgentState) -> AgentState:
    """
    Classify user intent from the last user message in conversation history.
    
    This node:
    1. Extracts the last user message from conversation history
    2. Classifies intent using the LLM-based intent classifier
    3. Updates state with intent and confidence information
    4. Handles errors gracefully with fallback behavior
    5. Preserves all existing message history
    
    Args:
        state: Current agent state with messages
        
    Returns:
        Updated state with intent and intent_confidence fields
    """
    # ------------------------------------------------------------------
    # 1. Extract last user message and AI message context (for classification)
    # ------------------------------------------------------------------
    user_text = ""
    ai_text = ""
    if state.get("messages"):
        found_user = False
        for msg in reversed(state["messages"]):
            if not found_user:
                if isinstance(msg, HumanMessage):
                    user_text = msg.content
                    found_user = True
                elif isinstance(msg, dict) and msg.get("role") == "user":
                    user_text = msg.get("content", "")
                    found_user = True
            else:
                # After finding the user message, the next message (going backwards) 
                # that is from the AI should be our context
                if isinstance(msg, AIMessage):
                    ai_text = msg.content
                    break
                elif isinstance(msg, dict) and msg.get("role") == "assistant":
                    ai_text = msg.get("content", "")
                    break
    

    # Phase 7: Centralized state validation
    validate_state_invariants(state, "intent_guard")
    
    user_id = state.get("user_id", 0)
    needs_name_enrichment = state.get("needs_name_enrichment", True)
    
    # Phase 4: Debug logging at node entry (enhanced from Phase 0)
    logger.debug(
        f"[INTENT DETECTION NODE ENTRY] "
        f"user_id={user_id}, needs_name_enrichment={needs_name_enrichment}, "
        f"user_text_length={len(user_text)}, "
        f"message_count={len(state.get('messages', []))}")
    
    # ------------------------------------------------------------------
    # 2. Intent locking guard (IVR transactional model)
    # ------------------------------------------------------------------
    #
    # If intent_locked is True, this node MUST NOT:
    # - re-run the classifier
    # - change active_intent
    # - downgrade confidence
    #
    # It simply passes through, preserving the locked transactional
    # state. Downstream nodes (business_router, appointment_agent)
    # own the flow until completion or explicit override.
    intent_locked = bool(state.get("intent_locked", False))

    # UNLOCK LOGIC: Check for explicit overrides before guarding
    if intent_locked and user_text:
        override = _detect_intent_override(user_text)
        if override and override != state.get("active_intent"):
            logger.info(f"[INTENT DETECTION] Override detected in '{user_text}': {override}. Unlocking.")
            intent_locked = False

    if intent_locked:
        logger.debug(
            "[INTENT DETECTION] intent_locked=True → skipping classification "
            f"(active_intent={state.get('active_intent')}, "
            f"intent={state.get('intent')}, "
            f"intent_confidence={state.get('intent_confidence')})"
        )
        # PERFORMANCE GUARD: LLM Skip Logic
        # Return authoritative locked intent immediately.
        active_intent = state.get("active_intent")
        logger.info(
            f"[INTENT GUARD] SKIPPING LLM - Intent Locked: {active_intent}"
        )
        return {
            "intent": active_intent,
            "intent_confidence": 1.0,
            # Ensure these persist
            "active_intent": active_intent,
            "intent_locked": True,
            "conversation_mode": "transaction"
        }

    # ------------------------------------------------------------------
    # 3. Classify intent with fallback behavior (only when unlocked)
    # ------------------------------------------------------------------
    intent = IntentCategory.INQUIRY
    intent_confidence = 0.5

    if user_text:
        try:
            with performance_monitor("intent_classification"):
                intent, intent_confidence = classify_intent_sync(user_text, _get_model(), ai_text)
            logger.info(
                f"Intent classified: {intent} (confidence: {intent_confidence:.2f}) "
                f"for message: {user_text[:50]}..."
            )
            logger.debug(
                f"[INTENT DETECTION] Classified as {intent} "
                f"with confidence {intent_confidence:.2f}"
            )
        except Exception as e:
            logger.warning(
                f"Intent classification failed: {e}, using fallback (inquiry, 0.5)"
            )
            intent = IntentCategory.INQUIRY
            intent_confidence = 0.5
    else:
        # No user message found - default to greeting
        logger.debug("No user message found, defaulting to greeting intent")
        intent = IntentCategory.GREETING
        intent_confidence = 0.5

    # ------------------------------------------------------------------
    # 4. Transactional locking semantics (session-level intent)
    # ------------------------------------------------------------------
    #
    # When confidence is high enough (≥ 0.7) AND the intent is one of the
    # transactional categories, we:
    #   - set active_intent (session-level)
    #   - lock intent (intent_locked=True)
    #   - initialize flow_step to the first step for that intent
    #   - reset flow_completed=False
    #
    # Otherwise, we keep the intent fields as message-level hints only
    # and allow downstream logic to use GENERAL_AGENT_PROMPT for
    # clarification (pre-transactional).
    transactional_intents = {
        IntentCategory.BOOKING,
        IntentCategory.CANCELLATION,
        IntentCategory.RESCHEDULING,
        # IntentCategory.INQUIRY,  <-- REMOVED: Inquiry should not lock the flow
    }

    active_intent = state.get("active_intent")
    flow_step = state.get("flow_step")
    flow_completed = bool(state.get("flow_completed", False))
    locked = False
    conversation_mode = "idle"

    if intent in transactional_intents and intent_confidence >= 0.7:
        locked = True
        active_intent = intent
        conversation_mode = "transaction"
        flow_completed = False
        # Initialize flow_step deterministically for this intent
        flow_step = FIRST_FLOW_STEP_BY_INTENT.get(
            intent, state.get("flow_step")  # fallback to prior step if unknown
        )
        # Initialize empty collected_slots for new flow
        collected_slots = {}
        logger.info(
            "[INTENT DETECTION] Locking transactional intent: "
            f"active_intent={active_intent}, "
            f"intent_confidence={intent_confidence:.2f}, "
            f"flow_step={flow_step}"
        )
    else:
        # Remain unlocked – use GENERAL_AGENT_PROMPT downstream for
        # clarification, but keep best-effort intent hints.
        locked = False
        active_intent = None
        collected_slots = state.get("collected_slots", {})  # Preserve existing slots
        logger.debug(
            "[INTENT DETECTION] Confidence below lock threshold or "
            "non-transactional intent → remaining unlocked."
        )

    # ------------------------------------------------------------------
    # 5. Return updated state
    # ------------------------------------------------------------------
    return {
        "intent": intent,
        "intent_confidence": intent_confidence,
        "active_intent": active_intent,
        "intent_locked": locked,
        "conversation_mode": conversation_mode if locked else "idle",
        "flow_step": flow_step,
        "flow_completed": flow_completed,
        "collected_slots": collected_slots,
    }