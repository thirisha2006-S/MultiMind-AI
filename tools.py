"""
Tools for the Multi-Agent System.
Includes Tavily Search, Python REPL, and MCP tools.
"""

import os
from typing import Optional, List, Dict, Any
from langchain_community.tools import TavilySearchResults
from langchain_core.tools import tool

# Import MCP integration if available
try:
    from mcp_integration import mcp_manager
    MCP_INTEGRATION_AVAILABLE = True
except ImportError:
    MCP_INTEGRATION_AVAILABLE = False
    mcp_manager = None


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


# MCP Tools
def get_mcp_tools() -> List[Dict[str, Any]]:
    """Get all available MCP tools."""
    if not MCP_INTEGRATION_AVAILABLE or not mcp_manager:
        return []
    return mcp_manager.get_available_tools()


def get_mcp_tool(server_name: str, tool_name: str) -> Optional[Dict[str, Any]]:
    """Get a specific MCP tool."""
    if not MCP_INTEGRATION_AVAILABLE or not mcp_manager:
        return None
    tool = mcp_manager.get_tool(server_name, tool_name)
    if tool:
        return {
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.input_schema,
            "server": server_name
        }
    return None


async def call_mcp_tool(server_name: str, tool_name: str, arguments: Dict[str, Any]) -> Any:
    """Call an MCP tool."""
    if not MCP_INTEGRATION_AVAILABLE or not mcp_manager:
        raise Exception("MCP integration not available")
    return await mcp_manager.call_tool(server_name, tool_name, arguments)


# MCP tool wrapper for LangChain
@tool
def mcp_tool_invoker(server_name: str, tool_name: str, arguments: str) -> str:
    """
    Invoke an MCP tool.
    
    Args:
        server_name: Name of the MCP server
        tool_name: Name of the tool to invoke
        arguments: JSON string of arguments to pass to the tool
        
    Returns:
        Result from the tool invocation
    """
    if not MCP_INTEGRATION_AVAILABLE or not mcp_manager:
        return "Error: MCP integration not available"
    
    try:
        # Parse arguments from JSON string
        import json
        args_dict = json.loads(arguments) if arguments else {}
        
        # Call the tool (need to handle async)
        import asyncio
        try:
            # Try to get existing event loop
            loop = asyncio.get_event_loop()
        except RuntimeError:
            # Create new event loop if none exists
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Run the async function
        result = loop.run_until_complete(
            call_mcp_tool(server_name, tool_name, args_dict)
        )
        
        return str(result)
    except Exception as e:
        return f"Error invoking MCP tool: {str(e)}"