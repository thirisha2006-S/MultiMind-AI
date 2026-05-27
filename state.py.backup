"""
Enhanced state definitions with planning and reflection support.
"""

from typing import Annotated, List, Optional, Dict, Any
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


class ValidationResult(TypedDict):
    """Validation result from the validator agent."""
    is_valid: bool
    confidence: float
    issues: List[str]
    suggestions: List[str]


class SharedState(TypedDict):
    """
    Shared state for the autonomous AI workflow system.
    
    Includes support for:
    - Multi-agent orchestration
    - Task planning and decomposition
    - Workflow validation
    - Self-reflection and learning
    """
    messages: Annotated[List[BaseMessage], add_messages]
    next: Optional[str]
    current_step: Optional[str]
    task_type: Optional[str]
    research_data: Optional[str]
    code_result: Optional[str]
    final_answer: Optional[str]
    validation: Optional[ValidationResult]
    retry_count: int
    max_retries: int
    error: Optional[str]
    requires_human_review: bool
    metadata: Dict[str, Any]
    # Planner fields
    task_plan: Optional[List[Dict[str, Any]]]
    plan_reasoning: Optional[str]
    current_task_index: int
    planner_ran: bool
    # Reflection fields
    reflection: Optional[Dict[str, Any]]
    workflow_quality: float