"""
Phase 0 Logging Tests
=====================

Tests to verify Phase 0 logging enhancements are working correctly.
Tests graph entry/exit logging and node-level debug logging.

Author: Advanced AI Systems Team
Created: 2026-02-09
"""

import pytest
from unittest.mock import Mock, patch
from langchain_core.messages import HumanMessage, AIMessage

from app.ai.graph.state import AgentState
from app.ai.graph.nodes.appointment_agent_node import appointment_agent_node
from app.ai.graph.nodes.user_context_node import user_context_loading_node
from app.ai.graph.nodes.name_enrichment_node import name_enrichment_node
from app.ai.graph.nodes.intent_detection_node import intent_detection_node


class TestGraphEntryExitLogging:
    """Test graph entry and exit logging in entrypoint.py"""
    
    def test_graph_entry_logging_present(self, caplog):
        """Verify graph entry logging contains required fields"""
        from app.ai.graph.entrypoint import run_agentic_graph
        
        messages = [HumanMessage(content="Hello")]
        thread_id = "test-thread-123"
        user_context = {
            "caller_mobile_number": "+919876543210",
            "user_id": 1,
            "needs_name_enrichment": False,
            "name_prompt_level": 0  # Phase 2: Added field
        }
        
        with caplog.at_level("INFO"):
            try:
                run_agentic_graph(messages, thread_id, user_context)
            except Exception:
                pass  # We're testing logging, not functionality
        
        # Check that graph entry log is present
        entry_logs = [r for r in caplog.records if "[GRAPH ENTRY]" in r.message]
        assert len(entry_logs) > 0, "Graph entry log not found"
        
        entry_log = entry_logs[0].message
        assert "thread_id=test-thread-123" in entry_log
        assert "caller_mobile_number=+919876543210" in entry_log
        assert "user_id=1" in entry_log
        assert "needs_name_enrichment=False" in entry_log
    
    def test_graph_exit_logging_present(self, caplog):
        """Verify graph exit logging contains required fields"""
        from app.ai.graph.entrypoint import run_agentic_graph
        
        messages = [HumanMessage(content="Hello")]
        thread_id = "test-thread-456"
        user_context = {
            "caller_mobile_number": "+919876543210",
            "user_id": 2,
            "needs_name_enrichment": True,
            "name_prompt_level": 0  # Phase 2: Added field
        }
        
        with caplog.at_level("INFO"):
            try:
                run_agentic_graph(messages, thread_id, user_context)
            except Exception:
                pass  # We're testing logging, not functionality
        
        # Check that graph exit log is present
        exit_logs = [r for r in caplog.records if "[GRAPH EXIT]" in r.message]
        assert len(exit_logs) > 0, "Graph exit log not found"
        
        exit_log = exit_logs[0].message
        assert "thread_id=test-thread-456" in exit_log
        assert "user_id=" in exit_log
        assert "needs_name_enrichment=" in exit_log
        assert "intent=" in exit_log


