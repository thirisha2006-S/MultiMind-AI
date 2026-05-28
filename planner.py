"""
Enhanced Planner Agent with self-improvement capabilities.
"""

import os
import json
from typing import Dict, Any, List, Optional
from langchain_core.messages import HumanMessage, SystemMessage
from state import SharedState
from memory import memory, rag_memory
from observability import trace_agent
from llm_utils import get_llm_instance


def get_llm(temperature: float = 0, model: str = "gpt-4"):
    """Get configured LLM instance - delegates to llm_utils."""
    return get_llm_instance(temperature, model)


def get_session_id(state: SharedState) -> str:
    """Get session ID from state."""
    return state.get("metadata", {}).get("session_id", "default_session")


class PolicyStore:
    """Stores learned planning policies for self-improvement."""
    
    def __init__(self):
        self.policies = {}  # pattern -> learned policy
    
    def get_policy(self, query: str) -> Optional[Dict]:
        """Get learned policy for similar queries."""
        # Simple similarity matching
        query_lower = query.lower()
        for pattern, policy in self.policies.items():
            if pattern in query_lower:
                return policy
        return None
    
    def update_policy(self, query: str, plan: List[Dict], success: bool):
        """Update policy based on execution outcome."""
        pattern = query.lower()[:30]  # First 30 chars as pattern
        if success:
            self.policies[pattern] = {
                "tasks": plan,
                "success_count": self.policies.get(pattern, {}).get("success_count", 0) + 1
            }


# Global policy store
policy_store = PolicyStore()


class TaskPlan:
    """Represents a decomposed task plan with metadata."""
    
    def __init__(self, tasks: List[Dict[str, Any]], reasoning: str = "", metadata: Dict = None):
        self.tasks = tasks
        self.reasoning = reasoning
        self.metadata = metadata or {}
        self.current_task_index = 0
    
    def next_task(self) -> Optional[Dict[str, Any]]:
        """Get the next task in the plan."""
        if self.current_task_index < len(self.tasks):
            task = self.tasks[self.current_task_index]
            self.current_task_index += 1
            return task
        return None
    
    def is_complete(self) -> bool:
        """Check if all tasks are completed."""
        return self.current_task_index >= len(self.tasks)


def assess_research_quality(content: str) -> float:
    """Assess quality of research content (0-1 score)."""
    if not content or "no results" in content.lower():
        return 0.0
    
    score = 0.5  # Base score
    
    # Length indicates detail
    if len(content) > 500:
        score += 0.2
    if len(content) > 1000:
        score += 0.1
    
    # Source citations improve quality
    if "http" in content or "url" in content.lower():
        score += 0.1
    
    # Structure indicates quality
    if "•" in content or "1." in content:
        score += 0.1
    
    return min(1.0, score)


@trace_agent("planner")
def planner_agent(state: SharedState) -> Dict[str, Any]:
    """
    Planner agent with self-learning capabilities.
    
    Compares current execution with past successful/failed attempts.
    """
    messages = state.get("messages", [])
    session_id = get_session_id(state)
    validation = state.get("validation", {})
    
    # Get the user's query
    query = ""
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            query = msg.content
            break
    
    # Check for learned policies from past executions
    learned_policy = policy_store.get_policy(query)
    
    # Check RAG memory for context, filtering to high-quality content
    rag_results = rag_memory.retrieve(query, k=5)
    
    # Filter low-quality memories
    high_quality_memories = [
        r for r in rag_results 
        if assess_research_quality(r["content"]) > 0.6
    ]
    
    context = "\n".join([r["content"][:150] for r in high_quality_memories[:2]])
    
    # If we have a learned successful policy, consider using it
    if learned_policy and learned_policy.get("success_count", 0) > 2:
        # Use learned policy as baseline
        tasks = learned_policy.get("tasks", [])
        reasoning = f"Using learned policy from {learned_policy.get('success_count', 0)} successful executions"
    else:
        # Normal planning - build messages directly to avoid template parsing issues
        system_content = """You are a planning agent. Break down the user's request into executable subtasks.

Available agent types:
- research_agent: For web searches, fact-finding, information gathering  
- coder_agent: For calculations, data processing, code execution

Output format (JSON):
{
    "tasks": [
        {"id": 1, "type": "research|coding", "description": "...", "priority": 1}
    ],
    "reasoning": "Explain why this plan makes sense"
}

Consider:
1. Dependencies between tasks
2. Optimal execution order
3. Resource efficiency"""
        
        user_content = f"User request: {query}\n\nPrevious context: {context}"
        
        messages = [
            SystemMessage(content=system_content),
            HumanMessage(content=user_content)
        ]
        
        try:
            llm = get_llm(temperature=0.3)
            response = llm.invoke(messages)
            
            plan_data = json.loads(response.content.strip())
            tasks = plan_data.get("tasks", [])
            reasoning = plan_data.get("reasoning", "")
            
        except Exception as e:
            tasks = [{"id": 1, "type": "research", "description": query, "priority": 1}]
            reasoning = f"Fallback plan due to error: {str(e)}"
    
    tasks.sort(key=lambda x: x.get("priority", 999))
    
    # Log and store for policy learning
    memory.log_execution(session_id, "planner", {"query": query}, {"plan": tasks})
    
    # Store policy if validation shows success
    if validation.get("is_valid", True) and validation.get("confidence", 0) > 0.7:
        policy_store.update_policy(query, tasks, success=True)
    
    return {
        "task_plan": tasks,
        "plan_reasoning": reasoning,
        "current_task_index": 0,
        "next": "supervisor",
        "planner_ran": True
    }