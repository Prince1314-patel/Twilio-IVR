# Appointment Voice Chatbot with Twilio

This project is an AI Voice IVR (Interactive Voice Response) system designed to automate appointment booking, rescheduling, and cancellation. It leverages Twilio for voice communication, FastAPI for the web server, and a sophisticated agentic AI powered by LangChain and LangGraph for intelligent conversational flow and appointment management.

### Features

*   **Voice-Enabled Appointment Management**: Users can interact with the AI assistant via voice to schedule, reschedule, or cancel appointments.
*   **Intelligent Conversational Agent**: Powered by LangChain and LangGraph, the AI understands natural language queries related to appointments.
*   **Appointment Availability Check**: The system can check for available time slots based on user-specified dates and times.
*   **Database Integration**: Seamlessly manages appointment data (creation, updates, cancellations) through a dedicated database tool.
*   **Input Validation**: Robust validation for dates, times, emails, names, and appointment types ensures data integrity.
*   **Business Hour & Slot Granularity Enforcement**: Appointments can only be booked within defined business hours and at specific time granularities (e.g., on the hour or half-hour).
*   **Twilio Integration**: Handles incoming and outgoing calls, converting speech to text and text to speech for a natural voice interaction.
*   **Scalable Web Server**: Built with FastAPI and Uvicorn for high-performance asynchronous operations.
*   **Modern Web Interface**: Beautiful React-based frontend with real-time chat, voice call initiation, and responsive design.

### Technologies Used

**Backend:**
*   **Python**: The core programming language.
*   **FastAPI**: A modern, fast (high-performance) web framework for building APIs.
*   **Uvicorn**: An ASGI server for running FastAPI applications.
*   **Twilio**: For programmable voice and SMS capabilities.
*   **LangChain**: Framework for developing applications powered by language models.
*   **LangGraph**: A library for building stateful, multi-actor applications with LLMs, enabling complex agentic behaviors.
*   **Groq**: Used as the LLM provider for fast inference.
*   **`python-dotenv`**: For managing environment variables.
*   **`pytz` & `tzdata`**: For timezone handling.
*   **`chatterbox-tts`**: For Text-to-Speech (TTS) capabilities.
*   **`pydub`**: For audio manipulation.
*   **`numpy`**: For numerical operations.
*   **`websockets`**: For WebSocket communication.
*   **`torch` & `torchaudio`**: Potentially for advanced audio processing or TTS.

**Frontend:**
*   **React**: Modern UI library for building interactive user interfaces.
*   **TypeScript**: Type-safe JavaScript for better code quality.
*   **Vite**: Fast build tool and development server.
*   **Tailwind CSS**: Utility-first CSS framework for rapid UI development.
*   **shadcn/ui**: Beautiful, accessible React components built on Radix UI.
*   **Framer Motion**: Animation library for smooth transitions.
*   **Axios**: HTTP client for API communication.
*   **date-fns**: Date utility library.

### Setup and Installation

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/your-username/appoinment_voice_chatbot_twilio.git
    cd appoinment_voice_chatbot_twilio
    ```

2.  **Create and activate a virtual environment**:
    ```bash
    python -m venv venv
    # On Windows
    .\venv\Scripts\activate
    # On macOS/Linux
    source venv/bin/activate
    ```

3.  **Install backend dependencies**:
    ```bash
    cd backend
    pip install -r requirements.txt
    ```

4.  **Environment Variables**:
    Create a `.env` file in the `backend/` directory (or root directory) and add the following:
    ```
    TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
    TWILIO_AUTH_TOKEN=your_twilio_auth_token
    TWILIO_PHONE_NUMBER=+1234567890  # Your Twilio phone number
    GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
    OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxx # Required by LangGraph agent
    ```
    Replace the placeholder values with your actual Twilio, Groq, and OpenAI API credentials.

5.  **Database Setup**:
    The `backend/db_tool` module uses an in-memory SQLite database for demonstration purposes. For persistent storage, you would need to modify `backend/db_tool/db_manager.py` to connect to a more robust database (e.g., PostgreSQL, MySQL).

6.  **Ngrok (or similar tunneling service)**:
    Twilio needs a publicly accessible URL to send incoming call webhooks. You can use `ngrok` for this.
    Download `ngrok.exe` (or the appropriate version for your OS) and place it in the project root or `backend/` directory.
    Run ngrok to expose your local server:
    ```bash
    ngrok http 8000
    ```
    Copy the `https` forwarding URL provided by ngrok (e.g., `https://your-ngrok-url.ngrok-free.app`). You will use this URL in your Twilio webhook configuration.

