"""
Enhanced agents with Planner integration, security, RBAC, and confidence scoring.
"""

import os
import re
from typing import Dict, Any, Literal, Optional, Tuple
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from tools import get_tavily_tool, python_repl, get_mcp_tools, mcp_tool_invoker
from state import SharedState, ValidationResult, SourceAttribution
from memory import memory, rag_memory
from observability import trace_agent
from llm_utils import get_llm_instance, is_demo_mode
from security import get_security_scanner
from rbac import get_rbac_manager, Role, Action
from cost_optimizer import get_cost_optimizer, TokenCounter


def get_llm(temperature: float = 0, model: str = "gpt-4"):
    """Get configured LLM instance - delegates to llm_utils."""
    return get_llm_instance(temperature, model)


def get_session_id(state: SharedState) -> str:
    """Get or create session ID from state."""
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


def rbac_check(state: SharedState, action: str, resource: str = "*") -> bool:
    """Check RBAC permission for current user."""
    user = state.get("user")
    if not user:
        return True  # Allow if no user context (backward compat)
    
    rbac = get_rbac_manager()
    rbac_user = rbac.get_user(user["user_id"])
    if not rbac_user:
        return True
    
    return rbac.has_permission(rbac_user, action, resource)


def log_audit(state: SharedState, action: str, details: Dict = None):
    """Log audit event for current user."""
    user = state.get("user", {})
    user_id = user.get("user_id", "unknown")
    session_id = user.get("session_id", get_session_id(state))
    agent = state.get("current_step", "unknown")
    
    scanner = get_security_scanner()
    scanner.audit_logger.log_action(
        user_id=user_id,
        session_id=session_id,
        agent=agent,
        action=action,
        details=details or {},
    )


def classify_query_complexity(query: str) -> Tuple[str, bool]:
    """
    Classify query complexity to determine if planner is needed.
    
    Returns (task_type, needs_planner) tuple.
    """
    # Complex query patterns that need planner
    complex_patterns = [
        r'\bcompare\b', r'\banalyze\b', r'\bevaluate\b', r'\bfind and\b',
        r'\bresearch and\b', r'\bboth\b', r'\band then\b', r'\bmultiple\b',
        r'\bcreate a\b', r'\bdevelop\b', r'\bbuild\b', r'\bdemonstrate\b',
        r'\bresearch\b.*\b(benchmark|script|policy)\b',  # "research and create..."
    ]
    
    query_lower = query.lower().strip()
    
    # Check if complex
    for pattern in complex_patterns:
        if re.search(pattern, query_lower):
            return "research", True
    
    # Check if simple coding
    coding_patterns = [r'\bcalculate\b', r'\bcompute\b', r'\bsolve\b', r'\bcode\b']
    for pattern in coding_patterns:
        if re.search(pattern, query_lower):
            return "coding", False
    
    # Default: simple queries under 30 chars go directly to research
    if len(query) < 30:
        return "research", False
    
    # Queries with research + action words trigger planner
    if "and" in query_lower or len(query) > 100:
        return "research", True
    
    return "research", False


