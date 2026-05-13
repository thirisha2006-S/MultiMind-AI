# MultiMind AI — Autonomous Cognitive Workflow System

A production-grade multi-agent system featuring **Planner + Orchestration + Validation + Reflection + Memory Governance** architecture — enabling self-improving, integrity-aware autonomous AI.

## 🏗️ Architecture Overview

```
[User Input]
     ↓
[Planner Agent] → Task decomposition & policy learning
     ↓
[Supervisor Agent] → Semantic routing + complexity detection
     ↓
[Worker Agents] → Research/Coding with RAG + provenance
     ↓
[Validator Agent] → LLM-based fact-checking & hallucination detection
     ↓
[Reflection Agent] → Workflow analysis, learning, final synthesis
     ↓
[Memory Layer] → SQLite + FAISS with trust decay, contradiction detection, governance
     ↓
[Observability] → Execution tracing, invariant enforcement, loop detection
     ↓
[Final Output]
```

## 🌟 Features

### Core Agents (6)
- **Planner Agent** — Decomposes complex tasks, learns from successful past plans
- **Supervisor Agent** — LLM-based semantic routing with retry & complexity handling
- **Research Agent** — Tavily web search + FAISS memory with provenance tracking
- **Coder Agent** — Safe Python execution with error recovery & validation
- **Validator Agent** — Real LLM scrutiny (not stub) for correctness & relevance
- **Reflection Agent** — Workflow quality analysis, planning feedback, self-improvement

### Memory & Governance
- **SQLite Memory** — Persistent conversation history with quality scores
- **FAISS Vector Store** — Local RAG with HuggingFace embeddings + disk persistence
- **Provenance Chain** — Every knowledge chunk tracks: agent, session, timestamp, validation status
- **Trust Decay** — Exponential age decay + access stabilization + validation boost
- **Contradiction Detection** — Flags conflicting knowledge before storage
- **Quality Reporting** — Aggregate trust statistics, agent breakdowns, validation coverage

### Reliability & Observability
- **Retry Logic** — Automatic retries with exponential backoff per agent
- **Invariant Enforcement** — State transition validators catch corruption early
- **Execution Tracing** — Full audit trail: before/after state, agent, timestamps
- **Loop Detection** — Flags infinite loops and stuck workflows automatically
- **State Integrity** — Every transition checked: field presence, index bounds, confidence ranges

## 📁 Project Structure

```
multimind-ai/
├── agents.py           # 6 agents with tracing + governance metadata
├── graph.py            # 6-node workflow orchestration
├── main.py             # Entry point with observability & governance report
├── state.py            # Shared state schema (TypedDict)
├── tools.py            # Tavily Search + Python REPL
├── memory.py           # SQLite + FAISS (provenance, trust decay, contradiction detection)
├── planner.py          # Task decomposition + policy learning
├── reflection.py       # Workflow analysis + insight generation
├── observability.py    # Tracing, invariants, loop detection (NEW)
├── requirements.txt    # Python dependencies
├── .env.example        # Environment variables template
├── examples.py         # Example interactions
├── ARCHITECTURE.md     # Technical deep-dive
└── README.md           # This file
```
multimind-ai/
├── agents.py           # 6 agents with tracing + governance metadata
├── graph.py            # 6-node workflow orchestration with conditional routing
├── main.py             # Entry point with observability reporting
├── state.py            # Shared state schema with planning & reflection fields
├── tools.py            # Tavily Search (deprecation warning) + Python REPL
├── memory.py           # SQLite + FAISS with provenance, decay, contradiction detection
├── planner.py          # Task decomposition engine with policy learning
├── reflection.py       # Workflow analysis and insight generation
├── observability.py    # Execution traces, invariant validation, loop detection
├── requirements.txt    # Python dependencies
├── .env.example        # Environment variables template
├── examples.py         # Example interactions (research, code, multi-turn)
├── ARCHITECTURE.md     # Technical deep-dive: layers, failure taxonomy, policies
└── README.md           # This file
```

## 🚀 Setup Instructions

### 1. Prerequisites
- Python 3.9 or higher (tested on 3.14)
- OpenAI API key (for LLM agents)
- Tavily API key (free tier: https://tavily.com)

### 2. Installation
```bash
cd "MultiMind AI"
python -m venv venv
# Windows: venv\Scripts\activate
# macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure Environment
```bash
cp .env.example .env
# Edit .env with your API keys:
# OPENAI_API_KEY=your_key_here
# TAVILY_API_KEY=your_key_here
```

