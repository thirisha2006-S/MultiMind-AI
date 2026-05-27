"""
Enhanced agents with Planner integration and improved validation.
"""

import os
from typing import Dict, Any, Literal, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from tools import get_tavily_tool, python_repl, get_mcp_tools, mcp_tool_invoker
from state import SharedState, ValidationResult
from memory import memory, rag_memory
from planner import planner_agent
from observability import trace_agent


def get_llm(temperature: float = 0, model: str = "gpt-4") -> ChatOpenAI:
    """Get configured LLM instance."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is required")
    
    return ChatOpenAI(
        api_key=api_key,
        model=model,
        temperature=temperature
    )


def get_session_id(state: SharedState) -> str:
    """Get or create session ID from state."""
    return state.get("metadata", {}).get("session_id", "default_session")


# Supervisor Agent with Planner Integration
@trace_agent("supervisor")
def supervisor_agent(state: SharedState) -> Dict[str, Any]:
    """
    Supervisor agent with planner integration and semantic routing.
    """
    messages = state.get("messages", [])
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 3)
    session_id = get_session_id(state)
    
    # Log execution
    memory.log_execution(session_id, "supervisor", {}, {"status": "routing"})
    
    # Check retry limit
    if retry_count >= max_retries:
        return {"next": "END", "error": "Maximum retries exceeded"}
    
    # Check if planner already ran
    if state.get("planner_ran") and state.get("task_plan"):
        # Get next task from plan
        tasks = state.get("task_plan", [])
        current_idx = state.get("current_task_index", 0)
        
        if current_idx < len(tasks):
            next_task = tasks[current_idx]
            task_type = next_task.get("type", "research")
            
            return {
                "next": "research_agent" if task_type == "research" else "coder_agent",
                "task_type": task_type,
                "current_task_index": current_idx,
                "retry_count": 0
            }
        else:
            # All planner tasks done, validate quality first
            return {"next": "validator"}
    
    # Check validation completion
    if state.get("validation"):
        return {"next": "END"}
    
    # Check if we have any execution results ready for validation
    if state.get("research_data") or state.get("code_result"):
        return {"next": "validator"}
    
    if not messages:
        return {"next": "END"}
    
    last_message = messages[-1]
    query = last_message.content if hasattr(last_message, 'content') else ""
    
    # Complex query detection - route to planner
    complexity_keywords = ["compare", "analyze", "find and", "research and", "multiple", "both", "and then"]
    is_complex = any(kw in query.lower() for kw in complexity_keywords) or len(query) > 100
    
    if is_complex and not state.get("planner_ran"):
        return {"next": "planner"}
    
    # Check RAG memory for relevant context
    rag_results = rag_memory.retrieve(query, k=2)
    context = "\n".join([r["content"][:200] for r in rag_results]) if rag_results else ""
    
    # LLM-based task classification
    try:
        llm = get_llm(temperature=0)
        classification_prompt = ChatPromptTemplate.from_messages([
            ("system", """Classify the user query into one of these categories:
                - research: Questions about facts, current events, web search, comparisons
                - coding: Calculations, code execution, data processing, algorithm tasks
                - general: General questions, greetings, unclear requests
                
                Return only the category name."""),
            ("user", query)
        ])
        
        response = llm.invoke(classification_prompt.format_messages())
        category = response.content.strip().lower()
        
        result = {
            "next": "research_agent" if "research" in category else "coder_agent",
            "retry_count": retry_count,
            "task_type": category.split()[0] if category else "research",
            "rag_context": context
        }
        
        # Store in RAG memory if we have research data
        if state.get("research_data"):
            rag_memory.add_knowledge(state["research_data"], {"session_id": session_id})
        
        return result
    except Exception as e:
        if any(kw in query.lower() for kw in ["search", "find", "who", "what", "when", "where", "why"]):
            return {"next": "research_agent", "retry_count": retry_count}
        elif any(kw in query.lower() for kw in ["calculate", "compute", "solve", "code", "program"]):
            return {"next": "coder_agent", "retry_count": retry_count}
        return {"next": "research_agent", "retry_count": retry_count}


# Validator Agent
@trace_agent("validator")
def validator_agent(state: SharedState) -> Dict[str, Any]:
    """
    Validator agent with fact-checking and hallucination detection.
    """
    messages = state.get("messages", [])
    research_data = state.get("research_data", "No research performed")
    code_result = state.get("code_result", "No code executed")
    session_id = get_session_id(state)
    
    # Check RAG memory for previous related knowledge
    last_msg = messages[-1].content if messages else ""
    rag_knowledge = rag_memory.retrieve(last_msg, k=3)
    rag_context = "\n".join([k["content"][:150] for k in rag_knowledge]) if rag_knowledge else "None"
    
    # Build messages directly to avoid template parsing issues with braces
    system_content = f"""You are a validator agent. Evaluate outputs for:
