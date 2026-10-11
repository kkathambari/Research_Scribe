import uuid
import shutil
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from sqlalchemy.orm import Session
from app.config import settings
from app.db.session import get_db
from app.models.source import Source, Document
from app.models.evidence import Evidence
from app.schemas.source import (
    SourceCreate, SourceUpdate, SourceResponse,
    ScholarlySearchQuery, ScholarlySearchResponse, DocumentResponse
)
from app.services.retrieval import retrieval_service, generate_citation_key
from app.services.document_parser import document_parser
from app.services.evidence_extractor import evidence_extractor

router = APIRouter(prefix="/sources", tags=["Sources"])

@router.post("/search", response_model=ScholarlySearchResponse)
async def search_literature(payload: ScholarlySearchQuery):
    """Searches scholarly indexes (OpenAlex & Crossref) for research papers."""
    return await retrieval_service.search(
        query=payload.query,
        limit=payload.limit or 10,
        year_start=payload.year_start,
        year_end=payload.year_end
    )

@router.get("", response_model=List[SourceResponse])
def list_sources(project_id: str = Query(...), db: Session = Depends(get_db)):
    sources = db.query(Source).filter(Source.project_id == project_id).order_by(Source.created_at.desc()).all()
    results = []
    for s in sources:
        resp = SourceResponse.from_orm(s)
        resp.evidences_count = db.query(Evidence).filter(Evidence.source_id == s.id).count()
        if s.document:
            resp.document = DocumentResponse.from_orm(s.document)
        results.append(resp)
    return results

@router.post("", response_model=SourceResponse)
def add_source(payload: SourceCreate, db: Session = Depends(get_db)):
    source_id = str(uuid.uuid4())
    cit_key = payload.citation_key or generate_citation_key(payload.authors, payload.year, payload.title)

    source = Source(
        id=source_id,
        project_id=payload.project_id,
        title=payload.title,
        authors=payload.authors,
        year=payload.year,
        venue=payload.venue,
        doi=payload.doi,
        url=payload.url,
        abstract=payload.abstract,
        access_status=payload.access_status or "open",
        verified_metadata=payload.verified_metadata if payload.verified_metadata is not None else True,
        citation_key=cit_key
    )
    db.add(source)

    # If abstract is present, automatically extract initial evidence items
    if payload.abstract and len(payload.abstract.strip()) > 30:
        extracted_items = evidence_extractor.extract_evidence_from_pages(
            pages=[{"page_number": 1, "text": payload.abstract}],
            source_abstract=payload.abstract
        )
        for item in extracted_items:
            ev = Evidence(
                id=str(uuid.uuid4()),
                source_id=source_id,
                project_id=payload.project_id,
                passage_text=item["passage_text"],
                page_number=item.get("page_number", 1),
                section_name=item.get("section_name", "Abstract"),
                category=item.get("category", "finding"),
                confidence=item.get("confidence", 0.85)
            )
            db.add(ev)

    db.commit()
    db.refresh(source)

    resp = SourceResponse.from_orm(source)
    resp.evidences_count = db.query(Evidence).filter(Evidence.source_id == source.id).count()
    return resp

@router.post("/{source_id}/upload-pdf", response_model=SourceResponse)
async def upload_pdf(
    source_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF documents are supported")

    # Save PDF to disk
    doc_id = str(uuid.uuid4())
    save_filename = f"{doc_id}_{file.filename}"
    save_path = settings.UPLOAD_DIR / save_filename

    with open(save_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    file_size = save_path.stat().st_size

    # Parse PDF with DocumentParserService
    try:
        parsed = document_parser.parse_pdf(save_path)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Failed to process PDF: {str(e)}")

    # Check for existing document, update or create
    doc = db.query(Document).filter(Document.source_id == source_id).first()
    if not doc:
        doc = Document(
            id=doc_id,
            source_id=source_id,
            project_id=source.project_id,
            filename=file.filename,
            file_path=str(save_path),
            file_size=file_size,
            extracted_text=parsed.get("extracted_text", ""),
            page_count=parsed.get("page_count", 0),
            extraction_status="processed",
            ocr_required=parsed.get("ocr_required", False)
        )
        db.add(doc)
    else:
        doc.filename = file.filename
        doc.file_path = str(save_path)
        doc.file_size = file_size
        doc.extracted_text = parsed.get("extracted_text", "")
        doc.page_count = parsed.get("page_count", 0)
        doc.extraction_status = "processed"
        doc.ocr_required = parsed.get("ocr_required", False)

    # Extract structured evidence items from parsed pages
    extracted_items = evidence_extractor.extract_evidence_from_pages(
        pages=parsed.get("pages", []),
        source_abstract=source.abstract
    )

    # Delete older evidences for this source to re-populate with full-text extractions
    db.query(Evidence).filter(Evidence.source_id == source_id).delete()

    for item in extracted_items:
        ev = Evidence(
            id=str(uuid.uuid4()),
            document_id=doc.id,
            source_id=source_id,
            project_id=source.project_id,
            passage_text=item["passage_text"],
            page_number=item.get("page_number", 1),
            section_name=item.get("section_name", "Main Text"),
            category=item.get("category", "finding"),
            confidence=item.get("confidence", 0.9)
        )
        db.add(ev)

    db.commit()
    db.refresh(source)

    resp = SourceResponse.from_orm(source)
    resp.document = DocumentResponse.from_orm(doc)
    resp.evidences_count = db.query(Evidence).filter(Evidence.source_id == source.id).count()
    return resp

@router.delete("/{source_id}")
def delete_source(source_id: str, db: Session = Depends(get_db)):
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    db.delete(source)
    db.commit()
    return {"status": "success", "message": "Source removed successfully"}
