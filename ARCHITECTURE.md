# MultiMind AI — Architecture Deep Dive

## System Overview

MultiMind AI is an **integrity-aware autonomous orchestration system** that combines:

- **Cognitive layering** (supervisor → planner → workers → validator → reflection)
- **Memory governance** (provenance, trust decay, contradiction detection)
- **Knowledge Evolution** (tracks how organizational knowledge changes over time)
- **Explainable Confidence** (breakdown of confidence factors)
- **Adaptive Routing** (skips unnecessary agents for simple queries)
- **Multi-Tenant Architecture** (isolation between organizations)
- **Agent Memory Replay** (inspect workflow reasoning steps)
- **Enterprise Evaluation Engine** (automatic quality assessment)
- **Observability** (execution tracing, invariant enforcement, loop detection)

Unlike traditional agent frameworks that focus on capability, MultiMind AI enforces **semantic correctness boundaries** across all state transitions.

---

## Architecture Diagram

```
User Query
     ↓
[Planner Agent]
  ├─ PolicyStore (learns from past successes)
  ├─ RAG context retrieval (trust-weighted)
  └─ Output: task_plan [{id, type, description, priority}]
     ↓
[Supervisor Agent]
  ├─ Complexity detection (keywords + LLM classification)
  ├─ Retry tracking (max_retries per agent)
  ├─ Task index management
  └─ Routing: planner | research_agent | coder_agent | validator | END
     ↓  ↺
[Research Agent] ───────────────┐
  ├─ Tavily search (web)         │
  ├─ Format: title, URL, content │
  ├─ Store in RAG with           │
  │   provenance: agent="research" │
  └─ Output: research_data        │
     ↓                            │
[Coder Agent] ───────────────────┘
  ├─ Python REPL (safe exec)
  ├─ Capture stdout
  ├─ On success → store with validated=True
  └─ Output: code_result
     ↓
[Validator Agent]  ← Both paths converge here
  ├─ Retrieve relevant knowledge (trust-weighted)
  ├─ LLM evaluation (real, not stub):
  │  • Correctness
  │  • Relevance
  │  • Completeness
  │  • Hallucination risk
  ├─ Parse LLM JSON response
  ├─ Store validated research with confidence boost
  └─ Output: validation {is_valid, confidence, issues, suggestions}
     ↓
[Reflection Agent]
  ├─ Analyze: planning quality, retrieval effectiveness, execution efficiency
  ├─ Generate: planning_feedback, next_iteration_tips
  ├─ Store insights (agent="reflection")
  ├─ Synthesize final_answer from best available output
  └─ Output: reflection + final_answer
     ↓
[Memory Layer]
  ├─ SQLite: conversations, execution_history
  ├─ FAISS: vector store with:
  │  ├─ Per-chunk provenance (_agent, _session, _timestamp, _validated, _validation_score)
  │  ├─ Trust decay: trust = quality × age_decay × access_factor × validation_boost
  │  ├─ Age half-life: 30 days
  │  └─ Disk persistence (faiss_index/)
  └─ Contradiction detection (pre-insertion check)
     ↓
[Observability Layer]
  ├─ Trace per session (start → end)
  ├─ State snapshot at each agent boundary
  ├─ Invariant validation:
  │  • Required fields present
  │  • Task index in bounds
  │  • Confidence ∈ [0,1]
  │  • No infinite loops (state hash stability check)
  ├─ Progress tracking
  └─ Violation logging (error level)
     ↓
Final result returned to caller
```

---

## Layer Responsibilities

| Layer | Duties | Key Invariants |
|-------|--------|----------------|
| **Planner** | Decompose queries, reuse policies, log executions | `task_plan` non-empty if `planner_ran=True` |
| **Supervisor** | Route correctly, enforce retry limits, advance task index | `current_task_index ≤ len(task_plan)` |
| **Research** | Fetch via Tavily, store with `agent_source="research"` | `research_data` present on success |
| **Coder** | Execute Python, capture output, store successes | `code_result` present on success |
| **Validator** | Real LLM scrutiny (not stub) for correctness & relevance | `validation` present; `confidence ∈ [0,1]` |
| **Reflection** | Analyze workflow, generate insights, set `final_answer` | `final_answer` present; `reflection` complete |
| **Memory (RAG)** | Chunk, embed, store with provenance; compute trust; detect contradictions | Quality per chunk; metadata preserved; trust decay applied |
| **Observability** | Trace transitions, validate invariants, detect loops | All state changes logged; violations surfaced |

