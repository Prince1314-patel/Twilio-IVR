from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore
from langchain_groq import ChatGroq
from db_tool.db_tools import check_appointment_availability, create_appointment_in_db, get_available_slots_for_date
import os
from dotenv import load_dotenv
from datetime import datetime
import pytz

india = pytz.timezone('Asia/Kolkata')
india_time = datetime.now(india)
print(india_time)

# Load environment variables
load_dotenv()
LANGSMITH_API_KEY = os.getenv('LANGSMITH_API_KEY')
GROQ_API_KEY = os.getenv('GROQ_API_KEY')

# --- LangGraph Store and Checkpointer for Memory ---
# In production, use a persistent store (e.g., RedisStore)
store = InMemoryStore()
checkpointer = InMemorySaver()

# --- LLM Model ---
chat_groq = ChatGroq(
    temperature=0.7,
    model_name="llama3-70b-8192",
    groq_api_key=GROQ_API_KEY
)

# --- System Prompt for the Agent ---
SYSTEM_MESSAGE = """
You are a helpful, friendly AI assistant for appointment scheduling.

This the current date and time in India: {india_time}, whenever user initiates booking request consider this date and time as current date andtime.

STRICT RULES FOR FACTUAL INFORMATION:
- For ANY information about appointments, availability, booking, or time slots, you MUST ALWAYS use the provided tools. NEVER guess, invent, or assume any appointment-related data.
- If the user asks about available slots, appointment status, or requests a booking, you must call the relevant tool and use its output in your reply.
- Do NOT answer any factual or database-related question from your own knowledge or assumptions. Only use the tool outputs.
- If a tool returns an error or no data, politely inform the user and suggest next steps, but do not make up information.
- Always speak in a warm, conversational tone.
- If the user asks to book an appointment, collect their name, email, appointment type, date, and time.
- If the user asks for available slots, provide them using the tool.
- Remember the conversation context for each call session.

DATA FORMATTING INSTRUCTIONS:
- When the user provides information (such as date, time, email, name, or appointment type), always convert it to the correct format required by the system before using any tool:
    - Dates: YYYY-MM-DD (e.g., 2025-06-05)
    - Times: HH:MM:SS in 24-hour format (e.g., 14:30:00)
    - Emails: Standard email format (e.g., user@example.com)
    - Names: Only letters and spaces
    - Appointment type: telephonic or virtual (use lowercase)
- If the user provides information in a different or natural language format, you must reformat it to match the above before passing it to any tool.
"""

# --- Register Tools ---
tools = [
    check_appointment_availability,
    create_appointment_in_db,
    get_available_slots_for_date
]

# --- Create the React Agent ---
agent = create_react_agent(
    chat_groq,
    tools=tools,
    prompt=SYSTEM_MESSAGE,
    checkpointer=checkpointer,
    store=store
)

def run_agentic_graph(messages, thread_id):
    """
    Run the agentic graph for a given conversation session.

    Args:
        messages (List[BaseMessage]): List of LangChain message objects (HumanMessage, AIMessage, etc.).
        thread_id (str): Unique session/call ID (e.g., Twilio CallSid).

    Returns:
        str: The agent's response as text.
    """
    config = {"configurable": {"thread_id": thread_id}}
    result = agent.invoke({"messages": messages}, config)
    # The agent returns a dict with a 'messages' key (list of message objects)
    # The last message is the agent's reply
    if result and "messages" in result and result["messages"]:
        return result["messages"][-1].content
    return "I'm sorry, I couldn't process your request right now."
