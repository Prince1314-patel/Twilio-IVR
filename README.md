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

### Technologies Used

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

3.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Environment Variables**:
    Create a `.env` file in the root directory of the project and add the following:
    ```
    TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
    TWILIO_AUTH_TOKEN=your_twilio_auth_token
    TWILIO_PHONE_NUMBER=+1234567890  # Your Twilio phone number
    GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
    OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxx # Required by LangGraph agent
    ```
    Replace the placeholder values with your actual Twilio, Groq, and OpenAI API credentials.

5.  **Database Setup**:
    The `db_tool` module uses an in-memory SQLite database for demonstration purposes. For persistent storage, you would need to modify `db_tool/db_manager.py` to connect to a more robust database (e.g., PostgreSQL, MySQL).

6.  **Ngrok (or similar tunneling service)**:
    Twilio needs a publicly accessible URL to send incoming call webhooks. You can use `ngrok` for this.
    Download `ngrok.exe` (or the appropriate version for your OS) and place it in the project root.
    Run ngrok to expose your local server:
    ```bash
    .
grok.exe http 8000
    ```
    Copy the `https` forwarding URL provided by ngrok (e.g., `https://your-ngrok-url.ngrok-free.app`). You will use this URL in your Twilio webhook configuration.

### Usage

1.  **Start the FastAPI server**:
    ```bash
    python answer_phone.py
    ```
    The server will run on `http://0.0.0.0:8000`.

2.  **Configure Twilio Webhook**:
    *   Go to your Twilio Phone Numbers dashboard.
    *   Select the Twilio phone number you want to use for this application.
    *   Under the "Voice & Fax" section, configure the "A CALL COMES IN" webhook to "Webhook" and paste your ngrok `https` forwarding URL followed by `/incoming-call`.
        Example: `https://your-ngrok-url.ngrok-free.app/incoming-call`
    *   Set the HTTP method to `POST`.

3.  **Make an Outbound Call (Optional)**:
    You can initiate an outbound call using the `make_call.py` script.
    **Before running `make_call.py`**:
    *   Ensure the `url` in `make_call.py` is updated with your current ngrok `https` forwarding URL.
    *   Update the `to` and `from_` phone numbers in `make_call.py` to your desired recipient and your Twilio phone number, respectively.
    ```python
    # make_call.py
    call = client.calls.create(
        to="+918200467191",  # Replace with the recipient's phone number
        from_="+19122145317", # Replace with your Twilio phone number
        url="https://d328ae9a1a6b.ngrok-free.app/incoming-call" # Replace with your ngrok URL
    )
    ```
    Then run:
    ```bash
    python make_call.py
    ```

4.  **Interact with the AI**:
    *   Call your Twilio phone number.
    *   The AI assistant will greet you and prompt you to state your request regarding appointments.
    *   Speak naturally to schedule, reschedule, or cancel appointments.

### Project Structure

```
.
├── .gitignore
├── answer_phone.py             # FastAPI application, handles Twilio webhooks and AI conversation
├── make_call.py                # Script to initiate outbound calls via Twilio
├── ngrok.exe                   # Ngrok executable for local tunneling
├── Readme.md                   # Project documentation
├── requirements.txt            # Python dependencies
├── run_agent_cli.py            # (Optional) CLI for agent interaction (if implemented)
├── __pycache__/                # Python cache files
├── .git/                       # Git version control
├── agentic_graph/
│   ├── __init__.py
│   ├── agent_graph.py          # Defines the LangGraph agent and its tools
│   ├── prompts.py              # Prompts used by the agent
│   └── __pycache__/
├── db_tool/
│   ├── db_manager.py           # Manages database operations (SQLite in-memory by default)
│   ├── db_tools.py             # LangChain-compatible tools for database interaction
│   └── __pycache__/
└── venv/                       # Python virtual environment

```
