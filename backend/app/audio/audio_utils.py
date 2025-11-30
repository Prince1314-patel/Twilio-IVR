"""
Audio Processing Utilities
==========================

This module provides audio conversion utilities for real-time voice streaming,
including mulaw to PCM conversion, resampling, and chunking for Twilio Media Streams.

Author: Advanced AI Systems Team
Last Modified: 2025-01-27
"""

import audioop
import logging
from typing import List

logger = logging.getLogger(__name__)

# Twilio Media Stream constants
TWILIO_SAMPLE_RATE = 8000  # Twilio uses 8 kHz
TARGET_STT_SAMPLE_RATE = 16000  # Sarvam STT expects 16 kHz
CHUNK_SIZE_BYTES = 160  # 20ms chunks at 8kHz mulaw (8000 * 0.02 * 1 byte)


def mulaw_to_pcm16(mulaw_bytes: bytes) -> bytes:
    """
    Convert mulaw (μ-law) encoded audio to 16-bit PCM.
    
    Twilio Media Streams send audio as mulaw-encoded bytes. This function
    decodes them to 16-bit PCM format required for speech recognition.
    
    Args:
        mulaw_bytes (bytes): Mulaw-encoded audio bytes from Twilio
        
    Returns:
        bytes: 16-bit PCM audio bytes
        
    Raises:
        Exception: If conversion fails
    """
    try:
        # audioop.ulaw2lin converts mulaw to 16-bit PCM
        # Format: (mulaw_bytes, sample_width)
        # sample_width=2 means 16-bit (2 bytes per sample)
        pcm16_bytes = audioop.ulaw2lin(mulaw_bytes, 2)
        return pcm16_bytes
    except Exception as e:
        logger.error(f"Error converting mulaw to PCM16: {e}")
        raise


def pcm16_8k_to_pcm16_16k(pcm_bytes: bytes) -> bytes:
    """
    Resample 16-bit PCM audio from 8 kHz to 16 kHz.
    
    Twilio sends audio at 8 kHz, but Sarvam STT requires 16 kHz.
    This function uses linear interpolation to resample the audio.
    
    Args:
        pcm_bytes (bytes): 16-bit PCM audio at 8 kHz
        
    Returns:
        bytes: 16-bit PCM audio at 16 kHz
        
    Raises:
        Exception: If resampling fails
    """
    try:
        # audioop.ratecv resamples audio
        # Parameters:
        #   - pcm_bytes: input audio
        #   - sample_width: 2 bytes (16-bit)
        #   - nchannels: 1 (mono)
        #   - inrate: 8000 Hz (input sample rate)
        #   - outrate: 16000 Hz (output sample rate)
        #   - state: None (no state preservation needed)
        resampled_bytes, _ = audioop.ratecv(
            pcm_bytes,
            2,  # sample_width (16-bit = 2 bytes)
            1,  # nchannels (mono)
            8000,  # inrate
            16000,  # outrate
            None  # state
        )
        return resampled_bytes
    except Exception as e:
        logger.error(f"Error resampling PCM16 8k to 16k: {e}")
        raise


def chunk_mulaw_for_twilio(mulaw_bytes: bytes) -> List[bytes]:
    """
    Chunk mulaw audio bytes into 20ms frames for Twilio Media Streams.
    
    Twilio expects audio to be sent in small chunks (typically 20ms).
    At 8 kHz, 20ms = 160 bytes (8000 samples/sec * 0.02 sec * 1 byte/sample).
    
    Args:
        mulaw_bytes (bytes): Complete mulaw audio bytes
        
    Returns:
        List[bytes]: List of 160-byte chunks (last chunk may be smaller)
    """
    chunks = []
    chunk_size = CHUNK_SIZE_BYTES
    
    for i in range(0, len(mulaw_bytes), chunk_size):
        chunk = mulaw_bytes[i:i + chunk_size]
        chunks.append(chunk)
    
    return chunks


def pcm16_to_mulaw(pcm16_bytes: bytes) -> bytes:
    """
    Convert 16-bit PCM audio to mulaw (μ-law) encoding.
    
    This is used to convert TTS output back to mulaw format
    for streaming to Twilio Media Streams.
    
    Args:
        pcm16_bytes (bytes): 16-bit PCM audio bytes
        
    Returns:
        bytes: Mulaw-encoded audio bytes
        
    Raises:
        Exception: If conversion fails
    """
    try:
        # audioop.lin2ulaw converts 16-bit PCM to mulaw
        # Format: (pcm_bytes, sample_width)
        mulaw_bytes = audioop.lin2ulaw(pcm16_bytes, 2)
        return mulaw_bytes
    except Exception as e:
        logger.error(f"Error converting PCM16 to mulaw: {e}")
        raise


def generate_silence_mulaw(duration_ms: int = 100) -> bytes:
    """
    Generate silence in mulaw format for a specified duration.
    
    This is useful for keeping Twilio Media Stream connections alive
    when no audio is available to send.
    
    Args:
        duration_ms (int): Duration of silence in milliseconds (default: 100ms)
        
    Returns:
        bytes: Mulaw-encoded silence bytes
    """
    try:
        # Calculate number of samples needed
        # At 8kHz: samples = (duration_ms / 1000) * 8000
        num_samples = int((duration_ms / 1000.0) * TWILIO_SAMPLE_RATE)
        
        # Generate PCM silence (0 amplitude = silence in PCM)
        # 16-bit PCM: 2 bytes per sample, value 0 = silence
        pcm_silence = b'\x00\x00' * num_samples
        
        # Convert to mulaw
        mulaw_silence = pcm16_to_mulaw(pcm_silence)
        return mulaw_silence
    except Exception as e:
        logger.error(f"Error generating silence: {e}")
        # Fallback: return minimal silence (1 chunk)
        return b'\xff' * CHUNK_SIZE_BYTES


def has_speech_activity(pcm16_bytes: bytes, threshold: int = 500) -> bool:
    """
    Detect if audio contains actual speech activity (not just silence).
    
    Uses RMS (Root Mean Square) to measure audio energy.
    If RMS is above threshold, considers it as speech.
    
    Args:
        pcm16_bytes (bytes): 16-bit PCM audio bytes
        threshold (int): RMS threshold for speech detection (default: 500)
        
    Returns:
        bool: True if speech activity detected, False if mostly silence
    """
    try:
        import struct
        
        if len(pcm16_bytes) < 2:
            return False
        
        # Unpack 16-bit signed integers (little-endian)
        num_samples = len(pcm16_bytes) // 2
        samples = struct.unpack(f'<{num_samples}h', pcm16_bytes)
        
        # Calculate RMS (Root Mean Square) - measure of audio energy
        sum_squares = sum(s * s for s in samples)
        rms = (sum_squares / num_samples) ** 0.5 if num_samples > 0 else 0
        
        # Check if RMS exceeds threshold (indicates speech, not silence)
        has_speech = rms > threshold
        
        logger.debug(f"Speech detection: RMS={rms:.2f}, threshold={threshold}, has_speech={has_speech}")
        
        return has_speech
        
    except Exception as e:
        logger.warning(f"Error in speech activity detection: {e}")
        # If detection fails, assume there's speech (safer to process)
        return True

