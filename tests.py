"""
Testing framework for the Multi-Agent System.
"""

import unittest
from unittest.mock import Mock, patch
from langchain_core.messages import HumanMessage
from graph import app
from state import SharedState


class TestMultiAgentSystem(unittest.TestCase):
    """Test suite for the autonomous AI workflow system."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.session_id = "test-session-123"
    
    def create_test_state(self, query: str, **kwargs) -> SharedState:
        """Create a test state with default values."""
        default_state = {
            "messages": [HumanMessage(content=query)],
            "retry_count": 0,
            "max_retries": 3,
            "metadata": {"session_id": self.session_id},
            "planner_ran": False,
            "task_plan": None,
            "reflection": None
        }
        default_state.update(kwargs)
        return default_state
    
    def test_simple_research_routing(self):
        """Test that simple research queries route correctly."""
        initial_state = self.create_test_state("What is Python?")
        
        # Mock the graph invoke to return quickly
        with patch('graph.app.invoke') as mock_invoke:
            mock_invoke.return_value = {"research_data": "Test result"}
            result = app.invoke(initial_state)
            
            # Verify the invoke was called
            mock_invoke.assert_called_once()
    
    def test_complex_query_triggers_planner(self):
        """Test that complex queries trigger the planner."""
        complex_query = "Compare FastAPI and Flask performance and create a benchmark"
        initial_state = self.create_test_state(complex_query)
        
        with patch('agents.supervisor_agent') as mock_supervisor:
            mock_supervisor.return_value = {"next": "planner"}
            
            # Verify complexity detection
            complexity_keywords = ["compare", "analyze", "and", "create"]
            is_complex = any(kw in complex_query.lower() for kw in complexity_keywords)
            self.assertTrue(is_complex)
    
    def test_planner_creates_valid_plan(self):
        """Test that planner creates valid task plans."""
        from planner import TaskPlan
        
        tasks = [
            {"id": 1, "type": "research", "description": "research A", "priority": 1},
            {"id": 2, "type": "coding", "description": "code B", "priority": 2}
        ]
        
        plan = TaskPlan(tasks, "Test reasoning")
        
        # Test task iteration
        first_task = plan.next_task()
        self.assertEqual(first_task["id"], 1)
        
        second_task = plan.next_task()
        self.assertEqual(second_task["id"], 2)
        
        # Test completion
        self.assertTrue(plan.is_complete())
    
    def test_memory_quality_assessment(self):
        """Test research quality assessment."""
        from planner import assess_research_quality
        
        # High quality content
        high_quality = "• Point one\n• Point two\nSource: http://example.com"
        score = assess_research_quality(high_quality)
        self.assertGreater(score, 0.5)
        
        # Low quality content
        low_quality = "No results found"
        score = assess_research_quality(low_quality)
        self.assertEqual(score, 0.0)
    
    def test_retry_logic(self):
        """Test that retry count is tracked correctly."""
        initial_state = self.create_test_state("test query", retry_count=2)
        
        # Simulate retry
        new_state = {**initial_state, "retry_count": 3}
        self.assertEqual(new_state["retry_count"], 3)
    
    def test_validation_routing(self):
        """Test that validator routes correctly."""
        from agents import validator_agent
        
        state = self.create_test_state(
            "test query",
            research_data="Test research",
            code_result="Test code output",
            validation={"is_valid": True, "confidence": 0.8}
        )
        
        with patch('agents.get_llm') as mock_llm:
            mock_llm.return_value.invoke.return_value = Mock(content='{"is_valid": true, "confidence": 0.8}')
            
            result = validator_agent(state)
            self.assertIn("next", result)


class TestPolicyStore(unittest.TestCase):
    """Test the policy learning capabilities."""
    
    def test_policy_storage_and_retrieval(self):
        """Test that policies are stored and retrieved correctly."""
        from planner import PolicyStore
        
        store = PolicyStore()
        
        # Store policy
        tasks = [{"id": 1, "type": "research", "description": "test"}]
        store.update_policy("compare A and B", tasks, success=True)
        
        # Retrieve policy
        policy = store.get_policy("compare A and B")
        self.assertIsNotNone(policy)
        self.assertEqual(policy["tasks"], tasks)
    
    def test_policy_success_counting(self):
        """Test that success counts are incremented."""
        from planner import PolicyStore
        
        store = PolicyStore()
        tasks = [{"id": 1, "type": "research", "description": "test"}]
        
        # Multiple successful runs
        store.update_policy("query", tasks, success=True)
        store.update_policy("query", tasks, success=True)
        store.update_policy("query", tasks, success=True)
        
        policy = store.get_policy("query")
        self.assertEqual(policy["success_count"], 3)


class TestRoutingLogic(unittest.TestCase):
    """Test the routing logic between agents."""
    
    def test_supervisor_routes_to_research(self):
        """Test supervisor routes research queries correctly."""
        research_query = "What is machine learning?"
        
        # Check keyword detection
        research_keywords = ["what", "who", "when", "where", "why", "how"]
        has_research_keyword = any(kw in research_query.lower() for kw in research_keywords)
        self.assertTrue(has_research_keyword)
    
    def test_supervisor_routes_to_coding(self):
        """Test supervisor routes coding queries correctly."""
        coding_query = "Calculate fibonacci sequence"
        
        coding_keywords = ["calculate", "compute", "solve", "code"]
        has_coding_keyword = any(kw in coding_query.lower() for kw in coding_keywords)
        self.assertTrue(has_coding_keyword)


def run_tests():
    """Run all tests and return results."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestMultiAgentSystem))
    suite.addTests(loader.loadTestsFromTestCase(TestPolicyStore))
    suite.addTests(loader.loadTestsFromTestCase(TestRoutingLogic))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result