# Supervisor Agent with Planner Integration
@trace_agent("supervisor")
def supervisor_agent(state: SharedState) -> Dict[str, Any]:
    """
    Supervisor agent with planner integration, security checks, and semantic routing.
    """
    # Security pre-check
    scanner = get_security_scanner()
    user = state.get("user", {})
    user_id = user.get("user_id") if user else None
    session_id = user.get("session_id") if user else state.get("metadata", {}).get("session_id")
    
    messages = state.get("messages", [])
    last_user_msg = ""
    for msg in reversed(messages):
        if hasattr(msg, 'content') and msg.content:
            last_user_msg = msg.content
            break
    
    is_safe, scan_report = scanner.scan_input(last_user_msg, user_id, session_id, "supervisor")
    if not is_safe:
        state["security_scan"] = {
            "is_safe": False,
            "prompt_injection_detected": not scan_report["prompt_injection"]["safe"],
            "pii_detected": len(scan_report["pii_detected"]) > 0,
            "sql_injection_detected": not scan_report["sql_injection"]["safe"],
            "blocked": scan_report.get("blocked", False),
            "warnings": scan_report.get("actions_taken", []),
            "scan_details": scan_report,
        }
        return {
            "error": "Input blocked by security scanner",
            "next": "END",
            "retry_count": state.get("retry_count", 0) + 1,
        }
    
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 3)
    session_id = get_session_id(state)
    
    # Log execution
    log_audit(state, "supervisor_routing", {"query": last_user_msg[:100]})
    
    # Check retry limit
    if retry_count >= max_retries:
        return {"next": "END", "error": "Maximum retries exceeded"}
    
    # Check if planner already ran
    if state.get("planner_ran") and state.get("task_plan"):
        tasks = state.get("task_plan", [])
        current_idx = state.get("current_task_index", 0)
        
        if current_idx < len(tasks):
            next_task = tasks[current_idx]
            task_type = next_task.get("type", "research")
            
            # RBAC check for agent access
            if not rbac_check(state, Action.RESEARCH_PUBLIC.value if task_type == "research" else Action.EXECUTE_CODE.value):
                return {"next": "END", "error": "Access denied for task type"}
            
            return {
                "next": "research_agent" if task_type == "research" else "coder_agent",
                "task_type": task_type,
                "current_task_index": current_idx,
                "retry_count": 0
            }
        else:
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
    
    # Adaptive query classification - skip planner for simple queries
    task_type, needs_planner = classify_query_complexity(query)
    
    if needs_planner and not state.get("planner_ran"):
        return {"next": "planner", "task_type": task_type, "adaptive_skipped": False}
    
    # For simple queries, go directly to agent (skip planner)
    # Simple queries can also skip validator if RAG context exists
    state["adaptive_skipped"] = True  # Mark that we skipped planner
    
    # RBAC check for research/code access
    if not rbac_check(state, Action.RESEARCH_PUBLIC.value if task_type == "research" else Action.EXECUTE_CODE.value):
        return {"next": "END", "error": "Access denied for task type"}
    
    # Check RAG memory for relevant context (with RBAC filtering)
    rag_results = rag_memory.retrieve(query, k=3)
    user = state.get("user")
    if user:
        rbac = get_rbac_manager()
        rbac_user = rbac.get_user(user.get("user_id"))
        if rbac_user:
            rag_results = rbac.filter_memory_chunks(rbac_user, rag_results)
    context = "\n".join([r["content"][:200] for r in rag_results]) if rag_results else ""
    
    # For very simple queries with good RAG context, skip to answer
    if rag_results and len(rag_results) > 0 and len(query) < 30:
        # Simple query with context - still go to worker but skip validator later
        return {
            "next": "research_agent" if task_type == "research" else "coder_agent",
            "task_type": task_type,
            "rag_context": context,
            "skip_validator": True,  # Flag to skip validation
        }
    
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
            rag_memory.add_knowledge(state["research_data"], {
                "session_id": session_id,
                "agent_source": "research",
                "iteration": state.get("current_task_index", 0)
            })
        
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
    Validator agent with fact-checking, hallucination detection, confidence scoring, and source attribution.
    """
    messages = state.get("messages", [])
    research_data = state.get("research_data", "No research performed")
    code_result = state.get("code_result", "No code executed")
    session_id = get_session_id(state)
    user_id = get_user_id(state)
    
    # Log execution
    log_audit(state, "validation_started", {
        "has_research": bool(research_data and "No research" not in research_data),
        "has_code": bool(code_result and "No code" not in code_result),
    })
    
    # Check RAG memory for previous related knowledge
    last_msg = messages[-1].content if messages else ""
    rag_knowledge = rag_memory.retrieve(last_msg, k=3)
    user = state.get("user")
    if user:
        rbac = get_rbac_manager()
        rbac_user = rbac.get_user(user.get("user_id"))
        if rbac_user:
            rag_knowledge = rbac.filter_memory_chunks(rbac_user, rag_knowledge)
    rag_context = "\n".join([k["content"][:150] for k in rag_knowledge]) if rag_knowledge else "None"
    
    # Build messages directly to avoid template parsing issues with braces
    system_content = f"""You are a validator agent. Evaluate outputs for:
1. Correctness - Are results accurate? Cross-check with known facts.
2. Relevance - Do they answer the original question?
3. Completeness - Is critical information missing?
4. Hallucination Risk - Are claims fabricated?
5. Source Quality - Are sources reliable and attributed?
6. Knowledge Conflicts - Are there contradictory sources in the retrieved knowledge?

Previous knowledge: {rag_context}

IMPORTANT: If you detect conflicting information in previous knowledge (e.g., different numbers, dates, or policies), note it in issues.

