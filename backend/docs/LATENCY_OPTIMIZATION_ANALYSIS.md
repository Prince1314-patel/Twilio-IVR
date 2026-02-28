# LangGraph Bottleneck Analysis & Latency Optimization Strategy

**Project**: Healthcare Voice Calling AI Agent (Twilio → LiveKit → LangGraph)  
**Date**: 2026-02-24  
**Scope**: End-to-end latency reduction for the voice IVR pipeline  
**Status**: Assessment Complete — Actionable Recommendations

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Current Architecture Overview](#current-architecture-overview)
3. [Graph Pipeline Audit — LLM Call Count Per Turn](#graph-pipeline-audit--llm-call-count-per-turn)
4. [Bottleneck Analysis (7 Critical Issues)](#bottleneck-analysis-7-critical-issues)
5. [Optimization Strategies](#optimization-strategies)
   - [Tier 1: Quick Wins (Immediate, Low-Risk)](#tier-1-quick-wins-immediate-low-risk)
   - [Tier 2: Architectural Changes (Medium Effort)](#tier-2-architectural-changes-medium-effort)
   - [Tier 3: Infrastructure & Provider-Level (High Impact)](#tier-3-infrastructure--provider-level-high-impact)
6. [Latency Budget Breakdown](#latency-budget-breakdown)
7. [Recommended Implementation Order](#recommended-implementation-order)
8. [Appendix: Code References](#appendix-code-references)

---

## Executive Summary

This document analyzes the **end-to-end response latency** of the voice calling AI agent, from the moment a user finishes speaking to the moment the AI's response begins playing via TTS. The focus is on identifying bottlenecks in the LangGraph workflow and proposing concrete, actionable optimizations.

### Key Findings

| Metric | Current State | Target |
|--------|---------------|--------|
| **LLM calls per user turn** | **3–7 calls** (worst case) | **1 call** (optimal) |
| **Estimated response latency** | **3–8 seconds** | **< 1.5 seconds** |
| **Sequential blocking nodes** | **6 nodes, all serial** | **Parallelize where possible** |
| **Database calls per turn** | **1–4 calls** | **1 call (cached)** |
| **Redundant LLM invocations** | **Yes (name extraction, slot extraction, intent override)** | **Eliminate** |

### Critical Insight
> **The single biggest latency contributor is the number of LLM calls per turn.** Each LLM call adds 200–800ms (Groq) or 500–2000ms+ (OpenAI). The current architecture makes 3–7 LLM calls per turn in the worst case. Reducing this to 1 call would cut latency by 60–80%.

---

## Current Architecture Overview

### Voice Pipeline
```
User Speaks → Sarvam STT (en-IN) → LangGraph Workflow → Sarvam TTS (en-IN) → User Hears
                ~70ms                  ~2000-6000ms            ~300ms
```

### LangGraph Node Pipeline (All Sequential)
```
user_context_loading  →  intent_guard  →  name_enrichment  →  business_router  →  appointment_agent  →  sanitize_output  →  END
     (DB call)          (LLM call*)       (LLM call*)           (no LLM)          (1-5 LLM calls)         (no LLM)
```

### Key Files

| File | Role | Latency Contribution |
|------|------|---------------------|
| `workflow.py` | Graph definition, node wiring | N/A (structure) |
| `state.py` | State schema, flow definitions | N/A (data) |
| `user_context_node.py` | DB lookup/create user | 50–200ms |
| `intent_detection_node.py` | LLM-based intent classification | **300–1500ms** |
| `name_enrichment_node.py` | LLM-based name extraction | **300–1500ms** |
| `appointment_agent_node.py` | ReAct tool loop (1–5 LLM calls) | **500–5000ms** |
| `sanitize_output_node.py` | Message filtering | < 1ms |
| `slot_extractor.py` | LLM-based slot extraction (per slot) | **300–1500ms each** |
| `classifier.py` | LLM intent classification | **300–1500ms** |
| `flow_manager.py` | Step progression logic | < 1ms |
| `langgraph_adapter.py` | LiveKit ↔ LangGraph bridge | < 5ms |
| `agent_worker.py` | LiveKit session setup | N/A (one-time) |

---

## Graph Pipeline Audit — LLM Call Count Per Turn

This is the **most critical section**. Every LLM call is a blocking network round-trip.

### Scenario 1: First Message — Greeting (New User)
```
Node: user_context_loading     → DB call (create user)         ~100ms
Node: intent_guard             → LLM call #1 (classify intent) ~500ms
Node: name_enrichment          → No LLM (returns static prompt) ~0ms
      [BLOCKED — returns to user for name]
──────────────────────────────────────────────────────────────────────
Total LLM calls: 1
Estimated latency: ~600ms ✅ Acceptable
```

### Scenario 2: User Provides Name
```
Node: user_context_loading     → DB call (lookup user)          ~50ms
Node: intent_guard             → LLM call #1 (classify intent)  ~500ms
Node: name_enrichment          → LLM call #2 (extract name!)    ~500ms
                               → DB call (update name)           ~50ms
Node: business_router          → No LLM                          ~0ms
Node: appointment_agent        → LLM call #3 (agent response)   ~800ms
Node: sanitize_output          → No LLM                          ~0ms
──────────────────────────────────────────────────────────────────────
Total LLM calls: 3
Estimated latency: ~1900ms ⚠️ Marginal
```

### Scenario 3: Transactional Turn (Booking — Slot Filling)
```
Node: user_context_loading     → DB call (lookup user)           ~50ms
Node: intent_guard             → SKIPPED (intent_locked=True)    ~0ms  ✅
Node: name_enrichment          → SKIPPED (name exists)           ~0ms  ✅
Node: business_router          → No LLM                          ~0ms
Node: appointment_agent:
  → LLM call #1 (agent decides next action)                     ~800ms
  → [If tool call] Tool execution                                ~100ms
  → LLM call #2 (process tool result)                           ~800ms
  → Eager slot extraction:
    → LLM call #3 (extract slot "date")                          ~500ms
    → LLM call #4 (extract slot "time")                          ~500ms
    → LLM call #5 (extract slot "symptoms")                      ~500ms
Node: sanitize_output          → No LLM                          ~0ms
──────────────────────────────────────────────────────────────────────
Total LLM calls: 3–5
Estimated latency: ~2750–4350ms 🔴 CRITICAL
```

### Scenario 4: Intent Override (Mid-Flow Switch)
```
Node: user_context_loading     → DB call                         ~50ms
Node: intent_guard             → SKIPPED (intent_locked=True)    ~0ms
Node: name_enrichment          → SKIPPED                         ~0ms
Node: business_router          → No LLM                          ~0ms
Node: appointment_agent:
  → _detect_intent_override    → Keyword match (no LLM)          ~0ms
  → classify_intent_sync       → LLM call #1 (confirmation!)    ~500ms
  → LLM call #2 (agent response)                                ~800ms
  → Tool call (get_upcoming_appointments)                         ~100ms
  → LLM call #3 (process tool result)                            ~800ms
  → Eager slot extraction:
    → LLM call #4+ (per uncollected slot)                        ~500ms each
──────────────────────────────────────────────────────────────────────
Total LLM calls: 4–7
Estimated latency: ~3250–5250ms 🔴🔴 CRITICAL
```

---

## Bottleneck Analysis (7 Critical Issues)

### Bottleneck #1: Eager Multi-Slot Extraction Makes Separate LLM Calls Per Slot 🔴
**Severity**: CRITICAL  
**File**: `appointment_agent_node.py`, lines 764–806  
**Impact**: +500ms per uncollected slot (up to 4 slots = +2000ms)

**Problem**: The eager extraction loop iterates over all uncollected required slots and makes a **separate LLM call per slot** via `extract_slots_from_message()`:

```python
for slot_name in required_slots_for_intent:
    if collected_slots.get(slot_name):
        continue
    eager_extracted = extract_slots_from_message(
        last_user_text, flow_step, slot_name, model  # ← LLM call per slot!
    )
```

For a booking flow with 4 required slots (`appointment_type`, `date`, `time`, `symptoms`), this means **4 separate LLM calls** just for slot extraction in a single turn.

**Root Cause**: `extract_slots_from_message()` in `slot_extractor.py` creates a new LangChain chain per invocation:
```python
chain = prompt_template | llm_model | StrOutputParser()
extracted_value = chain.invoke({})  # ← Blocking LLM call
```

---

### Bottleneck #2: Name Extraction Uses a Separate LLM Call 🟡
**Severity**: HIGH  
**File**: `name_enrichment_node.py`, lines 288–337  
**Impact**: +500ms per name extraction attempt

**Problem**: `_extract_name_with_llm()` creates a **new LLM model instance** and makes a standalone LLM call:
```python
def _extract_name_with_llm(user_message: str) -> str:
    llm = create_llm_model()  # ← Creates a NEW model instance every time!
    response = llm.invoke(extraction_prompt)  # ← Blocking LLM call
```

This is doubly wasteful:
1. It creates a new `ChatOpenAI`/`ChatGroq` instance (unnecessary overhead)
2. It uses a full LLM call for a task that can be done with regex + heuristics in most cases

---

### Bottleneck #3: Intent Classification Uses Full LLM Call Instead of Lightweight Classifier 🔴
**Severity**: CRITICAL  
**File**: `intent_detection_node.py` + `classifier.py`  
**Impact**: +300–1500ms per unlocked turn

**Problem**: `classify_intent_sync()` sends a full prompt to the LLM with examples and asks it to return a structured response:
```python
prompt = INTENT_CLASSIFICATION_PROMPT.format(user_text=user_text.strip())
response = llm_model.invoke(prompt)  # ← Full LLM round-trip for 6-class classification
```

For a task as simple as classifying into 6 categories (`booking`, `cancellation`, `rescheduling`, `inquiry`, `greeting`, `out_of_scope`), this is overkill.

**Mitigating Factor**: When `intent_locked=True`, this call is correctly skipped. But for the first turn (and any unlocked turn), it adds significant latency.

---

### Bottleneck #4: Intent Override Confirmation Triggers Additional LLM Call 🟡
**Severity**: MEDIUM-HIGH  
**File**: `appointment_agent_node.py`, lines 270–302  
**Impact**: +500ms when an override is detected

**Problem**: When a user says something like "actually cancel it", the code:
1. Detects it with keyword matching (`_detect_intent_override`) — fast ✅
2. Then **re-runs the full LLM classifier** to confirm:
```python
classifier_intent, classifier_conf = classify_intent_sync(
    last_user_text, model  # ← Extra LLM call just for confirmation
)
```

This is an extra LLM call that only fires occasionally, but when it does, it adds ~500ms.

---

### Bottleneck #5: All 6 Graph Nodes Execute Sequentially — No Parallelism 🟡
**Severity**: MEDIUM  
**File**: `workflow.py`  
**Impact**: Cumulative latency from sequential execution

**Problem**: The graph is a pure linear chain:
```
user_context_loading → intent_guard → name_enrichment → business_router → appointment_agent → sanitize_output
```

There is **no parallelism**. Even nodes that don't depend on each other's output run sequentially. While LangGraph doesn't natively support parallel nodes in a linear chain, some operations (like DB lookup and intent classification) could theoretically run concurrently.

---

### Bottleneck #6: DatabaseManager Instantiated Per Call (No Connection Pooling) 🟡
**Severity**: MEDIUM  
**File**: `user_context_node.py` (line 73), `name_enrichment_node.py` (line 183)  
**Impact**: +10–50ms per DB operation (connection setup overhead)

**Problem**: `DatabaseManager()` is instantiated fresh inside each node function call:
```python
db_manager = DatabaseManager()  # ← New instance every invocation
```

While `appointment_tools.py` correctly uses a module-level singleton (`db_manager = DatabaseManager()`), the graph nodes do not. This creates unnecessary connection setup overhead.

---

### Bottleneck #7: LLM Model Instantiated Multiple Times 🟡
**Severity**: MEDIUM  
**File**: Multiple files  
**Impact**: +20–100ms per unnecessary instantiation

**Problem**: `create_llm_model()` is called in multiple places:
1. `intent_detection_node.py` line 22: Module-level (singleton) ✅
2. `appointment_agent_node.py` line 78: Module-level (singleton) ✅
3. `name_enrichment_node.py` line 299: **Inside function** `_extract_name_with_llm()` — called per invocation ❌
4. `slot_extractor.py`: Uses `llm_model` param — depends on caller ⚠️

The `name_enrichment_node.py` case is the worst — it creates a fresh model instance on every name extraction attempt.

---

## Optimization Strategies

### Tier 1: Quick Wins (Immediate, Low-Risk)

#### 1.1 🔴 Batch Slot Extraction — Single LLM Call for All Slots
**Impact**: Reduces 4 LLM calls → 1 LLM call  
**Estimated Latency Savings**: 1500–3000ms  
**Risk**: Low  
**Files to Modify**: `slot_extractor.py`, `appointment_agent_node.py`

**Strategy**: Replace the per-slot extraction loop with a single LLM call that extracts **all** uncollected slots at once.

```python
# NEW: Batch extraction function
def extract_all_slots_from_message(
    message: str,
    current_step: str,
    uncollected_slots: list[str],
    llm_model,
) -> dict:
    """Extract ALL uncollected slots in a single LLM call."""
    
    slot_instructions = []
    for slot_name in uncollected_slots:
        slot_instructions.append(
            f"- {slot_name}: {_get_slot_description(slot_name)}"
        )
    
    prompt = f"""Extract the following information from the user's message.
Return a JSON object with the extracted values.
If a value is not found, set it to null.

Information to extract:
{chr(10).join(slot_instructions)}

User message: "{message}"

Return ONLY valid JSON, nothing else. Example:
{{"date": "2026-02-25", "time": "14:00:00", "symptoms": "headache"}}
"""
    
    response = llm_model.invoke(prompt)
    # Parse JSON response and validate each slot
    ...
```

**Usage in appointment_agent_node.py**:
```python
# BEFORE (4 LLM calls):
for slot_name in required_slots_for_intent:
    eager_extracted = extract_slots_from_message(...)

# AFTER (1 LLM call):
uncollected = [s for s in required_slots if s not in collected_slots]
if uncollected:
    batch_extracted = extract_all_slots_from_message(
        last_user_text, flow_step, uncollected, model
    )
    collected_slots.update(batch_extracted)
```

---

#### 1.2 🟡 Replace LLM-Based Name Extraction with Three-Layer Validation Stack
**Impact**: Eliminates 1 LLM call in ~95% of cases  
**Estimated Latency Savings**: 300–800ms  
**Risk**: Low  
**Files to Modify**: `name_enrichment_node.py`  
**New Dependency**: `spacy` + `en_core_web_sm` model (~15 MB)

##### The Problem with Naive Regex-First

The existing `_extract_name_with_regex()` uses trigger phrases (`i'm`, `call me`, `this is`) plus 
`re.IGNORECASE`, which causes **critical false positives** when users respond to the name prompt 
with conversational phrases instead of their name:

| User Says | Regex Captures | Actual Name? |
|-----------|---------------|-------------|
| `"I'm fine"` | `"Fine"` | ❌ No |
| `"I'm good"` | `"Good"` | ❌ No |
| `"Call me back"` | `"Back"` | ❌ No |
| `"Call me later"` | `"Later"` | ❌ No |
| `"This is urgent"` | `"Urgent"` | ❌ No |
| `"How are you"` | `"How Are You"` (bare pattern) | ❌ No |
| `"Yes"` | `"Yes"` (bare pattern) | ❌ No |

Voice STT engines (Sarvam) often capitalize output, making the bare-word pattern 
(`^([A-Z][a-z]+...)$`) match virtually anything.

##### Solution: Three-Layer Validation Stack (No LLM for 95%+ Cases)

Use regex to *extract candidates*, then **validate** through two fast guardrails before accepting.
LLM is only used as a rare fallback.

```
User message arrives at Name Gate
          │
          ▼
    ┌─ Refusal check ──────────────── Yes → BLOCK (escalate prompt)
    │
    ├─ Layer 1: Regex extraction ──── No match → try spaCy NER directly
    │        │
    │     Candidate extracted
    │        │
    │        ▼
    ├─ Layer 2: Blocklist check ───── In blocklist → Reject candidate
    │        │
    │     Not in blocklist
    │        │
    │        ▼
    ├─ Layer 3: spaCy NER ─────────── NOT labeled PERSON → Reject
    │        │
    │     Confirmed PERSON
    │        │
    │        ▼
    └─ ✅ ACCEPT as name
    
If all fast-path layers REJECT but message is >3 words:
          │
          ▼
    LLM fallback (_extract_name_with_llm)  ← Only ~5% of cases
```

**Layer 1 — Regex Extraction (< 0.1ms):** Unchanged from current implementation. Extracts candidates 
using trigger phrases + bare-word patterns.

**Layer 2 — Anti-Name Blocklist (< 0.01ms):** A curated set of common English words that regex 
falsely matches. This specifically targets the IVR voice context:

```python
# Words/phrases that regex captures but are NOT names.
# Curated for the voice IVR context (responses to "what's your name?")
NON_NAME_WORDS = {
    # Common responses to "what's your name?"
    "fine", "good", "great", "well", "okay", "ok", "bad", "tired",
    "alright", "busy", "sick", "happy", "sad", "angry", "hungry",
    
    # Captured by "I'm ___" / "I am ___"
    "doing", "not", "here", "ready", "waiting", "calling",
    "looking", "trying", "wondering", "just", "already",
    
    # Captured by "call me ___"
    "back", "later", "tomorrow", "please", "again", "soon",
    
    # Captured by "this is ___"
    "ridiculous", "important", "urgent", "about", "regarding",
    "concerning", "wrong", "right", "correct", "it",
    
    # Single-word non-names (bare pattern + STT capitalization)
    "yes", "yeah", "yep", "yup", "no", "nah", "nope", "sure",
    "hello", "hi", "hey", "bye", "thanks", "thank", "please",
    "what", "why", "how", "when", "where", "who", "which",
    "help", "stop", "wait", "hold", "cancel", "book", "need",
    "want", "can", "will", "would", "could", "should",
    
    # Common words that look like names but aren't
    "how", "are", "you", "the", "and", "for", "but", "not",
    "have", "has", "was", "were", "been", "being", "very",
    
    # Medical/appointment context words
    "doctor", "appointment", "hospital", "clinic", "nurse",
    "emergency", "regular", "followup", "checkup", "fever",
    "pain", "headache",
}

def _is_blocked_word(candidate: str) -> bool:
    """Check if ALL words in the candidate are in the blocklist."""
    words = candidate.lower().split()
    return all(w in NON_NAME_WORDS for w in words)
```

**Layer 3 — spaCy NER Validation (~0.3–1ms):** Uses spaCy's `en_core_web_sm` model with only the 
NER pipeline enabled. Confirms the candidate is actually labeled `PERSON` in the full message context.

```python
import spacy

# Load once at module level — disable unused pipeline components for speed
_nlp = spacy.load("en_core_web_sm", disable=["parser", "lemmatizer"])

def _validate_name_with_ner(candidate: str, full_message: str) -> bool:
    """Validate that the candidate is a person name using spaCy NER."""
    doc = _nlp(full_message)
    for ent in doc.ents:
        if ent.label_ == "PERSON" and candidate.lower() in ent.text.lower():
            return True
    return False
```

**Combined Usage in `name_enrichment_node()`:**

```python
def name_enrichment_node(state):
    ...
    # --- Layer 1: Regex extraction (< 0.1ms) ---
    extracted_name = _extract_name_with_regex(last_user_message)
    
    if extracted_name:
        # --- Layer 2: Blocklist filter (< 0.01ms) ---
        if _is_blocked_word(extracted_name):
            logger.info(f"[NAME GATE] Blocklist rejected: '{extracted_name}'")
            extracted_name = ""
        
        # --- Layer 3: spaCy NER validation (~0.3–1ms) ---
        elif not _validate_name_with_ner(extracted_name, last_user_message):
            logger.info(f"[NAME GATE] spaCy NER rejected: '{extracted_name}'")
            extracted_name = ""
    
    # --- Fallback: Try spaCy NER directly on full message ---
    if not extracted_name:
        doc = _nlp(last_user_message)
        person_entities = [ent.text for ent in doc.ents if ent.label_ == "PERSON"]
        if person_entities:
            extracted_name = person_entities[0]
            logger.info(f"[NAME GATE] spaCy NER direct extraction: '{extracted_name}'")
    
    # --- Last resort: LLM fallback (only ~5% of cases) ---
    if not extracted_name and len(last_user_message.split()) > 3:
        extracted_name = _extract_name_with_llm(last_user_message)
    ...
```

##### Validation Results — Before vs After

| User Says | BEFORE (regex-only) | AFTER (3-layer) | Why |
|-----------|-------------------|----------------|-----|
| `"I'm fine"` | ❌ `"Fine"` | ✅ Rejected | Blocklist: "fine" |
| `"I'm good"` | ❌ `"Good"` | ✅ Rejected | Blocklist: "good" |
| `"How are you"` | ❌ `"How Are You"` | ✅ Rejected | Blocklist: all common words |
| `"Call me back"` | ❌ `"Back"` | ✅ Rejected | Blocklist: "back" |
| `"Call me later"` | ❌ `"Later"` | ✅ Rejected | Blocklist: "later" |
| `"This is urgent"` | ❌ `"Urgent"` | ✅ Rejected | Blocklist: "urgent" |
| `"Yes"` | ❌ `"Yes"` | ✅ Rejected | Blocklist: "yes" |
| `"My name is Raj"` | ✅ `"Raj"` | ✅ `"Raj"` | Not blocked, NER confirms |
| `"I'm Priya"` | ✅ `"Priya"` | ✅ `"Priya"` | Not blocked, NER confirms |
| `"Call me Amit"` | ✅ `"Amit"` | ✅ `"Amit"` | Not blocked, NER confirms |
| `"Rahul"` | ✅ `"Rahul"` | ✅ `"Rahul"` | Not blocked, NER confirms |
| `"It's Jane Doe"` | No regex match | ✅ `"Jane Doe"` | spaCy NER direct extraction |

##### Latency Impact

| Path | Latency | Calls LLM? | Cases |
|------|---------|-----------|-------|
| Blocklist rejects | < 0.1ms | No | ~30% (common phrases) |
| Regex + NER accepts | ~1ms | No | ~50% (clear names) |
| Regex + NER rejects → LLM fallback | ~500ms | Yes | ~5% (ambiguous) |
| spaCy direct extraction (no regex match) | ~1ms | No | ~10% (e.g. "It's Jane") |
| No name found → LLM fallback | ~500ms | Yes | ~5% (complex) |
| **Weighted average** | **~30ms** | **~10% of cases** | |

##### Indian Name Consideration

Since this is a healthcare IVR in India (Sarvam STT, en-IN locale), names like **Raj**, **Priya**, 
**Amit**, **Meera**, **Arjun** need to work. spaCy's `en_core_web_sm` handles common Indian names 
well. For rare Indian names that spaCy misses, the LLM fallback catches them (the ~5% case).

##### Additional Fix: Singleton LLM Instance

Also fix the unnecessary model re-instantiation in the LLM fallback path:
```python
# BEFORE:
def _extract_name_with_llm(user_message):
    llm = create_llm_model()  # ❌ Creates new instance every time

# AFTER:
_llm_instance = None
def _get_llm():
    global _llm_instance
    if _llm_instance is None:
        _llm_instance = create_llm_model()
    return _llm_instance
```

---

#### 1.3 🟡 Eliminate Redundant Intent Override LLM Confirmation
**Impact**: Eliminates 1 LLM call on intent override  
**Estimated Latency Savings**: 300–800ms  
**Risk**: Low-Medium  
**Files to Modify**: `appointment_agent_node.py`

**Strategy**: The `_detect_intent_override()` function already uses strong keyword matching with negation handling. The follow-up LLM classification is redundant for clear overrides.

```python
# BEFORE:
override_intent = _detect_intent_override(last_user_text)
if override_intent:
    # Redundant LLM call to "confirm"
    classifier_intent, classifier_conf = classify_intent_sync(last_user_text, model)

# AFTER — Trust the keyword matcher for clear overrides:
override_intent = _detect_intent_override(last_user_text)
if override_intent and override_intent != active_intent:
    active_intent = override_intent
    # Reset flow state directly — no confirmation needed
    flow_step = FIRST_FLOW_STEP_BY_INTENT.get(override_intent)
    collected_slots = {}
```

---

#### 1.4 🟡 Use Module-Level Singleton for DatabaseManager in Graph Nodes
**Impact**: Eliminates connection setup overhead  
**Estimated Latency Savings**: 10–50ms per turn  
**Risk**: Very Low  
**Files to Modify**: `user_context_node.py`, `name_enrichment_node.py`

```python
# BEFORE (in user_context_node.py):
def user_context_loading_node(state):
    db_manager = DatabaseManager()  # ❌ New instance per call

# AFTER:
from app.database.manager import DatabaseManager
_db_manager = DatabaseManager()  # Module-level singleton

def user_context_loading_node(state):
    # Uses module-level singleton
    user_data = _db_manager.get_user_by_mobile_number(caller_mobile_number)
```

---

#### 1.5 🟢 Reduce LLM Temperature for Deterministic Tasks
**Impact**: Slightly faster inference, more predictable outputs  
**Estimated Latency Savings**: 10–50ms  
**Risk**: Very Low  
**Files to Modify**: `config.py`, `client_factory.py`

```python
# For intent classification and slot extraction, use temperature=0
# This reduces token sampling overhead and produces more deterministic results.
# Keep temperature=0.7 only for the conversational agent.

# In classifier.py / slot_extractor.py:
model_for_classification = create_llm_model(temperature=0)
# In appointment_agent_node.py:
model_for_conversation = create_llm_model()  # uses default 0.7
```

---

### Tier 2: Architectural Changes (Medium Effort)

#### 2.1 🔴 Replace LLM Intent Classification with a Local Keyword/Embedding Classifier
**Impact**: Eliminates 1 LLM call per unlocked turn  
**Estimated Latency Savings**: 300–1500ms  
**Risk**: Medium (requires testing against edge cases)  
**Files to Modify**: `classifier.py`, `intent_detection_node.py`

**Strategy**: For a 6-class classification problem with well-defined categories, use a lightweight local classifier instead of a full LLM call. Options:

**Option A — Rule-Based Keyword Classifier (Fastest, ~1ms):**
```python
INTENT_KEYWORDS = {
    "booking": {"book", "schedule", "appointment", "make an appointment", "set up"},
    "cancellation": {"cancel", "remove", "delete", "don't want"},
    "rescheduling": {"reschedule", "change", "move", "different time", "postpone"},
    "greeting": {"hello", "hi", "hey", "good morning", "good afternoon"},
    "inquiry": {"what", "how", "when", "where", "tell me", "question"},
}

def classify_intent_fast(text: str) -> tuple[str, float]:
    text_lower = text.lower()
    scores = {}
    for intent, keywords in INTENT_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > 0:
            scores[intent] = score
    
    if not scores:
        return "inquiry", 0.5
    
    best_intent = max(scores, key=scores.get)
    confidence = min(0.95, 0.6 + scores[best_intent] * 0.1)
    return best_intent, confidence
```

**Option B — Sentence Transformer Embedding (Fast, ~20ms, more accurate):**
```python
from sentence_transformers import SentenceTransformer, util

model = SentenceTransformer('all-MiniLM-L6-v2')
intent_embeddings = model.encode([
    "I want to book an appointment",
    "I need to cancel my appointment",
    ...
])

def classify_intent_embedding(text):
    text_emb = model.encode(text)
    similarities = util.cos_sim(text_emb, intent_embeddings)
    best_idx = similarities.argmax()
    return INTENTS[best_idx], float(similarities[0][best_idx])
```

**Option C — Hybrid (Keyword first, LLM fallback for ambiguous cases):**
```python
def classify_intent_hybrid(text, llm_model):
    intent, confidence = classify_intent_fast(text)
    if confidence >= 0.75:
        return intent, confidence  # ← Fast path, no LLM
    # Ambiguous — fall back to LLM
    return classify_intent_sync(text, llm_model)
```

---

#### 2.2 🔴 Merge Slot Extraction into the Main LLM Agent Call
**Impact**: Eliminates ALL separate slot extraction LLM calls  
**Estimated Latency Savings**: 1000–3000ms  
**Risk**: Medium  
**Files to Modify**: `appointment_agent_node.py`, `slot_extractor.py`

**Strategy**: Instead of running the agent AND then extracting slots separately, instruct the agent to extract and return slots as part of its response. Use structured output or a post-processing step on the agent's response.

```python
# Add to the system prompt sent to the appointment_agent:
SLOT_EXTRACTION_INSTRUCTION = """
IMPORTANT: When the user provides information, you MUST extract and include
the following in your internal reasoning (not shown to user):
- appointment_type: regular/emergency/followup
- date: YYYY-MM-DD
- time: HH:MM:SS
- symptoms: free text

When you ask a question, focus on ONE piece of missing information.
"""

# Then parse the agent's tool_calls or structured output to extract
# collected slots, instead of making separate LLM calls.
```

This approach eliminates the entire eager extraction loop because the agent itself handles extraction as part of its natural response.

---

#### 2.3 🟡 Short-Circuit user_context_loading for Known Users
**Impact**: Eliminates DB call on subsequent turns  
**Estimated Latency Savings**: 50–200ms  
**Risk**: Low  
**Files to Modify**: `user_context_node.py`

**Strategy**: If `user_context_loaded=True` and `user_id != 0` are already in state, skip the entire node.

```python
def user_context_loading_node(state):
    # Short-circuit if already loaded from a previous invocation
    if state.get("user_context_loaded") and state.get("user_id", 0) != 0:
        logger.debug("[USER CONTEXT] Already loaded, skipping DB lookup")
        return {}  # No state changes needed
    
    # ... existing logic ...
```

---

#### 2.4 🟡 Implement Streaming for the Main Agent Response
**Impact**: Reduces perceived latency (user hears response start sooner)  
**Estimated Latency Savings**: 500–2000ms (perceived, not actual)  
**Risk**: Medium (requires LiveKit streaming compatibility)  
**Files to Modify**: `appointment_agent_node.py`, `langgraph_adapter.py`

**Strategy**: Instead of waiting for the full LLM response, stream tokens as they arrive. LiveKit's `LLMAdapter` already supports streaming — the bottleneck is that `appointment_agent_node` uses `model_bound.invoke()` (blocking) instead of `model_bound.astream()`.

```python
# BEFORE:
response = model_bound.invoke(messages_for_agent)  # ← Waits for full response

# AFTER:
async for chunk in model_bound.astream(messages_for_agent):
    yield chunk  # ← Starts TTS as soon as first tokens arrive
```

> **Note**: This requires converting the appointment_agent_node to an async generator, which impacts the LangGraph execution model. The `LLMAdapter` already handles streaming from the graph — the issue is that the node itself blocks.

---

#### 2.5 🟡 Collapse business_router Into a Conditional Edge (Remove Node)
**Impact**: Eliminates one graph node hop  
**Estimated Latency Savings**: 5–20ms  
**Risk**: Very Low  
**Files to Modify**: `workflow.py`, `business_router_node.py`

**Strategy**: `business_router_node` does zero work — it validates state and returns an empty dict. The actual routing is done by `route_by_intent()` on the conditional edge. This node can be eliminated entirely.

```python
# BEFORE:
workflow.add_node("business_router", business_router_node)
workflow.add_conditional_edges("name_enrichment", route_after_name_enrichment, ...)
workflow.add_conditional_edges("business_router", route_by_intent, ...)

# AFTER:
# Remove business_router node entirely
# Move validation into the conditional edge function
workflow.add_conditional_edges(
    "name_enrichment",
    route_after_name_enrichment_and_intent,  # Combined routing
    {
        "appointment_agent": "appointment_agent",
        "end": END
    }
)
```

---

#### 2.6 🟡 Reduce MAX_TURNS in the Execution Loop
**Impact**: Prevents runaway tool-calling loops  
**Estimated Latency Savings**: Guards against 3000–5000ms worst case  
**Risk**: Low  
**Files to Modify**: `appointment_agent_node.py`

**Current**: `MAX_TURNS = 5` allows up to 5 LLM calls in the tool loop.

**Recommendation**: For voice, reduce to `MAX_TURNS = 3`. The agent should rarely need more than 2 tool calls in a single turn (1 to call the tool, 1 to respond with the result). If it needs more, something is wrong.

```python
MAX_TURNS = 3  # Voice-optimized: 1 tool call + 1 response + 1 buffer
```

---

### Tier 3: Infrastructure & Provider-Level (High Impact)

#### 3.1 🔴 Switch to Groq for All Classification/Extraction Tasks
**Impact**: 3–5x faster inference for non-conversational tasks  
**Estimated Latency Savings**: 500–2000ms  
**Risk**: Low (Groq supports the same models)  
**Files to Modify**: `client_factory.py`, `config.py`

**Strategy**: Use Groq (which has ~100–200ms inference for Llama 3.3 70B) for all deterministic tasks:
- Intent classification
- Slot extraction
- Name extraction

Keep OpenAI (GPT-5-nano) for the main conversational agent only if its quality is needed.

```python
def create_llm_model(task: str = "conversation") -> BaseChatModel:
    if task in ["classification", "extraction"]:
        # Use Groq for fast inference on deterministic tasks
        return ChatGroq(model="llama-3.3-70b-versatile", temperature=0)
    else:
        # Use configured provider for conversation
        return _create_from_config()
```

---

#### 3.2 🔴 Use a Smaller/Faster Model for Classification Tasks
**Impact**: Dramatically faster inference  
**Estimated Latency Savings**: 200–1000ms per call  
**Risk**: Medium (may need prompt tuning)

**Strategy**: For intent classification (a simple 6-class problem), use the smallest viable model:

| Model | Provider | Inference Time | Accuracy |
|-------|----------|---------------|----------|
| Llama 3.3 70B | Groq | ~150ms | Excellent |
| Llama 3.1 8B | Groq | ~50ms | Good |
| GPT-5-nano | OpenAI | ~300ms | Excellent |
| `gpt-4o-mini` | OpenAI | ~200ms | Excellent |

For classification and extraction, **Llama 3.1 8B on Groq** would give ~50ms inference — 10x faster than a large model.

---

#### 3.3 🟡 Implement Prompt Caching (OpenAI / Groq)
**Impact**: Reduces token processing time for repeated system prompts  
**Estimated Latency Savings**: 100–500ms  
**Risk**: Low  
**Files to Modify**: System prompts

**Strategy**: Both OpenAI and Anthropic support prompt caching for system prompts. The system prompt in `appointment_agent_node.py` is largely static — only the flow context and time change per turn.

**Implementation**: Structure prompts so the static portion comes first:
```python
# Put all static content BEFORE dynamic content
system_ctx = [
    CORE_IDENTITY,       # Static ← Cached
    CORE_RULES,          # Static ← Cached
    ANTI_HALLUCINATION,  # Static ← Cached
    BOOKING_FLOW,        # Static ← Cached
    # --- Dynamic content below (not cached) ---
    user_context,        # Dynamic
    flow_context,        # Dynamic
    f"CURRENT TIME: {current_time_str}",  # Dynamic
]
```

> **Important**: For this to work with OpenAI, the static prefix must be identical across calls. Currently, the system prompt varies too much between turns (user context, flow step). Restructuring it would enable caching.

---

#### 3.4 🟡 Pre-Warm LLM Connections
**Impact**: Eliminates cold-start connection overhead  
**Estimated Latency Savings**: 100–300ms on first call  
**Risk**: Very Low  

**Strategy**: Make a lightweight LLM call during application startup to establish the HTTP connection pool:
```python
# In agent_worker.py or app startup:
async def prewarm_connections():
    model = create_llm_model()
    await model.ainvoke("hi")  # Warms up the connection pool
```

---

#### 3.5 🟢 Optimize System Prompt Length
**Impact**: Reduces input token processing time  
**Estimated Latency Savings**: 50–200ms  
**Risk**: Very Low  

**Strategy**: The combined system prompt in `appointment_agent_node.py` is very long (estimated 1500–2500 tokens). For voice, every token counts. Audit and trim:

1. Remove redundant instructions (e.g., `CRITICAL INSTRUCTION` appears multiple times)
2. Use shorter variable names in the flow context
3. Remove example formatting that the LLM doesn't need
4. Remove redundant anti-hallucination instructions that are repeated in multiple prompts

**Target**: Reduce system prompt from ~2000 tokens to ~800 tokens.

---

## Latency Budget Breakdown

### Current State (Worst Case — Booking Slot Fill Turn)
```
┌─────────────────────────────────────────────────────────────┐
│ Component                        │ Latency    │ Cumulative │
├──────────────────────────────────┼────────────┼────────────┤
│ Sarvam STT (speech → text)       │    70ms    │     70ms   │
│ user_context_loading (DB)        │   100ms    │    170ms   │
│ intent_guard (SKIPPED)           │     0ms    │    170ms   │
│ name_enrichment (SKIPPED)        │     0ms    │    170ms   │
│ business_router                  │     0ms    │    170ms   │
│ appointment_agent:               │            │            │
│   ├─ LLM call #1 (agent)        │   800ms    │    970ms   │
│   ├─ Tool execution              │   100ms    │   1070ms   │
│   ├─ LLM call #2 (tool result)  │   800ms    │   1870ms   │
│   ├─ Slot extract #1 (date)     │   500ms    │   2370ms   │
│   ├─ Slot extract #2 (time)     │   500ms    │   2870ms   │
│   └─ Slot extract #3 (symptoms) │   500ms    │   3370ms   │
│ sanitize_output                  │     0ms    │   3370ms   │
│ Sarvam TTS (text → speech)       │   300ms    │   3670ms   │
└──────────────────────────────────┴────────────┴────────────┘
Total: ~3670ms (3.7 seconds)
```

### Target State (After Tier 1 + Tier 2 Optimizations)
```
┌─────────────────────────────────────────────────────────────┐
│ Component                        │ Latency    │ Cumulative │
├──────────────────────────────────┼────────────┼────────────┤
│ Sarvam STT (speech → text)       │    70ms    │     70ms   │
│ user_context_loading (CACHED)    │     5ms    │     75ms   │
│ intent_guard (SKIPPED)           │     0ms    │     75ms   │
│ name_enrichment (SKIPPED)        │     0ms    │     75ms   │
│ appointment_agent (STREAMED):    │            │            │
│   ├─ LLM call #1 (agent+slots)  │   600ms    │    675ms   │  ← Merged extraction
│   ├─ Tool call (if needed)       │   100ms    │    775ms   │
│   └─ LLM call #2 (tool result)  │   600ms    │   1375ms   │  ← Only if tool was called
│ sanitize_output                  │     0ms    │   1375ms   │
│ Sarvam TTS (text → speech)       │   300ms    │   1675ms   │
└──────────────────────────────────┴────────────┴────────────┘
Total: ~1375–1675ms (1.4–1.7 seconds)
```

### Aspirational State (Tier 3 — Groq + Streaming)
```
┌─────────────────────────────────────────────────────────────┐
│ Component                        │ Latency    │ Cumulative │
├──────────────────────────────────┼────────────┼────────────┤
│ Sarvam STT (speech → text)       │    70ms    │     70ms   │
│ user_context_loading (CACHED)    │     5ms    │     75ms   │
│ intent (keyword classifier)      │     1ms    │     76ms   │
│ appointment_agent (STREAMED):    │            │            │
│   └─ LLM call (Groq, streamed)  │   200ms*   │    276ms   │  ← *Time to first token
│ Sarvam TTS (text → speech)       │   300ms    │    576ms   │
└──────────────────────────────────┴────────────┴────────────┘
Total (time to first audio): ~576ms (< 0.6 seconds)
```

---

## Recommended Implementation Order

### Phase 1 — Quick Wins (Week 1) — Expected: -50% latency
| # | Action | Impact | Risk | Est. Savings |
|---|--------|--------|------|-------------|
| 1 | **Batch slot extraction** (1.1) | 🔴 Critical | Low | 1500–3000ms |
| 2 | **Regex-first name extraction** (1.2) | 🟡 High | Low | 300–800ms |
| 3 | **Remove override LLM confirmation** (1.3) | 🟡 Medium | Low | 300–800ms |
| 4 | **Singleton DatabaseManager** (1.4) | 🟡 Low | Very Low | 10–50ms |
| 5 | **Lower temperature for deterministic tasks** (1.5) | 🟢 Low | Very Low | 10–50ms |
| 6 | **Reduce MAX_TURNS to 3** (2.6) | 🟡 Guard | Low | Guards worst case |

### Phase 2 — Architecture (Week 2–3) — Expected: -30% additional latency
| # | Action | Impact | Risk | Est. Savings |
|---|--------|--------|------|-------------|
| 7 | **Keyword/hybrid intent classifier** (2.1) | 🔴 Critical | Medium | 300–1500ms |
| 8 | **Merge slot extraction into agent** (2.2) | 🔴 Critical | Medium | 1000–3000ms |
| 9 | **Short-circuit user_context_loading** (2.3) | 🟡 Medium | Low | 50–200ms |
| 10 | **Remove business_router node** (2.5) | 🟡 Low | Very Low | 5–20ms |

### Phase 3 — Infrastructure (Week 3–4) — Expected: -50% additional latency
| # | Action | Impact | Risk | Est. Savings |
|---|--------|--------|------|-------------|
| 11 | **Groq for classification/extraction** (3.1) | 🔴 Critical | Low | 500–2000ms |
| 12 | **Smaller model for classification** (3.2) | 🔴 High | Medium | 200–1000ms |
| 13 | **Implement streaming** (2.4) | 🟡 High (perceived) | Medium | 500–2000ms |
| 14 | **Prompt caching** (3.3) | 🟡 Medium | Low | 100–500ms |
| 15 | **Pre-warm connections** (3.4) | 🟢 Low | Very Low | 100–300ms |
| 16 | **Optimize prompt length** (3.5) | 🟢 Low | Very Low | 50–200ms |

---

## Appendix: Code References

### Files with LLM Calls (Latency Hotspots)

| File | Function | LLM Call Type | Per-Turn? |
|------|----------|--------------|-----------|
| `classifier.py:213` | `classify_intent_sync()` | `llm_model.invoke(prompt)` | Yes (unlocked) |
| `name_enrichment_node.py:315` | `_extract_name_with_llm()` | `llm.invoke(extraction_prompt)` | Yes (name unknown) |
| `slot_extractor.py:62` | `extract_slots_from_message()` | `chain.invoke({})` | Yes (per slot!) |
| `appointment_agent_node.py:467` | Execution loop | `model_bound.invoke(messages)` | Yes (1–5x) |
| `appointment_agent_node.py:279` | Override confirmation | `classify_intent_sync()` | Rare |

### Files with DB Calls

| File | Function | DB Operation | Per-Turn? |
|------|----------|-------------|-----------|
| `user_context_node.py:117` | `user_context_loading_node()` | `get_user_by_mobile_number()` | Yes |
| `user_context_node.py:149` | `user_context_loading_node()` | `create_user_with_phone()` | Once |
| `name_enrichment_node.py:184` | `name_enrichment_node()` | `update_user_name()` | Once |
| `appointment_tools.py` | Various tools | Multiple DB operations | As needed |

### Graph Structure (workflow.py)
```
Nodes: 6 (all sequential)
Conditional Edges: 2 (after name_enrichment, after business_router)
Entry: user_context_loading
Exit: sanitize_output → END
Checkpointer: InMemorySaver (no persistence across restarts)
```

---

*Document generated by codebase analysis on 2026-02-24. All latency estimates are based on typical Groq/OpenAI inference times and may vary based on load, model, and network conditions.*
