"""
LangGraph Entry Points
======================

Public API entry points for the appointment booking agent.
These functions are used by the REST and WebSocket APIs.

Author: Advanced AI Systems Team
Last Modified: 2026-02-27
"""

from langchain_core.messages import HumanMessage, AIMessage
from langgraph.types import Command

from app.core.logger_config import get_ai_agent_logger

logger = get_ai_agent_logger()



def run_agentic_graph(messages: list, thread_id: str, user_context: dict = None) -> str:
    """
    Runs the appointment agent for a given conversation session using LangGraph.
    
    This is the main entry point for chat-based interactions.
    
    Phase 7 Enhancement: Supports loop-back architecture by detecting suspended graphs
    and resuming from the interrupt point instead of re-running from __start__.
    
    Args:
        messages (list): List of message dicts (role/content) or LangChain message objects.
        thread_id (str): Unique session/call ID (used for memory).
        user_context (dict, optional): Context dictionary containing resolved user info.
        
    Returns:
        str: The agent's response as text.
    """
    from app.ai.graph.workflow import app as compiled_graph
    
    # Configure with thread_id for conversation memory
    config = {"configurable": {"thread_id": thread_id}}
    
    # Phase 7: Check if graph is suspended (mid-conversation)
    # If state.next is not empty, the graph is waiting at an interrupt point
    try:
        state_snapshot = compiled_graph.get_state(config)
        is_suspended = bool(state_snapshot.next)  # e.g., ('wait_for_input',)
        
        if is_suspended:
            # ✅ RESUME PATH: Graph is suspended at wait_for_input
            # Extract the last user message content
            last_message = messages[-1] if messages else {}
            if isinstance(last_message, HumanMessage):
                user_message_content = last_message.content
            elif isinstance(last_message, dict):
                user_message_content = last_message.get("content", "")
            else:
                user_message_content = str(last_message)
            
            logger.info(
                f"[GRAPH RESUME] thread_id={thread_id}, "
                f"resuming from interrupt with message: {user_message_content[:100]}..."
            )
            
            # Resume from interrupt point - skips user_context_loading, intent_guard, name_enrichment
            result = compiled_graph.invoke(
                Command(resume=user_message_content),
                config=config
            )
            
            logger.info(
                f"[GRAPH RESUME COMPLETE] thread_id={thread_id}, "
                f"skipped expensive nodes (user_context_loading, intent_guard)"
            )
            
        else:
            # 🆕 FRESH PATH: New conversation or first turn
            # Convert messages to LangChain message objects if needed
            langchain_messages = []
            for msg in messages:
                if isinstance(msg, (HumanMessage, AIMessage)):
                    langchain_messages.append(msg)
                elif isinstance(msg, dict):
                    role = msg.get("role")
                    content = msg.get("content", "")
                    if role == "user":
                        langchain_messages.append(HumanMessage(content=content))
                    elif role == "assistant":
                        langchain_messages.append(AIMessage(content=content))
            
            # Initialize defaults
            context = user_context or {}
            
            # Prepare initial state
            initial_state = {
                "messages": langchain_messages,
                # User context fields
                "caller_mobile_number": context.get("caller_mobile_number", ""),
                "user_profile": context.get("user_profile", {}),
                "user_context_loaded": context.get("user_context_loaded", False),
                "user_id": context.get("user_id", 0),
                "needs_name_enrichment": context.get("needs_name_enrichment", False),
                "name_prompt_level": context.get("name_prompt_level", 0)  # Phase 2: Escalation level
            }
            
            # Phase 0: Log graph entry with initial state
            logger.info(
                f"[GRAPH ENTRY] thread_id={thread_id}, "
                f"caller_mobile_number={initial_state.get('caller_mobile_number', 'N/A')}, "
                f"user_id={initial_state.get('user_id', 0)}, "
                f"needs_name_enrichment={initial_state.get('needs_name_enrichment', False)}"
            )
            logger.debug(
                f"[GRAPH ENTRY DEBUG] Full initial state: "
                f"user_context_loaded={initial_state.get('user_context_loaded', False)}, "
                f"message_count={len(initial_state.get('messages', []))}"
            )
            
            # Invoke compiled graph from __start__
            result = compiled_graph.invoke(initial_state, config)
        
        # Phase 0: Log graph exit with final state
        logger.info(
            f"[GRAPH EXIT] thread_id={thread_id}, "
            f"user_id={result.get('user_id', 0)}, "
            f"needs_name_enrichment={result.get('needs_name_enrichment', False)}, "
            f"intent={result.get('intent', 'N/A')}, "
            f"name_collection_in_progress={result.get('name_collection_in_progress', False)}"
        )
        logger.debug(
            f"[GRAPH EXIT DEBUG] Final state: "
            f"user_context_loaded={result.get('user_context_loaded', False)}, "
            f"response_message_count={len(result.get('messages', []))}"
        )
        
        # Extract final response from last message
        if result and "messages" in result and result["messages"]:
            last_message = result["messages"][-1]
            if hasattr(last_message, 'content'):
                final_response = last_message.content
                logger.info(f"Final AI Response (returned to API): {final_response[:200]}{'...' if len(final_response) > 200 else ''}")
                return final_response
            elif isinstance(last_message, dict) and 'content' in last_message:
                final_response = last_message['content']
                logger.info(f"Final AI Response (returned to API): {final_response[:200]}{'...' if len(final_response) > 200 else ''}")
                return final_response
            else:
                return "I'm sorry, the agent returned an unexpected message format."
        return "I'm sorry, I couldn't process your request right now (no messages in result)."
        
    except Exception as e:
        logger.error(f"Error running agentic graph: {e}", exc_info=True)
        return "An unexpected error occurred while processing your request. Please try again later."


def run_agentic_graph_stream(messages: list, thread_id: str, user_context: dict = None):
    """
    Streaming version - yields response text in chunks.
    
    Note: Since graph execution is blocking, this collects the full response
    then yields it in word-sized chunks to simulate streaming.
    
    For true token streaming, the LLM has streaming=True enabled,
    so internal token aggregation is happening at the LLM layer.
    
    Args:
        messages (list): List of message dicts or LangChain message objects.
        thread_id (str): Unique session/call ID (used for memory).
        user_context (dict, optional): Context dictionary containing resolved user info.
        
    Yields:
        str: Words/chunks of the response.
    """
    logger.info(f"[STREAM] Starting graph execution for thread_id={thread_id}")
    
    try:
        # Get full response using invoke (which now uses Groq streaming internally)
        full_response = run_agentic_graph(messages, thread_id, user_context)
        
        logger.info(f"[STREAM] Got full response ({len(full_response)} chars), now yielding tokens...")
        
        # Yield response in chunks (word-by-word for realistic streaming)
        words = full_response.split()
        token_count = 0
        for i, word in enumerate(words):
            token_count += 1
            if i < len(words) - 1:
                token = word + " "
            else:
                token = word
            
            logger.debug(f"[STREAM_TOKEN {token_count}] {token!r}")
            yield token
        
        logger.info(f"[STREAM COMPLETE] thread_id={thread_id}, response_len={len(full_response)}, tokens_yielded={token_count}")
        
    except Exception as e:
        logger.error(f"[STREAM ERROR] thread_id={thread_id}, error={e}", exc_info=True)
        yield f"Error: {str(e)}"



