import os
from dotenv import load_dotenv
from datetime import datetime
from zoneinfo import ZoneInfo

from langgraph.prebuilt import create_react_agent
from langgraph_supervisor import create_supervisor
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore
from langchain_openai import ChatOpenAI

from db_tool.db_tools import (
    create_appointment_in_db,
    check_appointment_availability,
    get_available_slots_for_date,
    update_appointment_in_db,
    cancel_appointment_in_db,
)

# Load environment variables from .env file
load_dotenv()
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# Initialize the OpenAI model
model = ChatOpenAI(
    temperature=0.7,
    model_name="gpt-4o",
    openai_api_key=OPENAI_API_KEY
)

# --- Register Tools ---
# Define your tools once
tools = [
    check_appointment_availability,
    create_appointment_in_db,
    get_available_slots_for_date,
    update_appointment_in_db,
    cancel_appointment_in_db
]

# --- Dynamic System Prompt Function ---
def get_system_message():
    """
    Generates the system prompt for the agent, including the current date and time
    in Asia/Kolkata timezone. This ensures the agent's time perception is always up-to-date.
    """
    current_kolkata_time = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M:%S")

    return f"""
You are a helpful, friendly AI assistant for appointment scheduling.

This is the current date and time in India: {current_kolkata_time}. Whenever the user initiates a booking request, consider this date and time as the current date and time for all comparisons and decisions.

OUTPUT FORMAT:
- DO NOT USE MARKDOWN FORMAT. ONLY USE PLAIN TEXT. As your response will be used to generate voice messages, it should be in a format that is easy to understand by a text to speech engine.
- When providing response to the user, if response is time then use the format "HH:MM:SS" in 24-hour format.

STRICT RULES FOR FACTUAL INFORMATION:
- For ANY information about appointments, availability, booking, or time slots, you MUST ALWAYS use the provided tools. NEVER guess, invent, or assume any appointment-related data.
- If the user asks about available slots, appointment status, or requests a booking, you must call the relevant tool and use its output in your reply.
- Do NOT answer any factual or database-related question from your own knowledge or assumptions. Only use the tool outputs.
- If a tool returns an error or no data, politely inform the user and suggest next steps, but do not make up information.
- Always speak in a warm, conversational tone.

BOOKING FLOW INSTRUCTIONS (IMPORTANT!):
- If the user asks to book an appointment, collect their name, email, appointment type, date, and time.
- After collecting these details, PROMPT THE USER to briefly describe their problem or symptoms for the doctor. Wait for their response. If they don't provide any symptoms, just move forward with the booking.
- After you have all booking details and the symptoms/problem, REPEAT BACK a summary of all details (name, email, appointment type, date, time, and symptoms) and ASK THE USER TO CONFIRM (e.g., "Do you want to confirm this booking?").
- ONLY IF THE USER CONFIRMS, call the tool to create the appointment in the database (including the symptoms/problem in the 'notes' field).
- After booking, provide a final summary to the user, including the appointment details and the symptoms they provided.
- If the user does NOT confirm, do NOT save the appointment and politely ask if they want to change anything or cancel.

DATA FORMATTING INSTRUCTIONS:
- When the user provides information (such as date, time, email, name, or appointment type), always convert it to the correct format required by the system before using any tool:
    - Dates: YYYY-MM-DD (e.g., 2025-06-05)
    - Times: HH:MM:SS in 24-hour format (e.g., 14:30:00)
    - Emails: Standard email format (e.g., user@example.com)
    - Names: Only letters and spaces
    - Appointment type: telephonic or virtual (use lowercase)
- If the user provides information in a different or natural language format, you must reformat it to match the above before passing it to any tool.
"""

# --- Define Specialized CRUD Agents ---

create_agent = create_react_agent(
    model=model,
    tools=[create_appointment_in_db],
    name="create_agent",
    prompt="You are an expert at creating new appointments. Only handle creation requests."
)

read_agent = create_react_agent(
    model=model,
    tools=[check_appointment_availability, get_available_slots_for_date],
    name="read_agent",
    prompt="You are an expert at reading appointment data. Only handle queries about availability or slots."
)

update_agent = create_react_agent(
    model=model,
    tools=[update_appointment_in_db],
    name="update_agent",
    prompt="You are an expert at updating appointments. Only handle update requests."
)

delete_agent = create_react_agent(
    model=model,
    tools=[cancel_appointment_in_db],
    name="delete_agent",
    prompt="You are an expert at cancelling appointments. Only handle cancellation requests."
)

# --- Create Supervisor Agent ---

supervisor_prompt = (
    "You are a supervisor agent managing four specialized agents: create_agent, read_agent, update_agent, and delete_agent. "
    "Route user requests to the correct agent based on intent: "
    "creation (create_agent), reading/querying (read_agent), updating (update_agent), or deleting/cancelling (delete_agent). "
    "If the request is ambiguous, ask the user for clarification."
)

supervisor_workflow = create_supervisor(
    [create_agent, read_agent, update_agent, delete_agent],
    model=model,
    prompt=supervisor_prompt,
)

# --- State Management and Workflow Compilation ---

checkpointer = InMemorySaver()
store = InMemoryStore()

app = supervisor_workflow.compile(
    checkpointer=checkpointer,
    store=store
)


# --- Entry Point Function ---
def run_agentic_graph(messages: list, thread_id: str) -> str:
    """
    Runs the supervisor agentic graph for a given conversation session.
    Args:
        messages (list): List of message dicts (role/content) or LangChain message objects.
        thread_id (str): Unique session/call ID (used for memory).
    Returns:
        str: The agent's response as text.
    """
    # Prepend system message with current date/time/zone
    now = datetime.now(ZoneInfo("Asia/Kolkata"))
    system_message = {
        "role": "system",
        "content": f"Current date and time in Asia/Kolkata: {now.strftime('%Y-%m-%d %H:%M:%S')}"
    }
    messages_with_time = [system_message] + messages
    config = {"configurable": {"thread_id": thread_id}}
    try:
        result = app.invoke({"messages": messages_with_time}, config)
        if result and "messages" in result and result["messages"]:
            last_message = result["messages"][-1]
            if hasattr(last_message, 'content'):
                return last_message.content
            elif isinstance(last_message, dict) and 'content' in last_message:
                return last_message['content']
            else:
                return "I'm sorry, the agent returned an unexpected message format."
        return "I'm sorry, I couldn't process your request right now (no messages in result)."
    except Exception as e:
        print(f"Error running agentic graph: {e}")
        return "An unexpected error occurred while processing your request. Please try again later."

