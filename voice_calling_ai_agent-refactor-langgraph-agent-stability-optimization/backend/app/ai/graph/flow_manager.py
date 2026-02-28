"""
Flow Manager Module
===================

Centralized flow progression logic for transactional intents.
Manages step transitions, completion validation, and context generation for LLM.

Author: Advanced AI Systems Team
Last Modified: 2026-02-10
"""

from typing import Optional, Tuple, List
from langchain_core.messages import SystemMessage

from app.ai.graph.state import (
    FLOW_DEFINITIONS,
    REQUIRED_SLOTS_BY_INTENT,
    FIRST_FLOW_STEP_BY_INTENT,
)
from app.core.logger_config import get_ai_agent_logger

logger = get_ai_agent_logger()


def get_step_info(active_intent: str, flow_step: str) -> Optional[dict]:
    """
    Get information about the current flow step.
    
    Args:
        active_intent: Current active intent (e.g., "booking")
        flow_step: Current flow step (e.g., "booking__date")
        
    Returns:
        Step info dict with keys: step, next_step, required_slot, prompt_hint
        Returns None if step not found
    """
    if active_intent not in FLOW_DEFINITIONS:
        logger.warning(f"[FLOW MANAGER] No flow definition for intent: {active_intent}")
        return None
    
    flow = FLOW_DEFINITIONS[active_intent]
    for step_info in flow:
        if step_info["step"] == flow_step:
            return step_info
    
    logger.warning(
        f"[FLOW MANAGER] Step {flow_step} not found in {active_intent} flow"
    )
    return None


def should_advance_step(
    current_step: str,
    collected_slots: dict,
    active_intent: str,
) -> bool:
    """
    Check if current step's requirements are satisfied and ready to advance.
    
    Args:
        current_step: Current flow step
        collected_slots: Dictionary of collected slot data
        active_intent: Current active intent
        
    Returns:
        True if step requirements met, False otherwise
    """
    step_info = get_step_info(active_intent, current_step)
    if not step_info:
        return False
    
    required_slot = step_info.get("required_slot")
    if not required_slot:
        return False
    
    # Check if the required slot has been collected
    slot_value = collected_slots.get(required_slot)
    
    if slot_value is None:
        logger.debug(
            f"[FLOW MANAGER] Step {current_step}: slot '{required_slot}' not yet collected"
        )
        return False
    
    # Optional: Run validation if defined
    validation_fn = step_info.get("validation")
    if validation_fn and callable(validation_fn):
        try:
            is_valid = validation_fn(slot_value)
            if not is_valid:
                logger.warning(
                    f"[FLOW MANAGER] Step {current_step}: slot '{required_slot}' "
                    f"validation failed for value '{slot_value}'"
                )
                return False
        except Exception as e:
            logger.error(
                f"[FLOW MANAGER] Validation error for {required_slot}: {e}"
            )
            return False
    
    logger.debug(
        f"[FLOW MANAGER] Step {current_step}: slot '{required_slot}' collected "
        f"and validated. Ready to advance."
    )
    return True


def get_next_step(active_intent: str, current_step: str) -> Optional[str]:
    """
    Get the next step in the flow sequence.
    
    Args:
        active_intent: Current active intent
        current_step: Current flow step
        
    Returns:
        Next step identifier, or None if current step is final
    """
    step_info = get_step_info(active_intent, current_step)
    if not step_info:
        return None
    
    next_step = step_info.get("next_step")
    
    logger.debug(
        f"[FLOW MANAGER] Advancing: {current_step} → {next_step or 'COMPLETE'}"
    )
    
    return next_step


def is_flow_complete(
    active_intent: str,
    collected_slots: dict,
) -> Tuple[bool, List[str]]:
    """
    Check if all required slots are collected for the flow.
    
    Args:
        active_intent: Current active intent
        collected_slots: Dictionary of collected slot data
        
    Returns:
        Tuple of (is_complete, missing_slots)
        - is_complete: True if all required slots present
        - missing_slots: List of slot names still needed
    """
    if active_intent not in REQUIRED_SLOTS_BY_INTENT:
        logger.warning(
            f"[FLOW MANAGER] No required slots defined for intent: {active_intent}"
        )
        return False, []
    
    required_slots = REQUIRED_SLOTS_BY_INTENT[active_intent]
    missing_slots = []
    
    for slot_name in required_slots:
        if slot_name not in collected_slots or collected_slots[slot_name] is None:
            missing_slots.append(slot_name)
    
    is_complete = len(missing_slots) == 0
    
    logger.debug(
        f"[FLOW MANAGER] Flow completion check: intent={active_intent}, "
        f"complete={is_complete}, missing={missing_slots}"
    )
    
    return is_complete, missing_slots


