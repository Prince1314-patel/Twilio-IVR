"""
Slot Extraction Module
======================

This module provides LLM-based slot extraction from user messages during
transactional flows. It uses the same LLM to extract structured data based
on the current flow step and validates the extracted values.

Author: Advanced AI Systems Team
Last Modified: 2026-02-10
"""

import re
import datetime
from zoneinfo import ZoneInfo
from typing import Any, Tuple, Optional

from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from app.core.logger_config import get_ai_agent_logger

logger = get_ai_agent_logger()

# Dedicated low-temperature model for deterministic slot extraction
from app.ai.llm.client_factory import create_llm_model as _create_llm
_extraction_model = None

def _get_extraction_model():
    """Lazy-init a temperature=0.0 model for deterministic extraction."""
    global _extraction_model
    if _extraction_model is None:
        _extraction_model = _create_llm(temperature=0.0, purpose="extraction")
    return _extraction_model


class AppointmentSlots(BaseModel):
    """Pydantic model containing all possible appointment slots for one-shot extraction."""
    appointment_type: Optional[str] = Field(None, description="Type of appointment: regular, followup, or emergency. ONLY extract if explicitly stated.")
    date: Optional[str] = Field(None, description="Preferred appointment date in YYYY-MM-DD. Convert relative dates (today, tomorrow, next Monday etc.).")
    time: Optional[str] = Field(None, description="Preferred appointment time in HH:MM:SS format 24-hour.")
    symptoms: Optional[str] = Field(None, description="Reason for the appointment, symptoms, or concerns mentioned.")
    appointment_id: Optional[str] = Field(None, description="Appointment ID if mentioned, usually strictly numeric.")
    new_date: Optional[str] = Field(None, description="New preferred date in YYYY-MM-DD format for rescheduling.")
    new_time: Optional[str] = Field(None, description="New preferred time in HH:MM:SS format for rescheduling.")
    reason: Optional[str] = Field(None, description="Reason for cancellation or changing the appointment.")
    confirmed: Optional[str] = Field(None, description="Determines if user confirmed (yes/confirmed) or rejected (no/cancel).")

def extract_all_slots_from_message(
    message: str,
    llm_model,
    last_ai_message: str = None,
) -> dict:
    """
    Extract all slot values from user message in one structured LLM call.
    
    Args:
        message: User's message text
        llm_model: LLM model instance for extraction
        last_ai_message: Optional last AI message for context
        
    Returns:
        Dictionary with extracted and validated slot data, e.g., {"date": "2026-02-11", "time": "15:00:00"}
    """
    if not message:
        return {}
        
    current_date = datetime.datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d")
    current_day = datetime.datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%A")
    
    context_instruction = ""
    if last_ai_message:
        context_instruction = f"""
CONVERSATION CONTEXT:
AI's last message: "{last_ai_message}"
User's response: "{message}"

Use the AI's message to understand what the user is responding to. For example:
- If AI asked about a specific appointment and user says "yes", extract that appointment's details.
- If AI asked for confirmation and user says "yes", extract confirmed=yes.
- If AI mentioned a date/time and user says "yes" or "that works", extract that date/time.
"""
    
    system_prompt = f"""Extract all relevant appointment slots from the user's message.
Today is {current_date} ({current_day}).
{context_instruction}
CRITICAL INSTRUCTIONS:
- Convert relative dates ("today", "tomorrow", "next Monday") to YYYY-MM-DD.
- Convert times to HH:MM:SS 24-hour format.
- For appointment_type: valid types are regular, emergency, followup. Do NOT infer from symptoms (e.g. fever is NOT emergency unless explicitly stated).
- For confirmed: return yes/no/none.
- If a piece of information is perfectly clear in the message, extract it. Otherwise leave it null.
- You MUST call the function with the extracted data. Do NOT return conversational text.
"""
    
    # attempt one-shot structured extraction using Pydantic schema
    try:
        extractor = llm_model.with_structured_output(AppointmentSlots)
        
        # Build messages with context if available
        messages_for_extraction = [("system", system_prompt)]
        if last_ai_message:
            messages_for_extraction.append(("assistant", last_ai_message))
        messages_for_extraction.append(("user", message))
        
        prompt_template = ChatPromptTemplate.from_messages(messages_for_extraction)

        # ``prompt_template | extractor`` should yield a LangChain "chain";
        # some providers (eg. Groq) do not support structured output / function
        # calling and will raise a 400 when we try to invoke it.  In that case we
        # catch the exception below and fall back to a safer per-slot approach.
        chain = prompt_template | extractor
        result = chain.invoke({})

        raw_slots = result.model_dump(exclude_none=True)

        logger.debug(
            f"[SLOT EXTRACTION - ONE SHOT] msg='{message[:50]}...', extracted='{raw_slots}'"
        )

        validated_slots = {}
        for k, v in raw_slots.items():
            if k == "confirmed" and v:
                # normalize validation for confirmed vs confirmation string usage
                is_valid, norm_v = validate_slot_value("confirmed", str(v))
                if is_valid:
                    validated_slots[k] = norm_v
                continue

            is_valid, norm_v = validate_slot_value(k, v)
            if is_valid:
                validated_slots[k] = norm_v

        return validated_slots

    except Exception as e:
        # Groq in particular will return a 400 invalid_request_error when
        # the chain tries to "call a function" for structured output.  The
        # message typically contains 'tool_use_failed' and the raw text of a
        # conversational reply.  We log the full exception for diagnostics
        # but then fall back to a safer loop that extracts each slot
        # individually using the existing `extract_slots_from_message()`
        # helper.  This ensures slot extraction keeps working even if the
        # LLM provider doesn't support LangChain's structured-output helpers.
        logger.error(f"[SLOT EXTRACTION - ONE SHOT] Error extracting slots: {e}")

        # fallback: call the single-slot extractor for each field defined in
        # the AppointmentSlots model.
        fallback_slots: dict = {}
        for field in AppointmentSlots.__fields__:
            if field in ("appointment_type", "date", "time", "symptoms",
                         "appointment_id", "new_date", "new_time",
                         "reason", "confirmed"):
                extracted = extract_slots_from_message(
                    message, "", field, llm_model, last_ai_message
                )
                if extracted:
                    # validate_slots is already performed by underlying
                    # helper, so we can just merge results
                    fallback_slots.update(extracted)
        if fallback_slots:
            logger.info(
                "[SLOT EXTRACTION] Fallback multi-slot extraction succeeded: %s",
                fallback_slots,
            )
        return fallback_slots


