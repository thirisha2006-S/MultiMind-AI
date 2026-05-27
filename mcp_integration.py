"""
MCP (Model Context Protocol) Integration for MultiMind AI.
Handles connections to MCP servers and tool discovery.
"""
import os
import json
import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

# Try to import MCP, handle gracefully if not available
try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    # Create dummy classes for type hints
    class ClientSession:
        pass
    class StdioServerParameters:
        pass


@dataclass
@dataclass
class MCPTool:
    """Represents an MCP tool."""
    name: str
    description: str
    input_schema: Dict[str, Any]


class MCPManager:
    """Manages MCP connections and tool discovery."""
    
    def __init__(self):
        self.sessions: Dict[str, ClientSession] = {}
        self.tools: Dict[str, List[MCPTool]] = {}  # server_name -> tools
        self.server_params: Dict[str, StdioServerParameters] = {}
        
    def add_server(self, name: str, command: str, args: List[str] = None, env: Dict[str, str] = None):
        """Add an MCP server configuration."""
        if not MCP_AVAILABLE:
            print(f"Warning: MCP not available. Cannot add server {name}")
            return
            
        args = args or []
        env = env or {}
        self.server_params[name] = StdioServerParameters(
            command=command,
            args=args,
            env=env
        )
        
    async def connect_server(self, name: str) -> bool:
        """Connect to an MCP server."""
        if not MCP_AVAILABLE:
            print("MCP not available")
            return False
            
        if name not in self.server_params:
            print(f"Server {name} not configured")
            return False
            
        try:
            server_params = self.server_params[name]
            # Use the stdio client context manager
            from mcp.client.stdio import stdio_client
            
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    # Initialize the session
                    await session.initialize()
                    
                    # Store session
                    self.sessions[name] = session
                    
                    # List tools
                    tools_result = await session.list_tools()
                    tools = []
                    for tool in tools_result.tools:
                        tools.append(MCPTool(
                            name=tool.name,
                            description=tool.description,
                            input_schema=tool.inputSchema
                        ))
                    self.tools[name] = tools
                    
                    print(f"Connected to MCP server {name} with {len(tools)} tools")
                    return True
                    
        except Exception as e:
            print(f"Failed to connect to MCP server {name}: {e}")
            return False
            
    async def connect_all(self):
        """Connect to all configured servers."""
        for name in self.server_params:
            await self.connect_server(name)
            
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get all available tools from all connected servers."""
        all_tools = []
        for server_name, tools in self.tools.items():
            for tool in tools:
                all_tools.append({
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.input_schema,
                    "server": server_name
                })
        return all_tools
        
    def get_tool(self, server_name: str, tool_name: str) -> Optional[MCPTool]:
        """Get a specific tool from a server."""
        if server_name in self.tools:
            for tool in self.tools[server_name]:
                if tool.name == tool_name:
                    return tool
        return None
        
    async def call_tool(self, server_name: str, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Call a tool on an MCP server."""
        if not MCP_AVAILABLE or server_name not in self.sessions:
            raise Exception(f"MCP not available or server {server_name} not connected")
            
        session = self.sessions[server_name]
        try:
            result = await session.call_tool(tool_name, arguments)
            return result
        except Exception as e:
            print(f"Error calling MCP tool {tool_name}: {e}")
            raise
            
    async def cleanup(self):
        """Clean up all connections."""
        for name, session in self.sessions.items():
            try:
                # Close session if it has a close method
                if hasattr(session, 'close'):
                    await session.close()
            except:
                pass
        self.sessions.clear()
        self.tools.clear()


# Global MCP manager instance
mcp_manager = MCPManager()


def setup_default_mcp_servers():
    """Setup default MCP servers for common services."""
    # Example: Filesystem MCP server
    # mcp_manager.add_server(
    #     "filesystem",
    #     "npx",
    #     ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/allowed/dir"]
    # )
    
    # Example: GitHub MCP server (would need GitHub token)
    # mcp_manager.add_server(
    #     "github",
    #     "npx",
    #     ["-y", "@modelcontextprotocol/server-github"],
    #     {"GITHUB_TOKEN": os.getenv("GITHUB_TOKEN")}
    # )
    
    # For now, we'll leave servers unconfigured - user must add them
    pass


# Initialize on import
setup_default_mcp_servers()

# Export availability flag
MCP_INTEGRATION_AVAILABLE = MCP_AVAILABLE