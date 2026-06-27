"""
Intent Classifier for MultiMind AI
Determines whether to use the LLM pipeline or show Knowledge Health dashboard.
"""

from enum import Enum


class Intent(Enum):
    """Intent types for user input."""
    CONVERSATION = "conversation"      # Small talk/greetings - still use LLM naturally
    ENTERPRISE_QUERY = "enterprise_query"  # Knowledge base questions - full pipeline
    CODING_QUERY = "coding_query"      # Code-related - coding pipeline


def classify_intent(prompt: str) -> tuple:
    """
    Classify user input into an intent.
    For CONVERSATION and CODING_QUERY, returns (intent, None) - still uses LLM.
    Returns (intent, response) tuple - response is only used for trivial edge cases.
    """
    prompt_lower = prompt.lower().strip().rstrip("!").rstrip("?")
    
    # Very short inputs that need LLM to respond naturally
    very_short = ["hi", "hello", "hey", "thanks", "bye", "ok"]
    if prompt_lower in very_short:
        return Intent.CONVERSATION, None
    
    # Small talk that still needs LLM
    if any(x in prompt_lower for x in ["how are you", "what's up", "who are you"]):
        return Intent.CONVERSATION, None
    
    # Coding keywords
    coding_words = ["code", "function", "python", "javascript", "debug", "api", "script", "class", "django", "react"]
    if any(word in prompt_lower for word in coding_words):
        return Intent.CODING_QUERY, None
    
    # Everything else goes through the research pipeline
    return Intent.ENTERPRISE_QUERY, None