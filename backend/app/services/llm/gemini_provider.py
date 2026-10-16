"""
Google Gemini LLM Provider Implementation.
Preserves Gemini integration as an optional or fallback provider without forcing its use.
"""

import json
import logging
import time
from typing import Any, Dict, List, Optional
import httpx

from app.services.llm.base import (
    BaseLLMProvider,
    ConfigurationError,
    GenerationTimeoutError,
    InvalidStructuredOutputError,
    LLMError,
    LLMResponse,
    ProviderHealthStatus,
    ProviderUnavailableError,
)

logger = logging.getLogger(__name__)


class GeminiProvider(BaseLLMProvider):
    """
    Optional cloud-based LLM provider using Google Generative Language API.
    Used only when explicitly selected or configured as an authorized fallback.
    """

    def __init__(
        self,
        api_key: str = "",
        model: str = "gemini-1.5-flash",
        timeout: float = 45.0
    ):
        super().__init__(name="gemini", model=model, timeout=timeout)
        self.api_key = api_key.strip() if api_key else ""

    def _is_configured(self) -> bool:
        return len(self.api_key) > 10

    async def list_models(self) -> List[str]:
        return ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-1.0-pro"]

    async def check_health(self) -> ProviderHealthStatus:
        if not self._is_configured():
            return ProviderHealthStatus(
                provider=self.name,
                available=False,
                configured_model=self.model,
                model_installed=False,
                error_message="GEMINI_API_KEY is not configured.",
                instructions="Set GEMINI_API_KEY in .env or switch to LLM_PROVIDER=ollama for local inference."
            )
        return ProviderHealthStatus(
            provider=self.name,
            available=True,
            configured_model=self.model,
            model_installed=True,
            available_models=await self.list_models()
        )

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: Optional[int] = 2048,
        json_mode: bool = False,
        timeout: Optional[float] = None
    ) -> LLMResponse:
        if not self._is_configured():
            raise ConfigurationError(
                "Gemini API key is not configured. Supply GEMINI_API_KEY or configure LLM_PROVIDER=ollama."
            )

        request_timeout = timeout or self.timeout
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"

        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"

        payload: Dict[str, Any] = {
            "contents": [{"parts": [{"text": full_prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens or 2048
            }
        }
        if json_mode:
            payload["generationConfig"]["responseMimeType"] = "application/json"

        start_time = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=request_timeout) as client:
                resp = await client.post(url, json=payload)
                latency_ms = (time.perf_counter() - start_time) * 1000.0

                if resp.status_code == 401 or resp.status_code == 403:
                    raise ConfigurationError(f"Gemini API authentication failed (HTTP {resp.status_code}): {resp.text}")
                elif resp.status_code != 200:
                    raise LLMError(f"Gemini API request failed with HTTP {resp.status_code}: {resp.text}")

                data = resp.json()
                candidates = data.get("candidates", [])
                text_content = ""
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        text_content = parts[0].get("text", "").strip()

                if json_mode and text_content:
                    try:
                        json.loads(text_content)
                    except json.JSONDecodeError as jde:
                        raise InvalidStructuredOutputError(f"Gemini returned invalid JSON: {jde}") from jde

                return LLMResponse(
                    text=text_content,
                    provider=self.name,
                    model=self.model,
                    latency_ms=round(latency_ms, 2),
                    prompt_tokens=data.get("usageMetadata", {}).get("promptTokenCount"),
                    completion_tokens=data.get("usageMetadata", {}).get("candidatesTokenCount"),
                    raw_metadata=data.get("usageMetadata", {})
                )

        except httpx.ConnectError as exc:
            raise ProviderUnavailableError(f"Could not connect to Gemini service: {exc}") from exc
        except httpx.TimeoutException as exc:
            raise GenerationTimeoutError(f"Gemini generation timed out after {request_timeout:.1f}s.") from exc