---

## Core Invariants (Enforced on Every Transition)

1. **Field Presence** — After each agent, its primary output field exists:
   - `research_agent` → `research_data`
   - `coder_agent` → `code_result`
   - `validator` → `validation` dict
   - `reflection` → `reflection` dict + `final_answer`

2. **Value Ranges** — Confidence and quality scores always ∈ [0, 1].

3. **Index Bounds** — `current_task_index` ∈ [0, len(task_plan)] (inclusive of completion state).

4. **Retry Sanity** — `retry_count` ≤ `max_retries` unless `next == "END"`.

5. **No Stagnation** — State hash must change after core agents (research, coder); repeated same agent without change → loop flag.

6. **Plan Consistency** — `planner_ran=True` implies non-empty `task_plan`.

7. **Terminal State** — `next == "END"` means workflow complete; no further transitions.

Any violation increments `trace.error_count` and logs an ERROR entry.

---

## Memory Governance Model

### Provenance Chain

Every knowledge chunk embeds metadata:

```python
{
  "_quality": 0.6,                    # intrinsic content score (0–1)
  "_hash": "abc123...",               # content fingerprint
  "_timestamp": 1715600000.0,          # creation epoch
  "_access_count": 3,                  # times retrieved
  "_agent": "validator",               # originating agent
  "_session": "a1b2c3d4",             # session id
  "_iteration": 2,                     # task plan index (if planned)
  "_validated": True,                  # passed through validator?
  "_validation_score": 0.92,           # validator's confidence
}
```

User-provided metadata keys can coexist but never overwrite reserved `_*` keys.

### Trust Decay Function

```
trust(t) = base_quality × age_decay(t) × access_factor(access_count) × validation_boost(validated)
```

where:
- `age_decay = 0.5 ** (age_days / 30)` → half-life 30 days
- `access_factor = min(1.0, 0.5 + access_count × 0.1)` → caps at 1.0 after 5 accesses
- `validation_boost = 1.0 + (0.5 × validation_score)` if validated, else 1.0

**Effect**: Old, never-accessed, or unvalidated knowledge naturally drifts toward 0. Frequently accessed and validated knowledge stays trustworthy.

### Contradiction Detection

On every `add_knowledge()`:
1. Perform similarity search for existing chunks above threshold (default 0.8 Jaccard word overlap)
2. Collect any highly similar existing chunks
3. **Currently**: returns list; future: automatic re-validation trigger

### Quality Reporting

`rag_memory.get_quality_report()` returns:
- `total_chunks` — FAISS vector count
- `average_trust` — mean of base quality proxy
- `min_trust`, `max_trust` — spread
- `agent_distribution` — counts per source agent (placeholder)
- `session_distribution` — counts per session (placeholder)
- `validated_chunks` — how many passed validator

---

## Observability Pipeline

### Trace Lifecycle

1. **Start** — `start_trace(session_id, **metadata)` creates `ExecutionTracer`, registers globally.
2. **Per-Agent** — `@trace_agent` wrapper:
   - Captures `prev_state` (shallow copy before agent)
   - Calls agent function (mutates state in-place)
   - Simulates state merge to produce `new_state` snapshot
   - Calls `tracer.record_transition(agent, prev, new, type)`
   - Invariant checks execute immediately
3. **Routing** — `@trace_routing` wrappers on conditional edges record decision outcomes.
4. **End** — `tracer.finalize(final_state)` stamps `end_time` and `final_state_hash`.
5. **Report** — `get_trace_report()` returns dict with snapshots, counts, loop events.
6. **Cleanup** — `close_trace(session_id)` removes from registry.

### Data Recorded Per Snapshot

