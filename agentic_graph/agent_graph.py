from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from langgraph.store.memory import InMemoryStore
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage # Import for clarity
from db_tool.db_tools import check_appointment_availability, create_appointment_in_db, get_available_slots_for_date
import os
from dotenv import load_dotenv
from datetime import datetime
from zoneinfo import ZoneInfo # Standard library for timezones
from langchain_core.messages import trim_messages

# Load environment variables from .env file
load_dotenv()
LANGSMITH_API_KEY = os.getenv('LANGSMITH_API_KEY')
GROQ_API_KEY = os.getenv('GROQ_API_KEY')

# --- LangGraph Store and Checkpointer for Memory ---
# In production, consider using a persistent store (e.g., RedisStore, SQLliteSaver)
# InMemorySaver and InMemoryStore are good for development/testing
# store = InMemoryStore()
# checkpointer = InMemorySaver()

# --- Conversation Memory (Official LangGraph Pattern) ---
memory = MemorySaver()

# --- Summary Store (in-memory, can be replaced with persistent storage) ---
summaries_by_thread = {}

# --- Summarization Logic ---
def summarize_old_messages(thread_id, all_messages, llm, max_recent=10):
    """
    Summarize old messages for a thread, keep the most recent N messages.
    Args:
        thread_id (str): Unique session/call ID.
        all_messages (list): All messages for the thread.
        llm: The LLM to use for summarization.
        max_recent (int): Number of recent messages to keep in detail.
    Returns:
        summary (str): The running summary.
        recent_messages (list): The most recent messages.
    """
    if len(all_messages) <= max_recent:
        # Not enough messages to summarize
        return summaries_by_thread.get(thread_id, ""), all_messages
    # Split into old and recent
    old_messages = all_messages[:-max_recent]
    recent_messages = all_messages[-max_recent:]
    # Combine old messages and previous summary
    prev_summary = summaries_by_thread.get(thread_id, "")
    to_summarize = prev_summary + "\n" + "\n".join([m.content for m in old_messages if hasattr(m, 'content')])
    # Summarize using the LLM
    summary_prompt = f"Summarize the following conversation history for future context.\n\n{to_summarize}"
    summary_result = llm.invoke([SystemMessage(content=summary_prompt)])
    new_summary = summary_result.content if hasattr(summary_result, 'content') else str(summary_result)
    # Store the new summary
    summaries_by_thread[thread_id] = new_summary
    return new_summary, recent_messages

# --- LLM Model ---
# Initialize the ChatGroq model once
chat_groq = ChatGroq(
    temperature=0.7,
    model_name="meta-llama/llama-4-maverick-17b-128e-instruct",
    groq_api_key=GROQ_API_KEY
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

STRICT RULES FOR FACTUAL INFORMATION:
- For ANY information about appointments, availability, booking, or time slots, you MUST ALWAYS use the provided tools. NEVER guess, invent, or assume any appointment-related data.
- If the user asks about available slots, appointment status, or requests a booking, you must call the relevant tool and use its output in your reply.
- Do NOT answer any factual or database-related question from your own knowledge or assumptions. Only use the tool outputs.
- If a tool returns an error or no data, politely inform the user and suggest next steps, but do not make up information.
- Always speak in a warm, conversational tone.

BOOKING FLOW INSTRUCTIONS (IMPORTANT!):
- If the user asks to book an appointment, collect their name, email, appointment type, date, and time.
- After collecting these details, PROMPT THE USER to briefly describe their problem or symptoms for the doctor. Wait for their response.
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

# --- Prompt Function ---
def prompt(state):
    """
    Compose the prompt for the LLM: summary + recent messages.
    """
    # Get thread_id from state/config
    thread_id = state.get("configurable", {}).get("thread_id", "default")
    all_messages = state["messages"]
    summary, recent_messages = summarize_old_messages(thread_id, all_messages, chat_groq, max_recent=10)
    prompt_msgs = []
    if summary:
        prompt_msgs.append(SystemMessage(content=summary))
    prompt_msgs.extend(recent_messages)
    return prompt_msgs

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
    current_agent = create_react_agent(
        chat_groq,
        tools=tools,
        prompt=prompt,           # Use the summarizing prompt
        checkpointer=memory,     # Use MemorySaver for persistence
    )

    # Configuration for the agent's state/memory
    config = {"configurable": {"thread_id": thread_id}}

    try:
        # Invoke the agent with the current conversation messages
        result = current_agent.invoke({"messages": messages, "configurable": {"thread_id": thread_id}}, config)

        # The agent returns a dict with a 'messages' key (list of message objects)
        # The last message in this list is typically the agent's final response
        if result and "messages" in result and result["messages"]:
            last_message = result["messages"][-1]
            if hasattr(last_message, 'content'):
                return last_message.content
            else:
                return "I'm sorry, the agent returned an unexpected message format."
        return "I'm sorry, I couldn't process your request right now (no messages in result)."
    except Exception as e:
        print(f"Error running agentic graph: {e}")
        return "An unexpected error occurred while processing your request. Please try again later."

