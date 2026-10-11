from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

class EvidenceBase(BaseModel):
    passage_text: str
    page_number: Optional[int] = None
    section_name: Optional[str] = None
    category: Optional[str] = "finding" # objective, method, finding, limitation, future_work
    confidence: Optional[float] = 1.0

class EvidenceCreate(EvidenceBase):
    project_id: str
    source_id: str
    document_id: Optional[str] = None

class EvidenceUpdate(BaseModel):
    passage_text: Optional[str] = None
    category: Optional[str] = None
    section_name: Optional[str] = None
    confidence: Optional[float] = None

class EvidenceResponse(EvidenceBase):
    id: str
    source_id: str
    document_id: Optional[str] = None
    project_id: str
    created_at: datetime
    source_title: Optional[str] = None
    source_authors: Optional[str] = None
    source_year: Optional[int] = None
    citation_key: Optional[str] = None

    class Config:
        from_attributes = True
