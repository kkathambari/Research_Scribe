from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

class CitationResponse(BaseModel):
    id: str
    claim_id: str
    source_id: Optional[str] = None
    evidence_id: Optional[str] = None
    in_text_citation: Optional[str] = None
    match_score: Optional[float] = 1.0
    source_title: Optional[str] = None
    source_authors: Optional[str] = None
    source_year: Optional[int] = None
    citation_key: Optional[str] = None
    evidence_passage: Optional[str] = None
    page_number: Optional[int] = None

    class Config:
        from_attributes = True

class ClaimResponse(BaseModel):
    id: str
    manuscript_id: str
    section_id: str
    claim_text: str
    status: str # supported, partially_supported, contradicted, unverified, citation_missing
    confidence: float = 0.5
    explanation: Optional[str] = None
    reviewer_status: str = "pending" # pending, accepted, modified, rejected
    created_at: datetime
    citations: List[CitationResponse] = []

    class Config:
        from_attributes = True

class ClaimReviewUpdate(BaseModel):
    reviewer_status: str # accepted, modified, rejected
    updated_claim_text: Optional[str] = None

class SectionVerificationRequest(BaseModel):
    section_id: str

class VerificationReportResponse(BaseModel):
    manuscript_id: str
    section_id: Optional[str] = None
    total_claims: int
    supported_count: int
    partially_supported_count: int
    contradicted_count: int
    unverified_count: int
    citation_missing_count: int
    accuracy_score: float # percentage of supported / partially supported
    claims: List[ClaimResponse]
