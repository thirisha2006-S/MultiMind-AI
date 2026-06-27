"""
Cost Optimizer for MultiMind AI Enterprise Knowledge Assistant.

Provides:
- Model tier classification (cheap/medium/expensive)
- Token counting and budgeting
- Automatic model routing based on task complexity
- Cost estimation per query
- Budget tracking with warnings
"""

import json
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class ModelTier(Enum):
    """Model cost tiers."""
    MOCK = "mock"           # Free (no API)
    CHEAP = "cheap"         # ~$0.001/1K tokens (Groq, Cohere Command-Light)
    MEDIUM = "medium"       # ~$0.01/1K tokens (GPT-3.5, Cohere Command-R)
    EXPENSIVE = "expensive" # ~$0.03/1K tokens (GPT-4, Claude)


@dataclass
class ModelConfig:
    """Configuration for a model tier."""
    tier: str
    provider: str
    model_name: str
    cost_per_1k_tokens: float
    max_tokens: int
    context_window: int
    description: str


# Model configurations (approximate pricing as of 2024)
MODEL_CONFIGS: Dict[str, ModelConfig] = {
    "mock": ModelConfig(
        tier="mock",
        provider="local",
        model_name="mock",
        cost_per_1k_tokens=0.0,
        max_tokens=500,
        context_window=2000,
        description="Free local mock for development",
    ),
    "command-r-08-2024": ModelConfig(
        tier="medium",
        provider="cohere",
        model_name="command-r-08-2024",
        cost_per_1k_tokens=0.0015,
        max_tokens=4000,
        context_window=128000,
        description="Cohere Command-R (balanced)",
    ),
    "gpt-4o": ModelConfig(
        tier="medium",
        provider="openai",
        model_name="gpt-4o",
        cost_per_1k_tokens=0.005,
        max_tokens=4000,
        context_window=128000,
        description="OpenAI GPT-4o (balanced)",
    ),
    "gpt-4": ModelConfig(
        tier="expensive",
        provider="openai",
        model_name="gpt-4",
        cost_per_1k_tokens=0.03,
        max_tokens=4000,
        context_window=8192,
        description="OpenAI GPT-4 (high quality)",
    ),
    "gpt-3.5-turbo": ModelConfig(
        tier="cheap",
        provider="openai",
        model_name="gpt-3.5-turbo",
        cost_per_1k_tokens=0.0005,
        max_tokens=4000,
        context_window=16385,
        description="OpenAI GPT-3.5 (fast/cheap)",
    ),
}


class TaskClassifier:
    """Classifies task complexity to select appropriate model tier."""

    # Keywords that indicate complexity
    COMPLEX_KEYWORDS = [
        "analyze", "compare", "evaluate", "synthesize", "comprehensive",
        "detailed", "in-depth", "complex", "advanced", "reasoning",
        "mathematical", "proof", "derive", "calculate", "optimize",
        "refactor", "architect", "design", "debug", "troubleshoot",
        "multi-step", "integrate", "combine", "research", "investigate",
    ]

    SIMPLE_KEYWORDS = [
        "what is", "define", "list", "name", "identify",
        "simple", "basic", "quick", "brief", "summary",
        "hello", "hi", "thanks", "thank you",
    ]

    @classmethod
    def classify(cls, query: str, context_length: int = 0) -> str:
        """
        Classify task complexity.
        
        Returns: "cheap", "medium", "expensive", or "mock"
        """
        query_lower = query.lower()
        
        # Check for complex indicators
        complex_score = sum(1 for kw in cls.COMPLEX_KEYWORDS if kw in query_lower)
        simple_score = sum(1 for kw in cls.SIMPLE_KEYWORDS if kw in query_lower)
        
        # Context length factor
        context_score = min(context_length / 10000, 2)
        
        total_score = complex_score + context_score - simple_score
        
        if total_score >= 3:
            return "expensive"
        elif total_score >= 1:
            return "medium"
        elif total_score <= -1:
            return "cheap"
        else:
            return "medium"

    @classmethod
    def should_use_tools(cls, query: str) -> bool:
        """Determine if query should use tools (search, code, etc.)."""
        tool_keywords = [
            "search", "find", "look up", "research", "current", "latest",
            "weather", "stock", "price", "news", "calculate", "compute",
            "run", "execute", "generate code", "write code", "script",
        ]
        query_lower = query.lower()
        return any(kw in query_lower for kw in tool_keywords)


