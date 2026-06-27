# MultiMind AI — Interview Preparation Guide

> **"MultiMind AI is a secure multi-agent enterprise knowledge assistant. It helps organizations retrieve information from private documents and trusted public sources while preventing unauthorized data access. Instead of using a single AI model, specialized agents collaborate for planning, retrieval, validation, security checks, and response generation."**

---

## 1. The Problem (30 seconds)

Organizations store knowledge across PDFs, policies, databases, and internal documentation. Employees spend significant time searching for accurate information, while public AI tools risk exposing confidential data. MultiMind AI securely retrieves only authorized internal information, enriches it with trusted public sources when appropriate, and provides explainable, permission-aware responses using a multi-agent workflow.

**Key points:**
- Users: employees in regulated/knowledge-heavy organizations
- Pain: data leakage + siloed information + poor search
- Why not just ChatGPT? Public AI can expose confidential data; no RBAC; no audit trail

---

## 2. The Architecture (2 minutes)

### Why LangGraph instead of a simple sequential workflow?

LangGraph provides:
- **Stateful orchestration**: Shared typed state flows through all agents, enabling memory, validation, and approval gates.
- **Conditional routing**: Supervisor dynamically routes to planner, research, coder, validator, or approval based on state — not a fixed pipeline.
- **Human-in-the-loop**: Natural pause/resume at any node (e.g., approval workflow).
- **Observability**: Built-in tracing of every state transition, invariant checks, loop detection.

A simple sequential chain cannot enforce RBAC, security scanning, or approval gates at arbitrary points.

### Agent Collaboration Flow

```
User Query
    ↓
[Supervisor] — complexity detection + RBAC check + security pre-scan
    ↓
[Planner] (if complex) — decomposes into typed subtasks
    ↓
[Research Agent] — web search + FAISS retrieval (RBAC-filtered)
    ↓
[Coder Agent] — Python REPL (if needed) with SQL injection checks
    ↓
[Validator] — LLM-based scrutiny: correctness, relevance, completeness, hallucination risk
    ↓
[Approval] (if confidence < 0.7 or non-admin sensitive action)
    ↓
[Reflection] — workflow quality analysis, final answer synthesis, source attribution
    ↓
Output with confidence score + sources + audit trail
```

**Why multiple agents instead of one GPT-4 prompt?**
- Specialization: each agent has a focused responsibility (research, code, validation, reflection).
- Governance: validator independently checks for hallucinations; reflection catches workflow failures.
- Security: RBAC and security scanning happen at agent boundaries.
- Observability: each agent transition is traced for audit.

---

## 3. The Security Model (2 minutes)

### RBAC

Four roles with granular permissions:
- **Admin**: full access, user management, audit logs
- **Employee**: department-scoped documents, code execution in sandbox
- **Customer**: public + own data only, no code execution
- **Guest**: public research only

RBAC is enforced at three points:
1. **Dashboard navigation** — sidebar hides unauthorized pages
2. **Agent invocation** — supervisor checks `get_accessible_agents()` before routing
3. **Memory retrieval** — `filter_memory_chunks()` excludes chunks from unauthorized departments

### Prompt Injection Protection

Three-layer defense:
1. **Regex patterns** — 50+ known injection signatures (instruction override, role hijacking, code injection, encoding bypass)
2. **Context manipulation detection** — "as we discussed earlier", "from now on", "new instructions"
3. **Output sanitization** — PII masking (email, phone, SSN, credit card) in final answers

### Audit Logging

Every agent action, security event, and approval decision is logged to SQLite with:
- Timestamp, user_id, session_id, agent, action, severity
- Security events table for critical/high alerts
- Used by admin dashboard for compliance

### Data Leakage Prevention

- Documents stored with `user_id` + `allowed_roles` metadata in FAISS
- Retrieval filters by current user's role/department before returning results
- PII masked in outputs regardless of user role
- Human approval required for low-confidence outputs from non-admin users

---

## 4. The Deployment Path (1 minute)

### Local Development
```
Docker Compose
├── Streamlit (port 8501)
├── FAISS index (volume mount)
├── SQLite databases (volume mount)
└── Optional Redis/PostgreSQL (production profile)
```

### Production (AWS)
```
Users → CloudFront (CDN + WAF)
    → API Gateway
    → Cognito (auth)
    → ALB
    → ECS Fargate (Docker containers)
    → Data: RDS PostgreSQL + ElastiCache Redis + S3 + OpenSearch
    → LLM: Bedrock / OpenAI / Cohere
    → Observability: CloudWatch + X-Ray + Security Hub
```

### Why Each AWS Service?

| Service | Why? |
|---------|------|
| **S3** | Stores uploaded documents (PDF, DOCX, Excel). Durable, scalable, fine-grained IAM permissions. |
| **RDS PostgreSQL** | Structured data: conversations, audit logs, user metadata. ACID compliance for audit integrity. |
| **OpenSearch / Vector DB** | Semantic search over document embeddings. Needed for RAG — keyword search isn't enough. |
| **ECS Fargate** | Runs the multi-agent workflow. LangGraph can take 30+ seconds. ECS handles long-running containers with volume mounts; Lambda has cold-start overhead and is better for short stateless functions. |
| **CloudWatch** | Metrics, logs, alarms. Essential for observability of agent execution times, error rates, and security events. |
| **Cognito** | Managed authentication and user management. Avoids building auth from scratch. |

**Why ECS instead of Lambda?**
- LangGraph workflows can run 30+ seconds (multiple agent calls, web search, validation).
- Lambda has 15-minute timeout but cold start overhead for heavy dependencies (FAISS, transformers).
- ECS Fargate allows persistent containers with volume mounts for FAISS index and SQLite.
- Easier to debug locally with same Docker image.

