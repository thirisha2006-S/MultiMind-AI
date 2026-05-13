"""
Multi-Agent System with LangGraph

A beginner-friendly mini project demonstrating multi-agent orchestration.
"""

__version__ = "0.1.0"

from .state import SharedState
from .graph import app

__all__ = ["SharedState", "app"]