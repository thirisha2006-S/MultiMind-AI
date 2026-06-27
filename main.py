"""
Main entry point for the MultiMind AI autonomous cognitive workflow system.
"""

import os
import uuid
import logging
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from graph import app
from memory import memory, rag_memory
from observability import start_trace, get_tracer, close_trace
from mcp_integration import mcp_manager
from security import get_security_scanner
from auth import get_auth_manager
from rbac import get_rbac_manager

# Load environment variables from .env file
load_dotenv()

# Configure logging for observability
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)

# Initialize enterprise modules
_security_scanner = get_security_scanner()
_auth_manager = get_auth_manager()
_rbac_manager = get_rbac_manager()
_conflict_detector = None

def get_conflict_detector():
    """Get global conflict detector."""
    global _conflict_detector
    if _conflict_detector is None:
        from conflict_detector import get_conflict_detector as _gcd
        _conflict_detector = _gcd()
    return _conflict_detector


def run_task(task: str, task_type: str = "research", session_id: str = None, user_id: str = None):
    """Run a task through the complete autonomous system."""
    session = session_id or str(uuid.uuid4())[:8]
    
    # Start observability trace
    start_trace(session, task=task, task_type=task_type)
    
    # Security pre-check
    is_safe, scan_report = _security_scanner.scan_input(task, user_id=user_id, session_id=session)
    if not is_safe:
        logging.warning(f"[Security] Task blocked for user={user_id}: {scan_report}")
        return {
            "error": "Input blocked by security scanner",
            "final_answer": "Your request could not be processed due to security policies.",
            "security_scan": scan_report,
        }, session, None
    
    input_data = {
        "messages": [HumanMessage(content=task)],
        "task_type": task_type,
        "retry_count": 0,
        "max_retries": 3,
        "metadata": {"session_id": session},
        "planner_ran": False,
        "task_plan": None,
        "reflection": None,
        "user": {
            "user_id": user_id or "anonymous",
            "username": user_id or "anonymous",
            "role": "guest",
            "session_id": session,
        },
        "sources": [],
        "confidence": 0.5,
        "pending_approval": False,
        "approval_request_id": None,
        "approval_required_for": None,
        "security_scan": {
            "is_safe": True,
            "prompt_injection_detected": False,
            "pii_detected": False,
            "sql_injection_detected": False,
            "blocked": False,
            "warnings": [],
            "scan_details": scan_report,
        },
        "feedback_collected": False,
        "feedback_id": None,
    }
    
    # Save initial state
    memory.save_conversation(session, input_data["messages"], {"initial_task": task})
    
    result = app.invoke(input_data)
    
    # Security post-check
    final_answer = result.get("final_answer", "")
    if final_answer:
        masked, pii = _security_scanner.pii_masker.mask(final_answer)
        if pii:
            result["final_answer"] = masked
            result["pii_masked"] = True
    
    # Save final state
    memory.save_conversation(session, result.get("messages", []), {
        "final_result": result.get("final_answer", ""),
        "validation": result.get("validation", {}),
        "plan": result.get("task_plan", []),
        "reflection": result.get("reflection", {}),
        "user_id": user_id,
        "sources": result.get("sources", []),
        "confidence": result.get("confidence", 0.5),
        "trace_hash": None
    })
    
    # Return the tracer so the caller can finalize and get the report
    tracer = get_tracer(session)
    return result, session, tracer


