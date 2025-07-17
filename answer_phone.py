import os
import json
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from twilio.twiml.voice_response import VoiceResponse, Gather
from dotenv import load_dotenv
import uvicorn
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from agentic_graph.agent_graph import run_agentic_graph

# --- Configuration ---
load_dotenv()
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
if not GROQ_API_KEY:
    raise ValueError('Missing the GROQ API key. Please set it in the .env file.')

# In-memory chat history per call session
# Note: For production, consider using a more persistent store like Redis.
call_sessions = {}

# System message for the AI wellness coach
SYSTEM_MESSAGE = """
You are an AI assistant whose sole purpose is to help users book appointments over the phone.

Your responsibilities:
- Assist users with scheduling, rescheduling, or canceling appointments.
- Provide information about available time slots and appointment status.
- Collect necessary details for bookings (name, email, appointment type, date, and time).
- Speak warmly, clearly, and keep responses short and conversational.

STRICT FACTUAL RULES:
- For any information about appointments, bookings, or time slots, NEVER guess or make up data. Only refer to information provided by the system or tools.
- If you do not know the answer, politely say you are unable to provide that information right now.

IMPORTANT:
- If a user asks about anything unrelated to appointments, politely explain that you can only assist with booking, rescheduling, or canceling appointments.
- Do not engage in general conversation or provide information outside of appointment scheduling.
"""

# --- Initialize FastAPI and LLM ---
app = FastAPI()

# Initialize Langchain ChatGroq for the LLM
try:
    chat_groq = ChatGroq(
        temperature=0.7,
        # Using a model known for strong conversational abilities.
        model_name="meta-llama/llama-4-maverick-17b-128e-instruct",
        groq_api_key=GROQ_API_KEY
    )
    print("Langchain ChatGroq LLM initialized successfully.")
except Exception as e:
    print(f"Error initializing Langchain ChatGroq LLM: {e}")
    chat_groq = None

# --- Core Application Logic ---

@app.api_route("/", methods=["GET", "POST"])
async def index_page():
    """
    A simple endpoint to confirm the server is running.

    Returns:
        HTMLResponse: HTML response indicating server status.
    """
    return HTMLResponse("<h1>AI Voice IVR Server is running</h1>")

@app.api_route("/incoming-call", methods=["POST"])
async def handle_incoming_call():
    """
    Handles a new incoming call from Twilio.

    Greets the user and starts the conversation loop with <Gather>.

    Returns:
        HTMLResponse: TwiML XML response for Twilio.
    """
    response = VoiceResponse()
    
    # Start listening for the user's response using <Gather>.
    gather = response.gather(
        input='speech',
        action='/handle-speech',
        speech_timeout='auto',
        speech_model='experimental_conversational',
        language='en-US'
    )
    
    # Nest the greeting inside the <Gather> verb. This is the prompt.
    gather.say(
        "Hello! Welcome to your personal AI booking assistant!",
        voice='Polly.Salli'
    )
    
    # If the <Gather> finishes without any speech, Twilio will proceed to the next verb.
    # This provides a graceful exit instead of an abrupt hang-up.
    response.say("We didn't receive a response. Thank you for calling. Goodbye.", voice='Polly.Salli')
    response.hangup()
    
    return HTMLResponse(content=str(response), media_type="application/xml")

@app.api_route("/handle-speech", methods=["POST"])
async def handle_speech(request: Request):
    """
    Processes speech input from the user (via <Gather>) and responds.
    This is the main conversational loop.

    Args:
        request (Request): FastAPI request object containing Twilio form data.

    Returns:
        HTMLResponse: TwiML XML response for Twilio.
    """
    # Parse the form data from Twilio's request
    form = await request.form()
    call_sid = form.get("CallSid")
    user_speech = form.get("SpeechResult", "").strip()
    
    response = VoiceResponse()

    if not call_sid:
        response.say("An application error occurred. Please call back later.", voice='Polly.Salli')
        response.hangup()
        return HTMLResponse(content=str(response), media_type="application/xml")

    # Initialize session if it's a new call
    if call_sid not in call_sessions:
        call_sessions[call_sid] = {'history': []}

    # Start the next <Gather> to continue the conversation loop.
    gather = response.gather(
        input='speech',
        action='/handle-speech',
        timeout=15,
        speech_timeout='auto',
        speech_model='experimental_conversational',
        language='en-US'
    )

    # If the user said something, process it and say the response.
    if user_speech:
        print(f"[{call_sid}] User said: {user_speech}")
        from langchain_core.messages import HumanMessage, AIMessage
        call_sessions[call_sid]['history'].append(HumanMessage(content=user_speech))

        # Use the agentic graph for response generation
        llm_response_text = run_agentic_graph(
            [*call_sessions[call_sid]['history']],
            thread_id=call_sid
        )
        print(f"[{call_sid}] AI said: {llm_response_text}")

        call_sessions[call_sid]['history'].append(AIMessage(content=llm_response_text))
        # Nest the AI's response inside the new <Gather> as its prompt.
        gather.say(llm_response_text, voice='Polly.Salli')
    else:
        # If no speech was detected from the previous <Gather>, prompt the user again.
        print(f"[{call_sid}] No speech detected.")
        # Nest the re-prompt inside the new <Gather>.
        gather.say("I'm sorry, I didn't hear anything. Could you please say that again?", voice='Polly.Salli')

    # Add a fallback in case this new <Gather> also times out.
    response.say("It seems we've been disconnected. Thank you for calling. Goodbye.", voice='Polly.Salli')
    response.hangup()

    return HTMLResponse(content=str(response), media_type="application/xml")


async def generate_llm_response(call_id: str) -> str:
    """
    Generates a response using the Groq LLM based on conversation history.

    Args:
        call_id (str): The call/session ID for which to generate a response.

    Returns:
        str: The generated LLM response text.
    """
    if not chat_groq:
        return "I'm sorry, my thinking cap isn't working right now. Could you please try again?"
        
    try:
        # Prepare messages with system prompt and history
        messages = [SystemMessage(content=SYSTEM_MESSAGE)]
        
        # Add the conversation history for context
        if call_id in call_sessions:
            messages.extend(call_sessions[call_id]['history'])
        
        # Generate response
        response = await chat_groq.ainvoke(messages)
        return response.content
        
    except Exception as e:
        print(f"Error generating LLM response for call {call_id}: {e}")
        return "I'm sorry, I'm having a little trouble understanding. Could you please say that again?"

# --- Run the Application ---
if __name__ == "__main__":
    # Use this for local development. For production, use a Gunicorn or other ASGI server.
    uvicorn.run(app, host="0.0.0.0", port=8000)
