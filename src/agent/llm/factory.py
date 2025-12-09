from typing import Dict, Type, Optional
from .base import BaseLLM
from .anthropic import AnthropicLLM
import logging

logger = logging.getLogger(__name__)


class LLMFactory:
    """
    Factory for creating LLM instances.
    Supports runtime model switching via configuration.
    """
    
    _adapters: Dict[str, Type[BaseLLM]] = {
        "anthropic": AnthropicLLM,
    }
    
    @classmethod
    def register_provider(cls, name: str, adapter_class: Type[BaseLLM]):
        """Register a new LLM provider adapter."""
        cls._adapters[name] = adapter_class
        logger.info(f"Registered LLM provider: {name}")
    
    @classmethod
    def get_providers(cls) -> list:
        """List available providers."""
        return list(cls._adapters.keys())
    
    @classmethod
    def create(
        cls,
        provider: str,
        model: str,
        api_key: Optional[str] = None,
        **kwargs
    ) -> BaseLLM:
        """Create an LLM instance."""
        if provider not in cls._adapters:
            available = ", ".join(cls._adapters.keys())
            raise ValueError(f"Unknown provider: {provider}. Available: {available}")
        
        adapter_class = cls._adapters[provider]
        return adapter_class(model=model, api_key=api_key, **kwargs)
    
    @classmethod
    def from_config(cls, config: dict) -> BaseLLM:
        """Create LLM from configuration dictionary."""
        return cls.create(
            provider=config["provider"],
            model=config["model"],
            api_key=config.get("api_key"),
            enable_cache=config.get("cache", {}).get("enabled", True),
            max_tokens=config.get("max_tokens", 4096),
            temperature=config.get("temperature", 0.7),
        )


# Auto-register OpenAI if available
try:
    from .openai import OpenAILLM
    LLMFactory.register_provider("openai", OpenAILLM)
except ImportError:
    pass
