"""
LangGraph Agent State Definition
=================================

Defines the state schema for the appointment booking agent graph.

Author: Advanced AI Systems Team
Last Modified: 2026-01-29
"""

from typing import TypedDict, Annotated, Optional
from operator import add
from langchain_core.messages import BaseMessage


def add_messages(left: list[BaseMessage], right: list[BaseMessage]) -> list[BaseMessage]:
    """
    Reducer function to add messages to the conversation history.
    
    This is the standard message reducer used by LangGraph to merge message lists.
    
    Args:
        left: Existing messages in state
        right: New messages to add
        
    Returns:
        Combined message list
    """
    return left + right



class InfrastructureState(TypedDict):
    """Core identity fields (Phase 1)"""
    caller_mobile_number: str
    user_id: int


class OnboardingState(TypedDict):
    """Fields used during user resolution and name interaction (Phase 2)"""
    user_profile: dict
    user_context_loaded: bool
    needs_name_enrichment: bool
    name_collection_in_progress: bool
    name_prompt_level: int


class BusinessState(TypedDict):
    """Fields used for intelligence and business logic (Phase 3+)"""

    # Core intelligence fields
    messages: Annotated[list[BaseMessage], add_messages]

    # Last classified intent (message-level, may change before lock)
    intent: str
    intent_confidence: float

    # Transactional flow control (IVR-grade, session-level)
    #
    # CRITICAL: These fields model the locked transactional intent and
    # deterministic flow progression. They MUST persist across graph
    # invocations via the LangGraph checkpointer.
    #
    # - active_intent:
    #       booking | cancellation | rescheduling | inquiry | greeting | out_of_scope
    #   When set AND intent_locked=True, this represents the current
    #   transactional session intent. Short user replies (e.g. "yes",
    #   "tomorrow", "5 pm") MUST NOT change this.
    #
    # - intent_locked:
    #       False by default. Once set to True after a high-confidence
    #       detection (≥ 0.7), the system MUST:
    #         * stop re-running the intent classifier
    #         * stay inside the owning flow until explicit completion
    #         * ignore future re-classification attempts
    #
    # - flow_step:
    #       A string identifier representing the current transactional
    #       step, e.g.:
    #         booking__appointment_type → booking__date → booking__time
    #         → booking__symptoms → booking__confirm → booking__complete
    #
    # - flow_completed:
    #       False by default. Set to True only when the transactional
    #       operation has been fully executed (e.g. booking created,
    #       cancellation applied, reschedule committed).
    #
    # - collected_slots:
    #       Dictionary tracking ONLY user-provided slot data for the current
    #       transactional flow.  Keys are slot names (e.g. "appointment_type",
    #       "date", "time"), values are the extracted/validated data.
    #       Initialized as empty dict {} when a flow starts, populated
    #       as the conversation progresses. Used to:
    #         * Determine when to advance flow_step
    #         * Provide context to the LLM about what's been captured
    #         * Validate flow completion before final confirmation
    #       Example: {"appointment_type": "regular", "date": "2026-02-11"}
    #
    #       INVARIANT: collected_slots MUST NOT contain control-state keys
    #       such as "flow_step", "valid_appointment_ids", or
    #       "valid_appointments".  Those belong in dedicated top-level fields
    #       (see valid_appointment_ids / valid_appointments below).
    #
    # - valid_appointment_ids:
    #       List of integer appointment IDs that were returned by
    #       get_upcoming_appointments and are therefore safe to use in
    #       destructive operations (cancel / reschedule).  This is
    #       CONTROL/VERIFICATION metadata — it must never be stored inside
    #       collected_slots.
    #
    # - valid_appointments:
    #       Full appointment dicts returned by get_upcoming_appointments for
    #       the current session.  Used for auto-resolution (single match)
    #       and for presenting choices to the user.  Also CONTROL metadata.
    #
    # Nodes MUST treat these fields as authoritative for routing and
    # MUST NOT infer new intent mid-flow unless the user explicitly
    # overrides (e.g. "actually cancel it instead").
    active_intent: Optional[str]
    intent_locked: bool
    conversation_mode: str  # "idle" | "transaction"
    flow_step: Optional[str]
    flow_completed: bool
    collected_slots: dict
    # Verification metadata — kept separate from slot payload (task #23)
    valid_appointment_ids: list
    valid_appointments: list
    safety_conflict_count: int
    validation_failure_count: int
    escalation_triggered: bool


