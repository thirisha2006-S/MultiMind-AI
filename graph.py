"""
Enhanced LangGraph workflow with Enterprise Features.

Includes:
- Security scanning (pre/post agent hooks)
- RBAC enforcement
- Human approval workflow
- Source attribution tracking
- Confidence scoring routing
- Knowledge Integrity Engine (conflict detection)
- Knowledge Evolution Engine
- Explainable Confidence
"""

from typing import Literal, Dict, Any
from langgraph.graph import StateGraph, END
from state import SharedState
from agents import supervisor_agent, research_agent, coder_agent, validator_agent
from planner import planner_agent
from reflection import reflection_agent
from security import get_security_scanner, SecurityScanner
from rbac import get_rbac_manager, check_permission
from approval import get_approval_manager, ApprovalStatus
from conflict_detector import get_conflict_detector, KnowledgeChunk

_security_scanner: SecurityScanner = None
_rbac_mgr = None
_approval_mgr = None
_conflict_detector = None


def _get_security():
    global _security_scanner
    if _security_scanner is None:
        _security_scanner = get_security_scanner()
    return _security_scanner


def _get_rbac():
    global _rbac_mgr
    if _rbac_mgr is None:
        _rbac_mgr = get_rbac_manager()
    return _rbac_mgr


def _get_approval():
    global _approval_mgr
    if _approval_mgr is None:
        _approval_mgr = get_approval_manager()
    return _approval_mgr


def _get_conflict_detector():
    global _conflict_detector
    if _conflict_detector is None:
        _conflict_detector = get_conflict_detector()
    return _conflict_detector


def security_pre_check(state: SharedState) -> SharedState:
    """Pre-agent security scan of user input."""
    scanner = _get_security()
    user = state.get("user", {})
    user_id = user.get("user_id") if user else None
    session_id = user.get("session_id") if user else state.get("metadata", {}).get("session_id")
    
    # Get the last user message
    messages = state.get("messages", [])
    last_user_msg = ""
    for msg in reversed(messages):
        if hasattr(msg, 'content') and msg.content:
            last_user_msg = msg.content
            break
    
    is_safe, scan_report = scanner.scan_input(
        last_user_msg,
        user_id=user_id,
        session_id=session_id,
        agent="pre_check"
    )
    
    state["security_scan"] = {
        "is_safe": is_safe,
        "prompt_injection_detected": not scan_report["prompt_injection"]["safe"],
        "pii_detected": len(scan_report["pii_detected"]) > 0,
        "sql_injection_detected": not scan_report["sql_injection"]["safe"],
        "blocked": scan_report.get("blocked", False),
        "warnings": scan_report.get("actions_taken", []),
        "scan_details": scan_report,
    }
    
    if not is_safe or scan_report.get("blocked"):
        state["error"] = "Input blocked by security scanner: " + ", ".join(scan_report.get("actions_taken", []))
        state["next"] = "END"
    
    return state


def security_post_check(state: SharedState) -> SharedState:
    """Post-agent security scan of output."""
    scanner = _get_security()
    user = state.get("user", {})
    user_id = user.get("user_id") if user else None
    session_id = user.get("session_id") if user else state.get("metadata", {}).get("session_id")
    
    # Check final answer for PII
    final_answer = state.get("final_answer", "") or state.get("research_data", "") or ""
    
    masked_output, pii_found = scanner.pii_masker.mask(final_answer)
    if pii_found:
        state["final_answer"] = masked_output
        if state.get("research_data"):
            state["research_data"] = scanner.pii_masker.mask(state["research_data"])[0]
    
    # Log to audit
    scanner.audit_logger.log_action(
        user_id=user_id,
        session_id=session_id,
        agent="post_check",
        action="output_security_scan",
        details={"pii_detected": list(pii_found.keys()), "masked": bool(pii_found)},
    )
    
    return state


