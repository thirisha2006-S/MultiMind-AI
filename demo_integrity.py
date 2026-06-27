"""
Demo Script: Knowledge Integrity Engine
Shows conflict detection, source ranking, freshness, and resolution.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from conflict_detector import (
    get_conflict_detector, 
    KnowledgeChunk, 
    SourceRanker, 
    get_knowledge_health,
    resolve_conflict
)
from datetime import datetime


def demo_conflict_detection():
    print("\n" + "=" * 60)
    print("DEMO: Knowledge Conflict Detection")
    print("=" * 60)
    
    detector = get_conflict_detector()
    
    # Simulate two policy documents with explicitly contradictory statements
    chunk_old = KnowledgeChunk(
        chunk_id="policy-v1",
        content="Leave policy grants 20 days of paid time off.",
        source_name="HR Policy Handbook v1.0",
        source_type="policy",
        timestamp=datetime(2023, 6, 1).timestamp(),
        trust_score=0.85,
        freshness_score=0.2,  # old
        allowed_roles=["*"],
        department="hr",
    )
    
    chunk_new = KnowledgeChunk(
        chunk_id="policy-v2",
        content="Leave policy grants 30 days of paid time off.",
        source_name="HR Policy Handbook v2.0",
        source_type="policy",
        timestamp=datetime(2025, 6, 1).timestamp(),
        trust_score=0.95,
        freshness_score=1.0,  # fresh
        allowed_roles=["*"],
        department="hr",
    )
    
    print("\n[Step 1] Older Policy (v1.0):")
    print(f"  Source: {chunk_old.source_name}")
    print(f"  Content: {chunk_old.content[:100]}...")
    print(f"  Trust: {chunk_old.trust_score} | Freshness: {chunk_old.freshness_score}")
    
    print("\n[Step 2] Newer Policy (v2.0):")
    print(f"  Source: {chunk_new.source_name}")
    print(f"  Content: {chunk_new.content[:100]}...")
    print(f"  Trust: {chunk_new.trust_score} | Freshness: {chunk_new.freshness_score}")
    
    # Debug similarity
    sim = detector._text_similarity(chunk_new.content, chunk_old.content)
    print(f"\n  [Debug] Text similarity between documents: {sim:.3f} (threshold: {detector.similarity_threshold})")
    
    # Detect conflicts
    conflicts = detector.detect_conflicts(chunk_new, [chunk_old])
    
    print(f"\n[Step 3] Conflict Detection:")
    if conflicts:
        print(f"  [WARNING] Detected {len(conflicts)} conflict(s)!")
        for c in conflicts:
            print(f"  Conflict ID: {c.conflict_id}")
            print(f"  Type: {c.conflict_type}")
            print(f"  Description: {c.description}")
            print(f"  Status: {c.status}")
    else:
        print("  No conflicts detected.")
        # Force-show what claims were extracted for debugging
        new_claims = detector._extract_claims(chunk_new.content)
        old_claims = detector._extract_claims(chunk_old.content)
        print(f"\n  [Debug] Extracted {len(new_claims)} claims from new doc, {len(old_claims)} from old doc")
        for i, claim in enumerate(new_claims[:3]):
            print(f"    New claim {i}: {claim[:80]}")
        for i, claim in enumerate(old_claims[:3]):
            print(f"    Old claim {i}: {claim[:80]}")
    
    # Source ranking
    print("\n[Step 4] Source Ranking:")
    ranked = SourceRanker.rank_chunks([chunk_old, chunk_new])
    for chunk, score in ranked:
        print(f"  {chunk.source_name}: composite_score={score:.3f}")
    
    return conflicts


def demo_conflict_resolution():
    print("\n" + "=" * 60)
    print("DEMO: Conflict Resolution")
    print("=" * 60)
    
    detector = get_conflict_detector()
    
    # Get any existing conflicts
    conflicts = detector.get_unresolved_conflicts()
    
    if not conflicts:
        print("  No conflicts to resolve. Run conflict detection first.")
        return
    
    conflict = conflicts[0]
    print(f"\n[Conflict ID]: {conflict.conflict_id}")
    print(f"  Description: {conflict.description}")
    
    # Find the newer chunk (higher trust)
    newer_chunk = max(conflict.chunks, key=lambda c: c.timestamp)
    print(f"\n[Resolution]:")
    print(f"  Authoritative source: {newer_chunk.source_name}")
    print(f"  Reason: Newer document (timestamp: {datetime.fromtimestamp(newer_chunk.timestamp).date()})")
    
    # Resolve
    detector.resolve_conflict(
        conflict.conflict_id,
        newer_chunk.chunk_id,
        resolved_by="admin"
    )
    
    print(f"  Status: {detector.get_request(conflict.conflict_id).status}")
    print(f"  Resolved by: admin")


def demo_knowledge_health():
    print("\n" + "=" * 60)
    print("DEMO: Knowledge Health Score")
    print("=" * 60)
    
    health = get_knowledge_health()
    print(f"\n  Total Conflicts: {health['total_conflicts']}")
    print(f"  Unresolved: {health['unresolved_conflicts']}")
    print(f"  Resolved: {health['resolved_conflicts']}")
    print(f"  Resolution Rate: {health['resolution_rate']:.0%}")
    print(f"  Knowledge Health Score: {health['knowledge_health_score']:.0%}")


def demo_freshness_scoring():
    print("\n" + "=" * 60)
    print("DEMO: Freshness Scoring")
    print("=" * 60)
    
    now = datetime.now().timestamp()
    old_doc = KnowledgeChunk(
        chunk_id="old", content="Old policy", source_name="2021 Policy",
        source_type="internal_document", timestamp=datetime(2021, 1, 1).timestamp(),
        trust_score=0.9, freshness_score=1.0, allowed_roles=["*"], department=None,
    )
    new_doc = KnowledgeChunk(
        chunk_id="new", content="New policy", source_name="2025 Policy",
        source_type="internal_document", timestamp=now,
        trust_score=0.9, freshness_score=1.0, allowed_roles=["*"], department=None,
    )
    
    print("\n  Old document (2021):")
    old_fresh = SourceRanker.compute_freshness_score(old_doc.timestamp, now)
    print(f"    Freshness score: {old_fresh:.3f} (age: {(now - old_doc.timestamp) / (365*24*3600):.1f} years)")
    
    print("\n  New document (2025):")
    new_fresh = SourceRanker.compute_freshness_score(new_doc.timestamp, now)
    print(f"    Freshness score: {new_fresh:.3f} (age: {(now - new_doc.timestamp) / (365*24*3600):.1f} years)")
    
    ranked = SourceRanker.rank_chunks([old_doc, new_doc])
    print("\n  Ranked sources:")
    for chunk, score in ranked:
        print(f"    {chunk.source_name}: {score:.3f}")


def main():
    print("=" * 60)
    print("MultiMind AI — Knowledge Integrity Engine Demo")
    print("=" * 60)
    
    demo_conflict_detection()
    demo_freshness_scoring()
    demo_knowledge_health()
    
    print("\n" + "=" * 60)
    print("Demo complete!")
    print("=" * 60)
    print("\nTo test resolution, uncomment demo_conflict_resolution()")


if __name__ == "__main__":
    main()
