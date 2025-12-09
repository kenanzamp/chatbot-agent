"""
Custom error types for the agent system.
"""


class AgentError(Exception):
    """Base exception for agent errors."""
    pass


class ToolExecutionError(AgentError):
    """Raised when a tool fails to execute."""
    pass


class SkillExecutionError(AgentError):
    """Raised when a skill command fails."""
    pass


class LLMError(AgentError):
    """Raised when an LLM operation fails."""
    pass


class ConfigurationError(AgentError):
    """Raised when there's a configuration problem."""
    pass