```python
StateSnapshot(
    timestamp=float,
    agent=str,                  # "planner", "research", "coder", etc.
    state_hash=str,             # 16-char hash of critical fields
    state_summary={             # Condensed for storage efficiency
        "agent": next agent,
        "task_index": int,
        "retries": int,
        "has_research": bool,
        "has_code": bool,
        "validated": bool,
        "reflected": bool,
        "confidence": float|None,
        "quality": float|None,
    },
    transition_type=AGENT|CONDITIONAL|LOOP|ERROR|TERMINAL,
    message=str
)
```

### Loop Detection Logic

`ProgressTracker` tracks sequence of `(agent, state_hash)` pairs. If:
- same agent appears twice consecutively
- AND state hash unchanged (no meaningful mutation)
→ loop flag raised, `trace.loop_count` increments.

Exempt agents: `supervisor`, `planner`, `validator`, `reflection` (they often update only routing/metadata fields).

---

## Failure Modes & Defenses

| Failure Mode | Detection Mechanism | Recovery |
|--------------|--------------------|----------|
| **Fake validation** | Validator actually calls LLM and parses JSON | Fallback on JSON parse error with lowered confidence |
| **Memory quality mismatch** | Quality stored per-chunk in metadata; retrieval reads directly | Guarantees quality survives chunking |
| **Execution drift** | `current_task_index` used directly; no `-1` offset | Agent task_desc matches plan exactly |
| **Infinite loop** | `state_hash` unchanged after non-exempt agent | Logged; loop count increments |
| **State corruption** | Invariant checker runs on every transition | All violations logged as ERROR |
| **Retry runaway** | `retry_count` checked against `max_retries` | Supervisor routes to END when exceeded |
| **Knowledge poisoning** | Trust decay naturally reduces old unvalidated knowledge; contradiction detector flags duplicates | Manual review flag if low confidence |
| **Missing final answer** | Invariant requires `final_answer` after reflection | Guaranteed in success & exception paths |

---

## Policy Learning (Planner)

`PolicyStore` maintains learned plans keyed by query prefix (first 30 chars):

```python
policy_store = {
  "compare python web fram": {
    "tasks": [...],
    "success_count": 5
  },
  ...
}
```

On successful validation (`confidence > 0.7`), the current plan is stored/incremented. Next time a similar query arrives, the planner uses the learned policy as a baseline, then optionally refines with LLM. This enables **operational memory** — the system gets faster at recurring patterns.

---

## State Schema (SharedState TypedDict)

```python
class SharedState(TypedDict):
    # Core
    messages: Annotated[List[BaseMessage], add_messages]
    next: Optional[str]
    current_step: Optional[str]
    
    # Execution outputs
    task_type: Optional[str]
    research_data: Optional[str]
    code_result: Optional[str]
    final_answer: Optional[str]          # ← always populated by reflection
    
    # Validation
    validation: Optional[ValidationResult]  # {is_valid, confidence, issues, suggestions}
    
    # Retry control
    retry_count: int
    max_retries: int
    error: Optional[str]
    
    # Metadata
    requires_human_review: bool
    metadata: Dict[str, Any]            # carries session_id
    
    # Planner fields
    task_plan: Optional[List[Dict]]     # [{id, type, description, priority}]
    plan_reasoning: Optional[str]
    current_task_index: int
    planner_ran: bool
    
    # Reflection fields
    reflection: Optional[Dict]          # {workflow_quality, planning_feedback, ...}
    workflow_quality: float
```

---

## Execution Trace Example

```json
{
  "session_id": "a1b2c3d4",
  "start_time": 1715600000.0,
  "end_time": 1715600025.0,
  "duration_seconds": 25.0,
  "snapshots": [
    {
      "timestamp": 1715600001.0,
      "agent": "supervisor",
      "state_hash": "f1e2d3c4b5a6...",
      "state_summary": {"agent": "planner", "task_index": 0, "retries": 0, ...},
      "transition_type": "agent_transition",
      "message": "Routed to 'planner'"
    },
    {
      "timestamp": 1715600005.0,
      "agent": "planner",
      "state_hash": "a1b2c3d4e5f6...",
      "state_summary": {"agent": "supervisor", "task_index": 0, "retries": 0, ...},
      "transition_type": "agent_transition",
      "message": "Agent planner produced updates ['task_plan', 'plan_reasoning']"
    },
    ...
  ],
  "loop_count": 0,
  "error_count": 0,
  "final_state_hash": "zzzzzzzz...",
  "progress": {
    "agent_visits": {"supervisor": 3, "planner": 1, "research": 1, "validator": 1, "reflection": 1},
    "total_steps": 8,
    "potential_loops": []
  }
}
```

