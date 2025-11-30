# Sarvam AI API Documentation Summary

## Overview
Sarvam AI provides Speech-to-Text (STT) and Text-to-Speech (TTS) APIs for Indian languages.

## SDK Initialization

```python
from sarvamai import SarvamAI

client = SarvamAI(api_subscription_key="YOUR_API_KEY")
```

**Note**: Parameter is `api_subscription_key`, NOT `api_key`

---

## Speech-to-Text (STT) API

### SDK Method (Recommended)

```python
# Open file as binary
with open("audio.wav", "rb") as audio_file:
    response = client.speech_to_text.transcribe(
        file=audio_file,  # File object, NOT file path!
        model="saarika:v2.5",
        language_code="hi-IN"  # Or "unknown" for auto-detection
    )

# Extract transcript
transcript = response.transcript  # If response object
# OR
transcript = response["transcript"]  # If response dict
```

### Key Points:
- **File Parameter**: SDK expects a **file object** (`open("file.wav", "rb")`), NOT a file path string
- **Model**: Use `"saarika:v2.5"` for transcription
- **Language Code**: 
  - Use specific code like `"hi-IN"` for Hindi
  - Use `"unknown"` for automatic language detection
- **Response Format**: Returns object with `.transcript` attribute or dict with `"transcript"` key

### Supported Audio Formats:
- WAV, MP3, AAC, AIFF, OGG, FLAC, MP4, AMR, WMA, WEBM
- **PCM formats** (pcm_s16le, pcm_l16, pcm_raw) - **ONLY at 16kHz sample rate**
- For PCM, must specify `input_audio_codec` parameter

### Real-time API Limits:
- Maximum duration: **30 seconds**
- For longer files, use Batch API or split into chunks

### REST API Endpoint:
- `POST https://api.sarvam.ai/speech-to-text`
- Headers: `api-subscription-key: YOUR_KEY`
- Content-Type: `multipart/form-data`
- Form fields:
  - `file`: Audio file
  - `model`: "saarika:v2.5"
  - `language_code`: "hi-IN"

---

## Text-to-Speech (TTS) API

### SDK Method (Recommended)

```python
response = client.text_to_speech.convert(
    target_language_code="hi-IN",
    text="नमस्ते",
    model="bulbul:v2",  # Use v2, not v1
    speaker="anushka"  # Available: anushka, meera, pavithra, etc.
)

# Extract audio (base64 encoded)
audio_base64 = response.audios[0]  # First audio in array
audio_bytes = base64.b64decode(audio_base64)
```

### Key Points:
- **Method**: `text_to_speech.convert()`, NOT `text_to_speech()`
- **Model**: Use `"bulbul:v2"` (latest), NOT `"bulbul:v1"`
- **Speaker Options**: "anushka", "meera", "pavithra", etc.
- **Response**: Object with `.audios` attribute (array of base64 strings)
- **Text Limit**: 500 characters per input, max 3 texts per call

### Advanced Parameters:
```python
response = client.text_to_speech.convert(
    target_language_code="hi-IN",
    text="Hello",
    model="bulbul:v2",
    speaker="anushka",
    speech_sample_rate=8000,  # 8000 for Twilio (mulaw)
    output_audio_codec="mulaw",  # For Twilio compatibility
    pitch=0.0,  # -20.0 to 20.0
    pace=1.0,  # 0.5 to 2.0
    loudness=1.0,  # 0.5 to 2.0
    enable_preprocessing=True  # For code-mixed text
)
```

### Supported Audio Formats:
- WAV (default)
- MP3
- Linear16
- Mulaw (for Twilio)
- Alaw
- Opus
- FLAC
- AAC

### REST API Endpoint:
- `POST https://api.sarvam.ai/text-to-speech`
- Headers: 
  - `api-subscription-key: YOUR_KEY`
  - `Content-Type: application/json`
- Body (JSON):
```json
{
  "text": "नमस्ते",
  "target_language_code": "hi-IN",
  "model": "bulbul:v2",
  "speaker": "anushka",
  "speech_sample_rate": 8000,
  "audio_format": "mulaw"
}
```

---

## Common Issues & Solutions

### Issue 1: "Failed to read the file, please check the audio format"
**Cause**: SDK expects file object, not file path string
**Solution**: Use `open("file.wav", "rb")` instead of file path

### Issue 2: Empty transcript
**Cause**: Audio too short, silent, or wrong format
**Solution**: 
- Ensure minimum 200ms of audio
- Check audio has actual speech content
- Verify WAV file format is correct

### Issue 3: 400 Bad Request
**Cause**: Incorrect request format or parameters
**Solution**: 
- Verify file is properly opened as binary
- Check model name is correct ("saarika:v2.5", "bulbul:v2")
- Ensure language code is valid BCP-47 format

### Issue 4: PCM format errors
**Cause**: PCM files must be 16kHz and require `input_audio_codec` parameter
**Solution**: 
- Resample to 16kHz if needed
- Specify `input_audio_codec="pcm_s16le"` for PCM files

---

## Response Format Examples

### STT Response:
```python
# Object format
response.transcript  # "नमस्ते"
response.language_code  # "hi-IN"
response.request_id  # "unique_id"

# Dict format
response["transcript"]
response["language_code"]
response["request_id"]
```

### TTS Response:
```python
# Object format
response.audios  # ["base64_encoded_audio_string"]
response.request_id  # "unique_id"

# Access first audio
audio_base64 = response.audios[0]
audio_bytes = base64.b64decode(audio_base64)
```

---

## Authentication

- Header: `api-subscription-key: YOUR_KEY`
- NOT `Authorization: Bearer` or `api-key`
- Get API key from: https://dashboard.sarvam.ai/

---

## Language Codes (BCP-47)

Supported languages:
- Hindi: `"hi-IN"`
- English: `"en-IN"`
- Bengali: `"bn-IN"`
- Tamil: `"ta-IN"`
- Telugu: `"te-IN"`
- Kannada: `"kn-IN"`
- Malayalam: `"ml-IN"`
- Marathi: `"mr-IN"`
- Gujarati: `"gu-IN"`
- Punjabi: `"pa-IN"`
- Odia: `"od-IN"`

---

## References

- Official Docs: https://docs.sarvam.ai/
- Quickstart: https://docs.sarvam.ai/api-reference-docs/getting-started/quickstart
- STT API: https://docs.sarvam.ai/api-reference-docs/api-guides-tutorials/speech-to-text/real-time-api
- TTS API: https://docs.sarvam.ai/api-reference-docs/api-guides-tutorials/text-to-speech/rest-api
- Discord: https://discord.com/invite/5rAsykttcs

