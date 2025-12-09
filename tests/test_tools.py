"""Tests for the tool system."""

import pytest
from agent.tools.registry import ToolRegistry
from agent.tools.schema import function_to_schema


def test_tool_registration():
    """Test that tools can be registered."""
    registry = ToolRegistry()
    
    @registry.tool(name="test_tool", description="A test tool")
    def my_tool(x: int, y: str = "default") -> str:
        return f"{x}-{y}"
    
    assert "test_tool" in registry.list_names()
    tool = registry.get("test_tool")
    assert tool is not None
    assert tool.description == "A test tool"


def test_schema_generation():
    """Test that schemas are generated correctly from functions."""
    def calculate(a: int, b: int, operation: str = "add") -> int:
        """
        Perform calculation.
        
        Args:
            a: First number
            b: Second number
            operation: The operation to perform
        """
        pass
    
    schema = function_to_schema(calculate)
    assert schema.name == "calculate"
    assert "a" in schema.parameters["required"]
    assert "b" in schema.parameters["required"]
    assert "operation" not in schema.parameters["required"]


def test_tool_listing():
    """Test that all registered tools are listed."""
    registry = ToolRegistry()
    
    @registry.tool(name="tool1")
    def tool1(): pass
    
    @registry.tool(name="tool2")
    def tool2(): pass
    
    names = registry.list_names()
    assert "tool1" in names
    assert "tool2" in names


def test_tool_disable():
    """Test that tools can be disabled."""
    registry = ToolRegistry()
    
    @registry.tool(name="disable_test")
    def disable_test(): pass
    
    assert "disable_test" in registry.list_names()
    
    registry.disable("disable_test")
    assert "disable_test" not in registry.list_names()
    
    registry.enable("disable_test")
    assert "disable_test" in registry.list_names()
