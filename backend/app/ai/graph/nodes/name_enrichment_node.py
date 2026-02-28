"""
Name Gate Node (formerly name_enrichment_node)
====================

LangGraph node that acts as a strict blocking gate for user name collection.
Ensures no downstream logic runs without a valid user name.

Author: Advanced AI Systems Team
Last Modified: 2026-02-09
"""

from langchain_core.messages import AIMessage, SystemMessage
from app.ai.graph.state import AgentState, FIRST_FLOW_STEP_BY_INTENT
from app.database.manager import DatabaseManager
from app.ai.llm.client_factory import create_llm_model
from app.core.logger_config import get_ai_agent_logger
import re

# Default module-level variable for test mocking
model = None

# Module-level singleton DatabaseManager instance
# Optimization: Eliminates 10-50ms connection setup overhead per call
_db_manager = DatabaseManager()

def _get_model():
    """Return Llama model for name extraction (fast and accurate).
    
    Hardcoded to use llama-3.1-8b-instant for name extraction.
    """
    import sys
    mod = sys.modules[__name__]
    if mod.model is not None:
        return mod.model
    
    # Hardcoded: Use Llama for name extraction (fast and accurate)
    from langchain_groq import ChatGroq
    from app.core.config import settings
    
    return ChatGroq(
        model="llama-3.1-8b-instant",
        temperature=0.0,
        api_key=settings.GROQ_API_KEY
    )

"""
MENTAL MODEL (Phase 3):
-----------------------
CURRENT ROLE: NameGate - The single source of truth for name collection.
responsibilities:
- BLOCK: If name is missing or invalid, stop graph execution and prompt user.
- PASS: If name is present and valid, allow graph to proceed to intelligence.
- PURE: Does NOT know about intent.
- AUTHORITATIVE: Replaces all distributed name logic.
"""

logger = get_ai_agent_logger()

# Phase 2: Escalating name collection prompts
NAME_PROMPTS = {
    "level_1_initial": "Before we proceed, may I have your name please?",
    
    "level_2_clarification": "I didn't quite catch your name. Could you please tell me your full name?",
    
    "level_3_importance": (
        "I understand your concern. We need your name to properly manage your appointment records "
        "and ensure we're updating the correct information in our system. This helps us provide you "
        "with personalized service and prevents any mix-ups with your appointments. May I have your "
        "name to continue?"
    ),
    
    "level_4_requirement": (
        "I appreciate your patience. Unfortunately, our system requires a name to create or manage "
        "appointments. This is essential for maintaining accurate medical records and ensuring your "
        "privacy. Without a name, I won't be able to proceed with booking, rescheduling, or managing "
        "your appointments. Could you please provide your name so we can continue?"
    ),
    
    "level_5_final": (
        "I completely understand if you have privacy concerns. However, providing your name is a "
        "mandatory requirement for our appointment system. Without it, I'm unable to assist you "
        "further with appointment-related services. If you'd like to proceed, please share your name. "
        "Otherwise, I can transfer you to our front desk staff who can discuss alternative options with you."
    )
}

# Phase 2: Refusal detection patterns
REFUSAL_PATTERNS = [
    "no", "nope", "nah", "i don't want",
    "why do you need", "i refuse", "not telling",
    "none of your business", "skip", "pass",
    "i'd rather not", "prefer not to", "don't want to share"
]


def _detect_refusal(user_message: str) -> bool:
    """
    Detect if user is refusing to provide their name.
    
    Args:
        user_message: User's message content
        
    Returns:
        True if refusal detected, False otherwise
    """
    message_lower = user_message.lower().strip()
    
    # Check for refusal patterns
    for pattern in REFUSAL_PATTERNS:
        if pattern in message_lower:
            return True
    
    return False



