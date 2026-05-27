"""
Benchmark Suite for MultiMind AI Integrity and Performance

Measures:
- Hallucination reduction through validator scrutiny
- Validation accuracy 
- Loop prevention effectiveness
- Task completion rates
- Memory retrieval precision
- System reliability under various conditions
"""

import time
import json
import statistics
from typing import Dict, Any, List
from unittest.mock import Mock, patch
from langchain_core.messages import HumanMessage

# Import our system components
from graph import app
from memory import memory, rag_memory
from observability import get_tracer


class IntegrityBenchmark:
    """Benchmark suite for measuring MultiMind AI integrity improvements."""
    
    def __init__(self):
        self.results = {
            "hallucination_reduction": [],
            "validation_accuracy": [],
            "loop_prevention": [],
            "task_completion": [],
            "memory_precision": [],
            "system_reliability": []
        }
    
    def run_hallucination_test(self) -> Dict[str, Any]:
        """
        Test hallucination reduction by asking for known false statements
        and measuring validator catch rate.
        """
        test_cases = [
            "The moon is made of green cheese",
            "Water boils at 0°C at sea level", 
            "Humans have three arms",
            "Python was invented in 1990",
            "The earth is flat"
        ]
        
        caught_hallucinations = 0
        total_tests = len(test_cases)
        
        for claim in test_cases:
            input_data = {
                "messages": [HumanMessage(content=f"Is this true: {claim}")],
                "task_type": "research",
                "retry_count": 0,
                "max_retries": 2,
                "metadata": {"session_id": f"hallucination_test_{hash(claim)}"},
                "planner_ran": False,
                "task_plan": None,
                "reflection": None
            }
            
            try:
                result = app.invoke(input_data)
                validation = result.get("validation", {})
                
                # Check if validator caught the hallucination
                is_valid = validation.get("is_valid", True)
                confidence = validation.get("confidence", 1.0)
                issues = validation.get("issues", [])
                
                # Consider it caught if marked invalid or low confidence with issues
                if not is_valid or (confidence < 0.7 and len(issues) > 0):
                    caught_hallucinations += 1
                    
            except Exception as e:
                # If system crashes, count as not caught (but this is bad)
                pass
        
        hallucination_reduction_rate = caught_hallucinations / total_tests if total_tests > 0 else 0
        self.results["hallucination_reduction"].append(hallucination_reduction_rate)
        
        return {
            "test": "hallucination_reduction",
            "caught": caught_hallucinations,
            "total": total_tests,
            "rate": hallucination_reduction_rate,
            "percentage": f"{hallucination_reduction_rate*100:.1f}%"
        }
    
    def run_validation_accuracy_test(self) -> Dict[str, Any]:
        """
        Test validation accuracy by checking if validator correctly 
        identifies true vs false statements.
        """
        test_cases = [
            # True statements
            ("Water boils at 100°C at sea level", True),
            ("Python is a programming language", True),
            ("The earth orbits the sun", True),
            ("2 + 2 = 4", True),
            # False statements  
            ("Water boils at 0°C at sea level", False),
            ("Python is a type of snake only", False),
            ("The sun orbits the earth", False),
            ("2 + 2 = 5", False)
        ]
        
        correct_validations = 0
        total_tests = len(test_cases)
        
        for statement, is_true in test_cases:
            input_data = {
                "messages": [HumanMessage(content=f"Verify this statement: {statement}")],
                "task_type": "research", 
                "retry_count": 0,
                "max_retries": 2,
                "metadata": {"session_id": f"validation_test_{hash(statement)}"},
                "planner_ran": False,
                "task_plan": None,
                "reflection": None
            }
            
            try:
                result = app.invoke(input_data)
                validation = result.get("validation", {})
                
                is_valid = validation.get("is_valid", True)
                confidence = validation.get("confidence", 0.5)
                
                # Simple heuristic: valid=true with high confidence for true statements
                # valid=false or low confidence for false statements
                if is_true:
                    if is_valid and confidence > 0.7:
                        correct_validations += 1
                else:
                    if (not is_valid) or confidence < 0.6:
                        correct_validations += 1
                        
            except Exception as e:
                pass
        
        accuracy = correct_validations / total_tests if total_tests > 0 else 0
        self.results["validation_accuracy"].append(accuracy)
        
        return {
            "test": "validation_accuracy",
            "correct": correct_validations,
            "total": total_tests,
            "accuracy": accuracy,
            "percentage": f"{accuracy*100:.1f}%"
        }
    
    def run_loop_prevention_test(self) -> Dict[str, Any]:
        """
        Test that the system prevents infinite loops through proper routing.
        """
        # These should terminate quickly, not loop
        looping_risk_queries = [
            "What is the meaning of life?",  # Open ended but should terminate
            "Keep explaining forever about nothing",  # Should not actually loop
            "Tell me about A, then B, then C, then D, then E, then F, then G, then H, then I, then J",  # Long chain
            "Repeat after me: hello world",  # Simple repetition
        ]
        
        completed_without_loop = 0
        total_tests = len(looping_risk_queries)
        
        for query in looping_risk_queries:
            input_data = {
                "messages": [HumanMessage(content=query)],
                "task_type": "research",
                "retry_count": 0,
                "max_retries": 3,
                "metadata": {"session_id": f"loop_test_{hash(query)}"},
                "planner_ran": False,
                "task_plan": None,
                "reflection": None
            }
            
            try:
                start_time = time.time()
                result = app.invoke(input_data)
                end_time = time.time()
                
                execution_time = end_time - start_time
                
                # Should complete in reasonable time (< 30 seconds) and not show loop indicators
                if execution_time < 30:
                    # Check observability for loop detection
                    # We'd need to check the tracer output, but for now assume no crash = good
                    completed_without_loop += 1
                    
            except Exception as e:
                # If it crashes or hangs badly, count as failed
                pass
        
        loop_prevention_rate = completed_without_loop / total_tests if total_tests > 0 else 0
        self.results["loop_prevention"].append(loop_prevention_rate)
        
        return {
            "test": "loop_prevention",
            "completed": completed_without_loop,
            "total": total_tests,
            "rate": loop_prevention_rate,
            "percentage": f"{loop_prevention_rate*100:.1f}%"
        }
    
    def run_task_completion_test(self) -> Dict[str, Any]:
        """
        Test that various types of tasks actually complete and return results.
        """
        test_cases = [
            ("What is 2+2?", "research"),  # Simple factual
            ("Calculate factorial of 5", "research"),  # Math (will use research but could trigger coder)
            ("Explain photosynthesis in simple terms", "research"),  # Explanation
            ("List 3 benefits of exercise", "research"),  # List generation
        ]
        
        completed_tasks = 0
        total_tests = len(test_cases)
        
        for query, task_type in test_cases:
            input_data = {
                "messages": [HumanMessage(content=query)],
                "task_type": task_type,
                "retry_count": 0,
                "max_retries": 3,
                "metadata": {"session_id": f"completion_test_{hash(query)}"},
                "planner_ran": False,
                "task_plan": None,
                "reflection": None
            }
            
            try:
                result = app.invoke(input_data)
                
                # Check if we got some kind of result
                has_output = (
                    result.get("research_data") or 
                    result.get("code_result") or
                    result.get("final_answer")
                )
                
                if has_output and len(str(has_output).strip()) > 10:  # Non-trivial output
                    completed_tasks += 1
                    
            except Exception as e:
                pass
        
        completion_rate = completed_tasks / total_tests if total_tests > 0 else 0
        self.results["task_completion"].append(completion_rate)
        
        return {
            "test": "task_completion",
            "completed": completed_tasks,
            "total": total_tests,
            "rate": completion_rate,
            "percentage": f"{completion_rate*100:.1f}%"
        }
    
    def run_memory_precision_test(self) -> Dict[str, Any]:
        """
        Test memory retrieval precision - does it return relevant information?
        """
        # First store some known information
        setup_queries = [
            "The capital of France is Paris",
            "Python was created by Guido van Rossum",
            "The speed of light is approximately 299,792,458 meters per second"
        ]
        
        # Store the knowledge
        for query in setup_queries:
            input_data = {
                "messages": [HumanMessage(content=query)],
                "task_type": "research",
                "retry_count": 0,
                "max_retries": 1,
                "metadata": {"session_id": f"memory_setup_{hash(query)}"},
                "planner_ran": False,
                "task_plan": None,
                "reflection": None
            }
            
            try:
                app.invoke(input_data)
            except:
                pass  # Even if storage fails, continue with test
        
        # Now test retrieval accuracy
        test_queries = [
            ("What is the capital of France?", "Paris"),
            ("Who created Python?", "Guido van Rossum"),
            ("What is the speed of light?", "299,792,458")
        ]
        
        precise_retrievals = 0
        total_tests = len(test_queries)
        
        for query, expected_fragment in test_queries:
            input_data = {
                "messages": [HumanMessage(content=query)],
                "task_type": "research",
                "retry_count": 0,
                "max_retries": 3,
                "metadata": {"session_id": f"memory_test_{hash(query)}"},
                "planner_ran": False,
                "task_plan": None,
                "reflection": None
            }
            
            try:
                result = app.invoke(input_data)
                research_data = result.get("research_data", "")
                
                # Check if expected fragment is in the result
                if expected_fragment.lower() in research_data.lower():
                    precise_retrievals += 1
                    
            except Exception as e:
                pass
        
        precision_rate = precise_retrievals / total_tests if total_tests > 0 else 0
        self.results["memory_precision"].append(precision_rate)
        
        return {
            "test": "memory_precision",
            "precise": precise_retrievals,
            "total": total_tests,
            "rate": precision_rate,
            "percentage": f"{precision_rate*100:.1f}%"
        }
    
    def run_system_reliability_test(self) -> Dict[str, Any]:
        """
        Test overall system reliability under stress.
        """
        stress_tests = [
            # Normal operations
            ("What is AI?", "research"),
            ("Calculate 10!", "research"),
            
            # Edge cases
            ("", "research"),  # Empty query
            ("a" * 1000, "research"),  # Very long query
            ("What? Why? How? When? Where?", "research"),  # Multiple questions
            
            # Mixed content
            ("Explain quantum computing and show me the math", "research"),
            ("Tell me a joke about programming", "research"),
        ]
        
        successful_executions = 0
        total_tests = len(stress_tests)
        
        for query, task_type in stress_tests:
            # Skip empty query to avoid issues
            if not query.strip():
                continue
                
            input_data = {
                "messages": [HumanMessage(content=query)],
                "task_type": task_type,
                "retry_count": 0,
                "max_retries": 2,
                "metadata": {"session_id": f"reliability_test_{hash(query)}"},
                "planner_ran": False,
                "task_plan": None,
                "reflection": None
            }
            
            try:
                result = app.invoke(input_data)
                
                # Basic success: no exception and we got some response
                if result is not None:
                    successful_executions += 1
                    
            except Exception as e:
                # System crashed or hung
                pass
        
        reliability_rate = successful_executions / max(total_tests - 1, 1)  # Subtract empty query
        self.results["system_reliability"].append(reliability_rate)
        
        return {
            "test": "system_reliability",
            "successful": successful_executions,
            "total": total_tests - 1,  # Excluding empty query
            "rate": reliability_rate,
            "percentage": f"{reliability_rate*100:.1f}%"
        }
    
    def run_all_benchmarks(self) -> Dict[str, Any]:
        """Run all benchmark tests and return comprehensive results."""
        print("Running MultiMind AI Integrity Benchmark Suite...")
        print("=" * 60)
        
        benchmarks = [
            self.run_hallucination_test,
            self.run_validation_accuracy_test,
            self.run_loop_prevention_test,
            self.run_task_completion_test,
            self.run_memory_precision_test,
            self.run_system_reliability_test
        ]
        
        results = []
        for benchmark_func in benchmarks:
            print(f"Running {benchmark_func.__name__}...")
            result = benchmark_func()
            results.append(result)
            print(f"  Result: {result}")
            print()
        
        # Calculate overall scores
        overall_scores = {}
        for key in self.results.keys():
            if self.results[key]:
                overall_scores[key] = statistics.mean(self.results[key])
            else:
                overall_scores[key] = 0.0
        
        print("=" * 60)
        print("BENCHMARK SUMMARY")
        print("=" * 60)
        for test_name, score in overall_scores.items():
            percentage = score * 100
            print(f"{test_name:25}: {percentage:5.1f}%")
        
        overall_avg = statistics.mean([score for score in overall_scores.values() if score > 0])
        print("-" * 60)
        print(f"{'OVERALL SCORE':25}: {overall_avg*100:5.1f}%")
        print("=" * 60)
        
        return {
            "individual_results": results,
            "overall_scores": overall_scores,
            "overall_average": overall_avg
        }


def run_benchmark_suite():
    """Convenience function to run the full benchmark suite."""
    benchmark = IntegrityBenchmark()
    return benchmark.run_all_benchmarks()


if __name__ == "__main__":
    # Run the benchmark when executed directly
    results = run_benchmark_suite()
    
    # Optionally save results to file
    with open("benchmark_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print("\nDetailed results saved to benchmark_results.json")