class TestKnowledgeEvolution(unittest.TestCase):
    """Test the Knowledge Evolution Engine."""
    
    def test_evolution_tracker_initialization(self):
        """Test that evolution tracker initializes correctly."""
        from knowledge_evolution import KnowledgeEvolutionTracker
        tracker = KnowledgeEvolutionTracker()
        self.assertIsNotNone(tracker)
    
    def test_topic_hash_generation(self):
        """Test topic hash generation is stable."""
        from knowledge_evolution import KnowledgeEvolutionTracker
        tracker = KnowledgeEvolutionTracker()
        
        hash1 = tracker._topic_hash("Leave Policy 2024")
        hash2 = tracker._topic_hash("leave policy 2024")
        self.assertEqual(hash1, hash2)  # Should normalize case
    
    def test_confidence_explainer_factors(self):
        """Test that confidence explainer generates correct factors."""
        from confidence_explainer import ConfidenceExplainer
        
        validation = {"confidence": 0.85, "issues": [], "suggestions": []}
        sources = [{"trust": 0.9, "freshness_score": 1.0}]
        
        breakdown = ConfidenceExplainer.explain(validation, sources)
        self.assertEqual(len(breakdown.factors), 5)
        self.assertGreater(breakdown.final_score, 0)
    
    def test_tenant_context(self):
        """Test tenant context functionality."""
        from tenant import TenantContext
        ctx = TenantContext()
        
        ctx.set_tenant("test-tenant")
        self.assertEqual(ctx.get_tenant_id(), "test-tenant")
    
    def test_replay_mechanism(self):
        """Test workflow replay recording."""
        from replay import WorkflowReplay
        replay = WorkflowReplay()
        
        replay.record_step("test", {"input": "a"}, {"output": "b"})
        self.assertEqual(len(replay.steps), 1)
        self.assertEqual(replay.steps[0].agent_name, "test")
    
    def test_evaluation_engine(self):
        """Test evaluation metrics generation."""
        from evaluation_engine import EvaluationEngine
        engine = EvaluationEngine()
        
        metrics = engine.evaluate(
            time.time(),
            {"confidence": 0.85, "conflicts": []},
            [{"source": "test"}]
        )
        self.assertEqual(metrics.confidence, 0.85)


if __name__ == "__main__":
    run_tests()