def name_enrichment_node(state: AgentState) -> AgentState:
    """
    Capture and update user's name with mandatory enforcement and escalating prompts.
    
    Phase 3: This is the NAME GATE - a hard blocker that prevents any further processing
    until the user provides their name.
    
    Returns:
    - BLOCK: name_collection_in_progress=True (Graph interrupts to wait for user)
    - PASS: name_collection_in_progress=False (Graph proceeds to next node)
    
    Escalation Strategy:
    1. Level 1: Polite request
    2. Level 2: Clarification (failed extraction)
    3. Level 3: Importance explanation (refusal detected)
    4. Level 4: System requirement (persistent refusal)
    5. Level 5: Final attempt (last chance before transfer)
    
    Args:
        state: Current agent state
        
    Returns:
        Updated state with name captured (PASS) or escalated prompt (BLOCK)
    """
    needs_enrichment = state.get("needs_name_enrichment", False)
    user_id = state.get("user_id", 0)
    
    # Phase 3: Debug logging at NameGate entry
    logger.debug(
        f"[NAME GATE ENTRY] "
        f"needs_enrichment={needs_enrichment}, "
        f"user_id={user_id}, "
        f"name_collection_in_progress={state.get('name_collection_in_progress', False)}"
    )
    
    # If name not needed, pass through
    if not needs_enrichment:
        logger.info("[NAME GATE] PASS - name not needed")
        return {"name_collection_in_progress": False}
    
    # Validate user_id exists
    if not user_id:
        logger.warning("[NAME GATE] No user_id found, cannot enforce name collection")
        return {
            "needs_name_enrichment": False,
            "name_collection_in_progress": False
        }
    
    messages = state.get("messages", [])
    prompt_level = state.get("name_prompt_level", 0)
    
    # Check if we already asked for name
    asked_for_name = _has_asked_for_name(messages)
    
    if not asked_for_name:
        # First time - Level 1: Polite request
        logger.info(f"[NAME GATE] BLOCK - Level 1: Initial polite request for user {user_id}")
        
        name_request_message = AIMessage(content=NAME_PROMPTS["level_1_initial"])
        logger.info(f"AI Response (Name Gate L1): {name_request_message.content}")
        
        return {
            "messages": [name_request_message],
            "name_collection_in_progress": True,
            "name_prompt_level": 1,
            "flow_step": "waiting_for_name"
        }
    
    # We already asked - try to extract name from last user message
    logger.info(f"[NAME GATE] Attempting name extraction for user {user_id} (prompt level: {prompt_level})")
    
    # Get last user message
    last_user_message = None
    for msg in reversed(messages):
        if hasattr(msg, 'type') and msg.type == 'human':
            last_user_message = msg.content
            break
    
    if not last_user_message:
        logger.warning("[NAME GATE] No user message found to extract name from")
        return {}
    
    # Check for refusal
    is_refusal = _detect_refusal(last_user_message)
    
    # Try to extract name
    extracted_name = _extract_name_with_llm(last_user_message)
    
    if extracted_name:
        # Success! Name extracted
        logger.info(f"[NAME GATE] Name extracted successfully: {extracted_name}")
        
        # Update database using module-level singleton (eliminates connection overhead)
        db_manager = _db_manager
        update_result = db_manager.update_user_name(user_id, extracted_name)
        
        if update_result.get("success"):
            logger.info(f"[NAME GATE] PASS - Name updated for user {user_id}: {extracted_name}")
            
            # Update user_profile in state
            user_profile = state.get("user_profile", {})
            user_profile["name"] = extracted_name
            
            # SUCCESS: Name collected
            # We must now restore the correct flow step if an intent was locked
            active_intent = state.get("active_intent")
            flow_step = None
            
            if active_intent and active_intent in FIRST_FLOW_STEP_BY_INTENT:
                # Restore the first step of the locked intent
                flow_step = FIRST_FLOW_STEP_BY_INTENT[active_intent]
                logger.info(f"[NAME GATE] Restoring flow step for locked intent '{active_intent}': {flow_step}")
            else:
                # No locked intent, just clear the waiting status
                logger.info("[NAME GATE] Name collected, clearing flow step (no locked intent)")
            
            return {
                "user_profile": user_profile,
                "needs_name_enrichment": False,
                "name_collection_in_progress": False,
                "name_prompt_level": 0,
                "flow_step": flow_step  # <--- CRITICAL FIX: Restore correct step or clear it
            }
        else:
            logger.error(f"[NAME GATE] Database update failed: {update_result.get('message')}")
            # Continue blocking - don't let them proceed without DB update
            escalation_message = AIMessage(
                content="I apologize, there was a technical issue saving your name. Could you please provide your name again?"
            )
            return {
                "messages": [escalation_message],
                "name_collection_in_progress": True,
                "name_prompt_level": prompt_level + 1,
                "flow_step": "waiting_for_name"
            }
    
    # Name extraction failed - escalate based on refusal detection and prompt level
    next_level = prompt_level + 1
    
    if is_refusal:
        # User explicitly refused - jump to level 3 (importance explanation)
        next_level = max(next_level, 3)
        logger.info(f"[NAME GATE] BLOCK - Refusal detected, escalating to level {next_level}")
    else:
        # Failed extraction (unclear response) - normal escalation
        logger.info(f"[NAME GATE] BLOCK - Failed extraction, escalating to level {next_level}")
    
    # Determine which prompt to use
    if next_level == 2:
        prompt_key = "level_2_clarification"
    elif next_level == 3:
        prompt_key = "level_3_importance"
    elif next_level == 4:
        prompt_key = "level_4_requirement"
    else:  # 5 or higher
        prompt_key = "level_5_final"
        next_level = 5  # Cap at 5
    
    escalation_message = AIMessage(content=NAME_PROMPTS[prompt_key])
    logger.info(f"[NAME GATE] AI Response (Level {next_level}): {escalation_message.content[:100]}...")
    
    return {
        "messages": [escalation_message],
        "name_collection_in_progress": True,
        "name_prompt_level": next_level,
        "flow_step": "waiting_for_name"
    }


