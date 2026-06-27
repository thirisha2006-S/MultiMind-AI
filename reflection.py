"""
Reflection Agent for workflow analysis and self-improvement.
Enables the system to learn from its own execution patterns.
"""

import os
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from langchain_core.messages import HumanMessage, SystemMessage
from state import SharedState, SourceAttribution
from memory import memory, rag_memory
from observability import trace_agent
from llm_utils import get_llm_instance
from rbac import get_rbac_manager, Action
from security import get_security_scanner


def get_llm(temperature: float = 0, model: str = "gpt-4"):
    """Get configured LLM instance - delegates to llm_utils."""
    return get_llm_instance(temperature, model)


def get_session_id(state: SharedState) -> str:
    """Get session ID from state."""
    return state.get("metadata", {}).get("session_id", "default_session")


def get_user_id(state: SharedState) -> Optional[str]:
    """Get user ID from state."""
    user = state.get("user")
    return user.get("user_id") if user else None


def add_source(state: SharedState, source: SourceAttribution):
    """Add a source attribution to state."""
    sources = state.get("sources", [])
    sources.append(source)
    state["sources"] = sources


def log_audit(state: SharedState, action: str, details: Dict = None):
    """Log audit event for current user."""
    user = state.get("user", {})
    user_id = user.get("user_id", "unknown")
    session_id = user.get("session_id", get_session_id(state))
    
    scanner = get_security_scanner()
    scanner.audit_logger.log_action(
        user_id=user_id,
        session_id=session_id,
        agent="reflection",
        action=action,
        details=details or {},
    )


