"""
Tools for the Multi-Agent System.
Includes Tavily Search and Python REPL tools.
"""

import os
from typing import Optional
from langchain_community.tools import TavilySearchResults
from langchain_core.tools import tool


def get_tavily_search_tool(max_results: int = 3, include_images: bool = False) -> TavilySearchResults:
    """
    Create and return a Tavily search tool.
    
    Args:
        max_results: Maximum number of search results to return
        include_images: Whether to include images in results
    
    Returns:
        TavilySearchResults tool instance
    """
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        raise ValueError("TAVILY_API_KEY environment variable is required")
    
    return TavilySearchResults(
        api_key=api_key,
        max_results=max_results,
        include_images=include_images,
        search_depth="advanced"
    )


@tool
def python_repl(code: str) -> str:
    """
    Execute Python code in a REPL environment.
    
    Args:
        code: Python code to execute
    
    Returns:
        Output from the executed code
    """
    import io
    import contextlib
    
    # Create a safe execution environment
    local_vars = {}
    
    try:
        # Capture stdout
        output_buffer = io.StringIO()
        with contextlib.redirect_stdout(output_buffer):
            exec(code, {"__builtins__": __builtins__}, local_vars)
        
        output = output_buffer.getvalue()
        return output if output else "Code executed successfully (no output)"
    
    except Exception as e:
        return f"Error: {str(e)}"


# Module-level tool references (initialized lazily)
_tavily_tool = None
_python_tool = python_repl


def get_tavily_tool():
    """Get or initialize the Tavily search tool."""
    global _tavily_tool
    if _tavily_tool is None:
        _tavily_tool = get_tavily_search_tool()
    return _tavily_tool


# For backward compatibility, expose tool functions
def tavily_tool(query: str):
    """Invoke Tavily search tool."""
    return get_tavily_tool().invoke({"query": query})


def python_tool(code: str):
    """Invoke Python REPL tool."""
    return _python_tool.invoke({"code": code})