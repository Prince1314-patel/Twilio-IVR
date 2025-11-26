"""
Streamlit Agent Testing App
============================

A simple Streamlit app to test the agent directly without making phone calls.
This app directly uses the agentic graph to process messages locally.

Author: Advanced AI Systems Team
Last Modified: 2025-01-27
"""

import streamlit as st
import uuid
from datetime import datetime
import logging
import asyncio
import base64
import io
import wave
try:
    import audioop
    AUDIOOP_AVAILABLE = True
except ImportError:
    AUDIOOP_AVAILABLE = False
    audioop = None  # Set to None if not available
from langchain_core.messages import HumanMessage, AIMessage
from audio_recorder_streamlit import audio_recorder

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configure Streamlit page
st.set_page_config(
    page_title="Agent Testing",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Import agent function
try:
    from agentic_graph.agent_graph import run_agentic_graph
    from app.core.config import settings
    from app.core.sarvam_client import SarvamClient
except ImportError as e:
    st.error(f"❌ Import Error: {e}")
    st.stop()

# Initialize Sarvam client
try:
    sarvam_client = SarvamClient()
except Exception as e:
    logger.warning(f"Could not initialize Sarvam client: {e}")
    sarvam_client = None

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
    }
    .user-message {
        background-color: #007bff;
        color: white;
        padding: 0.75rem 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        margin-left: 15%;
    }
    .ai-message {
        background-color: #e9ecef;
        color: #333;
        padding: 0.75rem 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        margin-right: 15%;
    }
    .config-box {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #007bff;
        margin: 1rem 0;
    }
    .status-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 12px;
        font-size: 0.875rem;
        font-weight: 500;
    }
    .status-success {
        background-color: #d4edda;
        color: #155724;
    }
    .status-info {
        background-color: #d1ecf1;
        color: #0c5460;
    }
