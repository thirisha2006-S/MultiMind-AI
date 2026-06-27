"""
Conflict Detection Engine for MultiMind AI.
Core of the Knowledge Integrity Engine.
"""

import time
import json
import uuid
import logging
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class ConflictType(Enum):
    CONTRADICTION = "contradiction"
    OUTDATED = "outdated"
    DUPLICATE = "duplicate"
    AMBIGUOUS = "ambiguous"


class ResolutionStatus(Enum):
    UNRESOLVED = "unresolved"
    PENDING = "pending"
    RESOLVED = "resolved"
    NEEDS_REVIEW = "needs_review"


@dataclass
class KnowledgeChunk:
    """Represents a knowledge chunk with integrity metadata."""
    chunk_id: str
    content: str
    source_name: str
    source_type: str  # "internal_document", "web_search", "llm_generation"
    timestamp: float
    trust_score: float  # 0.0 - 1.0
    freshness_score: float  # 0.0 - 1.0
    allowed_roles: List[str]
    department: Optional[str]
    metadata: Dict = field(default_factory=dict)
    content_hash: str = ""

    def __post_init__(self):
        if not self.content_hash:
            self.content_hash = str(hash(self.content))


@dataclass
class ConflictRecord:
    """Represents a detected knowledge conflict."""
    conflict_id: str
    conflict_type: str  # ConflictType.value
    chunks: List[KnowledgeChunk]
    description: str
    detected_at: float
    status: str  # ResolutionStatus.value
    resolution: Optional[str] = None
    resolved_by: Optional[str] = None
    resolved_at: Optional[float] = None
    authoritative_chunk_id: Optional[str] = None

    def to_dict(self) -> Dict:
        data = asdict(self)
        # Convert dataclasses nested within
        data["chunks"] = [asdict(c) if hasattr(c, '__dataclass_fields__') else c for c in (self.chunks if isinstance(self.chunks, list) else [])]
        data["detected_at_iso"] = datetime.fromtimestamp(self.detected_at).isoformat() if self.detected_at else None
        if self.resolved_at:
            data["resolved_at_iso"] = datetime.fromtimestamp(self.resolved_at).isoformat()
        return data


class SourceRanker:
    """Ranks sources by trust, freshness, and authority."""

    @staticmethod
    def compute_freshness_score(timestamp: float, now: float = None) -> float:
        """Compute freshness score. Newer = higher score.
        Half-life: 90 days. Score = 0.5 ** (age_days / 90)
        """
        if now is None:
            now = time.time()
        age_days = (now - timestamp) / (24 * 3600)
        return max(0.0, min(1.0, 0.5 ** (age_days / 90)))

    @staticmethod
    def compute_authority_score(source_type: str, allowed_roles: List[str]) -> float:
        """Compute authority score based on source type and role scope."""
        type_scores = {
            "internal_document": 0.9,
            "policy": 0.95,
            "web_search": 0.7,
            "llm_generation": 0.5,
            "user_upload": 0.6,
        }
        base = type_scores.get(source_type, 0.5)

        # More restrictive roles = higher authority (e.g., admin-only docs are more trusted)
        if "*" in allowed_roles:
            base *= 0.9  # Public docs are slightly less authoritative
        elif len(allowed_roles) <= 2:
            base *= 1.05  # Restricted docs are more authoritative

        return max(0.0, min(1.0, base))

    @staticmethod
    def rank_chunks(chunks: List[KnowledgeChunk], now: float = None) -> List[Tuple[KnowledgeChunk, float]]:
        """Rank chunks by composite score: trust * 0.4 + freshness * 0.3 + authority * 0.3"""
        if now is None:
            now = time.time()

        scored = []
        for chunk in chunks:
            freshness = SourceRanker.compute_freshness_score(chunk.timestamp, now)
            authority = SourceRanker.compute_authority_score(chunk.source_type, chunk.allowed_roles)
            composite = (chunk.trust_score * 0.4) + (freshness * 0.3) + (authority * 0.3)
            scored.append((chunk, composite))
        
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored


class ConflictDetector:
    """Detects conflicts between knowledge chunks."""

    def __init__(self, similarity_threshold: float = 0.7):
        self.similarity_threshold = similarity_threshold
        self.conflicts: Dict[str, ConflictRecord] = {}

    def _text_similarity(self, text1: str, text2: str) -> float:
        """Compute Jaccard similarity between two texts."""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        if not words1 or not words2:
            return 0.0
        return len(words1 & words2) / len(words1 | words2)

    def _extract_claims(self, text: str) -> List[str]:
        """Extract factual claims from text (simplified: sentence splitting)."""
        import re
        sentences = re.split(r'[.!?]+', text)
        claims = []
        for s in sentences:
            s = s.strip()
            if len(s) > 10 and any(c.isdigit() for c in s):
                claims.append(s)
        return claims

    def detect_conflicts(self, new_chunk: KnowledgeChunk, existing_chunks: List[KnowledgeChunk]) -> List[ConflictRecord]:
        """
        Detect conflicts between a new chunk and existing chunks.
        Returns list of ConflictRecord objects.
        """
        conflicts = []
        new_claims = self._extract_claims(new_chunk.content)

        for existing in existing_chunks:
            # Skip if same content
            if new_chunk.content_hash == existing.content_hash:
                continue

            # Check textual similarity
            similarity = self._text_similarity(new_chunk.content, existing.content)
            if similarity < self.similarity_threshold:
                continue

            # Check for conflicting claims
            existing_claims = self._extract_claims(existing.content)
            conflict_found = False
            conflict_description = ""

            for new_claim in new_claims:
                for old_claim in existing_claims:
                    # If similar sentences contain different numbers/percentages/dates
                    claim_sim = self._text_similarity(new_claim, old_claim)
                    if claim_sim > 0.5:
                        # Extract numbers from both claims
                        import re
                        old_nums = set(re.findall(r'\b\d+\.?\d*\b', old_claim))
                        new_nums = set(re.findall(r'\b\d+\.?\d*\b', new_claim))
                        if old_nums and new_nums and old_nums != new_nums:
                            conflict_found = True
                            conflict_description = (
                                f"Conflicting values: {old_claim.strip()} vs {new_claim.strip()}"
                            )
                            break

            if conflict_found:
                conflict_id = str(uuid.uuid4())[:8]
                conflict = ConflictRecord(
                    conflict_id=conflict_id,
                    conflict_type=ConflictType.CONTRADICTION.value,
                    chunks=[existing, new_chunk],
                    description=conflict_description,
                    detected_at=time.time(),
                    status=ResolutionStatus.UNRESOLVED.value,
                )
                conflicts.append(conflict)
                self.conflicts[conflict_id] = conflict

        return conflicts

    def get_unresolved_conflicts(self) -> List[ConflictRecord]:
        """Get all unresolved conflicts."""
        return [c for c in self.conflicts.values() if c.status in [
            ResolutionStatus.UNRESOLVED.value,
            ResolutionStatus.NEEDS_REVIEW.value,
        ]]

    def get_conflicts_for_topic(self, topic: str) -> List[ConflictRecord]:
        """Get conflicts related to a topic."""
        relevant = []
        topic_words = set(topic.lower().split())
        for conflict in self.get_unresolved_conflicts():
            for chunk in conflict.chunks:
                chunk_words = set(chunk.content.lower().split())
                if topic_words & chunk_words:
                    relevant.append(conflict)
                    break
        return relevant

    def resolve_conflict(self, conflict_id: str, authoritative_chunk_id: str, resolved_by: str) -> Optional[ConflictRecord]:
        """Mark a conflict as resolved."""
        conflict = self.conflicts.get(conflict_id)
        if not conflict:
            return None

        conflict.status = ResolutionStatus.RESOLVED.value
        conflict.resolution = f"Authoritative source set to chunk {authoritative_chunk_id}"
        conflict.resolved_by = resolved_by
        conflict.resolved_at = time.time()
        conflict.authoritative_chunk_id = authoritative_chunk_id

        # Boost trust of authoritative chunk
        for chunk in conflict.chunks:
            if chunk.chunk_id == authoritative_chunk_id:
                chunk.trust_score = min(1.0, chunk.trust_score + 0.1)

        logger.info(f"[Integrity] Conflict {conflict_id} resolved by {resolved_by}")
        return conflict

    def get_knowledge_health(self, total_chunks: int = 0) -> Dict:
        """Compute knowledge health metrics."""
        unresolved = len(self.get_unresolved_conflicts())
        
        # Rough freshness calculation
        now = time.time()
        # We don't have all chunks here, but we can return what we know
        
        return {
            "total_conflicts": len(self.conflicts),
            "unresolved_conflicts": unresolved,
            "resolved_conflicts": len(self.conflicts) - unresolved,
            "resolution_rate": (len(self.conflicts) - unresolved) / max(len(self.conflicts), 1),
            "knowledge_health_score": max(0.0, 1.0 - (unresolved * 0.05)),  # Each conflict costs 5%
        }


# Global conflict detector instance
_conflict_detector: Optional[ConflictDetector] = None


def get_conflict_detector() -> ConflictDetector:
    """Get or create the global conflict detector."""
    global _conflict_detector
    if _conflict_detector is None:
        _conflict_detector = ConflictDetector()
    return _conflict_detector


def detect_conflicts(new_chunk: KnowledgeChunk, existing_chunks: List[KnowledgeChunk]) -> List[ConflictRecord]:
    """Convenience function to detect conflicts."""
    detector = get_conflict_detector()
    return detector.detect_conflicts(new_chunk, existing_chunks)


def get_knowledge_health() -> Dict:
    """Convenience function to get knowledge health."""
    detector = get_conflict_detector()
    return detector.get_knowledge_health()


def resolve_conflict(conflict_id: str, authoritative_chunk_id: str, resolved_by: str):
    """Convenience function to resolve a conflict."""
    detector = get_conflict_detector()
    return detector.resolve_conflict(conflict_id, authoritative_chunk_id, resolved_by)
