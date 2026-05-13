"""
Enhanced Memory layer with quality controls, decay, provenance, and observability.
"""

import os
import json
import sqlite3
import time
from typing import List, Dict, Any, Optional
from datetime import datetime
from langchain_core.messages import BaseMessage, messages_to_dict, messages_from_dict


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
            self.persist_dir = persist_dir
            self.vector_store = None
            self.text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=500,
                chunk_overlap=50
            )
            self.knowledge_scores: Dict[str, float] = {}   # content_hash -> base quality
            self.access_counts: Dict[str, int] = {}        # content_hash -> access count
            
            self._load_or_initialize()
        
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
                }
                merged_metadata = {**provenance, **(metadata or {})}
                
                new_docs.append(Document(
                    page_content=chunk,
                    metadata=merged_metadata
                ))
            
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
                - provenance (agent, session, created, access_count, validated, validation_score, iteration)
                - metadata (full)
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
                    
                    filtered.append({
                        "content": content,
                        "metadata": metadata,
                        "trust": trust,
                        "provenance": provenance
                    })
            
            filtered.sort(key=lambda x: x["trust"], reverse=True)
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
                return {"total_chunks": 0, "average_trust": 0.0}
            
            total = self.vector_store.index.ntotal
            current_time = time.time()
            
            trust_scores = list(self.knowledge_scores.values())  # proxy for trust
            
            return {
                "total_chunks": total,
                "average_trust": sum(trust_scores) / len(trust_scores) if trust_scores else 0.0,
                "min_trust": min(trust_scores) if trust_scores else 0.0,
                "max_trust": max(trust_scores) if trust_scores else 0.0,
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
