"""
LLM Tracing - saves all LLM inputs and outputs for debugging.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class LLMTracer:
    """Traces LLM calls to files for debugging and analysis."""
    
    def __init__(self, trace_dir: str = "llm_traces"):
        self.trace_dir = Path(trace_dir)
        self.trace_dir.mkdir(parents=True, exist_ok=True)
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.call_count = 0
        
        # Create session directory
        self.session_dir = self.trace_dir / self.session_id
        self.session_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"LLM Tracer initialized. Traces will be saved to: {self.session_dir}")
    
    def _serialize(self, obj: Any) -> Any:
        """Serialize objects for JSON."""
        if hasattr(obj, '__dict__'):
            return {k: self._serialize(v) for k, v in obj.__dict__.items() if not k.startswith('_')}
        elif isinstance(obj, (list, tuple)):
            return [self._serialize(item) for item in obj]
        elif isinstance(obj, dict):
            return {k: self._serialize(v) for k, v in obj.items()}
        elif hasattr(obj, 'value'):  # Enum
            return obj.value
        else:
            try:
                json.dumps(obj)
                return obj
            except (TypeError, ValueError):
                return str(obj)
    
    def trace_request(
        self,
        messages: List[Dict],
        system_prompt: Optional[str],
        tools: Optional[List[Dict]],
        model: str,
        **kwargs
    ) -> str:
        """
        Trace an LLM request.
        
        Returns:
            trace_id: Unique ID for this trace
        """
        self.call_count += 1
        trace_id = f"{self.call_count:04d}_{datetime.now().strftime('%H%M%S_%f')}"
        
        trace_data = {
            "trace_id": trace_id,
            "timestamp": datetime.now().isoformat(),
            "model": model,
            "system_prompt": system_prompt,
            "messages": self._serialize(messages),
            "tools": tools,
            "kwargs": self._serialize(kwargs),
            "response": None,
            "error": None,
            "duration_ms": None
        }
        
        # Save request immediately
        trace_file = self.session_dir / f"{trace_id}_request.json"
        with open(trace_file, 'w') as f:
            json.dump(trace_data, f, indent=2, default=str)
        
        logger.debug(f"Traced LLM request: {trace_id}")
        return trace_id
    
    def trace_response(
        self,
        trace_id: str,
        response: Any,
        duration_ms: float,
        error: Optional[str] = None
    ):
        """Trace an LLM response."""
        trace_data = {
            "trace_id": trace_id,
            "timestamp": datetime.now().isoformat(),
            "response": self._serialize(response) if response else None,
            "error": error,
            "duration_ms": duration_ms
        }
        
        # Save response
        trace_file = self.session_dir / f"{trace_id}_response.json"
        with open(trace_file, 'w') as f:
            json.dump(trace_data, f, indent=2, default=str)
        
        logger.debug(f"Traced LLM response: {trace_id} ({duration_ms:.0f}ms)")
    
    def trace_stream_chunk(self, trace_id: str, chunk: Any):
        """Trace a streaming chunk (appends to file)."""
        chunk_file = self.session_dir / f"{trace_id}_stream.jsonl"
        with open(chunk_file, 'a') as f:
            chunk_data = {
                "timestamp": datetime.now().isoformat(),
                "chunk": self._serialize(chunk)
            }
            f.write(json.dumps(chunk_data, default=str) + "\n")
    
    def trace_tool_call(
        self,
        trace_id: str,
        tool_name: str,
        tool_input: Dict,
        tool_output: Any,
        success: bool,
        duration_ms: float
    ):
        """Trace a tool call."""
        tool_data = {
            "trace_id": trace_id,
            "timestamp": datetime.now().isoformat(),
            "tool_name": tool_name,
            "input": tool_input,
            "output": str(tool_output)[:1000],  # Truncate large outputs
            "success": success,
            "duration_ms": duration_ms
        }
        
        # Append to tools file
        tools_file = self.session_dir / f"{trace_id}_tools.jsonl"
        with open(tools_file, 'a') as f:
            f.write(json.dumps(tool_data, default=str) + "\n")
        
        logger.debug(f"Traced tool call: {tool_name} ({duration_ms:.0f}ms)")


# Global tracer instance
tracer = LLMTracer()
