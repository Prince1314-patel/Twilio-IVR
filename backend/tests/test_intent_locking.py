
import pytest
import sys
from unittest.mock import MagicMock, patch

# Ensure modules are imported
import app.ai.graph.nodes.intent_detection_node
import app.ai.graph.nodes.name_enrichment_node

# Get module objects explicitly from sys.modules to avoid function shadowing issues
intent_node_module = sys.modules["app.ai.graph.nodes.intent_detection_node"]
name_node_module = sys.modules["app.ai.graph.nodes.name_enrichment_node"]

from app.ai.graph.state import AgentState
from app.ai.intent.classifier import IntentCategory
from langchain_core.messages import AIMessage, HumanMessage

class TestIntentLocking:
    
    def test_intent_locking_activation(self):
        """Test that high confidence intent triggers locking and mode switch."""
        state = {
            "messages": [{"role": "user", "content": "I want to book an appointment"}],
            "intent_locked": False,
            "active_intent": None,
            "conversation_mode": "idle",
            "user_id": 123,
            "needs_name_enrichment": False
        }
        
        # Mock LLM response to return high confidence booking
        with patch.object(intent_node_module, "classify_intent_sync") as mock_classify:
            mock_classify.return_value = (IntentCategory.BOOKING, 0.95)
            
            result = intent_node_module.intent_detection_node(state)
            
            assert result["intent"] == IntentCategory.BOOKING
            assert result["intent_confidence"] == 0.95
            assert result["active_intent"] == IntentCategory.BOOKING
            assert result["intent_locked"] is True
            assert result["conversation_mode"] == "transaction"
            assert result["flow_completed"] is False
            
            # Verify flow_step initialization (booking first step)
            assert result["flow_step"] == "booking__appointment_type"

    def test_intent_guard_skips_llm(self):
        """Test that locked intent bypasses LLM and returns authoritative intent."""
        state = {
            "messages": [{"role": "user", "content": "My name is Prince"}],
            "intent_locked": True,
            "active_intent": "booking",
            "conversation_mode": "transaction",
            "user_id": 123,
            "needs_name_enrichment": False # Intent guard runs before name gate, but state persists
        }
        
        with patch.object(intent_node_module, "classify_intent_sync") as mock_classify:
            result = intent_node_module.intent_detection_node(state)
            
            # Ensure LLM was NOT called
            mock_classify.assert_not_called()
            
            # Ensure intent is preserved
            assert result["intent"] == "booking"
            assert result["intent_confidence"] == 1.0
            assert result["intent_locked"] is True
            assert result["conversation_mode"] == "transaction"

    def test_name_gate_non_destructive(self):
        """Test that name collection does not reset intent state."""
        state = {
            "messages": [
                AIMessage(content="What is your name?"),
                HumanMessage(content="Prince Patel")
            ],
            "needs_name_enrichment": True,
            "name_collection_in_progress": True,
            "intent_locked": True,
            "active_intent": "booking",
            "user_id": 123,
            "name_prompt_level": 1
        }
        
        with patch.object(name_node_module, "_extract_name_with_llm", return_value="Prince Patel"):
            with patch.object(name_node_module, "DatabaseManager") as mock_db_cls:
                mock_db = mock_db_cls.return_value
                mock_db.update_user_name.return_value = {"success": True}
                
                result = name_node_module.name_enrichment_node(state)
                
                # Check updates
                assert result["needs_name_enrichment"] is False
                assert result["name_collection_in_progress"] is False
                assert result["user_profile"]["name"] == "Prince Patel"
                
                # CRITICAL: result should NOT contain intent/locked keys (preserving them)
                assert "active_intent" not in result
                assert "intent_locked" not in result
                assert "conversation_mode" not in result
                
                # flow_step SHOULD be restored to the active intent's first step
                assert result.get("flow_step") == "booking__appointment_type"