**Why FAISS instead of a managed vector DB?**
- Zero operational cost for prototype.
- Disk persistence (`faiss_index/`) survives restarts.
- Can swap to OpenSearch/Elasticsearch in production with same retrieval interface.
- For enterprise: OpenSearch provides RBAC-native ACLs, encryption, and monitoring.

---

## 5. Key Design Decisions to Defend

| Decision | Rationale |
|----------|-----------|
| LangGraph | Stateful, conditional routing, human-in-the-loop, observability |
| FAISS | Free, local, persistent; upgrade path to OpenSearch |
| SQLite | Simple, file-based, sufficient for prototype |
| Streamlit | Rapid dashboard development, easy Cloud deployment |
| 6 agents | Specialization + governance; not just "one prompt" |
| Confidence threshold 0.7 | Below this → approval or re-routing; tunable per use case |
| Trust decay (30-day half-life) | Prevents stale knowledge from polluting retrieval |
| Validation boost (+50%) | External verification is a strong trust signal |
| Layered security | Regex + LLM classifier + output sanitizer |

---

## 6. Practice Questions & Answers

### Q: Why RBAC?
> "In enterprise environments, not every employee should access all documents. RBAC ensures users only retrieve information they are authorized to see, reducing the risk of confidential data exposure. It's enforced at three layers: the dashboard UI, the agent routing layer, and the memory retrieval layer."

### Q: Why multiple agents instead of one GPT-4 prompt?
> "A single prompt can't enforce governance. Multiple agents provide specialization — planning, research, code execution, validation, and reflection each have isolated responsibilities. The validator independently checks for hallucinations, security scanning happens at boundaries, and every transition is traced for audit. You can't get that from a single LLM call."

### Q: Why FAISS?
> "For the prototype, FAISS is zero-cost, runs locally, and persists to disk. In production, we'd swap to OpenSearch, which adds RBAC-native ACLs, encryption, and managed scaling — but the retrieval interface stays the same."

### Q: Why Docker?
> "Docker ensures consistency between development and production. The same container image runs locally with docker-compose and on ECS Fargate in AWS. It also isolates dependencies like FAISS and transformers."

### Q: How do you prevent prompt injection?
> "Three layers: first, regex patterns catch known injection signatures; second, an LLM classifier detects context manipulation and semantic attacks; third, output sanitization masks PII. The system logs all injection attempts for audit."

### Q: How is the confidence score calculated?
> "The validator agent outputs a confidence breakdown across four dimensions: correctness, relevance, completeness, and hallucination risk. If confidence is below 0.7, the system either routes back to the supervisor for rework or triggers a human approval gate. This prevents low-quality or unsafe responses from reaching users."

### Q: What happens if Tavily is unavailable?
> "The research agent has retry logic with exponential backoff. If all retries fail, it returns an error message and routes to the validator, which can still score the response or trigger approval. The system never crashes — it degrades gracefully."

---

## 7. The HR Salary Challenge

> "Suppose an HR employee asks: 'Show me the salary of all employees.' How does your system prevent unauthorized access?"

**Expected answer framework:**

1. **Authentication**: User logs in with credentials. System knows who they are (user_id, role, department).

2. **RBAC Check**: Supervisor checks if the user's role has permission to view all employees. An HR employee might have `view_document:department:hr`, but not `view_document:*`. The system routes to permission check before any retrieval.

3. **Memory Filtering**: Even if salary data exists in FAISS, `filter_memory_chunks()` checks each chunk's metadata for `allowed_roles` and `department`. Chunks the user isn't authorized to see are filtered out.

4. **Audit Log**: The system logs the attempted query, the user's ID, and the access decision (granted/denied). Admins can review this in the audit dashboard.

5. **Response**: If authorized, the system returns results with source attribution. If not, it returns an access-denied message with a reference to company policy — not a stack trace or raw database error.

**Why this matters**: This single question tests whether you understand that security isn't just a login page — it's enforced at every layer of the system.

---

## 8. Failure Modes & Mitigations

| What If... | Mitigation |
|------------|------------|
| Tavily API is down | Fallback to internal knowledge only; no crash |
| LLM returns invalid JSON | Fallback validation dict with lowered confidence |
| User uploads 1GB PDF | Chunked parsing + storage; chunk size = 500 chars |
| 1000 concurrent users | ECS autoscaling + Redis session store + OpenSearch |
| Prompt injection bypasses regex | Layer 2: LLM classifier; Layer 3: output sanitizer |
| FAISS index corrupts | Rebuild from SQLite conversation history |
| Admin leaves company | Cognito/SSO integration in production; demo uses hardcoded roles |

---

## 9. Metrics to Mention

- **Security**: 50+ injection patterns detected; PII masking covers 7 PII types
- **Performance**: Parallel agent execution goal (30% latency reduction)
- **Reliability**: Invariant enforcement on every transition; loop detection
- **Cost**: $0–5/month for dev; ~$110–140/month on AWS production
- **Knowledge**: Trust decay (30-day half-life), validation boost (+50%), access stabilization

---

## 10. Honest Project Status

**Don't say:**
> "This is a production-ready system."

**Do say:**
> "The architecture is designed with production deployment in mind. The current implementation demonstrates the core concepts such as security, RBAC, approval workflows, and deployment patterns. It's built to be extended and hardened for production use."

---

## Elevator Pitch Practice

> "MultiMind AI is a secure multi-agent enterprise knowledge assistant. It helps organizations retrieve information from private documents and trusted public sources while preventing unauthorized data access. Instead of using a single AI model, specialized agents collaborate for planning, retrieval, validation, security checks, and response generation."

---

*Focus on the "why" behind every design choice.Your mentor wants to understand how you think, not whether you memorized documentation.*
