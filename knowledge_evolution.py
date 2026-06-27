"""
Knowledge Evolution Engine for MultiMind AI.
Tracks how organizational knowledge changes over time and answers evolution queries.
"""

import time
import sqlite3
import json
import re
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict

import logging
logger = logging.getLogger(__name__)


@dataclass
class KnowledgeVersion:
    """Represents a version of a knowledge item over time."""
    content_id: str
    content: str
    source_name: str
    source_type: str
    timestamp: float
    trust_score: float
    metadata: Dict = field(default_factory=dict)


@dataclass
class KnowledgeEvolution:
    """Timeline of how knowledge evolved for a topic."""
    topic: str
    versions: List[KnowledgeVersion]
    changes: List[Dict]  # Descriptions of changes between versions
    
    def to_dict(self) -> Dict:
        return {
            "topic": self.topic,
            "versions": [
                {
                    "timestamp": v.timestamp,
                    "timestamp_iso": datetime.fromtimestamp(v.timestamp).isoformat(),
                    "source": v.source_name,
                    "content": v.content[:500],
                    "trust_score": v.trust_score,
                }
                for v in self.versions
            ],
            "changes": self.changes,
            "total_versions": len(self.versions),
        }


class KnowledgeEvolutionTracker:
    """
    Tracks knowledge evolution over time.
    
    For each topic/query pattern, maintains a timeline of versions showing how
    organizational knowledge has changed.
    """
    
    def __init__(self, db_path: str = "knowledge_evolution.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize evolution tracking database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS knowledge_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic_hash TEXT,
                topic_keywords TEXT,
                content TEXT,
                source_name TEXT,
                source_type TEXT,
                timestamp REAL,
                trust_score REAL,
                metadata TEXT,
                UNIQUE(topic_hash, timestamp)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS evolution_cache (
                topic_hash TEXT PRIMARY KEY,
                evolution_json TEXT,
                updated_at REAL
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _topic_hash(self, topic: str) -> str:
        """Generate stable hash for topic."""
        # Normalize and extract key terms
        normalized = re.sub(r'[^\w\s]', ' ', topic.lower())
        keywords = sorted(set(normalized.split()))
        key_phrase = ' '.join(keywords[:10])  # First 10 keywords
        return str(hash(key_phrase))
    
    def record_knowledge(self, content: str, source_name: str, source_type: str,
                        trust_score: float = 0.5, metadata: Dict = None):
        """
        Record a knowledge item with its timestamp.
        
        Called when knowledge is added to RAG memory.
        """
        # Extract topic keywords from content
        normalized = re.sub(r'[^\w\s]', ' ', content.lower())
        keywords = [w for w in normalized.split() if len(w) > 3]
        topic_keywords = json.dumps(list(set(keywords))[:20])
        
        # Get topic from metadata or derive from source
        topic = metadata.get("topic", "") if metadata else ""
        if not topic:
            topic = source_name
        
        topic_hash = self._topic_hash(topic)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT OR IGNORE INTO knowledge_versions 
                (topic_hash, topic_keywords, content, source_name, source_type, timestamp, trust_score, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                topic_hash,
                topic_keywords,
                content[:1000],  # Limit content size
                source_name,
                source_type,
                time.time(),
                trust_score,
                json.dumps(metadata or {}),
            ))
            conn.commit()
        except Exception as e:
            logger.error(f"Failed to record knowledge: {e}")
        finally:
            conn.close()
    
    def get_evolution(self, query: str) -> Optional[KnowledgeEvolution]:
        """
        Get the evolution timeline for a topic.
        
        Finds all versions of knowledge related to the query.
        """
        topic_hash = self._topic_hash(query)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Try cache first
        cursor.execute(
            'SELECT evolution_json FROM evolution_cache WHERE topic_hash = ?',
            (topic_hash,)
        )
        cached = cursor.fetchone()
        if cached:
            try:
                data = json.loads(cached[0])
                conn.close()
                evolution = KnowledgeEvolution(
                    topic=query,
                    versions=[KnowledgeVersion(**v) for v in data["versions"]],
                    changes=data["changes"],
                )
                return evolution
            except Exception:
                pass  # Fall through to fresh query
        
        # Find relevant knowledge versions by keyword matching
        query_words = set(query.lower().split())
        
        # Get all versions and filter by relevance
        cursor.execute('''
            SELECT topic_keywords, content, source_name, source_type, timestamp, trust_score, metadata
            FROM knowledge_versions 
            ORDER BY timestamp
        ''')
        
        all_versions = cursor.fetchall()
        conn.close()
        
        relevant_versions = []
        for vk, content, source, stype, ts, trust, meta in all_versions:
            try:
                keywords = set(json.loads(vk))
                if query_words & keywords or any(w in content.lower() for w in query_words):
                    relevant_versions.append(KnowledgeVersion(
                        content_id=f"{source}_{ts}",
                        content=content,
                        source_name=source,
                        source_type=stype,
                        timestamp=ts,
                        trust_score=trust,
                        metadata=json.loads(meta) if meta else {},
                    ))
            except Exception:
                continue
        
        if not relevant_versions:
            return None
        
        # Detect changes between versions
        changes = self._detect_changes(relevant_versions)
        
        evolution = KnowledgeEvolution(
            topic=query,
            versions=relevant_versions,
            changes=changes,
        )
        
        # Cache the result
        self._cache_evolution(topic_hash, evolution)
        
        return evolution
    
    def _detect_changes(self, versions: List[KnowledgeVersion]) -> List[Dict]:
        """Detect what changed between versions."""
        changes = []
        
        for i in range(1, len(versions)):
            prev = versions[i - 1]
            curr = versions[i]
            
            # Extract numbers/dates from both versions
            prev_nums = set(re.findall(r'\b\d+\.?\d*\b', prev.content))
            curr_nums = set(re.findall(r'\b\d+\.?\d*\b', curr.content))
            
            # Find what changed
            added_numbers = curr_nums - prev_nums
            removed_numbers = prev_nums - curr_nums
            
            change_desc = {
                "from_source": prev.source_name,
                "to_source": curr.source_name,
                "from_timestamp": prev.timestamp,
                "to_timestamp": curr.timestamp,
                "change_type": "numeric_change" if (added_numbers or removed_numbers) else "content_update",
                "added_values": list(added_numbers),
                "removed_values": list(removed_numbers),
                "summary": f"{prev.source_name} → {curr.source_name}: values changed",
            }
            
            if added_numbers or removed_numbers:
                change_desc["summary"] = (
                    f"{prev.source_name} ({prev.content[:100]}...) → "
                    f"{curr.source_name}: {list(removed_numbers)} → {list(added_numbers)}"
                )
            
            changes.append(change_desc)
        
        return changes
    
    def _cache_evolution(self, topic_hash: str, evolution: KnowledgeEvolution):
        """Cache evolution result."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO evolution_cache (topic_hash, evolution_json, updated_at)
            VALUES (?, ?, ?)
        ''', (topic_hash, json.dumps(evolution.to_dict()), time.time()))
        
        conn.commit()
        conn.close()
    
    def find_topic_variants(self, query: str) -> List[Tuple[str, str, float]]:
        """
        Find different variants of a topic over time.
        
        Returns list of (content_preview, source, timestamp) tuples sorted by time.
        """
        evolution = self.get_evolution(query)
        if not evolution:
            return []
        
        return [
            (v.content[:200], v.source_name, v.timestamp)
            for v in evolution.versions
        ]


# Global instance
_evolution_tracker: Optional[KnowledgeEvolutionTracker] = None


def get_evolution_tracker() -> KnowledgeEvolutionTracker:
    """Get or create the evolution tracker."""
    global _evolution_tracker
    if _evolution_tracker is None:
        _evolution_tracker = KnowledgeEvolutionTracker()
    return _evolution_tracker


def track_knowledge_evolution(content: str, source_name: str, source_type: str,
                              trust_score: float = 0.5, metadata: Dict = None):
    """Convenience function to track knowledge evolution."""
    tracker = get_evolution_tracker()
    tracker.record_knowledge(content, source_name, source_type, trust_score, metadata)


def get_knowledge_timeline(query: str) -> Optional[Dict]:
    """Get knowledge evolution timeline for a query."""
    tracker = get_evolution_tracker()
    evolution = tracker.get_evolution(query)
    return evolution.to_dict() if evolution else None