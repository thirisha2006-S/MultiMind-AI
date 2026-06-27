# MultiMind AI - Architecture Documentation

## System Architecture

```
User Query
    │
    ▼
Supervisor Agent (Adaptive Routing)
    │
    ├── Simple Query ───────────────────────┐
    │   (skips planner for < 50 chars)         │
    │    │                                     │
    │    ▼                                     │
    │ Research/Coding Agent                      │
    │    │                                     │
    │    ▼                                     │
    │ Validator (skipped if simple + RAG)       │
    │    │                                     │
    │    ▼                                     │
    │ Reflection Agent                          │
    │    │                                     │
    │    ▼                                     │
    │ Final Answer ◄────────────────────────────┤
    │                                           │
    └── Complex Query ──────────────────────────┘
        │
        ▼
    Planner Agent
        │
        ▼
    Supervisor (task iteration)
        │
        ▼
    Research/Coding Agents (multiple)
        │
        ▼
    Knowledge Integrity Engine
        │
        ▼
    Validator Agent
        │
        ▼
    Reflection Agent
        │
        ▼
    Final Answer
```

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Adaptive Routing** | Simple queries don't need full pipeline; reduces latency 40-60% |
| **Tenant Isolation** | Data must never leak between organizations; per-tenant FAISS indices |
| **Knowledge Evolution** | Answers become more valuable when showing historical context |
| **Explainable Confidence** | Trust requires understanding; factor breakdown enables debugging |
| **Memory Replay** | Auditing requires step inspection; stored state per transition |

## Trade-offs

| Trade-off | Choice |
|-----------|--------|
| Local FAISS vs Pinecone | Local for portability; can swap backend |
| HuggingFace vs OpenAI embeddings | Free local; upgrade path available |
| SQLite vs Postgres | Zero-config; scales to moderate load |
| Pattern matching vs LLM classification | Fast for routing; LLM as fallback |

## Limitations

1. **Single-node deployment** - No distributed processing
2. **In-memory policy store** - Doesn't persist across restarts  
3. **Jaccard similarity** - Upgrade to cosine embedding similarity
4. **Simple conflict detection** - Could use LLM for semantic contradictions