"""
Ollama Local LLM Provider Implementation.
Communicates with local or containerized Ollama daemon via official REST endpoints.
"""

import json
import logging
import time
from typing import Any, Dict, List, Optional
import httpx

from app.services.llm.base import (
    BaseLLMProvider,
    GenerationTimeoutError,
    InvalidStructuredOutputError,
    LLMError,
    LLMResponse,
    ModelNotFoundError,
    ProviderHealthStatus,
    ProviderUnavailableError,
)

logger = logging.getLogger(__name__)


class OllamaProvider(BaseLLMProvider):
    """
    Integrates ResearchScribe with local Ollama instances (e.g., http://localhost:11434).
    Adheres strictly to local execution without leaking prompts to external clouds.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "deepseek-coder:latest",
        timeout: float = 60.0,
        keep_alive: str = "5m"
    ):
        super().__init__(name="ollama", model=model, timeout=timeout)
        self.base_url = base_url.rstrip("/")
        self.keep_alive = keep_alive

    def _normalize_model_name(self, name: str) -> str:
        """Strips tags or normalizes for loose matching (e.g. 'mistral' matches 'mistral:latest')."""
        return name.strip().lower()

    async def list_models(self) -> List[str]:
        """Queries /api/tags for installed models."""
        url = f"{self.base_url}/api/tags"
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    models = [m.get("name", "") for m in data.get("models", []) if m.get("name")]
                    return models
                raise ProviderUnavailableError(f"Ollama returned HTTP {resp.status_code} while listing models.")
        except httpx.ConnectError as exc:
            raise ProviderUnavailableError(
                f"Could not connect to Ollama at {self.base_url}. Ensure the service is running ('ollama serve')."
            ) from exc
        except httpx.TimeoutException as exc:
            raise GenerationTimeoutError(f"Connection to Ollama at {self.base_url} timed out.") from exc
        except Exception as exc:
            if isinstance(exc, LLMError):
                raise
            raise LLMError(f"Failed to query Ollama models: {str(exc)}") from exc

    async def check_health(self) -> ProviderHealthStatus:
        """Verifies Ollama availability and confirms whether the configured model is installed."""
        start = time.perf_counter()
        try:
            installed_models = await self.list_models()
            latency = (time.perf_counter() - start) * 1000.0

            # Match model name exactly or with/without :latest
            cfg_norm = self._normalize_model_name(self.model)
            installed_norm = [self._normalize_model_name(m) for m in installed_models]
            
            model_installed = False
            if cfg_norm in installed_norm:
                model_installed = True
            elif f"{cfg_norm}:latest" in installed_norm:
                model_installed = True
            elif ":" in cfg_norm and cfg_norm.split(":")[0] in [m.split(":")[0] for m in installed_norm]:
                model_installed = True

            instructions = None
            error_msg = None
            if not model_installed:
                error_msg = f"Model '{self.model}' is not installed in Ollama."
                instructions = f"To install this model, run: 'ollama pull {self.model}' on the host machine."

            return ProviderHealthStatus(
                provider=self.name,
                available=True,
                configured_model=self.model,
                model_installed=model_installed,
                latency_ms=round(latency, 2),
                available_models=installed_models,
                error_message=error_msg,
                instructions=instructions
            )
        except ProviderUnavailableError as e:
            return ProviderHealthStatus(
                provider=self.name,
                available=False,
                configured_model=self.model,
                model_installed=False,
                error_message=str(e),
                instructions=f"Start Ollama locally ('ollama serve') or check OLLAMA_BASE_URL={self.base_url}."
            )
        except Exception as e:
            return ProviderHealthStatus(
                provider=self.name,
                available=False,
                configured_model=self.model,
                model_installed=False,
                error_message=f"Ollama health check error: {str(e)}",
                instructions=f"Verify Ollama service configuration at {self.base_url}."
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
        """
        Submits prompt to Ollama /api/generate endpoint.
        Does not automatically download missing models.
        """
        request_timeout = timeout or self.timeout
        url = f"{self.base_url}/api/generate"

        payload: Dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "keep_alive": self.keep_alive,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens or 2048
            }
        }
        if system_prompt:
            payload["system"] = system_prompt
        if json_mode:
            payload["format"] = "json"

        logger.info(
            f"[Ollama] Requesting generation: model={self.model}, "
            f"prompt_len={len(prompt)} chars, json_mode={json_mode}, timeout={request_timeout}s"
        )
        start_time = time.perf_counter()

        try:
            async with httpx.AsyncClient(timeout=request_timeout) as client:
                resp = await client.post(url, json=payload)
                latency_ms = (time.perf_counter() - start_time) * 1000.0

                if resp.status_code == 404:
                    err_body = resp.text
                    raise ModelNotFoundError(
                        f"Model '{self.model}' was not found by Ollama server at {self.base_url}. "
                        f"Run 'ollama pull {self.model}' to download it first. Server response: {err_body}"
                    )
                elif resp.status_code != 200:
                    err_msg = resp.text
                    if "out of memory" in err_msg.lower() or "cuda" in err_msg.lower():
                        raise LLMError(f"Ollama host ran out of memory while loading model '{self.model}': {err_msg}")
                    raise LLMError(f"Ollama server returned error status {resp.status_code}: {err_msg}")

                data = resp.json()
                response_text = data.get("response", "").strip()

                # If JSON mode requested, validate output can be parsed
                if json_mode and response_text:
                    try:
                        json.loads(response_text)
                    except json.JSONDecodeError as jde:
                        logger.warning(f"[Ollama] Structured JSON validation failed: {jde}")
                        raise InvalidStructuredOutputError(
                            f"Ollama returned malformed JSON output: {jde}. Raw snippet: {response_text[:120]}"
                        ) from jde

                prompt_tokens = data.get("prompt_eval_count")
                completion_tokens = data.get("eval_count")

                logger.info(
                    f"[Ollama] Generation complete in {latency_ms:.1f}ms. "
                    f"Prompt tokens: {prompt_tokens}, Eval tokens: {completion_tokens}"
                )

                return LLMResponse(
                    text=response_text,
                    provider=self.name,
                    model=self.model,
                    latency_ms=round(latency_ms, 2),
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    raw_metadata={
                        "total_duration": data.get("total_duration"),
                        "load_duration": data.get("load_duration"),
                        "done": data.get("done")
                    }
                )

        except httpx.ConnectError as exc:
            raise ProviderUnavailableError(
                f"Could not connect to Ollama at {self.base_url}. Ensure the service is active ('ollama serve')."
            ) from exc
        except httpx.TimeoutException as exc:
            raise GenerationTimeoutError(
                f"Ollama generation timed out after {request_timeout:.1f} seconds. "
                f"Consider selecting a smaller model or increasing OLLAMA_TIMEOUT."
            ) from exc
        except (ModelNotFoundError, GenerationTimeoutError, ProviderUnavailableError, InvalidStructuredOutputError):
            raise
        except Exception as exc:
            raise LLMError(f"Unexpected error during Ollama generation: {str(exc)}") from exc