1. Correctness - Are results accurate? Cross-check with known facts.
2. Relevance - Do they answer the original question?
3. Completeness - Is critical information missing?
4. Hallucination Risk - Are claims fabricated?

Previous knowledge: {rag_context}

Return JSON:
- is_valid: boolean
- confidence: 0-1 score
- issues: list of problems
- suggestions: list of improvements"""
    
    user_content = f"""
Original question: {messages[-1].content if messages else "N/A"}
Research results: {research_data}
Code results: {code_result}

Validate and return JSON:"""
    
    messages_llm = [
        SystemMessage(content=system_content),
        HumanMessage(content=user_content)
    ]
    
    try:
        llm = get_llm(temperature=0.3)
        response = llm.invoke(messages_llm)
        
        # Parse LLM's JSON validation result
        import json
        try:
            llm_validation = json.loads(response.content.strip())
            validation: ValidationResult = {
                "is_valid": llm_validation.get("is_valid", True),
                "confidence": llm_validation.get("confidence", 0.85),
                "issues": llm_validation.get("issues", []),
                "suggestions": llm_validation.get("suggestions", [])
            }
        except (json.JSONDecodeError, AttributeError):
            # Fallback if LLM output is invalid
            validation = {
                "is_valid": True,
                "confidence": 0.7,
                "issues": ["Could not parse LLM validation output"],
                "suggestions": ["Manual review recommended"]
            }
        
        # Store validated research in RAG memory with governance metadata
        if research_data and "No research" not in research_data:
            rag_memory.add_knowledge(research_data, {
                "type": "validated_research",
                "session_id": session_id,
                "agent_source": "validator",
                "validated": True,
                "validation_score": validation.get("confidence", 0.85)
            })
        
        memory.log_execution(session_id, "validator", {"research": research_data, "code": code_result}, 
                           {"validation": validation})
        
        return {
            "validation": validation,
            "next": "reflection" if validation["confidence"] > 0.7 else "supervisor",
            "retry_count": 0
        }
    except Exception as e:
        validation: ValidationResult = {
            "is_valid": True,
            "confidence": 0.5,
            "issues": [f"Validation error: {str(e)}"],
            "suggestions": ["Manual review recommended"]
        }
        return {"validation": validation, "next": "reflection"}


# Research Agent with RAG Integration
@trace_agent("research")
def research_agent(state: SharedState) -> Dict[str, Any]:
    """
    Research agent with FAISS memory storage.
    """
    messages = state.get("messages", [])
    retry_count = state.get("retry_count", 0)
    session_id = get_session_id(state)
    
    # Check if this is a planned task
    tasks = state.get("task_plan") or []
    current_idx = state.get("current_task_index", 0)
    if current_idx >= 0 and current_idx < len(tasks):
        task_desc = tasks[current_idx].get("description", "")
    else:
        task_desc = ""
    
    query = ""
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            query = msg.content
            break
    
    search_query = task_desc or query
    
    if not search_query:
        search_query = state.get("current_step", "general research")
    
    try:
        search_results = get_tavily_tool().invoke({"query": search_query})
        
        formatted_results = "Research Results:\n\n"
        if isinstance(search_results, list):
            for i, result in enumerate(search_results, 1):
                if isinstance(result, dict):
                    formatted_results += f"{i}. {result.get('title', 'Untitled')}\n"
                    formatted_results += f"   URL: {result.get('url', 'N/A')}\n"
                    formatted_results += f"   Content: {result.get('content', 'N/A')[:200]}...\n\n"
        
        # Store in RAG memory with provenance
        rag_memory.add_knowledge(formatted_results, {
            "type": "research",
            "session_id": session_id,
            "agent_source": "research",
            "iteration": state.get("current_task_index", 0)
        })
        
        result = {
            "research_data": formatted_results,
            "current_step": "research_complete",
            "next": "supervisor",
            "retry_count": 0
        }
        
        # Update task index if using plan
        if state.get("planner_ran") and state.get("task_plan"):
            result["current_task_index"] = state.get("current_task_index", 0) + 1
        
        return result
    except Exception as e:
        if retry_count < state.get("max_retries", 3):
            return {
                "error": f"Research failed (attempt {retry_count + 1}): {str(e)}",
                "retry_count": retry_count + 1,
                "next": "research_agent"
            }
        return {
            "research_data": f"Research failed after {retry_count} attempts: {str(e)}",
            "current_step": "research_failed",
            "next": "validator"
        }


# Coder Agent with Error Handling
@trace_agent("coder")
def coder_agent(state: SharedState) -> Dict[str, Any]:
    """
    Coder agent that executes Python code with error handling.
    """
    messages = state.get("messages", [])
    retry_count = state.get("retry_count", 0)
    
    # Check if this is a planned task
    tasks = state.get("task_plan") or []
    current_idx = state.get("current_task_index", 0)
    if current_idx >= 0 and current_idx < len(tasks):
        task_desc = tasks[current_idx].get("description", "")
    else:
        task_desc = ""
    
    task = ""
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            task = msg.content
            break
    
    code_task = task_desc or task
    
    if not code_task:
        code_task = state.get("current_step", "print('Hello, World!')")
    
    try:
        # First check if this is an MCP tool invocation request
        if code_task.startswith("MCP:"):
            # Format: MCP:server_name:tool_name:json_arguments
            parts = code_task.split(":", 3)
            if len(parts) >= 4:
                _, server_name, tool_name, json_args = parts
                try:
                    import json
                    args_dict = json.loads(json_args) if json_args else {}
                    result = mcp_tool_invoker(server_name, tool_name, json_args)
                    result_data = {
                        "code_result": result,
                        "current_step": "mcp_tool_complete",
                        "next": "supervisor",
                        "retry_count": 0
                    }
                    # Update task index if using plan
                    if state.get("planner_ran") and state.get("task_plan"):
                        result_data["current_task_index"] = state.get("current_task_index", 0) + 1
                    return result_data
                except Exception as e:
                    return {
                        "error": f"MCP tool invocation failed: {str(e)}",
                        "retry_count": retry_count + 1,
                        "next": "coder_agent"
                    }
            else:
                # Fallback to regular code execution if MCP format is invalid
                result = python_repl(code_task)
        else:
            result = python_repl(code_task)
        
        result_data = {
            "code_result": result,
            "current_step": "code_complete",
            "next": "supervisor",
            "retry_count": 0
        }
        
        # Store successful code execution as validated knowledge
        if "error" not in result.lower():
            rag_memory.add_knowledge(f"Code execution result: {result}", {
                "type": "code_output",
                "session_id": session_id,
                "agent_source": "coder",
                "validated": True,
                "validation_score": 1.0  # Code execution either works or fails; success = high trust
            })
        
        # Update task index if using plan
        if state.get("planner_ran") and state.get("task_plan"):
            result_data["current_task_index"] = state.get("current_task_index", 0) + 1
        
        return result_data
    except Exception as e:
        if retry_count < state.get("max_retries", 3):
            return {
                "error": f"Code execution failed (attempt {retry_count + 1}): {str(e)}",
                "retry_count": retry_count + 1,
                "next": "coder_agent"
            }
        return {
            "code_result": f"Code execution failed after {retry_count} attempts: {str(e)}",
            "current_step": "code_failed",
            "next": "validator"
        }