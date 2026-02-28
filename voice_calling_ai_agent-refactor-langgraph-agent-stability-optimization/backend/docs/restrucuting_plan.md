Below is a **phase-wise, execution-ready restructuring plan** that realigns your LangGraph system **exactly** to `plan.md`, while **reusing maximum existing code** and **eliminating over-engineering**.
This is written as a **technical delivery plan**, not conceptual advice.

---

# LangGraph Restructuring Plan

**Objective:** Enforce deterministic IVR onboarding, simplify graph control, and isolate business logic — without rewriting the system.

---

## Guiding Constraints (Non-Negotiable)

Before phases, lock these invariants:

1. **User identity resolution must be Step 0**
2. **Name validation is a hard gate**
3. **Intent detection only runs after onboarding**
4. **Appointment agent assumes identity is complete**
5. **Graph controls flow — nodes do not**

---

# PHASE 0 — Stabilization & Guardrails (Pre-Refactor) ✅ COMPLETE

**Goal:** Prevent regressions while restructuring.

**Status:** ✅ Completed on 2026-02-09

### To-Dos

* [x] Freeze feature development
* [x] Add logging at graph entry + exit
* [x] Add debug log for:

  * `user_id`
  * `needs_name_enrichment`
  * `intent`
* [x] Add temporary assertion:

  * `appointment_agent_node` **must not run** if `user_id == 0`

> Outcome: Safe refactor surface with observability. ✅

**Implementation Summary:**
- Added comprehensive graph entry/exit logging to `entrypoint.py`
- Implemented safety assertion in `appointment_agent_node.py` to block execution when `user_id == 0`
- Enhanced debug logging in all nodes (`user_context_node.py`, `name_enrichment_node.py`, `intent_detection_node.py`)
- Created test suites (`test_phase0_assertions.py`, `test_phase0_logging.py`)
- Fixed 2 existing tests to comply with new assertion requirements
- All regression tests passing

---

# PHASE 1 — Redefine the Mental Model in Code ✅ COMPLETE

**Goal:** Encode the plan’s mental model explicitly in the graph.

**Status:** ✅ Completed on 2026-02-09

### Target Phases in Graph

```
ENTRY
 → USER_RESOLUTION
 → NAME_GATE (blocking)
 → INTENT_DETECTION
 → BUSINESS_ROUTER
 → APPOINTMENT_AGENT
 → END
```

### To-Dos

* [x] Write this phase diagram into a README or docstring
* [x] Stop thinking in “agents”; think in **state transitions**
* [x] Treat onboarding as **infrastructure**, not AI logic

> Outcome: Clear ownership of responsibility per node. ✅

**Implementation Summary:**
- Created comprehensive `GRAPH_ARCHITECTURE.md` with phase diagrams, mental model principles, and migration roadmap
- Enhanced `workflow.py` docstring with current vs. target architecture documentation
- Enhanced `state.py` docstring with state lifecycle and ownership model
- Added mental model comments to all 5 node files explaining current vs. target roles
- All documentation consistent with `plan.md` and aligned with restructuring objectives
- No functional code changes (documentation only)

---

# PHASE 2 — Restructure Graph Entry (Most Critical) ✅ COMPLETE

**Goal:** Establish identity-first architecture with mandatory name collection.

**Status:** ✅ Completed on 2026-02-09

## Target

Entry **must** start at user resolution.

### To-Dos

* [x] Change graph entry point to `user_context_loading`
* [x] Remove `sentiment_analysis` and `intent_detection` from entry path
* [x] Ensure `caller_mobile_number` is mandatory at graph invocation
* [x] Implement escalating name collection prompts (5 levels)
* [x] Add refusal detection for graceful handling
* [x] Make name enrichment a true blocking gate
* [x] Update appointment prompts to remove name collection

### Resulting Entry State Guarantee

After Phase 2:

* `user_id` always exists OR explicitly failed
* `user_profile` always exists (possibly partial)
* `needs_name_enrichment` is authoritative
* `caller_mobile_number` is validated at entry point
* Name collection blocks all downstream processing

> Outcome: Identity-first system. ✅

**Implementation Summary:**
- Changed graph entry point from `sentiment_analysis` to `user_context_loading`
- Implemented 5-level escalating name collection prompts with refusal detection
- Added `name_prompt_level` field to state schema for tracking escalation (0-5)
- Implemented mandatory `caller_mobile_number` validation with format checking
- Updated conditional routing: name gate now routes to `sentiment_analysis` (PASS) or `END` (BLOCK)
- Removed name collection from appointment booking flow
- Updated appointment prompts to assume user identity is established
- Graph flow now: `user_context_loading` → `name_enrichment` (NAME GATE) → `sentiment_analysis` → `intent_detection` → `appointment_agent`

---

# PHASE 3 — Convert Name Enrichment into a True Gate ✅ COMPLETE

## Current Anti-Pattern

* Name logic spread across:

  * user context node
  * name enrichment node
  * appointment agent

## Target Pattern

**Single blocking gate node**.

### New Responsibility of Name Gate

* Decide **only one thing**:

  * “Can we proceed, or must we stop and ask for name?”

### To-Dos

