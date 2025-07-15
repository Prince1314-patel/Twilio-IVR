import os
import json
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from twilio.twiml.voice_response import VoiceResponse, Gather
from dotenv import load_dotenv
import uvicorn
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

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
You are a kind, caring AI assistant speaking directly to a user over the phone.
Your goal is to provide responses in natural, spoken language.

Tone and Style:
- Speak warmly and with empathy.
- Keep replies short and conversational (2-3 short sentences is ideal).
- Always sound like you're talking, not writing.

Strict Voice Output Rules:
- Use plain text only. Do not include any formatting like asterisks or markdown.
- Never describe your actions (e.g., "Here’s what I think..."). Just say the response.
- Do not repeat user errors. Respond kindly and move the conversation forward.
- Your response will be converted directly to speech.

Important: Your primary role is emotional support. Reinforce positivity and ask gentle, open-ended follow-up questions to keep the conversation going.
"""

# --- Initialize FastAPI and LLM ---
app = FastAPI()

# Initialize Langchain ChatGroq for the LLM
try:
    chat_groq = ChatGroq(
        temperature=0.7,
        # Using a model known for strong conversational abilities.
        model_name="llama3-70b-8192",
        groq_api_key=GROQ_API_KEY
    )
    print("Langchain ChatGroq LLM initialized successfully.")
except Exception as e:
    print(f"Error initializing Langchain ChatGroq LLM: {e}")
    chat_groq = None

# --- Core Application Logic ---

@app.api_route("/", methods=["GET", "POST"])
async def index_page():
    """A simple endpoint to confirm the server is running."""
    return HTMLResponse("<h1>AI Voice IVR Server is running</h1>")

@app.api_route("/incoming-call", methods=["POST"])
async def handle_incoming_call():
    """
    Handles a new incoming call from Twilio.
    Greets the user and starts the conversation loop with <Gather>.
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
        "Hello! Welcome to your personal AI wellness coach. How are you feeling today?",
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
        speech_timeout='auto',
        speech_model='experimental_conversational',
        language='en-US'
    )

    # If the user said something, process it and say the response.
    if user_speech:
        print(f"[{call_sid}] User said: {user_speech}")
        
        call_sessions[call_sid]['history'].append(HumanMessage(content=user_speech))
        
        llm_response_text = await generate_llm_response(call_sid)
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
