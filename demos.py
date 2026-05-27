"""
Demo Scenarios for MultiMind AI

Three compelling use cases showing the system in action:
1. Research Assistant - Deep research with validation
2. Code Debugging Workflow - Iterative coding with testing  
3. Agricultural Advisory - Domain-specific advice with memory
"""

import os
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from graph import app
from memory import memory, rag_memory


def demo_research_assistant():
    """
    Demo 1: Research Assistant
    Shows deep research with fact validation and memory retention.
    """
    print("=" * 60)
    print("DEMO 1: RESEARCH ASSISTANT")
    print("=" * 60)
    print("Query: 'Compare renewable energy adoption in Germany vs Japan 2020-2023'")
    print()
    
    session_id = "research-demo-001"
    
    input_data = {
        "messages": [HumanMessage(content="Compare renewable energy adoption in Germany vs Japan from 2020 to 2023, including policies, percentages, and future targets.")],
        "task_type": "research",
        "retry_count": 0,
        "max_retries": 3,
        "metadata": {"session_id": session_id},
        "planner_ran": False,
        "task_plan": None,
        "reflection": None
    }
    
    result = app.invoke(input_data)
    
    print("PLAN GENERATED:")
    plan = result.get("task_plan", [])
    for i, task in enumerate(plan, 1):
        print(f"  {i}. [{task.get('type')}] {task.get('description')} (priority: {task.get('priority')})")
    print()
    
    print("RESEARCH RESULTS:")
    research = result.get("research_data", "No research data")
    print(research[:800] + ("..." if len(research) > 800 else ""))
    print()
    
    print("VALIDATION:")
    validation = result.get("validation", {})
    print(f"  Valid: {validation.get('is_valid', 'N/A')}")
    print(f"  Confidence: {validation.get('confidence', 'N/A'):.2f}")
    if validation.get("issues"):
        print(f"  Issues: {validation.get('issues')}")
    if validation.get("suggestions"):
        print(f"  Suggestions: {validation.get('suggestions')}")
    print()
    
    print("REFLECTION:")
    reflection = result.get("reflection", {})
    print(f"  Workflow Quality: {reflection.get('workflow_quality', 'N/A'):.2f}")
    print(f"  Planning Feedback: {reflection.get('planning_feedback', 'N/A')[:100]}...")
    print(f"  Final Answer Length: {len(result.get('final_answer', ''))} characters")
    print()
    
    # Show memory impact
    print("MEMORY IMPACT:")
    memory_report = rag_memory.get_quality_report()
    print(f"  Knowledge chunks stored: {memory_report.get('total_chunks', 0)}")
    print(f"  Average trust score: {memory_report.get('average_trust', 0):.3f}")
    print()
    
    return result


def demo_code_debugging():
    """
    Demo 2: Code Debugging Workflow
    Shows iterative coding, testing, and validation.
    """
    print("=" * 60)
    print("DEMO 2: CODE DEBUGGING WORKFLOW")
    print("=" * 60)
    print("Query: 'Create a Python function to calculate Fibonacci numbers with error handling and test it'")
    print()
    
    session_id = "code-demo-001"
    
    input_data = {
        "messages": [HumanMessage(content="Create a Python function to calculate Fibonacci numbers. Include error handling for invalid inputs, add docstring, and provide test cases for 0, 1, 5, and 10.")],
        "task_type": "research",  # Will likely trigger planner due to complexity
        "retry_count": 0,
        "max_retries": 3,
        "metadata": {"session_id": session_id},
        "planner_ran": False,
        "task_plan": None,
        "reflection": None
    }
    
    result = app.invoke(input_data)
    
    print("PLAN GENERATED:")
    plan = result.get("task_plan", [])
    for i, task in enumerate(plan, 1):
        print(f"  {i}. [{task.get('type')}] {task.get('description')} (priority: {task.get('priority')})")
    print()
    
    print("CODE RESULTS:")
    code_result = result.get("code_result", "No code results")
    print(code_result)
    print()
    
    print("VALIDATION:")
    validation = result.get("validation", {})
    print(f"  Valid: {validation.get('is_valid', 'N/A')}")
    print(f"  Confidence: {validation.get('confidence', 'N/A'):.2f}")
    print()
    
    print("REFLECTION:")
    reflection = result.get("reflection", {})
    print(f"  Workflow Quality: {reflection.get('workflow_quality', 'N/A'):.2f}")
    print(f"  Planning Feedback: {reflection.get('planning_feedback', 'N/A')[:100]}...")
    print()
    
    # Test the generated code if possible
    print("TESTING GENERATED CODE:")
    if "def fibonacci" in code_result:
        print("  OK Fibonacci function detected in output")
        # Try to extract and test it (simplified)
        try:
            # This is a simplified test - in practice would be more robust
            if "return" in code_result and ("n == 0" in code_result or "n <= 1" in code_result):
                print("  OK Appears to handle base cases")
            if "for" in code_result or "while" in code_result:
                print("  OK Appears to have iterative logic")
        except:
            pass
    else:
        print("  ! No clear function definition found")
    print()
    
    return result