### Usage

#### Backend Setup

1.  **Navigate to backend directory and start the FastAPI server**:
    ```bash
    cd backend
    python -m uvicorn app.main:app --reload
    # Or
    python app/main.py
    ```
    The server will run on `http://localhost:8000`.

#### Frontend Setup

1.  **Navigate to the frontend directory**:
    ```bash
    cd frontend
    ```

2.  **Install dependencies** (if not already installed):
    ```bash
    npm install
    ```

3.  **Start the development server**:
    ```bash
    npm run dev
    ```
    The frontend will run on `http://localhost:3000` by default.

4.  **Build for production**:
    ```bash
    npm run build
    ```

5.  **Preview production build**:
    ```bash
    npm run preview
    ```

#### Twilio Configuration

6.  **Configure Twilio Webhook**:
    *   Go to your Twilio Phone Numbers dashboard.
    *   Select the Twilio phone number you want to use for this application.
    *   Under the "Voice & Fax" section, configure the "A CALL COMES IN" webhook to "Webhook" and paste your ngrok `https` forwarding URL followed by `/api/voice/incoming-call`.
        Example: `https://your-ngrok-url.ngrok-free.app/api/voice/incoming-call`
    *   Set the HTTP method to `POST`.

7.  **Make an Outbound Call (Optional)**:
    You can initiate an outbound call via the web interface (recommended) or using the API directly.
    **Using the Web Interface:**
    *   Open `http://localhost:3000` in your browser
    *   Enter your phone number in the voice call panel
    *   Click "Get Voice Call" to initiate a call
    
    **Using the API directly:**
    *   Make a POST request to `http://localhost:8000/api/voice/initiate-call`
    *   Include a JSON body with `phone_number` field
    *   Example:
    ```bash
    curl -X POST http://localhost:8000/api/voice/initiate-call \
      -H "Content-Type: application/json" \
      -d '{"phone_number": "+1234567890"}'
    ```

#### Interacting with the Application

8.  **Interact with the AI**:

    **Via Web Interface:**
    *   Open `http://localhost:3000` in your browser.
    *   Use the chat interface to interact with the AI assistant.
    *   Type messages to schedule, check, update, or cancel appointments.
    *   Click "Get Voice Call" to initiate a phone call to your number.

    **Via Voice Call:**
    *   Call your Twilio phone number.
    *   The AI assistant will greet you and prompt you to state your request regarding appointments.
    *   Speak naturally to schedule, reschedule, or cancel appointments.

### Project Structure

