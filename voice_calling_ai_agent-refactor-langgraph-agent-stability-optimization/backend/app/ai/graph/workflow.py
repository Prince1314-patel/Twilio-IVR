"""
LangGraph Workflow
==================

Constructs and compiles the appointment booking agent graph.

CURRENT ARCHITECTURE (Phase 7 COMPLETE - Loop-Back):
----------------------------------------------
Entry: user_context_loading
Flow: user_context_loading → intent_guard → name_enrichment (NAME GATE) → business_router → appointment_agent → sanitize_output

Loop-Back: sanitize_output → [flow_completed?]
                              ├── YES → END
                              └── NO  → wait_for_input → business_router (loop)

Conditional Routing:
- After name_enrichment: Routes to END if name_collection_in_progress=True (BLOCK), else to business_router (PASS)
- After sanitize_output: Routes to END if flow_completed=True, else to wait_for_input (loop back)

PHASE 7 CHANGES (Loop-Back Architecture):
--------------------------
1. ✅ Added wait_for_input node that uses interrupt() to pause for next user message
2. ✅ Added conditional routing after sanitize_output based on flow_completed flag
3. ✅ Loop back to business_router instead of re-running expensive nodes
4. ✅ Skips user_context_loading, intent_guard, name_enrichment on subsequent turns

LATENCY BENEFITS:
--------------------------
- Saves ~350-1200ms per mid-conversation turn (30-60% reduction)
- Skips DB lookup (50-100ms) on subsequent turns
- Skips intent classification LLM call (300-1500ms) when intent is locked
- Maintains conversation context without re-establishing identity

TARGET ARCHITECTURE (Phase 7 COMPLETE):
--------------------------------
Entry: user_context_loading (runs once per conversation)
First Turn: user_context_loading → intent_guard → name_enrichment → business_router → appointment_agent → sanitize_output
Subsequent Turns: wait_for_input → business_router → appointment_agent → sanitize_output (loop until flow_completed=True)

Key Changes:
- User resolution becomes entry point (Phase 2) ✅
- Name enrichment becomes a true blocking gate (Phase 3) ✅
- Intent detection moved after name gate with assertions (Phase 4) ✅
- Business router added for intent-based routing (Phase 5) ✅
- Appointment agent simplified to pure business logic (Phase 6) ✅
- Loop-back architecture for multi-turn conversations (Phase 7) ✅

See docs/GRAPH_ARCHITECTURE.md for detailed mental model and migration plan.

Author: Advanced AI Systems Team
Last Modified: 2026-02-27
"""

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.types import interrupt
from psycopg_pool import ConnectionPool

from app.core.config import settings
from app.ai.graph.state import AgentState
from app.ai.graph.nodes import (
    intent_detection_node,
    user_context_loading_node,
    name_enrichment_node,
    business_router_node,
    route_by_intent,
    appointment_agent_node,
    sanitize_output_node,
)
from app.core.logger_config import get_ai_agent_logger

logger = get_ai_agent_logger()


def route_after_name_enrichment(state: AgentState) -> str:
    """
    Conditional routing function to determine next node after name enrichment.
    
    Phase 2: NAME GATE routing - enforces identity-first architecture.
    
    Routes to:
    - "end": If we're waiting for user to provide their name (BLOCK - name_collection_in_progress=True)
    - "business_router": If name collection is complete (PASS - proceed to business routing)
    
    Args:
        state: Current agent state
        
    Returns:
        Next node name: "end" or "business_router"
    """
    name_collection_in_progress = state.get("name_collection_in_progress", False)
    
    if name_collection_in_progress:
        logger.info("[NAME GATE ROUTING] BLOCK - routing to END (waiting for user response)")
        return "end"
    else:
        logger.info("[NAME GATE ROUTING] PASS - routing to business_router")
        return "business_router"


