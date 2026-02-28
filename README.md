# Healthcare AI Voice Calling Agent

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![LiveKit](https://img.shields.io/badge/LiveKit-Agents-brightgreen.svg)](https://livekit.io/)
[![LangGraph](https://img.shields.io/badge/LangGraph-Agentic%20Workflows-orange.svg)](https://langchain-ai.github.io/langgraph/)
[![Sarvam AI](https://img.shields.io/badge/Sarvam%20AI-Indian%20Languages-blue.svg)](https://www.sarvam.ai/)

This project is a high-performance **Healthcare AI Voice Assistant** designed to automate appointment management (booking, rescheduling, and cancellation). It leverages **LiveKit** for real-time voice orchestration, **LangGraph** for deterministic conversational logic, and **Sarvam AI** for specialized Indian language STT/TTS.

---

## 🌟 Key Features

*   **Real-Time Agentic Voice**: Low-latency, bi-directional voice interactions using LiveKit Agents.
*   **Localized Language Excellence**: High-accuracy STT and natural TTS for Indian English and Hindi via Sarvam AI (Saaras & Bulbul models).
*   **Deterministic Conversation Flows**: LangGraph-powered state machine ensures strict adherence to clinical protocols and business rules.
*   **Transactional Safety**: Robust handling of appointment operations with backend verification to prevent hallucinations.
*   **SIP Telephony Support**: Seamless integration with traditional phone lines via SIP trunking.
*   **Multi-Modal**: Support for both Voice (LiveKit) and Chat (FastAPI/WebSocket) interfaces.

---

## 🏗️ Architecture

The system has transitioned from a legacy Twilio-centric model to a modular **LiveKit Agent** architecture:

1.  **Orchestrator**: `agent_worker.py` (LiveKit Worker) listens for room events and manages `AgentSession`.
2.  **Perception (STT)**: Sarvam AI streaming STT converts audio to text with Indian accent optimization.
3.  **Brain (LLM/Graph)**: A LangGraph-based ReAct agent handles intent detection, slot filling, and tool execution.
4.  **Synthesis (TTS)**: Sarvam AI Bulbul model generates empathetic, high-quality audio responses.
5.  **Database**: Managed SQLite layer for consistent appointment tracking.

---

## 🛠️ Setup and Installation

### 1. Prerequisites
- Python 3.9+ 
- LiveKit Cloud account (or self-hosted)
- OpenAI / Groq API Keys
- Sarvam AI API Key
- Twilio Account (for SIP/Telephony)

### 2. Installation
```bash
git clone https://github.com/Inexture-Projects/voice_calling_ai_agent.git
cd voice_calling_ai_agent/backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Environment Setup
Configure your `.env` file based on `.env.example`:
```env
LIVEKIT_URL=wss://your-livekit-url.livekit.cloud
LIVEKIT_API_KEY=your_key
LIVEKIT_API_SECRET=your_secret
SARVAM_API_KEY=your_sarvam_key
OPENAI_API_KEY=your_openai_key
```

---

## 🚀 Running the Project

### Starting the LiveKit Agent
The agent worker must be running to handle voice calls or playground sessions.

**Development (Auto-reload):**
```bash
cd backend
python -m app.livekit.agent_worker dev
```

**Production:**
```bash
cd backend
python -m app.livekit.agent_worker start
```

### Starting the Backend API (For Chat/Dashboard)
```bash
cd backend
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

---

## 🧪 Testing and Deployment

### 1. SIP Participant Testing
To test the agent via a real phone call using the SIP trunk, use the LiveKit CLI with the provided credentials:

```bash
lk sip participant create call.json \
  --url wss://voice-calling-agent-1k8t5v8j.livekit.cloud \
  --api-key APIE8uXibtphfRr \
  --api-secret UUa22CfNgLwkDMYVydBeeUJa9Uc4b3WzyfXFRHcaIrnD
```
*(Note: Ensure `call.json` contains the correct `sip_trunk_id` and `sip_call_to` number.)*

### 2. LiveKit Playground
1. Generate a dev token: `python3 scripts/generate_dev_token.py`
2. Open [LiveKit Agents Playground](https://agents-playground.livekit.io/).
3. Connect using the generated URL and Token.

---

## 📂 Project Structure

- `backend/app/livekit/`: LiveKit worker and LangGraph adapters.
- `backend/app/ai/graph/`: Deterministic agent graph and node logic.
- `backend/app/database/`: SQL models and transactional tools.
- `frontend/`: React monitoring dashboard.
- `scripts/`: Development utilities.

---

## 📜 Recent Architecture Changes
- **LiveKit Migration**: Replaced legacy Twilio Media Stream WebSockets with LiveKit AgentSession for superior voice performance and simplified orchestration.
- **Deterministic Routing**: Integrated LangGraph to eliminate LLM hallucinations during appointment booking.
- **Sarvam Native Integration**: Optimized STT/TTS for Indian locales, reducing latency significantly.

---

## 📄 License
MIT License. See `LICENSE` for details.