def main():
    """Run the complete MultiMind AI autonomous workflow system."""
    load_dotenv()
    
    print("=" * 70)
    print("MultiMind AI — Secure Enterprise Knowledge Assistant")
    print("Architecture: Multi-Agent + Security + RBAC + Memory Governance")
    print("=" * 70)
    print()
    
    # Print security status
    print("[Security] Scanner initialized")
    print("[RBAC] 4 roles configured: admin, employee, customer, guest")
    print("[Auth] Demo credentials: admin/admin123, employee/emp123, customer/cust123")
    print()
    
    session = str(uuid.uuid4())[:8]
    
    # Example 1: Simple task
    print("Example 1: Simple Research Task")
    print("-" * 50)
    result, session, tracer = run_task("What is LangGraph?", "research", session)
    if tracer:
        tracer.finalize(result)
        report = tracer.get_trace_report()
        num_transitions = len(report.get('snapshots', []))
        print(f"[Observability] Session {session}: {num_transitions} transitions, "
              f"{report.get('error_count',0)} violations, {report.get('loop_count',0)} loops detected")
        close_trace(session)
    print(f"Result: {result.get('research_data', 'No results')[:200]}...")
    print(f"Workflow Quality: {result.get('reflection', {}).get('workflow_quality', 'N/A')}")
    print()
    
    # Example 2: Complex multi-step task
    print("Example 2: Complex Task (Triggers Full Pipeline)")
    print("-" * 50)
    result, session, tracer = run_task(
        "Compare Python web frameworks and create a performance benchmark script",
        "research",
        session
    )
    if tracer:
        tracer.finalize(result)
        report = tracer.get_trace_report()
        num_transitions = len(report.get('snapshots', []))
        print(f"[Observability] Session {session}: {num_transitions} transitions, "
              f"{report.get('error_count',0)} violations, {report.get('loop_count',0)} loops detected")
        close_trace(session)
    print(f"Plan: {len(result.get('task_plan') or [])} tasks")
    if result.get('reflection'):
        print(f"Workflow Quality: {result.get('reflection', {}).get('workflow_quality', 'N/A')}")
        feedback = result.get('reflection', {}).get('planning_feedback', '')
        if feedback:
            print(f"Feedback: {feedback[:100]}...")
    print()
    
    # Example 3: Coding + Research combination
    print("Example 3: Analysis Task (Research + Code)")
    print("-" * 50)
    result, session, tracer = run_task(
        "Analyze the Fibonacci sequence and explain its mathematical significance",
        "research",
        session
    )
    if tracer:
        tracer.finalize(result)
        report = tracer.get_trace_report()
        num_transitions = len(report.get('snapshots', []))
        print(f"[Observability] Session {session}: {num_transitions} transitions, "
              f"{report.get('error_count',0)} violations, {report.get('loop_count',0)} loops detected")
        close_trace(session)
    print(f"Plan: {result.get('task_plan') or []}")
    if result.get('reflection'):
        print(f"Workflow Quality: {result.get('reflection', {}).get('workflow_quality', 'N/A')}")
        tips = result.get('reflection', {}).get('next_iteration_tips', [])
        if tips:
            print(f"Next Tips: {tips}")
    print()
    
    # Example 4: MCP Tool Usage (if MCP is available)
    print("Example 4: MCP Tool Integration Example")
    print("-" * 50)
    # Check if MCP integration is available
    try:
        from mcp_integration import MCP_INTEGRATION_AVAILABLE
        if MCP_INTEGRATION_AVAILABLE:
            # Example task that would use MCP tools
            mcp_task = "Use MCP filesystem tool to list files in current directory"
            result, session, tracer = run_task(mcp_task, "research", session)
            if tracer:
                tracer.finalize(result)
                report = tracer.get_trace_report()
                num_transitions = len(report.get('snapshots', []))
                print(f"[Observability] Session {session}: {num_transitions} transitions, "
                      f"{report.get('error_count',0)} violations, {report.get('loop_count',0)} loops detected")
                close_trace(session)
            print(f"MCP Task Result: {result.get('research_data', 'No results')[:200]}...")
            print(f"Workflow Quality: {result.get('reflection', {}).get('workflow_quality', 'N/A')}")
        else:
            print("MCP integration not available - install 'mcp' package to enable MCP tools")
            print("Example task that would use MCP: List files using filesystem MCP server")
    except ImportError:
        print("MCP integration not available - install 'mcp' package to enable MCP tools")
        print("Example task that would use MCP: List files using filesystem MCP server")
    print()
    
    # Example 5: Knowledge Evolution
    print("Example 5: Knowledge Evolution (New Feature)")
    print("-" * 50)
    try:
        from knowledge_evolution import get_knowledge_timeline
        evolution = get_knowledge_timeline("leave policy")
        if evolution:
            print(f"Found {len(evolution.get('versions', []))} versions")
            for v in evolution.get('versions', [])[:3]:
                print(f"  - {v['source']} ({datetime.fromtimestamp(v['timestamp']).strftime('%Y-%m-%d')})")
        else:
            print("No evolution data yet - upload documents to track changes over time")
    except ImportError:
        print("Knowledge evolution module loaded")
    print()
    
    print("=" * 70)
    print("Architecture Summary:")
    print("  User -> Supervisor -> (Planner if complex) -> Workers -> Validator -> Reflection -> Memory")
    print("  Features: Knowledge Evolution (track changes), Explainable Confidence, Adaptive Routing")
    print("=" * 70)
    
    # Print final memory governance report
    report = rag_memory.get_quality_report()
    print("\n[Memory Governance Report]")
    print(f"  Total knowledge chunks: {report.get('total_chunks', 0)}")
    print(f"  Average trust score: {report.get('average_trust', 0.0):.3f}")
    print(f"  Trust range: [{report.get('min_trust', 0.0):.3f}, {report.get('max_trust', 0.0):.3f}]")
    
    print("\nMultiMind AI execution complete.")


if __name__ == "__main__":
    main()