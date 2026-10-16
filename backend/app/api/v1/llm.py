"""
LLM Diagnostics, Monitoring, and Model Management Endpoints.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import settings
from app.services.llm import (
    GenerationTimeoutError,
    LLMError,
    ModelNotFoundError,
    ProviderUnavailableError,
    llm_manager,
)

router = APIRouter(prefix="/llm", tags=["Local & Cloud LLM Providers"])


class LLMTestRequest(BaseModel):
    prompt: Optional[str] = "Confirm ResearchScribe LLM integration in one sentence."
    temperature: Optional[float] = 0.2
    max_tokens: Optional[int] = 100


class LLMTestResponse(BaseModel):
    status: str
    provider: str
    model: str
    response: str
    latency_ms: float
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None


@router.get("/status")
async def get_llm_status() -> Dict[str, Any]:
    """
    Returns diagnostics on the currently configured LLM provider and local service reachability.
    """
    health = await llm_manager.check_health()
    diag = llm_manager.get_diagnostic_info()

    return {
        **diag,
        "available": health.available,
        "model_installed": health.model_installed,
        "latency_ms": health.latency_ms,
        "available_models": health.available_models,
        "error_message": health.error_message,
        "instructions": health.instructions
    }


@router.get("/models")
async def list_models() -> Dict[str, Any]:
    """
    Lists models currently downloaded and available on the active provider.
    """
    try:
        models = await llm_manager.list_available_models()
        return {
            "provider": settings.LLM_PROVIDER,
            "models": models,
            "count": len(models)
        }
    except LLMError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.post("/test", response_model=LLMTestResponse)
async def test_llm_generation(payload: LLMTestRequest):
    """
    AC-02: Generates a test response using the configured local model.
    """
    try:
        resp = await llm_manager.generate(
            prompt=payload.prompt or "Confirm ResearchScribe LLM integration in one sentence.",
            temperature=payload.temperature or 0.2,
            max_tokens=payload.max_tokens or 100
        )
        return LLMTestResponse(
            status="success",
            provider=resp.provider,
            model=resp.model,
            response=resp.text,
            latency_ms=resp.latency_ms,
            prompt_tokens=resp.prompt_tokens,
            completion_tokens=resp.completion_tokens
        )
    except ModelNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ProviderUnavailableError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except GenerationTimeoutError as e:
        raise HTTPException(status_code=504, detail=str(e))
    except LLMError as e:
        raise HTTPException(status_code=500, detail=str(e))
