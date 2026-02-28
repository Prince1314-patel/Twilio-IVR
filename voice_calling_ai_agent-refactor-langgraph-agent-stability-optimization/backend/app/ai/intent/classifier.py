"""
Intent Classification Engine
===========================

LLM-based intent classification for appointment booking conversations.
Classifies user messages into predefined intent categories with confidence scoring.

Author: Advanced AI Systems Team
Last Modified: 2026-02-03
"""

import re
import time
from typing import Tuple, Optional
from langchain_core.language_models.chat_models import BaseChatModel
from app.core.logger_config import get_ai_agent_logger

logger = get_ai_agent_logger()

class IntentCategory:
    """Predefined intent categories for appointment booking conversations."""
    BOOKING = "booking"
    CANCELLATION = "cancellation"
    RESCHEDULING = "rescheduling"
    INQUIRY = "inquiry"
    GREETING = "greeting"
    OUT_OF_SCOPE = "out_of_scope"
    
    @classmethod
    def all_intents(cls) -> set[str]:
        """Return all valid intent categories."""
        return {
            cls.BOOKING, cls.CANCELLATION, cls.RESCHEDULING,
            cls.INQUIRY, cls.GREETING, cls.OUT_OF_SCOPE
        }


# Intent classification prompt with examples and confidence scoring
INTENT_CLASSIFICATION_PROMPT = """Classify the user's message into one of these intent categories and provide a confidence score. Use the previous AI message as context if provided, but if the user ignores the AI's question to ask their own question or change the subject, classify based ONLY on the user's new message.

Intent Categories:
- booking: User wants to schedule a new appointment
- cancellation: User wants to cancel an existing appointment  
- rescheduling: User wants to change an existing appointment time/date
- inquiry: User is asking questions about services, hours, policies, etc.
- greeting: User is greeting or engaging in social pleasantries
- out_of_scope: User is discussing topics unrelated to appointments

Examples without context:
"I need to book an appointment" → booking
"Cancel my appointment please" → cancellation
"Can I change my appointment to tomorrow?" → rescheduling
"What are your office hours?" → inquiry
"Hello, good morning" → greeting
"What's the weather like?" → out_of_scope

Examples with context:
Context: "Would you like to book a new appointment?"
User: "yes" → booking

Context: "I found your appointment for tomorrow. Would you like to reschedule it?"
User: "no, actually cancel it" → cancellation

Context: "Would you like to schedule that now?"
User: "Sure" → booking

Context: "Can I help you with anything else?"
User: "no" → out_of_scope

Context (Previous AI Message): "{ai_text}"
User Message: "{user_text}"

Respond in this exact format:
Intent: [intent_category]
Confidence: [0.0-1.0]

Classification:"""


def _parse_classification_response(response_text: str) -> Tuple[str, float]:
    """
    Parse the LLM response to extract intent and confidence.
    
    Args:
        response_text: Raw LLM response text
        
    Returns:
        Tuple of (intent, confidence_score)
    """
    try:
        # Extract intent using regex
        intent_match = re.search(r'Intent:\s*(\w+)', response_text, re.IGNORECASE)
        confidence_match = re.search(r'Confidence:\s*([\d.]+)', response_text, re.IGNORECASE)
        
        if intent_match and confidence_match:
            intent = intent_match.group(1).lower()
            confidence = float(confidence_match.group(1))
            
            # Validate intent category
            if intent not in IntentCategory.all_intents():
                logger.warning(f"Invalid intent category: {intent}, defaulting to inquiry")
                intent = IntentCategory.INQUIRY
            
            # Clamp confidence to valid range
            confidence = max(0.0, min(1.0, confidence))
            
            return intent, confidence
        else:
            logger.warning(f"Could not parse classification response: {response_text}")
            return IntentCategory.INQUIRY, 0.5
            
    except Exception as e:
        logger.error(f"Error parsing classification response: {e}")
        return IntentCategory.INQUIRY, 0.5