class TestNodeLevelLogging:
    """Test node-level debug logging"""
    
    def test_appointment_agent_debug_logging(self, caplog):
        """Verify appointment agent logs critical state fields"""
        state: AgentState = {
            "messages": [HumanMessage(content="Book appointment")],
            "intent": "booking",
            "intent_confidence": 0.9,
            "user_id": 123,
            "needs_name_enrichment": False,
            "user_context_loaded": True,
            "caller_mobile_number": "+919876543210",
            "user_profile": {"name": "Test User"},
            "name_collection_in_progress": False,
            "name_prompt_level": 0  # Phase 2: Added field
        }
        
        with caplog.at_level("DEBUG"):
            try:
                appointment_agent_node(state)
            except Exception:
                pass  # We're testing logging, not functionality
        
        # Check for appointment agent entry log
        entry_logs = [r for r in caplog.records if "[APPOINTMENT AGENT ENTRY]" in r.message]
        assert len(entry_logs) > 0, "Appointment agent entry log not found"
        
        entry_log = entry_logs[0].message
        assert "user_id=123" in entry_log
        assert "needs_name_enrichment=False" in entry_log
        assert "intent=booking" in entry_log
        assert "intent_confidence=0.90" in entry_log
    
    @patch('app.ai.graph.nodes.user_context_node.DatabaseManager')
    def test_user_context_node_debug_logging(self, mock_db, caplog):
        """Verify user context node logs entry state"""
        state: AgentState = {
            "messages": [],
            "caller_mobile_number": "+919876543210",
            "user_id": 0,
            "intent": "",
            "intent_confidence": 0.0,
            "user_profile": {},
            "user_context_loaded": False,
            "needs_name_enrichment": False,
            "name_collection_in_progress": False,
            "name_prompt_level": 0  # Phase 2: Added field
        }
        
        # Mock database response
        mock_db_instance = Mock()
        mock_db_instance.get_user_by_mobile_number.return_value = None
        mock_db_instance.create_user_with_phone.return_value = {"success": True, "user_id": 1}
        mock_db.return_value = mock_db_instance
        
        with caplog.at_level("DEBUG"):
            user_context_loading_node(state)
        
        # Check for user context node entry log
        entry_logs = [r for r in caplog.records if "[USER CONTEXT NODE ENTRY]" in r.message]
        assert len(entry_logs) > 0, "User context node entry log not found"
        
        entry_log = entry_logs[0].message
        assert "caller_mobile_number=+919876543210" in entry_log
        assert "existing_user_id=0" in entry_log
    
    def test_name_enrichment_node_debug_logging(self, caplog):
        """Verify name enrichment node logs state transitions"""
        state: AgentState = {
            "messages": [],
            "user_id": 456,
            "needs_name_enrichment": True,
            "name_collection_in_progress": False,
            "name_prompt_level": 0,  # Phase 2: Added field
            "intent": "",
            "intent_confidence": 0.0,
            "caller_mobile_number": "",
            "user_profile": {},
            "user_context_loaded": True
        }
        
        with caplog.at_level("DEBUG"):
            name_enrichment_node(state)
        
        # Phase 2: Check for NAME GATE entry log (renamed from NAME ENRICHMENT NODE ENTRY)
        entry_logs = [r for r in caplog.records if "[NAME GATE ENTRY]" in r.message]
        assert len(entry_logs) > 0, "Name gate entry log not found"
        
        entry_log = entry_logs[0].message
        assert "needs_enrichment=True" in entry_log
        assert "user_id=456" in entry_log
        assert "name_collection_in_progress=False" in entry_log
    
    @patch('app.ai.graph.nodes.intent_detection_node.classify_intent_sync')
    def test_intent_detection_node_debug_logging(self, mock_classify, caplog):
        """Verify intent detection node logs classification results"""
        from app.ai.intent.classifier import IntentCategory
        
        state: AgentState = {
            "messages": [HumanMessage(content="I want to book an appointment")],
            "intent": "",
            "intent_confidence": 0.0,
            "user_id": 0,
            "caller_mobile_number": "",
            "user_profile": {},
            "user_context_loaded": False,
            "needs_name_enrichment": False,
            "name_collection_in_progress": False,
            "name_prompt_level": 0  # Phase 2: Added field
        }
        
        # Mock intent classification
        mock_classify.return_value = (IntentCategory.BOOKING, 0.95)
        
        with caplog.at_level("DEBUG"):
            intent_detection_node(state)
        
        # Check for intent detection node entry log
        entry_logs = [r for r in caplog.records if "[INTENT DETECTION NODE ENTRY]" in r.message]
        assert len(entry_logs) > 0, "Intent detection node entry log not found"
        
        # Check for classification result log
        classification_logs = [r for r in caplog.records if "[INTENT DETECTION]" in r.message]
        assert len(classification_logs) > 0, "Intent classification result log not found"


class TestStreamingLogging:
    """Test streaming-specific logging"""
    
    @pytest.mark.asyncio
    async def test_streaming_entry_logging(self, caplog):
        """Verify streaming graph entry logging"""
        from app.ai.graph.entrypoint import run_agentic_graph_streaming
        
        with caplog.at_level("INFO"):
            try:
                await run_agentic_graph_streaming(
                    user_text="Hello",
                    session_id="stream-session-123",
                    caller_mobile_number="+919876543210"
                )
            except Exception:
                pass  # We're testing logging, not functionality
        
        # Check for streaming entry log
        entry_logs = [r for r in caplog.records if "[GRAPH ENTRY STREAMING]" in r.message]
        assert len(entry_logs) > 0, "Streaming graph entry log not found"
        
        entry_log = entry_logs[0].message
        assert "session_id=stream-session-123" in entry_log
        assert "caller_mobile_number=+919876543210" in entry_log
