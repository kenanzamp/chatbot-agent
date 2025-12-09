from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional, List
from pathlib import Path
import yaml
import os


class ServerConfig(BaseSettings):
    host: str = "0.0.0.0"
    port: int = 8000
    heartbeat_interval: int = 30
    connection_timeout: int = 300


class LLMCacheConfig(BaseSettings):
    enabled: bool = True
    cache_system_prompt: bool = True


class LLMConfig(BaseSettings):
    provider: str = "anthropic"
    model: str = "claude-sonnet-4-5-20250929"
    max_tokens: int = 4096
    temperature: float = 0.7
    cache: LLMCacheConfig = LLMCacheConfig()
    
    # API keys from environment
    anthropic_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    
    model_config = {"extra": "ignore"}


class CircuitBreakerConfig(BaseSettings):
    failure_threshold: int = 5
    recovery_timeout: int = 60


class AgentConfig(BaseSettings):
    max_iterations: int = 15
    max_tool_retries: int = 3
    tool_timeout: float = 30.0
    circuit_breaker: CircuitBreakerConfig = CircuitBreakerConfig()


class SkillsConfig(BaseSettings):
    base_path: str = "./skills"
    auto_discover: bool = True
    allowed_commands: List[str] = ["python3", "python", "node", "bash"]
    command_timeout: int = 60
    sandbox: bool = False


class ToolsConfig(BaseSettings):
    builtin_enabled: bool = True
    external_path: Optional[str] = None


class Settings(BaseSettings):
    server: ServerConfig = ServerConfig()
    llm: LLMConfig = LLMConfig()
    agent: AgentConfig = AgentConfig()
    skills: SkillsConfig = SkillsConfig()
    tools: ToolsConfig = ToolsConfig()
    
    @classmethod
    def from_yaml(cls, path: str = "config/config.yaml") -> "Settings":
        """Load settings from YAML file, with environment variable overrides."""
        config_data = {}
        if Path(path).exists():
            with open(path) as f:
                config_data = yaml.safe_load(f) or {}
        
        # Handle nested config properly
        instance = cls()
        
        if "server" in config_data:
            instance.server = ServerConfig(**config_data["server"])
        
        if "llm" in config_data:
            llm_data = config_data["llm"].copy()
            if "cache" in llm_data:
                llm_data["cache"] = LLMCacheConfig(**llm_data["cache"])
            instance.llm = LLMConfig(**llm_data)
        
        # Set API keys from environment (after creating instance)
        instance.llm.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        instance.llm.openai_api_key = os.getenv("OPENAI_API_KEY")
        
        if "agent" in config_data:
            agent_data = config_data["agent"]
            if "circuit_breaker" in agent_data:
                agent_data["circuit_breaker"] = CircuitBreakerConfig(**agent_data["circuit_breaker"])
            instance.agent = AgentConfig(**agent_data)
        
        if "skills" in config_data:
            instance.skills = SkillsConfig(**config_data["skills"])
        
        if "tools" in config_data:
            instance.tools = ToolsConfig(**config_data["tools"])
        
        return instance
    
    model_config = {
        "env_file": ".env",
        "env_nested_delimiter": "__"
    }


# Global settings instance
settings = Settings.from_yaml()
