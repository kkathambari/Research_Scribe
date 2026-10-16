"""
ResearchScribe LLM Provider Package.
"""

from app.services.llm.base import (
    BaseLLMProvider,
    ConfigurationError,
    GenerationTimeoutError,
    InvalidStructuredOutputError,
    LLMError,
    LLMResponse,
    ModelNotFoundError,
    ProviderHealthStatus,
    ProviderUnavailableError,
)
from app.services.llm.gemini_provider import GeminiProvider
from app.services.llm.heuristic_provider import HeuristicProvider
from app.services.llm.manager import LLMManager, llm_manager
from app.services.llm.ollama_provider import OllamaProvider

__all__ = [
    "BaseLLMProvider",
    "OllamaProvider",
    "GeminiProvider",
    "HeuristicProvider",
    "LLMManager",
    "llm_manager",
    "LLMResponse",
    "ProviderHealthStatus",
    "LLMError",
    "ConfigurationError",
    "ProviderUnavailableError",
    "ModelNotFoundError",
    "GenerationTimeoutError",
    "InvalidStructuredOutputError",
]
