# MultiMind AI: A Secure Multi-Agent Enterprise Knowledge Assistant

An enterprise-grade Agentic AI platform that securely retrieves information from private organizational documents and public web sources using a multi-agent architecture, while preventing data leakage through role-based access control, human approval workflows, and explainable AI.

**Problem:** Organizations have large amounts of internal documents, policies, and databases. Employees struggle to find accurate information, and using public AI tools can risk exposing confidential data. MultiMind AI provides a secure, multi-agent AI assistant that retrieves authorized internal information, combines it with relevant public knowledge when needed, and generates reliable, explainable responses without leaking sensitive data.

## 🏗️ Architecture Overview

```
Users
   │
   ▼
Authentication (JWT / Cognito)
   │
   ▼
API Gateway
   │
   ▼
Load Balancer
   │
   ▼
Docker Containers (ECS/EKS)
   │
   ├── Supervisor Agent
   ├── Planner Agent
   ├── Research Agent
   ├── Validator Agent
   ├── Reflection Agent
   │
   ▼
Knowledge Layer
 ├── Amazon RDS
 ├── OpenSearch / Vector DB
 ├── S3 (Documents)
 └── Web Search
   │
   ▼
LLM
(Bedrock / OpenAI / Cohere)
   │
   ▼
CloudWatch + Audit Logs
```

## 🌟 Features

### Security & Access Control
- **RBAC** — Admin, Employee, Customer, Guest roles with permission granularity
- **Authentication** — Session-based login with role-aware access
- **Prompt Injection Detection** — Real-time scanning of user inputs
- **PII Masking** — Automatic redaction of sensitive data in outputs
- **SQL Injection Prevention** — Code and input validation
- **Audit Logging** — Full audit trail for all agent actions

### Enterprise Memory & RAG
- **Private Document Upload** — PDF, DOCX, Excel, CSV, images, audio
- **FAISS Vector Store** — Local RAG with HuggingFace embeddings + disk persistence
- **Permission-Aware Retrieval** — Documents filtered by user role and department

### Knowledge Intelligence
- **Knowledge Evolution Engine** — Track how policies change over time
- **Knowledge Doctor AI** — Proactive health checks for your knowledge base (NEW)
- **Source Attribution** — Every answer traced to internal, web, or LLM sources
- **Trust Decay** — 30-day half-life; validated knowledge gets +50% boost

### Core Agents (6)
- **Planner Agent** — Decomposes complex tasks, learns from successful past plans
- **Supervisor Agent** — Adaptive routing; skips planner for simple queries
- **Research Agent** — Tavily web search + FAISS memory with provenance
- **Coder Agent** — Safe Python execution with SQL injection checks
- **Validator Agent** — Real LLM scrutiny; confidence breakdown
- **Reflection Agent** — Workflow analysis; synthesizes final answer

### Human-in-the-Loop & Trust
- **Human Approval Workflow** — Optional approval gate for sensitive actions
- **Explainable Confidence** — Factor breakdown (validator score, trust, freshness)
- **Self-Learning Agent** — Thumbs up/down feedback; trust score adjustment
- **Agent Memory Replay** — Inspect every step in any workflow

### Production & Observability
- **Docker Deployment** — docker-compose for local, ECS Fargate for production
- **Execution Tracing** — Full audit trail before/after each agent
- **Invariant Enforcement** — State transition validators catch corruption early
- **Loop Detection** — Flags infinite loops and stuck workflows
- **Multi-Tenant Support** — Full data isolation between organizations

## 📁 Project Structure

```
multimind-ai/
├── agents.py           # 6 agents with security, RBAC, adaptive selection
├── graph.py            # Enterprise workflow orchestration with approval
├── main.py             # Entry point with security & RBAC
├── state.py            # Shared state schema with enterprise fields
├── tools.py            # Tavily Search + Python REPL + MCP tools
├── memory.py           # SQLite + FAISS (provenance, trust decay, tenant isolation)
├── planner.py          # Task decomposition + policy learning
├── reflection.py       # Workflow analysis + confidence scoring + evolution
├── observability.py    # Tracing, invariants, loop detection
├── knowledge_evolution.py # Knowledge timeline tracking
├── confidence_explainer.py  # Explainable confidence breakdown
├── evaluation_engine.py   # Enterprise evaluation metrics
├── replay.py           # Agent memory replay
├── tenant.py           # Multi-tenant architecture
├── security.py         # Prompt injection, PII masking, audit logs
├── rbac.py             # Role-based access control
├── auth.py             # Authentication & session management
├── approval.py         # Human approval workflow
├── parsers.py          # PDF, DOCX, Excel parsers
├── feedback.py         # Self-learning from user feedback
├── multimodal.py       # Image, audio, PDF input handling
├── cost_optimizer.py   # Model routing and budget tracking
├── admin_dashboard.py  # Enterprise admin dashboard
├── memory_dashboard.py # Agent memory visualization
├── dashboard.py        # Streamlit chat interface with all enterprise features
├── requirements.txt    # Python dependencies
├── .env.example        # Environment variables template
├── Dockerfile          # Container configuration
├── docker-compose.yml  # Local orchestration
├── deploy/             # AWS deployment templates
├── examples.py         # Example interactions
├── ARCHITECTURE.md     # Technical deep-dive
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

## 📊 Evaluation

| Feature | MultiMind AI |
|---------|------------|
| Multi-Agent | ✅ |
| Authentication | ✅ |
| RBAC | ✅ |
| Prompt Injection Protection | ✅ |
| PII Masking | ✅ |
| Human Approval | ✅ |
| Knowledge Integrity | ✅ |
| Knowledge Evolution | ✅ |
| Explainable Confidence | ✅ |
| Multi-Tenant | ✅ |
| Agent Replay | ✅ |
| See full comparison → | [docs/evaluation.md](docs/evaluation.md) |

---

## 🚀 Quick Deploy

### Docker
```bash
docker build -t multimind-ai .
docker-compose up
```

### Streamlit
```bash
streamlit run dashboard.py
```

---

## 📚 Documentation

- Architecture → [docs/architecture.md](docs/architecture.md)
- Evaluation → [docs/evaluation.md](docs/evaluation.md)
- API Examples → [examples.py](examples.py)

---

## 🛠️ Extending MultiMind AI

See the architecture document for design trade-offs and extension points:
- New agents: Add function with `@trace_agent("name")` decorator
- Custom trust: Override `compute_trust_score` in RAGMemory
- Persistence: Replace in-memory PolicyStore with Redis/SQLite
- Embeddings: Swap HuggingFace for OpenAI/Pinecone

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