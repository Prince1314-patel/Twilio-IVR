"""
Appointment Pipeline Sub-Nodes
================================

These four focused nodes replace the monolithic ``appointment_agent_node``.
Each node has a single, well-defined responsibility:

1. flow_planner_node      — Deterministic FSM step progression. No LLM.
2. tool_executor_node     — Strict per-step allowlist + precondition guards +
                            tool execution. No LLM.
3. result_validator_node  — Evidence gate: blocks hallucinated confirmations.
                            No LLM.
4. response_generator_node— LLM-only language generation from validated state.

The nodes are composable — they share ``AgentState`` as the data contract and
can be wired into the LangGraph workflow individually or through the backwards-
compatible ``appointment_agent_node`` orchestrator.

Author: Advanced AI Systems Team
Last Modified: 2026-02-25
"""

from app.ai.graph.nodes.appointment_pipeline.flow_planner_node import flow_planner_node
from app.ai.graph.nodes.appointment_pipeline.tool_executor_node import tool_executor_node
from app.ai.graph.nodes.appointment_pipeline.result_validator_node import result_validator_node
from app.ai.graph.nodes.appointment_pipeline.response_generator_node import response_generator_node

__all__ = [
    "flow_planner_node",
    "tool_executor_node",
    "result_validator_node",
    "response_generator_node",
]
