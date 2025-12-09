from anthropic import AsyncAnthropic
from .base import BaseLLM, LLMMessage, LLMResponse, StreamChunk, ToolCall, StopReason
from .tracer import tracer
from typing import List, Optional, AsyncIterator, Dict, Any
import json
import logging
import time

logger = logging.getLogger(__name__)


class AnthropicLLM(BaseLLM):
    """Claude adapter with streaming and prompt caching support."""
    
    def __init__(
        self,
        model: str = "claude-sonnet-4-5-20250929",
        api_key: Optional[str] = None,
        enable_cache: bool = True,
        max_tokens: int = 4096,
        temperature: float = 0.7
    ):
        self._model = model
        self._client = AsyncAnthropic(api_key=api_key)
        self._enable_cache = enable_cache
        self._max_tokens = max_tokens
        self._temperature = temperature
    
    @property
    def provider_name(self) -> str:
        return "anthropic"
    
    @property
    def model_name(self) -> str:
        return self._model
    
    def _convert_messages(self, messages: List[LLMMessage]) -> List[Dict]:
        """Convert unified messages to Anthropic format."""
        converted = []
        
        for msg in messages:
            if msg.role == "system":
                # System messages handled separately in Anthropic
                continue
            
            if msg.role == "tool_result":
                converted.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": msg.tool_call_id,
                        "content": msg.content
                    }]
                })
            elif msg.tool_calls:
                # Assistant message with tool calls
                content = []
                if msg.content:
                    content.append({"type": "text", "text": msg.content})
                for tc in msg.tool_calls:
                    content.append({
                        "type": "tool_use",
                        "id": tc["id"],
                        "name": tc["name"],
                        "input": tc["input"]
                    })
                converted.append({"role": "assistant", "content": content})
            else:
                converted.append({
                    "role": msg.role,
                    "content": msg.content
                })
        
        return converted
    
    def _convert_tools(self, tools: List[Dict]) -> List[Dict]:
        """Convert generic tool schemas to Anthropic format."""
        return [
            {
                "name": t["name"],
                "description": t["description"],
                "input_schema": t["parameters"]
            }
            for t in tools
        ]
    
    def _build_system_prompt(self, system_prompt: str) -> Any:
        """Build system prompt with optional caching."""
        if self._enable_cache:
            return [{
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"}
            }]
        return system_prompt
    
    def _parse_stop_reason(self, reason: str) -> StopReason:
        """Convert Anthropic stop reason to unified format."""
        mapping = {
            "end_turn": StopReason.END_TURN,
            "tool_use": StopReason.TOOL_USE,
            "max_tokens": StopReason.MAX_TOKENS,
        }
        return mapping.get(reason, StopReason.END_TURN)
    
    async def complete(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[Dict]] = None,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate completion with optional tool use."""
        request = {
            "model": self._model,
            "max_tokens": kwargs.get("max_tokens", self._max_tokens),
            "temperature": kwargs.get("temperature", self._temperature),
            "messages": self._convert_messages(messages),
        }
        
        if system_prompt:
            request["system"] = self._build_system_prompt(system_prompt)
        
        if tools:
            request["tools"] = self._convert_tools(tools)
        
        try:
            response = await self._client.messages.create(**request)
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            raise
        
        # Parse response
        content = ""
        tool_calls = []
        
        for block in response.content:
            if block.type == "text":
                content += block.text
            elif block.type == "tool_use":
                tool_calls.append(ToolCall(
                    id=block.id,
                    name=block.name,
                    input=block.input
                ))
        
        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            stop_reason=self._parse_stop_reason(response.stop_reason),
            usage={
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
                "cache_read_tokens": getattr(response.usage, 'cache_read_input_tokens', 0),
                "cache_creation_tokens": getattr(response.usage, 'cache_creation_input_tokens', 0),
            }
        )
    
    async def stream(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[Dict]] = None,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> AsyncIterator[StreamChunk]:
        """Stream completion with real-time token delivery."""
        request = {
            "model": self._model,
            "max_tokens": kwargs.get("max_tokens", self._max_tokens),
            "temperature": kwargs.get("temperature", self._temperature),
            "messages": self._convert_messages(messages),
        }
        
        if system_prompt:
            request["system"] = self._build_system_prompt(system_prompt)
        
        if tools:
            request["tools"] = self._convert_tools(tools)
        
        try:
            async with self._client.messages.stream(**request) as stream:
                current_tool: Optional[Dict] = None
                tool_input_json = ""
                
                async for event in stream:
                    if event.type == "content_block_start":
                        block = event.content_block
                        if hasattr(block, 'type'):
                            if block.type == "tool_use":
                                current_tool = {
                                    "id": block.id,
                                    "name": block.name,
                                }
                                tool_input_json = ""
                                yield StreamChunk(
                                    type="tool_use_start",
                                    tool_call=ToolCall(
                                        id=block.id,
                                        name=block.name,
                                        input={}
                                    )
                                )
                    
                    elif event.type == "content_block_delta":
                        delta = event.delta
                        if hasattr(delta, 'text'):
                            yield StreamChunk(type="text_delta", content=delta.text)
                        elif hasattr(delta, 'partial_json'):
                            tool_input_json += delta.partial_json
                    
                    elif event.type == "content_block_stop":
                        if current_tool:
                            # Parse complete tool input
                            try:
                                parsed_input = json.loads(tool_input_json) if tool_input_json else {}
                            except json.JSONDecodeError:
                                parsed_input = {"raw": tool_input_json}
                            
                            yield StreamChunk(
                                type="tool_use_complete",
                                tool_call=ToolCall(
                                    id=current_tool["id"],
                                    name=current_tool["name"],
                                    input=parsed_input
                                )
                            )
                            current_tool = None
                            tool_input_json = ""
                    
                    elif event.type == "message_stop":
                        yield StreamChunk(type="done")
        
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield StreamChunk(type="error", error=str(e))