---

## Governance Metrics

After each run, MultiMind AI prints:

```
[Observability] Session <id>: 7 transitions, 0 violations, 0 loops detected
[Memory Governance Report]
  Total knowledge chunks: 47
  Average trust score: 0.62
  Trust range: [0.31, 0.94]
```

**Interpretation**:
- **Transitions** = agent + routing boundary crossings
- **Violations** = invariant breaches (should be 0 in correct operation)
- **Loops** = same agent twice without state change (possible infinite loop)
- **Trust score** = decayed, access-stabilized, validation-boosted quality

---

## Design Trade-offs

| Decision | Rationale |
|----------|-----------|
| **Per-chunk quality** | Enables fine-grained trust; avoids full-document averaging which loses local structure |
| **Exponential decay (30d half-life)** | Knowledge naturally becomes stale; prevents memory pollution from outdated facts |
| **Validation boost (+50%)** | External verification is a strong signal; rewards validated knowledge |
| **Access count stabilization** | Frequently retrieved knowledge is likely useful; prevents decay of popular facts |
| **Invariant check on every transition** | Fail-fast principle; catches corruption early before propagation |
| **Trace snapshots as summaries** | Full state would be too large; critical fields only balance insight vs size |
| **Word-overlap contradiction detection** | Lightweight; no extra embedding calls; can upgrade to cosine similarity later |
| **State hash excludes messages** | Messages can be large & variable; critical is agent decisions & indices |

---

## Extensibility Points

1. **New Agent** — Add function with `@trace_agent("name")`, return dict merging into state. Ensure invariant checker knows about any new required output fields.
2. **New Invariant** — Add static method to `InvariantChecker`, call from `validate_transition`.
3. **Custom Trust Function** — Override `compute_trust_score` or inject via dependency injection.
4. **Contradiction Resolution** — Currently detects; next step: auto-revalidate when contradiction score > threshold.
5. **Policy Store Backend** — Currently in-memory dict; replace with Redis/SQLite for persistence across restarts.
6. **Trace Export** — Implement ` ExecutionTracer.export_trace(filepath)` (skeleton exists).

---

## Known Non-Blocking Issues

- **401 Unauthorized** from OpenAI/Tavily when using placeholder `.env` keys → requires real API keys for live runs
- **Tavily deprecation** → upgrade to `langchain-tavily` package (`pip install langchain-tavily`)
- **Pydantic V1 warning** on Python 3.14 → benign; upstream library compatibility forthcoming
- **Contradiction detection** uses Jaccard word overlap; semantic equivalence needs embedding cosine (future upgrade)
- **Memory report** uses proxy `knowledge_scores` dict; full docstore iteration possible but memory-intensive

---

## Quick Start (Developer)

```python
from graph import app
from memory import memory, rag_memory

# Simple research
input_data = {
    "messages": [HumanMessage(content="What is LangGraph?")],
    "task_type": "research",
    "retry_count": 0,
    "max_retries": 3,
    "metadata": {"session_id": "demo-123"},
    "planner_ran": False,
    "task_plan": None,
    "reflection": None
}

result = app.invoke(input_data)
print(result["final_answer"])

# Check memory governance
print(rag_memory.get_quality_report())
```

---

## Philosophy

MultiMind AI is built on these principles:

1. **Capability without integrity is danger** — a validator that always passes is worse than no validator.
2. **State is the source of truth** — if state gets corrupted, all agents inherit the corruption.
3. **Observability is not optional** — autonomous systems must be traceable to be trustworthy.
4. **Memory must govern itself** — unchecked knowledge accumulation leads to pollution and hallucination cascades.
5. **Invariants are the guardrails** — they define the correctness envelope; violating them means the system has left the building.

This is not just another agent demo. It's a **cognitive runtime with integrity guarantees**.

---

*MultiMind AI — Where autonomous systems learn to tell the truth.*
