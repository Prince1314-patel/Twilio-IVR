"""
LangGraph Adapter for LiveKit
==============================

Wraps the existing compiled LangGraph workflow so that LiveKit's AgentSession
can use it as its LLM provider via livekit-plugins-langchain's LLMAdapter.

STREAMING SUPPORT:
    The Groq LLM is configured with streaming=True, which means:
    - Groq returns tokens incrementally (not waiting for full response)
    - LLMAdapter consumes the token stream automatically
    - Tokens are sent to TTS pipeline in real-time
    - Result: Natural, responsive voice agent with minimal latency

IMPORTANT: LLMAdapter does NOT accept an `initial_state` parameter.
We pre-seed the graph's InMemorySaver checkpointer via graph.update_state()
so that identity-first fields (caller_mobile_number, etc.) are already
present when the adapter invokes the graph for the first time.

Author: Advanced AI Systems Team
Last Modified: 2026-02-27
"""

from livekit.plugins.langchain import LLMAdapter
from langchain_core.runnables import RunnableConfig

from app.ai.graph.workflow import app as compiled_graph
from app.core.logger_config import get_ai_agent_logger

logger = get_ai_agent_logger()


def create_langgraph_llm(
    caller_mobile_number: str,
    session_id: str,
) -> LLMAdapter:
    """
    Create an LLMAdapter that wraps our compiled LangGraph workflow with streaming.

    The adapter translates LiveKit ChatContext into LangChain messages,
    invokes the graph with streaming enabled, and streams the response tokens
    in real-time back to the AgentSession voice pipeline.

    Streaming Architecture:
        Caller Speech
           ↓
        STT (Sarvam) - streaming enabled
           ↓
        User Messages (streamed to LLM)
           ↓
        LangGraph with Groq (streaming=True)
           ↓
        Token Stream → TTS (Sarvam) - processes tokens as they arrive
           ↓
        Agent Speech (minimal latency)

    State injection strategy:
        LLMAdapter only accepts ``graph`` and ``config``.  To satisfy the
        identity-first architecture (the graph's entry node,
        ``user_context_loading``, expects ``caller_mobile_number``), we
        pre-seed the checkpointer via ``graph.update_state()`` *before*
        creating the adapter.

    Args:
        caller_mobile_number: Caller's phone number extracted from SIP
            participant attributes or room metadata.
        session_id: Unique session identifier (typically the LiveKit room
            name).  Mapped to the LangGraph ``thread_id``.

    Returns:
        LLMAdapter instance ready for use in an AgentSession with streaming enabled.
    """
    config = RunnableConfig(
        run_name=session_id,
        tags=["livekit-session", "streaming"],
        metadata={
            "source": "livekit",
            "session_id": session_id,
            "streaming_enabled": True,
        },
        configurable={"thread_id": session_id},
    )

    # ------------------------------------------------------------------
    # Pre-seed the graph's checkpointer with identity & initial state.
    # This writes the initial state into the InMemorySaver so the first
    # graph.invoke() from the adapter already has caller context.
    # ------------------------------------------------------------------
    initial_state = {
        "caller_mobile_number": caller_mobile_number,
        "user_profile": {},
        "user_context_loaded": False,
        "user_id": 0,
        "needs_name_enrichment": False,
        "name_collection_in_progress": False,
        "name_prompt_level": 0,
        "intent": "",
        "intent_confidence": 0.0,
    }

    compiled_graph.update_state(config, values=initial_state)

    logger.info(
        f"[LIVEKIT STREAMING ADAPTER] Pre-seeded graph state for session={session_id}, "
        f"caller={caller_mobile_number}, streaming=enabled"
    )

    # ------------------------------------------------------------------
    # Create the adapter — it only accepts `graph` and `config`.
    # Important: Groq LLM already has streaming=True, so LLMAdapter
    # will automatically receive tokens and pass them to TTS.
    # ------------------------------------------------------------------
    adapter = LLMAdapter(
        graph=compiled_graph,
        config=config,
    )

    logger.info(
        f"[LIVEKIT STREAMING ADAPTER] LLMAdapter created for session={session_id} "
        f"with Groq streaming enabled"
    )

    return adapter
