from fastapi import APIRouter
from app.schemas.writing import PolishRequest, PolishResponse
from app.services.academic_rewriter import academic_rewriter

router = APIRouter(prefix="/writing", tags=["Academic Writing"])

@router.post("/polish", response_model=PolishResponse)
def polish_prose(payload: PolishRequest):
    """Refines academic prose for clarity, tone, or conciseness while preserving in-text citations."""
    return academic_rewriter.polish(
        text=payload.text,
        mode=payload.mode,
        preserve_citations=payload.preserve_citations
    )
