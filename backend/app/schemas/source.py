from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

class SourceBase(BaseModel):
    title: str
    authors: Optional[str] = Field(None, description="Comma-separated or list of author names")
    year: Optional[int] = None
    venue: Optional[str] = None
    doi: Optional[str] = None
    url: Optional[str] = None
    abstract: Optional[str] = None
    access_status: Optional[str] = "open" # open, restricted, abstract_only
    verified_metadata: Optional[bool] = True
    citation_key: Optional[str] = None # e.g. Vaswani2017

class SourceCreate(SourceBase):
    project_id: str

class SourceUpdate(BaseModel):
    title: Optional[str] = None
    authors: Optional[str] = None
    year: Optional[int] = None
    venue: Optional[str] = None
    doi: Optional[str] = None
    url: Optional[str] = None
    abstract: Optional[str] = None
    citation_key: Optional[str] = None

class DocumentResponse(BaseModel):
    id: str
    source_id: Optional[str] = None
    filename: str
    file_size: int
    page_count: int
    extraction_status: str
    ocr_required: bool
    created_at: datetime

    class Config:
        from_attributes = True

class SourceResponse(SourceBase):
    id: str
    project_id: str
    retrieval_date: datetime
    created_at: datetime
    document: Optional[DocumentResponse] = None
    evidences_count: Optional[int] = 0

    class Config:
        from_attributes = True

class ScholarlySearchQuery(BaseModel):
    query: str
    limit: Optional[int] = 10
    year_start: Optional[int] = None
    year_end: Optional[int] = None

class ScholarlySearchResultItem(BaseModel):
    title: str
    authors: Optional[str] = None
    year: Optional[int] = None
    venue: Optional[str] = None
    doi: Optional[str] = None
    url: Optional[str] = None
    abstract: Optional[str] = None
    access_status: Optional[str] = "open"
    citation_count: Optional[int] = 0
    source_provider: str = "openalex" # openalex, crossref, arxiv
    citation_key: Optional[str] = None

class ScholarlySearchResponse(BaseModel):
    query: str
    total: int
    results: List[ScholarlySearchResultItem]
