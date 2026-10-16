import uuid
import shutil
import re
from pathlib import Path
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from sqlalchemy.orm import Session
from app.config import settings
from app.db.session import get_db
from app.models.source import Source, Document
from app.models.evidence import Evidence
from app.models.project import Project
from app.schemas.source import (
    SourceCreate, SourceUpdate, SourceResponse,
    ScholarlySearchQuery, ScholarlySearchResponse, DocumentResponse,
    BatchUploadResponse, BatchUploadResultItem
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
    # Check duplicate by DOI or title in project
    if payload.doi:
        clean_doi = payload.doi.strip().lower()
        existing = db.query(Source).filter(Source.project_id == payload.project_id, Source.doi == clean_doi).first()
        if existing:
            resp = SourceResponse.from_orm(existing)
            resp.evidences_count = db.query(Evidence).filter(Evidence.source_id == existing.id).count()
            if existing.document:
                resp.document = DocumentResponse.from_orm(existing.document)
            return resp

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
        verified_metadata=payload.verified_metadata if payload.verified_metadata is not None else False,
        metadata_verification_status=payload.metadata_verification_status or ("verified" if payload.verified_metadata else "unverified"),
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

@router.put("/{source_id}", response_model=SourceResponse)
def update_source(source_id: str, payload: SourceUpdate, db: Session = Depends(get_db)):
    """FR-03.5: Review and correct metadata when automatic matching is uncertain."""
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    data = payload.dict(exclude_unset=True)
    for field, value in data.items():
        setattr(source, field, value)

    db.commit()
    db.refresh(source)

    resp = SourceResponse.from_orm(source)
    resp.evidences_count = db.query(Evidence).filter(Evidence.source_id == source.id).count()
    if source.document:
        resp.document = DocumentResponse.from_orm(source.document)
    return resp

@router.get("/{source_id}/verify-metadata")
async def verify_source_metadata(source_id: str, db: Session = Depends(get_db)):
    """FR-03.2: Compare stored metadata with authoritative DOI records in Crossref/OpenAlex."""
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    if not source.doi:
        return {
            "source_id": source.id,
            "verification_status": "unverified",
            "message": "No DOI associated with this record to verify against external indexes."
        }

    lookup_result = await retrieval_service.lookup_doi(source.doi)
    if not lookup_result:
        return {
            "source_id": source.id,
            "verification_status": source.metadata_verification_status or "unverified",
            "message": "DOI lookup did not return a definitive external record."
        }

    comparison = retrieval_service.compare_metadata(
        extracted={"doi": source.doi, "title": source.title, "year": source.year},
        bibliographic={"doi": lookup_result.doi, "title": lookup_result.title, "year": lookup_result.year}
    )

    source.metadata_verification_status = comparison["status"]
    source.verified_metadata = comparison["is_match"]
    db.commit()

    return {
        "source_id": source.id,
        "verification_status": comparison["status"],
        "is_match": comparison["is_match"],
        "mismatches": comparison["mismatches"],
        "authoritative_record": lookup_result.dict()
    }

@router.post("/upload-batch", response_model=BatchUploadResponse)
async def upload_batch_pdfs(
    project_id: str = Form(...),
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    """
    FR-02: Batch reference PDF upload workflow.
    - Validates file type and size.
    - Cleans up failed files.
    - Detects duplicates.
    - Extracts text, page numbers, and structured evidence.
    - Identifies papers requiring OCR.
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    results: List[BatchUploadResultItem] = []
    processed_count = 0
    duplicates_count = 0
    ocr_required_count = 0
    failed_count = 0

    # Cache existing sources for duplicate detection
    existing_sources = db.query(Source).filter(Source.project_id == project_id).all()

    for file in files:
        if not file.filename.lower().endswith(".pdf"):
            results.append(BatchUploadResultItem(
                filename=file.filename,
                status="failed",
                error="Invalid file type. Only PDF documents are supported."
            ))
            failed_count += 1
            continue

        doc_id = str(uuid.uuid4())
        save_filename = f"{doc_id}_{file.filename}"
        save_path = settings.UPLOAD_DIR / save_filename

        try:
            with open(save_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            file_size = save_path.stat().st_size
            if file_size > 50 * 1024 * 1024:
                if save_path.exists():
                    save_path.unlink()
                results.append(BatchUploadResultItem(
                    filename=file.filename,
                    status="failed",
                    error="File exceeds maximum allowed size of 50MB."
                ))
                failed_count += 1
                continue

            # Parse PDF
            parsed = document_parser.parse_pdf(save_path)
            extracted_meta = parsed.get("metadata", {})
            ocr_required = parsed.get("ocr_required", False)
            if ocr_required:
                ocr_required_count += 1

            # Duplicate detection (FR-02.8)
            matched_source = None
            pdf_doi = extracted_meta.get("doi")
            pdf_title = extracted_meta.get("title")

            for s in existing_sources:
                if pdf_doi and s.doi and pdf_doi.lower().strip() in s.doi.lower().strip():
                    matched_source = s
                    break
                if pdf_title and s.title:
                    norm_s = re.sub(r'[^a-z0-9]', '', s.title.lower())
                    norm_p = re.sub(r'[^a-z0-9]', '', pdf_title.lower())
                    if norm_s and norm_p and len(norm_s) > 8 and norm_s not in ("untitled",) and (norm_s in norm_p or norm_p in norm_s):
                        matched_source = s
                        break

            if matched_source and matched_source.document:
                # Duplicate upload detected
                if save_path.exists():
                    save_path.unlink()
                duplicates_count += 1
                results.append(BatchUploadResultItem(
                    filename=file.filename,
                    status="duplicate_detected",
                    source_id=matched_source.id,
                    title=matched_source.title,
                    citation_key=matched_source.citation_key,
                    page_count=matched_source.document.page_count,
                    warning=f"Duplicate upload detected: Paper '{matched_source.title}' already exists with a processed PDF in this project."
                ))
                continue

            # If matched existing source without document, attach to it
            target_source = matched_source
            if not target_source:
                # Attempt to resolve metadata using DOI
                resolved_title = extracted_meta.get("title") or Path(file.filename).stem
                resolved_authors = extracted_meta.get("authors") or "Unknown Author"
                resolved_year = extracted_meta.get("year")
                resolved_doi = extracted_meta.get("doi")
                cit_key = generate_citation_key(resolved_authors, resolved_year, resolved_title)

                target_source_id = str(uuid.uuid4())
                target_source = Source(
                    id=target_source_id,
                    project_id=project_id,
                    title=resolved_title,
                    authors=resolved_authors,
                    year=resolved_year,
                    doi=resolved_doi,
                    citation_key=cit_key,
                    verified_metadata=False,
                    metadata_verification_status="unverified"
                )
                db.add(target_source)
                existing_sources.append(target_source)

            # Create or update Document record
            doc = Document(
                id=doc_id,
                source_id=target_source.id,
                project_id=project_id,
                filename=file.filename,
                file_path=str(save_path),
                file_size=file_size,
                extracted_text=parsed.get("extracted_text", ""),
                page_count=parsed.get("page_count", 0),
                extraction_status="ocr_required" if ocr_required else "processed",
                ocr_required=ocr_required
            )
            db.add(doc)

            # Compare metadata if source already had bibliographic information (FR-03)
            if target_source.doi and pdf_doi:
                comp = retrieval_service.compare_metadata(
                    extracted={"doi": pdf_doi, "title": pdf_title, "year": extracted_meta.get("year")},
                    bibliographic={"doi": target_source.doi, "title": target_source.title, "year": target_source.year}
                )
                if not comp["is_match"]:
                    target_source.metadata_verification_status = "mismatch_flagged"

            # Extract structured evidence items
            extracted_items = evidence_extractor.extract_evidence_from_pages(
                pages=parsed.get("pages", []),
                source_abstract=target_source.abstract
            )
            for item in extracted_items:
                ev = Evidence(
                    id=str(uuid.uuid4()),
                    document_id=doc.id,
                    source_id=target_source.id,
                    project_id=project_id,
                    passage_text=item["passage_text"],
                    page_number=item.get("page_number", 1),
                    section_name=item.get("section_name", "Main Text"),
                    category=item.get("category", "finding"),
                    confidence=item.get("confidence", 0.9)
                )
                db.add(ev)

            db.commit()
            processed_count += 1

            status_str = "ocr_required" if ocr_required else "processed"
            warning_msg = parsed.get("warnings", [None])[0] if parsed.get("warnings") else None

            results.append(BatchUploadResultItem(
                filename=file.filename,
                status=status_str,
                source_id=target_source.id,
                title=target_source.title,
                citation_key=target_source.citation_key,
                page_count=parsed.get("page_count", 0),
                ocr_required=ocr_required,
                evidence_count=len(extracted_items),
                metadata_status=target_source.metadata_verification_status,
                warning=warning_msg
            ))

        except Exception as e:
            # Clean up on failure (FR-02.7)
            if save_path.exists():
                try:
                    save_path.unlink()
                except Exception:
                    pass
            results.append(BatchUploadResultItem(
                filename=file.filename,
                status="failed",
                error=f"Processing failed: {str(e)}"
            ))
            failed_count += 1

    return BatchUploadResponse(
        total_files=len(files),
        total_processed=len(files),
        processed_count=processed_count,
        successful_count=processed_count,
        duplicates_count=duplicates_count,
        duplicate_count=duplicates_count,
        ocr_required_count=ocr_required_count,
        failed_count=failed_count,
        results=results
    )

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

    try:
        with open(save_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        file_size = save_path.stat().st_size
        if file_size > 50 * 1024 * 1024:
            if save_path.exists():
                save_path.unlink()
            raise HTTPException(status_code=400, detail="File exceeds maximum allowed size of 50MB.")

        # Parse PDF with DocumentParserService
        parsed = document_parser.parse_pdf(save_path)
    except HTTPException:
        raise
    except Exception as e:
        # Clean up file on failure (FR-02.7)
        if save_path.exists():
            try:
                save_path.unlink()
            except Exception:
                pass
        raise HTTPException(status_code=422, detail=f"Failed to process PDF: {str(e)}")

    ocr_required = parsed.get("ocr_required", False)
    status_str = "ocr_required" if ocr_required else "processed"

    # Compare metadata between uploaded PDF and source record (FR-03)
    pdf_meta = parsed.get("metadata", {})
    if source.doi and pdf_meta.get("doi"):
        comp = retrieval_service.compare_metadata(
            extracted=pdf_meta,
            bibliographic={"doi": source.doi, "title": source.title, "year": source.year}
        )
        if not comp["is_match"]:
            source.metadata_verification_status = "mismatch_flagged"

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
            extraction_status=status_str,
            ocr_required=ocr_required
        )
        db.add(doc)
    else:
        doc.filename = file.filename
        doc.file_path = str(save_path)
        doc.file_size = file_size
        doc.extracted_text = parsed.get("extracted_text", "")
        doc.page_count = parsed.get("page_count", 0)
        doc.extraction_status = status_str
        doc.ocr_required = ocr_required

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
    
    # If source has a document, delete physical file on disk
    if source.document and source.document.file_path:
        p = Path(source.document.file_path)
        if p.exists():
            try:
                p.unlink()
            except Exception:
                pass

    db.delete(source)
    db.commit()
    return {"status": "success", "message": "Source removed successfully"}