```
.
├── README.md                           # Project documentation
├── appointments.db                     # SQLite database file
├── appointment_tools.log              # Application logs
├── backend/                            # Backend application
│   ├── requirements.txt               # Python backend dependencies
│   ├── streamlit_app.py               # Legacy Streamlit app (optional)
│   ├── twilio_pipeline_app.py         # Twilio pipeline Streamlit app
│   ├── test_agent_streamlit.py        # Agent testing script
│   ├── test_sarvam_flow.py            # Sarvam integration test
│   ├── PROJECT_OVERVIEW_PROMPT.md     # Project overview documentation
│   ├── SARVAM_AI_DOCUMENTATION.md     # Sarvam AI documentation
│   ├── app/                           # FastAPI backend application
│   │   ├── main.py                    # FastAPI application entry point
│   │   ├── routers/                   # API route handlers
│   │   │   ├── chat.py                # Chat API endpoints
│   │   │   ├── voice.py               # Voice call API endpoints
│   │   │   └── voice_stream.py        # Voice streaming endpoints
│   │   ├── core/                      # Core configuration and utilities
│   │   │   ├── config.py              # Application configuration
│   │   │   ├── sarvam_client.py       # Sarvam AI client
│   │   │   └── websocket_manager.py   # WebSocket connection manager
│   │   └── audio/                     # Audio processing utilities
│   │       └── audio_utils.py         # Audio manipulation functions
│   ├── agentic_graph/                 # AI agent implementation
│   │   ├── agent_graph.py             # LangGraph agent setup
│   │   └── prompts.py                 # AI agent prompts
│   ├── db_tool/                       # Database layer
│   │   ├── db_manager.py              # Database operations
│   │   └── db_tools.py                # LangChain-compatible tools
│   └── archive/                       # Archived legacy files
│       └── legacy_files/              # Old implementation files
│           ├── answer_phone.py
│           ├── legacy_make_call.py
│           ├── make_call.py
│           ├── run_agent_cli.py
│           ├── start_app.py
│           └── test_integration.py
├── frontend/                          # React frontend application
│   ├── package.json                   # Frontend dependencies
│   ├── package-lock.json              # Dependency lock file
│   ├── vite.config.ts                 # Vite configuration
│   ├── tsconfig.json                  # TypeScript configuration
│   ├── tsconfig.node.json             # TypeScript config for Node
│   ├── tailwind.config.js             # Tailwind CSS configuration
│   ├── postcss.config.js              # PostCSS configuration
│   ├── components.json                # shadcn/ui configuration
│   ├── index.html                     # HTML entry point
│   ├── public/                        # Static assets
│   │   └── vite.svg
│   └── src/                           # Source code
│       ├── main.tsx                   # React application entry point
│       ├── App.tsx                    # Main app component
│       ├── components/                # React components
│       │   ├── ui/                    # shadcn/ui base components
│       │   │   ├── alert.tsx
│       │   │   ├── alert-dialog.tsx
│       │   │   ├── avatar.tsx
│       │   │   ├── badge.tsx
│       │   │   ├── button.tsx
│       │   │   ├── card.tsx
│       │   │   ├── input.tsx
│       │   │   ├── scroll-area.tsx
│       │   │   ├── separator.tsx
│       │   │   ├── skeleton.tsx
│       │   │   └── sonner.tsx
│       │   ├── chat/                  # Chat interface components
│       │   │   ├── ChatInterface.tsx
│       │   │   ├── ChatInput.tsx
│       │   │   └── MessageBubble.tsx
│       │   ├── voice/                 # Voice call components
│       │   │   ├── VoiceCallPanel.tsx
│       │   │   ├── CallStatusCard.tsx
│       │   │   └── PhoneInput.tsx
│       │   ├── sidebar/               # Sidebar components
│       │   │   ├── Sidebar.tsx
│       │   │   ├── CallStatusSection.tsx
│       │   │   ├── QuickActions.tsx
│       │   │   └── AboutSection.tsx
│       │   └── layout/                # Layout components
│       │       ├── Header.tsx
│       │       └── Footer.tsx
│       ├── services/                  # API service layer
│       │   ├── api.ts                 # Axios client configuration
│       │   ├── chat.ts                # Chat API service
│       │   ├── voice.ts               # Voice call API service
│       │   └── websocket.ts           # WebSocket client
│       ├── hooks/                     # Custom React hooks
│       │   ├── useChat.ts
│       │   ├── useVoiceCall.ts
│       │   ├── useSession.ts
│       │   └── useWebSocket.ts
│       ├── store/                     # State management
│       │   └── context/               # React Context providers
│       │       ├── AppContext.tsx     # App-level state
│       │       ├── ChatContext.tsx    # Chat state
│       │       ├── VoiceContext.tsx   # Voice call state
│       │       └── index.ts           # Context exports
│       ├── types/                     # TypeScript type definitions
│       │   ├── api.ts                 # API types
│       │   ├── chat.ts                # Chat types
│       │   └── voice.ts               # Voice types
│       ├── utils/                     # Utility functions
│       │   ├── constants.ts           # Application constants
│       │   ├── helpers.ts             # Helper functions
│       │   └── index.ts               # Utility exports
│       ├── lib/                       # Library utilities
│       │   └── utils.ts               # shadcn/ui utilities
│       └── styles/                    # Global styles
│           └── globals.css            # Tailwind CSS and global styles
└── venv/                              # Python virtual environment (optional)

```
