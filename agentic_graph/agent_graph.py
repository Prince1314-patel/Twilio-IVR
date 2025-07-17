from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage # Import for clarity
from db_tool.db_tools import check_appointment_availability, create_appointment_in_db, get_available_slots_for_date
import os
from dotenv import load_dotenv
from datetime import datetime
from zoneinfo import ZoneInfo # Standard library for timezones

# Load environment variables from .env file
load_dotenv()
LANGSMITH_API_KEY = os.getenv('LANGSMITH_API_KEY')
# GROQ_API_KEY = os.getenv('GROQ_API_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# --- LangGraph Store and Checkpointer for Memory ---
# In production, consider using a persistent store (e.g., RedisStore, SQLliteSaver)
# InMemorySaver and InMemoryStore are good for development/testing
store = InMemoryStore()
checkpointer = InMemorySaver()

# --- LLM Model ---
# Initialize the ChatGroq model once
# model = ChatGroq(
#     temperature=0.7,
#     model_name="meta-llama/llama-4-maverick-17b-128e-instruct",
#     groq_api_key=GROQ_API_KEY
# )

model = ChatOpenAI(
    temperature=0.7,
    model_name="gpt-4.1-nano",
    openai_api_key=OPENAI_API_KEY
)

# --- Register Tools ---
# Define your tools once
tools = [
    check_appointment_availability,
    create_appointment_in_db,
    get_available_slots_for_date
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

def run_agentic_graph(messages: list, thread_id: str) -> str:
    """
    Runs the agentic graph for a given conversation session.
    The agent's system prompt is dynamically updated with the current time for each invocation.

    Args:
        messages (List[BaseMessage]): List of LangChain message objects (HumanMessage, AIMessage, etc.).
                                      This should contain the conversation history.
        thread_id (str): Unique session/call ID (e.g., Twilio CallSid).
                         Used by the checkpointer for conversation memory.

    Returns:
        str: The agent's response as text.
    """
    # Generate the dynamic system message for the current invocation
    dynamic_system_message = get_system_message()

    # Re-create the agent with the dynamic system message.
    # This is necessary because `create_react_agent` takes a static prompt string.
    # For a high-throughput production system, you might explore more advanced LangGraph patterns
    # for dynamic prompt injection if recreating the agent becomes a performance bottleneck.
    # However, for most use cases, this approach is robust and clear.
    current_agent = create_react_agent(
        model,
        tools=tools,
        prompt=dynamic_system_message, # Pass the dynamically generated system message
        checkpointer=checkpointer,
        store=store
    )

    # Configuration for the agent's state/memory
    config = {"configurable": {"thread_id": thread_id}}

    try:
        # Invoke the agent with the current conversation messages
        result = current_agent.invoke({"messages": messages}, config)

        # The agent returns a dict with a 'messages' key (list of message objects)
        # The last message in this list is typically the agent's final response
        if result and "messages" in result and result["messages"]:
            # Ensure the last message is a string type (e.g., HumanMessage, AIMessage)
            # and extract its content.
            last_message = result["messages"][-1]
            if hasattr(last_message, 'content'):
                return last_message.content
            else:
                return "I'm sorry, the agent returned an unexpected message format."
        return "I'm sorry, I couldn't process your request right now (no messages in result)."
    except Exception as e:
        # Basic error handling for the agent invocation itself
        print(f"Error running agentic graph: {e}") # You might want to log this more robustly
        return "An unexpected error occurred while processing your request. Please try again later."