@trace_agent("reflection")
def reflection_agent(state: SharedState) -> Dict[str, Any]:
    """
    Reflection agent that analyzes workflow execution and extracts learnings.
    
    Analyzes:
    - Planning effectiveness
    - Retrieval relevance
    - Execution efficiency
    - Validation accuracy
    - Memory utility
    
    Now also handles Knowledge Evolution queries.
    
    Args:
        state: Current shared state after workflow completion
    
    Returns:
        Updated state with reflection insights
    """
    messages = state.get("messages", [])
    research_data = state.get("research_data", "")
    code_result = state.get("code_result", "")
    validation = state.get("validation", {})
    task_plan = state.get("task_plan", [])
    sources = state.get("sources", [])
    session_id = get_session_id(state)
    user_id = get_user_id(state)
    
    log_audit(state, "reflection_started", {
        "has_research": bool(research_data),
        "has_code": bool(code_result),
        "source_count": len(sources),
    })
    
    # Get the original query
    query = ""
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            query = msg.content
            break
    
    # Check for evolution query patterns
    evolution_keywords = ["evolution", "history", "changed", "timeline", "over time", "versions", "how has"]
    is_evolution_query = any(kw in query.lower() for kw in evolution_keywords)
    
    evolution_timeline = None
    if is_evolution_query:
        try:
            from knowledge_evolution import get_knowledge_timeline
            evolution_timeline = get_knowledge_timeline(query)
        except Exception as e:
            logger.debug(f"[Evolution] Timeline lookup failed: {e}")
    
     # Get execution metrics
    validation_confidence = validation.get("confidence", 0.5) if validation else 0.5
    has_research = bool(research_data and "No research" not in research_data)
    has_code = bool(code_result and "failed" not in code_result.lower())
    
    # Determine final answer early so it's available even if LLM fails
    final_answer = ""
    
    # Handle evolution queries specially
    if is_evolution_query and evolution_timeline:
        timeline = evolution_timeline
        versions = timeline.get("versions", [])
        
        if versions:
            final_answer = f"# Knowledge Evolution Timeline: {timeline.get('topic', query)}\n\n"
            for v in versions:
                ts = datetime.fromtimestamp(v['timestamp']).strftime('%Y-%m-%d')
                final_answer += f"## {ts} — {v['source']} (Trust: {v['trust_score']:.0%})\n"
                final_answer += f"{v['content']}\n\n"
            
            changes = timeline.get("changes", [])
            if changes:
                final_answer += "## Changes Detected\n"
                for c in changes:
                    final_answer += f"- {c['summary']}\n"
        else:
            final_answer = f"No evolution data found for: {query}"
    elif has_research:
        final_answer = research_data[:1000]
    elif has_code:
        final_answer = code_result
    else:
        final_answer = "Workflow completed with limited results."
    
    # Add source summary to final answer
    if sources:
        source_summary = "\n\n--- Sources ---\n"
        for src in sources[:5]:
            source_summary += f"- [{src.get('source_type', 'unknown')}] {src.get('source_name', 'Unknown')} (confidence: {src.get('confidence', 0):.2f})\n"
        final_answer += source_summary
    
    # Build messages directly to avoid template parsing issues with braces
    # Build messages directly to avoid template parsing issues with braces
    system_content = """You are a reflection agent. Analyze the completed workflow and provide insights.

Analyze:
1. Planning Quality - Was the plan appropriate? Could it be better?
2. Retrieval Effectiveness - Was the retrieved context useful?
3. Execution Efficiency - Were the right agents used at the right time?
4. Validation Accuracy - Did validation catch issues appropriately?
5. Memory Utility - Should relevant knowledge be stored or forgotten?
6. Source Quality - Were sources reliable and sufficient?

Output JSON format:
{
    "workflow_quality": 0.0-1.0 score,
    "planning_feedback": "improvement suggestions",
    "retrieval_quality": "relevant/irrelevant/mixed",
    "execution_efficiency": "optimal/inefficient",
    "memory_updates": ["knowledge to store"],
    "next_iteration_tips": ["what to do differently"],
    "confidence_assessment": "high/medium/low"
}"""
    
    user_content = f"""
Workflow Summary:
- Query: {query}
- Plan: {task_plan}
- Research: {has_research}
- Code: {has_code}
- Validation Confidence: {validation_confidence}
- Sources Used: {len(sources)}

Analyze and provide JSON reflection:"""
    
    messages = [
        SystemMessage(content=system_content),
        HumanMessage(content=user_content)
    ]
    
    try:
        llm = get_llm(temperature=0.5)
        response = llm.invoke(messages)
        
        # Parse reflection
        import json
        try:
            reflection = json.loads(response.content.strip())
        except json.JSONDecodeError:
            reflection = {
                "workflow_quality": 0.7,
                "planning_feedback": "Unable to parse reflection",
                "retrieval_quality": "unknown",
                "execution_efficiency": "unknown",
                "memory_updates": [],
                "next_iteration_tips": [],
                "confidence_assessment": "medium",
            }
        
        # Store reflection insights in memory with provenance
        insights_to_store = reflection.get("memory_updates", [])
        for insight in insights_to_store:
            if insight:
                rag_memory.add_knowledge(
                    f"Workflow Insight: {insight}\nContext: {query}",
                    {
                        "type": "reflection_insight",
                        "session_id": session_id,
                        "agent_source": "reflection",
                        "iteration": 0,
                        "user_id": user_id,
                    }
                )
        
        # Log reflection
        memory.log_execution(session_id, "reflection", {
            "query": query,
            "plan": task_plan,
            "validation": validation,
            "sources": len(sources),
        }, {"reflection": reflection})
        
        log_audit(state, "reflection_completed", {
            "workflow_quality": reflection.get("workflow_quality", 0.7),
            "source_count": len(sources),
        })
        
        # Determine next step based on reflection quality
        workflow_quality = reflection.get("workflow_quality", 0.7)
        confidence_assessment = reflection.get("confidence_assessment", "medium")
        
        if workflow_quality < 0.5 or confidence_assessment == "low":
            # Poor execution, might need human review
            return {
                "reflection": reflection,
                "final_answer": final_answer,
                "workflow_quality": workflow_quality,
                "requires_human_review": True,
                "next": "END",
                "approval_required_for": "low_quality_reflection"
            }
        
        # Add overall confidence from validation
        state["confidence"] = validation_confidence
        
        # Include evolution data in state if present
        if evolution_timeline:
            state["evolution_timeline"] = evolution_timeline
        
        # If we have sources, mark as sourced
        if sources:
            state["sources"] = sources
        
        return {
            "reflection": reflection,
            "final_answer": final_answer,
            "workflow_quality": workflow_quality,
            "confidence": validation_confidence,
            "requires_human_review": False,
            "next": "END"
        }
        
    except Exception as e:
        # Compute final_answer even on error
        final_answer = ""
        if research_data and "No research" not in research_data:
            final_answer = research_data[:1000]
        elif code_result and "failed" not in code_result.lower():
            final_answer = code_result
        else:
            final_answer = "Workflow completed with limited results."
        
        log_audit(state, "reflection_error", {"error": str(e)})
        
        return {
            "reflection": {
                "workflow_quality": 0.5,
                "planning_feedback": f"Reflection error: {str(e)}",
                "retrieval_quality": "unknown",
                "execution_efficiency": "unknown",
                "memory_updates": [],
                "next_iteration_tips": ["Manual review recommended"],
                "confidence_assessment": "medium",
            },
            "final_answer": final_answer,
            "workflow_quality": 0.5,
            "requires_human_review": False,
            "next": "END"
        }