def extract_slots_from_message(
    message: str,
    current_step: str,
    required_slot: str,
    llm_model,
    last_ai_message: str = None,
) -> dict:
    """
    Extract slot values from user message based on current step.
    
    Uses LLM with specialized prompt to identify and extract the specific
    data required by the current flow step.
    
    Args:
        message: User's message text
        current_step: Current flow step (e.g., "booking__date")
        required_slot: Slot to extract (e.g., "date")
        llm_model: LLM model instance for extraction
        last_ai_message: Optional last AI message for context
        
    Returns:
        Dictionary with extracted slot data, e.g., {"date": "2026-02-11"}
        Returns empty dict if extraction fails or no data found
    """
    if not message or not required_slot:
        return {}
    
    # Fast-path: confirmation is a deterministic yes/no — no LLM needed
    if required_slot in ("confirmed", "confirmation"):
        is_valid, normalized = validate_slot_value(required_slot, message.strip())
        if is_valid:
            return {required_slot: normalized}
        return {}
    
    # Build extraction prompt based on slot type
    extraction_prompt = _build_extraction_prompt(required_slot, message, last_ai_message)
    
    try:
        # Use LLM to extract the slot value
        messages_for_extraction = [("system", extraction_prompt)]
        if last_ai_message:
            messages_for_extraction.append(("assistant", last_ai_message))
        messages_for_extraction.append(("user", message))
        
        prompt_template = ChatPromptTemplate.from_messages(messages_for_extraction)
        
        # Use dedicated extraction model (temp=0.0) for deterministic extraction
        extraction_llm = _get_extraction_model()
        chain = prompt_template | extraction_llm | StrOutputParser()
        extracted_value = chain.invoke({})
        
        logger.debug(
            f"[SLOT EXTRACTION] step={current_step}, slot={required_slot}, "
            f"message='{message[:50]}...', extracted='{extracted_value}'"
        )
        
        # Validate and normalize the extracted value
        is_valid, normalized_value = validate_slot_value(required_slot, extracted_value)
        
        if is_valid:
            return {required_slot: normalized_value}
        else:
            logger.debug(
                f"[SLOT EXTRACTION] Validation failed for {required_slot}='{extracted_value}'"
            )
            return {}
            
    except Exception as e:
        logger.error(f"[SLOT EXTRACTION] Error extracting {required_slot}: {e}")
        return {}


