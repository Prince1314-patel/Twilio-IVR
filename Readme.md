# AI Voice IVR Wellness Coach

## Overview

This project is an AI-powered Interactive Voice Response (IVR) system designed to provide empathetic, conversational wellness coaching over the phone. It leverages FastAPI, Twilio, and advanced language models (Groq LLM via LangChain) to create a natural, supportive experience for users calling in. The system can receive calls, transcribe speech, generate AI responses, and reply with synthesized speech.

---

## Features

- **AI Assistant:** Empathetic, conversational AI that supports users with positive, open-ended dialogue.
- **Voice Interaction:** Users interact entirely via phone calls using speech.
- **Twilio Integration:** Handles incoming and outgoing calls.
- **LLM Integration:** Uses Groq LLM (via LangChain) for generating responses.
- **Speech-to-Text & Text-to-Speech:** (Planned) Converts user speech to text and AI responses to speech.
- **Modular API:** Extensible FastAPI endpoints for speech and LLM services.

---

## Directory Structure

```
.
├── answer_phone.py         # Main FastAPI app for handling incoming calls and conversation loop
├── make_call.py            # Script to initiate outbound calls via Twilio
├── modules/
│   ├── text_to_speech.py   # (Stub) API for TTS synthesis (Chatterbox TTS integration planned)
│   ├── speech_to_text.py   # (Stub) API for STT transcription (Groq Whisper integration planned)
│   ├── llm_agent.py        # (Stub) API for LLM-based responses (LangChain integration planned)
│   └── twilio_webhook.py   # (Stub) API for handling Twilio voice webhooks
├── requirements.txt        # Python dependencies
├── Readme.md               # Project documentation
└── ...
```

---

## Setup Instructions

### 1. Clone the Repository

```bash
git clone <repo-url>
cd <repo-directory>
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Environment Variables

Create a `.env` file in the project root with the following keys:

```
GROQ_API_KEY=your_groq_api_key
TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
```

### 4. Run the Server

```bash
uvicorn answer_phone:app --reload
```

The FastAPI server will start on `http://0.0.0.0:8000`.

### 5. Run the ngrok app

```bash
ngrok.exe http 8000
```
---

## Usage

### Receiving Calls

- Twilio should be configured to forward incoming calls to your server’s `/incoming-call` endpoint.
- The AI will greet the user and engage in a conversational loop, responding empathetically to user speech.

### Making Outbound Calls

- Use `make_call.py` to initiate a call from your Twilio number to a target number.
- The script will connect the call and start the AI conversation.

---

## API Endpoints

- `/` : Health check (GET/POST)
- `/incoming-call` : Handles new incoming calls (POST)
- `/handle-speech` : Processes user speech and responds (POST)

### Modular APIs (in `modules/`)

- `/synthesize` : (Planned) Synthesize speech from text
- `/transcribe` : (Planned) Transcribe audio to text
- `/ask` : (Planned) Get LLM response to user text
- `/voice` : (Planned) Handle Twilio voice webhook

---

## Dependencies

- `fastapi`, `uvicorn` — Web server and API framework
- `websockets` — For real-time communication (future use)
- `twilio` — Telephony integration
- `torch`, `torchaudio` — For audio processing (future use)
- `langchain-groq`, `groq` — LLM integration
- `chatterbox-tts` — Text-to-speech (planned)
- `pydub`, `numpy` — Audio manipulation
- `python-dotenv` — Environment variable management

---

## Extending the Project

- **Speech-to-Text:** Integrate Groq Whisper in `modules/speech_to_text.py`.
- **Text-to-Speech:** Integrate Chatterbox TTS in `modules/text_to_speech.py`.
- **LLM Agent:** Complete LangChain integration in `modules/llm_agent.py`.
- **Production Deployment:** Use a production ASGI server (e.g., Gunicorn) and persistent session storage (e.g., Redis).

---

## License

Specify your license here.

---

## Acknowledgments

- [Twilio](https://www.twilio.com/)
- [LangChain](https://www.langchain.com/)
- [Groq](https://groq.com/)
- [FastAPI](https://fastapi.tiangolo.com/)
