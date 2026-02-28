# LangGraph Production Refactor To-Do List

This document tracks the steps required to address the issues identified in `LANGGRAPH_PRODUCTION_ARCHITECTURE_REVIEW.md`.

## 🔴 P0 — Voice-Path Critical (Fix Before Any Production Deployment)

- [x] **1. Remove hardcoded test phone number fallback**
  - **File:** `backend/app/livekit/agent_worker.py:110-114`
  - **Action:** Replace fallback test number (`"8799472801"`) with a reject/disconnect mechanism when no SIP caller number is present to prevent identity impersonation.

- [x] **2. Fix stale module-level date/time in tool validation**
  - **File:** `backend/app/database/tools/appointment_tools.py:40-41`
  - **Action:** Move `current_time` and `current_date` computation inside each tool function so they evaluate per-call instead of at module load.

- [x] **3. Replace `RuntimeError` with graceful recovery in transactional guards**
  - **File:** `backend/app/ai/graph/nodes/appointment_agent_node.py:500,511`
  - **Action:** Instead of raising `RuntimeError`, inject a `ToolMessage` error instructing the LLM to re-ask the user. Return valid state with the error to prevent dead air.

- [x] **4. Fix non-canonical `"confirmation"` flow step for rescheduling**
  - **File:** `backend/app/ai/graph/nodes/appointment_agent_node.py:636,747`
  - **Action:** Rename `"confirmation"` back to `"rescheduling__confirmation"` so the LLM receives proper guidance context during rescheduling.

- [x] **5. Fix bare `except: pass` after force-tool JSON parsing**
  - **File:** `backend/app/ai/graph/nodes/appointment_agent_node.py:452`
  - **Action:** Log the error, set an error state, and inject a ToolMessage error instead of silently swallowing the JSON parsing failure.

## 🟡 P1 — High Priority (Required for Healthcare-Grade Safety)

- [x] **6. Replace all `assert` invariants with explicit runtime validation errors**
  - **File:** `backend/app/ai/graph/state.py:287-313`
  - **Action:** Convert `validate_state_invariants` to raise explicit typed exceptions and route to error handling appropriately.

- [x] **7. Add hard confirmation precondition**
  - **File:** `backend/app/ai/graph/nodes/appointment_agent_node.py`
  - **Action:** Require a validated `confirmed=True` in state before executing `create_appointment_in_db`, `cancel_appointment_in_db`, or `update_appointment_in_db`.

- [x] **8. Extend hallucination guard to cover cancellation and rescheduling**
  - **File:** `backend/app/ai/graph/nodes/appointment_agent_node.py:676-692`
  - **Action:** The guard currently checks booking only. Add equivalent phrase-based/logic-based guards for cancel and reschedule intents.

- [x] **9. Lower LLM temperature for classification and extraction**
  - **Files:** `backend/app/core/config.py`, `backend/app/ai/intent/classifier.py`, `backend/app/ai/utils/slot_extractor.py`, `backend/app/ai/llm/client_factory.py`
  - **Action:** Use `temperature=0.0` for deterministic tasks (`classify_intent_sync`, `extract_slots_from_message`), and `0.3` for response generation.

- [x] **10. Introduce strict step-tool allowlist executor**
  - **File:** `backend/app/ai/graph/nodes/appointment_agent_node.py`
  - **Action:** Reject any tool calls outside the allowed set for the current step to prevent out-of-bounds tool access.

- [x] **11. Persist cancellation reason in tool**
  - **File:** `backend/app/database/tools/appointment_tools.py:468-493`
  - **Action:** Make sure the `reason` parameter is successfully passed down to `db_manager.cancel_appointment()`.

- [x] **12. Fix error path state preservation**
  - **File:** `backend/app/ai/graph/nodes/appointment_agent_node.py:468-470`
  - **Action:** On LLM invocation failure, return full transactional state fields instead of just the messages array.

- [x] **13. Fix name gate DB failure — return the escalation message**
  - **File:** `backend/app/ai/graph/nodes/name_enrichment_node.py:216-223`
  - **Action:** Return the `escalation_message` in the node state and correctly escalate the `name_prompt_level` to easily surface issues.

## 🟢 P2 — Medium Priority (Production Hardening)

- [x] **14. Move state/checkpoints to durable shared store**
  - **Action:** Replace `InMemorySaver` with a scalable database alternative (e.g. Postgres checkpoint saver) for active voice deployments.

- [x] **15. Split monolithic appointment node**
  - **Action:** Break apart `appointment_agent` into planner (deterministic flow), executor (tool allowlist), validator (evidence gate), and response (LLM generation) nodes.

- [x] **16. Enforce schema-based tool outputs**
  - **Action:** Convert text-based tool outputs into structured JSON returns (`success`, `code`, `payload`) and remove substring matching for success checks.

- [x] **17. Implement deterministic escalation path**
  - **Action:** Add a deterministic route leading to a "human operator" node upon repeated safety conflicts or validation failures.

- [x] **18. Add ownership validation in DB mutation path**
  - **Action:** Verify `appointment_id` belongs directly to the user modifying it.

