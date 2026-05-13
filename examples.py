"""
Example interactions with the Multi-Agent System.
Demonstrates RAG + Memory integration.
"""

import uuid
from langchain_core.messages import HumanMessage
from graph import app
from memory import memory


def example_research():
    """Example: Research task with RAG memory."""
    session = str(uuid.uuid4())[:8]
    
    input_data = {
        "messages": [HumanMessage(content="What are the benefits of LangGraph for building agents?")],
        "task_type": "research",
        "retry_count": 0,
        "max_retries": 3,
        "metadata": {"session_id": session}
    }
    
    result = app.invoke(input_data)
    return result, session


def example_coding():
    """Example: Coding task with error handling."""
    session = str(uuid.uuid4())[:8]
    
    input_data = {
        "messages": [HumanMessage(content="Calculate the factorial of 10")],
        "task_type": "coding",
        "retry_count": 0,
        "max_retries": 3,
        "metadata": {"session_id": session}
    }
    
    result = app.invoke(input_data)
    return result, session


def example_multi_turn():
    """Example: Multi-turn conversation leveraging RAG memory."""
    session = str(uuid.uuid4())[:8]
    
    # First query
    input_data = {
        "messages": [HumanMessage(content="Who developed LangGraph?")],
        "task_type": "research",
        "retry_count": 0,
        "max_retries": 3,
        "metadata": {"session_id": session}
    }
    
    result1 = app.invoke(input_data)
    
    # Second query can leverage RAG memory from first
    input_data = {
        "messages": [HumanMessage(content="What features make it strong for multi-agent systems?")],
        "task_type": "research",
        "retry_count": 0,
        "max_retries": 3,
        "metadata": {"session_id": session}
    }
    
    result2 = app.invoke(input_data)
    
    return result1, result2, session


if __name__ == "__main__":
    print("Running example interactions...\n")
    
    print("=" * 50)
    print("Research Example (RAG-enabled)")
    print("=" * 50)
    result, session = example_research()
    print(f"Results: {result.get('research_data', 'No results')[:300]}...")
    print(f"Validation: {result.get('validation', {})}")
    
    print("\n" + "=" * 50)
    print("Coding Example")
    print("=" * 50)
    result, session = example_coding()
    print(f"Results: {result.get('code_result', 'No results')}")
    
    print("\n" + "=" * 50)
    print("Multi-turn Example (Memory-enabled)")
    print("=" * 50)
    r1, r2, session = example_multi_turn()
    print(f"Q1 Result: {r1.get('research_data', 'N/A')[:150]}...")
    print(f"Q2 Result: {r2.get('research_data', 'N/A')[:150]}...")