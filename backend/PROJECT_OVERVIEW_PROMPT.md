# Twilio IVR Project Overview Prompt for ChatGPT

Copy and paste this entire prompt into ChatGPT to provide comprehensive project context:

---

## PROJECT OVERVIEW

I'm working on a **Healthcare AI Voice IVR (Interactive Voice Response) System** built with Python, FastAPI, Twilio, and LangChain. This is an intelligent appointment booking system that allows users to interact via voice calls to schedule, reschedule, or cancel appointments.

## TECHNOLOGY STACK

- **Backend Framework**: FastAPI with Uvicorn (ASGI server)
- **Voice Communication**: Twilio (voice calls, webhooks, TwiML)
- **AI/LLM**: 
  - LangChain & LangGraph for agentic AI workflows
  - OpenAI GPT-4o (primary LLM)
  - Groq (alternative LLM provider)
- **Text-to-Speech & Speech-to-Text**: 
  - Sarvam AI SDK (for Hindi/Indian languages)
  - Twilio Polly (fallback TTS)
- **Database**: SQLite (in-memory by default, can be configured for persistent storage)
- **Real-time Communication**: WebSockets for chat interface
- **Additional**: Streamlit for web UI, Pydantic for validation, pytz for timezone handling

## PROJECT STRUCTURE

```
Twilio-IVR/
├── app/                          # Main application module
│   ├── main.py                   # FastAPI app entry point, WebSocket handling
│   ├── core/                     # Core utilities and configuration
│   │   ├── config.py            # Settings and environment variables
│   │   ├── sarvam_client.py     # Sarvam AI SDK wrapper (TTS/STT)
│   │   └── websocket_manager.py # WebSocket connection management
│   └── routers/                  # API route handlers
│       ├── chat.py              # Chat API endpoints
│       └── voice.py             # Voice/Twilio webhook endpoints
├── agentic_graph/                # AI agent implementation
│   ├── agent_graph.py           # LangGraph agent setup and execution
│   └── prompts.py               # AI agent system prompts
├── db_tool/                      # Database layer
│   ├── db_manager.py            # SQLite database operations
│   └── db_tools.py              # LangChain-compatible tools for AI agent
├── archive/                      # Legacy/archived files
├── requirements.txt              # Python dependencies
├── README.md                     # Project documentation
└── streamlit_app.py              # Streamlit web interface (optional)
```

## KEY ARCHITECTURAL COMPONENTS

### 1. **FastAPI Application (`app/main.py`)**
- Main FastAPI app with CORS middleware
- WebSocket endpoint (`/ws/{session_id}`) for real-time chat
- Includes routers for chat and voice functionality
- Manages conversation history per session
- Health check endpoint

### 2. **Voice Router (`app/routers/voice.py`)**
- **`/incoming-call`**: Handles incoming Twilio calls, generates greeting with Sarvam TTS
- **`/handle-recording`**: Processes user speech recordings:
  - Downloads audio from Twilio
  - Transcribes using Sarvam STT
  - Processes through AI agent
  - Generates response audio with Sarvam TTS
  - Returns TwiML for next interaction
- **`/initiate-call`**: API endpoint to make outbound calls
- **`/audio/{audio_id}`**: Serves cached audio files
- **`/call-status/{call_sid}`**: Get call status
- **`/active-calls`**: List active call sessions
- Uses retry logic with exponential backoff for Twilio operations
- Maintains in-memory `call_sessions` dict for conversation history per call

### 3. **AI Agent (`agentic_graph/agent_graph.py`)**
- Uses LangGraph's `create_react_agent` pattern
- Single comprehensive ReAct agent for appointment management
- Tools available:
  - `check_appointment_availability(date, time)`
  - `create_appointment_in_db(name, email, type, date, time, notes)`
  - `get_available_slots_for_date(date)`
  - `update_appointment_in_db(appointment_id, ...)`
  - `cancel_appointment_in_db(appointment_id)`
- Entry point: `run_agentic_graph(messages, thread_id)` returns agent response as string
- Includes current time context (Asia/Kolkata timezone) in system message

### 4. **Database Tools (`db_tool/db_tools.py`)**
- LangChain-compatible `@tool` decorated functions
- Comprehensive validation:
  - Date format (YYYY-MM-DD)
  - Time format (HH:MM:SS, 24-hour)
  - Email validation
  - Name validation (letters, spaces, hyphens only)
  - Appointment type (telephonic/virtual)
  - Future datetime check
  - Business hours (9 AM - 5 PM)
  - Slot granularity (hour or half-hour only)
- Returns user-friendly error messages
- Suggests alternative slots when requested slot unavailable

### 5. **Database Manager (`db_tool/db_manager.py`)**
- SQLite database operations
- CRUD operations for appointments
- Availability checking
- Slot generation (9 AM - 5 PM, hourly/half-hourly)

### 6. **Sarvam Client (`app/core/sarvam_client.py`)**
- Wrapper around `sarvamai` SDK
- **`text_to_speech(text, language_code, speaker_gender)`**: Returns audio bytes
- **`speech_to_text(audio_content, language_code)`**: Returns transcript string
- Uses temporary files for STT processing
- Handles errors gracefully with fallback to Twilio TTS

