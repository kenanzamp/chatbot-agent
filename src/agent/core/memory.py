"""
Conversation memory management.
"""

from dataclasses import dataclass, field
from typing import List, Optional
from ..llm.base import LLMMessage, ToolCall
import json


@dataclass
class ConversationMemory:
    """
    Manages conversation history with context window awareness.
    """
    
    max_messages: int = 100  # Maximum messages to retain
    messages: List[LLMMessage] = field(default_factory=list)
    
    def add_user_message(self, content: str):
        """Add a user message to history."""
        self.messages.append(LLMMessage(role="user", content=content))
        self._trim_if_needed()
    
    def add_assistant_message(
        self,
        content: str,
        tool_calls: Optional[List[ToolCall]] = None
    ):
        """Add an assistant message to history."""
        tc_dicts = None
        if tool_calls:
            tc_dicts = [
                {"id": tc.id, "name": tc.name, "input": tc.input}
                for tc in tool_calls
            ]
        
        self.messages.append(LLMMessage(
            role="assistant",
            content=content,
            tool_calls=tc_dicts
        ))
        self._trim_if_needed()
    
    def add_tool_result(self, tool_call_id: str, result: str):
        """Add a tool result to history."""
        self.messages.append(LLMMessage(
            role="tool_result",
            content=result,
            tool_call_id=tool_call_id
        ))
        self._trim_if_needed()
    
    def get_messages(self) -> List[LLMMessage]:
        """Get all messages for LLM context."""
        return self.messages.copy()
    
    def _trim_if_needed(self):
        """Trim old messages if exceeding limit."""
        if len(self.messages) > self.max_messages:
            # Keep the most recent messages
            excess = len(self.messages) - self.max_messages
            self.messages = self.messages[excess:]
    
    def clear(self):
        """Clear all history."""
        self.messages = []
    
    def get_last_user_message(self) -> Optional[str]:
        """Get the most recent user message."""
        for msg in reversed(self.messages):
            if msg.role == "user":
                return msg.content
        return None
    
    def to_dict(self) -> List[dict]:
        """Serialize for persistence."""
        return [m.to_dict() for m in self.messages]
    
    @classmethod
    def from_dict(cls, data: List[dict]) -> "ConversationMemory":
        """Deserialize from persistence."""
        memory = cls()
        for item in data:
            memory.messages.append(LLMMessage(**item))
        return memory
