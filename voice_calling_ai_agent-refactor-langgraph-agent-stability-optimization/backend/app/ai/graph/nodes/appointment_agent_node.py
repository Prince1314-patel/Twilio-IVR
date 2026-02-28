"""
Appointment Agent Node
======================

**Backwards-compatible orchestrator**.

This module provides the ``appointment_agent_node`` that the LangGraph workflow
``workflow.py`` already imports.  Internally it now delegates to four focused
pipeline sub-nodes rather than containing the logic itself:

    flow_planner_node      → tool_executor_node
    → result_validator_node → response_generator_node

Each sub-node has a single responsibility:

1. ``flow_planner_node``       — deterministic FSM step progression (no LLM)
2. ``tool_executor_node``      — allowlist guards + tool execution
3. ``result_validator_node``   — evidence gate (hallucination guard)
4. ``response_generator_node`` — emit final AIMessage

The graph wiring in ``workflow.py`` is unchanged — only the internals of this
node have been restructured.

Backwards-compatibility shims
------------------------------
Tests and other callers that historically accessed module-level symbols from
this file (``model``, ``FIRST_FLOW_STEP_BY_INTENT``, ``_detect_intent_override``)
can still do so via the re-exports below.

Author: Advanced AI Systems Team
Last Modified: 2026-02-25
"""

# ---------------------------------------------------------------------------
# Backwards-compatibility re-exports
# Patch-targets like ``patch.object(agent_node_module, "model", ...)`` and
# ``getattr(agent_node_module, "_detect_intent_override")`` will still work.
# ---------------------------------------------------------------------------

# The module-level LLM model lives in tool_executor_node now.
from app.ai.graph.nodes.appointment_pipeline.tool_executor_node import model  # noqa: F401

# Intent-override helper lives in flow_planner_node now.
from app.ai.graph.nodes.appointment_pipeline.flow_planner_node import (  # noqa: F401
    _detect_intent_override,
)

# State constants (unchanged location — still in state.py, re-exported for patch convenience)
from app.ai.graph.state import FIRST_FLOW_STEP_BY_INTENT  # noqa: F401

# ---------------------------------------------------------------------------
# Pipeline sub-node imports
# ---------------------------------------------------------------------------
from app.ai.graph.state import AgentState
from app.core.logger_config import get_ai_agent_logger

from app.ai.graph.nodes.appointment_pipeline.flow_planner_node    import flow_planner_node
from app.ai.graph.nodes.appointment_pipeline.tool_executor_node   import tool_executor_node
from app.ai.graph.nodes.appointment_pipeline.result_validator_node  import result_validator_node
from app.ai.graph.nodes.appointment_pipeline.response_generator_node import response_generator_node

logger = get_ai_agent_logger()


def appointment_agent_node(state: AgentState) -> dict:
    """Orchestrate the four-node appointment pipeline.

    The function merges each sub-node's output dict into a running state
    snapshot so that each downstream node sees the latest values produced
    by its predecessor.
    """
    logger.info("[APPOINTMENT AGENT] Starting four-node pipeline.")

    # ------------------------------------------------------------------ #
    # 1. FLOW PLANNER — deterministic FSM                                 #
    # ------------------------------------------------------------------ #
    planner_out = flow_planner_node(state)
    merged = {**state, **planner_out}     # planner output overlays base state

    # ------------------------------------------------------------------ #
    # 2. TOOL EXECUTOR — guards + tool loop                               #
    # ------------------------------------------------------------------ #
    executor_out = tool_executor_node(merged)
    merged = {**merged, **executor_out}

    # ------------------------------------------------------------------ #
    # 3. RESULT VALIDATOR — evidence gate                                 #
    # ------------------------------------------------------------------ #
    validator_out = result_validator_node(merged)
    merged = {**merged, **validator_out}

    # ------------------------------------------------------------------ #
    # 4. RESPONSE GENERATOR (or ESCALATION)                               #
    # ------------------------------------------------------------------ #
    safety_conflicts = merged.get("safety_conflict_count", 0)
    validation_failures = merged.get("validation_failure_count", 0)

    if safety_conflicts >= 2 or validation_failures >= 2:
        from app.ai.graph.nodes.appointment_pipeline.human_escalation_node import human_escalation_node
        generator_out = human_escalation_node(merged)
        merged.update(generator_out)
    else:
        generator_out = response_generator_node(merged)

    # ------------------------------------------------------------------ #
    # Compose final return dict                                           #
    # State fields that the graph/checkpointer must persist:             #
    #   messages, active_intent, intent_locked, flow_step,               #
    #   flow_completed, collected_slots, intent, intent_confidence        #
    # Ephemeral cross-node fields (_planner_*, _executor_*, _validator_*) #
    #   are intentionally NOT forwarded so they don't pollute the        #
    #   LangGraph checkpoint.                                             #
    # ------------------------------------------------------------------ #
    logger.info("[APPOINTMENT AGENT] Pipeline complete.")

    return {
        # Messages emitted this turn (single clean AIMessage from generator)
        "messages": generator_out["messages"],

        # Flow control state
        "active_intent":      merged.get("active_intent"),
        "intent_locked":      merged.get("intent_locked"),
        "flow_step":          merged.get("flow_step"),
        "flow_completed":     merged.get("flow_completed"),
        "collected_slots":    merged.get("collected_slots"),
        "conversation_mode":  merged.get("conversation_mode"),

        # Verification metadata — top-level, NOT inside collected_slots (task #23)
        "valid_appointment_ids": merged.get("valid_appointment_ids", []),
        "valid_appointments":    merged.get("valid_appointments", []),

        # Escalation and Safety 
        "safety_conflict_count":    merged.get("safety_conflict_count"),
        "validation_failure_count": merged.get("validation_failure_count"),
        "escalation_triggered":     merged.get("escalation_triggered"),

        # Intent classification fields
        "intent":             merged.get("intent"),
        "intent_confidence":  merged.get("intent_confidence"),
    }
