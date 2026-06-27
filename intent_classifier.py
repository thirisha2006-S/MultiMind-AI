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
GREETING_KEYWORDS = ["hi", "hello", "hey", "greetings", "good morning", "good afternoon", "good evening"]

SMALL_TALK_KEYWORDS = ["how are you", "how are u", "what's up", "whats up", "how is your day", "how's it going", "how are things"]

THANKS_KEYWORDS = ["thank you", "thanks", "thx", "ty", "thank you so much"]

GOODBYE_KEYWORDS = ["bye", "goodbye", "see you", "see ya", "good night", "later", "farewell"]

IDENTITY_KEYWORDS = ["who are you", "what are you", "who is this", "what is this"]

CODING_KEYWORDS = ["code", "coding", "script", "function", "class", "python", "javascript", "java", "c++", "debug", "error", "bug", "implement", "api", "django", "react"]

QUESTION_WORDS = ["what", "how", "why", "when", "where", "who", "which", "can you"]


def classify_intent(prompt: str) -> Tuple[Intent, str]:
    """
    Classify user input into an intent.
    """
    prompt_lower = prompt.lower().strip().rstrip("!").rstrip("?")
    
    # Check identity questions
    for keyword in IDENTITY_KEYWORDS:
        if keyword in prompt_lower:
            return Intent.IDENTITY, get_identity_response()
    
    # Check thanks
    for keyword in THANKS_KEYWORDS:
        if keyword in prompt_lower:
            return Intent.THANKS, get_thanks_response()
    
    # Check greetings
    for keyword in GREETING_KEYWORDS:
        if prompt_lower == keyword or prompt_lower.startswith(keyword + " "):
            return Intent.GREETING, get_greeting_response()
    
    # Check small talk
    for keyword in SMALL_TALK_KEYWORDS:
        if keyword in prompt_lower:
            return Intent.SMALL_TALK, get_small_talk_response()
    
    # Check help
    if "what can you do" in prompt_lower or "help" in prompt_lower:
        return Intent.HELP, get_help_response()
    
    # Check goodbye
    for keyword in GOODBYE_KEYWORDS:
        if prompt_lower == keyword or prompt_lower.startswith(keyword + " "):
            return Intent.GOODBYE, get_goodbye_response()
    
    # Check coding queries
    for keyword in CODING_KEYWORDS:
        if keyword in prompt_lower:
            return Intent.CODING_QUERY, None
    
    # Check business questions
    if any(prompt_lower.startswith(q) for q in QUESTION_WORDS):
        if len(prompt.split()) < 3 and prompt_lower.split()[0] in QUESTION_WORDS:
            return Intent.UNKNOWN, get_natural_unclear_response()
        return Intent.ENTERPRISE_QUERY, None
    
    # Default detection
    knowledge_keywords = ["policy", "document", "leave", "handbook", "sop", "hr", "benefits", "salary"]
    if any(kw in prompt_lower for kw in knowledge_keywords):
        return Intent.ENTERPRISE_QUERY, None
    
    if len(prompt.strip()) < 5 or prompt_lower in ["what", "how", "why"]:
        return Intent.UNKNOWN, get_natural_unclear_response()
    
    return Intent.ENTERPRISE_QUERY, None


def get_greeting_response() -> str:
    """NATURAL greeting - like ChatGPT would reply."""
    return "Hey! What's up? How can I help you today?"


def get_small_talk_response() -> str:
    """NATURAL small talk - like a friend replying."""
    return "I'm good, thanks! Just hanging out here ready to help. What's on your mind?"


def get_thanks_response() -> str:
    """NATURAL thanks response."""
    return "You're welcome! Anything else I can help with?"


def get_identity_response() -> str:
    """NATURAL identity response."""
    return "I'm MultiMind AI - I help you search through your company documents and answer questions about policies."


def get_help_response() -> str:
    """NATURAL help response."""
    return "I can help you find info in your company docs, answer policy questions, or compare documents. What do you need?"


def get_goodbye_response() -> str:
    """NATURAL goodbye response."""
    return "Take care! Catch you later."


def get_natural_unclear_response() -> str:
    """NATURAL unclear response - like ChatGPT."""
    return "Hmm, I'm not quite following. Could you give me a bit more to go on? Maybe ask about a policy or document?"


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