Return JSON:
- is_valid: boolean
- confidence: 0-1 score
- confidence_breakdown: {{"correctness": 0-1, "relevance": 0-1, "completeness": 0-1, "hallucination_risk": 0-1}}
- issues: list of problems (including conflicts)
- suggestions: list of improvements
- source_type: "internal", "web", "llm", or "mixed"
"""
    
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
            confidence_breakdown = llm_validation.get("confidence_breakdown", {
                "correctness": 0.8, "relevance": 0.8, "completeness": 0.8, "hallucination_risk": 0.2
            })
            validation: ValidationResult = {
                "is_valid": llm_validation.get("is_valid", True),
                "confidence": llm_validation.get("confidence", 0.85),
                "confidence_breakdown": confidence_breakdown,
                "issues": llm_validation.get("issues", []),
                "suggestions": llm_validation.get("suggestions", []),
                "source_type": llm_validation.get("source_type", "llm"),
            }
        except (json.JSONDecodeError, AttributeError):
            # Fallback if LLM output is invalid
            validation = {
                "is_valid": True,
                "confidence": 0.7,
                "confidence_breakdown": {
                    "correctness": 0.7, "relevance": 0.7, "completeness": 0.7, "hallucination_risk": 0.3
                },
                "issues": ["Could not parse LLM validation output"],
                "suggestions": ["Manual review recommended"],
                "source_type": "llm",
            }
        
        # Store validated research in RAG memory with governance metadata
        if research_data and "No research" not in research_data:
            rag_memory.add_knowledge(research_data, {
                "type": "validated_research",
                "session_id": session_id,
                "agent_source": "validator",
                "validated": validation["is_valid"],
                "validation_score": validation.get("confidence", 0.85),
                "user_id": user_id,
            })
            # Add source attribution
            add_source(state, {
                "source_type": "web_search" if validation.get("source_type") == "web" else "llm_generation",
                "source_name": "Tavily Search" if validation.get("source_type") == "web" else "LLM",
                "url": None,
                "page": None,
                "timestamp": datetime.now().isoformat(),
                "confidence": validation.get("confidence", 0.85),
                "agent": "validator",
            })
        
        memory.log_execution(session_id, "validator", {"research": research_data, "code": code_result}, 
                            {"validation": validation})
        
        log_audit(state, "validation_completed", {
            "is_valid": validation["is_valid"],
            "confidence": validation["confidence"],
        })
        
        # Determine next step
        if validation["confidence"] < 0.5:
            next_step = "supervisor"
        elif validation["confidence"] < 0.7:
            next_step = "approval"
        else:
            next_step = "reflection"
        
        return {
            "validation": validation,
            "confidence": validation["confidence"],
            "next": next_step,
            "retry_count": 0
        }
    except Exception as e:
        validation: ValidationResult = {
            "is_valid": True,
            "confidence": 0.5,
            "confidence_breakdown": {
                "correctness": 0.5, "relevance": 0.5, "completeness": 0.5, "hallucination_risk": 0.5
            },
            "issues": [f"Validation error: {str(e)}"],
            "suggestions": ["Manual review recommended"],
            "source_type": "llm",
        }
        log_audit(state, "validation_error", {"error": str(e)})
        return {"validation": validation, "confidence": 0.5, "next": "reflection"}


# Research Agent with RAG Integration
@trace_agent("research")
def research_agent(state: SharedState) -> Dict[str, Any]:
    """
    Research agent with FAISS memory storage, security, RBAC, and source attribution.
    """
    messages = state.get("messages", [])
    retry_count = state.get("retry_count", 0)
    session_id = get_session_id(state)
    user_id = get_user_id(state)
    
    # RBAC check
    if not rbac_check(state, Action.RESEARCH_PUBLIC.value):
        log_audit(state, "access_denied", {"agent": "research_agent", "reason": "RBAC"})
        return {
            "error": "Access denied: insufficient permissions for research",
            "next": "END",
            "retry_count": retry_count + 1,
        }
    
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
    
    log_audit(state, "research_started", {"query": search_query[:100]})
    
    try:
        cost_optimizer = get_cost_optimizer()
        cost_info = cost_optimizer.estimate_query_cost(search_query)
        if cost_info["estimated_cost_usd"] > 0.01:
            logger.info(f"[Cost] Research query estimated cost: ${cost_info['estimated_cost_usd']:.4f}")
        
        search_results = get_tavily_tool().invoke({"query": search_query})
        
        formatted_results = "Research Results:\n\n"
        if isinstance(search_results, list):
            for i, result in enumerate(search_results, 1):
                if isinstance(result, dict):
                    title = result.get('title', 'Untitled')
                    url = result.get('url', 'N/A')
                    content = result.get('content', 'N/A')[:200]
                    formatted_results += f"{i}. {title}\n"
                    formatted_results += f"   URL: {url}\n"
                    formatted_results += f"   Content: {content}...\n\n"
                    
                    # Add source attribution
                    add_source(state, {
                        "source_type": "web_search",
                        "source_name": title,
                        "url": url,
                        "page": None,
                        "timestamp": datetime.now().isoformat(),
                        "confidence": 0.9,
                        "agent": "research_agent",
                    })
        
        # Store in RAG memory with provenance
        rag_memory.add_knowledge(formatted_results, {
            "type": "research",
            "session_id": session_id,
            "agent_source": "research",
            "iteration": state.get("current_task_index", 0),
            "user_id": user_id,
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
        
        log_audit(state, "research_completed", {"results_count": len(search_results) if isinstance(search_results, list) else 1})
        return result
    except Exception as e:
        if retry_count < state.get("max_retries", 3):
            log_audit(state, "research_retry", {"attempt": retry_count + 1, "error": str(e)})
            return {
                "error": f"Research failed (attempt {retry_count + 1}): {str(e)}",
                "retry_count": retry_count + 1,
                "next": "research_agent"
            }
        log_audit(state, "research_failed", {"attempts": retry_count, "error": str(e)})
        return {
            "research_data": f"Research failed after {retry_count} attempts: {str(e)}",
            "current_step": "research_failed",
            "next": "validator"
        }


# Coder Agent with Error Handling
@trace_agent("coder")
def coder_agent(state: SharedState) -> Dict[str, Any]:
    """
    Coder agent that executes Python code with error handling, security, and RBAC.
    """
    messages = state.get("messages", [])
    retry_count = state.get("retry_count", 0)
    
    # RBAC check
    if not rbac_check(state, Action.EXECUTE_CODE.value):
        log_audit(state, "access_denied", {"agent": "coder_agent", "reason": "RBAC"})
        return {
            "error": "Access denied: insufficient permissions for code execution",
            "next": "END",
            "retry_count": retry_count + 1,
        }
    
    # Security check on code task
    scanner = get_security_scanner()
    user = state.get("user", {})
    user_id = user.get("user_id") if user else None
    session_id = user.get("session_id") if user else state.get("metadata", {}).get("session_id")
    
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
    
    # Scan code for SQL injection
    sql_safe, sql_patterns = scanner.sql_detector.scan(code_task)
    if not sql_safe:
        log_audit(state, "sql_injection_detected", {"patterns": sql_patterns})
        return {
            "error": "Potentially unsafe code detected",
            "next": "END",
            "retry_count": retry_count + 1,
        }
    
    log_audit(state, "code_execution_started", {"code_preview": code_task[:100]})
    
    try:
        session_id_int = get_session_id(state)
        
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
                "session_id": session_id_int,
                "agent_source": "coder",
                "validated": True,
                "validation_score": 1.0,  # Code execution either works or fails; success = high trust
                "user_id": user_id,
            })
            add_source(state, {
                "source_type": "code_execution",
                "source_name": "Python REPL",
                "url": None,
                "page": None,
                "timestamp": datetime.now().isoformat(),
                "confidence": 0.95,
                "agent": "coder_agent",
            })
        
        # Update task index if using plan
        if state.get("planner_ran") and state.get("task_plan"):
            result_data["current_task_index"] = state.get("current_task_index", 0) + 1
        
        log_audit(state, "code_execution_completed", {"success": "error" not in result.lower()})
        return result_data
    except Exception as e:
        if retry_count < state.get("max_retries", 3):
            log_audit(state, "code_retry", {"attempt": retry_count + 1, "error": str(e)})
            return {
                "error": f"Code execution failed (attempt {retry_count + 1}): {str(e)}",
                "retry_count": retry_count + 1,
                "next": "coder_agent"
            }
        log_audit(state, "code_execution_failed", {"attempts": retry_count, "error": str(e)})
        return {
            "code_result": f"Code execution failed after {retry_count} attempts: {str(e)}",
            "current_step": "code_failed",
            "next": "validator"
        }