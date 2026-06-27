"""
Enhanced Memory layer with quality controls, decay, provenance, and observability.
"""

import os
import json
import sqlite3
import time
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from langchain_core.messages import BaseMessage, messages_to_dict, messages_from_dict

logger = logging.getLogger(__name__)


def get_tenant_context():
    """Lazy import to avoid circular dependency."""
    try:
        from tenant import get_tenant_context as _get_ctx
        return _get_ctx()
    except Exception:
        class DummyContext:
            def get_tenant_id(self):
                return None
        return DummyContext()


class MemoryStore:
    """Persistent memory store for agent conversations and results with quality tracking."""
    
    def __init__(self, db_path: str = "agent_memory.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize SQLite database for memory storage."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                timestamp TEXT,
                messages TEXT,
                metadata TEXT,
                quality_score REAL DEFAULT 0.5
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS execution_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                agent TEXT,
                input TEXT,
                output TEXT,
                timestamp TEXT,
                success INTEGER DEFAULT 1
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def save_conversation(self, session_id: str, messages: List[BaseMessage], 
                         metadata: Dict = None, quality_score: float = 0.5):
        """Save conversation to memory with quality score."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO conversations (id, timestamp, messages, metadata, quality_score)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            session_id,
            datetime.now().isoformat(),
            json.dumps(messages_to_dict(messages)),
            json.dumps(metadata or {}),
            quality_score
        ))
        
        conn.commit()
        conn.close()
    
    def load_conversation(self, session_id: str) -> tuple:
        """Load conversation from memory."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT messages, metadata FROM conversations WHERE id = ?', (session_id,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            messages = messages_from_dict(json.loads(result[0]))
            metadata = json.loads(result[1]) if result[1] else {}
            return messages, metadata
        return [], {}
    
    def log_execution(self, session_id: str, agent: str, input_data: Dict, 
                     output: Dict, success: int = 1):
        """Log agent execution for debugging and analysis."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO execution_history (session_id, agent, input, output, timestamp, success)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            session_id,
            agent,
            json.dumps(input_data),
            json.dumps(output),
            datetime.now().isoformat(),
            success
        ))
        
        conn.commit()
        conn.close()
    
    def get_success_rate(self, agent: str) -> float:
        """Get success rate for an agent."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT AVG(success) FROM execution_history WHERE agent = ?
        ''', (agent,))
        
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result and result[0] else 0.5


# RAG Memory with Quality Controls, Governance, Provenance, and Observability
try:
    from langchain_community.vectorstores import FAISS
    from langchain_community.embeddings import HuggingFaceEmbeddings
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    from langchain_core.documents import Document
    import os
    
    class RAGMemory:
        """RAG-enabled memory with quality, decay, provenance, contradiction detection, and persistence."""
        
        def __init__(self, model_name: str = "all-MiniLM-L6-v2", persist_dir: str = "faiss_index"):
            self.embeddings = HuggingFaceEmbeddings(model_name=model_name)
            self.base_persist_dir = persist_dir
            self.persist_dir = self._get_tenant_persist_dir()
            self.vector_store = None
            self.text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=500,
                chunk_overlap=50
            )
            self.knowledge_scores: Dict[str, float] = {}   # content_hash -> base quality
            self.access_counts: Dict[str, int] = {}        # content_hash -> access count
            
            self._load_or_initialize()
        
        def _get_tenant_persist_dir(self) -> str:
            """Get tenant-specific persistence directory."""
            try:
                from tenant import tenant_memory_key
                tenant_id = get_tenant_context().get_tenant_id()
                if tenant_id:
                    return f"faiss_index_{tenant_id}"
            except Exception:
                pass
            return self.base_persist_dir
        
        def _load_or_initialize(self):
            """Load existing FAISS index from disk or start fresh."""
            index_file = os.path.join(self.persist_dir, "index.faiss")
            if os.path.exists(index_file):
                try:
                    self.vector_store = FAISS.load_local(
                        self.persist_dir,
                        self.embeddings,
                        allow_dangerous_deserialization=True
                    )
                    print(f"[RAGMemory] Loaded FAISS index from '{self.persist_dir}' ({self.vector_store.index.ntotal} vectors)")
                except Exception as e:
                    print(f"[RAGMemory] Failed to load FAISS index: {e}")
                    self.vector_store = None
            else:
                self.vector_store = None
        
        def _save_index(self):
            """Persist FAISS index to disk."""
            if self.vector_store is None:
                return
            try:
                os.makedirs(self.persist_dir, exist_ok=True)
                self.vector_store.save_local(self.persist_dir)
            except Exception as e:
                print(f"[RAGMemory] Failed to save index: {e}")
        
        def _content_hash(self, content: str) -> str:
            """Stable hash for content."""
            return str(hash(content))
        
        def assess_quality(self, content: str) -> float:
            """Intrinsic quality assessment of a knowledge chunk (0-1)."""
            if not content:
                return 0.0
            
            score = 0.5  # baseline
            
            if len(content) > 200:
                score += 0.1
            if len(content) > 500:
                score += 0.1
            if "•" in content or "1." in content:
                score += 0.1
            if "http" in content:
                score += 0.1
            if any(word in content.lower() for word in ["result", "analysis", "finding", "conclusion"]):
                score += 0.1
            
            return min(1.0, score)
        
        def compute_trust_score(self, metadata: Dict, current_time: float) -> float:
            """
            Dynamic trust score with decay and stabilization.
            
            Factors:
                base_quality     – intrinsic content quality
                age_decay        – exponential half-life 30 days
                access_factor    – more accesses stabilize trust (caps at 1.0)
                validation_boost – +50% if externally validated
            """
            base_quality = float(metadata.get("_quality", 0.5))
            timestamp = metadata.get("_timestamp", current_time)
            access_count = int(metadata.get("_access_count", 1))
            validated = bool(metadata.get("_validated", False))
            validation_score = float(metadata.get("_validation_score", base_quality))
            
            # Age decay (half-life 30 days)
            age_days = (current_time - timestamp) / (24 * 3600)
            age_decay = 0.5 ** (age_days / 30)
            
            # Access count factor (stabilizes trust)
            access_factor = min(1.0, 0.5 + (access_count * 0.1))
            
            # Validation boost
            validation_boost = 1.0 + (0.5 * validation_score) if validated else 1.0
            
            trust = base_quality * age_decay * access_factor * validation_boost
            return max(0.0, min(1.0, trust))
        
        def add_knowledge(self, content: str, metadata: Dict = None):
            """Add content to RAG memory with per-chunk provenance and governance metadata."""
            if not content:
                return
            
            chunks = self.text_splitter.split_text(content)
            new_docs = []
            
            for chunk in chunks:
                quality = self.assess_quality(chunk)
                content_hash = self._content_hash(chunk)
                now = time.time()
                
                self.knowledge_scores[content_hash] = quality
                self.access_counts[content_hash] = 1
                
                # Provenance + governance metadata
                provenance = {
                    "_quality": quality,
                    "_hash": content_hash,
                    "_timestamp": now,
                    "_access_count": 1,
                    "_agent": metadata.get("agent_source", "unknown") if metadata else "unknown",
                    "_session": metadata.get("session_id", "default") if metadata else "default",
                    "_iteration": metadata.get("iteration", 0) if metadata else 0,
                    "_validated": metadata.get("validated", False) if metadata else False,
                    "_validation_score": metadata.get("validation_score", quality) if metadata else quality,
                    # Knowledge Integrity fields
                    "_source_type": metadata.get("source_type", "llm_generation") if metadata else "llm_generation",
                    "_source_name": metadata.get("source_name", "unknown") if metadata else "unknown",
                    "_user_id": metadata.get("user_id", "unknown") if metadata else "unknown",
                    "_allowed_roles": metadata.get("allowed_roles", ["*"]) if metadata else ["*"],
                    "_department": metadata.get("department", None) if metadata else None,
                    "_freshness_score": metadata.get("freshness_score", 1.0) if metadata else 1.0,
                    "_conflict_id": metadata.get("conflict_id", None) if metadata else None,
                    # Multi-tenant field
                    "_tenant_id": get_tenant_context().get_tenant_id(),
                }
                merged_metadata = {**provenance, **(metadata or {})}
                
                new_docs.append(Document(
                    page_content=chunk,
                    metadata=merged_metadata
                ))
            
            # Track knowledge evolution
            try:
                from knowledge_evolution import track_knowledge_evolution
                track_knowledge_evolution(
                    content=content,
                    source_name=metadata.get("source_name", "unknown") if metadata else "unknown",
                    source_type=metadata.get("source_type", "llm_generation") if metadata else "llm_generation",
                    trust_score=quality,
                    metadata=metadata
                )
            except Exception as e:
                logger.debug(f"[Evolution] Tracking skipped: {e}")
            
            # Check for conflicts before storing
            try:
                from conflict_detector import get_conflict_detector, KnowledgeChunk
                detector = get_conflict_detector()
                
                # Build KnowledgeChunk for new content
                new_chunk_obj = KnowledgeChunk(
                    chunk_id=content_hash,
                    content=chunks[0],  # Use first chunk as representative
                    source_name=metadata.get("source_name", "unknown") if metadata else "unknown",
                    source_type=metadata.get("source_type", "llm_generation") if metadata else "llm_generation",
                    timestamp=now,
                    trust_score=quality,
                    freshness_score=metadata.get("freshness_score", 1.0) if metadata else 1.0,
                    allowed_roles=metadata.get("allowed_roles", ["*"]) if metadata else ["*"],
                    department=metadata.get("department", None) if metadata else None,
                    metadata=metadata or {},
                    content_hash=content_hash,
                )
                
                # Get existing chunks (simplified: use all indexed docs)
                existing_chunks = []
                if self.vector_store:
                    for doc_id in range(min(self.vector_store.index.ntotal, 50)):
                        try:
                            doc = self.vector_store.docstore.search(doc_id)
                            if doc:
                                meta = doc.metadata
                                existing_chunks.append(KnowledgeChunk(
                                    chunk_id=doc_id,
                                    content=doc.page_content,
                                    source_name=meta.get("_source_name", "unknown"),
                                    source_type=meta.get("_source_type", "llm_generation"),
                                    timestamp=meta.get("_timestamp", now),
                                    trust_score=meta.get("_quality", 0.5),
                                    freshness_score=meta.get("_freshness_score", 1.0),
                                    allowed_roles=meta.get("_allowed_roles", ["*"]),
                                    department=meta.get("_department", None),
                                    metadata=meta,
                                    content_hash=meta.get("_hash", ""),
                                ))
                        except Exception:
                            pass
                
                conflicts = detector.detect_conflicts(new_chunk_obj, existing_chunks)
                if conflicts:
                    logger.info(f"[Memory] Detected {len(conflicts)} conflicts when adding knowledge")
                    # Store conflict IDs in metadata of the new doc
                    for i, conflict in enumerate(conflicts):
                        # Add conflict reference to the first chunk's metadata
                        if i == 0 and new_docs:
                            new_docs[0].metadata["_conflict_id"] = conflict.conflict_id
                            new_docs[0].metadata["_conflicts_detected"] = True
            except Exception as e:
                logger.debug(f"[Memory] Conflict detection skipped: {e}")
            
            if self.vector_store is None:
                self.vector_store = FAISS.from_documents(new_docs, self.embeddings)
            else:
                self.vector_store.add_documents(new_docs)
            
            self._save_index()
        
        def retrieve(self, query: str, k: int = 3) -> List[Dict]:
            """
            Retrieve knowledge with trust-based ranking and provenance.
            
            Returns each result with:
                - content
                - trust (decayed 0-1 score)
                - freshness_score
                - provenance (agent, session, created, access_count, validated, validation_score, iteration)
                - metadata (full)
                - conflict_info (if applicable)
            """
            if self.vector_store is None:
                return []
            
            results = self.vector_store.similarity_search(query, k=k*2)
            current_time = time.time()
            filtered = []
            
            for r in results:
                content = r.page_content
                metadata = r.metadata
                content_hash = metadata.get("_hash") or self._content_hash(content)
                
                trust = self.compute_trust_score(metadata, current_time)
                
                # Compute freshness
                timestamp = metadata.get("_timestamp", current_time)
                age_days = (current_time - timestamp) / (24 * 3600)
                freshness = max(0.0, 0.5 ** (age_days / 90))
                
                if trust > 0.3:
                    # Increment access tracking (in-memory; not persisted back to FAISS on read)
                    metadata["_access_count"] = int(metadata.get("_access_count", 0)) + 1
                    self.access_counts[content_hash] = metadata["_access_count"]
                    
                    provenance = {
                        "agent_source": metadata.get("_agent", "unknown"),
                        "session": metadata.get("_session", "default"),
                        "created": metadata.get("_timestamp", current_time),
                        "access_count": metadata.get("_access_count", 1),
                        "validated": metadata.get("_validated", False),
                        "validation_score": metadata.get("_validation_score", trust),
                        "iteration": metadata.get("_iteration", 0),
                    }
                    
                    # Conflict info
                    conflict_info = {
                        "has_conflict": metadata.get("_conflicts_detected", False),
                        "conflict_id": metadata.get("_conflict_id", None),
                    }
                    
                    filtered.append({
                        "content": content,
                        "metadata": metadata,
                        "trust": trust,
                        "freshness_score": freshness,
                        "provenance": provenance,
                        "conflict_info": conflict_info,
                    })
            
            filtered.sort(key=lambda x: (x.get("trust", 0) * 0.6 + x.get("freshness_score", 1.0) * 0.4), reverse=True)
            return filtered[:k]
        
        def detect_contradictions(self, new_content: str, threshold: float = 0.8) -> List[Dict]:
            """Find existing knowledge that is very similar (possible contradictions)."""
            if self.vector_store is None:
                return []
            
            similar = self.vector_store.similarity_search(new_content, k=5)
            contradictions = []
            
            for sim in similar:
                existing = sim.page_content
                similarity = self._text_similarity(new_content, existing)
                if similarity > threshold:
                    contradictions.append({
                        "existing_content": existing[:200],
                        "similarity": similarity,
                        "metadata": sim.metadata
                    })
            
            return contradictions
        
        def _text_similarity(self, text1: str, text2: str) -> float:
            """Lightweight Jaccard-like word overlap."""
            w1 = set(text1.lower().split())
            w2 = set(text2.lower().split())
            if not w1 or not w2:
                return 0.0
            return len(w1 & w2) / len(w1 | w2)
        
        def get_quality_report(self) -> Dict:
            """
            Generate governance and quality metrics for the memory store.
            
            Returns aggregate statistics about trust distribution, provenance breakdown,
            and validation coverage.
            """
            if self.vector_store is None:
                return {
                    "total_chunks": 0, 
                    "average_trust": 0.0,
                    "knowledge_health_score": 1.0,
                    "unresolved_conflicts": 0
                }
            
            total = self.vector_store.index.ntotal
            current_time = time.time()
            
            trust_scores = list(self.knowledge_scores.values())  # proxy for trust
            
            # Compute average freshness
            freshness_scores = []
            for doc_id in range(min(total, 100)):
                try:
                    doc = self.vector_store.docstore.search(doc_id)
                    if doc and "_timestamp" in doc.metadata:
                        age_days = (current_time - doc.metadata["_timestamp"]) / (24 * 3600)
                        freshness = max(0.0, 0.5 ** (age_days / 90))
                        freshness_scores.append(freshness)
                except Exception:
                    pass
            
            avg_freshness = sum(freshness_scores) / len(freshness_scores) if freshness_scores else 1.0
            
            # Include knowledge health if available
            health_score = 1.0
            unresolved_conflicts = 0
            try:
                from conflict_detector import get_knowledge_health
                health = get_knowledge_health()
                health_score = health.get("knowledge_health_score", 1.0)
                unresolved_conflicts = health.get("unresolved_conflicts", 0)
            except Exception:
                pass
            
            return {
                "total_chunks": total,
                "average_trust": sum(trust_scores) / len(trust_scores) if trust_scores else 0.0,
                "min_trust": min(trust_scores) if trust_scores else 0.0,
                "max_trust": max(trust_scores) if trust_scores else 0.0,
                "average_freshness": avg_freshness,
                "knowledge_health_score": health_score,
                "unresolved_conflicts": unresolved_conflicts,
                "report_generated_at": current_time
            }
    
    rag_memory = RAGMemory()
    
except ImportError:
    # Graceful fallback if FAISS not available
    class RAGMemory:
        def __init__(self, *args, **kwargs):
            self.knowledge = {}
            self.knowledge_scores = {}
        
        def add_knowledge(self, content: str, metadata: Dict = None):
            pass
        
        def retrieve(self, query: str, k: int = 3) -> List[Dict]:
            return []
        
        def detect_contradictions(self, new_content: str, threshold: float = 0.8) -> List[Dict]:
            return []
        
        def get_quality_report(self) -> Dict:
            return {"total_chunks": 0, "average_trust": 0.0}
    
    rag_memory = RAGMemory()


# Global memory instances
memory = MemoryStore()