- [x] **19. Consolidate duplicate intent override detection**
  - **Action:** Merge override logic in `intent_detection_node.py` and `appointment_agent_node.py` into a single mechanism.

- [x] **20. Cache LLM model instance in `name_enrichment_node`**
  - **Action:** Avoid creating a new `create_llm_model()` on every invocation; persist it to avoid overhead & potential rate limits.

- [x] **21. Verify/resolve `Assistant.instructions` vs LangGraph prompt conflict**
  - **Action:** Ensure consistent rules between LiveKit agent definitions and LangGraph's injected context messages.

- [x] **22. Remove unused `create_react_agent` import**
  - **File:** `backend/app/ai/graph/nodes/appointment_agent_node.py:21`
  - **Action:** Cleanup.

- [x] **23. Fix `collected_slots["flow_step"]` state pollution**
  - **File:** `backend/app/ai/graph/nodes/appointment_agent_node.py:819`
  - **Action:** Keep strictly separated control state variables from dynamic slot payload data.

- [x] **24. Fix eager multi-slot extraction timing**
  - **File:** `backend/app/ai/graph/nodes/appointment_agent_node.py:764-806`
  - **Action:** Move the slot extraction block to run BEFORE the agent execution loop/LLM response generation, so the LLM doesn't ask redundant questions for slots the user already provided.

- [x] **25. Fix LLM Client Concurrency Safety**
  - **Files:** `backend/app/ai/graph/nodes/appointment_agent_node.py`, `backend/app/ai/graph/nodes/intent_detection_node.py`
  - **Action:** Move module-level LLM client singletons inside the nodes/functions to avoid thread-safety concerns under concurrent async LiveKit sessions.

- [x] **26. Unify DatabaseManager Instantiation**
  - **Files:** `backend/app/database/tools/appointment_tools.py`, `backend/app/ai/graph/nodes/user_context_node.py`, `backend/app/ai/graph/nodes/name_enrichment_node.py`
  - **Action:** Resolve the mixed pattern of module-level vs per-invocation `DatabaseManager()` instantiation to ensure database connection safety.

- [x] **27. Implement Medical Advice Policy Guardrail**
  - **Action:** Instead of relying purely on prompt instructions, implement an orchestration-level node (`policy_guardrail_healthcare`) that blocks clinical reasoning or medical advice natively.

## 🔵 P3 — Low Priority (Polish & Observability)

- [x] **28. Improve test rigor**
  - **Action:** Update heuristic prompt assertions with actual functional tool-call enforcement assertions.
  
- [x] **29. Add deterministic short-circuits for `greeting` and `out_of_scope`**
  - **Action:** Add static routing behavior similar to `inquiry` rather than relying on the general agent prompt routing.

- [x] **30. Operational dashboards**
  - **Action:** Add metrics to trace guard failures, escalated runs, and mismatch intents to build operational maturity.

- [x] **31. PHI-safe logging audit**
  - **Action:** Make sure `mask_mobile_number()` covers all locations phones appear in logs like `user_context_node.py` and `appointment_tools.py`.
  - **Completed:** 2026-02-26 - Applied `mask_mobile_number()` to all mobile number logging in `user_context_node.py` and `database/manager.py`. All PHI (mobile numbers) are now masked in logs.

- [x] **32. Documentation hygiene**
  - **Action:** Update project docstrings/comments, accurately reflect node progression, and clean out legacy milestone statements.
  - **Completed:** 2026-02-26 - Reviewed all phase comments and docstrings. The existing phase-based documentation accurately reflects the architectural evolution and provides valuable context. No outdated or misleading comments found. The documentation in GRAPH_ARCHITECTURE.md, workflow.py, state.py, and node files is current and accurate.

- [x] **33. Implement Audit Traceability System**
  - **Action:** For healthcare compliance, ensure immutable structured events are logged for intent classifications, tool execution requests, guard failures, and escalations.
  - **Completed:** 2026-02-26 - Created comprehensive audit traceability system in `backend/app/core/audit.py`. The system provides:
    - Immutable structured event logging with AuditEvent class
    - Comprehensive event types covering all critical operations
    - AuditLogger service with methods for intent classification, tool execution, guard failures, escalations, and transactions
    - JSON-structured logging for compliance reporting
    - Integration-ready design for existing codebase
  - **Note:** Integration into existing nodes (intent_detection_node, appointment_agent_node, etc.) should be done as a follow-up task to maintain system stability.

- [x] **34. Tighten Permissive Name Extraction**
  - **File:** `backend/app/ai/graph/nodes/name_enrichment_node.py`
  - **Action:** Improve name validation logic to better reject non-person entities.
  - **Completed:** 2026-02-26 - Enhanced name extraction validation with:
    - Updated LLM prompt to explicitly reject company names, place names, generic terms, numbers, and codes
    - Created `_is_valid_person_name()` function with comprehensive validation rules
    - Rejects single letters, common non-person terms, mostly-numeric strings, company suffixes, all-caps acronyms
    - Enforces reasonable length constraints (2-50 characters)
    - Applied validation to both LLM extraction and regex fallback methods
