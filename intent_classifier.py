"""
Intent Classifier for MultiMind AI
Classifies user input into intents before routing to agents.
Provides natural, human-like conversational responses.
"""

from enum import Enum
from typing import Tuple


class Intent(Enum):
    """Intent types for user input."""
    GREETING = "greeting"
    SMALL_TALK = "small_talk"
    HELP = "help"
    GOODBYE = "goodbye"
    THANKS = "thanks"
    IDENTITY = "identity"
    ENTERPRISE_QUERY = "enterprise_query"
    CODING_QUERY = "coding_query"
    UNKNOWN = "unknown"


# Intent keyword lists
GREETING_KEYWORDS = [
    "hi", "hello", "hey", "greetings", "good morning", "good afternoon", 
    "good evening", "yo", "howdy"
]

SMALL_TALK_KEYWORDS = [
    "how are you", "how are u", "what's up", "whats up", "how is your day",
    "how's it going", "how are things", "nice to meet you"
]

THANKS_KEYWORDS = [
    "thank you", "thanks", "thx", "ty", "thank you so much"
]

GOODBYE_KEYWORDS = [
    "bye", "goodbye", "see you", "see ya", "good night", "later", "farewell", "peace"
]

IDENTITY_KEYWORDS = [
    "who are you", "what are you", "who is this", "what is this"
]

CODING_KEYWORDS = [
    "code", "coding", "script", "function", "class", "python", "javascript",
    "java", "c++", "debug", "error", "bug", "implement", "algorithm",
    "write code", "write a function", "api", "django", "react", "node.js"
]

QUESTION_WORDS = ["what", "how", "why", "when", "where", "who", "which", "can you"]


def classify_intent(prompt: str) -> Tuple[Intent, str]:
    """
    Classify user input into an intent.
    
    Returns:
        Tuple of (Intent, response_text or None)
        For conversational intents, returns the response text.
        For query intents, returns None.
    """
    prompt_lower = prompt.lower().strip().rstrip("!").rstrip("?")
    
    # Check identity questions first
    for keyword in IDENTITY_KEYWORDS:
        if keyword in prompt_lower:
            return Intent.IDENTITY, get_identity_response()
    
    # Check thanks
    for keyword in THANKS_KEYWORDS:
        if keyword in prompt_lower:
            return Intent.THANKS, get_thanks_response()
    
    # Check greetings - exact match or starts with
    for keyword in GREETING_KEYWORDS:
        if prompt_lower == keyword or prompt_lower.startswith(keyword + " "):
            return Intent.GREETING, get_greeting_response()
    
    # Check small talk
    for keyword in SMALL_TALK_KEYWORDS:
        if keyword in prompt_lower:
            return Intent.SMALL_TALK, get_small_talk_response()
    
    # Check help - this is handled as help, not unknown
    if "what can you do" in prompt_lower or "what can you help" in prompt_lower:
        return Intent.HELP, get_help_response()
    
    # Check goodbye
    for keyword in GOODBYE_KEYWORDS:
        if prompt_lower == keyword or prompt_lower.startswith(keyword + " "):
            return Intent.GOODBYE, get_goodbye_response()
    
    # Check coding queries
    for keyword in CODING_KEYWORDS:
        if keyword in prompt_lower:
            return Intent.CODING_QUERY, None
    
    # Check if it's a real business question
    if any(prompt_lower.startswith(q) for q in QUESTION_WORDS):
        # Filter out incomplete/unclear questions
        if len(prompt.split()) < 3 and prompt_lower.split()[0] in QUESTION_WORDS:
            return Intent.UNKNOWN, get_natural_unclear_response()
        return Intent.ENTERPRISE_QUERY, None
    
    # Default: if it looks like a statement about knowledge/docs, treat as enterprise query
    knowledge_keywords = ["policy", "document", "leave", "handbook", "sop", "rule", "procedure", "knowledge", "hr", "benefits", "salary"]
    if any(kw in prompt_lower for kw in knowledge_keywords):
        return Intent.ENTERPRISE_QUERY, None
    
    # Unclear input - but respond naturally
    if len(prompt.strip()) < 5 or prompt_lower in ["what", "how", "why"]:
        return Intent.UNKNOWN, get_natural_unclear_response()
    
    # Default to enterprise query if it seems like a request
    return Intent.ENTERPRISE_QUERY, None


def get_greeting_response() -> str:
    """Response for greetings - friendly and direct."""
    return """Hey there! 😊

What can I help you with today?"""


def get_small_talk_response() -> str:
    """Response for small talk - natural conversation."""
    return """I'm doing great, thanks for asking! 

I'm ready when you are - just let me know what you'd like to dive into."""


def get_thanks_response() -> str:
    """Response for thanks - warm and encouraging."""
    return """Anytime! 

Anything else I can help with?"""


def get_identity_response() -> str:
    """Response for identity questions - clear but friendly."""
    return """I'm MultiMind AI!

I'm your go-to for searching company docs, answering policy questions, or comparing documents. Think of me as your knowledge base assistant."""


def get_help_response() -> str:
    """Response for help requests - simple guidance."""
    return """Happy to help!

Just ask me about anything in your organization's knowledge base - policies, procedures, or documents."""


def get_goodbye_response() -> str:
    """Response for goodbyes - warm sign-off."""
    return """See you later! 👋

Come back anytime you need to dig into your docs."""


def get_natural_unclear_response() -> str:
    """Natural response for unclear inputs - conversational, not robotic."""
    return """Hey! What's on your mind?

Ask me something like "What's our leave policy?" or "Find docs about PTO" """


def get_intent_label(intent: Intent) -> str:
    """Get a human-readable label for the intent."""
    labels = {
        Intent.GREETING: "Greeting",
        Intent.SMALL_TALK: "Small Talk",
        Intent.HELP: "Help Request",
        Intent.GOODBYE: "Goodbye",
        Intent.THANKS: "Thanks",
        Intent.IDENTITY: "Identity Question",
        Intent.ENTERPRISE_QUERY: "Enterprise Query",
        Intent.CODING_QUERY: "Coding Query",
        Intent.UNKNOWN: "Ambiguous"
    }
    return labels.get(intent, "Unknown")