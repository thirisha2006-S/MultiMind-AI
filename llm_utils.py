"""
LLM utilities for MultiMind AI.
"""

import os
from langchain_core.messages import AIMessage
from langchain_cohere import ChatCohere
from langchain_openai import ChatOpenAI

# Track if we're in demo mode
_demo_mode = False


class MockLLM:
    """Mock LLM for demo mode when no valid API key is available."""
    
    def __init__(self, model: str = "demo"):
        self.model = model
    
    def invoke(self, messages):
        """Return mock responses based on the prompt type."""
        msg_text = ""
        for msg in messages:
            if hasattr(msg, 'content'):
                msg_text += msg.content.lower()
        
        # For classification prompts
        if "classify" in msg_text or "category" in msg_text:
            if any(kw in msg_text for kw in ["search", "find", "who", "what", "when", "where", "why", "research", "web"]):
                return AIMessage(content="research")
            elif any(kw in msg_text for kw in ["calculate", "compute", "solve", "code", "program", "python"]):
                return AIMessage(content="coding")
            else:
                return AIMessage(content="research")
        
        # For validator prompts
        if "validator" in msg_text or "validate" in msg_text:
            return AIMessage(content='{"is_valid": true, "confidence": 0.85, "issues": [], "suggestions": ["Demo mode - add API key for real validation"]}')
        
        # For reflection prompts
        if "reflection" in msg_text or "analyze" in msg_text:
            return AIMessage(content='{"workflow_quality": 0.75, "planning_feedback": "Good execution with clear steps in demo mode", "retrieval_quality": "relevant", "execution_efficiency": "optimal", "memory_updates": ["Demo execution completed"], "next_iteration_tips": ["Add API key for real LLM responses"]}')
        
        # For planner prompts
        if "planning" in msg_text or "plan" in msg_text:
            return AIMessage(content='{"tasks": [{"id": 1, "type": "research", "description": "Research task", "priority": 1}], "reasoning": "Demo plan for demonstration"}')
        
        # Default response
        return AIMessage(content="Demo mode: No API key configured. The system is working but using mock responses. Add COHERE_API_KEY or OPENAI_API_KEY for real LLM responses.")


class CohereLLM:
    """Wrapper for Cohere SDK to match LangChain interface."""
    
    def __init__(self, api_key: str, model: str = "command", temperature: float = 0):
        import cohere
        self.client = cohere.Client(api_key)
        self.model = model
        self.temperature = temperature
    
    def invoke(self, messages):
        """Invoke Cohere chat API."""
        # Convert messages to Cohere format
        chat_history = []
        message = ""
        
        for msg in messages[:-1]:
            role = "USER" if hasattr(msg, 'type') and msg.type == "human" else "CHATBOT"
            if hasattr(msg, 'content'):
                if role == "USER":
                    chat_history.append({"role": "USER", "message": msg.content})
                else:
                    chat_history.append({"role": "CHATBOT", "message": msg.content})
        
        # Get the last message (the actual query)
        if messages:
            last_msg = messages[-1]
            if hasattr(last_msg, 'content'):
                message = last_msg.content
        
        try:
            response = self.client.chat(
                model=self.model,
                message=message,
                chat_history=chat_history,
                temperature=self.temperature
            )
            return AIMessage(content=response.text)
        except Exception as e:
            raise Exception(f"Cohere API error: {str(e)}")


def get_llm_instance(temperature: float = 0, model: str = "gpt-4"):
    """Get configured LLM instance - uses Cohere/OpenAI as primary, MockLLM as fallback."""
    global _demo_mode
    
    # Try Cohere first
    cohere_api_key = os.getenv("COHERE_API_KEY")
    if cohere_api_key:
        _demo_mode = False
        try:
            # Use direct Cohere SDK for better compatibility
            return CohereLLM(
                api_key=cohere_api_key,
                model="command",
                temperature=temperature
            )
        except Exception as e:
            print(f"Cohere initialization error: {e}")
            _demo_mode = True
            return MockLLM(model="demo")
    
    # Fallback to OpenAI
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key and api_key != "your_openai_api_key_here":
        _demo_mode = False
        return ChatOpenAI(
            api_key=api_key,
            model=model,
            temperature=temperature
        )
    
    # Demo mode - no valid API key
    _demo_mode = True
    return MockLLM(model="demo")


def is_demo_mode():
    """Check if system is running in demo mode."""
    return _demo_mode