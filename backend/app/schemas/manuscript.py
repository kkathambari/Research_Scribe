from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

class ManuscriptSectionBase(BaseModel):
    section_type: str # abstract, introduction, literature_review, methodology, results, discussion, conclusion, references
    title: str
    order: int = 0
    content: str = ""
    instructions: Optional[str] = None
    word_limit: Optional[int] = None
    status: Optional[str] = "draft" # draft, generated, reviewed

class ManuscriptSectionUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    instructions: Optional[str] = None
    word_limit: Optional[int] = None
    status: Optional[str] = None

class ManuscriptSectionResponse(ManuscriptSectionBase):
    id: str
    manuscript_id: str
    updated_at: datetime
    claims_count: Optional[int] = 0
    verified_claims_count: Optional[int] = 0

    class Config:
        from_attributes = True

class ManuscriptBase(BaseModel):
    title: str
    citation_style: Optional[str] = "APA"
    version: Optional[int] = 1

class ManuscriptCreate(ManuscriptBase):
    pass

class ManuscriptResponse(ManuscriptBase):
    id: str
    project_id: str
    created_at: datetime
    updated_at: datetime
    sections: List[ManuscriptSectionResponse] = []

    class Config:
        from_attributes = True

class SectionGenerateRequest(BaseModel):
    section_type: str
    title: Optional[str] = None
    instructions: Optional[str] = None
    word_limit: Optional[int] = 500
    source_ids: Optional[List[str]] = None
    experimental_data: Optional[str] = None # For FR-13 Results & Methodology Fidelity

GenerateSectionRequest = SectionGenerateRequest

class OutlineItem(BaseModel):
    section_type: str
    title: str
    order: int
    instructions: Optional[str] = None
    word_limit: Optional[int] = None

class OutlineGenerateRequest(BaseModel):
    manuscript_id: str
    suggest_standard_sections: bool = True
