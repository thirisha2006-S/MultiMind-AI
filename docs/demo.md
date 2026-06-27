# MultiMind AI Demo

## 5-Minute Walkthrough

1. **Authentication** - Demo login (admin/admin123)
2. **Simple Query** - "What is LangGraph?" (shows adaptive routing)
3. **Complex Query** - "Compare Python web frameworks..." (triggers planner)
4. **Knowledge Evolution** - "How has leave policy changed?" (timeline)
5. **Security Scan** - "Test PII detection"
6. **Confidence Breakdown** - Click to expand confidence factors
7. **Agent Replay** - Inspect workflow reasoning steps

## Running the Demo

```bash
streamlit run dashboard.py
```

Login with demo credentials (from sidebar):
- admin/admin123 - Full access
- employee/emp123 - Employee access  
- customer/cust123 - Limited access

## Sample Questions to Try

- "What is LangGraph?" (simple research)
- "Calculate fibonacci numbers" (coding)
- "Compare FastAPI vs Flask performance" (complex, triggers planner)
- "How has our leave policy changed over time?" (evolution)
- "What is the capital of France?" (simple with cache)

## Architecture Diagrams

![System Flow](docs/flow.png)
*Workflow orchestration with adaptive routing*

![Tenant Isolation](docs/tenant.png)
*Multi-tenant data separation