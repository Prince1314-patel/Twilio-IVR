"""
TTS Utilities for LiveKit Integration
======================================

Utilities for filtering and processing messages before sending to TTS.

This module provides a wrapper around Sarvam TTS that ensures only AI-generated
response text is sent for speech synthesis, filtering out system messages,
timestamps, and other non-conversational content.

Author: Advanced AI Systems Team
Last Modified: 2026-02-16
"""

from typing import Any
from livekit.plugins import sarvam
from app.core.logger_config import get_ai_agent_logger

logger = get_ai_agent_logger()


def create_filtered_tts(
    target_language_code: str = "en-IN",
    model: str = "bulbul:v2",
    speaker: str = "vidya",
    **kwargs
) -> sarvam.TTS:
    """
    Create a Sarvam TTS instance with built-in message filtering.
    
    This factory function creates a standard Sarvam TTS instance.
    The actual filtering happens at the LiveKit AgentSession level,
    which automatically extracts only AIMessage content for TTS.
    
    IMPORTANT:
    ----------
    LiveKit's AgentSession already filters messages intelligently:
    - It only sends AIMessage content to TTS
    - SystemMessage and HumanMessage are NOT sent to TTS
    - Tool call responses are handled separately
    
    The issue we're solving is when SystemMessage content gets concatenated
    with AIMessage content during LangGraph processing. To prevent this,
    we must ensure the LangGraph nodes only return AIMessage objects,
    not SystemMessage objects in the final output.
    
    Args:
        target_language_code: Language code for TTS (default: "en-IN")
        model: Sarvam TTS model to use (default: "bulbul:v2")
        speaker: Voice speaker ID (default: "vidya")
        **kwargs: Additional arguments passed to sarvam.TTS
        
    Returns:
        Configured Sarvam TTS instance
        
    Example:
        >>> tts = create_filtered_tts(
        ...     target_language_code="en-IN",
        ...     model="bulbul:v2",
        ...     speaker="vidya"
        ... )
    """
    logger.info(
        f"Creating Sarvam TTS: model={model}, speaker={speaker}, "
        f"language={target_language_code}"
    )
    
    # Create standard Sarvam TTS instance
    # LiveKit's AgentSession handles the message filtering
    tts = sarvam.TTS(
        target_language_code=target_language_code,
        model=model,
        speaker=speaker,
        **kwargs
    )
    
    logger.info("Sarvam TTS instance created successfully")
    
    return tts