def wait_for_input_node(state: AgentState) -> AgentState:
    """
    Pause execution and wait for the next user message.
    
    This node uses interrupt() to suspend the graph until the next user input arrives.
    When resumed, it appends the new user message to the conversation and loops back
    to business_router to continue the transactional flow.
    
    This enables multi-turn conversations without re-running expensive nodes like
    user_context_loading and intent_guard on every turn.
    
    Args:
        state: Current agent state
        
    Returns:
        Updated state with new user message appended
    """
    logger.info("[WAIT FOR INPUT] Pausing graph, waiting for next user message...")
    
    # Suspend execution until next user input
    user_message = interrupt("waiting_for_user_input")
    
    logger.info(f"[WAIT FOR INPUT] Resumed with user message: {user_message[:100]}...")
    
    # Append the new user message to conversation history
    return {
        "messages": state["messages"] + [
            {"role": "user", "content": user_message}
        ]
    }


def route_after_sanitize(state: AgentState) -> str:
    """
    Conditional routing after sanitize_output to determine if conversation continues.
    
    Routes to:
    - "end": If flow is completed (transaction finished)
    - "wait_for_input": If flow continues (multi-turn conversation)
    
    Args:
        state: Current agent state
        
    Returns:
        Next node name: "end" or "wait_for_input"
    """
    flow_completed = state.get("flow_completed", False)
    
    if flow_completed:
        logger.info("[SANITIZE ROUTING] Flow completed - routing to END")
        return "end"
    else:
        logger.info("[SANITIZE ROUTING] Flow continues - routing to wait_for_input (loop back)")
        return "wait_for_input"


# Create checkpointer for conversation memory
try:
    if settings.DATABASE_URL and settings.DATABASE_URL.startswith("postgres"):
        # Safe-guard if SQLAlchemy-style URI is provided
        db_url = settings.DATABASE_URL.replace("postgresql+psycopg2", "postgresql", 1)
        pool = ConnectionPool(
            conninfo=db_url,
            max_size=20,
            kwargs={'autocommit': True, 'prepare_threshold': 0}
        )
        memory = PostgresSaver(pool)
        memory.setup()
        logger.info("Using PostgresSaver for LangGraph memory")
    else:
        memory = InMemorySaver()
        logger.info("Using InMemorySaver for LangGraph memory")
except Exception as e:
    logger.error(f"Failed to initialize PostgresSaver, falling back to InMemorySaver: {e}")
    memory = InMemorySaver()

# Build the graph
workflow = StateGraph(AgentState)

# Add nodes
workflow.add_node("user_context_loading", user_context_loading_node)
workflow.add_node("intent_guard", intent_detection_node)
workflow.add_node("name_enrichment", name_enrichment_node)
workflow.add_node("business_router", business_router_node)
workflow.add_node("appointment_agent", appointment_agent_node)
workflow.add_node("sanitize_output", sanitize_output_node)
workflow.add_node("wait_for_input", wait_for_input_node)  # New: Loop-back node

# Phase 6+: Identity-First + Intent Guard Flow
# user_context_loading → intent_guard → name_enrichment (NAME GATE) → business_router
workflow.add_edge("user_context_loading", "intent_guard")
workflow.add_edge("intent_guard", "name_enrichment")

# Conditional routing after name enrichment (NAME GATE)
workflow.add_conditional_edges(
    "name_enrichment",
    route_after_name_enrichment,
    {
        "business_router": "business_router",  # PASS: name collected
        "end": END  # BLOCK: waiting for name
    }
)

# Phase 5: Business Routing (Intent -> Agent)
workflow.add_conditional_edges(
    "business_router",
    route_by_intent,
    {
        "appointment_agent": "appointment_agent"
    }
)

workflow.add_edge("appointment_agent", "sanitize_output")

# Phase 7: Loop-back architecture for multi-turn conversations
# After sanitize_output, check if flow is completed:
#   - If completed: END
#   - If not completed: wait_for_input → business_router (loop back)
workflow.add_conditional_edges(
    "sanitize_output",
    route_after_sanitize,
    {
        "end": END,                      # Flow completed
        "wait_for_input": "wait_for_input"  # Continue conversation
    }
)

# Loop back to business_router after receiving next user input
workflow.add_edge("wait_for_input", "business_router")

# Phase 2: Set entry point to user_context_loading (identity-first)
workflow.set_entry_point("user_context_loading")

# Compile the graph with checkpointer
app = workflow.compile(checkpointer=memory)

logger.info(
    "LangGraph workflow compiled successfully with Postgres/InMemory saver."
)



