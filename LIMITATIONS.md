# MultiMind AI - Limitations & Trade-offs

## Current Limitations

### Technical
| Limitation | Workaround | Future Fix |
|------------|------------|----------|
| Single-node deployment | Docker for portability | Kubernetes for scale |
| In-memory policy store | SQLite for persistence | Redis or Postgres |
| Jaccard similarity | Fast for detection | Embedding cosine similarity |
| SQLite (not Postgres) | Zero-config dev | RDS for production |

### Scalability
- FAISS index rebuild on updates: O(n) scan
- No distributed workers
- No streaming responses

### Accuracy
- Conflict detection uses word overlap (false positives possible)
- Evolution relies on timestamps (requires correct metadata)

## Design Trade-offs

### Why These Choices?

| Choice | Because |
|--------|---------|
| 6 agents vs 3 | Separation of concerns; validator/reflection need isolation |
| FAISS vs Pinecone | Local demo; Pinecone swap in 3 lines |
| SQLite vs Postgres | Zero-config; obvious upgrade path |
| LLM classification | Accurate; regex fallback for speed |
| Adaptive routing | 40-60% latency reduction for common case |

## What Alternatives Were Considered

### Agent Count
- 3-agent (supervisor → worker → validator) - Too simple
- 6-agent (added planner + reflection) - Right balance
- 10+ agents - Overkill for this scope

### Memory Backend
- FAISS - Chosen for portability
- Pinecone - Rejected (requires account)
- Weaviate - Rejected (heavyweight)

### Conflict Detection
- Jaccard - Chosen (fast, no embedding calls)
- Cosine similarity - Rejected (slower)
- LLM-based - Rejected (cost)

---

## Production Readiness Checklist

| Item | Status |
|------|--------|
| Automated tests | ✅ |
| CI/CD pipeline | ✅ |
| Docker deployment | ✅ |
| Security scanning | ✅ |
| RBAC | ✅ |
| Audit logs | ✅ |
| Monitoring | ✅ |
| Load testing | ❌ (future) |
| Horizontal scale | ❌ (future) |