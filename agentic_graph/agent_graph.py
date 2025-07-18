import os
from dotenv import load_dotenv
from datetime import datetime
from zoneinfo import ZoneInfo

from langgraph.prebuilt import create_react_agent
from langgraph_supervisor import create_supervisor
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore
from langchain_openai import ChatOpenAI
from datetime import datetime
import pytz

from db_tool.db_tools import (
    create_appointment_in_db,
    check_appointment_availability,
    get_available_slots_for_date,
    update_appointment_in_db,
    cancel_appointment_in_db,
)

from agentic_graph.prompts import GENERAL_AGENT_PROMPT

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

# --- Define a Single Comprehensive ReAct Agent ---

appointment_agent = create_react_agent(
    model=model,
    tools=[
        create_appointment_in_db,
        check_appointment_availability,
        get_available_slots_for_date,
        update_appointment_in_db,
        cancel_appointment_in_db,
    ],
    name="appointment_agent",
    prompt=GENERAL_AGENT_PROMPT
)

# --- Entry Point Function ---
def run_agentic_graph(messages: list, thread_id: str) -> str:
    """
    Runs the appointment agent for a given conversation session.
    Args:
        messages (list): List of message dicts (role/content) or LangChain message objects.
        thread_id (str): Unique session/call ID (used for memory).
    Returns:
        str: The agent's response as text.
    """
    import pytz
    from datetime import datetime
    india = pytz.timezone('Asia/Kolkata')
    india_time = datetime.now(india)
    system_message = {
        "role": "system",
        "content": f"Current date and time in Asia/Kolkata: {india_time.strftime('%Y-%m-%d %H:%M:%S')}"
    }
    messages_with_time = [system_message] + messages
    config = {"configurable": {"thread_id": thread_id}}
    try:
        result = appointment_agent.invoke({"messages": messages_with_time}, config)
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