class TokenCounter:
    """Estimate token counts for cost calculation."""

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """
        Rough token estimation: ~4 characters per token for English text.
        More accurate: use tiktoken if available.
        """
        try:
            import tiktoken
            enc = tiktoken.encoding_for_model("gpt-4")
            return len(enc.encode(text))
        except ImportError:
            # Fallback estimation
            return max(1, len(text) // 4)

    @classmethod
    def estimate_cost(cls, text: str, model_config: ModelConfig) -> float:
        """Estimate cost for a text given a model config."""
        tokens = cls.estimate_tokens(text)
        cost = (tokens / 1000) * model_config.cost_per_1k_tokens
        return cost


class BudgetTracker:
    """Track spending against a budget."""

    def __init__(self, budget_dollars: float = 10.0):
        self.total_budget = budget_dollars
        self.current_spend = 0.0
        self.query_costs: List[Dict] = []
        self.warning_threshold = 0.8  # Warn at 80% of budget

    def record_cost(self, cost: float, query: str = "", user_id: str = ""):
        """Record a query cost."""
        self.current_spend += cost
        self.query_costs.append({
            "cost": cost,
            "query": query[:100],
            "user_id": user_id,
            "timestamp": datetime.now().isoformat(),
        })
        
        if self.current_spend >= self.total_budget * self.warning_threshold:
            logger.warning(f"[Cost] Budget warning: ${self.current_spend:.4f} / ${self.total_budget:.2f} ({self.current_spend/self.total_budget*100:.1f}%)")

    def get_remaining_budget(self) -> float:
        """Get remaining budget."""
        return max(0.0, self.total_budget - self.current_spend)

    def get_budget_status(self) -> Dict:
        """Get budget status summary."""
        pct_used = (self.current_spend / self.total_budget * 100) if self.total_budget > 0 else 0
        return {
            "total_budget": self.total_budget,
            "current_spend": self.current_spend,
            "remaining": self.get_remaining_budget(),
            "percent_used": pct_used,
            "warning": pct_used >= 80,
            "exceeded": self.current_spend >= self.total_budget,
        }

    def reset(self):
        """Reset budget tracking."""
        self.current_spend = 0.0
        self.query_costs = []


class CostOptimizer:
    """Main cost optimization engine."""

    def __init__(self, budget_dollars: float = 10.0):
        self.token_counter = TokenCounter()
        self.classifier = TaskClassifier()
        self.budget_tracker = BudgetTracker(budget_dollars)
        self.current_model: str = "mock"
        self.model_config = MODEL_CONFIGS.get("mock")

    def select_model(self, query: str, context_length: int = 0, force_tier: str = None) -> str:
        """
        Select the best model for a query based on cost/performance tradeoff.
        
        Args:
            query: User query text
            context_length: Length of context in characters
            force_tier: Override with specific tier
        
        Returns:
            Model name to use
        """
        if force_tier:
            tier = force_tier
        else:
            tier = self.classifier.classify(query, context_length)
        
        # Find best model for tier
        if tier == "mock":
            return "mock"
        elif tier == "cheap":
            return "gpt-3.5-turbo"
        elif tier == "medium":
            return "command-r-08-2024"
        elif tier == "expensive":
            return "gpt-4"
        else:
            return "mock"

    def estimate_query_cost(self, query: str, context_text: str = "", model: str = None) -> Dict:
        """Estimate cost for a query before execution."""
        model_name = model or self.current_model
        config = MODEL_CONFIGS.get(model_name, MODEL_CONFIGS["mock"])
        
        query_tokens = self.token_counter.estimate_tokens(query)
        context_tokens = self.token_counter.estimate_tokens(context_text)
        total_tokens = query_tokens + context_tokens
        
        estimated_cost = (total_tokens / 1000) * config.cost_per_1k_tokens
        
        return {
            "model": model_name,
            "tier": config.tier,
            "estimated_tokens": total_tokens,
            "estimated_cost_usd": estimated_cost,
            "cost_per_1k_tokens": config.cost_per_1k_tokens,
            "budget_remaining": self.budget_tracker.get_remaining_budget(),
        }

    def record_execution(self, query: str, context_text: str, model: str, actual_tokens: int = None):
        """Record actual execution cost."""
        config = MODEL_CONFIGS.get(model, MODEL_CONFIGS["mock"])
        
        if actual_tokens:
            cost = (actual_tokens / 1000) * config.cost_per_1k_tokens
        else:
            text = query + context_text
            cost = self.token_counter.estimate_cost(text, config)
        
        self.budget_tracker.record_cost(cost, query)
        return cost

    def get_budget_status(self) -> Dict:
        """Get current budget status."""
        return self.budget_tracker.get_budget_status()

    def should_proceed(self, estimated_cost: float) -> Tuple[bool, str]:
        """
        Check if execution should proceed based on budget.
        
        Returns:
            (should_proceed, reason)
        """
        status = self.budget_tracker.get_budget_status()
        
        if status["exceeded"]:
            return False, f"Budget exceeded: ${status['current_spend']:.4f} / ${status['total_budget']:.2f}"
        
        if status["warning"]:
            logger.warning(f"[Cost] Approaching budget limit: {status['percent_used']:.1f}% used")
        
        return True, "OK"

    def get_cost_report(self) -> Dict:
        """Get cost report summary."""
        status = self.budget_tracker.get_budget_status()
        recent = self.budget_tracker.query_costs[-10:] if self.budget_tracker.query_costs else []
        
        return {
            "budget": status,
            "total_queries": len(self.budget_tracker.query_costs),
            "recent_queries": recent,
            "average_cost_per_query": (
                sum(q["cost"] for q in self.budget_tracker.query_costs) / len(self.budget_tracker.query_costs)
                if self.budget_tracker.query_costs else 0.0
            ),
        }


# Global cost optimizer instance
_cost_optimizer: Optional[CostOptimizer] = None


def get_cost_optimizer(budget_dollars: float = 10.0) -> CostOptimizer:
    """Get or create the global cost optimizer."""
    global _cost_optimizer
    if _cost_optimizer is None:
        _cost_optimizer = CostOptimizer(budget_dollars)
    return _cost_optimizer


def select_optimal_model(query: str, context_length: int = 0, force_tier: str = None) -> str:
    """Convenience function to select optimal model."""
    optimizer = get_cost_optimizer()
    return optimizer.select_model(query, context_length, force_tier)


def estimate_cost(query: str, context_text: str = "", model: str = None) -> Dict:
    """Convenience function to estimate query cost."""
    optimizer = get_cost_optimizer()
    return optimizer.estimate_query_cost(query, context_text, model)