class AgentState(InfrastructureState, OnboardingState, BusinessState):
    """
    State schema for the appointment booking agent graph.
    
    STATE LIFECYCLE & OWNERSHIP:
    ----------------------------
    
    Phase 1: Infrastructure State (Set Once, Never Modified)
    - caller_mobile_number: Set at graph entry, immutable
    - user_id: Set by user_context_loading, immutable after (must be != 0)
    
    Phase 2: Onboarding State (Used Only Until Name Gate)
    - user_profile: Loaded by user_context_loading, enriched by name_enrichment
    - user_context_loaded: Set by user_context_loading
    - needs_name_enrichment: Set by user_context_loading, cleared by name_enrichment
    - name_collection_in_progress: Set/cleared by name_enrichment
    - name_prompt_level: Tracks escalation level for name collection (0-5, Phase 2+)
    
    Phase 3: Intelligence State (Set After Onboarding)
    - intent: Set by intent_detection_node
    - intent_confidence: Set by intent_detection_node
    
    Phase 4: Business State (Used Throughout Conversation)
    - messages: Conversation history (append-only via reducer)
    
    CRITICAL INVARIANTS:
    --------------------
    1. user_id must be != 0 before appointment_agent_node runs
    2. needs_name_enrichment must be False before intent_detection runs (target)
    3. Onboarding state fields should not be read after name gate (target)
    4. Infrastructure state is immutable after initial population
    
    See docs/GRAPH_ARCHITECTURE.md for detailed state transition model.
    """
    pass


# ---------------------------------------------------------------------------
# Transactional Flow Step Definitions
# ---------------------------------------------------------------------------
#
# These canonical step identifiers are used by intent detection and
# downstream business logic (e.g. appointment_agent_node) to implement
# deterministic, IVR-grade flows. Steps are namespaced by intent to
# make ownership explicit and to prevent cross-intent leakage.

# First step per transactional intent. Used when an intent is first
# locked (intent_locked becomes True).
FIRST_FLOW_STEP_BY_INTENT: dict[str, str] = {
    "booking": "booking__appointment_type",
    "cancellation": "cancellation__appointment_id",
    "rescheduling": "rescheduling__select_appointment",
    "inquiry": "inquiry__question",
    # Non-transactional but still useful for routing:
    "greeting": "greeting__open",
    "out_of_scope": "out_of_scope__redirect",
}


# Complete flow definitions for each transactional intent.
# Each flow is a list of steps in sequence, with metadata about what to collect.
FLOW_DEFINITIONS: dict[str, list[dict]] = {
    "booking": [
        {
            "step": "booking__appointment_type",
            "next_step": "booking__date",
            "required_slot": "appointment_type",
            "prompt_hint": "Ask what type of appointment (regular, emergency, or followup)",
            "validation": lambda v: v and str(v).lower() in ["regular", "emergency", "followup"],
        },
        {
            "step": "booking__date",
            "next_step": "booking__time",
            "required_slot": "date",
            "prompt_hint": "Ask for preferred appointment date",
            "validation": None,  # Validated by slot extractor
        },
        {
            "step": "booking__time",
            "next_step": "booking__symptoms",
            "required_slot": "time",
            "prompt_hint": "Ask for preferred appointment time",
            "validation": None,  # Validated by slot extractor and availability check
        },
        {
            "step": "booking__symptoms",
            "next_step": "booking__confirmation",
            "required_slot": "symptoms",
            "prompt_hint": "Ask what brings them in / reason for appointment",
            "validation": None,  # Free text, always acceptable
        },
        {
            "step": "booking__confirmation",
            "next_step": None,  # Final step
            "required_slot": "confirmed",
            "prompt_hint": "Confirm all details and get explicit yes/no",
            "validation": lambda v: v and str(v).lower() in ["yes", "confirmed", "true"],
        },
    ],
    "cancellation": [
        {
            "step": "cancellation__appointment_id",
            "next_step": "cancellation__reason",
            "required_slot": "appointment_id",
            "prompt_hint": "Ask for appointment ID or identify from user history",
            "validation": lambda v: v and (isinstance(v, int) or str(v).isdigit()),
        },
        {
            "step": "cancellation__reason",
            "next_step": "cancellation__confirmation",
            "required_slot": "reason",
            "prompt_hint": "Ask reason for cancellation",
            "validation": None,  # Free text
        },
        {
            "step": "cancellation__confirmation",
            "next_step": None,  # Final step
            "required_slot": "confirmed",
            "prompt_hint": "Confirm cancellation with explicit yes/no",
            "validation": lambda v: v and str(v).lower() in ["yes", "confirmed", "true"],
        },
    ],
    "rescheduling": [
        {
            "step": "rescheduling__select_appointment",
            "next_step": "rescheduling__new_date",
            "required_slot": "appointment_id",
            "prompt_hint": "Check if user has multiple upcoming appointments. If so, list them and ask user to select one. If only one, confirm it. If none, inform user.",
            "validation": lambda v: v and (isinstance(v, int) or str(v).isdigit()),
        },
        {
            "step": "rescheduling__new_date",
            "next_step": "rescheduling__new_time",
            "required_slot": "new_date",
            "prompt_hint": "Ask for new preferred date",
            "validation": None,  # Validated by slot extractor
        },
        {
            "step": "rescheduling__new_time",
            "next_step": "rescheduling__confirmation",
            "required_slot": "new_time",
            "prompt_hint": "Ask for new preferred time",
            "validation": None,  # Validated by slot extractor and availability check
        },
        {
            "step": "rescheduling__confirmation",
            "next_step": None,  # Final step
            "required_slot": "confirmed",
            "prompt_hint": "Confirm rescheduling with explicit yes/no",
            "validation": lambda v: v and str(v).lower() in ["yes", "confirmed", "true"],
        },
    ],
    "inquiry": [
        {
            "step": "inquiry__question",
            "next_step": None,
            "required_slot": None,
            "prompt_hint": "Answer the user's question directly and professionally.",
            "validation": None,
        },
    ],
}


