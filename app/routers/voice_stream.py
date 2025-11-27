"""
Voice Streaming API Router
==========================

This module provides real-time bi-directional audio streaming for Twilio voice calls
using Twilio Media Streams (WebSocket). It handles audio processing, speech-to-text,
AI agent interaction, and text-to-speech synthesis in real-time.

Author: Advanced AI Systems Team
Last Modified: 2025-01-27
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import json
import logging
import base64
import asyncio
import time
from typing import Dict, Optional

from app.core.config import settings
from app.core.sarvam_client import SarvamClient
from agentic_graph.agent_graph import run_agentic_graph_streaming
from app.audio.audio_utils import (
    mulaw_to_pcm16,
    pcm16_8k_to_pcm16_16k,
    chunk_mulaw_for_twilio,
    generate_silence_mulaw,
    has_speech_activity
)

logger = logging.getLogger(__name__)

# Create router instance
router = APIRouter()

# Initialize Sarvam client
sarvam_client = SarvamClient()

# Session storage for streaming calls
# Format: {
#   session_id: {
#       "call_sid": str,
#       "history": list,
#       "audio_buffer": bytes,
#       "is_speaking": bool,
#       "websocket": WebSocket,
#       "last_audio_time": float,  # Timestamp of last audio received
#       "silence_timer": asyncio.Task,  # Task for silence detection
#       "has_speech_detected": bool  # Whether speech has been detected in current buffer
#   }
# }
streaming_sessions: Dict[str, dict] = {}

# Audio buffer configuration
MIN_BUFFER_DURATION_MS = 1500  # Minimum 1.5 seconds before processing
MAX_BUFFER_DURATION_MS = 20000  # Maximum 20 seconds buffer (allows longer speech without cutting off)
SILENCE_DURATION_MS = 3000  # Wait 3 seconds of silence (no speech activity) before processing
SAMPLE_RATE_8K = 8000
BYTES_PER_SAMPLE_8K = 1  # mulaw is 1 byte per sample
MIN_BUFFER_SIZE_BYTES = int((MIN_BUFFER_DURATION_MS / 1000) * SAMPLE_RATE_8K * BYTES_PER_SAMPLE_8K)
MAX_BUFFER_SIZE_BYTES = int((MAX_BUFFER_DURATION_MS / 1000) * SAMPLE_RATE_8K * BYTES_PER_SAMPLE_8K)
# Silence detection: check for speech activity every 200ms during silence period
SILENCE_CHECK_INTERVAL_MS = 200  # Check for speech every 200ms


@router.websocket("/stream")
async def handle_media_stream(websocket: WebSocket):
    """
    Handle Twilio Media Stream WebSocket connection.
    
    This WebSocket receives audio frames from Twilio and sends audio back.
    It processes:
    - "start" event: Initialize session
    - "media" event: Receive audio, buffer, transcribe, process, synthesize, stream back
    - "stop" event: Cleanup session
    
    Args:
        websocket (WebSocket): WebSocket connection from Twilio
    """
    await websocket.accept()
    session_id = None
    call_sid = None
    
    try:
        while True:
            # Receive message from Twilio
            message = await websocket.receive_text()
            data = json.loads(message)
            event_type = data.get("event")
            
            if event_type == "start":
                # Initialize session
                start_data = data.get("start", {})
                call_sid = start_data.get("callSid")
                stream_sid = start_data.get("streamSid")
                
                if not call_sid:
                    logger.error("No callSid in start event")
                    await websocket.close()
                    return
                
                session_id = call_sid
                streaming_sessions[session_id] = {
                    "call_sid": call_sid,
                    "stream_sid": stream_sid or call_sid,  # Fallback to call_sid if stream_sid not provided
                    "history": [],
                    "audio_buffer": b"",
                    "is_speaking": False,
                    "websocket": websocket,
                    "last_audio_time": None,  # Timestamp of last audio chunk received
                    "silence_timer": None,  # Task for silence detection timeout
                    "has_speech_detected": False  # Track if speech has been detected in current buffer
                }
                logger.info(f"[{session_id}] Media stream started (streamSid: {stream_sid})")
                
                # CRITICAL: Send immediate silence to keep connection alive
                # Twilio will disconnect if no audio is sent within a few seconds
                try:
                    silence = generate_silence_mulaw(duration_ms=50)  # 50ms silence
                    await stream_audio_to_twilio(session_id, silence)
                    logger.debug(f"[{session_id}] Sent initial silence to keep connection alive")
                except Exception as e:
                    logger.warning(f"[{session_id}] Failed to send initial silence: {e}")
                
                # Send initial greeting through the stream to keep call active
                # This ensures the call doesn't disconnect after connecting to stream
                # Run as background task to not block the main loop
                asyncio.create_task(send_greeting(session_id))
                
            elif event_type == "media":
                # Skip if we're currently speaking (turn-taking)
                if session_id and streaming_sessions.get(session_id, {}).get("is_speaking", False):
                    continue
                
                if not session_id:
                    logger.warning("Received media event before start event")
                    continue
                
                # Extract audio payload
                media_payload = data.get("media", {}).get("payload")
                if not media_payload:
                    continue
                
                # Decode base64 mulaw audio
                try:
                    mulaw_audio = base64.b64decode(media_payload)
                except Exception as e:
                    logger.error(f"[{session_id}] Error decoding media payload: {e}")
                    continue
                
                # Add to buffer
                session = streaming_sessions[session_id]
                session["audio_buffer"] += mulaw_audio
                
                # Check for speech activity in the new audio chunk
                # Convert mulaw to PCM16 to check for speech
                try:
                    pcm16_8k_chunk = mulaw_to_pcm16(mulaw_audio)
                    if has_speech_activity(pcm16_8k_chunk, threshold=500):
                        session["has_speech_detected"] = True
                        logger.debug(f"[{session_id}] Speech activity detected in audio chunk")
                except Exception as e:
                    logger.debug(f"[{session_id}] Could not check speech activity: {e}")
                    # Assume speech if detection fails
                    session["has_speech_detected"] = True
                
                # Update last audio timestamp
                session["last_audio_time"] = time.time()
                
                # Cancel existing silence timer if any (new audio means we need to restart silence detection)
                if session.get("silence_timer") and not session["silence_timer"].done():
                    session["silence_timer"].cancel()
                    session["silence_timer"] = None  # Clear reference so new timer can be created
                
                # Check if buffer exceeds maximum size (safety mechanism to prevent unbounded growth)
                # This should rarely trigger now with 20s buffer, but acts as a fallback
                if len(session["audio_buffer"]) >= MAX_BUFFER_SIZE_BYTES:
                    logger.debug(f"[{session_id}] Buffer reached max size ({MAX_BUFFER_DURATION_MS}ms), processing to prevent overflow")
                    await process_audio_buffer(session_id)
                # Check if buffer has minimum audio and start silence detection
                # Only start timer if speech has been detected (don't process pure silence)
                elif len(session["audio_buffer"]) >= MIN_BUFFER_SIZE_BYTES and session.get("has_speech_detected", False):
                    # Start silence detection timer only if one doesn't exist or is done
                    if not session.get("silence_timer") or session["silence_timer"].done():
                        # Start silence detection timer
                        # Continuously check for 3 seconds of actual silence (no speech activity)
                        async def check_silence_and_process():
                            silence_start_time = None
                            check_interval = SILENCE_CHECK_INTERVAL_MS / 1000.0  # Convert to seconds
                            total_silence_needed = SILENCE_DURATION_MS / 1000.0  # 3 seconds
                            
                            while session_id in streaming_sessions:
                                current_session = streaming_sessions[session_id]
                                
                                # Check if we should stop (session deleted, speaking, or no buffer)
                                if (current_session.get("is_speaking", False) or
                                    len(current_session.get("audio_buffer", b"")) < MIN_BUFFER_SIZE_BYTES or
                                    not current_session.get("has_speech_detected", False)):
                                    return
                                
                                # Get recent audio from buffer to check for speech activity
                                # Check last 500ms of audio (4000 bytes at 8kHz mulaw)
                                recent_audio_bytes = 4000  # ~500ms at 8kHz
                                buffer = current_session.get("audio_buffer", b"")
                                recent_buffer = buffer[-recent_audio_bytes:] if len(buffer) > recent_audio_bytes else buffer
                                
                                # Check if recent audio has speech activity
                                has_recent_speech = False
                                if len(recent_buffer) > 0:
                                    try:
                                        pcm16_8k_recent = mulaw_to_pcm16(recent_buffer)
                                        has_recent_speech = has_speech_activity(pcm16_8k_recent, threshold=500)
                                    except Exception as e:
                                        logger.debug(f"[{session_id}] Could not check recent speech activity: {e}")
                                        # If check fails, assume there's speech (safer to wait)
                                        has_recent_speech = True
                                
                                if has_recent_speech:
                                    # Speech detected - reset silence timer
                                    silence_start_time = None
                                    logger.debug(f"[{session_id}] Speech activity detected, resetting silence timer")
                                else:
                                    # No speech detected
                                    if silence_start_time is None:
                                        # Start tracking silence period
                                        silence_start_time = time.time()
                                        logger.debug(f"[{session_id}] Silence detected, starting {total_silence_needed}s timer")
                                    else:
                                        # Check if we've had enough silence
                                        silence_duration = time.time() - silence_start_time
                                        if silence_duration >= total_silence_needed:
                                            # 3 seconds of silence confirmed - process buffer
                                            if (len(current_session.get("audio_buffer", b"")) >= MIN_BUFFER_SIZE_BYTES and
                                                current_session.get("has_speech_detected", False) and
                                                not current_session.get("is_speaking", False)):
                                                logger.debug(f"[{session_id}] {total_silence_needed}s of silence confirmed, processing buffer ({len(current_session['audio_buffer'])} bytes)")
                                                await process_audio_buffer(session_id)
                                                return
                                
                                # Wait before next check
                                await asyncio.sleep(check_interval)
                        
                        session["silence_timer"] = asyncio.create_task(check_silence_and_process())
                    
            elif event_type == "stop":
                # Cleanup session
                if session_id:
                    logger.info(f"[{session_id}] Media stream stopped")
                    if session_id in streaming_sessions:
                        session = streaming_sessions[session_id]
                        # Cancel silence timer if active
                        if session.get("silence_timer") and not session["silence_timer"].done():
                            session["silence_timer"].cancel()
                        del streaming_sessions[session_id]
                await websocket.close()
                return
                
    except WebSocketDisconnect:
        logger.info(f"[{session_id}] WebSocket disconnected")
        if session_id and session_id in streaming_sessions:
            session = streaming_sessions[session_id]
            # Cancel silence timer if active
            if session.get("silence_timer") and not session["silence_timer"].done():
                session["silence_timer"].cancel()
            del streaming_sessions[session_id]
    except Exception as e:
        logger.error(f"[{session_id}] Error in media stream: {e}")
        if session_id and session_id in streaming_sessions:
            session = streaming_sessions[session_id]
            # Cancel silence timer if active
            if session.get("silence_timer") and not session["silence_timer"].done():
                session["silence_timer"].cancel()
            del streaming_sessions[session_id]
        try:
            await websocket.close()
        except:
            pass


async def send_greeting(session_id: str):
    """
    Send initial greeting when Media Stream starts to keep call active.
    
    Args:
        session_id (str): Session identifier
    """
    if session_id not in streaming_sessions:
        logger.warning(f"[{session_id}] Session not found when sending greeting")
        return
    
    try:
        # Hindi greeting message
        greeting_text = "नमस्ते! मैं आपकी सहायता कैसे कर सकता हूं?"
        
        logger.info(f"[{session_id}] Sending initial greeting")
        
        # Synthesize greeting using Sarvam TTS
        mulaw_audio = await sarvam_client.streaming_tts(greeting_text)
        
        if mulaw_audio and len(mulaw_audio) > 0:
            # Stream greeting audio to Twilio
            await stream_audio_to_twilio(session_id, mulaw_audio)
            logger.info(f"[{session_id}] Greeting sent successfully")
        else:
            logger.error(f"[{session_id}] Failed to generate greeting audio, sending fallback silence")
            # Fallback: Send silence to keep connection alive
            # This prevents call from disconnecting if TTS fails
            fallback_silence = generate_silence_mulaw(duration_ms=500)  # 500ms silence
            await stream_audio_to_twilio(session_id, fallback_silence)
            logger.info(f"[{session_id}] Sent fallback silence to maintain connection")
            
    except Exception as e:
        logger.error(f"[{session_id}] Error sending greeting: {e}", exc_info=True)
        # Last resort: try to send silence to prevent disconnection
        try:
            if session_id in streaming_sessions:
                emergency_silence = generate_silence_mulaw(duration_ms=200)
                await stream_audio_to_twilio(session_id, emergency_silence)
                logger.info(f"[{session_id}] Sent emergency silence after greeting error")
        except Exception as fallback_error:
            logger.error(f"[{session_id}] Failed to send emergency silence: {fallback_error}")


async def process_audio_buffer(session_id: str):
    """
    Process accumulated audio buffer: convert, transcribe, get AI response, synthesize, stream back.
    
    Args:
        session_id (str): Session identifier
    """
    if session_id not in streaming_sessions:
        return
    
    session = streaming_sessions[session_id]
    
    # Cancel any pending silence timer
    if session.get("silence_timer") and not session["silence_timer"].done():
        session["silence_timer"].cancel()
        session["silence_timer"] = None
    
    # Set speaking flag to prevent processing new audio
    session["is_speaking"] = True
    
    try:
        # Get audio buffer and clear it
        mulaw_buffer = session["audio_buffer"]
        session["audio_buffer"] = b""
        # Reset speech detection flag
        session["has_speech_detected"] = False
        
        if len(mulaw_buffer) == 0:
            session["is_speaking"] = False
            return
        
        # Convert mulaw to PCM16
        try:
            pcm16_8k = mulaw_to_pcm16(mulaw_buffer)
        except Exception as e:
            logger.error(f"[{session_id}] Error converting mulaw to PCM16: {e}")
            session["is_speaking"] = False
            return
        
        # Check if buffer contains actual speech before processing
        # This prevents processing silence or thinking pauses
        if not has_speech_activity(pcm16_8k, threshold=500):
            logger.debug(f"[{session_id}] Buffer contains no speech activity, skipping processing")
            session["is_speaking"] = False
            return
        
        # Resample 8k to 16k
        try:
            pcm16_16k = pcm16_8k_to_pcm16_16k(pcm16_8k)
        except Exception as e:
            logger.error(f"[{session_id}] Error resampling audio: {e}")
            session["is_speaking"] = False
            return
        
        # Transcribe using Sarvam STT
        transcript = await sarvam_client.streaming_stt(pcm16_16k)
        
        if not transcript or transcript.strip() == "":
            logger.debug(f"[{session_id}] Empty transcript, skipping")
            session["is_speaking"] = False
            return
        
        logger.info(f"[{session_id}] User said: {transcript}")
        
        # Process through AI agent
        try:
            ai_response = await run_agentic_graph_streaming(transcript, session_id)
            logger.info(f"[{session_id}] AI response: {ai_response}")
        except Exception as e:
            logger.error(f"[{session_id}] Error in agent processing: {e}")
            ai_response = "मुझे क्षमा करें, मैं अभी आपकी बात नहीं समझ पाया।"
        
        # Synthesize speech using Sarvam TTS
        mulaw_audio = await sarvam_client.streaming_tts(ai_response)
        
        if not mulaw_audio:
            logger.error(f"[{session_id}] Failed to generate TTS audio")
            session["is_speaking"] = False
            return
        
        # Stream audio back to Twilio in chunks
        await stream_audio_to_twilio(session_id, mulaw_audio)
        
    except Exception as e:
        logger.error(f"[{session_id}] Error processing audio buffer: {e}")
    finally:
        # Clear speaking flag
        session["is_speaking"] = False


async def stream_audio_to_twilio(session_id: str, mulaw_audio: bytes):
    """
    Stream mulaw audio to Twilio in 20ms chunks.
    
    Args:
        session_id (str): Session identifier
        mulaw_audio (bytes): Complete mulaw audio bytes to stream
    """
    if session_id not in streaming_sessions:
        logger.warning(f"[{session_id}] Session not found when streaming audio")
        return
    
    session = streaming_sessions[session_id]
    websocket = session.get("websocket")
    
    if not websocket:
        logger.error(f"[{session_id}] No WebSocket connection")
        return
    
    # Check WebSocket connection state before sending
    # Starlette WebSocket has a 'client_state' attribute
    try:
        # Check if WebSocket is still connected
        # Starlette WebSocket raises WebSocketDisconnect if not connected
        # We'll catch it in the try-except below
        client_state = getattr(websocket, 'client_state', None)
        application_state = getattr(websocket, 'application_state', None)
        
        # If states indicate disconnection, don't proceed
        if client_state == 'DISCONNECTED' or application_state == 'DISCONNECTED':
            logger.warning(f"[{session_id}] WebSocket already disconnected, skipping audio stream")
            return
    except Exception as state_check_error:
        logger.debug(f"[{session_id}] Could not check WebSocket state: {state_check_error}")
        # Continue anyway - let the send attempt reveal the actual state
    
    try:
        # Chunk audio into 20ms frames (160 bytes at 8kHz)
        chunks = chunk_mulaw_for_twilio(mulaw_audio)
        
        for chunk in chunks:
            # Check connection before each chunk send
            try:
                # Encode chunk to base64
                chunk_base64 = base64.b64encode(chunk).decode('utf-8')
                
                # Create media event message
                # Note: streamSid is optional when sending from server, but included for compatibility
                media_message = {
                    "event": "media",
                    "streamSid": session.get("stream_sid", session.get("call_sid", "")),
                    "media": {
                        "payload": chunk_base64
                    }
                }
                
                # Send to Twilio with connection check
                await websocket.send_text(json.dumps(media_message))
                
                # Small delay to maintain real-time streaming (20ms per chunk)
                await asyncio.sleep(0.02)
                
            except WebSocketDisconnect:
                # Connection was closed during streaming
                logger.warning(f"[{session_id}] WebSocket disconnected during audio streaming")
                # Remove session since connection is lost
                if session_id in streaming_sessions:
                    del streaming_sessions[session_id]
                return
            except Exception as chunk_error:
                # Check if it's a connection-related error
                error_str = str(chunk_error).lower()
                if 'disconnect' in error_str or 'closed' in error_str or 'not connected' in error_str:
                    logger.warning(f"[{session_id}] WebSocket connection lost: {chunk_error}")
                    if session_id in streaming_sessions:
                        del streaming_sessions[session_id]
                    return
                else:
                    # Other error - log and continue with next chunk
                    logger.warning(f"[{session_id}] Error sending audio chunk: {chunk_error}")
                    continue
            
        logger.debug(f"[{session_id}] Streamed {len(chunks)} audio chunks")
        
    except WebSocketDisconnect:
        logger.info(f"[{session_id}] WebSocket disconnected during audio streaming")
        if session_id in streaming_sessions:
            del streaming_sessions[session_id]
    except Exception as e:
        logger.error(f"[{session_id}] Error streaming audio to Twilio: {e}", exc_info=True)
        # Check if it's a connection error
        error_str = str(e).lower()
        if 'disconnect' in error_str or 'closed' in error_str or 'not connected' in error_str:
            if session_id in streaming_sessions:
                del streaming_sessions[session_id]


@router.get("/active-streams")
async def get_active_streams():
    """
    Get list of active streaming sessions.
    
    Returns:
        dict: List of active streaming session IDs
    """
    return {
        "active_streams": len(streaming_sessions),
        "session_ids": list(streaming_sessions.keys())
    }

