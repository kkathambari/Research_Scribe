"""
LLM Provider Manager and Orchestrator for ResearchScribe.
Coordinates active provider selection, health diagnostics, structured JSON generation,
and strictly controlled fallback mechanisms.
"""

import json
import logging
from typing import Any, Dict, List, Optional

from app.config import settings
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
from app.services.llm.ollama_provider import OllamaProvider

logger = logging.getLogger(__name__)


class LLMManager:
    """
    Central orchestration engine for ResearchScribe's language models.
    Supports local Ollama inference, optional Gemini cloud inference, and deterministic heuristics.
    """

    def __init__(self):
        self._provider_instances: Dict[str, BaseLLMProvider] = {}

    def get_provider(self, provider_name: Optional[str] = None) -> BaseLLMProvider:
        """Instantiates or retrieves the configured LLM provider."""
        target = (provider_name or settings.LLM_PROVIDER or "ollama").strip().lower()

        if target in self._provider_instances:
            return self._provider_instances[target]

        provider: BaseLLMProvider
        if target == "ollama":
            provider = OllamaProvider(
                base_url=settings.OLLAMA_BASE_URL,
                model=settings.OLLAMA_MODEL,
                timeout=settings.OLLAMA_TIMEOUT,
                keep_alive=getattr(settings, "OLLAMA_KEEP_ALIVE", "5m")
            )
        elif target == "gemini":
            provider = GeminiProvider(
                api_key=settings.GEMINI_API_KEY,
                model=settings.GEMINI_MODEL,
                timeout=getattr(settings, "GEMINI_TIMEOUT", 45.0)
            )
        elif target in ["heuristic", "mock", "heuristic_and_gemini"]:
            # If heuristic_and_gemini and Gemini API key is configured, use Gemini else heuristic
            if target == "heuristic_and_gemini" and settings.GEMINI_API_KEY and len(settings.GEMINI_API_KEY.strip()) > 10:
                provider = GeminiProvider(
                    api_key=settings.GEMINI_API_KEY,
                    model=settings.GEMINI_MODEL,
                    timeout=getattr(settings, "GEMINI_TIMEOUT", 45.0)
                )
            else:
                provider = HeuristicProvider()
        else:
            raise ConfigurationError(
                f"Unknown LLM provider '{target}'. Supported options: 'ollama', 'gemini', 'heuristic'."
            )

        self._provider_instances[target] = provider
        return provider

    def get_fallback_provider(self) -> Optional[BaseLLMProvider]:
        """Returns the fallback provider if explicitly configured, otherwise None."""
        fb_name = getattr(settings, "LLM_FALLBACK_PROVIDER", "none").strip().lower()
        if fb_name in ["", "none", "null", "false", "no"]:
            return None
        return self.get_provider(fb_name)

    async def check_health(self) -> ProviderHealthStatus:
        """Audits the health of the currently active provider."""
        provider = self.get_provider()
        return await provider.check_health()

    async def list_available_models(self) -> List[str]:
        """Lists models available on the active provider."""
        provider = self.get_provider()
        return await provider.list_models()

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: Optional[int] = 2048,
        json_mode: bool = False,
        timeout: Optional[float] = None
    ) -> LLMResponse:
        """
        Executes text generation using the configured active provider.
        Enforces strict fallback rules: no silent fallback to Gemini unless explicitly authorized.
        """
        primary = self.get_provider()
        retries = max(0, getattr(settings, "LLM_MAX_RETRIES", 2))

        attempt = 0
        last_exception: Optional[Exception] = None

        while attempt <= retries:
            try:
                return await primary.generate(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    json_mode=json_mode,
                    timeout=timeout
                )
            except (ModelNotFoundError, ConfigurationError) as fatal_err:
                # Configuration / missing model errors are non-retryable on the same provider
                last_exception = fatal_err
                break
            except (ProviderUnavailableError, GenerationTimeoutError, LLMError) as retryable_err:
                last_exception = retryable_err
                attempt += 1
                if attempt <= retries:
                    logger.warning(
                        f"[{primary.name}] Generation attempt {attempt} failed ({type(retryable_err).__name__}). Retrying..."
                    )

        # Primary provider failed after all retries
        fallback = self.get_fallback_provider()
        if fallback and fallback.name != primary.name:
            logger.warning(
                f"[LLMManager] Primary provider '{primary.name}' failed ({type(last_exception).__name__}: {last_exception}). "
                f"Invoking explicitly configured fallback provider: '{fallback.name}'"
            )
            try:
                return await fallback.generate(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    json_mode=json_mode,
                    timeout=timeout
                )
            except Exception as fb_err:
                logger.error(f"[LLMManager] Fallback provider '{fallback.name}' also failed: {fb_err}")
                raise LLMError(
                    f"Both primary provider '{primary.name}' ({last_exception}) "
                    f"and fallback provider '{fallback.name}' ({fb_err}) failed."
                ) from fb_err

        # No fallback configured or fallback failed: re-raise primary exception
        if last_exception:
            raise last_exception
        raise LLMError("Generation request could not be completed.")

    async def generate_structured(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: Optional[int] = 2048,
        retries: int = 2
    ) -> Dict[str, Any]:
        """
        Requests structured JSON output from LLM, validating parsing across configured retry limits.
        """
        json_sys_prompt = (system_prompt or "") + "\nRespond with valid JSON only. Do not include markdown codeblocks or conversational text."

        last_error = None
        for attempt in range(retries + 1):
            try:
                resp = await self.generate(
                    prompt=prompt,
                    system_prompt=json_sys_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    json_mode=True
                )
                clean_text = resp.text.strip()
                if clean_text.startswith("```json"):
                    clean_text = clean_text[7:]
                if clean_text.startswith("```"):
                    clean_text = clean_text[3:]
                if clean_text.endswith("```"):
                    clean_text = clean_text[:-3]
                clean_text = clean_text.strip()

                return json.loads(clean_text)
            except (json.JSONDecodeError, InvalidStructuredOutputError) as err:
                last_error = err
                logger.warning(f"[LLMManager] Structured JSON attempt {attempt+1} failed: {err}")

        raise InvalidStructuredOutputError(f"Failed to obtain valid JSON output after {retries+1} attempts: {last_error}")

    def get_diagnostic_info(self) -> Dict[str, Any]:
        """Provides status summary for monitoring and API endpoints."""
        primary_name = (settings.LLM_PROVIDER or "ollama").strip().lower()
        fb_name = getattr(settings, "LLM_FALLBACK_PROVIDER", "none").strip().lower()

        return {
            "active_provider": primary_name,
            "configured_model": settings.OLLAMA_MODEL if primary_name == "ollama" else settings.GEMINI_MODEL,
            "ollama_base_url": settings.OLLAMA_BASE_URL,
            "fallback_provider": fb_name if fb_name not in ["", "none", "null"] else None,
            "gemini_configured": bool(settings.GEMINI_API_KEY and len(settings.GEMINI_API_KEY.strip()) > 10)
        }


llm_manager = LLMManager()