def route_from_supervisor(state: SharedState) -> Literal["planner", "research_agent", "coder_agent", "validator", "approval", "END"]:
    """Route from supervisor to next agent with security/RBAC checks."""
    # Security check
    security = state.get("security_scan")
    if security and (not security.get("is_safe") or security.get("blocked")):
        return END
    
    # Check if we're returning from approval
    if state.get("approval_request_id") and not state.get("pending_approval"):
        # Approval was resolved, go to reflection
        return "reflection"
    
    next_agent = state.get("next", "END")
    if next_agent == "END":
        return END
    
    # RBAC check for agent access
    user = state.get("user")
    if user:
        rbac = _get_rbac()
        allowed_agents = rbac.get_accessible_agents(rbac.get_user(user["user_id"]))
        if next_agent not in allowed_agents and next_agent != "approval":
            # Route to research (public access) or end
            if "research_agent" in allowed_agents:
                return "research_agent"
            return END
    
    return next_agent


def route_from_validator(state: SharedState) -> Literal["supervisor", "approval", "reflection", "END"]:
    """Route from validator - go to approval, reflection, supervisor, or end."""
    security = state.get("security_scan")
    if security and (not security.get("is_safe") or security.get("blocked")):
        return END
    
    # Adaptive: skip validation for simple queries with RAG context
    if state.get("skip_validator"):
        return "reflection"
    
    user = state.get("user")
    if user:
        rbac = _get_rbac()
        rbac_user = rbac.get_user(user["user_id"])
        validation = state.get("validation", {})
        confidence = validation.get("confidence", 1.0)
        
        # Check if action requires approval
        requires_approval = False
        if rbac_user and rbac_user.role != "admin":
            # Non-admin actions with validation confidence < 0.7 might need approval
            if confidence < 0.7:
                requires_approval = True
            # Code execution always needs approval for non-admin
            if state.get("code_result") and rbac_user.role == "customer":
                requires_approval = True
        
        if requires_approval:
            return "approval"
    
    reflection = state.get("reflection", {})
    if reflection and reflection.get("requires_human_review"):
        return "approval"
    
    validation = state.get("validation")
    if validation and validation.get("confidence", 1.0) < 0.5:
        return "supervisor"
    return "reflection"


def route_from_reflection(state: SharedState) -> Literal["supervisor", "approval", "END"]:
    """Route from reflection agent."""
    if state.get("requires_human_review"):
        return "approval"
    return END


def route_from_approval(state: SharedState) -> Literal["supervisor", "reflection", "END"]:
    """Route from approval node."""
    if state.get("pending_approval"):
        # Waiting for human approval
        return END  # Halt workflow until approval is resolved
    
    # Approval resolved
    approval_status = state.get("approval_status", "")
    if approval_status == "rejected":
        return "supervisor"  # Go back to supervisor for replanning
    
    return "reflection"


def approval_workflow(state: SharedState) -> Dict[str, Any]:
    """
    Human approval workflow node.
    
    Creates an approval request and halts until human review.
    """
    approval_mgr = _get_approval()
    user = state.get("user", {})
    session_id = user.get("session_id", state.get("metadata", {}).get("session_id", "unknown"))
    user_id = user.get("user_id", "unknown")
    
    validation = state.get("validation", {})
    action = state.get("approval_required_for", "general_action")
    description = f"Validation confidence: {validation.get('confidence', 0):.2f} — requires human review"
    
    proposed_output = state.get("final_answer") or state.get("research_data") or "No output"
    
    request = approval_mgr.create_request(
        session_id=session_id,
        user_id=user_id,
        agent="validator",
        action=action,
        description=description,
        proposed_output=proposed_output,
        context={
            "validation": validation,
            "task_plan": state.get("task_plan"),
            "confidence": validation.get("confidence", 0),
        },
    )
    
    return {
        "pending_approval": True,
        "approval_request_id": request.request_id,
        "next": "END",
    }


