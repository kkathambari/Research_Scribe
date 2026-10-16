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
    verified_metadata: Optional[bool] = False
    metadata_verification_status: Optional[str] = "verified" # verified, unverified, mismatch_flagged
    metadata_source: Optional[str] = "crossref_openalex"
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
    verified_metadata: Optional[bool] = None
    metadata_verification_status: Optional[str] = None

class DocumentResponse(BaseModel):
    id: str
    source_id: Optional[str] = None
    filename: str
    file_size: int
    page_count: int
    extraction_status: str
    ocr_required: bool
    created_at: datetime
    warnings: Optional[List[str]] = []

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
    verified_metadata: Optional[bool] = True

class ScholarlySearchResponse(BaseModel):
    query: str
    total: int
    results: List[ScholarlySearchResultItem]
    retrieval_status: str = "success"

class BatchUploadResultItem(BaseModel):
    filename: str
    status: str # processed, duplicate_detected, ocr_required, failed
    source_id: Optional[str] = None
    title: Optional[str] = None
    citation_key: Optional[str] = None
    page_count: Optional[int] = 0
    ocr_required: Optional[bool] = False
    evidence_count: Optional[int] = 0
    metadata_status: Optional[str] = "unverified"
    warning: Optional[str] = None
    error: Optional[str] = None

class BatchUploadResponse(BaseModel):
    total_files: int
    total_processed: Optional[int] = None
    processed_count: int
    successful_count: Optional[int] = None
    duplicates_count: int
    duplicate_count: Optional[int] = None
    ocr_required_count: int
    failed_count: int
    results: List[BatchUploadResultItem]
