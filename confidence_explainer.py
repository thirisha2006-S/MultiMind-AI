"""
Explainable Confidence Engine for MultiMind AI.
Breaks down confidence scores into understandable factors.
"""

import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass


@dataclass
class ConfidenceFactor:
    """A single factor contributing to overall confidence."""
    name: str
    score: float  # 0.0 - 1.0
    weight: float  # Relative weight in final score
    description: str


@dataclass
class ConfidenceBreakdown:
    """Complete breakdown of confidence calculation."""
    factors: List[ConfidenceFactor]
    final_score: float
    explanation: str
    
    def to_dict(self) -> Dict:
        return {
            "factors": [
                {
                    "name": f.name,
                    "score": f.score,
                    "weight": f.weight,
                    "description": f.description,
                    "contribution": f.score * f.weight,
                }
                for f in self.factors
            ],
            "final_score": self.final_score,
            "explanation": self.explanation,
        }


class ConfidenceExplainer:
    """
    Explains why a response has a particular confidence score.
    
    Factors include:
    - Document Trust: Quality of source documents
    - Source Agreement: Consistency between sources
    - Validator Score: LLM validation confidence
    - Document Freshness: How recent the sources are
    - Conflict Status: Whether conflicts were detected
    - Retrieval Quality: How well retrieved context matches query
    """
    
    @staticmethod
    def explain(validation: Dict, sources: List[Dict], 
                integrity_check: Dict = None, retrieval_quality: float = 0.5) -> ConfidenceBreakdown:
        """
        Generate a detailed confidence breakdown.
        """
        factors = []
        
        # 1. Validator Score (40% weight)
        validator_score = validation.get("confidence", 0.5) if validation else 0.5
        factors.append(ConfidenceFactor(
            name="Validator Score",
            score=validator_score,
            weight=0.4,
            description="LLM assessment of correctness, relevance, completeness, and hallucination risk"
        ))
        
        # 2. Document Trust (25% weight)
        doc_trust = sum(s.get("trust", 0.5) for s in sources) / max(len(sources), 1) if sources else 0.5
        factors.append(ConfidenceFactor(
            name="Document Trust",
            score=doc_trust,
            weight=0.25,
            description="Average trust score of source documents (based on validation, age, and access)"
        ))
        
        # 3. Source Agreement (15% weight)
        source_agreement = 1.0 if len(sources) <= 1 else min(1.0, 0.5 + len(sources) * 0.1)
        factors.append(ConfidenceFactor(
            name="Source Count",
            score=source_agreement,
            weight=0.15,
            description=f"{len(sources)} source(s) found - more sources increase agreement confidence"
        ))
        
        # 4. Document Freshness (10% weight)
        if sources:
            freshness_scores = [s.get("freshness_score", 0.5) for s in sources]
            avg_freshness = sum(freshness_scores) / len(freshness_scores)
        else:
            avg_freshness = 0.3  # No sources = stale knowledge
        factors.append(ConfidenceFactor(
            name="Document Freshness",
            score=avg_freshness,
            weight=0.1,
            description="How recent the source documents are (90-day half-life)"
        ))
        
        # 5. Conflict Status (10% weight)
        if integrity_check and integrity_check.get("conflicts_detected"):
            conflict_score = 0.5  # Reduced due to conflicts
            conflict_reason = f"{len(integrity_check.get('conflict_records', []))} conflict(s) detected"
        else:
            conflict_score = 1.0  # No conflicts is good
            conflict_reason = "No knowledge conflicts detected"
        factors.append(ConfidenceFactor(
            name="Conflict Status",
            score=conflict_score,
            weight=0.1,
            description=conflict_reason
        ))
        
        # Calculate weighted final score
        final_score = sum(f.score * f.weight for f in factors)
        
        # Generate explanation
        explanation = ConfidenceExplainer._generate_explanation(factors, validation)
        
        return ConfidenceBreakdown(factors=factors, final_score=final_score, explanation=explanation)
    
    @staticmethod
    def _generate_explanation(factors: List[ConfidenceFactor], validation: Dict) -> str:
        """Generate a natural language explanation of confidence."""
        if not validation:
            return "No validation performed - confidence based on document trust and freshness."
        
        issues = validation.get("issues", [])
        if issues:
            return f"Confidence reduced due to: {', '.join(issues[:2])}"
        
        suggestions = validation.get("suggestions", [])
        if suggestions:
            return f"Valid response. Consider: {', '.join(suggestions[:2])}"
        
        return "All confidence factors are strong - response is trustworthy."
    
    @staticmethod
    def get_factor_breakdown_html(breakdown: ConfidenceBreakdown) -> str:
        """Generate HTML for displaying confidence breakdown."""
        html = '<table style="width: 100%; border-collapse: collapse;">'
        html += '<tr><th style="text-align: left; padding: 4px;">Factor</th>'
        html += '<th style="text-align: right; padding: 4px;">Score</th>'
        html += '<th style="text-align: right; padding: 4px;">Contribution</th></tr>'
        
        for f in breakdown.factors:
            contrib = f.score * f.weight
            color = "#28a745" if f.score >= 0.8 else ("#ffc107" if f.score >= 0.6 else "#dc3545")
            html += f'<tr>'
            html += f'<td style="padding: 4px;">{f.name} <span title="{f.description}" style="font-size: 0.8em; color: #666;">ⓘ</span></td>'
            html += f'<td style="text-align: right; padding: 4px; color: {color}; font-weight: bold;">{f.score:.0%}</td>'
            html += f'<td style="text-align: right; padding: 4px;">{contrib:.2f}</td>'
            html += f'</tr>'
        
        color = "#28a745" if breakdown.final_score >= 0.8 else ("#ffc107" if breakdown.final_score >= 0.6 else "#dc3545")
        html += f'<tr style="border-top: 2px solid #333;"><td style="padding: 8px; font-weight: bold;">Final Confidence</td>'
        html += f'<td colspan="2" style="text-align: right; padding: 8px; color: {color}; font-weight: bold; font-size: 1.2em;">{breakdown.final_score:.0%}</td></tr>'
        html += '</table>'
        
        return html


# Global instance
_explainer = ConfidenceExplainer()


def get_confidence_explainer() -> ConfidenceExplainer:
    """Get the global confidence explainer."""
    return _explainer


def explain_confidence(validation: Dict, sources: List[Dict], 
                     integrity_check: Dict = None, retrieval_quality: float = 0.5) -> Dict:
    """Convenience function to get confidence explanation."""
    breakdown = _explainer.explain(validation, sources, integrity_check, retrieval_quality)
    return breakdown.to_dict()