### 7. **Configuration (`app/core/config.py`)**
- Centralized settings via `Settings` class
- Environment variables loaded via `python-dotenv`
- Required settings: OpenAI API key, Twilio credentials
- Optional: Groq API key, Sarvam API key
- Business hours, timezone, model configurations

## DATA FLOW

### Voice Call Flow:
1. User calls Twilio number → Twilio sends POST to `/api/voice/incoming-call`
2. Server generates greeting with Sarvam TTS → Returns TwiML with audio URL
3. Twilio plays audio → Records user speech → POSTs to `/api/voice/handle-recording`
4. Server downloads recording → Transcribes with Sarvam STT
5. Transcript sent to `run_agentic_graph()` → Agent processes with tools
6. Agent response → Generated as audio with Sarvam TTS → Returned as TwiML
7. Loop continues until call ends

### Chat Flow (WebSocket):
1. Client connects to `/ws/{session_id}`
2. Messages sent via WebSocket → Processed through `run_agentic_graph()`
3. Conversation history maintained per session
4. AI responses sent back via WebSocket

## KEY PATTERNS & CONVENTIONS

### Code Style:
- **Google-style docstrings** with Args, Returns, Parameters sections
- **snake_case** for functions/variables
- **PascalCase** for classes
- **UPPER_CASE** for constants
- Modular structure with clear separation of concerns

### Error Handling:
- Comprehensive validation at tool level
- Retry logic for Twilio operations (3 attempts, exponential backoff)
- Graceful fallbacks (Sarvam TTS → Twilio TTS)
- User-friendly error messages

### AI Agent Behavior:
- **Strict anti-hallucination rules**: Must use tools for all appointment data
- Never guesses or invents information
- Asks clarifying questions when unclear
- Collects all required fields before booking
- Confirms details before finalizing actions
- Provides appointment IDs after creation

### Timezone Handling:
- All times in **Asia/Kolkata** timezone
- Current time injected into agent context
- Business hours: 9 AM - 5 PM IST
- Slot granularity: Hour or half-hour only

## CURRENT STATE

### Recent Changes (from git status):
- Modified: `app/routers/voice.py` (voice handling improvements)
- Modified: `requirements.txt` (dependency updates)
- New: `app/core/sarvam_client.py` (Sarvam AI integration)
- New: `test_sarvam_flow.py` (testing file)

### Active Branch: `servan-tts` (likely "Sarvam TTS")

## IMPORTANT ENVIRONMENT VARIABLES

Required:
- `OPENAI_API_KEY`: For LangGraph agent
- `TWILIO_ACCOUNT_SID`: Twilio account identifier
- `TWILIO_AUTH_TOKEN`: Twilio authentication token
- `TWILIO_PHONE_NUMBER`: Twilio phone number (E.164 format)
- `TWILIO_WEBHOOK_URL`: Public URL for Twilio webhooks (e.g., ngrok URL)

Optional:
- `GROQ_API_KEY`: Alternative LLM provider
- `SARVAM_API_KEY`: For Sarvam TTS/STT (if using)
- `DEBUG`: Enable debug mode
- `TIMEZONE`: Default "Asia/Kolkata"
- `BUSINESS_START_HOUR`: Default 9
- `BUSINESS_END_HOUR`: Default 17

## KEY FEATURES

1. **Voice-Enabled Appointment Management**: Full voice interaction via phone calls
2. **Intelligent Conversational AI**: LangGraph agent with tool-calling capabilities
3. **Multi-language Support**: Sarvam AI for Hindi/Indian languages
4. **Robust Validation**: Comprehensive input validation at multiple layers
5. **Business Rules Enforcement**: Business hours, slot granularity, future-only bookings
6. **Alternative Slot Suggestions**: When requested slot unavailable, suggests closest alternatives
7. **Session Management**: Maintains conversation context per call/chat session
8. **Error Recovery**: Retry logic, fallbacks, graceful error handling

## TESTING & DEVELOPMENT

- Virtual environment: `venv/` or `.venv/`
- Activate before running: `source venv/bin/activate` (Linux/Mac) or `venv\Scripts\activate` (Windows)
- Run server: `python -m uvicorn app.main:app --reload` or `python app/main.py`
- Streamlit UI: `streamlit run streamlit_app.py`
- Testing: `test_sarvam_flow.py` for Sarvam integration testing

## COMMON TASKS

- **Add new appointment field**: Update `db_manager.py` schema, `db_tools.py` validation, agent prompt
- **Change business hours**: Update `config.py` or environment variables
- **Add new tool**: Create in `db_tools.py` with `@tool` decorator, add to `agent_graph.py` tools list
- **Modify AI behavior**: Update `agentic_graph/prompts.py` `GENERAL_AGENT_PROMPT`
- **Add new API endpoint**: Create in `app/routers/` and include in `app/main.py`

---

**When helping with this project, please:**
1. Follow the existing code structure and patterns
2. Maintain Google-style docstrings
3. Add proper error handling and validation
4. Consider both voice and chat interfaces
5. Ensure timezone handling (Asia/Kolkata)
6. Test with actual Twilio calls when possible
7. Follow the modular architecture (routers → services → database)

