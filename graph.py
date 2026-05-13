"""
Enhanced LangGraph workflow with Reflection Agent integration.
"""

from typing import Literal
from langgraph.graph import StateGraph, END
from state import SharedState
from agents import supervisor_agent, research_agent, coder_agent, validator_agent
from planner import planner_agent
from reflection import reflection_agent


def route_from_supervisor(state: SharedState) -> Literal["planner", "research_agent", "coder_agent", "validator", "END"]:
    """Route from supervisor to next agent."""
    next_agent = state.get("next", "END")
    if next_agent == "END":
        return END
    return next_agent


def route_from_validator(state: SharedState) -> Literal["supervisor", "reflection", "END"]:
    """Route from validator - go to reflection or end."""
    validation = state.get("validation")
    if validation and validation.get("confidence", 1.0) < 0.5:
        return "supervisor"
    return "reflection"


def route_from_reflection(state: SharedState) -> Literal["supervisor", "END"]:
    """Route from reflection agent."""
    if state.get("requires_human_review"):
        return "supervisor"
    return END


def create_workflow() -> StateGraph:
    """
    Create and return the autonomous AI workflow with Reflection.
    
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
    
    # Add edges
    workflow.add_edge("planner", "supervisor")
    workflow.add_edge("research_agent", "supervisor")
    workflow.add_edge("coder_agent", "supervisor")
    
    # Conditional edges from supervisor
    workflow.add_conditional_edges(
        "supervisor",
        route_from_supervisor,
        {
            "planner": "planner",
            "research_agent": "research_agent",
            "coder_agent": "coder_agent",
            "validator": "validator",
            END: END
        }
    )
    
    # Conditional edges from validator
    workflow.add_conditional_edges(
        "validator",
        route_from_validator,
        {
            "supervisor": "supervisor",
            "reflection": "reflection",
            END: END
        }
    )
    
    # Conditional edges from reflection
    workflow.add_conditional_edges(
        "reflection",
        route_from_reflection,
        {
            "supervisor": "supervisor",
            END: END
        }
    )
    
    # Set entry point
    workflow.set_entry_point("supervisor")
    
    return workflow.compile()


# Create the app instance
app = create_workflow()