### 4. Run the System
```bash
python main.py
```

## 📖 Agent Pipeline

### Planner Agent
- LLM decomposes complex queries into prioritized, dependency-aware subtasks
- Learns from successful past plans via `PolicyStore`
- Reuses high-success policies to accelerate similar future queries

### Supervisor Agent (Orchestrator)
- Classifies queries: research / coding / general
- Detects complexity → routes to planner when needed
- Manages retry logic (max 3 attempts)
- Coordinates agent handoffs until all tasks complete

### Research Agent
- Tavily web search (advanced depth)
- Results stored in FAISS with provenance (`agent_source="research"`)
- Includes source citation and structured formatting

### Coder Agent
- Safe Python REPL execution with stdout capture
- Error handling with retry + context preservation
- Successful outputs stored as validated knowledge

### Validator Agent
- **Real LLM-based scrutiny** (not a stub)
- Checks: correctness, relevance, completeness, hallucination risk
- Returns structured JSON with confidence, issues, suggestions
- Stores validated results with `validated=True` + confidence boost

### Reflection Agent
- Analyzes entire workflow: planning quality, retrieval effectiveness, execution efficiency
- Generates planning feedback and next-iteration tips
- Stores workflow insights for future learning
- Synthesizes `final_answer` from best available output

### Memory Layer (Governance-Enabled)
- **SQLite** — conversations, execution history, metadata
- **FAISS** — vector store with disk persistence (`faiss_index/`)
- **Per-chunk quality scoring** — intrinsic structure/length heuristics
- **Trust decay** — 30-day half-life; access count stabilizes; validated knowledge gets +50% boost
- **Provenance** — agent, session, iteration, validation status attached to every chunk
- **Contradiction detection** — flags potentially conflicting knowledge on insertion

### Observability Layer
- **Execution tracing** — full state snapshots before/after each agent
- **Invariant checks** — field presence, index bounds, confidence ranges, no-change detection
- **Loop detection** — same agent twice without state change → flagged
- **Progress reporting** — per-session transition count, violation count, agent visit distribution
- **Export capability** — traces can be saved to JSON for offline analysis

## 🔧 Cost Optimization

Designed for minimal operational cost:

| Component | Free Option |
|-----------|-------------|
| LLM | Groq free tier (or OpenAI trial) |
| Search | Tavily free tier (100 searches/month) |
| Embeddings | HuggingFace local (all-MiniLM-L6-v2) |
| Vector DB | FAISS local file |
| Memory | SQLite local file |

**Estimated monthly cost: $0–5** for learning/portfolio projects.

## 🔮 Production Roadmap

### Current Capabilities
- ✅ End-to-end autonomous workflow (planner → reflection)
- ✅ Invariant enforcement + observability
- ✅ Memory governance (provenance, trust decay, validation boost)
- ✅ Persistent knowledge across runs
- ✅ Policy learning from successful executions

### Next Improvements
- [ ] Parallel agent execution for independent sub-tasks
- [ ] Contradiction resolution (re-validation when conflicts detected)
- [ ] Confidence propagation into agent prompts (weight sources by trust)
- [ ] Policy store persistence across sessions
- [ ] Semantic evaluation framework (plan quality scoring, retrieval relevance)
- [ ] Distributed observability dashboard (Grafana/Prometheus integration)
- [ ] Human-in-the-loop approval gates for low-confidence outputs
- [ ] Docker deployment with volume mounts for persistence

## 📊 Governance Metrics

After each run, the system reports:
```
[Observability] Session <id>: N transitions, M violations, P loops detected
[Memory Governance Report]
  Total knowledge chunks: X
  Average trust score: 0.XX
  Trust range: [0.XX, 0.XX]
```

Zero violations indicates all state transitions respected integrity boundaries.

## 🧪 Testing

Unit tests validate:
- Simple query routing (research vs coding)
- Complex query → planner trigger
- Planner creates valid task lists
- Quality assessment heuristics
- Retry count tracking
- Policy store success counting

Run tests:
```bash
python tests.py
```

## 📝 License

Educational open-source — fork, extend, and build trustworthy autonomous systems.