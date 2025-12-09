import asyncio
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from .registry import ToolRegistry, RegisteredTool
from ..resilience.circuit_breaker import CircuitBreaker, CircuitBreakerOpen
import logging
import traceback
import time

logger = logging.getLogger(__name__)


@dataclass
class ToolResult:
    """Result of a tool execution."""
    tool_call_id: str
    tool_name: str
    success: bool
    result: Any
    error: Optional[str] = None
    execution_time_ms: float = 0
    
    def to_message_content(self) -> str:
        """Format result for LLM consumption."""
        if self.success:
            return str(self.result) if self.result is not None else "Success (no output)"
        else:
            return f"Error: {self.error}"


class ToolExecutor:
    """
    Executes tools with:
    - Timeout protection
    - Circuit breaker for fault tolerance
    - Parallel execution support
    - Detailed error handling
    """
    
    def __init__(
        self,
        registry: ToolRegistry,
        default_timeout: float = 30.0,
        circuit_breaker_threshold: int = 5,
        circuit_breaker_timeout: int = 60
    ):
        self.registry = registry
        self.default_timeout = default_timeout
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._cb_threshold = circuit_breaker_threshold
        self._cb_timeout = circuit_breaker_timeout
    
    def _get_circuit_breaker(self, tool_name: str) -> CircuitBreaker:
        """Get or create circuit breaker for a tool."""
        if tool_name not in self._circuit_breakers:
            self._circuit_breakers[tool_name] = CircuitBreaker(
                failure_threshold=self._cb_threshold,
                recovery_timeout=self._cb_timeout,
                name=f"tool:{tool_name}"
            )
        return self._circuit_breakers[tool_name]
    
    async def execute(
        self,
        tool_call_id: str,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> ToolResult:
        """Execute a single tool call with all protections."""
        start_time = time.time()
        
        # Get tool from registry
        tool = self.registry.get(tool_name)
        if not tool:
            return ToolResult(
                tool_call_id=tool_call_id,
                tool_name=tool_name,
                success=False,
                result=None,
                error=f"Unknown tool: '{tool_name}'. Available tools: {', '.join(self.registry.list_names())}"
            )
        
        if not tool.enabled:
            return ToolResult(
                tool_call_id=tool_call_id,
                tool_name=tool_name,
                success=False,
                result=None,
                error=f"Tool '{tool_name}' is currently disabled"
            )
        
        # Check circuit breaker
        cb = self._get_circuit_breaker(tool_name)
        try:
            cb.check()
        except CircuitBreakerOpen:
            return ToolResult(
                tool_call_id=tool_call_id,
                tool_name=tool_name,
                success=False,
                result=None,
                error=f"Tool '{tool_name}' is temporarily unavailable due to repeated failures. It will be retried automatically."
            )
        
        # Execute with timeout
        try:
            timeout = tool.timeout or self.default_timeout
            
            if tool.is_async:
                result = await asyncio.wait_for(
                    tool.func(**arguments),
                    timeout=timeout
                )
            else:
                # Run sync function in thread pool
                loop = asyncio.get_event_loop()
                result = await asyncio.wait_for(
                    loop.run_in_executor(
                        None,
                        lambda: tool.func(**arguments)
                    ),
                    timeout=timeout
                )
            
            cb.record_success()
            execution_time = (time.time() - start_time) * 1000
            
            return ToolResult(
                tool_call_id=tool_call_id,
                tool_name=tool_name,
                success=True,
                result=result,
                execution_time_ms=execution_time
            )
        
        except asyncio.TimeoutError:
            cb.record_failure()
            execution_time = (time.time() - start_time) * 1000
            logger.warning(f"Tool '{tool_name}' timed out after {timeout}s")
            
            return ToolResult(
                tool_call_id=tool_call_id,
                tool_name=tool_name,
                success=False,
                result=None,
                error=f"Tool '{tool_name}' timed out after {timeout} seconds",
                execution_time_ms=execution_time
            )
        
        except Exception as e:
            cb.record_failure()
            execution_time = (time.time() - start_time) * 1000
            logger.exception(f"Tool '{tool_name}' failed with error: {e}")
            
            return ToolResult(
                tool_call_id=tool_call_id,
                tool_name=tool_name,
                success=False,
                result=None,
                error=f"Tool execution error: {str(e)}",
                execution_time_ms=execution_time
            )
    
    async def execute_parallel(
        self,
        tool_calls: List[Dict[str, Any]]
    ) -> List[ToolResult]:
        """
        Execute multiple tool calls in parallel.
        
        Args:
            tool_calls: List of dicts with 'id', 'name', 'input' keys
        """
        tasks = [
            self.execute(
                tool_call_id=tc["id"],
                tool_name=tc["name"],
                arguments=tc.get("input", {})
            )
            for tc in tool_calls
        ]
        return await asyncio.gather(*tasks)
    
    def get_circuit_breaker_status(self) -> Dict[str, str]:
        """Get status of all circuit breakers."""
        return {
            name: cb.state.value
            for name, cb in self._circuit_breakers.items()
        }