* [x] Rename conceptual role: `name_enrichment_node` → **NameGate**
* [x] Remove greeting logic from appointment agent
* [x] Move all “did we ask already?” logic into NameGate
* [x] NameGate outputs:

  * `BLOCK` → graph ends (waiting for user input)
  * `PASS` → intent detection

### Explicit Rules

* NameGate:

  * ❌ does NOT know intent
  * ❌ does NOT know sentiment
  * ✅ only enforces name existence

> Outcome: Deterministic onboarding that exactly matches `plan.md`. ✅

**Implementation Summary:**
- Renamed conceptual role of `name_enrichment_node` to **NameGate** in comments and logs
- Refactored `name_enrichment_node` to return explicit `BLOCK` (name_collection_in_progress=True) or `PASS` signals
- Consolidated all name collection logic (including "did we ask already?") into NameGate
- Updated `workflow.py` conditional routing to explicitly handle NameGate outputs
- Removed all greeting logic and name detection heuristics from `appointment_agent_node`
- Verified NameGate strict blocking and Appointment Agent pure business logic with new test suite `test_phase3_gates.py`

---

# PHASE 4 — Reorder Sentiment & Intent (De-risk Intelligence) ✅ COMPLETE

## Correct Order

1. Identity resolved
2. Name resolved
3. **Then** intelligence

**Status:** ✅ Completed on 2026-02-09

### To-Dos

* [x] Move `sentiment_analysis` after NameGate PASS
* [x] Move `intent_detection` immediately after sentiment
* [x] Remove any onboarding checks from intent logic
* [x] Ensure intent node assumes:

  * `user_id != 0`
  * `name exists`
* [x] Add safety assertions to enforce identity-first architecture

### Optional Optimization

* [ ] Defer sentiment entirely for non-frustrated flows later

> Outcome: AI runs only when it has full context. ✅

**Implementation Summary:**
- Added Phase 4 safety assertions to `sentiment_node.py` verifying `user_id != 0` and `needs_name_enrichment = False`
- Added Phase 4 safety assertions to `intent_detection_node.py` with same identity checks
- Updated MENTAL MODEL docstrings in both nodes to reflect Phase 4 completion
- Updated `workflow.py` docstring to document Phase 4 changes
- Created comprehensive test suite `test_phase4_intelligence.py` with 8 test cases
- Graph flow already correctly ordered from Phase 2/3 (sentiment/intent run after NameGate PASS)

---

# PHASE 5 — Introduce a Business Router (Lightweight) ✅ COMPLETE

## Problem Today

* Appointment agent internally branches on intent
* Graph has no semantic awareness of business paths

## Target

Graph-level intent routing.

**Status:** ✅ Completed on 2026-02-09

### To-Dos

* [x] Add `business_router_node` (pure logic, no LLM)
* [x] Route based on `intent`:

  * booking
  * cancellation
  * reschedule
* [x] Initially route **all** to existing appointment agent

> This is future-proofing, not scope creep.

> Outcome: Graph owns control flow; agent owns execution.

---

# PHASE 6 — Slim Down Appointment Agent (Major Payoff) ✅ COMPLETE

## Current State

Appointment agent is overloaded.

## Target State

Appointment agent assumes:

* User exists
* Name exists
* Intent exists
* Context exists

**Status:** ✅ Completed on 2026-02-09

### To-Dos

* [x] Remove:

  * Name greeting logic
  * Name detection heuristics
  * Onboarding assumptions
* [x] Keep:

  * Tool calling
  * Confirmation loops
  * Slot validation
* [x] Treat appointment agent as a **pure executor**

### Rule

> If the appointment agent checks `needs_name_enrichment`, the graph is wrong.

> Outcome: Clean, testable business logic.

---

# PHASE 7 — Simplify State Schema

## Problem

State contains transitional flags that leak across phases.


**Status:** ✅ Completed on 2026-02-09

### To-Dos

* [x] Classify state fields:

  * **Infrastructure**: user_id, mobile_number
  * **Onboarding**: needs_name_enrichment
  * **Business**: intent, appointment data
* [x] Ensure onboarding fields are never read past NameGate
* [x] Lock `user_id` as immutable post Phase 2

> Outcome: Predictable state lifecycle.

**Implementation Summary:**
- Refactored `AgentState` in `state.py` into composed `InfrastructureState`, `OnboardingState`, and `BusinessState` TypedDicts
- Implemented `validate_state_invariants` function to centralize validation logic
- Updated `sentiment_node`, `intent_detection_node`, `business_router_node`, and `appointment_agent_node` to use centralized validation
- Verified strict state enforcement with `test_phase7_state_schema.py` and updated regression tests

---

# PHASE 8 — Validation Against plan.md (Hard Check)

**Status:** ✅ Completed on 2026-02-09

### Explicit Checks

* [x] Phone number always resolves to user_id
* [x] Name gate blocks ALL flows
* [x] Intent detection never runs before onboarding
* [x] Appointment creation never happens without name
* [x] Cancel/reschedule always fetch appointments first

> Outcome: 100% Validated against Plan.

**Implementation Summary:**
- Created comprehensive validation suite `tests/test_phase8_final_validation.py`
- Implemented 5 specific test cases corresponding directly to the requirements
- Verified all 5/5 hard checks PASS
- Confirmed system is fully aligned with `restructuring_plan.md` architecture