
import sys
import os
import datetime
from zoneinfo import ZoneInfo
import logging
from unittest.mock import MagicMock

# Add backend directory to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.messages.tool import ToolCall

from app.ai.graph.nodes.appointment_agent_node import appointment_agent_node
from app.ai.graph.state import AgentState

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_agent_slot_capture():
    """
    Test that appointment_agent_node correctly captures slots from tool calls.
    """
    logger.info("--- Starting Agent Slot Capture Test ---")
    
    # Mock date
    today = datetime.datetime.now(ZoneInfo("Asia/Kolkata")).date()
    next_date = today + datetime.timedelta(days=2)
    next_date_str = next_date.strftime("%Y-%m-%d")
    
    # 1. Setup State: Rescheduling flow, asking for ID
    state = {
        "messages": [HumanMessage(content="Hello, I want to reschedule my appointment to next week")],
        "current_intent": "reschedule",
        "tone_instruction": "",
        "intent": "rescheduling",
        "intent_confidence": 0.9,
        "active_intent": "rescheduling",
        "intent_locked": True,
        "flow_step": "rescheduling__appointment_id", # Current step: Need ID
        "flow_completed": False,
        "collected_slots": {},
        "caller_mobile_number": "9998887776",
        "user_id": 1, 
        "user_profile": {"name": "Test User"}
    }
    
    # We need to Mock the agent invoke to return a Tool Call
    # This simulates the LLM deciding to call 'update_appointment' or 'get_upcoming'
    # tailored to test the specific capture logic.
    
    # Scenario: Agent calls 'update_appointment_in_db' with an ID it found
    # This happens when the agent is smart enough to find the ID from context/tools
    
    class MockAgent:
        def invoke(self, inputs):
            # Agent decides to call update_appointment with ID 123
            msg = AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "update_appointment_in_db",
                        "args": {
                            "appointment_id": 123,
                            "date": next_date_str, 
                            "time": "10:00:00"
                        },
                        "id": "call_123"
                    }
                ]
            )
            return {"messages": inputs["messages"] + [msg]}

    # Monkeypatch the create_react_agent (or _create_intent_specific_agent) 
    # logic is hard because it's inside the node.
    # EASIER: We can just unit test the specific logic if we extracted it, 
    # but since it's inside the node, we have to mock the factory.
    
    from unittest.mock import patch
    
    # Patch _create_intent_specific_agent to return our MockAgent
    with patch("app.ai.graph.nodes.appointment_agent_node._create_intent_specific_agent", return_value=MockAgent()):
        
        # Run the node
        result = appointment_agent_node(state)
        
        # Verify results
        collected = result["collected_slots"]
        logger.info(f"Collected Slots: {collected}")
        
        # Check if appointment_id was captured from the tool call
        if collected.get("appointment_id") == 123:
            logger.info("✅ SUCCESS: Captured appointment_id=123 from tool call")
        else:
            logger.error(f"❌ FAILED: precise appointment_id not captured. Got: {collected.get('appointment_id')}")
            
        # Check if new_date was captured (mapped from 'date' arg)
        if collected.get("new_date") == next_date_str:
            logger.info(f"✅ SUCCESS: Captured new_date={next_date_str} from tool arg 'date'")
        else:
            logger.error(f"❌ FAILED: new_date not captured. Got: {collected.get('new_date')}")

        # Check Flow Step Advancement
        # If we have appointment_id, we should have moved past 'rescheduling__appointment_id'
        # Actually, since we also got new_date/new_time, we might have jumped ahead or at least moved once.
        # But 'should_advance_step' checks one step at a time.
        # 'rescheduling__appointment_id' requires 'appointment_id'. We got it. So it should advance.
        
        flow_step = result["flow_step"]
        logger.info(f"New Flow Step: {flow_step}")
        
        if flow_step != "rescheduling__appointment_id":
             logger.info("✅ SUCCESS: Flow step advanced")
        else:
             logger.error("❌ FAILED: Flow step did not advance")
             
        assert collected.get("appointment_id") == 123
        assert collected.get("new_date") == next_date_str


if __name__ == "__main__":
    test_agent_slot_capture()
