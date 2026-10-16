"""
Deterministic Local Heuristic / Mock LLM Provider.
Enables offline development and deterministic testing without external API dependencies.
"""

import json
import time
from typing import List, Optional

from app.services.llm.base import (
    BaseLLMProvider,
    LLMResponse,
    ProviderHealthStatus,
)


class HeuristicProvider(BaseLLMProvider):
    """
    Deterministic rule-based provider for testing, mock environments, or offline fallbacks.
    """

    def __init__(self, model: str = "deterministic-heuristic", timeout: float = 5.0):
        super().__init__(name="heuristic", model=model, timeout=timeout)

    async def list_models(self) -> List[str]:
        return ["deterministic-heuristic", "academic-mock-v1"]

    async def check_health(self) -> ProviderHealthStatus:
        return ProviderHealthStatus(
            provider=self.name,
            available=True,
            configured_model=self.model,
            model_installed=True,
            latency_ms=0.5,
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
        start_time = time.perf_counter()

        if json_mode:
            text = json.dumps({
                "status": "success",
                "summary": "Heuristic structured synthesis of available research evidence.",
                "claims": [
                    {"claim": "Grounded synthesis maintains citation provenance.", "status": "supported"}
                ]
            })
        else:
            text = (
                "Academic literature underscores the critical role of verifiable evidence provenance in research writing. "
                "Prior investigations demonstrate that systematically grounding narrative assertions in documented empirical findings "
                "significantly enhances scholarly rigor and minimizes factual hallucinations."
            )

        latency_ms = (time.perf_counter() - start_time) * 1000.0
        return LLMResponse(
            text=text,
            provider=self.name,
            model=self.model,
            latency_ms=round(latency_ms, 2),
            prompt_tokens=len(prompt.split()),
            completion_tokens=len(text.split()),
            raw_metadata={"mode": "heuristic"}
        )
