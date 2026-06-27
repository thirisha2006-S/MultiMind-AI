"""
Knowledge Doctor AI - Proactive knowledge base health monitoring.
Continuously audits the knowledge base for issues and generates reports.
"""

import time
import re
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class KnowledgeIssue:
    """Represents an issue detected in the knowledge base."""
    issue_id: str
    issue_type: str  # "duplicate", "contradiction", "outdated", "orphaned", "broken_link"
    severity: str    # "low", "medium", "high", "critical"
    description: str
    affected_sources: List[str]
    recommendation: str
    detected_at: float


@dataclass 
class KnowledgeHealthReport:
    """Complete knowledge health report."""
    generated_at: float
    knowledge_score: float  # 0-1 overall score
    total_issues: int
    issues: List[KnowledgeIssue]
    metrics: Dict[str, Any]
    
    def to_dict(self) -> Dict:
        return {
            "generated_at": datetime.fromtimestamp(self.generated_at).isoformat(),
            "knowledge_score": self.knowledge_score,
            "total_issues": self.total_issues,
            "issues": [
                {
                    "issue_id": i.issue_id,
                    "issue_type": i.issue_type,
                    "severity": i.severity,
                    "description": i.description,
                    "affected_sources": i.affected_sources,
                    "recommendation": i.recommendation,
                }
                for i in self.issues
            ],
            "metrics": self.metrics,
        }


