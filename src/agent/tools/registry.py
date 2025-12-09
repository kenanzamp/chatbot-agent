from typing import Callable, Dict, Optional, List, Any
from dataclasses import dataclass, field
from .schema import ToolSchema, function_to_schema
import asyncio
import logging

logger = logging.getLogger(__name__)


@dataclass
class RegisteredTool:
    """A registered tool with its metadata."""
    name: str
    description: str
    func: Callable
    schema: ToolSchema
    is_async: bool
    timeout: float = 30.0
    tags: List[str] = field(default_factory=list)
    enabled: bool = True


class ToolRegistry:
    """
    Central registry for tools.
    Supports decorator-based and programmatic registration.
    """
    
    def __init__(self):
        self._tools: Dict[str, RegisteredTool] = {}
    
    def tool(
        self,
        name: Optional[str] = None,
        description: Optional[str] = None,
        timeout: float = 30.0,
        tags: Optional[List[str]] = None
    ) -> Callable:
        """
        Decorator for registering a function as a tool.
        
        Example:
            @registry.tool(name="search", description="Search the web")
            async def web_search(query: str) -> str:
                ...
        """
        def decorator(func: Callable) -> Callable:
            tool_name = name or func.__name__
            schema = function_to_schema(func, name_override=tool_name, description_override=description)
            
            # Override description if provided
            if description:
                schema.description = description
            
            registered = RegisteredTool(
                name=tool_name,
                description=schema.description,
                func=func,
                schema=schema,
                is_async=asyncio.iscoroutinefunction(func),
                timeout=timeout,
                tags=tags or []
            )
            
            self._tools[tool_name] = registered
            logger.debug(f"Registered tool: {tool_name}")
            
            return func
        
        return decorator
    
    def register(
        self,
        func: Callable,
        name: Optional[str] = None,
        description: Optional[str] = None,
        timeout: float = 30.0,
        tags: Optional[List[str]] = None
    ):
        """Programmatically register a tool."""
        self.tool(name=name, description=description, timeout=timeout, tags=tags)(func)
    
    def unregister(self, name: str) -> bool:
        """Remove a tool from the registry."""
        if name in self._tools:
            del self._tools[name]
            logger.debug(f"Unregistered tool: {name}")
            return True
        return False
    
    def get(self, name: str) -> Optional[RegisteredTool]:
        """Get a registered tool by name."""
        return self._tools.get(name)
    
    def get_schema(self, name: str) -> Optional[Dict]:
        """Get a tool's schema by name."""
        tool = self._tools.get(name)
        return tool.schema.to_dict() if tool else None
    
    def list_tools(self, tags: Optional[List[str]] = None) -> List[RegisteredTool]:
        """List all registered tools, optionally filtered by tags."""
        tools = list(self._tools.values())
        if tags:
            tools = [t for t in tools if any(tag in t.tags for tag in tags)]
        return [t for t in tools if t.enabled]
    
    def list_schemas(self, tags: Optional[List[str]] = None) -> List[Dict]:
        """Get all tool schemas for LLM consumption."""
        return [t.schema.to_dict() for t in self.list_tools(tags=tags)]
    
    def list_names(self) -> List[str]:
        """Get names of all registered tools."""
        return [t.name for t in self.list_tools()]
    
    def enable(self, name: str):
        """Enable a tool."""
        if tool := self._tools.get(name):
            tool.enabled = True
    
    def disable(self, name: str):
        """Disable a tool without unregistering."""
        if tool := self._tools.get(name):
            tool.enabled = False


# Global registry instance
registry = ToolRegistry()


# Convenience decorator using global registry
def tool(
    name: str = None,
    description: str = None,
    timeout: float = 30.0,
    tags: List[str] = None
):
    """Decorator for registering tools to the global registry."""
    return registry.tool(name=name, description=description, timeout=timeout, tags=tags)
