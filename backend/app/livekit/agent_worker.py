"""
LiveKit Agent Worker with Streaming Support
============================================

LiveKit Agents process entry point for the hospital management voice agent.

This module registers as a worker with the LiveKit server, listens for new
rooms (i.e. incoming phone calls via SIP trunking), and spins up an
AgentSession per call.

STREAMING ARCHITECTURE:
    ┌─────────────────────────────────────────────────────────────┐
    │                    Real-Time Token Flow                     │
    ├─────────────────────────────────────────────────────────────┤
    │                                                              │
    │  Caller Audio → STT (Sarvam, streaming)                    │
    │                    ↓                                         │
    │  User Text → LLM Adapter → LangGraph                       │
    │                    ↓                                         │
    │  Groq LLM (streaming=True) emits tokens                    │
    │                    ↓                                         │
    │  Tokens (buffered) → TTS (Sarvam)                          │
    │                    ↓                                         │
    │  AI Speech → Caller (with minimal latency)                 │
    │                                                              │
    └─────────────────────────────────────────────────────────────┘

Key Components:
    - STT:  livekit-plugins-sarvam  (Saaras v3 streaming model, en-IN)
    - LLM:  livekit-plugins-langchain LLMAdapter wrapping LangGraph
            (Groq configured with streaming=True for incremental tokens)
    - TTS:  livekit-plugins-sarvam  (Bulbul v2 model, en-IN)

    Turn detection relies on Sarvam STT's own end-of-utterance signalling.
    No separate VAD is used.

Streaming Benefits:
    ✓ Tokens arrive from Groq continuously (not waiting for full response)
    ✓ TTS buffers as tokens arrive and begins playback early
    ✓ Caller hears response faster (reduced latency by ~60-80%)
    ✓ Natural, conversational interaction

Usage:
    # Development mode (auto-reloads):
    python -m app.livekit.agent_worker dev

    # Production mode:
    python -m app.livekit.agent_worker start

Author: Advanced AI Systems Team
Last Modified: 2026-02-27
"""

import logging

from livekit.agents import (
    Agent,
    AgentSession,
    AutoSubscribe,
    JobContext,
    JobRequest,
    WorkerOptions,
    cli,
)
from livekit.plugins import sarvam

from app.livekit.langgraph_adapter import create_langgraph_llm
from app.livekit.tts_utils import create_filtered_tts
from app.core.logger_config import get_ai_agent_logger

logger = get_ai_agent_logger()


class Assistant(Agent):
    """
    Hospital AI Assistant Agent
    
    Defines the core AI persona and instructions for the voice agent.
    This agent handles appointment scheduling, cancellations, and general
    hospital inquiries with a warm, empathetic tone.
    """
    def __init__(self) -> None:
        super().__init__(
            instructions="""You are a helpful and empathetic hospital receptionist AI assistant.
You assist patients with appointment scheduling, rescheduling, cancellations, and general inquiries.
Your responses are warm, professional, conversational, and to the point.
You speak naturally like a human receptionist would, without complex formatting or symbols."""
        )


async def request_fnc(req: JobRequest) -> None:
    """
    Called when a new job request is received.
    We accept the job and set the agent's display name.
    """
    logger.info(f"[LIVEKIT WORKER] Accepting job request for room={req.room.name}")
    await req.accept(name="Hospital Assistant")


async def entrypoint(ctx: JobContext):
    """
    Called by the LiveKit worker runtime when a new participant joins a room.

    In the SIP trunking model:
        1.  Twilio routes an inbound call via SIP trunk to LiveKit.
        2.  LiveKit SIP service creates a new room and adds the caller
            as a SIP participant.
        3.  This entrypoint fires, extracts caller metadata, builds the
            AgentSession pipeline, and starts the conversation.

    In the local/Playground model:
        1.  A browser client connects to the LiveKit room via WebRTC.
        2.  This entrypoint fires identically.

    STREAMING ENABLED:
        The LLM adapter uses Groq with streaming=True, which means:
        - Tokens arrive incrementally from Groq API
        - LLMAdapter automatically consumes the token stream
        - Tokens are buffered and sent to TTS as they arrive
        - Result: Minimal latency, natural conversation pace

    Args:
        ctx: LiveKit job context containing room and participant info.
    """
    # Wait for the first participant to connect (the caller)
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    participant = await ctx.wait_for_participant()

    # ------------------------------------------------------------------
    # Extract caller identity from SIP participant attributes.
    # For SIP calls, LiveKit populates sip.phoneNumber automatically.
    # For Playground/browser testing, use a test mobile number.
    # ------------------------------------------------------------------
    caller_number = participant.attributes.get("sip.phoneNumber", "")
    
    # TESTING FALLBACK: Use registered test number for non-SIP calls
    # TODO: Remove this fallback before production deployment
    if not caller_number:
        caller_number = "8799472801"  # Test user mobile number
        logger.warning(
            f"[TESTING MODE] No SIP caller number found, using test mobile: {caller_number}"
        )
    room_name = ctx.room.name

    logger.info(
        f"[LIVEKIT WORKER] ========== NEW SESSION ==========\n"
        f"room={room_name} | participant={participant.identity} | "
        f"caller={caller_number} | streaming=ENABLED"
    )

    # ------------------------------------------------------------------
    # Build the voice pipeline with streaming enabled
    # ------------------------------------------------------------------
    logger.info(
        f"[LIVEKIT WORKER] Streaming pipeline:\n"
        f"  STT:  Sarvam (saaras:v3, en-IN)\n"
        f"  LLM:  LangGraph + Groq (streaming=True)\n"
        f"  TTS:  Sarvam (bulbul:v2, anushka voice)"
    )

    session = AgentSession(
        # Sarvam Speech-to-Text
        stt=sarvam.STT(
            language="en-IN",         # Indian English
            model="saaras:v3",        # Sarvam's latest streaming model
            flush_signal=True         # REQUIRED: Enables speech start/end events
        ),
        # LangGraph LLM Adapter with Groq Streaming
        llm=create_langgraph_llm(
            caller_mobile_number=caller_number,
            session_id=room_name,
        ),
        # Sarvam Text-to-Speech with message filtering
        # Uses create_filtered_tts to ensure only AI responses are spoken
        tts=create_filtered_tts(
            target_language_code="en-IN",  # Indian English locale
            model="bulbul:v2",             # Sarvam's conversational model
            speaker="anushka",                # Indian English female voice
        ),
        # --- Sarvam-Specific Optimizations ---
        # 1. Let Sarvam's STT handle turn detection instead of a VAD
        turn_detection="stt",
        # 2. Minimize response delay (Sarvam STT has ~70ms processing latency)
        min_endpointing_delay=0.07
    )

    # Start the session — this begins listening for audio from the
    # participant and routes it through STT → LLM → TTS automatically.
    # Streaming is transparent: LLMAdapter receives tokens from Groq
    # and TTS processes them as they arrive.
    await session.start(
        room=ctx.room,
        agent=Assistant()
    )

    logger.info(
        f"[LIVEKIT WORKER] ✓ AgentSession started (streaming active)\n"
        f"room={room_name} | caller={caller_number}"
    )

    # Send the initial greeting (same as the current voice_stream.py
    # send_greeting function, but now handled natively by AgentSession).
    await session.say("Hello! How can I help you today?")

    logger.info(
        f"[LIVEKIT WORKER] Greeting sent"
    )


if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            request_fnc=request_fnc,
        )
    )
