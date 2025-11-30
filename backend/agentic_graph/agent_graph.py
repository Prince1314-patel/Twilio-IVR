import os
from dotenv import load_dotenv
from datetime import datetime
from zoneinfo import ZoneInfo
import re

from langgraph.prebuilt import create_react_agent
from langgraph_supervisor import create_supervisor
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore
from datetime import datetime
import pytz
import logging

from db_tool.db_tools import (
    create_appointment_in_db,
    check_appointment_availability,
    get_available_slots_for_date,
    update_appointment_in_db,
    cancel_appointment_in_db,
)

from agentic_graph.prompts import GENERAL_AGENT_PROMPT
from langchain_core.messages import HumanMessage, AIMessage
from app.core.config import create_llm_model, settings

logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

def clean_agent_response(response: str) -> str:
    """
    Clean and sanitize agent response to remove markdown, special characters, and formatting.
    
    This function ensures the response is plain text suitable for text-to-speech engines.
    
    Args:
        response (str): Raw agent response that may contain markdown or special formatting.
        
    Returns:
        str: Clean plain text response.
    """
    if not response:
        return response
    
    # Remove markdown formatting
    # Remove bold/italic markers
    response = re.sub(r'\*\*([^*]+)\*\*', r'\1', response)  # **bold**
    response = re.sub(r'\*([^*]+)\*', r'\1', response)  # *italic*
    response = re.sub(r'__([^_]+)__', r'\1', response)  # __bold__
    response = re.sub(r'_([^_]+)_', r'\1', response)  # _italic_
    
    # Remove code blocks
    response = re.sub(r'```[\s\S]*?```', '', response)  # ```code blocks```
    response = re.sub(r'`([^`]+)`', r'\1', response)  # `inline code`
    
    # Remove markdown headers
    response = re.sub(r'^#+\s*', '', response, flags=re.MULTILINE)
    
    # Remove markdown links [text](url) -> text
    response = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', response)
    
    # Remove markdown lists markers
    response = re.sub(r'^\s*[-*+]\s+', '', response, flags=re.MULTILINE)
    response = re.sub(r'^\s*\d+\.\s+', '', response, flags=re.MULTILINE)
    
    # Remove special Unicode characters that might cause issues (zero-width spaces, etc.)
    response = re.sub(r'[\u200B-\u200D\uFEFF]', '', response)  # Zero-width spaces
    
    # Normalize whitespace - replace multiple spaces/newlines with single space
    response = re.sub(r'\s+', ' ', response)
    
    # Strip leading/trailing whitespace
    response = response.strip()
    
    return response

# In-memory conversation history for streaming sessions
# Format: {session_id: [messages]}
streaming_sessions = {}

# Initialize the LLM model based on configuration
try:
    model = create_llm_model()
    logger.info(
        f"Initialized LLM model: provider={settings.LLM_PROVIDER}, "
        f"model={settings.get_llm_model_name()}, temperature={settings.AI_TEMPERATURE}"
    )
except Exception as e:
    logger.error(f"Failed to initialize LLM model: {e}")
    raise

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
                raw_response = last_message.content
            elif isinstance(last_message, dict) and 'content' in last_message:
                raw_response = last_message['content']
            else:
                return "I'm sorry, the agent returned an unexpected message format."
            
            # Clean the response to remove markdown and special characters
            cleaned_response = clean_agent_response(str(raw_response))
            return cleaned_response
        return "I'm sorry, I couldn't process your request right now (no messages in result)."
    except Exception as e:
        print(f"Error running agentic graph: {e}")
        return "An unexpected error occurred while processing your request. Please try again later."


async def run_agentic_graph_streaming(user_text: str, session_id: str) -> str:
    """
    Run the agentic graph for streaming voice sessions.
    
    This function maintains conversation history per session (similar to chat WebSocket)
    and processes user input through the AI agent. Designed for real-time voice streaming.
    
    Args:
        user_text (str): User's transcribed speech input
        session_id (str): Unique session identifier (typically call SID)
        
    Returns:
        str: AI agent's response text in Hinglish
        
    Raises:
        Exception: If agent processing fails
    """
    import pytz
    from datetime import datetime
    
    # Initialize session history if new
    if session_id not in streaming_sessions:
        streaming_sessions[session_id] = []
    
    # Add user message to history
    user_message = HumanMessage(content=user_text)
    streaming_sessions[session_id].append(user_message)
    
    # Prepare messages with time context
    india = pytz.timezone('Asia/Kolkata')
    india_time = datetime.now(india)
    system_message = {
        "role": "system",
        "content": f"Current date and time in Asia/Kolkata: {india_time.strftime('%Y-%m-%d %H:%M:%S')}"
    }
    
    # Convert LangChain messages to dict format for agent
    messages_for_agent = [system_message]
    for msg in streaming_sessions[session_id]:
        if isinstance(msg, HumanMessage):
            messages_for_agent.append({"role": "user", "content": msg.content})
        elif isinstance(msg, AIMessage):
            messages_for_agent.append({"role": "assistant", "content": msg.content})
    
    # Run agent
    config = {"configurable": {"thread_id": session_id}}
    try:
        result = appointment_agent.invoke({"messages": messages_for_agent}, config)
        
        if result and "messages" in result and result["messages"]:
            last_message = result["messages"][-1]
            
            # Extract content
            if hasattr(last_message, 'content'):
                raw_response = last_message.content
            elif isinstance(last_message, dict) and 'content' in last_message:
                raw_response = last_message['content']
            else:
                raw_response = "Mujhe kshama karein, main aapki baat samajh nahi paya. Kripya dobara kahein."
            
            # Clean the response to remove markdown and special characters
            ai_response = clean_agent_response(str(raw_response))
            
            # Add AI response to history
            ai_message = AIMessage(content=ai_response)
            streaming_sessions[session_id].append(ai_message)
            
            return ai_response
        else:
            error_msg = "Mujhe kshama karein, main abhi aapki baat nahi samajh paya. Kripya dobara koshish karein."
            return error_msg
            
    except Exception as e:
        print(f"Error running agentic graph for streaming: {e}")
        error_msg = "Ek apratyashit truti hui. Kripya baad mein punah prayas karein."
        return error_msg

