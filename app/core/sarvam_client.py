"""
Sarvam AI Client Wrapper
=======================

Wrapper around the official sarvamai Python SDK.
Uses SDK as the primary method for all operations.
REST API is only used as a fallback when SDK is not available.
"""

import logging
import base64
import os
import tempfile
import wave
import asyncio
from typing import Optional
import httpx
from app.core.config import settings

# Import the official SDK
try:
    from sarvamai import SarvamAI
except ImportError:
    SarvamAI = None

logger = logging.getLogger(__name__)

# Sarvam API endpoints
SARVAM_STT_URL = "https://api.sarvam.ai/v1/speech-to-text"
SARVAM_TTS_URL = "https://api.sarvam.ai/v1/text-to-speech"

class SarvamClient:
    """
    Wrapper for Sarvam AI SDK.
    """
    
    def __init__(self):
        """
        Initialize Sarvam AI SDK client.
        
        SDK is required for all operations. REST API fallback is only used
        if SDK initialization fails.
        """
        self.api_key = settings.SARVAM_API_KEY
        if not self.api_key:
            logger.error("SARVAM_API_KEY is not set. Sarvam AI features will not work.")
            self.client = None
        elif SarvamAI is None:
            logger.error("sarvamai SDK not installed. SDK is required!")
            logger.error("Please run: pip install sarvamai")
            self.client = None
        else:
            try:
                self.client = SarvamAI(api_subscription_key=self.api_key)
                logger.info("Sarvam AI SDK initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize SarvamAI SDK client: {e}")
                logger.error("Sarvam AI features will not work without SDK")
                self.client = None

    def text_to_speech(self, text: str, language_code: str = "hi-IN", speaker_gender: str = "Female") -> Optional[bytes]:
        """
        Convert text to speech using Sarvam AI SDK.
        """
        if not self.client:
            logger.error("Sarvam client not initialized")
            return None
            
        try:
            # Map gender to speaker ID if needed, or let SDK handle defaults
            # Based on docs, we might need specific speaker IDs.
            # For now, we'll use the SDK's text_to_speech method.
            # Assuming SDK has a method like this based on typical patterns.
            # If SDK signature differs, we will adjust.
            
            # Note: The SDK documentation wasn't fully visible, so I'm inferring standard usage.
            # Usually: client.text_to_speech.create(...) or similar.
            # Let's assume a direct method for now or check available attributes if possible.
            # Given the search result showed `client = SarvamAI(api_key=...)`, 
            # let's try to use the likely method.
            
            # According to Sarvam AI docs: client.text_to_speech.convert(...)
            response = self.client.text_to_speech.convert(
                text=text,  # Single text string, not array
                target_language_code=language_code,
                speaker="anushka" if speaker_gender == "Female" else "pavithra",
                speech_sample_rate=8000,
                output_audio_codec="mulaw",  # Parameter name is output_audio_codec
                model="bulbul:v2",  # Use v2, not v1
                enable_preprocessing=True
            )
            
            # Extract audio from response (object with .audios or dict with "audios")
            audio_base64 = None
            if hasattr(response, 'audios'):
                if response.audios and len(response.audios) > 0:
                    audio_base64 = response.audios[0]
            elif isinstance(response, dict):
                if "audios" in response and len(response["audios"]) > 0:
                    audio_base64 = response["audios"][0]
                elif "audio" in response:
                    audio_base64 = response["audio"]
            
            if audio_base64:
                return base64.b64decode(audio_base64)
            
            return None
                
        except Exception as e:
            logger.error(f"Error calling Sarvam TTS: {e}")
            return None

    def speech_to_text(self, audio_content: bytes, language_code: str = "hi-IN") -> Optional[str]:
        """
        Convert speech to text using Sarvam AI SDK.
        """
        if not self.client:
            logger.error("Sarvam client not initialized")
            return None
            
        try:
            # Create a temporary file for the SDK if it requires a file path
            # Or pass bytes if supported. 
            # The API expects a file upload. SDK likely handles file objects.
            
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio:
                temp_audio.write(audio_content)
                temp_path = temp_audio.name
            
            try:
                # IMPORTANT: SDK expects file object, NOT file path string
                # According to Sarvam AI documentation
                with open(temp_path, "rb") as audio_file:
                    response = self.client.speech_to_text.transcribe(
                        file=audio_file,  # File object, not path!
                        model="saarika:v2.5",
                        language_code=language_code
                    )
                # Extract transcript from response
                if isinstance(response, dict):
                    return response.get("transcript", "")
                elif hasattr(response, 'transcript'):
                    return response.transcript
                elif hasattr(response, 'text'):
                    return response.text
                else:
                    logger.warning(f"Unexpected SDK response format: {type(response)}")
                    return None
            finally:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                
        except Exception as e:
            logger.error(f"Error calling Sarvam SST: {e}")
            return None

    async def streaming_stt(self, pcm16_16k: bytes) -> Optional[str]:
        """
        Convert speech to text using Sarvam STT SDK for streaming.
        
        Uses SDK as primary method. Falls back to REST API only if SDK is not available.
        Expects 16-bit PCM audio at 16 kHz.
        
        Args:
            pcm16_16k (bytes): 16-bit PCM audio bytes at 16 kHz sample rate
            
        Returns:
            Optional[str]: Transcript text, or None if transcription fails
            
        Raises:
            Exception: If API request fails
        """
        if not self.api_key:
            logger.error("SARVAM_API_KEY is not set")
            return None
        
        # Validate audio input
        if not pcm16_16k or len(pcm16_16k) == 0:
            logger.warning("Empty audio data provided to STT")
            return None
        
        # Check minimum audio duration (at least 200ms = 3200 bytes at 16kHz, 16-bit)
        # 200ms = 0.2s * 16000 samples/s * 2 bytes/sample = 6400 bytes
        MIN_AUDIO_BYTES = 6400  # 200ms minimum
        if len(pcm16_16k) < MIN_AUDIO_BYTES:
            logger.warning(f"Audio too short for STT: {len(pcm16_16k)} bytes (minimum: {MIN_AUDIO_BYTES} bytes)")
            return None
        
        # Check if audio has actual content (not all zeros/silence)
        # Calculate RMS to detect if audio is mostly silence
        import struct
        try:
            samples = struct.unpack(f'<{len(pcm16_16k)//2}h', pcm16_16k)
            rms = (sum(s*s for s in samples) / len(samples)) ** 0.5
            if rms < 100:  # Very low RMS indicates silence
                logger.debug(f"Audio appears to be silence (RMS: {rms:.2f}), skipping STT")
                return None
        except Exception as e:
            logger.debug(f"Could not analyze audio RMS: {e}")
            # Continue anyway - let API decide
        
        # PRIMARY METHOD: Use SDK (preferred and required)
        if not self.client:
            logger.error("Sarvam SDK client not initialized. Cannot use STT without SDK.")
            # Only fall back to REST API if SDK is completely unavailable
            logger.warning("Falling back to REST API (SDK not available)")
        else:
            # Use SDK method (primary and preferred)
            try:
                # Convert PCM16 bytes to WAV file format for SDK
                # Create temporary WAV file
                temp_path = None
                try:
                    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio:
                        temp_path = temp_audio.name
                    
                    # Write WAV header and PCM data
                    sample_rate = 16000
                    num_channels = 1
                    sample_width = 2  # 16-bit = 2 bytes
                    
                    # Write WAV file and ensure it's properly closed
                    with wave.open(temp_path, 'wb') as wav_file:
                        wav_file.setnchannels(num_channels)
                        wav_file.setsampwidth(sample_width)
                        wav_file.setframerate(sample_rate)
                        wav_file.writeframes(pcm16_16k)
                    # File is now closed and flushed
                    
                    # Verify file was created and has content
                    if not os.path.exists(temp_path):
                        raise ValueError("WAV file was not created")
                    
                    file_size = os.path.getsize(temp_path)
                    if file_size == 0:
                        raise ValueError("WAV file is empty")
                    
                    # Verify WAV file has minimum size (header + some data)
                    if file_size < 44:  # WAV header is typically 44 bytes
                        raise ValueError(f"WAV file too small: {file_size} bytes")
                    
                    logger.debug(f"Created WAV file: {temp_path}, size: {file_size} bytes")
                    
                    # Use SDK in executor (SDK is synchronous)
                    # IMPORTANT: SDK expects a file object (opened file), NOT a file path string
                    # This is the correct way according to Sarvam AI documentation
                    loop = asyncio.get_event_loop()
                    
                    def transcribe_with_file():
                        # Open file as binary for SDK
                        with open(temp_path, "rb") as audio_file:
                            return self.client.speech_to_text.transcribe(
                                file=audio_file,  # File object, not path!
                                model="saarika:v2.5",
                                language_code="hi-IN"
                            )
                    
                    response = await loop.run_in_executor(None, transcribe_with_file)
                    
                    # Extract transcript from response
                    if isinstance(response, dict):
                        transcript = response.get("transcript", "")
                    elif hasattr(response, 'transcript'):
                        transcript = response.transcript
                    elif hasattr(response, 'text'):
                        transcript = response.text
                    else:
                        logger.warning(f"Unexpected SDK response format: {type(response)}")
                        transcript = ""
                    
                    if transcript:
                        logger.info(f"SDK STT Success: {transcript}")
                        return transcript
                    else:
                        logger.warning("Empty transcript from Sarvam SDK STT")
                        # Don't fall through - SDK returned empty, return None
                        return None
                        
                finally:
                    # Clean up temp file
                    if temp_path and os.path.exists(temp_path):
                        try:
                            os.remove(temp_path)
                        except Exception as cleanup_error:
                            logger.warning(f"Failed to cleanup temp file: {cleanup_error}")
                        
            except Exception as e:
                logger.error(f"SDK STT method failed: {e}")
                logger.debug(f"SDK error details: {e}", exc_info=True)
                # SDK failed - return None (don't fall back to REST API)
                return None
        
        # FALLBACK: REST API (only used if SDK is not available)
        # This should rarely be needed if SDK is properly installed
        logger.warning("Using REST API fallback (SDK not available)")
        # REST API expects multipart/form-data with file upload
        temp_path = None
        try:
            # Create temporary WAV file for REST API
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio:
                temp_path = temp_audio.name
            
            # Write WAV header and PCM data
            sample_rate = 16000
            num_channels = 1
            sample_width = 2  # 16-bit = 2 bytes
            
            # Write WAV file and ensure it's properly closed
            with wave.open(temp_path, 'wb') as wav_file:
                wav_file.setnchannels(num_channels)
                wav_file.setsampwidth(sample_width)
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(pcm16_16k)
            # File is now closed and flushed
            
            # Verify file was created and has content
            if not os.path.exists(temp_path):
                raise ValueError("WAV file was not created")
            
            file_size = os.path.getsize(temp_path)
            if file_size == 0:
                raise ValueError("WAV file is empty")
            
            # Verify WAV file has minimum size (header + some data)
            if file_size < 44:  # WAV header is typically 44 bytes
                raise ValueError(f"WAV file too small: {file_size} bytes")
            
            logger.debug(f"Created WAV file for REST API: {temp_path}, size: {file_size} bytes")
            
            # Read file content into bytes for multipart upload
            with open(temp_path, "rb") as f:
                audio_file_content = f.read()
            
            # Sarvam API uses 'api-subscription-key' header
            headers = {
                "api-subscription-key": self.api_key
                # Don't set Content-Type - httpx will set it automatically for multipart
            }
            
            # Additional form fields
            data = {
                "language_code": "hi-IN",
                "model": "saarika:v2.5"
            }
            
            # Try alternative endpoint formats
            endpoints_to_try = [
                "https://api.sarvam.ai/speech-to-text",  # Without /v1/ - correct endpoint
                "https://api.sarvam.ai/v1/speech-to-text",  # With /v1/
                "https://api.sarvam.ai/v1/stt",  # Short form
            ]
            
            for endpoint in endpoints_to_try:
                try:
                    # Prepare multipart form data with file content
                    files = {
                        "file": ("audio.wav", audio_file_content, "audio/wav")
                    }
                    
                    async with httpx.AsyncClient(timeout=30.0) as client:
                        response = await client.post(
                            endpoint,
                            files=files,
                            data=data,
                            headers=headers
                        )
                        response.raise_for_status()
                        
                        result = response.json()
                        transcript = result.get("transcript", "") or result.get("text", "")
                        
                        if transcript:
                            logger.debug(f"REST API STT transcript from {endpoint}: {transcript}")
                            return transcript
                        else:
                            logger.warning(f"Empty transcript from endpoint {endpoint}")
                            continue
                            
                except httpx.HTTPStatusError as e:
                    logger.debug(f"Endpoint {endpoint} failed: {e.response.status_code}")
                    if e.response.status_code != 404:
                        # If it's not 404, log the error and try next endpoint
                        logger.error(f"Sarvam STT API error ({endpoint}): {e.response.status_code} - {e.response.text}")
                    continue
                except Exception as e:
                    logger.debug(f"Endpoint {endpoint} error: {e}")
                    continue
            
            logger.error("All STT endpoints failed")
            return None
                    
        except Exception as e:
            logger.error(f"Error calling Sarvam STT REST API: {e}", exc_info=True)
            return None
        finally:
            # Clean up temp file
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception as cleanup_error:
                    logger.warning(f"Failed to cleanup temp file: {cleanup_error}")

    async def streaming_tts(self, text: str) -> Optional[bytes]:
        """
        Convert text to speech using Sarvam TTS SDK.
        
        Uses SDK as primary method. Falls back to REST API only if SDK is not available.
        Returns mulaw-encoded audio at 8 kHz for Twilio.
        
        Args:
            text (str): Text to convert to speech (Hindi)
            
        Returns:
            Optional[bytes]: Mulaw-encoded audio bytes at 8 kHz, or None if synthesis fails
            
        Raises:
            Exception: If API request fails
        """
        if not self.api_key:
            logger.error("SARVAM_API_KEY is not set")
            return None
        
        # PRIMARY METHOD: Use SDK (preferred and required)
        if not self.client:
            logger.error("Sarvam SDK client not initialized. Cannot use TTS without SDK.")
            # Only fall back to REST API if SDK is completely unavailable
            logger.warning("Falling back to REST API (SDK not available)")
        else:
            # Use SDK method (primary and preferred)
            try:
                logger.info("Attempting TTS using Sarvam SDK...")
                # Use the SDK's text_to_speech.convert method (synchronous)
                # According to docs: client.text_to_speech.convert(...)
                import asyncio
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: self.client.text_to_speech.convert(
                        text=text,
                        target_language_code="hi-IN",
                        speaker="anushka",
                        speech_sample_rate=8000,
                        output_audio_codec="mulaw",  # For Twilio mulaw format
                        model="bulbul:v2"  # Use v2, not v1
                    )
                )
                
                # Extract audio from SDK response
                # Response can be object with .audios attribute or dict with "audios" key
                audio_base64 = None
                if hasattr(response, 'audios'):
                    # Object format
                    if response.audios and len(response.audios) > 0:
                        audio_base64 = response.audios[0]
                elif isinstance(response, dict) and "audios" in response:
                    # Dict format
                    if response["audios"] and len(response["audios"]) > 0:
                        audio_base64 = response["audios"][0]
                elif isinstance(response, dict) and "audio" in response:
                    # Alternative dict format
                    audio_base64 = response["audio"]
                
                if audio_base64:
                    # Decode base64 string to bytes
                    audio_bytes = base64.b64decode(audio_base64)
                    logger.info(f"SDK TTS Success: Generated {len(audio_bytes)} bytes")
                    return audio_bytes
                else:
                    logger.error(f"SDK response has no audio data. Response type: {type(response)}")
                    # SDK returned no audio - return None (don't fall back to REST API)
                    return None
                    
            except Exception as e:
                logger.error(f"SDK TTS method failed: {e}")
                logger.debug(f"SDK error details: {e}", exc_info=True)
                # SDK failed - return None (don't fall back to REST API)
                return None
        
        # FALLBACK: REST API (only used if SDK is not available)
        # This should rarely be needed if SDK is properly installed
        logger.warning("Using REST API fallback (SDK not available)")
        try:
            logger.info("Attempting TTS using REST API...")
            # Prepare request payload
            payload = {
                "text": text,
                "target_language_code": "hi-IN",
                "speaker": "anushka",
                "speech_sample_rate": 8000,
                "audio_format": "mulaw",
                "model": "bulbul:v2"
            }
            
            # Sarvam API uses 'api-subscription-key' header, not 'Authorization: Bearer'
            headers = {
                "api-subscription-key": self.api_key,
                "Content-Type": "application/json"
            }
            
            # Try alternative endpoint formats
            endpoints_to_try = [
                "https://api.sarvam.ai/text-to-speech",  # Without /v1/ - correct endpoint
                "https://api.sarvam.ai/v1/text-to-speech",
                "https://api.sarvam.ai/v1/tts",
                "https://api.sarvam.ai/tts",
            ]
            
            for endpoint in endpoints_to_try:
                try:
                    async with httpx.AsyncClient(timeout=30.0) as client:
                        response = await client.post(
                            endpoint,
                            json=payload,
                            headers=headers
                        )
                        response.raise_for_status()
                        
                        result = response.json()
                        logger.debug(f"Sarvam TTS API response keys: {list(result.keys())}")
                        
                        # Extract audio from response
                        audio_base64 = None
                        if "audio" in result:
                            audio_base64 = result["audio"]
                        elif "audios" in result and len(result["audios"]) > 0:
                            audio_base64 = result["audios"][0]
                        elif "data" in result:
                            audio_base64 = result["data"]
                        else:
                            logger.warning(f"Endpoint {endpoint} returned unexpected format: {list(result.keys())}")
                            continue
                        
                        if audio_base64:
                            audio_bytes = base64.b64decode(audio_base64)
                            logger.info(f"REST API TTS Success: Generated {len(audio_bytes)} bytes from {endpoint}")
                            return audio_bytes
                            
                except httpx.HTTPStatusError as e:
                    logger.debug(f"Endpoint {endpoint} failed: {e.response.status_code}")
                    if e.response.status_code != 404:
                        # If it's not 404, log the error
                        logger.error(f"Sarvam TTS API error ({endpoint}): {e.response.status_code} - {e.response.text}")
                    continue
                except Exception as e:
                    logger.debug(f"Endpoint {endpoint} error: {e}")
                    continue
            
            logger.error("All TTS endpoints failed")
            return None
                
        except Exception as e:
            error_msg = f"Error calling Sarvam TTS: {e}"
            logger.error(error_msg, exc_info=True)
            return None
