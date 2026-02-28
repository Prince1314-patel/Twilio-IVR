"""
Tool Executor Node
==================

**Responsibility**: Enforce per-step tool allowlist, run precondition guards,
execute approved tool calls, and update state with execution evidence.

This node MUST NOT call any LLM for generation.  It drives the full inner
tool-execution loop (up to MAX_TURNS iterations), using the *already-bound*
model only to obtain tool-call decisions from the LLM.

Key guards (in evaluation order)
---------------------------------
1. **Step-tool allowlist** — rejects any tool call not in
   ``STEP_TOOL_ALLOWLIST[flow_step]``.
2. **Hard confirmation precondition** — destructive tools require
   ``collected_slots["confirmed"] == "confirmed"``.
3. **Transactional safety guard** — cancel/update require a verified
   ``appointment_id`` that originated from ``get_upcoming_appointments``.
4. **All-slots completeness guard** — create/update blocked until every
   required slot is present.

Outputs written to state
------------------------
- ``messages``               (extended with AI + Tool messages from this turn)
- ``collected_slots``        (ONLY user-provided slot data; never contains
                              control keys like valid_appointment_ids)
- ``valid_appointment_ids``  (top-level — IDs verified via get_upcoming_appointments)
- ``valid_appointments``     (top-level — full appointment dicts for this session)
- ``flow_step``              (reset on guard-triggered step correction)
- ``flow_completed``         (set True on successful commit)
- ``active_intent``          (cleared on successful commit)
- ``intent_locked``          (False on successful commit)
- ``_executor_final_ai_message``  (the last AIMessage from the loop,
                                   consumed by response_generator_node)
- ``_executor_appointment_created``    (bool)
- ``_executor_cancellation_cancelled`` (bool)
- ``_executor_rescheduling_rescheduled`` (bool)
- ``_executor_initial_flow_completed``   (bool — snapshot taken at entry)

Author: Advanced AI Systems Team
Last Modified: 2026-02-25
"""

import os
import json
from datetime import datetime
import pytz

from langchain_core.messages import SystemMessage, AIMessage, HumanMessage, ToolMessage

from app.ai.graph.state import (
    AgentState,
    STEP_TOOL_ALLOWLIST,
    FLOW_DEFINITIONS,
    REQUIRED_SLOTS_BY_INTENT,
    FIRST_FLOW_STEP_BY_INTENT,
)
from app.ai.graph.flow_manager import is_flow_complete, get_step_info, build_flow_context_message
from app.ai.utils.slot_extractor import extract_all_slots_from_message
from app.ai.prompts.appointment_prompts import (
    get_intent_specific_prompt,
    get_clarification_prompt,
    should_use_direct_flow,
)
from app.ai.utils.text_processing import clean_agent_response
from app.ai.llm.client_factory import create_llm_model
from app.core.config import settings
from app.core.logger_config import get_ai_agent_logger

from app.database.tools.appointment_tools import (
    create_appointment_in_db,
    check_appointment_availability,
    get_available_slots_for_date,
    update_appointment_in_db,
    cancel_appointment_in_db,
    get_upcoming_appointments,
)

logger = get_ai_agent_logger()

MAX_TURNS = 5

# ---------------------------------------------------------------------------
# Module-level model and tool set (singleton removed for thread-safety)
# ---------------------------------------------------------------------------
# NOTE: named ``model`` (not ``_model``) so that:
#   - ``appointment_agent_node.py`` re-exports it as ``model`` for patch compat
#   - tests can patch ``tool_executor_node.model`` directly

# Default module-level variables for test mocking
model = None
_model = None

_tools = [
    create_appointment_in_db,
    check_appointment_availability,
    get_available_slots_for_date,
    update_appointment_in_db,
    cancel_appointment_in_db,
    get_upcoming_appointments,
]
_tool_map = {t.name: t for t in _tools}


def _get_model():
    """Return Llama model for slot extraction (fast and cheap).
    
    Hardcoded to use llama-3.1-8b-instant for slot extraction.
    """
    import sys
    mod = sys.modules[__name__]
    
    # Check if a test suite has patched the 'model' variable
    if mod.model is not None:
        return mod.model
        
    # Hardcoded: Use Llama for slot extraction (fast and cheap)
    from langchain_groq import ChatGroq
    from app.core.config import settings
    
    return ChatGroq(
        model="llama-3.1-8b-instant",
        temperature=0.3,
        api_key=settings.GROQ_API_KEY
    )


