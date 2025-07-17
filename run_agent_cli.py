"""
run_agent_cli.py

Standalone CLI runner for the LangGraph agent.
Allows interactive testing and debugging of the appointment scheduling agent without Twilio.
Logs all interactions for debugging and verification.
"""

from agentic_graph.agent_graph import run_agentic_graph
from langchain_core.messages import HumanMessage, AIMessage
import uuid
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def main():
    """
    Run the CLI loop for interacting with the LangGraph agent.

    Accepts user input, maintains conversation history, and logs all interactions.
    Optionally accepts a custom thread/session ID as a command-line argument.

    Args:
        None. (Uses sys.argv for optional thread ID.)

    Returns:
        None
    """
    logger.info("Starting LangGraph Agent CLI Runner.")
    if len(sys.argv) > 1:
        thread_id = sys.argv[1]
        logger.info(f"Using custom session thread_id from argument: {thread_id}")
    else:
        thread_id = str(uuid.uuid4())
        logger.info(f"Generated new session thread_id: {thread_id}")
    messages = []
    print("\nType your message (type 'exit' or 'quit' to end):\n")
    while True:
        try:
            user_input = input("You: ").strip()
            if user_input.lower() in ("exit", "quit"):
                logger.info("User exited the session.")
                print("Goodbye!")
                break
            logger.debug(f"User input: {user_input}")
            messages.append(HumanMessage(content=user_input))
            logger.debug("Message history: %s", [f"{type(m).__name__}: {m.content}" for m in messages])
            response = run_agentic_graph(messages, thread_id)
            logger.debug(f"Agent response: {response}")
            print(f"Agent: {response}\n")
            messages.append(AIMessage(content=response))
        except Exception as e:
            logger.exception(f"Error during agent interaction: {e}")
            print(f"[Error] {e}\n")

if __name__ == "__main__":
    main() 