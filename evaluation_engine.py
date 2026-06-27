"""
Enterprise Evaluation Engine for MultiMind AI.
Automatically evaluates every response for quality, cost, and risk.
"""

import time
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class EvaluationMetrics:
    """Metrics for a single response evaluation."""
    latency_seconds: float
    retrieved_docs: int
    conflicts_detected: int
    hallucination_risk: str  # "low", "medium", "high"
    confidence: float
    cost_usd: float
    approval_required: bool
    sources_used: int
    
    def to_dict(self) -> Dict:
        return {
            "latency_seconds": self.latency_seconds,
            "retrieved_docs": self.retrieved_docs,
            "conflicts_detected": self.conflicts_detected,
            "hallucination_risk": self.hallucination_risk,
            "confidence": self.confidence,
            "cost_usd": self.cost_usd,
            "approval_required": self.approval_required,
            "sources_used": self.sources_used,
        }


class EvaluationEngine:
    """
    Evaluates every agent response automatically.
    
    Provides:
    - Latency tracking
    - Cost calculation
    - Quality scoring
    - Risk assessment
    """
    
    def __init__(self):
        self.metrics_history: list = []
    
    def evaluate(self, start_time: float, result: Dict, sources: list) -> EvaluationMetrics:
        """
        Evaluate a response.
        
        Args:
            start_time: Workflow start timestamp
            result: Final workflow result
            sources: List of source attributions
        
        Returns:
            EvaluationMetrics with all tracked metrics
        """
        latency = time.time() - start_time
        
        # Count retrieved docs
        retrieved_docs = len(result.get("research_data", [])) if result.get("research_data") else 0
        
        # Check conflicts
        conflicts = result.get("conflicts", [])
        conflicts_detected = len(conflicts) if conflicts else 0
        
        # Hallucination risk from validation
        validation = result.get("validation", {})
        if validation:
            hallucination_risk_score = validation.get("confidence_breakdown", {}).get("hallucination_risk", 0.5)
            if hallucination_risk_score > 0.7:
                hallucination_risk = "high"
            elif hallucination_risk_score > 0.4:
                hallucination_risk = "medium"
            else:
                hallucination_risk = "low"
        else:
            hallucination_risk = "low"
        
        # Confidence
        confidence = result.get("confidence", 0.5)
        
        # Cost (estimated)
        cost = result.get("cost_usd", 0.001)  # Default small cost
        
        # Approval required
        approval_required = result.get("pending_approval", False)
        
        metrics = EvaluationMetrics(
            latency_seconds=latency,
            retrieved_docs=retrieved_docs,
            conflicts_detected=conflicts_detected,
            hallucination_risk=hallucination_risk,
            confidence=confidence,
            cost_usd=cost,
            approval_required=approval_required,
            sources_used=len(sources),
        )
        
        self.metrics_history.append(metrics.to_dict())
        return metrics
    
    def get_summary(self) -> Dict:
        """Get evaluation summary statistics."""
        if not self.metrics_history:
            return {"total_queries": 0}
        
        total = len(self.metrics_history)
        avg_latency = sum(m["latency_seconds"] for m in self.metrics_history) / total
        avg_confidence = sum(m["confidence"] for m in self.metrics_history) / total
        total_conflicts = sum(m["conflicts_detected"] for m in self.metrics_history)
        total_cost = sum(m["cost_usd"] for m in self.metrics_history)
        
        return {
            "total_queries": total,
            "avg_latency_seconds": avg_latency,
            "avg_confidence": avg_confidence,
            "total_conflicts": total_conflicts,
            "total_cost": total_cost,
        }


# Global instance
_eval_engine: Optional[EvaluationEngine] = None


def get_evaluation_engine() -> EvaluationEngine:
    """Get the global evaluation engine."""
    global _eval_engine
    if _eval_engine is None:
        _eval_engine = EvaluationEngine()
    return _eval_engine


def evaluate_response(start_time: float, result: Dict, sources: list) -> Dict:
    """Convenience function to evaluate a response."""
    engine = get_evaluation_engine()
    return engine.evaluate(start_time, result, sources).to_dict()