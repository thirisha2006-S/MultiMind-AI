"""
Performance Benchmark for MultiMind AI

Measures:
- Execution time for different query types
- Memory usage patterns
- Throughput under load
- Scalability characteristics
"""

import time
import statistics
from typing import List, Dict
from langchain_core.messages import HumanMessage
from graph import app


class PerformanceBenchmark:
    """Performance benchmark suite for MultiMind AI."""
    
    def __init__(self):
        self.results = {
            "simple_query_latency": [],
            "complex_query_latency": [],
            "memory_recall_speed": [],
            "concurrent_simulation": []
        }
    
    def measure_simple_query_latency(self) -> Dict[str, Any]:
        """Measure latency for simple factual queries."""
        queries = [
            "What is the capital of France?",
            "Who invented Python?",
            "What is 2+2?",
            "When did World War II end?",
            "What is the largest planet?"
        ]
        
        times = []
        for query in queries:
            input_data = {
                "messages": [HumanMessage(content=query)],
                "task_type": "research",
                "retry_count": 0,
                "max_retries": 2,
                "metadata": {"session_id": f"perf_simple_{hash(query)}"},
                "planner_ran": False,
                "task_plan": None,
                "reflection": None
            }
            
            start = time.time()
            result = app.invoke(input_data)
            end = time.time()
            
            times.append(end - start)
        
        avg_time = statistics.mean(times) if times else 0
        self.results["simple_query_latency"].append(avg_time)
        
        return {
            "test": "simple_query_latency",
            "average_time": avg_time,
            "min_time": min(times) if times else 0,
            "max_time": max(times) if times else 0,
            "unit": "seconds"
        }
    
    def measure_complex_query_latency(self) -> Dict[str, Any]:
        """Measure latency for complex multi-step queries."""
        queries = [
            "Compare machine learning algorithms for image recognition and provide code examples",
            "Analyze the economic impact of renewable energy adoption in Europe 2020-2023",
            "Explain quantum computing principles and suggest a simple experiment to demonstrate superposition",
            "Create a Python web scraper for news headlines with error handling and testing",
            "What are the best practices for microservices architecture and provide a simple example"
        ]
        
        times = []
        plan_lengths = []
        
        for query in queries:
            input_data = {
                "messages": [HumanMessage(content=query)],
                "task_type": "research",
                "retry_count": 0,
                "max_retries": 3,
                "metadata": {"session_id": f"perf_complex_{hash(query)}"},
                "planner_ran": False,
                "task_plan": None,
                "reflection": None
            }
            
            start = time.time()
            result = app.invoke(input_data)
            end = time.time()
            
            execution_time = end - start
            times.append(execution_time)
            
            # Also measure plan complexity
            plan = result.get("task_plan", [])
            plan_lengths.append(len(plan))
        
        avg_time = statistics.mean(times) if times else 0
        avg_plan_length = statistics.mean(plan_lengths) if plan_lengths else 0
        
        self.results["complex_query_latency"].append(avg_time)
        
        return {
            "test": "complex_query_latency",
            "average_time": avg_time,
            "average_plan_length": avg_plan_length,
            "min_time": min(times) if times else 0,
            "max_time": max(times) if times else 0,
            "unit": "seconds"
        }
    
    def measure_memory_recall_speed(self) -> Dict[str, Any]:
        """Measure how quickly the system can recall previously stored information."""
        # First, store some knowledge
        knowledge_items = [
            "The capital of Australia is Canberra",
            "Machine learning is a subset of artificial intelligence",
            "The human heart has four chambers",
            "Python uses indentation for code blocks",
            "Photosynthesis converts sunlight to chemical energy"
        ]
        
        # Store the knowledge
        for i, item in enumerate(knowledge_items):
            input_data = {
                "messages": [HumanMessage(content=item)],
                "task_type": "research",
                "retry_count": 0,
                "max_retries": 1,
                "metadata": {"session_id": f"memory_store_{i}"},
                "planner_ran": False,
                "task_plan": None,
                "reflection": None
            }
            try:
                app.invoke(input_data)
            except:
                pass  # Continue even if some fail to store
        
        # Now measure recall speed
        recall_queries = [
            "What is the capital of Australia?",
            "What is machine learning related to?",
            "How many chambers does the human heart have?",
            "What does Python use for code blocks?",
            "What does photosynthesis convert?"
        ]
        
        times = []
        for query in recall_queries:
            input_data = {
                "messages": [HumanMessage(content=query)],
                "task_type": "research",
                "retry_count": 0,
                "max_retries": 2,
                "metadata": {"session_id": f"memory_recall_{hash(query)}"},
                "planner_ran": False,
                "task_plan": None,
                "reflection": None
            }
            
            start = time.time()
            result = app.invoke(input_data)
            end = time.time()
            
            times.append(end - start)
        
        avg_time = statistics.mean(times) if times else 0
        self.results["memory_recall_speed"].append(avg_time)
        
        return {
            "test": "memory_recall_speed",
            "average_time": avg_time,
            "min_time": min(times) if times else 0,
            "max_time": max(times) if times else 0,
            "unit": "seconds"
        }
    
    def measure_concurrent_simulation(self) -> Dict[str, Any]:
        """Simulate concurrent load by running multiple queries rapidly."""
        # Simulate by running queries in quick succession (not true concurrency)
        queries = [
            "What is AI?",
            "Define machine learning",
            "What is deep learning?",
            "Explain neural networks",
            "What is supervised learning?",
            "What is unsupervised learning?",
            "How does reinforcement learning work?",
            "What is the difference between AI and ML?",
            "Give an example of AI in healthcare",
            "What is the future of AI?"
        ]
        
        start_time = time.time()
        results = []
        
        for i, query in enumerate(queries):
            input_data = {
                "messages": [HumanMessage(content=query)],
                "task_type": "research",
                "retry_count": 0,
                "max_retries": 2,
                "metadata": {"session_id": f"concurrent_{i}"},
                "planner_ran": False,
                "task_plan": None,
                "reflection": None
            }
            
            try:
                result = app.invoke(input_data)
                results.append(result)
            except Exception as e:
                results.append({"error": str(e)})
        
        end_time = time.time()
        total_time = end_time - start_time
        avg_time_per_query = total_time / len(queries) if queries else 0
        
        successful_queries = sum(1 for r in results if "error" not in r)
        success_rate = successful_queries / len(queries) if queries else 0
        
        self.results["concurrent_simulation"].append(avg_time_per_query)
        
        return {
            "test": "concurrent_simulation",
            "total_time": total_time,
            "average_time_per_query": avg_time_per_query,
            "successful_queries": successful_queries,
            "total_queries": len(queries),
            "success_rate": success_rate,
            "unit": "seconds per query"
        }
    
    def run_performance_benchmark(self) -> Dict[str, Any]:
        """Run all performance benchmarks."""
        print("Running MultiMind AI Performance Benchmark Suite...")
        print("=" * 60)
        
        benchmarks = [
            self.measure_simple_query_latency,
            self.measure_complex_query_latency,
            self.measure_memory_recall_speed,
            self.measure_concurrent_simulation
        ]
        
        results = []
        for benchmark_func in benchmarks:
            print(f"Running {benchmark_func.__name__}...")
            result = benchmark_func()
            results.append(result)
            print(f"  Result: {result}")
            print()
        
        print("=" * 60)
        print("PERFORMANCE BENCHMARK SUMMARY")
        print("=" * 60)
        for result in results:
            test_name = result.get("test", "unknown")
            if "average_time" in result:
                print(f"{test_name:30}: {result['average_time']:.3f}s")
            elif "average_time_per_query" in result:
                print(f"{test_name:30}: {result['average_time_per_query']:.3f}s/query")
            else:
                print(f"{test_name:30}: {result}")
        
        print("=" * 60)
        return {
            "benchmarks": results,
            "timestamp": time.time()
        }


def run_performance_benchmark():
    """Convenience function to run performance benchmark."""
    benchmark = PerformanceBenchmark()
    return benchmark.run_performance_benchmark()


if __name__ == "__main__":
    # Run the performance benchmark when executed directly
    results = run_performance_benchmark()
    
    # Save results
    import json
    with open("performance_benchmark_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print("\nDetailed performance results saved to performance_benchmark_results.json")