</style>
""", unsafe_allow_html=True)

def initialize_session():
    """Initialize session state variables."""
    if 'session_id' not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.session_state.message_history = []  # LangChain message format
    
    return st.session_state.session_id

def send_message_to_agent(user_message: str, session_id: str) -> str:
    """
    Send a message to the agent and get response.
    
    Args:
        user_message (str): User's message
        session_id (str): Session identifier
        
    Returns:
        str: Agent's response
    """
    try:
        # Add user message to LangChain format
        user_msg = HumanMessage(content=user_message)
        st.session_state.message_history.append(user_msg)
        
        # Convert to format expected by agent (list of dicts)
        messages_for_agent = []
        for msg in st.session_state.message_history:
            if isinstance(msg, HumanMessage):
                messages_for_agent.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                messages_for_agent.append({"role": "assistant", "content": msg.content})
        
        # Call the agent
        logger.info(f"Calling agent with {len(messages_for_agent)} messages")
        response = run_agentic_graph(messages_for_agent, session_id)
        
        # Add AI response to history
        ai_msg = AIMessage(content=response)
        st.session_state.message_history.append(ai_msg)
        
        return response
        
    except Exception as e:
        logger.error(f"Error calling agent: {e}", exc_info=True)
        return f"❌ Error: {str(e)}"

def convert_mulaw_to_wav(mulaw_bytes: bytes) -> bytes | None:
    """
    Convert mulaw audio bytes to WAV format for browser playback.
    
    Args:
        mulaw_bytes (bytes): Mulaw-encoded audio bytes
        
    Returns:
        bytes | None: WAV audio bytes, or None if conversion fails
    """
    if not AUDIOOP_AVAILABLE or audioop is None:
        logger.error("audioop not available, cannot convert audio")
        return None
    
    try:
        # Convert mulaw to linear PCM
        linear_pcm = audioop.ulaw2lin(mulaw_bytes, 2)  # 16-bit
        
        # Create WAV file in memory
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(8000)  # 8kHz
            wav_file.writeframes(linear_pcm)
        wav_buffer.seek(0)
        return wav_buffer.getvalue()
    except Exception as e:
        logger.error(f"Error converting mulaw to WAV: {e}", exc_info=True)
        return None

async def test_sarvam_stt(audio_bytes: bytes) -> tuple[str | None, str]:
    """
    Test Sarvam STT API.
    
    Args:
        audio_bytes (bytes): Audio bytes (PCM16 16kHz)
        
    Returns:
        tuple: (transcript, error_message)
    """
    if not sarvam_client:
        return None, "Sarvam client not initialized. Check SARVAM_API_KEY in environment."
    
    if not sarvam_client.api_key:
        return None, "❌ SARVAM_API_KEY is not set."
    
    if not audio_bytes:
        return None, "❌ No audio data provided."
    
    if len(audio_bytes) < 1000:  # Very small audio might not have enough data
        return None, f"❌ Audio too short ({len(audio_bytes)} bytes). Need at least 1000 bytes."
    
    try:
        logger.info(f"Calling Sarvam STT with {len(audio_bytes)} bytes of audio")
        logger.info(f"SDK available: {sarvam_client.client is not None}")
        
        # Call STT
        transcript = await sarvam_client.streaming_stt(audio_bytes)
        
        if transcript:
            logger.info(f"STT Success: {transcript}")
            return transcript, ""
        else:
            error_msg = "Failed to transcribe audio. "
            if sarvam_client.client:
                error_msg += "SDK method returned empty result. "
            error_msg += "Check audio format (PCM16 16kHz mono) and ensure audio contains speech."
            return None, error_msg
            
    except Exception as e:
        logger.error(f"Error in Sarvam STT: {e}", exc_info=True)
        error_details = str(e)
        
        # Provide more helpful error messages
        if "404" in error_details or "Not Found" in error_details:
            return None, f"API endpoint not found. Check if endpoint URL is correct. Error: {error_details}"
        elif "403" in error_details or "Forbidden" in error_details or "api" in error_details.lower():
            return None, f"Authentication failed. Check if SARVAM_API_KEY is valid. Error: {error_details}"
        elif "timeout" in error_details.lower():
            return None, f"Request timeout. The audio might be too long or network issue. Error: {error_details}"
        else:
            return None, f"STT Error: {error_details}"

def convert_recorded_audio_to_pcm16(audio_bytes: bytes) -> tuple[bytes | None, str]:
    """
    Convert recorded audio bytes to PCM16 16kHz mono format.
    
    Args:
        audio_bytes (bytes): Recorded audio bytes (typically WAV from browser)
        
    Returns:
        tuple: (pcm16_16k_bytes, error_message)
    """
    if not audio_bytes:
        return None, "No audio data provided"
    
    # Check if audio_bytes might be a string (base64) and decode if needed
    if isinstance(audio_bytes, str):
        try:
            audio_bytes = base64.b64decode(audio_bytes)
            logger.info("Decoded base64 audio data")
        except Exception as e:
            return None, f"Failed to decode base64 audio: {str(e)}"
    
    if len(audio_bytes) < 44:  # WAV header is at least 44 bytes
        return None, f"Audio too short ({len(audio_bytes)} bytes). Minimum WAV header is 44 bytes."
    
    # Check if it's a valid WAV file by checking the header
    if not audio_bytes.startswith(b'RIFF') and not audio_bytes.startswith(b'riff'):
        # Try to decode as base64 if it looks like base64
        try:
            decoded = base64.b64decode(audio_bytes)
            if decoded.startswith(b'RIFF') or decoded.startswith(b'riff'):
                audio_bytes = decoded
                logger.info("Decoded base64 WAV data")
            else:
                return None, "Audio data doesn't appear to be a valid WAV file (missing RIFF header)"
        except Exception:
            return None, "Audio data doesn't appear to be a valid WAV file (missing RIFF header)"
    
    try:
        # Try to read as WAV
        wav_buffer = io.BytesIO(audio_bytes)
        try:
            wav_file = wave.open(wav_buffer, 'rb')
        except wave.Error as e:
            # If it's not a WAV file, try to detect format
            logger.error(f"Not a valid WAV file: {e}")
            return None, f"Audio format error: {str(e)}. Expected WAV format."
        
        sample_rate = wav_file.getframerate()
        channels = wav_file.getnchannels()
        sample_width = wav_file.getsampwidth()
        n_frames = wav_file.getnframes()
        frames = wav_file.readframes(n_frames)
        wav_file.close()
        
        logger.info(f"Original audio: {sample_rate}Hz, {channels} channel(s), {sample_width*8}-bit, {n_frames} frames")
        
        if n_frames == 0:
            return None, "Audio file contains no audio frames (empty recording)"
        
        # Convert to mono if stereo
        if channels == 2:
            if AUDIOOP_AVAILABLE and audioop:
                frames = audioop.tomono(frames, sample_width, 1, 1)
                logger.info("Converted stereo to mono")
            else:
                return None, "Cannot convert stereo to mono: audioop not available"
        elif channels != 1:
            return None, f"Unsupported channel count: {channels}. Expected mono (1) or stereo (2)."
        
        # Ensure we have 16-bit samples
        if sample_width != 2:  # 2 bytes = 16-bit
            if AUDIOOP_AVAILABLE and audioop:
                # Convert to 16-bit
                if sample_width == 1:  # 8-bit to 16-bit
                    frames = audioop.lin2lin(frames, 1, 2)
                elif sample_width == 4:  # 32-bit to 16-bit
                    frames = audioop.lin2lin(frames, 4, 2)
                else:
                    return None, f"Unsupported sample width: {sample_width*8}-bit. Expected 8, 16, or 32-bit."
                logger.info(f"Converted {sample_width*8}-bit to 16-bit")
            else:
                return None, f"Cannot convert {sample_width*8}-bit to 16-bit: audioop not available"
        
        # Resample to 16kHz if needed
        if sample_rate != 16000:
            if AUDIOOP_AVAILABLE and audioop:
                frames = audioop.ratecv(frames, 2, 1, sample_rate, 16000, None)[0]
                logger.info(f"Resampled from {sample_rate}Hz to 16000Hz")
            else:
                return None, f"Cannot resample from {sample_rate}Hz to 16000Hz: audioop not available"
        
        logger.info(f"Final audio: {len(frames)} bytes PCM16 16kHz mono")
        
        if len(frames) < 1000:
            return None, f"Converted audio too short ({len(frames)} bytes). Recording might be too brief."
        
        return frames, ""
        
    except Exception as e:
        logger.error(f"Error converting recorded audio: {e}", exc_info=True)
        return None, f"Error processing audio: {str(e)}"

async def test_sarvam_tts(text: str) -> tuple[bytes | None, str]:
    """
    Test Sarvam TTS API.
    
    Args:
        text (str): Text to convert to speech
        
    Returns:
        tuple: (audio_bytes, error_message)
    """
    if not sarvam_client:
        return None, "Sarvam client not initialized. Check SARVAM_API_KEY in environment."
    
    # Check if API key is set
    if not sarvam_client.api_key:
        return None, "❌ SARVAM_API_KEY is not set. Please add it to your .env file."
    
    if not text or not text.strip():
        return None, "❌ Please enter some text to convert to speech."
    
    try:
        logger.info(f"Calling Sarvam TTS with text: {text[:50]}...")
        audio_bytes = await sarvam_client.streaming_tts(text)
        
        if audio_bytes:
            logger.info(f"Successfully generated {len(audio_bytes)} bytes of audio")
            return audio_bytes, ""
        else:
            # Check logs for more details - the actual error is logged in streaming_tts
            error_details = []
            if not sarvam_client.api_key:
                error_details.append("API key is missing")
            else:
                error_details.append("API returned None - check server logs for details")
                error_details.append(f"API Key present: {'Yes' if sarvam_client.api_key else 'No'}")
                error_details.append(f"API Key length: {len(sarvam_client.api_key) if sarvam_client.api_key else 0}")
            
            return None, f"❌ Failed to generate audio.\n\nPossible issues:\n" + "\n".join(f"- {detail}" for detail in error_details)
            
    except Exception as e:
        logger.error(f"Error in Sarvam TTS: {e}", exc_info=True)
        return None, f"❌ Error: {str(e)}\n\nCheck the console/logs for more details."

def main():
    """Main application function."""
    
    # Initialize session
    session_id = initialize_session()
    
    # Initialize voice session state
    if 'voice_messages' not in st.session_state:
        st.session_state.voice_messages = []
    
    # Header
    st.markdown('<h1 class="main-header">🤖 Agent & Voice Testing Interface</h1>', unsafe_allow_html=True)
    
    # Sidebar with configuration and controls
    with st.sidebar:
        st.markdown("## ⚙️ Configuration")
        st.markdown("---")
        
        # Show current LLM configuration
        st.markdown("### 🔧 LLM Settings")
        st.markdown(f"""
        <div class="config-box">
            <strong>Provider:</strong> {settings.LLM_PROVIDER.upper()}<br>
            <strong>Model:</strong> {settings.get_llm_model_name()}<br>
            <strong>Temperature:</strong> {settings.AI_TEMPERATURE}
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        st.markdown("### 📊 Session Info")
        st.code(f"Session ID:\n{session_id[:8]}...", language=None)
        st.info(f"💬 Messages: {len(st.session_state.voice_messages)}")
        
        st.markdown("---")
        st.markdown("### 🎯 Quick Actions")
        
        if st.button("🔄 New Session", use_container_width=True):
            st.session_state.session_id = str(uuid.uuid4())
            st.session_state.voice_messages = []
            st.session_state.message_history = []
            st.rerun()
        
        if st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.voice_messages = []
            st.session_state.message_history = []
            st.rerun()
        
        st.markdown("---")
        st.markdown("### ℹ️ About")
        st.markdown("""
        This interface allows you to test the agent with voice interaction.
        
        **Features:**
        - Voice recording
        - Speech-to-text (STT)
        - Agent processing
        - Text-to-speech (TTS)
        - Conversation history
        """)
    
    # Main content area
    st.markdown("### 🎙️ Voice Agent Interface")
    
    # Check if Sarvam client is available
    if not sarvam_client or not sarvam_client.api_key:
        st.error("❌ Sarvam client not initialized. Please set SARVAM_API_KEY in your environment variables.")
        st.info("💡 Add `SARVAM_API_KEY=your_key_here` to your `.env` file.")
        st.stop()
    
    # Display conversation history
    if st.session_state.voice_messages:
        st.markdown("#### 💬 Conversation History")
        for idx, msg in enumerate(st.session_state.voice_messages):
            if msg["role"] == "user":
                st.markdown(f'<div class="user-message">🎤 <strong>You:</strong> {msg["text"]}</div>', unsafe_allow_html=True)
                if msg.get("audio"):
                    st.audio(msg["audio"], format="audio/wav")
            else:
                st.markdown(f'<div class="ai-message">🤖 <strong>Agent:</strong> {msg["text"]}</div>', unsafe_allow_html=True)
                audio_data = msg.get("audio")
                if audio_data:
                    try:
                        if isinstance(audio_data, bytes) and len(audio_data) > 0:
                            st.audio(audio_data, format="audio/wav")
                        else:
                            st.warning(f"⚠️ Invalid audio data")
                    except Exception as e:
                        logger.error(f"Error playing audio: {e}", exc_info=True)
                        st.error(f"❌ Could not play audio: {e}")
        st.markdown("---")
    else:
        st.info("👋 Click the microphone button below to start a voice conversation!")
    
    # Microphone button - centered
    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("<div style='text-align: center;'>", unsafe_allow_html=True)
        audio_bytes = audio_recorder()
        st.markdown("</div>", unsafe_allow_html=True)
    
    # Process recorded audio
    # audio-recorder-streamlit returns a dict with 'bytes' key or bytes directly
    if audio_bytes:
        # Handle dict format if returned
        if isinstance(audio_bytes, dict):
            audio_bytes = audio_bytes.get('bytes') or audio_bytes.get('audio_bytes')
            if not audio_bytes:
                st.warning("⚠️ Audio recorder returned unexpected format. Please try recording again.")
                audio_bytes = None
        
        if audio_bytes:
            st.info(f"📊 Received audio: {len(audio_bytes)} bytes")
            with st.spinner("🔄 Processing your voice..."):
                try:
                    # Step 1: Convert recorded audio to PCM16 16kHz
                    pcm16_16k, conversion_error = convert_recorded_audio_to_pcm16(audio_bytes)
                    
                    if not pcm16_16k:
                        st.error(f"❌ Audio conversion failed: {conversion_error}")
                        with st.expander("🔍 Debug Audio Info"):
                            st.code(f"""
Audio Size: {len(audio_bytes)} bytes
First 100 bytes (hex): {audio_bytes[:100].hex() if len(audio_bytes) >= 100 else 'N/A'}
Error: {conversion_error}
                            """)
                    else:
                        st.info(f"✅ Audio converted: {len(pcm16_16k)} bytes PCM16 16kHz mono")
                        # Step 2: Speech to Text
                        with st.spinner("🎤 Converting speech to text..."):
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            transcript, stt_error = loop.run_until_complete(test_sarvam_stt(pcm16_16k))
                            loop.close()
                        
                        if transcript:
                            st.success(f"✅ You said: {transcript}")
                            
                            # Add user message to history
                            st.session_state.voice_messages.append({
                                "role": "user",
                                "text": transcript,
                                "audio": audio_bytes,
                                "timestamp": datetime.now().isoformat()
                            })
                            
                            # Step 3: Get Agent Response
                            with st.spinner("🤔 Agent is thinking..."):
                                try:
                                    ai_response = send_message_to_agent(transcript, session_id)
                                except Exception as e:
                                    ai_response = f"❌ Error: {str(e)}"
                                    logger.error(f"Error in agent call: {e}", exc_info=True)
                            
                            # Step 4: Text to Speech
                            if ai_response and not ai_response.startswith("❌"):
                                with st.spinner("🔊 Converting response to speech..."):
                                    loop = asyncio.new_event_loop()
                                    asyncio.set_event_loop(loop)
                                    tts_audio_bytes, tts_error = loop.run_until_complete(test_sarvam_tts(ai_response))
                                    loop.close()
                                
                                if tts_audio_bytes:
                                    # Convert mulaw to WAV for playback
                                    logger.info(f"Converting {len(tts_audio_bytes)} bytes of mulaw audio to WAV")
                                    response_audio = convert_mulaw_to_wav(tts_audio_bytes)
                                    
                                    if response_audio:
                                        logger.info(f"Created WAV file: {len(response_audio)} bytes")
                                    else:
                                        logger.warning("Failed to convert audio to WAV")
                                        st.warning("⚠️ Audio conversion failed")
                                    
                                    # Add agent response to history
                                    msg_data = {
                                        "role": "assistant",
                                        "text": ai_response,
                                        "timestamp": datetime.now().isoformat()
                                    }
                                    if response_audio:
                                        msg_data["audio"] = response_audio
                                        logger.info(f"Added message with audio ({len(response_audio)} bytes)")
                                    else:
                                        logger.warning("Added message without audio (conversion failed)")
                                    
                                    st.session_state.voice_messages.append(msg_data)
                                    
                                    if response_audio:
                                        st.success(f"✅ Voice response generated!")
                                        st.audio(response_audio, format="audio/wav")
                                    else:
                                        st.warning("⚠️ Text response generated but audio conversion failed. Check logs.")
                                    st.rerun()
                                else:
                                    st.error(f"❌ TTS Error: {tts_error}")
                            else:
                                st.error(f"❌ Agent Error: {ai_response}")
                        else:
                            st.error(f"❌ STT Error: {stt_error}")
                        
            except Exception as e:
                st.error(f"❌ Error processing audio: {str(e)}")
                logger.error(f"Audio processing error: {e}", exc_info=True)
    
    # Footer
    st.markdown("---")
    st.markdown(
        '<p style="text-align: center; color: #666; font-size: 0.875rem;">'
        'Agent & Voice Testing Interface | Direct Testing | No Phone Calls Required'
        '</p>',
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()