# Required slots for each intent (everything except 'confirmed')
# Used to validate flow completion before asking for final confirmation
REQUIRED_SLOTS_BY_INTENT: dict[str, list[str]] = {
    "booking": ["appointment_type", "date", "time", "symptoms"],
    "cancellation": ["appointment_id", "reason"],
    "rescheduling": ["appointment_id", "new_date", "new_time"],
    "inquiry": [],  # No slots required
    "greeting": [],  # No slots required
    "out_of_scope": [],  # No slots required
}


# Strict per-step tool allowlist.
# Used by the appointment_agent_node to reject tool calls that are
# not appropriate for the current flow step.
STEP_TOOL_ALLOWLIST: dict[str, set[str]] = {
    # Booking flow
    "booking__appointment_type": {"check_appointment_availability", "get_available_slots_for_date"},
    "booking__date": {"check_appointment_availability", "get_available_slots_for_date"},
    "booking__time": {"check_appointment_availability", "get_available_slots_for_date"},
    "booking__symptoms": set(),
    "booking__confirmation": {"create_appointment_in_db", "check_appointment_availability"},
    # Cancellation flow
    "cancellation__appointment_id": {"get_upcoming_appointments"},
    "cancellation__reason": set(),
    "cancellation__confirmation": {"cancel_appointment_in_db"},
    # Rescheduling flow
    "rescheduling__select_appointment": {"get_upcoming_appointments"},
    "rescheduling__new_date": {"check_appointment_availability", "get_available_slots_for_date"},
    "rescheduling__new_time": {"check_appointment_availability", "get_available_slots_for_date"},
    "rescheduling__confirmation": {"update_appointment_in_db", "check_appointment_availability"},
}


class StateInvariantError(Exception):
    """Raised when a state invariant is violated.
    
    Unlike assert, this cannot be disabled by Python's -O flag,
    ensuring safety checks remain active in production.
    """
    def __init__(self, phase: str, detail: str):
        self.phase = phase
        self.detail = detail
        super().__init__(f"CRITICAL: {phase} — {detail}")


def validate_state_invariants(state: AgentState, phase: str) -> None:
    """
    Centralized validation of state invariants.
    
    Args:
        state: Current agent state
        phase: Execution phase ("intelligence" or "business")
        
    Raises:
        StateInvariantError: If invariants are violated
    """
    user_id = state.get("user_id", 0)
    needs_name_enrichment = state.get("needs_name_enrichment", True)
    
    # Common invariant: Identity must be resolved
    if phase in ["intelligence", "business", "intent_guard"]:
        if user_id == 0:
            raise StateInvariantError(
                phase,
                f"user_id=0. Identity must be resolved before this phase."
            )
        
    if phase in ["intelligence", "business"]:
        if needs_name_enrichment:
            raise StateInvariantError(
                phase,
                f"needs_name_enrichment=True. Name gate must PASS before {phase} logic runs. user_id={user_id}"
            )

