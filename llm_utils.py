"""
MultiMind AI - Dual Mode Architecture
Coding Mode (pure LLM) and Research Mode (with tools)
"""

import os
import json
from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

# Load environment variables (safe to call multiple times)
load_dotenv()

# Try to import Cohere SDK directly for better compatibility
try:
    import cohere
    COHERE_SDK_AVAILABLE = True
except ImportError:
    COHERE_SDK_AVAILABLE = False
    cohere = None


class CohereLLM:
    """Wrapper for Cohere SDK to match LangChain interface."""
    
    def __init__(self, api_key: str, model: str = "command-r-08-2024", temperature: float = 0):
        self.client = cohere.Client(api_key=api_key)
        self.model = model
        self.temperature = temperature
    
    def invoke(self, messages):
        # Extract the user query (last HumanMessage)
        query = ""
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                query = msg.content
                break
        
        try:
            response = self.client.chat(
                model=self.model,
                message=query,
                temperature=self.temperature
            )
            return AIMessage(content=response.text)
        except Exception as e:
            return AIMessage(content=f"Cohere error: {str(e)}")


# Track current mode
_current_mode = "coding"  # Default mode


def set_mode(mode: str):
    """Set the operational mode: 'coding' or 'research'."""
    global _current_mode
    _current_mode = mode


def get_mode():
    """Get current mode."""
    return _current_mode


def get_coding_llm(temperature: float = 0, model: str = None):
    """Get LLM for coding mode - pure reasoning, no search."""
    from cost_optimizer import get_cost_optimizer
    
    optimizer = get_cost_optimizer()
    selected_model = model or optimizer.select_model("coding task", force_tier="medium")
    config = {"command-r-08-2024": "command-r-08-2024", "gpt-3.5-turbo": "gpt-3.5-turbo", "gpt-4o": "gpt-4o", "mock": "mock"}
    model_name = config.get(selected_model, "command-r-08-2024")
    
    # Cohere preferred (using SDK directly)
    if COHERE_SDK_AVAILABLE:
        cohere_api_key = os.getenv("COHERE_API_KEY")
        if cohere_api_key:
            return CohereLLM(api_key=cohere_api_key, model=model_name, temperature=temperature)
    
    # OpenAI fallback
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key and api_key != "your_openai_api_key_here":
        return ChatOpenAI(api_key=api_key, model=model_name, temperature=temperature)
    
    # Demo mode fallback
    return MockLLMCoding()


def get_llm_instance(temperature: float = 0, model: str = "gpt-4"):
    """Get LLM instance for agents - delegates to get_coding_llm with cost optimization."""
    from cost_optimizer import get_cost_optimizer
    optimizer = get_cost_optimizer()
    
    # Select model based on cost optimizer
    selected_model = optimizer.select_model(model or "gpt-4", force_tier="medium")
    
    # Cohere preferred
    if COHERE_SDK_AVAILABLE:
        cohere_api_key = os.getenv("COHERE_API_KEY")
        if cohere_api_key:
            return CohereLLM(api_key=cohere_api_key, model="command-r-08-2024", temperature=temperature)
    
    # OpenAI fallback
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key and api_key != "your_openai_api_key_here":
        return ChatOpenAI(api_key=api_key, model="gpt-4o", temperature=temperature)
    
    # Demo mode fallback
    return MockLLMCoding()


def is_demo_mode() -> bool:
    """Check if running in demo mode (no valid API keys)."""
    cohere_api_key = os.getenv("COHERE_API_KEY")
    openai_api_key = os.getenv("OPENAI_API_KEY")
    return not (cohere_api_key or (openai_api_key and openai_api_key != "your_openai_api_key_here"))


class MockLLMCoding:
    """Mock LLM for coding mode in demo."""
    
    def invoke(self, messages):
        # Extract user query - look for HumanMessage specifically, not just any message
        query = ""
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                query = msg.content
                break
            elif hasattr(msg, 'content') and query == "":
                # Fallback to any message as last resort
                query = msg.content
        
        # Simple mock responses for coding tasks
        if "factorial" in query.lower():
            return AIMessage(content="```python\ndef factorial(n):\n    return 1 if n <= 1 else n * factorial(n - 1)\n\nprint(factorial(10))  # 3628800\n```")
        elif "bmi" in query.lower():
            return AIMessage(content="```python\ndef calculate_bmi(weight_kg, height_m):\n    return weight_kg / (height_m ** 2)\n\n# Example: weight=70kg, height=1.75m\nbmi = calculate_bmi(70, 1.75)\nprint(f\"BMI: {bmi:.1f}\")\n```")
        elif "python" in query.lower() or "code" in query.lower():
            return AIMessage(content=f"Here's a Python solution:\n\n```python\n# Code for: {query}\nprint('Working on it!')\n```")
        
        return AIMessage(content=f"Answer for: {query}")


def chat_coding_mode(query: str) -> dict:
    """Pure LLM coding mode - no search, direct answers with cost tracking."""
    from cost_optimizer import get_cost_optimizer
    optimizer = get_cost_optimizer()
    
    cost_info = optimizer.estimate_query_cost(query)
    st_cost = cost_info["estimated_cost_usd"]
    
    llm = get_coding_llm(temperature=0)
    
    system_prompt = SystemMessage(content="""You are an AI coding assistant.

You must NOT perform web search or return external links.
You must NOT show research results, articles, or references.
You must directly answer the user request.

If the user asks for code:
- Provide clean, working code only
- No explanations unless asked
- No URLs
- No browsing content

If the user request is unclear:
- Ask a short clarification question

Output must be:
- Direct answer only
- No extra content
- No metadata
- No 'research results' section""")
    
    user_prompt = HumanMessage(content=query)
    
    try:
        response = llm.invoke([system_prompt, user_prompt])
        cost = optimizer.record_execution(query, "", "command-r", optimizer.token_counter.estimate_tokens(query + response.content))
        return {"final_answer": response.content, "research_data": None, "estimated_cost": cost}
    except Exception as e:
        return {"final_answer": f"Error: {str(e)}", "research_data": None}


def chat_research_mode(query: str) -> dict:
    """Research mode - with web search capabilities and cost tracking."""
    from cost_optimizer import get_cost_optimizer
    optimizer = get_cost_optimizer()
    
    try:
        from tools import get_tavily_tool
        search_results = get_tavily_tool().invoke({"query": query})
        
        formatted = "Research Results:\n\n"
        if isinstance(search_results, list):
            for i, r in enumerate(search_results[:3], 1):
                if isinstance(r, dict):
                    title = r.get('title', 'Result')
                    content = r.get('content', '')[:200]
                    url = r.get('url', '')
                    formatted += f"{i}. {title}\n"
                    formatted += f"   {content}...\n"
                    if url:
                        formatted += f"   Source: {url}\n\n"
        
        # Estimate cost
        cost = optimizer.estimate_query_cost(query, formatted)
        optimizer.record_execution(query, formatted, "tavily_search", cost["estimated_tokens"])
        
        return {"final_answer": formatted, "research_data": formatted, "estimated_cost": cost["estimated_cost_usd"]}
    except Exception as e:
        # Graceful fallback
        return {"final_answer": f"Research error: {str(e)}\n\nAdd TAVILY_API_KEY to .env for web search.", "research_data": None}