def get_flow_progress(active_intent: str, flow_step: str) -> Tuple[int, int]:
    """
    Get current progress through the flow.
    
    Args:
        active_intent: Current active intent
        flow_step: Current flow step
        
    Returns:
        Tuple of (current_step_number, total_steps)
    """
    if active_intent not in FLOW_DEFINITIONS:
        return 0, 0
    
    flow = FLOW_DEFINITIONS[active_intent]
    total_steps = len(flow)
    
    current_step_number = 0
    for i, step_info in enumerate(flow, start=1):
        if step_info["step"] == flow_step:
            current_step_number = i
            break
    
    return current_step_number, total_steps


def build_flow_context_message(
    active_intent: str,
    flow_step: str,
    collected_slots: dict,
) -> SystemMessage:
    """
    Build a comprehensive context message for the LLM with flow state.
    
    This message tells the LLM:
    - What flow they're in and current progress
    - What data has already been collected
    - What data is still needed
    - What to ask about next
    
    Args:
        active_intent: Current active intent
        flow_step: Current flow step
        collected_slots: Dictionary of collected slot data
        
    Returns:
        SystemMessage with formatted flow context
    """
    step_info = get_step_info(active_intent, flow_step)
    current_step_num, total_steps = get_flow_progress(active_intent, flow_step)
    is_complete, missing_slots = is_flow_complete(active_intent, collected_slots)
    
    # Build the context message
    lines = [
        "TRANSACTIONAL FLOW CONTEXT:",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"Intent: {active_intent} (LOCKED)",
        f"Current Step: {flow_step}",
        f"Flow Progress: {current_step_num} of {total_steps} steps",
        "",
    ]
    
    # Show collected data
    if collected_slots:
        lines.append("ALREADY COLLECTED:")
        for slot_name, slot_value in collected_slots.items():
            # Skip 'confirmed' slot in the display
            if slot_name not in ["confirmed", "confirmation"]:
                lines.append(f"✓ {slot_name}: \"{slot_value}\"")
        lines.append("")
    
    # Show missing data
    if missing_slots:
        lines.append("STILL NEEDED:")
        for slot_name in missing_slots:
            # Mark current slot as the active one
            if step_info and step_info.get("required_slot") == slot_name:
                lines.append(f"- {slot_name} (current question) ← ASK ABOUT THIS NOW")
            else:
                lines.append(f"- {slot_name}")
        lines.append("")
    
    # Current task instruction
    if step_info:
        prompt_hint = step_info.get("prompt_hint", "")
        if prompt_hint:
            lines.append(f"CURRENT TASK: {prompt_hint}")
            lines.append("")
    
    # Critical instructions
    lines.extend([
        "CRITICAL INSTRUCTIONS:",
        "- The user's next response should be their answer to your last question",
        f"- Extract the {step_info.get('required_slot', 'required data')} from their response"
            if step_info else "",
        "- Do NOT re-ask for information already collected (marked with ✓)",
        "- Do NOT skip ahead to ask about data not yet needed",
        "- Ask EXACTLY ONE question per response",
        "- Stay focused on the current step until its data is captured",
    ])

    # Hard tool-call block when any required slot is still missing
    if missing_slots:
        lines.extend([
            "",
            "⛔ TOOL CALL RESTRICTION:",
            f"The following required slots are still MISSING: {missing_slots}.",
            "You MUST NOT call create_appointment_in_db or update_appointment_in_db",
            "until ALL required slots (marked above as STILL NEEDED) have been collected.",
            f"Right now you MUST ask the user for: '{missing_slots[0]}'.",
            "Do NOT assume, invent, or guess any missing value.",
        ])
    
    # If flow is complete (all required slots filled), add confirmation instruction
    if is_complete and flow_step.endswith("__confirmation"):
        lines.extend([
            "",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "CONFIRMATION STEP:",
            "All required information has been collected.",
            "Summarize all the details and ask for explicit confirmation (yes/no).",
        ])
    
    context_text = "\n".join(lines)
    
    logger.debug(
        f"[FLOW MANAGER] Built context for {flow_step}: "
        f"{len(collected_slots)} slots collected, {len(missing_slots)} missing"
    )
    
    return SystemMessage(content=context_text)
