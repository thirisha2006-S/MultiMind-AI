"""
Reflection Agent for workflow analysis and self-improvement.
Enables the system to learn from its own execution patterns.
"""

import os
from typing import Dict, Any, List, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from state import SharedState
from memory import memory, rag_memory
from observability import trace_agent


def get_llm(temperature: float = 0, model: str = "gpt-4"):
    """Get configured LLM instance."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is required")
    return ChatOpenAI(api_key=api_key, model=model, temperature=temperature)


def get_session_id(state: SharedState) -> str:
    """Get session ID from state."""
    return state.get("metadata", {}).get("session_id", "default_session")


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
    session_id = get_session_id(state)
    
    # Get the original query
    query = ""
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            query = msg.content
            break
    
     # Get execution metrics
    validation_confidence = validation.get("confidence", 0.5) if validation else 0.5
    has_research = bool(research_data and "No research" not in research_data)
    has_code = bool(code_result and "failed" not in code_result.lower())
    
    # Determine final answer early so it's available even if LLM fails
    final_answer = ""
    if research_data and "No research" not in research_data:
        final_answer = research_data[:1000]
    elif code_result and "failed" not in code_result.lower():
        final_answer = code_result
    else:
        final_answer = "Workflow completed with limited results."
    
    # Build messages directly to avoid template parsing issues with braces
    system_content = """You are a reflection agent. Analyze the completed workflow and provide insights.

Analyze:
1. Planning Quality - Was the plan appropriate? Could it be better?
2. Retrieval Effectiveness - Was the retrieved context useful?
3. Execution Efficiency - Were the right agents used at the right time?
4. Validation Accuracy - Did validation catch issues appropriately?
5. Memory Utility - Should relevant knowledge be stored or forgotten?

Output JSON format:
{
    "workflow_quality": 0.0-1.0 score,
    "planning_feedback": "improvement suggestions",
    "retrieval_quality": "relevant/irrelevant/mixed",
    "execution_efficiency": "optimal/inefficient",
    "memory_updates": ["knowledge to store"],
    "next_iteration_tips": ["what to do differently"]
}"""
    
    user_content = f"""
Workflow Summary:
- Query: {query}
- Plan: {task_plan}
- Research: {has_research}
- Code: {has_code}
- Validation Confidence: {validation_confidence}

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
                "next_iteration_tips": []
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
                        "iteration": 0
                    }
                )
        
        # Log reflection
        memory.log_execution(session_id, "reflection", {
            "query": query,
            "plan": task_plan,
            "validation": validation
        }, {"reflection": reflection})
        
        # Determine next step based on reflection quality
        workflow_quality = reflection.get("workflow_quality", 0.7)
        
        if workflow_quality < 0.5:
            # Poor execution, might need human review
            return {
                "reflection": reflection,
                "final_answer": final_answer,
                "requires_human_review": True,
                "next": "END"
            }
        
        return {
            "reflection": reflection,
            "final_answer": final_answer,
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
        
        return {
            "reflection": {
                "workflow_quality": 0.5,
                "planning_feedback": f"Reflection error: {str(e)}",
                "retrieval_quality": "unknown",
                "execution_efficiency": "unknown",
                "memory_updates": [],
                "next_iteration_tips": ["Manual review recommended"]
            },
            "final_answer": final_answer,
            "requires_human_review": False,
            "next": "END"
        }