def _validate_confidence_score(confidence: float) -> float:
    """
    Validate and clamp confidence score to valid range.
    
    Args:
        confidence: Raw confidence score
        
    Returns:
        Validated confidence score between 0.0 and 1.0
    """
    if confidence < 0.0:
        logger.warning(f"Confidence score {confidence} below 0.0, clamping to 0.0")
        return 0.0
    elif confidence > 1.0:
        logger.warning(f"Confidence score {confidence} above 1.0, clamping to 1.0")
        return 1.0
    return confidence


async def classify_intent(user_text: str, llm_model: BaseChatModel, ai_text: str = "") -> Tuple[str, float]:
    """
    Classify user message intent using LLM with confidence scoring.
    
    Args:
        user_text: User's message to classify
        llm_model: LangChain LLM model instance
        ai_text: Optional previous AI message for context
        
    Returns:
        Tuple of (intent, confidence_score)
        - intent: One of IntentCategory values
        - confidence_score: Float between 0.0 and 1.0
        
    Fallback behavior:
        - Empty/None input: Returns ("greeting", 0.5)
        - Classification error: Returns ("inquiry", 0.5)
    """
    start_time = time.time()
    
    # Handle empty or None input
    if not user_text or not user_text.strip():
        logger.debug("Empty user text, defaulting to greeting intent")
        return IntentCategory.GREETING, 0.5
    
    try:
        # Create classification prompt
        prompt = INTENT_CLASSIFICATION_PROMPT.format(user_text=user_text.strip(), ai_text=ai_text.strip())
        
        # Get LLM response
        response = await llm_model.ainvoke(prompt)
        
        # Extract response content
        if hasattr(response, 'content'):
            response_text = response.content.strip()
        else:
            response_text = str(response).strip()
        
        # Parse intent and confidence
        intent, confidence = _parse_classification_response(response_text)
        
        # Validate confidence score
        confidence = _validate_confidence_score(confidence)
        
        # Log performance metrics
        processing_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        logger.debug(
            f"Intent classified as '{intent}' with confidence {confidence:.2f} "
            f"for text: '{user_text[:50]}...' (took {processing_time:.1f}ms)"
        )
        
        return intent, confidence
        
    except Exception as e:
        processing_time = (time.time() - start_time) * 1000
        logger.error(
            f"Error in intent classification: {e}, defaulting to inquiry "
            f"(took {processing_time:.1f}ms)"
        )
        return IntentCategory.INQUIRY, 0.5


def classify_intent_sync(user_text: str, llm_model: BaseChatModel, ai_text: str = "") -> Tuple[str, float]:
    """
    Synchronous version of intent classification for non-async contexts.
    
    Args:
        user_text: User's message to classify
        llm_model: LangChain LLM model instance
        ai_text: Optional previous AI message for context
        
    Returns:
        Tuple of (intent, confidence_score)
        - intent: One of IntentCategory values
        - confidence_score: Float between 0.0 and 1.0
        
    Fallback behavior:
        - Empty/None input: Returns ("greeting", 0.5)
        - Classification error: Returns ("inquiry", 0.5)
    """
    start_time = time.time()
    
    # Handle empty or None input
    if not user_text or not user_text.strip():
        logger.debug("Empty user text, defaulting to greeting intent")
        return IntentCategory.GREETING, 0.5
    
    try:
        # Create classification prompt
        prompt = INTENT_CLASSIFICATION_PROMPT.format(user_text=user_text.strip(), ai_text=ai_text.strip())
        
        # Get LLM response
        response = llm_model.invoke(prompt)
        
        # Extract response content
        if hasattr(response, 'content'):
            response_text = response.content.strip()
        else:
            response_text = str(response).strip()
        
        # Parse intent and confidence
        intent, confidence = _parse_classification_response(response_text)
        
        # Validate confidence score
        confidence = _validate_confidence_score(confidence)
        
        # Log performance metrics
        processing_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        logger.debug(
            f"Intent classified as '{intent}' with confidence {confidence:.2f} "
            f"for text: '{user_text[:50]}...' (took {processing_time:.1f}ms)"
        )
        
        return intent, confidence
        
    except Exception as e:
        processing_time = (time.time() - start_time) * 1000
        logger.error(
            f"Error in intent classification: {e}, defaulting to inquiry "
            f"(took {processing_time:.1f}ms)"
        )
        return IntentCategory.INQUIRY, 0.5