"""
Main ReAct (Reasoning + Acting) agent implementation.
"""

from typing import AsyncIterator, List, Optional, Dict, Any
from dataclasses import dataclass, field
from ..llm.base import BaseLLM, LLMMessage, LLMResponse, StreamChunk, ToolCall, StopReason
from ..tools.registry import ToolRegistry
from ..tools.executor import ToolExecutor, ToolResult
from ..skills.index import SkillIndex
from .memory import ConversationMemory
import logging
import time

logger = logging.getLogger(__name__)


@dataclass
class AgentEvent:
    """Event emitted during agent processing."""
    type: str
    data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResponse:
    """Complete response from the agent."""
    content: str
    tool_calls_made: List[Dict]
    iterations: int
    total_time_ms: float


class ReactAgent:
    """
    ReAct agent that combines reasoning and acting.
    
    Supports:
    - Direct tool calls (JSON Schema tools)
    - Skill-based execution (read SKILL.md → execute commands)
    - Streaming responses
    - Fault tolerance and recovery
    """
    
    def __init__(
        self,
        llm: BaseLLM,
        tool_registry: ToolRegistry,
        skill_index: SkillIndex,
        system_prompt: str,
        max_iterations: int = 15
    ):
        self.llm = llm
        self.tool_registry = tool_registry
        self.skill_index = skill_index
        self.executor = ToolExecutor(tool_registry)
        self.system_prompt = system_prompt
        self.max_iterations = max_iterations
        self.memory = ConversationMemory()
    
    def _build_system_prompt(self) -> str:
        """Build complete system prompt with skill information."""
        skill_info = ""
        skills = self.skill_index.list_skills()
        
        if skills:
            skill_list = "\n".join([
                f"- **{s.name}**: {s.description}"
                for s in skills
            ])
            skill_info = f"""

## Available Skills

The following skills are available. Use `read_skill` to get documentation before using a skill:

{skill_list}

**Important**: Always call `read_skill("skill_name")` to read the SKILL.md documentation BEFORE attempting to use any skill. The documentation contains the exact command formats and examples you need.
"""
        
        return self.system_prompt + skill_info
    
    async def process(self, user_message: str) -> AgentResponse:
        """
        Process a user message through the ReAct loop.
        Non-streaming version.
        """
        start_time = time.time()
        self.memory.add_user_message(user_message)
        
        tool_calls_made = []
        final_content = ""
        iterations = 0
        
        system_prompt = self._build_system_prompt()
        tool_schemas = self.tool_registry.list_schemas()
        
        for iteration in range(self.max_iterations):
            iterations = iteration + 1
            logger.debug(f"ReAct iteration {iterations}")
            
            try:
                response = await self.llm.complete(
                    messages=self.memory.get_messages(),
                    tools=tool_schemas,
                    system_prompt=system_prompt
                )
            except Exception as e:
                logger.error(f"LLM error on iteration {iterations}: {e}")
                final_content = f"I encountered an error while processing your request: {str(e)}"
                break
            
            # No tool calls = final response
            if not response.has_tool_calls:
                final_content = response.content
                self.memory.add_assistant_message(response.content)
                break
            
            # Record assistant message with tool calls
            self.memory.add_assistant_message(
                content=response.content,
                tool_calls=response.tool_calls
            )
            
            # Execute all tool calls in parallel
            tool_call_dicts = [
                {"id": tc.id, "name": tc.name, "input": tc.input}
                for tc in response.tool_calls
            ]
            
            results = await self.executor.execute_parallel(tool_call_dicts)
            
            # Process results
            for result in results:
                tool_calls_made.append({
                    "name": result.tool_name,
                    "success": result.success,
                    "time_ms": result.execution_time_ms
                })
                
                self.memory.add_tool_result(
                    tool_call_id=result.tool_call_id,
                    result=result.to_message_content()
                )
        else:
            # Reached max iterations
            final_content = "I've reached my maximum number of steps for this task. Here's what I was able to accomplish so far."
            logger.warning(f"Max iterations ({self.max_iterations}) reached")
        
        total_time = (time.time() - start_time) * 1000
        
        return AgentResponse(
            content=final_content,
            tool_calls_made=tool_calls_made,
            iterations=iterations,
            total_time_ms=total_time
        )
    
    async def process_stream(
        self,
        user_message: str
    ) -> AsyncIterator[AgentEvent]:
        """
        Process with streaming response.
        Yields events for real-time UI updates.
        """
        start_time = time.time()
        self.memory.add_user_message(user_message)
        
        system_prompt = self._build_system_prompt()
        tool_schemas = self.tool_registry.list_schemas()
        
        yield AgentEvent(type="processing_start", data={"message": user_message})
        
        for iteration in range(self.max_iterations):
            yield AgentEvent(type="iteration_start", data={"iteration": iteration + 1})
            
            # Collect response through streaming
            full_content = ""
            tool_calls: List[ToolCall] = []
            
            try:
                async for chunk in self.llm.stream(
                    messages=self.memory.get_messages(),
                    tools=tool_schemas,
                    system_prompt=system_prompt
                ):
                    if chunk.type == "text_delta":
                        full_content += chunk.content
                        yield AgentEvent(
                            type="text_delta",
                            data={"content": chunk.content}
                        )
                    
                    elif chunk.type == "tool_use_start":
                        yield AgentEvent(
                            type="tool_start",
                            data={"tool_name": chunk.tool_call.name}
                        )
                    
                    elif chunk.type == "tool_use_complete":
                        tool_calls.append(chunk.tool_call)
                        yield AgentEvent(
                            type="tool_call_complete",
                            data={
                                "tool_name": chunk.tool_call.name,
                                "tool_id": chunk.tool_call.id
                            }
                        )
                    
                    elif chunk.type == "error":
                        yield AgentEvent(
                            type="error",
                            data={"error": chunk.error}
                        )
                        return
                    
                    elif chunk.type == "done":
                        pass
            
            except Exception as e:
                logger.exception(f"Streaming error: {e}")
                yield AgentEvent(type="error", data={"error": str(e)})
                return
            
            # No tool calls = final response
            if not tool_calls:
                self.memory.add_assistant_message(full_content)
                total_time = (time.time() - start_time) * 1000
                yield AgentEvent(
                    type="complete",
                    data={
                        "content": full_content,
                        "iterations": iteration + 1,
                        "total_time_ms": total_time
                    }
                )
                return
            
            # Record and execute tools
            self.memory.add_assistant_message(full_content, tool_calls=tool_calls)
            
            yield AgentEvent(
                type="executing_tools",
                data={"count": len(tool_calls)}
            )
            
            # Execute tools in parallel
            tool_call_dicts = [
                {"id": tc.id, "name": tc.name, "input": tc.input}
                for tc in tool_calls
            ]
            
            results = await self.executor.execute_parallel(tool_call_dicts)
            
            for result in results:
                self.memory.add_tool_result(
                    tool_call_id=result.tool_call_id,
                    result=result.to_message_content()
                )
                
                yield AgentEvent(
                    type="tool_result",
                    data={
                        "tool_name": result.tool_name,
                        "success": result.success,
                        "time_ms": result.execution_time_ms
                    }
                )
        
        # Max iterations reached
        total_time = (time.time() - start_time) * 1000
        yield AgentEvent(
            type="max_iterations",
            data={
                "iterations": self.max_iterations,
                "total_time_ms": total_time
            }
        )
    
    def reset(self):
        """Reset conversation state."""
        self.memory.clear()
    
    def update_llm(self, llm: BaseLLM):
        """Hot-swap the LLM (for model switching)."""
        self.llm = llm
        logger.info(f"Switched to LLM: {llm.provider_name}/{llm.model_name}")
