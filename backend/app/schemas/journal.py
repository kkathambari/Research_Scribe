from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class JournalRequirementResponse(BaseModel):
    id: str
    requirement_type: str
    description: str
    expected_value: Optional[str] = None
    source_type: str = "template"
    confidence: float = 1.0
    verification_status: str = "confirmed"
    user_approval_status: str = "approved"

    class Config:
        from_attributes = True

class JournalProfileCreate(BaseModel):
    journal_name: str
    publisher: Optional[str] = None
    official_guidelines_url: Optional[str] = None
    manuscript_type: Optional[str] = "Full Research Paper"
    citation_style: Optional[str] = "IEEE"
    required_sections: Optional[List[str]] = None
    word_limit: Optional[int] = 6000
    page_limit: Optional[int] = 10
    declaration_requirements: Optional[List[str]] = None

class JournalProfileResponse(BaseModel):
    id: str
    journal_name: str
    publisher: Optional[str] = None
    official_guidelines_url: Optional[str] = None
    manuscript_type: str
    citation_style: str
    required_sections: Optional[str] = None
    section_order: Optional[str] = None
    abstract_requirements: Optional[str] = None
    keyword_requirements: Optional[str] = None
    word_limit: Optional[int] = None
    page_limit: Optional[int] = None
    declaration_requirements: Optional[str] = None
    layout_requirements: Optional[str] = None
    verification_status: str = "approved"
    profile_version: int = 1
    requirements: List[JournalRequirementResponse] = []

    class Config:
        from_attributes = True

class ComplianceCheckResponse(BaseModel):
    id: str
    check_type: str
    status: str  # passed, failed, warning, not_verifiable
    observed_value: Optional[str] = None
    expected_value: Optional[str] = None
    explanation: Optional[str] = None
    suggested_correction: Optional[str] = None
    checked_at: datetime

    class Config:
        from_attributes = True

class ComplianceReportResponse(BaseModel):
    manuscript_id: str
    journal_name: str
    overall_status: str  # compliant, non_compliant, warnings_detected
    passed_count: int
    failed_count: int
    warning_count: int
    not_verifiable_count: int
    compliance_score: float  # 0.0 - 100.0%
    checks: List[ComplianceCheckResponse] = []