def _build_extraction_prompt(slot_name: str, user_message: str, last_ai_message: str = None) -> str:
    """Build extraction prompt based on slot type."""
    
    context_note = ""
    if last_ai_message:
        context_note = f"""
CONVERSATION CONTEXT:
AI's last message: "{last_ai_message}"
User's response: "{user_message}"

Use the AI's message to understand what the user is responding to.
"""
    
    base_instruction = (
        "Extract ONLY the requested information from the user's message. "
        "Return ONLY the extracted value, nothing else. "
        "If the information is not present, return 'NONE'."
        f"{context_note}"
    )
    
    if slot_name == "appointment_type":
        return f"""{base_instruction}

Extract the appointment type ONLY if the user explicitly states it.
Valid types are: regular, emergency, followup.

Accepted phrasings:
- "regular", "regular checkup", "routine", "normal" → regular
- "emergency", "urgent", "asap", "it's urgent" → emergency
- "follow-up", "followup", "follow up visit" → followup

CRITICAL RULES:
- Do NOT infer the appointment type from symptoms (e.g. "fever", "chest pain") alone.
- Do NOT guess. If the user has not explicitly said regular/emergency/followup, return NONE.
- "I have a fever" alone is NOT enough to return emergency — the user must explicitly say the type.

Return ONLY one of: regular, emergency, followup
If the user has not explicitly stated the appointment type, return: NONE"""

    elif slot_name == "date" or slot_name == "new_date":
        current_date = datetime.datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d")
        current_day = datetime.datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%A")
        
        return f"""{base_instruction}

Today is {current_date} ({current_day}).

Extract the appointment date from the user's message.
Convert relative dates to YYYY-MM-DD format:
- "today" → {current_date}
- "tomorrow" → calculate next day
- "next Monday" → calculate next Monday
- "15th" or "15 February" → convert to YYYY-MM-DD

Return ONLY the date in YYYY-MM-DD format.
If no date mentioned, return: NONE"""

    elif slot_name == "time" or slot_name == "new_time":
        return f"""{base_instruction}

Extract the appointment time from the user's message.
Convert to HH:MM:SS 24-hour format:
- "5 PM" → 17:00:00
- "10 in the morning" → 10:00:00
- "2:30" → 14:30:00 (if PM context) or 02:30:00 (if AM context). If completely ambiguous or no AM/PM provided, assume typical business hours (08:00-18:00).
- "5 o'clock" → infer AM/PM from context, default to business hours (08:00-18:00).

Return ONLY the time in HH:MM:SS format.
If no time mentioned, return: NONE"""

    elif slot_name == "symptoms":
        return f"""{base_instruction}

Extract the reason for the appointment or symptoms mentioned.
This could be:
- Specific symptoms: "headache", "fever", "chest pain"
- General reasons: "regular checkup", "follow-up", "just a checkup"
- Health concerns: "not feeling well", "pain in my back"

If user says "no", "none", "nothing specific" → return: none

Return the exact phrase they used, or "none" if they indicated no specific reason.
If they didn't mention it yet, return: NONE"""

    elif slot_name == "appointment_id":
        context_hint = ""
        if last_ai_message:
            context_hint = f"""
CONVERSATION CONTEXT - CRITICAL:
The AI just said: "{last_ai_message}"
The user responded: "{user_message}"

EXTRACTION RULES:
1. If the AI mentioned a specific appointment (with date, time, or ID) and the user responded affirmatively ("yes", "that one", "correct", "sure", etc.):
   - Extract the appointment ID from the AI's message
   - Look for patterns like "appointment ID is X", "ID: X", "appointment X", or dates/times that identify an appointment
   
2. If the user explicitly mentioned an appointment ID in their message, extract that instead.

3. If neither the AI nor user mentioned a specific ID, return NONE.
"""
        return f"""{base_instruction}
{context_hint}
Extract the appointment ID from the conversation.
This is typically a number or alphanumeric code.

Return ONLY the appointment ID number.
If not mentioned in either message, return: NONE"""

    elif slot_name == "reason":
        return f"""{base_instruction}

Extract the reason for cancellation/change mentioned by the user.
This could be any explanation like:
- "Something came up"
- "I have a conflict"
- "Feeling better already"
- "Need to reschedule"

Return the exact phrase they used.
If they didn't provide a reason, return: none"""

    elif slot_name == "confirmed" or slot_name == "confirmation":
        return f"""{base_instruction}

Determine if the user confirmed, agreed, or rejected.

AFFIRMATIVE (return: yes):
- "yes", "yeah", "yep", "yup", "sure", "correct", "that's right", "right"
- "okay", "ok", "alright", "all right"
- "confirmed", "sounds good", "looks good", "perfect", "great"
- "go ahead", "proceed", "book it", "do it", "please do", "please proceed"
- "absolutely", "definitely", "of course"

NEGATIVE (return: no):
- "no", "nope", "nah", "not quite", "that's wrong", "incorrect"
- "wait", "hold on", "stop", "let me change", "actually"
- "cancel", "don't", "do not"

Return ONLY: yes, no, or NONE (if truly unclear)"""

    else:
        # Generic extraction for unknown slots
        return f"""{base_instruction}

Extract the value for "{slot_name}" from the user's message.
Return ONLY the extracted value, or NONE if not present."""


