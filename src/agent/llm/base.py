from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, AsyncIterator, Any, Dict
from enum import Enum


class StopReason(Enum):
    END_TURN = "end_turn"
    TOOL_USE = "tool_use"
    MAX_TOKENS = "max_tokens"
    ERROR = "error"


@dataclass
class LLMMessage:
    """Unified message format across providers."""
    role: str  # "system" | "user" | "assistant" | "tool_result"
    content: str
    tool_call_id: Optional[str] = None
    tool_calls: Optional[List[Dict]] = None
    
    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "content": self.content,
            "tool_call_id": self.tool_call_id,
            "tool_calls": self.tool_calls
        }


@dataclass
class ToolCall:
    """Represents a tool call from the LLM."""
    id: str
    name: str
    input: Dict[str, Any]


@dataclass
class LLMResponse:
    """Complete response from LLM."""
    content: str
    tool_calls: List[ToolCall] = field(default_factory=list)
    stop_reason: StopReason = StopReason.END_TURN
    usage: Dict[str, int] = field(default_factory=dict)
    
    @property
    def has_tool_calls(self) -> bool:
        return len(self.tool_calls) > 0


@dataclass
class StreamChunk:
    """Streaming chunk from LLM."""
    type: str  # "text_delta" | "tool_use_start" | "tool_use_delta" | "tool_use_complete" | "done" | "error"
    content: str = ""
    tool_call: Optional[ToolCall] = None
    error: Optional[str] = None


class BaseLLM(ABC):
    """Abstract interface for LLM providers. Implement this to add new models."""
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return provider identifier (e.g., 'anthropic', 'openai')."""
        pass
    
    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the model identifier."""
        pass
    
    @abstractmethod
    async def complete(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[Dict]] = None,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate a completion (non-streaming)."""
        pass
    
    @abstractmethod
    async def stream(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[Dict]] = None,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> AsyncIterator[StreamChunk]:
        """Generate a streaming completion."""
        pass
    
    def format_tool_schema(self, tool: Dict) -> Dict:
        """
        Convert generic tool schema to provider-specific format.
        Override in subclasses if needed.
        """
        return tool
