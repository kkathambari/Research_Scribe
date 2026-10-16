from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.config import settings
from app.db.session import get_db
from app.models.manuscript import Manuscript
from app.models.source import Source
from app.models.journal import JournalTemplate
from app.models.verification import Claim
from app.schemas.export import ExportRequest, ExportResponse
from app.services.exporter import exporter
from app.services.verification_engine import verification_engine

router = APIRouter(prefix="/export", tags=["Export"])

@router.post("", response_model=ExportResponse)
def export_manuscript(payload: ExportRequest, db: Session = Depends(get_db)):
    manuscript = db.query(Manuscript).filter(Manuscript.id == payload.manuscript_id).first()
    if not manuscript:
        raise HTTPException(status_code=404, detail="Manuscript not found")

    project = manuscript.project
    if project and project.generation_mode == "guided":
        from app.models.workflow import ReviewAction
        approved_actions = db.query(ReviewAction).filter(
            ReviewAction.project_id == project.id,
            ReviewAction.action_type == "approved"
        ).all()
        approved_cps = set(a.checkpoint_name for a in approved_actions)
        if "compliance" not in approved_cps:
            raise HTTPException(
                status_code=400,
                detail="Guided Mode Gate: Manuscript export is blocked until 'compliance' checkpoint has been reviewed and approved by the researcher."
            )

    # FR-11.6: Pre-export citation integrity check
    integrity = verification_engine.verify_manuscript_integrity(db, payload.manuscript_id)
    if not integrity.get("can_export", True) and payload.block_on_critical_errors:
        raise HTTPException(
            status_code=400,
            detail=f"Export blocked due to critical citation-integrity errors: {'; '.join(integrity.get('critical_errors', []))}"
        )

    sections_list = [
        {
            "id": sec.id,
            "title": sec.title,
            "section_type": sec.section_type,
            "order": sec.order,
            "content": sec.content
        }
        for sec in manuscript.sections
    ]

    sources_db = db.query(Source).filter(Source.project_id == manuscript.project_id).all()
    sources_list = [
        {
            "id": s.id,
            "title": s.title,
            "authors": s.authors,
            "year": s.year or s.publication_year,
            "venue": s.venue,
            "doi": s.doi,
            "url": s.url,
            "citation_key": s.citation_key
        }
        for s in sources_db
    ]

    claims_db = db.query(Claim).filter(Claim.manuscript_id == manuscript.id).all()
    claims_list = []
    unresolved_warnings = 0
    for c in claims_db:
        if c.status in ["unverified", "citation_missing", "contradicted"]:
            unresolved_warnings += 1
        cites = []
        for cite in c.citations:
            cites.append({
                "source_title": cite.source.title if cite.source else None,
                "in_text_citation": cite.in_text_citation,
                "evidence_passage": cite.evidence.passage_text if cite.evidence else None
            })
        claims_list.append({
            "claim_text": c.claim_text,
            "status": c.status,
            "explanation": c.explanation or c.verification_explanation,
            "citations": cites
        })

    # Resolve template path if template requested or linked (FR-23)
    template_path = None
    template_applied = False
    template_obj = None
    if payload.template_id:
        template_obj = db.query(JournalTemplate).filter(JournalTemplate.id == payload.template_id).first()
    elif manuscript.journal_template_id:
        template_obj = db.query(JournalTemplate).filter(JournalTemplate.id == manuscript.journal_template_id).first()

    if template_obj and Path(template_obj.storage_reference).exists():
        template_path = template_obj.storage_reference
        template_applied = True

    abstract_sec = next((s for s in manuscript.sections if s.section_type == "abstract"), None)
    abstract_text = getattr(manuscript, "abstract", None) or (abstract_sec.content if abstract_sec else "")
    target_journal = getattr(manuscript, "target_journal", None) or (manuscript.journal_profile.journal_name if manuscript.journal_profile else (manuscript.project.target_publication if manuscript.project else ""))

    exported_file_path = exporter.export_manuscript(
        manuscript={
            "id": manuscript.id,
            "title": manuscript.title,
            "abstract": abstract_text,
            "target_journal": target_journal
        },
        sections=sections_list,
        sources=sources_list,
        claims=claims_list,
        export_format=payload.export_format,
        citation_style=payload.citation_style or manuscript.citation_style,
        include_verification_appendix=payload.include_verification_appendix,
        template_path=template_path
    )

    filename = exported_file_path.name
    download_url = f"/api/v1/export/download/{filename}"

    return ExportResponse(
        download_url=download_url,
        filename=filename,
        format=payload.export_format,
        citation_style=payload.citation_style or manuscript.citation_style,
        unresolved_warnings_count=unresolved_warnings,
        template_applied=template_applied,
        critical_errors=integrity.get("critical_errors", [])
    )

@router.get("/download/{filename}")
def download_export(filename: str):
    safe_name = Path(filename).name
    file_path = (settings.EXPORTS_DIR / safe_name).resolve()
    if not file_path.is_relative_to(settings.EXPORTS_DIR.resolve()) or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Export file not found")
    
    media_types = {
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".pdf": "application/pdf",
        ".md": "text/markdown",
        ".bib": "text/plain"
    }
    ext = file_path.suffix.lower()
    media_type = media_types.get(ext, "application/octet-stream")

    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=safe_name
    )