def _has_asked_for_name(messages: list) -> bool:
    """
    Check if we already asked the user for their name.
    
    Args:
        messages: List of conversation messages
        
    Returns:
        True if we already asked for name, False otherwise
    """
    name_request_patterns = [
        "may i have your name",
        "what's your name",
        "what is your name",
        "could you tell me your name",
        "can i get your name",
        "your name please",
        "tell me your name"
    ]
    
    for msg in reversed(messages):
        if hasattr(msg, 'type') and msg.type == 'ai':
            content_lower = msg.content.lower()
            for pattern in name_request_patterns:
                if pattern in content_lower:
                    return True
    
    return False


def _extract_name_with_llm(user_message: str) -> str:
    """
    Extract user's name from their message using LLM.
    
    Args:
        user_message: User's message content
        
    Returns:
        Extracted name or empty string if not found
    """
    try:
        llm = _get_model()
        
        extraction_prompt = f"""Extract the person's full name from the following message. 
Return ONLY the name, nothing else. If no name is found, return "NONE".

IMPORTANT: Only extract actual person names. Reject:
- Company names (e.g., "Google", "Microsoft")
- Place names (e.g., "New York", "London")
- Generic single-word terms (e.g., "Guest", "Customer", "Admin")
- Numbers or codes (e.g., "123", "ABC123")
- Single letters (e.g., "A", "B")

Examples:
- "My name is John Doe" -> "John Doe"
- "I'm Sarah Smith" -> "Sarah Smith"
- "Call me Mike" -> "Mike"
- "It's Jane" -> "Jane"
- "I don't want to say" -> "NONE"
- "My name is Google" -> "NONE"
- "I'm 123" -> "NONE"

Message: {user_message}

Name:"""
        
        response = llm.invoke(extraction_prompt)
        
        # Extract content from response
        if hasattr(response, 'content'):
            extracted = response.content.strip()
        else:
            extracted = str(response).strip()
        
        # Clean up the response
        extracted = extracted.replace('"', '').replace("'", '').strip()
        
        # Validate it's a reasonable name
        if extracted and extracted.upper() != "NONE" and len(extracted) > 1:
            # Enhanced validation
            if _is_valid_person_name(extracted):
                return extracted
        
        return ""
        
    except Exception as e:
        logger.error(f"Error extracting name with LLM: {e}")
        # Fallback to simple regex extraction
        return _extract_name_with_regex(user_message)


def _is_valid_person_name(name: str) -> bool:
    """
    Validate that the extracted string is likely a person's name.
    
    Args:
        name: Extracted name string
        
    Returns:
        True if valid person name, False otherwise
    """
    # Must contain letters
    if not re.search(r'[a-zA-Z]', name):
        return False
    
    # Reject single letters
    if len(name) == 1:
        return False
    
    # Reject common non-person terms (case-insensitive)
    # Only reject if the ENTIRE name is one of these terms
    invalid_exact_terms = [
        'user', 'guest', 'customer', 'client', 'patient',
        'admin', 'administrator', 'test', 'demo', 'sample',
        'unknown', 'anonymous', 'none', 'null', 'n/a',
        'company', 'organization', 'business', 'hospital',
        'doctor', 'nurse', 'staff', 'employee'
    ]
    
    name_lower = name.lower().strip()
    if name_lower in invalid_exact_terms:
        return False
    
    # Reject if it's mostly numbers
    letter_count = sum(1 for c in name if c.isalpha())
    digit_count = sum(1 for c in name if c.isdigit())
    if digit_count > letter_count:
        return False
    
    # Reject common company/place suffixes
    invalid_suffixes = ['inc', 'llc', 'ltd', 'corp', 'co', 'pvt']
    for suffix in invalid_suffixes:
        if name_lower.endswith(suffix) or name_lower.endswith(f' {suffix}'):
            return False
    
    # Must have reasonable length (2-50 characters)
    if len(name) < 2 or len(name) > 50:
        return False
    
    # Should not be all uppercase (likely an acronym or code)
    if name.isupper() and len(name) > 3:
        return False
    
    return True


def _extract_name_with_regex(user_message: str) -> str:
    """
    Fallback method to extract name using regex patterns.
    
    Args:
        user_message: User's message content
        
    Returns:
        Extracted name or empty string
    """
    patterns = [
        r"(?:my name is|i'm|i am|call me|this is)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
        r"^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)$"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, user_message, re.IGNORECASE)
        if match:
            name = match.group(1).strip()
            # Capitalize properly
            name = ' '.join(word.capitalize() for word in name.split())
            # Validate using the same validation function
            if _is_valid_person_name(name):
                return name
    
    return ""
