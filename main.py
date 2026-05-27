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

# Configure logging for observability
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)


def run_task(task: str, task_type: str = "research", session_id: str = None):
    """Run a task through the complete autonomous system."""
    session = session_id or str(uuid.uuid4())[:8]
    
    # Start observability trace
    start_trace(session, task=task, task_type=task_type)
    
    input_data = {
        "messages": [HumanMessage(content=task)],
        "task_type": task_type,
        "retry_count": 0,
        "max_retries": 3,
        "metadata": {"session_id": session},
        "planner_ran": False,
        "task_plan": None,
        "reflection": None
    }
    
    # Save initial state
    memory.save_conversation(session, input_data["messages"], {"initial_task": task})
    
    result = app.invoke(input_data)
    
    # Save final state
    memory.save_conversation(session, result.get("messages", []), {
        "final_result": result.get("final_answer", ""),
        "validation": result.get("validation", {}),
        "plan": result.get("task_plan", []),
        "reflection": result.get("reflection", {}),
        "trace_hash": None  # Will be set after tracer is finalized
    })
    
    # Return the tracer so the caller can finalize and get the report
    tracer = get_tracer(session)
    return result, session, tracer


def main():
    """Run the complete MultiMind AI autonomous workflow system."""
    load_dotenv()
    
    print("=" * 70)
    print("MultiMind AI — Autonomous Cognitive Workflow System")
    print("Planner -> Supervisor -> Workers -> Validator -> Reflection -> Memory")
    print("=" * 70)
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
    print(f"Plan: {len(result.get('task_plan', []))} tasks")
    print(f"Workflow Quality: {result.get('reflection', {}).get('workflow_quality', 'N/A')}")
    print(f"Feedback: {result.get('reflection', {}).get('planning_feedback', 'N/A')[:100]}...")
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
    print(f"Plan: {result.get('task_plan', [])}")
    print(f"Workflow Quality: {result.get('reflection', {}).get('workflow_quality', 'N/A')}")
    print(f"Next Tips: {result.get('reflection', {}).get('next_iteration_tips', [])}")
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
    
    print("=" * 70)
    print("Architecture Summary:")
    print("  User -> Planner -> Supervisor -> Workers -> Validator -> Reflection -> Memory")
    print("  Plus: Observability (tracing + invariants) + Memory Governance (provenance + trust decay)")
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