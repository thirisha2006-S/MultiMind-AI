#!/usr/bin/env python3
"""
Test script to verify MCP integration works correctly.
"""

import asyncio
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp_integration import mcp_manager, MCPTool

def test_mcp_import():
    """Test that MCP integration can be imported."""
    try:
        from mcp_integration import mcp_manager
        print("PASS: MCP integration imported successfully")
        return True
    except Exception as e:
        print(f"FAIL: Failed to import MCP integration: {e}")
        return False

def test_mcp_manager_creation():
    """Test that MCP manager is created correctly."""
    try:
        assert mcp_manager is not None
        assert hasattr(mcp_manager, 'sessions')
        assert hasattr(mcp_manager, 'tools')
        assert hasattr(mcp_manager, 'server_params')
        print("PASS: MCP manager created successfully")
        return True
    except Exception as e:
        print(f"FAIL: MCP manager creation failed: {e}")
        return False

def test_mcp_tool_dataclass():
    """Test that MCPTool dataclass works correctly."""
    try:
        tool = MCPTool(
            name="test_tool",
            description="A test tool",
            input_schema={"type": "object", "properties": {}}
        )
        assert tool.name == "test_tool"
        assert tool.description == "A test tool"
        assert tool.input_schema == {"type": "object", "properties": {}}
        print("PASS: MCPTool dataclass works correctly")
        return True
    except Exception as e:
        print(f"FAIL: MCPTool dataclass failed: {e}")
        return False

def test_get_mcp_tools_empty():
    """Test getting MCP tools when none are connected."""
    try:
        tools = mcp_manager.get_available_tools()
        assert isinstance(tools, list)
        print("PASS: get_available_tools returns empty list when no servers connected")
        return True
    except Exception as e:
        print(f"FAIL: get_available_tools failed: {e}")
        return False

def test_get_mcp_tool_none():
    """Test getting a specific MCP tool when none are connected."""
    try:
        tool = mcp_manager.get_tool("nonexistent", "tool")
        assert tool is None
        print("PASS: get_tool returns None for nonexistent tool")
        return True
    except Exception as e:
        print(f"FAIL: get_tool failed: {e}")
        return False

async def test_connect_nonexistent_server():
    """Test connecting to a nonexistent server."""
    try:
        result = await mcp_manager.connect_server("nonexistent")
        assert result == False
        print("PASS: connect_server correctly returns False for nonexistent server")
        return True
    except Exception as e:
        print(f"FAIL: connect_server failed unexpectedly: {e}")
        return False

def run_tests():
    """Run all tests."""
    print("Running MCP Integration Tests...")
    print("=" * 50)
    
    tests = [
        test_mcp_import,
        test_mcp_manager_creation,
        test_mcp_tool_dataclass,
        test_get_mcp_tools_empty,
        test_get_mcp_tool_none,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    # Run async test
    try:
        result = asyncio.run(test_connect_nonexistent_server())
        if result:
            passed += 1
        total += 1
    except Exception as e:
        print(f"FAIL: Async test failed: {e}")
        total += 1
    
    print("=" * 50)
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("PASS: All tests passed!")
        return True
    else:
        print("FAIL: Some tests failed!")
        return False

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)