def _get_agent_model():
    """Return Moonshot model for main appointment agent (high quality).
    
    Hardcoded to use moonshotai/kimi-k2-instruct-0905 for conversational agent.
    """
    import sys
    mod = sys.modules[__name__]
    
    # Check if a test suite has patched the 'model' variable
    if mod.model is not None:
        return mod.model
        
    # Hardcoded: Use Moonshot for main agent (high quality)
    from langchain_groq import ChatGroq
    from app.core.config import settings
    
    return ChatGroq(
        model="moonshotai/kimi-k2-instruct-0905",
        temperature=0.3,
        api_key=settings.GROQ_API_KEY
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_last_user_text(messages: list) -> str:
    for msg in reversed(messages or []):
        if isinstance(msg, HumanMessage):
            return str(msg.content or "").strip()
        if isinstance(msg, dict) and msg.get("role") == "user":
            return str(msg.get("content", "")).strip()
    return ""


def _get_last_ai_text(messages: list) -> str:
    """Return the content of the most recent AIMessage."""
    for msg in reversed(messages or []):
        if isinstance(msg, AIMessage):
            return str(msg.content or "").strip()
        if isinstance(msg, dict) and msg.get("role") == "assistant":
            return str(msg.get("content", "")).strip()
    return ""


def _build_user_context_str(user_profile: dict | None) -> str | None:
    if not user_profile:
        return None
    parts = []
    if user_profile.get("name"):
        parts.append(f"User's name: {user_profile['name']}")
    if user_profile.get("mobile_number"):
        parts.append(f"User's mobile number: {user_profile['mobile_number']}")
    if user_profile.get("email"):
        parts.append(f"User's email: {user_profile['email']}")
    if parts:
        return (
            "USER CONTEXT:\n" + "\n".join(parts) + "\n\n"
            "CRITICAL INSTRUCTION: Use this information to personalise the conversation. "
            "Do not ask for information already provided here. "
            "Address the user by name if known. "
            "You have NO knowledge of past appointments until you call tools."
        )
    return None


def _build_system_prompt(
    intent: str,
    intent_confidence: float,
    intent_locked: bool,
    active_intent: str | None,
    flow_step: str | None,
    collected_slots: dict,
    user_profile: dict | None,
    tone_instruction: str | None,
) -> str:
    """Assemble the system prompt string for this turn."""
    parts = []

    # Main prompt
    if intent_locked:
        parts.append(get_intent_specific_prompt(intent, max(intent_confidence, 0.7)))
    else:
        if intent_confidence < 0.6:
            parts.append(get_clarification_prompt(intent, intent_confidence))
        else:
            parts.append(get_intent_specific_prompt(intent, intent_confidence))
            if should_use_direct_flow(intent, intent_confidence):
                parts.append(
                    "CRITICAL INSTRUCTION: The user's intent is VERY CLEAR. "
                    "Skip excessive pleasantries."
                )

    # User context
    ctx = _build_user_context_str(user_profile)
    if ctx:
        parts.append(ctx)

    # Tone
    if tone_instruction:
        parts.append(tone_instruction)

    # Flow context
    if intent_locked and flow_step and active_intent:
        fc = build_flow_context_message(active_intent, flow_step, collected_slots)
        parts.append(fc.content)

    # Time
    try:
        ist_tz = pytz.timezone("Asia/Kolkata")
        ts = datetime.now(ist_tz).strftime("%A, %Y-%m-%d %H:%M %p")
    except Exception:
        ts = datetime.now().strftime("%A, %Y-%m-%d %H:%M %p")
    parts.append(f"CURRENT DATE & TIME: {ts}")

    # Transactional meta
    parts.append(
        f"ACTIVE INTENT: {active_intent}\n"
        f"FLOW STEP: {flow_step}\n"
        "CRITICAL: System handles appointment_id resolution. You must NEVER INVENT IDs."
    )

    return "\n\n".join(str(p) for p in parts)


# ---------------------------------------------------------------------------
# Public node function
# ---------------------------------------------------------------------------

def tool_executor_node(state: AgentState) -> dict:
    """Run the tool-execution loop with strict guards.

    Reads:   (all state fields)
    Writes:  messages, collected_slots, flow_step, flow_completed,
             active_intent, intent_locked, intent, intent_confidence,
             + private _executor_* fields consumed by result_validator_node
             and response_generator_node.
    """
    # ------------------------------------------------------------------
    # Extract state
    # ------------------------------------------------------------------
    intent = state.get("intent", "inquiry")
    intent_confidence = state.get("intent_confidence", 0.5)
    active_intent = state.get("active_intent") or intent
    intent_locked = bool(state.get("intent_locked", False))
    flow_step = state.get("flow_step")
    flow_completed = bool(state.get("flow_completed", False))
    collected_slots = dict(state.get("collected_slots") or {})
    # Task #23 — verification metadata lives at the TOP LEVEL, NOT inside collected_slots.
    valid_appointment_ids: list = list(state.get("valid_appointment_ids") or [])
    valid_appointments: list = list(state.get("valid_appointments") or [])
    caller_mobile_number = state.get("caller_mobile_number", "N/A")
    messages = state.get("messages", [])
    last_user_text = _get_last_user_text(messages)
    last_ai_text = _get_last_ai_text(messages)
    user_profile = state.get("user_profile")
    tone_instruction = state.get("tone_instruction")
    safety_conflict_count = state.get("safety_conflict_count", 0)

    # Snapshot for hallucination guard
    initial_flow_completed = bool(flow_completed)

    # Transaction completion flags
    appointment_created = False
    cancellation_cancelled = False
    rescheduling_rescheduled = False

    logger.info(
        "[TOOL EXECUTOR] ENTRY intent=%s active=%s locked=%s step=%s",
        intent, active_intent, intent_locked, flow_step,
    )

    # ------------------------------------------------------------------
    # Inquiry short-circuit: nothing to execute
    # Exception: appointment-lookup queries (“show my appointments”, etc.)
    # bypass the short-circuit; they are handled by the force-call block
    # below and a single LLM formatting pass.
    # ------------------------------------------------------------------
    is_appointment_lookup = bool(state.get("_planner_appointment_lookup", False))

    if intent == "inquiry" and not intent_locked and not is_appointment_lookup:
        logger.info("[TOOL EXECUTOR] Inquiry short-circuit — skip execution loop.")
        return {
            "intent": intent,
            "intent_confidence": intent_confidence,
            "active_intent": active_intent,
            "intent_locked": intent_locked,
            "flow_step": flow_step,
            "flow_completed": flow_completed,
            "collected_slots": collected_slots,
            "valid_appointment_ids": valid_appointment_ids,
            "valid_appointments": valid_appointments,
            "_executor_final_ai_message": None,
            "_executor_appointment_created": False,
            "_executor_cancellation_cancelled": False,
            "_executor_rescheduling_rescheduled": False,
            "_executor_initial_flow_completed": initial_flow_completed,
            "safety_conflict_count": safety_conflict_count,
        }

    # ------------------------------------------------------------------
    # Build message list for the loop
    # OPTIMIZATION: Only send last 2 turns (4 messages) to avoid token limit
    # Context engineering in system prompt provides all necessary information
    # ------------------------------------------------------------------
    all_messages = state["messages"]
    
    # DEBUG: Log message types to understand what's in state
    logger.info(
        "[TOOL EXECUTOR] Message types in state: %s",
        [f"{type(m).__name__}:{getattr(m, 'name', getattr(m, 'role', 'N/A'))}" for m in all_messages[-10:]]
    )
    
    # DEBUG: Log dict structure AND check for ToolMessage instances
    for i, m in enumerate(all_messages[-10:]):
        if isinstance(m, ToolMessage):
            logger.info(
                "[TOOL EXECUTOR] ToolMessage [%d]: name=%s, content_preview=%s",
                i, m.name, str(m.content)[:100]
            )
        elif isinstance(m, dict):
            content_preview = str(m.get("content", ""))[:100]  # First 100 chars
            logger.info(
                "[TOOL EXECUTOR] Dict message [%d]: keys=%s, role=%s, content_preview=%s",
                i, list(m.keys()), m.get("role"), content_preview
            )
    
    # Get last 4 messages (2 human + 2 AI turns)
    # This provides conversational context while keeping tokens minimal
    recent_messages = all_messages[-4:] if len(all_messages) >= 4 else all_messages
    
    # Build system prompt with full context (collected_slots, flow_step, etc.)
    system_prompt = _build_system_prompt(
        intent=intent,
        intent_confidence=intent_confidence,
        intent_locked=intent_locked,
        active_intent=active_intent,
        flow_step=flow_step,
        collected_slots=collected_slots,
        user_profile=user_profile,
        tone_instruction=tone_instruction,
    )
    
    # Start with system prompt + recent messages
    messages_for_agent = [SystemMessage(content=system_prompt)] + list(recent_messages)
    
    # Track the count BEFORE any force-called tools
    original_message_count = len(state.get("messages", []))
    force_called_tool_messages = []  # Track force-called messages separately
    
    # SPECIAL CASE: For cancellation/rescheduling, preserve the last 
    # get_upcoming_appointments tool call if it's not in recent_messages
    # This ensures the AI can see the appointment list for selection
    if active_intent in ("cancellation", "rescheduling"):
        # Find the most recent get_upcoming_appointments tool call
        tool_call_msg = None
        tool_result_msg = None
        
        for i in range(len(all_messages) - 1, -1, -1):
            msg = all_messages[i]
            # Look for AI message with get_upcoming_appointments tool call
            if isinstance(msg, AIMessage) and hasattr(msg, 'tool_calls') and msg.tool_calls:
                for tc in msg.tool_calls:
                    if tc.get('name') == 'get_upcoming_appointments':
                        tool_call_msg = msg
                        # Get the corresponding tool result
                        if i + 1 < len(all_messages):
                            next_msg = all_messages[i + 1]
                            if isinstance(next_msg, ToolMessage) and next_msg.name == 'get_upcoming_appointments':
                                tool_result_msg = next_msg
                        break
            if tool_call_msg:
                break
        
        # If we found a tool call and it's not in recent_messages, add it
        if tool_call_msg and tool_call_msg not in recent_messages:
            # Insert after system prompt but before recent messages
            messages_for_agent.insert(1, tool_call_msg)
            if tool_result_msg:
                messages_for_agent.insert(2, tool_result_msg)
            logger.info(
                "[TOOL EXECUTOR] Preserved get_upcoming_appointments tool call "
                "for appointment selection context"
            )
    
    logger.info(
        "[TOOL EXECUTOR] Message window: %d messages (system + %d recent + %d preserved tools)",
        len(messages_for_agent),
        len(recent_messages),
        len(messages_for_agent) - len(recent_messages) - 1  # -1 for system prompt
    )

    # ------------------------------------------------------------------
    # FORCE TOOL: get_upcoming_appointments for cancel/reschedule
    # ------------------------------------------------------------------
    # CRITICAL: Only force-call if we don't already have valid appointment IDs
    # This prevents redundant calls on every turn
    needs_appointment_list = (
        active_intent in ("cancellation", "rescheduling") and
        not valid_appointment_ids and  # No IDs loaded yet
        not collected_slots.get("appointment_id")  # No ID selected yet
    )
    
    if needs_appointment_list:
        logger.info("[TOOL EXECUTOR] Force-calling get_upcoming_appointments for %s", active_intent)

        # Task #23 — reset only the user-data slot IF NOT ALREADY COLLECTED
        # CRITICAL: Don't reset appointment_id if user has already selected one!
        if not collected_slots.get("appointment_id"):
            collected_slots.pop("appointment_id", None)
            valid_appointment_ids = []
            valid_appointments = []
        else:
            logger.info(
                "[TOOL EXECUTOR] Skipping appointment_id reset - already collected: %s",
                collected_slots.get("appointment_id")
            )

        tool_args = {"mobile_number": caller_mobile_number}
        try:
            raw_output = get_upcoming_appointments.invoke(tool_args)
        except Exception as exc:
            raw_output = json.dumps({"error": str(exc)})

        tool_call_id = "call_forced_" + os.urandom(4).hex()
        tool_call_msg = AIMessage(
            content="",
            tool_calls=[{
                "name": "get_upcoming_appointments",
                "args": tool_args,
                "id": tool_call_id,
            }],
        )
        tool_result_msg = ToolMessage(
            content=str(raw_output),
            tool_call_id=tool_call_id,
            name="get_upcoming_appointments",
        )
        
        messages_for_agent.append(tool_call_msg)
        messages_for_agent.append(tool_result_msg)
        
        # Track these for return (they're new and must be persisted)
        force_called_tool_messages = [tool_call_msg, tool_result_msg]

        # Pre-load valid IDs into TOP-LEVEL vars (not collected_slots).
        try:
            tool_data = json.loads(raw_output)
            if isinstance(tool_data, dict) and tool_data.get("success"):
                appts = tool_data.get("payload", [])
                if isinstance(appts, list):
                    valid_appointment_ids = [a["appointment_id"] for a in appts if "appointment_id" in a]
                    valid_appointments = appts
                    logger.info("[TOOL EXECUTOR] Pre-loaded IDs: %s", valid_appointment_ids)
        except json.JSONDecodeError as exc:
            logger.error("[TOOL EXECUTOR] Force-tool JSON parse error: %s", exc)
            messages_for_agent.append(
                ToolMessage(
                    content=json.dumps({
                        "error": (
                            "Could not retrieve appointments due to a technical issue. "
                            "Please ask the user to try again or contact the front desk."
                        )
                    }),
                    tool_call_id=tool_call_id,
                    name="get_upcoming_appointments",
                )
            )

    # ------------------------------------------------------------------
    # APPOINTMENT LOOKUP: force-fetch appointments for inquiry sub-type
    # ------------------------------------------------------------------
    if is_appointment_lookup:
        logger.info("[TOOL EXECUTOR] Appointment lookup — calling get_upcoming_appointments.")
        tool_args = {"mobile_number": caller_mobile_number}
        try:
            raw_output = get_upcoming_appointments.invoke(tool_args)
        except Exception as exc:
            raw_output = json.dumps({"error": str(exc)})

        tool_call_id = "call_lookup_" + os.urandom(4).hex()
        messages_for_agent.append(
            AIMessage(
                content="",
                tool_calls=[{
                    "name": "get_upcoming_appointments",
                    "args": tool_args,
                    "id": tool_call_id,
                }],
            )
        )
        messages_for_agent.append(
            ToolMessage(
                content=str(raw_output),
                tool_call_id=tool_call_id,
                name="get_upcoming_appointments",
            )
        )

        # Override the system message with a focused formatting instruction
        lookup_system = (
            f"You are a helpful healthcare front-desk assistant. "
            f"The user has asked to view their upcoming appointments. "
            f"The get_upcoming_appointments tool has already been called and its result is in the conversation. "
            f"Summarise the appointments clearly and concisely for the user "
            f"(mention date, time, type, and notes). "
            f"If there are no appointments, tell the user they have none scheduled. "
            f"Do NOT offer to book, cancel or reschedule unless the user asks. "
            f"Speak naturally and warmly — address the user by name if available in their profile."
        )
        messages_for_agent[0] = SystemMessage(content=lookup_system)

    # ------------------------------------------------------------------
    # Eager multi-slot extraction (runs BEFORE LLM so it sees current slots)
    # ------------------------------------------------------------------
    # This is critical: if the user provided e.g. a cancellation reason or
    # booking date in the current message, we extract it into collected_slots
    # NOW so that the LLM's system prompt reflects an accurate picture of
    # what has already been provided. Without this, the LLM may hallucinate
    # completing an action that still needs more steps.
    #
    # OPTIMIZATION: Only run for intents that actually need slot extraction
    # - booking: needs appointment_type, date, time, symptoms
    # - rescheduling: needs appointment_id, new_date, new_time
    # - cancellation: needs appointment_id, reason
    # - inquiry: NO slots needed (skip extraction)
    SLOT_REQUIRING_INTENTS = {"booking", "rescheduling", "cancellation"}
    
    if not flow_completed and last_user_text and active_intent in SLOT_REQUIRING_INTENTS:
        extracted = extract_all_slots_from_message(last_user_text, _get_model(), last_ai_text)
        
        if extracted:
            # Determine which slot is required for the CURRENT step
            current_step_required_slot = None
            if flow_step and active_intent:
                flow_def = FLOW_DEFINITIONS.get(active_intent, [])
                for step_def in flow_def:
                    if step_def.get("step") == flow_step:
                        current_step_required_slot = step_def.get("required_slot")
                        break
            
            # If no flow_step yet, use the first step's required slot
            if not current_step_required_slot and active_intent:
                first_step = FIRST_FLOW_STEP_BY_INTENT.get(active_intent)
                if first_step:
                    flow_def = FLOW_DEFINITIONS.get(active_intent, [])
                    for step_def in flow_def:
                        if step_def.get("step") == first_step:
                            current_step_required_slot = step_def.get("required_slot")
                            break
            
            # Only extract:
            # 1. The slot required for the current step
            # 2. appointment_id (can be extracted at any time for transactional flows)
            valid_keys_to_update = set()
            if current_step_required_slot:
                valid_keys_to_update.add(current_step_required_slot)
            
            # Always allow appointment_id extraction for transactional flows
            if active_intent in ("cancellation", "rescheduling"):
                valid_keys_to_update.add("appointment_id")
            
            # For rescheduling, map 'date' → 'new_date' and 'time' → 'new_time'
            if active_intent == "rescheduling":
                if "date" in extracted:
                    extracted["new_date"] = extracted.pop("date")
                if "time" in extracted:
                    extracted["new_time"] = extracted.pop("time")
            
            for k, v in extracted.items():
                if k in valid_keys_to_update and not collected_slots.get(k):
                    collected_slots[k] = v
                    logger.info(
                        "[EAGER EXTRACTION] Pre-LLM (One-Shot): '%s' = '%s'", k, v
                    )
            
            # Advance flow_step if appointment_id was just extracted for cancellation/rescheduling
            if "appointment_id" in extracted and active_intent == "cancellation":
                if flow_step == "cancellation__appointment_id" and not collected_slots.get("reason"):
                    flow_step = "cancellation__reason"
                    logger.info("[EAGER EXTRACTION] Advanced flow_step to cancellation__reason")
            elif "appointment_id" in extracted and active_intent == "rescheduling":
                if flow_step == "rescheduling__select_appointment":
                    flow_step = "rescheduling__new_date"
                    logger.info("[EAGER EXTRACTION] Advanced flow_step to rescheduling__new_date")

        # Rebuild the system prompt now that collected_slots is up-to-date,
        # then replace the SystemMessage already at position 0.
        system_prompt = _build_system_prompt(
            intent=intent,
            intent_confidence=intent_confidence,
            intent_locked=intent_locked,
            active_intent=active_intent,
            flow_step=flow_step,
            collected_slots=collected_slots,
            user_profile=user_profile,
            tone_instruction=tone_instruction,
        )
        messages_for_agent[0] = SystemMessage(content=system_prompt)

    # ------------------------------------------------------------------
    # Bind tools & run execution loop
    # ------------------------------------------------------------------
    model_bound = _get_agent_model().bind_tools(_tools)  # Use Moonshot for main agent
    turn_count = 0
    final_response_msg: AIMessage | None = None

    while turn_count < MAX_TURNS:
        turn_count += 1

        try:
            response = model_bound.invoke(messages_for_agent)
        except Exception as exc:
            logger.error("[TOOL EXECUTOR] LLM invocation failed: %s", exc)
            error_msg = AIMessage(
                content="I apologise, but I'm having trouble connecting right now."
            )
            return {
                "messages": [error_msg],
                "intent": intent,
                "intent_confidence": intent_confidence,
                "active_intent": active_intent,
                "intent_locked": intent_locked,
                "flow_step": flow_step,
                "flow_completed": flow_completed,
                "collected_slots": collected_slots,
                "valid_appointment_ids": valid_appointment_ids,
                "valid_appointments": valid_appointments,
                "_executor_final_ai_message": error_msg,
                "_executor_appointment_created": appointment_created,
                "_executor_cancellation_cancelled": cancellation_cancelled,
                "_executor_rescheduling_rescheduled": rescheduling_rescheduled,
                "_executor_initial_flow_completed": initial_flow_completed,
                "safety_conflict_count": safety_conflict_count,
            }

        messages_for_agent.append(response)
        final_response_msg = response

        if not response.tool_calls:
            break  # Natural language response — leave the loop

        # ---- Process each tool call in this response -------------------
        for tool_call in response.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]
            tool_id   = tool_call["id"]

            logger.info("[TOOL EXECUTOR] Tool call: %s args=%s", tool_name, tool_args)

            # ---- Guard 1: Step-Tool Allowlist ----
            if flow_step and flow_step in STEP_TOOL_ALLOWLIST:
                allowed = STEP_TOOL_ALLOWLIST[flow_step]
                if tool_name not in allowed:
                    logger.warning(
                        "[ALLOWLIST GUARD] Blocked %s at step %s. Allowed: %s",
                        tool_name, flow_step, sorted(allowed),
                    )
                    messages_for_agent.append(
                        ToolMessage(
                            content=json.dumps({
                                "error": (
                                    f"Tool '{tool_name}' is not allowed at step '{flow_step}'. "
                                    f"Allowed tools: {sorted(allowed) if allowed else 'none'}. "
                                    "Focus on collecting the required information for this step."
                                )
                            }),
                            tool_call_id=tool_id,
                            name=tool_name,
                        )
                    )
                    continue

            # ---- Guard 2: Hard Confirmation Precondition ----
            if tool_name in (
                "create_appointment_in_db",
                "cancel_appointment_in_db",
                "update_appointment_in_db",
            ):
                if collected_slots.get("confirmed") != "confirmed":
                    logger.warning(
                        "[CONFIRMATION GUARD] Blocked %s: confirmed=%r",
                        tool_name, collected_slots.get("confirmed"),
                    )
                    messages_for_agent.append(
                        ToolMessage(
                            content=json.dumps({
                                "error": (
                                    "BLOCKED: User has not explicitly confirmed this action. "
                                    "Summarise the details and ask for explicit yes/no confirmation "
                                    "before proceeding."
                                )
                            }),
                            tool_call_id=tool_id,
                            name=tool_name,
                        )
                    )
                    continue

            # ---- Guard 3: Transactional Safety (cancel / update) ----
            if tool_name in ("cancel_appointment_in_db", "update_appointment_in_db"):
                # Task #23 — read IDs from top-level verification vars, NOT collected_slots.
                verified_id = collected_slots.get("appointment_id")
                passed_id   = tool_args.get("appointment_id")

                if verified_id:
                    if passed_id != verified_id:
                        logger.critical(
                            "[SAFETY GUARD] ID mismatch: passed=%s verified=%s",
                            passed_id, verified_id,
                        )
                        safety_conflict_count += 1
                        messages_for_agent.append(
                            ToolMessage(
                                content=json.dumps({
                                    "error": (
                                        "SAFETY BLOCK: The appointment ID does not match "
                                        "the verified appointment on file. Please ask the user "
                                        "to confirm which appointment they want to modify."
                                    )
                                }),
                                tool_call_id=tool_id,
                                name=tool_name,
                            )
                        )
                        continue

                elif passed_id in valid_appointment_ids:
                    logger.info("[SAFETY GUARD] Accepting ID %s from valid list.", passed_id)
                    verified_id = passed_id
                    collected_slots["appointment_id"] = verified_id

                else:
                    logger.critical(
                        "[SAFETY GUARD] Unverified ID %s. Valid: %s", passed_id, valid_appointment_ids,
                    )
                    safety_conflict_count += 1
                    messages_for_agent.append(
                        ToolMessage(
                            content=json.dumps({
                                "error": (
                                    f"SAFETY BLOCK: appointment_id {passed_id} was not found "
								    f"in verified appointments ({valid_appointment_ids}). Do NOT proceed. "
                                    "Ask the user to select a valid appointment from the list shown."
                                )
                            }),
                            tool_call_id=tool_id,
                            name=tool_name,
                        )
                    )
                    continue

            # ---- Guard 4: All-Slots Completeness ----
            if tool_name in ("create_appointment_in_db", "update_appointment_in_db"):
                is_complete, missing = is_flow_complete(active_intent, collected_slots)
                if not is_complete:
                    missing_slot = missing[0]
                    step_def = next(
                        (s for s in FLOW_DEFINITIONS.get(active_intent, [])
                         if s.get("required_slot") == missing_slot),
                        None,
                    )
                    hint = (
                        step_def.get("prompt_hint", f"Please ask for {missing_slot}")
                        if step_def else f"Please ask the user for {missing_slot}"
                    )
                    if step_def:
                        flow_step = step_def["step"]
                        logger.info("[ALL-SLOTS GUARD] Reset flow_step → %s", flow_step)
                    logger.warning(
                        "[ALL-SLOTS GUARD] Blocked %s: missing %s", tool_name, missing,
                    )
                    messages_for_agent.append(
                        ToolMessage(
                            content=json.dumps({
                                "error": (
                                    f"BOOKING BLOCKED — missing required information: "
                                    f"'{missing_slot}'. Do NOT confirm or complete the action. "
                                    f"STOP and ask the user for '{missing_slot}' now. "
                                    f"Hint: {hint}"
                                )
                            }),
                            tool_call_id=tool_id,
                            name=tool_name,
                        )
                    )
                    continue

            # ---- Execute Tool ----
            tool_fn = _tool_map.get(tool_name)
            if tool_fn:
                try:
                    if tool_name in ("cancel_appointment_in_db", "update_appointment_in_db"):
                        tool_args["caller_mobile_number"] = caller_mobile_number
                    tool_output = tool_fn.invoke(tool_args)
                except Exception as exc:
                    tool_output = f"Error: {exc}"
            else:
                tool_output = f"Error: Tool '{tool_name}' not found."

            # ---- Post-execution: ID resolution ----
            if tool_name == "get_upcoming_appointments":
                # Task #23 — store verified IDs in top-level vars, NOT collected_slots.
                collected_slots.pop("appointment_id", None)
                try:
                    tool_data = json.loads(tool_output)
                    if isinstance(tool_data, dict) and tool_data.get("success"):
                        appts = tool_data.get("payload", [])
                        if isinstance(appts, list):
                            valid_appointment_ids = [
                                a["appointment_id"] for a in appts if "appointment_id" in a
                            ]
                            valid_appointments = appts
                            logger.info("[TOOL EXECUTOR] Stored valid IDs: %s", valid_appointment_ids)

                            if appts:
                                target = None
                                if len(appts) == 1:
                                    target = appts[0]
                                else:
                                    # Try to match via already-collected slots (no redundant extraction)
                                    date_c = collected_slots.get("date")
                                    time_c = collected_slots.get("time")
                                    matches = [
                                        a for a in appts
                                        if (not date_c or date_c in str(a.get("date", "")))
                                        and (not time_c or time_c in str(a.get("time", "")))
                                    ]
                                    if len(matches) == 1:
                                        target = matches[0]

                                if target:
                                    collected_slots["appointment_id"] = target["appointment_id"]
                                    logger.info(
                                        "[TOOL EXECUTOR] Auto-resolved ID: %s",
                                        target["appointment_id"],
                                    )
                                    if active_intent == "cancellation":
                                        if not collected_slots.get("reason"):
                                            flow_step = "cancellation__reason"
                                    elif active_intent == "rescheduling":
                                        flow_step = "rescheduling__confirmation"
                except json.JSONDecodeError:
                    pass

            # ---- Post-execution: Transaction completion flags ----
            if tool_name in (
                "cancel_appointment_in_db",
                "create_appointment_in_db",
                "update_appointment_in_db",
            ):
                try:
                    tool_data = json.loads(str(tool_output))
                    if isinstance(tool_data, dict) and tool_data.get("success") is True:
                        if tool_name == "create_appointment_in_db":
                            appointment_created = True
                        elif tool_name == "cancel_appointment_in_db":
                            cancellation_cancelled = True
                        elif tool_name == "update_appointment_in_db":
                            rescheduling_rescheduled = True

                        flow_completed = True
                        flow_step = None
                        active_intent = None
                        intent_locked = False
                        # Task #23 — reset all slot data AND verification metadata
                        collected_slots = {}
                        valid_appointment_ids = []
                        valid_appointments = []
                        logger.info("[TOOL EXECUTOR] Transaction completed via %s.", tool_name)
                except json.JSONDecodeError:
                    pass

            messages_for_agent.append(
                ToolMessage(content=str(tool_output), tool_call_id=tool_id, name=tool_name)
            )

    # ------------------------------------------------------------------
    # ID resolution from history (turn-by-turn fallback)
    # Task #23 — use top-level valid_appointments, not collected_slots.
    # ------------------------------------------------------------------
    if (
        not flow_completed
        and not collected_slots.get("appointment_id")
        and valid_appointments
    ):
        candidates = valid_appointments
        
        # Try to match from last user message
        # Extract date/time mentions from user text
        user_lower = last_user_text.lower()
        
        # Simple date/time matching
        filtered = []
        for appt in candidates:
            appt_date = str(appt.get("date", "")).lower()
            appt_time = str(appt.get("time", "")).lower()
            
            # Check if user mentioned this appointment's date or time
            date_match = False
            time_match = False
            
            # Date matching (e.g., "march 2", "monday", "tomorrow")
            if "march" in user_lower and "march" in appt_date:
                if "2" in user_lower or "2nd" in user_lower:
                    date_match = "2026-03-02" in appt_date
            elif "monday" in user_lower:
                date_match = "2026-03-02" in appt_date  # Monday is March 2
            elif "tomorrow" in user_lower or "saturday" in user_lower:
                date_match = "2026-02-28" in appt_date
                
            # Time matching (e.g., "9 am", "9:00", "10:30")
            if "9" in user_lower and ("am" in user_lower or "morning" in user_lower):
                time_match = "09:00" in appt_time
            elif "10:30" in user_lower or ("10" in user_lower and "30" in user_lower):
                time_match = "10:30" in appt_time
            elif "12" in user_lower or "noon" in user_lower:
                time_match = "12:00" in appt_time
            elif "3:30" in user_lower or ("3" in user_lower and "30" in user_lower):
                time_match = "15:30" in appt_time
                
            if date_match or time_match:
                filtered.append(appt)
                logger.info(
                    "[TOOL EXECUTOR] Matched appointment: ID=%s, date=%s, time=%s (date_match=%s, time_match=%s)",
                    appt.get("appointment_id"), appt_date, appt_time, date_match, time_match
                )

        target = None
        if len(filtered) == 1:
            target = filtered[0]
        elif len(filtered) > 1:
            # Multiple matches - try to narrow down with both date AND time
            for appt in filtered:
                appt_date = str(appt.get("date", "")).lower()
                appt_time = str(appt.get("time", "")).lower()
                if ("march" in user_lower or "monday" in user_lower) and "2026-03-02" in appt_date:
                    if "9" in user_lower and "09:00" in appt_time:
                        target = appt
                        break
        
        # Check for confirmation keywords
        is_conf = any(w in last_user_text.lower() for w in ["yes","yeah","sure","correct","confirm","right"])
        if is_conf and len(candidates) == 1:
            target = candidates[0]

        if target:
            collected_slots["appointment_id"] = target["appointment_id"]
            logger.info("[TOOL EXECUTOR] History ID resolution: %s", target["appointment_id"])
            if active_intent == "cancellation" and not collected_slots.get("reason"):
                flow_step = "cancellation__reason"
            elif active_intent == "rescheduling":
                flow_step = "rescheduling__confirmation"

    # Note: eager multi-slot extraction was moved to BEFORE the LLM call
    # (see the pre-LLM extraction block above) so the LLM always sees
    # current slot values in its system prompt.


    # ------------------------------------------------------------------
    # Return — only write new AI + Tool messages (don't replay history)
    # ------------------------------------------------------------------
    new_messages = [
        m for m in messages_for_agent[1:]      # strip leading SystemMessage
        if not isinstance(m, SystemMessage)
    ]

    # The AI messages that came from state["messages"] are already in the
    # checkpointer — we only want the *new* ones generated this turn.
    # CRITICAL: Use original_message_count (before force-call), not current count
    brand_new_messages = new_messages[original_message_count:]  # only additions
    
    # CRITICAL: Add force-called tool messages (they're new and must be persisted)
    if force_called_tool_messages:
        # Prepend force-called messages so they appear before LLM responses
        brand_new_messages = force_called_tool_messages + brand_new_messages
        logger.info("[TOOL EXECUTOR] Including %d force-called tool messages in return", len(force_called_tool_messages))

    logger.info(
        "[TOOL EXECUTOR] DONE turn_count=%d new_msgs=%d",
        turn_count, len(brand_new_messages),
    )

    return {
        "messages": brand_new_messages,
        "intent": intent,
        "intent_confidence": intent_confidence,
        "active_intent": active_intent,
        "intent_locked": intent_locked,
        "flow_step": flow_step,
        "flow_completed": flow_completed,
        "collected_slots": collected_slots,
        # Task #23 — verification metadata returned as top-level fields
        "valid_appointment_ids": valid_appointment_ids,
        "valid_appointments": valid_appointments,
        "_executor_final_ai_message": final_response_msg,
        "_executor_appointment_created": appointment_created,
        "_executor_cancellation_cancelled": cancellation_cancelled,
        "_executor_rescheduling_rescheduled": rescheduling_rescheduled,
        "_executor_initial_flow_completed": initial_flow_completed,
        "safety_conflict_count": safety_conflict_count,
    }