def knowledge_integrity_check(state: SharedState) -> Dict[str, Any]:
    """
    Knowledge Integrity Engine node.
    
    Checks for conflicts in retrieved knowledge, ranks sources,
    and determines if human resolution is needed.
    """
    detector = _get_conflict_detector()
    user = state.get("user", {})
    user_id = user.get("user_id", "unknown")
    
    research_data = state.get("research_data", "")
    sources = state.get("sources", [])
    
    # Get unresolved conflicts for the current query
    query = ""
    for msg in reversed(state.get("messages", [])):
        if hasattr(msg, 'content') and msg.content:
            query = msg.content
            break
    
    relevant_conflicts = detector.get_conflicts_for_topic(query) if query else []
    
    # Build integrity result
    conflict_records = []
    for c in relevant_conflicts:
        conflict_records.append(c.to_dict())
    
    requires_resolution = len(relevant_conflicts) > 0
    
    # Compute confidence adjustment
    confidence_adjustment = 0.0
    if requires_resolution:
        confidence_adjustment = -0.15 * len(relevant_conflicts)  # -15% per conflict
    
    # Get knowledge health
    health = detector.get_knowledge_health()
    
    integrity_result = {
        "conflicts_detected": requires_resolution,
        "conflict_records": conflict_records,
        "recommended_source": None,
        "confidence_adjustment": confidence_adjustment,
        "requires_human_resolution": requires_resolution,
        "knowledge_health_score": health.get("knowledge_health_score", 1.0),
    }
    
    # If conflicts found, adjust confidence and set approval flag
    if requires_resolution:
        current_confidence = state.get("confidence", 0.5)
        adjusted_confidence = max(0.0, current_confidence + confidence_adjustment)
        
        # Log conflict detection
        scanner = _get_security()
        scanner.audit_logger.log_action(
            user_id=user_id,
            session_id=user.get("session_id", state.get("metadata", {}).get("session_id")),
            agent="knowledge_integrity",
            action="conflict_detected",
            details={
                "conflict_count": len(relevant_conflicts),
                "query": query[:100],
                "confidence_adjustment": confidence_adjustment,
            },
        )
        
        return {
            "integrity_check": integrity_result,
            "confidence": adjusted_confidence,
            "conflicts": conflict_records,
            "knowledge_health_score": health.get("knowledge_health_score", 1.0),
            "approval_required_for": "knowledge_conflict",
            "next": "approval" if adjusted_confidence < 0.6 else "reflection",
        }
    
    return {
        "integrity_check": integrity_result,
        "confidence": state.get("confidence", 0.5),
        "conflicts": [],
        "knowledge_health_score": health.get("knowledge_health_score", 1.0),
        "next": "reflection",
    }


def create_workflow() -> StateGraph:
    """
    Create and return the enterprise AI workflow with security, RBAC, approval, and Knowledge Integrity Engine.
    
    Returns:
        Compiled StateGraph workflow
    """
    workflow = StateGraph(SharedState)
    
    # Add all nodes
    workflow.add_node("planner", planner_agent)
    workflow.add_node("supervisor", supervisor_agent)
    workflow.add_node("research_agent", research_agent)
    workflow.add_node("coder_agent", coder_agent)
    workflow.add_node("validator", validator_agent)
    workflow.add_node("reflection", reflection_agent)
    workflow.add_node("approval", approval_workflow)
    workflow.add_node("knowledge_integrity", knowledge_integrity_check)
    workflow.add_node("security_pre_check", security_pre_check)
    workflow.add_node("security_post_check", security_post_check)
    
    # Edges
    workflow.add_edge("planner", "supervisor")
    workflow.add_edge("security_pre_check", "supervisor")
    
    # After research/coder, check knowledge integrity before validator
    workflow.add_edge("research_agent", "knowledge_integrity")
    workflow.add_edge("coder_agent", "knowledge_integrity")
    
    # From knowledge_integrity to validator
    workflow.add_edge("knowledge_integrity", "validator")
    
    # From validator to reflection or approval
    workflow.add_edge("validator", "reflection")
    
    # Conditional edges from supervisor
    workflow.add_conditional_edges(
        "supervisor",
        route_from_supervisor,
        {
            "planner": "planner",
            "research_agent": "research_agent",
            "coder_agent": "coder_agent",
            "validator": "validator",
            "approval": "approval",
            END: END
        }
    )
    
    # Conditional edges from reflection
    workflow.add_conditional_edges(
        "reflection",
        route_from_reflection,
        {
            "supervisor": "supervisor",
            "approval": "approval",
            END: END
        }
    )
    
    # Conditional edges from approval
    workflow.add_conditional_edges(
        "approval",
        route_from_approval,
        {
            "supervisor": "supervisor",
            "reflection": "reflection",
            "knowledge_integrity": "knowledge_integrity",
            END: END
        }
    )
    
    # Set entry point
    workflow.set_entry_point("supervisor")
    
    return workflow.compile()


# Create the app instance
app = create_workflow()