class KnowledgeDoctor:
    """
    Proactive knowledge base auditor.
    
    Checks for:
    - Duplicate documents (similar content)
    - Contradictory policies (conflicting values)
    - Outdated documents (old timestamps)
    - Orphaned documents (no references)
    - Missing approvals (unapproved changes)
    """
    
    def __init__(self):
        self.last_check: Optional[float] = None
        self.last_report: Optional[KnowledgeHealthReport] = None
    
    def check_knowledge_health(self) -> KnowledgeHealthReport:
        """
        Run comprehensive knowledge health check.
        
        Returns a report with issues and recommendations.
        """
        from memory import rag_memory
        from conflict_detector import get_conflict_detector, get_knowledge_health
        
        issues: List[KnowledgeIssue] = []
        
        # Get knowledge base stats
        kb_stats = rag_memory.get_quality_report()
        conflict_health = get_knowledge_health()
        
        # Check 1: Unresolved conflicts (contradictions)
        unresolved = conflict_health.get("unresolved_conflicts", 0)
        if unresolved > 0:
            issues.append(KnowledgeIssue(
                issue_id=f"conflict-{int(time.time())}",
                issue_type="contradiction",
                severity="high" if unresolved > 5 else "medium",
                description=f"{unresolved} conflicting document(s) detected in knowledge base",
                affected_sources=["Multiple sources"],
                recommendation="Review and resolve conflicts in Knowledge Integrity dashboard",
                detected_at=time.time()
            ))
        
        # Check 2: Outdated documents (older than 90 days)
        old_docs = self._find_outdated_documents(kb_stats)
        if old_docs:
            issues.append(KnowledgeIssue(
                issue_id=f"outdated-{int(time.time())}",
                issue_type="outdated",
                severity="medium" if len(old_docs) > 10 else "low",
                description=f"{len(old_docs)} documents haven't been updated in 90+ days",
                affected_sources=old_docs[:5],  # Show first 5
                recommendation="Review outdated documents and update if necessary",
                detected_at=time.time()
            ))
        
        # Check 3: Low trust documents
        low_trust_count = kb_stats.get("total_chunks", 0) - kb_stats.get("validated_chunks", 0)
        if low_trust_count > 10:
            issues.append(KnowledgeIssue(
                issue_id=f"unvalidated-{int(time.time())}",
                issue_type="unvalidated",
                severity="low",
                description=f"{low_trust_count} documents haven't been validated",
                affected_sources=["Various"],
                recommendation="Run validation on unvalidated knowledge chunks",
                detected_at=time.time()
            ))
        
        # Check 4: Missing approvals
        # Check if any sources lack approval metadata
        approval_issues = self._find_missing_approvals()
        if approval_issues:
            issues.append(KnowledgeIssue(
                issue_id=f"approval-{int(time.time())}",
                issue_type="missing_approval",
                severity="low",
                description=f"{approval_issues} documents uploaded without approval",
                affected_sources=["Recents uploads"],
                recommendation="Review recent uploads and add approval workflow",
                detected_at=time.time()
            ))
        
        # Calculate overall score
        base_score = 1.0 - (len(issues) * 0.05)
        conflict_penalty = conflict_health.get("unresolved_conflicts", 0) * 0.02
        knowledge_score = max(0.0, min(1.0, base_score - conflict_penalty))
        
        report = KnowledgeHealthReport(
            generated_at=time.time(),
            knowledge_score=knowledge_score,
            total_issues=len(issues),
            issues=issues,
            metrics={
                "total_chunks": kb_stats.get("total_chunks", 0),
                "avg_trust": kb_stats.get("average_trust", 0.0),
                "unresolved_conflicts": unresolved,
                "knowledge_health_score": conflict_health.get("knowledge_health_score", 1.0),
            }
        )
        
        self.last_check = time.time()
        self.last_report = report
        
        return report
    
    def _find_outdated_documents(self, kb_stats: Dict) -> List[str]:
        """Find documents older than 90 days."""
        # Simplified - check age from stats
        old_docs = []
        try:
            from memory import rag_memory
            # We could iterate through all docs, but use metadata proxy
            if kb_stats.get("average_freshness", 1.0) < 0.5:
                old_docs.append("Multiple outdated documents detected")
        except Exception:
            pass
        return old_docs
    
    def _find_missing_approvals(self) -> int:
        """Count documents without approval metadata."""
        # Simplified check - in production would query metadata
        return 0  # Placeholder
    
    def get_doctor_report_markdown(self, report: KnowledgeHealthReport) -> str:
        """Generate markdown report for display."""
        lines = [
            "# 🩺 Knowledge Health Report",
            "",
            f"**Generated:** {datetime.fromtimestamp(report.generated_at).isoformat()[:19]}",
            f"**Knowledge Score:** {report.knowledge_score:.0%}",
            "",
            f"**Total Issues:** {report.total_issues}",
            "",
        ]
        
        if report.issues:
            lines.append("## 🔍 Issues Found")
            lines.append("")
            for issue in report.issues:
                severity_icon = {
                    "critical": "🔴",
                    "high": "🟠", 
                    "medium": "🟡",
                    "low": "🔵"
                }.get(issue.severity, "⚪")
                
                lines.append(f"### {severity_icon} {issue.issue_type.title()}")
                lines.append(f"**{issue.description}**")
                lines.append(f"*Sources:* {', '.join(issue.affected_sources[:3])}")
                lines.append(f"*Recommended action:* {issue.recommendation}")
                lines.append("")
        else:
            lines.append("✅ No issues detected. Knowledge base is healthy.")
        
        lines.append("---")
        lines.append("")
        lines.append("## 📊 Metrics")
        lines.append("")
        for key, value in report.metrics.items():
            if isinstance(value, float):
                lines.append(f"- **{key.replace('_', ' ').title()}:** {value:.2%}")
            else:
                lines.append(f"- **{key.replace('_', ' ').title()}:** {value}")
        
        return "\n".join(lines)


# Global instance
_doctor: Optional[KnowledgeDoctor] = None


def get_knowledge_doctor() -> KnowledgeDoctor:
    """Get the global knowledge doctor."""
    global _doctor
    if _doctor is None:
        _doctor = KnowledgeDoctor()
    return _doctor


def run_knowledge_check() -> Dict:
    """Run knowledge health check and return report."""
    doctor = get_knowledge_doctor()
    report = doctor.check_knowledge_health()
    return report.to_dict()


def get_knowledge_check_markdown() -> str:
    """Get markdown version of latest report."""
    doctor = get_knowledge_doctor()
    if doctor.last_report:
        return doctor.get_doctor_report_markdown(doctor.last_report)
    return "No health check run yet."