def validate_slot_value(slot_name: str, value: Any) -> Tuple[bool, Optional[Any]]:
    """
    Validate and normalize extracted slot value.
    
    Args:
        slot_name: Name of the slot
        value: Extracted value to validate
        
    Returns:
        Tuple of (is_valid, normalized_value)
    """
    if not value or str(value).upper() == "NONE":
        return False, None
    
    value_str = str(value).strip()
    
    try:
        # Appointment type validation
        if slot_name == "appointment_type":
            normalized = value_str.lower()
            if normalized in ["regular", "emergency", "followup"]:
                return True, normalized
            # Handle common variations
            if normalized in ["regular", "normal", "checkup"]:
                return True, "regular"
            if normalized in ["urgent", "asap"]:
                return True, "emergency"
            if normalized in ["follow-up", "follow up"]:
                return True, "followup"
            return False, None
        
        # Date validation
        if slot_name in ["date", "new_date"]:
            # Try to parse YYYY-MM-DD format
            try:
                parsed_date = datetime.datetime.strptime(value_str, "%Y-%m-%d")
                # Check if date is in the future
                now = datetime.datetime.now(ZoneInfo("Asia/Kolkata"))
                if parsed_date.date() >= now.date():
                    return True, value_str
                else:
                    logger.warning(f"Date {value_str} is in the past")
                    return False, None
            except ValueError:
                logger.warning(f"Invalid date format: {value_str}")
                return False, None
        
        # Time validation
        if slot_name in ["time", "new_time"]:
            # Try to parse HH:MM:SS format
            try:
                datetime.datetime.strptime(value_str, "%H:%M:%S")
                return True, value_str
            except ValueError:
                # Try HH:MM format and add :00
                try:
                    datetime.datetime.strptime(value_str, "%H:%M")
                    return True, f"{value_str}:00"
                except ValueError:
                    logger.warning(f"Invalid time format: {value_str}")
                    return False, None
        
        # Appointment ID validation
        if slot_name == "appointment_id":
            # Should be numeric
            if value_str.isdigit():
                return True, int(value_str)
            return False, None
        
        # Confirmation validation
        if slot_name in ["confirmed", "confirmation"]:
            normalized = value_str.strip().lower()
            affirmative = {
                "yes", "yeah", "yep", "yup", "sure", "correct", "confirmed",
                "true", "okay", "ok", "alright", "all right", "sounds good",
                "looks good", "perfect", "great", "go ahead", "proceed",
                "book it", "do it", "please do", "please proceed",
                "absolutely", "definitely", "of course", "right", "that's right",
            }
            negative = {
                "no", "nope", "nah", "false", "not quite", "that's wrong",
                "incorrect", "wait", "hold on", "stop", "cancel",
            }
            if normalized in affirmative:
                return True, "confirmed"
            if normalized in negative:
                return True, "rejected"
            return False, None
        
        # For other slots (symptoms, reason, etc.), accept any non-empty string
        if slot_name in ["symptoms", "reason", "notes"]:
            if len(value_str) > 0:
                # Normalize "none" or "no" to explicit "none" string
                if value_str.lower() in ["no", "none", "nothing", "n/a"]:
                    return True, "none"
                return True, value_str
            return False, None
        
        # Default: accept any non-empty value
        return True, value_str
        
    except Exception as e:
        logger.error(f"Error validating slot {slot_name}={value}: {e}")
        return False, None
