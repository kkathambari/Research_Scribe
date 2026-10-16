"""
Abstract Base Classes, Data Models, and Exceptions for ResearchScribe LLM Providers.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


class LLMError(Exception):
    """Base exception for all LLM provider errors."""
    pass


class ConfigurationError(LLMError):
    """Raised when an LLM provider is misconfigured (e.g., missing API key or bad base URL)."""
    pass


class ProviderUnavailableError(LLMError):
    """Raised when the LLM service endpoint cannot be reached."""
    pass


class ModelNotFoundError(LLMError):
    """Raised when the requested model is not installed or available on the provider."""
    pass


class GenerationTimeoutError(LLMError):
    """Raised when a generation request exceeds the configured timeout."""
    pass


class InvalidStructuredOutputError(LLMError):
    """Raised when structured JSON output is requested but the response cannot be parsed or validated."""
    pass


@dataclass
class LLMResponse:
    """Standardized response from an LLM provider."""
    text: str
    provider: str
    model: str
    latency_ms: float
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    raw_metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProviderHealthStatus:
    """Health and availability report for an LLM provider."""
    provider: str
    available: bool
    configured_model: str
    model_installed: bool
    latency_ms: Optional[float] = None
    available_models: List[str] = field(default_factory=list)
    error_message: Optional[str] = None
    instructions: Optional[str] = None


class BaseLLMProvider(ABC):
    """Abstract Base Class for all LLM providers in ResearchScribe."""

    def __init__(self, name: str, model: str, timeout: float = 60.0):
        self.name = name
        self.model = model
        self.timeout = timeout

    @abstractmethod
    async def check_health(self) -> ProviderHealthStatus:
        """Checks provider reachability and verifies whether the configured model is available."""
        pass

    @abstractmethod
    async def list_models(self) -> List[str]:
        """Lists available models on this provider."""
        pass

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: Optional[int] = 2048,
        json_mode: bool = False,
        timeout: Optional[float] = None
    ) -> LLMResponse:
        """Executes a text generation request with standardized parameters."""
        pass
