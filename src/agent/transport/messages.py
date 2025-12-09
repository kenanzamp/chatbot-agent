"""
WebSocket message schemas using Pydantic.
"""

from pydantic import BaseModel, Field
from typing import Optional, Literal, Any, Dict
from datetime import datetime


class ClientMessage(BaseModel):
    """Message from client to server."""
    type: Literal["chat", "ping", "reset", "switch_model"]
    content: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ServerMessage(BaseModel):
    """Message from server to client."""
    type: Literal[
        "connected",       # Initial connection confirmation
        "text_delta",      # Streaming text chunk
        "tool_start",      # Tool execution started
        "tool_result",     # Tool execution completed
        "tool_call_complete",  # Tool call parsed
        "iteration_start", # New ReAct iteration
        "processing_start",# Started processing message
        "executing_tools", # About to execute tools
        "complete",        # Response complete
        "error",           # Error occurred
        "pong",            # Heartbeat response
        "ping",            # Heartbeat ping
        "status",          # Status update
        "model_switched",  # Model changed
        "max_iterations"   # Max iterations reached
    ]
    content: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    def to_json_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            "type": self.type,
            "content": self.content,
            "data": self.data,
            "timestamp": self.timestamp.isoformat()
        }
