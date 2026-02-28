
import sys
import os
import pytest
from unittest.mock import MagicMock, patch
from langchain_core.messages import HumanMessage, AIMessage

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from app.ai.graph.nodes.user_context_node import user_context_loading_node
from app.ai.graph.nodes.name_enrichment_node import name_enrichment_node

# --- User Context Node Tests ---

@patch("app.ai.graph.nodes.user_context_node.DatabaseManager")
def test_user_context_new_user(mock_db_cls):
    """Test context loading for a new user (needs enrichment)."""
    mock_db = mock_db_cls.return_value
    mock_db.get_user_by_mobile_number.return_value = None
    mock_db.create_user_with_phone.return_value = {"success": True, "user_id": 100}

    state = {"caller_mobile_number": "+1234567890"}
    result = user_context_loading_node(state)
    
    assert result["user_id"] == 100
    assert result["needs_name_enrichment"] is True
    assert result["user_profile"]["name"] is None

@patch("app.ai.graph.nodes.user_context_node.DatabaseManager")
def test_user_context_existing_nameless_user(mock_db_cls):
    """Test context loading for existing user without name."""
    mock_db = mock_db_cls.return_value
    mock_db.get_user_by_mobile_number.return_value = {
        "user_id": 101, "name": None, "mobile_number": "+1234567890"
    }
    
    state = {"caller_mobile_number": "+1234567890"}
    result = user_context_loading_node(state)
    
    assert result["user_id"] == 101
    assert result["needs_name_enrichment"] is True

@patch("app.ai.graph.nodes.user_context_node.DatabaseManager")
def test_user_context_existing_named_user(mock_db_cls):
    """Test context loading for existing user with name."""
    mock_db = mock_db_cls.return_value
    mock_db.get_user_by_mobile_number.return_value = {
        "user_id": 102, "name": "Jane Doe", "mobile_number": "+1234567890"
    }
    mock_db.get_user_appointment_history.return_value = []
    
    state = {"caller_mobile_number": "+1234567890"}
    result = user_context_loading_node(state)
    
    assert result["user_id"] == 102
    assert result["needs_name_enrichment"] is False


# --- Name Enrichment Node Tests ---

def test_name_enrichment_skip():
    """Test skipping if not needed."""
    state = {"needs_name_enrichment": False}
    result = name_enrichment_node(state)
    assert result == {}

def test_name_enrichment_ask_first_time():
    """Test asking for name if needed and not yet asked."""
    state = {
        "needs_name_enrichment": True,
        "user_id": 100,
        "messages": [HumanMessage(content="Hello")]
    }
    result = name_enrichment_node(state)
    
    assert "messages" in result
    assert len(result["messages"]) == 1
    assert "may i have your name" in result["messages"][0].content.lower()

@patch("app.ai.llm.client_factory.create_llm_model")
def test_name_enrichment_extract_success(mock_llm_fac):
    """Test extracting name successfully."""
    # Mock LLM to extract name
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = AIMessage(content="John Doe")
    mock_llm_fac.return_value = mock_llm
    
    # Access the module directly from sys.modules to bypass the function shadowing
    module = sys.modules["app.ai.graph.nodes.name_enrichment_node"]
    
    with patch.object(module, "DatabaseManager") as mock_db_cls:
        # Mock DB update
        mock_db = mock_db_cls.return_value
        mock_db.update_user_name.return_value = {"success": True}
        
        state = {
            "needs_name_enrichment": True,
            "user_id": 100,
            "messages": [
                HumanMessage(content="Hello"),
                AIMessage(content="May I have your name?"),
                HumanMessage(content="My name is John Doe")
            ]
        }
        
        result = name_enrichment_node(state)
        
        assert result["needs_name_enrichment"] is False
        assert result["user_profile"]["name"] == "John Doe"
        mock_db.update_user_name.assert_called_with(100, "John Doe")


# --- Helper Function Tests ---

def test_build_user_context_message():
    """Test the context message builder handles recent_appointments correctly."""
    from app.ai.graph.nodes.appointment_agent_node import _build_user_context_message
    
    # Test with standard recent_appointments (from user_context_node)
    profile = {
        "name": "Test User",
        "recent_appointments": [
            {
                "date": "2026-02-10",
                "time": "10:00:00",
                "service": "Checkup",
                "status": "scheduled"
            }
        ]
    }
    
    msg = _build_user_context_message(profile)
    assert msg is not None
    assert "2026-02-10 at 10:00:00" in msg.content
    assert "Checkup" in msg.content