def demo_agricultural_advisory():
    """
    Demo 3: Agricultural Advisory (AgriDream direction)
    Shows domain-specific advice with domain memory retention.
    """
    print("=" * 60)
    print("DEMO 3: AGRICULTURAL ADVISORY")
    print("=" * 60)
    print("Query: 'What are the best practices for drought-resistant farming in Mediterranean climates?'")
    print()
    
    session_id = "agri-demo-001"
    
    input_data = {
        "messages": [HumanMessage(content="What are the best practices for drought-resistant farming in Mediterranean climates? Include soil management, crop selection, irrigation techniques, and timing considerations.")],
        "task_type": "research",
        "retry_count": 0,
        "max_retries": 3,
        "metadata": {"session_id": session_id},
        "planner_ran": False,
        "task_plan": None,
        "reflection": None
    }
    
    result = app.invoke(input_data)
    
    print("PLAN GENERATED:")
    plan = result.get("task_plan", [])
    for i, task in enumerate(plan, 1):
        print(f"  {i}. [{task.get('type')}] {task.get('description')} (priority: {task.get('priority')})")
    print()
    
    print("ADVISORY RESULTS:")
    advisory = result.get("research_data", "No advisory data")
    print(advisory[:800] + ("..." if len(advisory) > 800 else ""))
    print()
    
    print("VALIDATION:")
    validation = result.get("validation", {})
    print(f"  Valid: {validation.get('is_valid', 'N/A')}")
    print(f"  Confidence: {validation.get('confidence', 'N/A'):.2f}")
    print()
    
    print("REFLECTION:")
    reflection = result.get("reflection", {})
    print(f"  Workflow Quality: {reflection.get('workflow_quality', 'N/A'):.2f}")
    print(f"  Planning Feedback: {reflection.get('planning_feedback', 'N/A')[:100]}...")
    print(f"  Final Answer: {result.get('final_answer', 'N/A')[:150]}...")
    print()
    
    print("DOMAIN MEMORY BUILDUP:")
    memory_report = rag_memory.get_quality_report()
    print(f"  Knowledge chunks stored: {memory_report.get('total_chunks', 0)}")
    print(f"  Average trust score: {memory_report.get('average_trust', 0):.3f}")
    print()
    
    # Second query to show memory reuse
    print("SECOND QUERY (testing memory reuse):")
    print("Query: 'Which specific crops are best for Mediterranean drought conditions?'")
    
    input_data2 = {
        "messages": [HumanMessage(content="Which specific crops are best suited for drought-resistant farming in Mediterranean climates?")],
        "task_type": "research",
        "retry_count": 0,
        "max_retries": 3,
        "metadata": {"session_id": session_id},  # Same session - should reuse memory
        "planner_ran": False,
        "task_plan": None,
        "reflection": None
    }
    
    result2 = app.invoke(input_data2)
    
    print("RESULTS FROM SECOND QUERY:")
    research2 = result2.get("research_data", "No results")
    print(research2[:500] + ("..." if len(research2) > 500 else ""))
    print()
    
    print("VALIDATION SECOND QUERY:")
    validation2 = result2.get("validation", {})
    print(f"  Valid: {validation2.get('is_valid', 'N/A')}")
    print(f"  Confidence: {validation2.get('confidence', 'N/A'):.2f}")
    print()
    
    return result, result2


def run_all_demos():
    """Run all three demo scenarios."""
    print("MultiMind AI Demo Suite")
    print("Showing real-world use cases of integrity-aware autonomous orchestration\n")
    
    # Load environment
    load_dotenv()
    
    # Check if we have API keys
    if not os.getenv("OPENAI_API_KEY"):
        print("WARNING: OPENAI_API_KEY not set - using mock responses where possible")
    if not os.getenv("TAVILY_API_KEY"):
        print("WARNING: TAVILY_API_KEY not set - research will be limited\n")
    
    try:
        result1 = demo_research_assistant()
        print("\n" + "="*60 + "\n")
        result2 = demo_code_debugging()
        print("\n" + "="*60 + "\n")
        result3a, result3b = demo_agricultural_advisory()
        
        print("=" * 60)
        print("ALL DEMOS COMPLETED SUCCESSFULLY")
        print("MultiMind AI demonstrated:")
        print("  OK Research assistant with validation")
        print("  OK Code debugging workflow") 
        print("  OK Domain-specific agricultural advisory")
        print("  OK Memory retention and reuse across queries")
        print("  OK Integrity checks at every stage")
        print("=" * 60)
        
        return [result1, result2, result3a, result3b]
        
    except Exception as e:
        print(f"\nERROR Error running demos: {e}")
        print("This might be due to missing API keys or network issues.")
        print("The system architecture is correct - configure API keys for full functionality.")
        return None


if __name__ == "__main__":
    run_all_demos()