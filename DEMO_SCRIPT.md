# MultiMind AI Demo Script

## 5-Minute Demo Story

### Scene 1: Setup (30s)
1. Run `streamlit run dashboard.py`
2. Login as admin/admin123
3. Show header: "🤖 MultiMind AI - Secure Enterprise Knowledge Platform"
4. Point out sidebar: Knowledge Health with Health Score metric

### Scene 2: Upload Policies (30s)
1. Navigate to "📄 Documents" tab
2. Upload sample policy documents
3. Show: Documents stored with provenance

### Scene 3: Enterprise Greeting (15s)
1. Chat: "Hi" (or "Hello")
2. Show: Structured greeting with capabilities list
3. Explain: "This isn't a chatbot - it's an AI workspace"

### Scene 4: Structured Q&A (60s)
1. Chat: "What is our leave policy?"
2. Show: Response in structured format:
   - ✅ Answer section
   - 📄 Source section
   - 📊 Confidence section (color-coded)
   - ✅ Validation section
   - ⚠️ Conflict Status section
3. Explain: "Enterprise users need this structured format for auditability"

### Scene 5: Knowledge Evolution (60s)
1. Chat: "How has our leave policy changed?"
2. Show: Timeline with changes detected
3. Explain: "Knowledge Evolution tracks policy changes over time"

### Scene 6: Conflict Detection (60s)
1. Knowledge Integrity tab
2. Show: Conflicts detected (if any)
3. Explain: "Conflicts matter for enterprise accuracy"

### Scene 7: Confidence Breakdown (60s)
1. Ask any question
2. Click "📊 Confidence Breakdown"
3. Show: Factors table (Validator, Trust, Freshness, etc.)
4. Explain: "No black box - every score is explainable"

### Scene 8: Human Approval (60s)
1. Admin tab
2. Show: Pending approval workflow
3. Approve/reject demonstration

### Scene 9: Knowledge Doctor (30s)
1. Admin Dashboard → "🩺 Knowledge Doctor" tab
2. Click "Run Knowledge Check"
3. Show: Health report with issues and recommendations

### Scene 10: Agent Replay (30s)
1. Replay tab
2. Select session
3. Inspect individual agent steps

### Scene 11: Architecture Summary (30s)
1. ARCHITECTURE.md on screen
2. Explain: Why 6 agents, adaptive routing, tenant isolation

---

## Key Talking Points

### On Knowledge Doctor:
> "Most AI assistants are reactive - they wait for questions. Knowledge Doctor is proactive: it identifies conflicting policies, outdated documents, and missing approvals without user prompting."

### On Adaptive Routing:
> "Simple queries like 'What is Python?' skip the planner and validator, reducing latency 40-60% compared to always running the full pipeline."

### On Multi-Tenant:
> "Each organization gets isolated FAISS indices. No data leakage possible."

### On Confidence:
> "Every answer shows exactly why we trust it: validator score, document trust, freshness, conflict status. No black box."

### On Enterprise Workspace Design:
> "Not a chatbot - it's an AI workspace. Structured sections (Answer, Source, Confidence, Validation) match what enterprise users expect for auditability."