"""
Enhanced state definitions with enterprise features.
"""

from typing import Annotated, List, Optional, Dict, Any
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


class ValidationResult(TypedDict):
    """Validation result from the validator agent."""
    is_valid: bool
    confidence: float
    confidence_breakdown: Dict[str, float]
    issues: List[str]
    suggestions: List[str]
    source_type: str  # "internal", "web", "llm", "mixed"


class SourceAttribution(TypedDict):
    """Represents a source attribution."""
    source_type: str  # "internal_document", "web_search", "llm_generation"
    source_name: str
    url: Optional[str]
    page: Optional[str]
    timestamp: str
    confidence: float
    agent: str


class SecurityCheckResult(TypedDict):
    """Security scan result."""
    is_safe: bool
    prompt_injection_detected: bool
    pii_detected: bool
    sql_injection_detected: bool
    blocked: bool
    warnings: List[str]
    scan_details: Dict[str, Any]


class UserContext(TypedDict):
    """User context for RBAC."""
    user_id: str
    username: str
    role: str
    department: Optional[str]
    session_id: str


class KnowledgeIntegrityResult(TypedDict):
    """Result from the Knowledge Integrity Engine."""
    conflicts_detected: bool
    conflict_records: List[Dict[str, Any]]
    recommended_source: Optional[str]
    confidence_adjustment: float  # e.g., -0.2 if conflict detected
    requires_human_resolution: bool
    knowledge_health_score: float


class SharedState(TypedDict):
    """
    Shared state for the MultiMind AI enterprise knowledge assistant.
    
    Includes support for:
    - Multi-agent orchestration
    - Task planning and decomposition
    - Workflow validation
    - Self-reflection and learning
    - Human approval workflow
    - RBAC and security
    - Source attribution and confidence
    - Knowledge Integrity Engine
    """
    # Core
    messages: Annotated[List[BaseMessage], add_messages]
    next: Optional[str]
    current_step: Optional[str]
    task_type: Optional[str]
    
    # Execution outputs
    research_data: Optional[str]
    code_result: Optional[str]
    final_answer: Optional[str]
    
    # Validation
    validation: Optional[ValidationResult]
    
    # Retry control
    retry_count: int
    max_retries: int
    error: Optional[str]
    
    # Metadata
    requires_human_review: bool
    metadata: Dict[str, Any]
    
    # User context (RBAC)
    user: Optional[UserContext]
    
    # Planner fields
    task_plan: Optional[List[Dict[str, Any]]]
    plan_reasoning: Optional[str]
    current_task_index: int
    planner_ran: bool
    
    # Reflection fields
    reflection: Optional[Dict[str, Any]]
    workflow_quality: float
    
    # Enterprise features
    sources: List[SourceAttribution]
    confidence: float
    
    # Adaptive execution flag
    adaptive_skipped: bool
    
    # Human approval workflow
    pending_approval: bool
    approval_request_id: Optional[str]
    approval_required_for: Optional[str]
    
    # Security
    security_scan: Optional[SecurityCheckResult]
    
    # Feedback
    feedback_collected: bool
    feedback_id: Optional[str]
    
    # Knowledge Integrity Engine
    integrity_check: Optional[KnowledgeIntegrityResult]
    conflicts: List[Dict[str, Any]]
    knowledge_health_score: float
    
    # Knowledge Evolution
    evolution_timeline: Optional[Dict[str, Any]]
