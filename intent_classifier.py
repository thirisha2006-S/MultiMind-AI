"""
Intent Classifier for MultiMind AI
Classifies user input into intents before routing to agents.
"""

from enum import Enum
from typing import Tuple


class Intent(Enum):
    """Intent types for user input."""
    GREETING = "greeting"
    SMALL_TALK = "small_talk"
    HELP = "help"
    GOODBYE = "goodbye"
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

HELP_KEYWORDS = [
    "help", "what can you do", "what can you help", "capabilities",
    "what do you do", "assist me", "support"
]

GOODBYE_KEYWORDS = [
    "bye", "goodbye", "see you", "see ya", "good night", "later", "farewell"
]

CODING_KEYWORDS = [
    "code", "coding", "script", "function", "class", "python", "javascript",
    "java", "c++", "debug", "error", "bug", "implement", "algorithm",
    "write code", "write a function"
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
    
    # Check greetings - but not if it's a real question
    for keyword in GREETING_KEYWORDS:
        if prompt_lower == keyword or prompt_lower.startswith(keyword + " "):
            return Intent.GREETING, get_greeting_response()
    
    # Check small talk
    for keyword in SMALL_TALK_KEYWORDS:
        if keyword in prompt_lower:
            return Intent.SMALL_TALK, get_small_talk_response()
    
    # Check help
    for keyword in HELP_KEYWORDS:
        if keyword in prompt_lower:
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
    # Questions starting with what/how/why etc. about policies/docs
    if any(prompt_lower.startswith(q) for q in QUESTION_WORDS):
        # But filter out incomplete/unclear questions
        if len(prompt.split()) < 3 and prompt_lower.split()[0] in QUESTION_WORDS:
            return Intent.UNKNOWN, get_unclear_response()
        return Intent.ENTERPRISE_QUERY, None
    
    # Default: if it looks like a statement about knowledge/docs, treat as enterprise query
    knowledge_keywords = ["policy", "document", "leave", "handbook", "sop", "rule", "procedure", "knowledge"]
    if any(kw in prompt_lower for kw in knowledge_keywords):
        return Intent.ENTERPRISE_QUERY, None
    
    # Unclear input
    if len(prompt.strip()) < 5 or prompt_lower in ["what", "how", "why"]:
        return Intent.UNKNOWN, get_unclear_response()
    
    # Default to enterprise query if it seems like a request
    return Intent.ENTERPRISE_QUERY, None


def get_greeting_response() -> str:
    """Response for greetings."""
    return """👋 Welcome to **MultiMind AI**!

I'm your enterprise knowledge assistant. I can help you:

* 📄 Search company documents
* 🔍 Answer questions from the knowledge base  
* ⚠️ Detect conflicting information
* 📊 Explain how confident I am in my answers

Try asking:

* "What is our leave policy?"
* "Summarize the HR handbook."
* "Compare the 2024 and 2026 leave policies." """


def get_small_talk_response() -> str:
    """Response for small talk."""
    return """I'm doing well, thanks for asking! 😊

I'm ready to help you search enterprise documents, answer questions, or analyze knowledge. What would you like to know? """


def get_help_response() -> str:
    """Response for help requests."""
    return """I'm here to help you with your organization's knowledge base.

You can ask me:

* **Policy questions** — "What is our leave policy?"
* **Document summaries** — "Summarize the HR handbook"
* **Comparisons** — "Compare 2024 vs 2026 policies"
* **Knowledge health** — "Show knowledge health report"

Just type your question and I'll find the relevant information. """


def get_goodbye_response() -> str:
    """Response for goodbyes."""
    return """Goodbye! Have a great day. 👋

If you need help with your organization's knowledge base, I'm here anytime. """


def get_unclear_response() -> str:
    """Response for unclear/ambiguous inputs."""
    return """I'm not sure what you're asking.

Could you provide a little more detail?

For example:

* "What is our leave policy?"
* "What is the travel reimbursement policy?"
* "What documents are available?" """


def get_intent_label(intent: Intent) -> str:
    """Get a human-readable label for the intent."""
    labels = {
        Intent.GREETING: "Greeting",
        Intent.SMALL_TALK: "Small Talk",
        Intent.HELP: "Help Request",
        Intent.GOODBYE: "Goodbye",
        Intent.ENTERPRISE_QUERY: "Enterprise Query",
        Intent.CODING_QUERY: "Coding Query",
        Intent.UNKNOWN: "Ambiguous"
    }
    return labels.get(intent, "Unknown")