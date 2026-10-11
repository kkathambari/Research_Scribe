import json
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.config import settings
from app.models.journal import JournalProfile, JournalTemplate
from app.models.manuscript import Manuscript
from app.schemas.journal import (
    JournalProfileResponse,
    JournalProfileCreate,
    ComplianceReportResponse,
)
from app.services.journal_intelligence import journal_intelligence, DEFAULT_JOURNAL_PROFILES

router = APIRouter(prefix="/journals", tags=["Journal Template Intelligence & Compliance"])

@router.get("/profiles", response_model=List[JournalProfileResponse])
def list_journal_profiles(project_id: Optional[str] = None, db: Session = Depends(get_db)):
    """FR-19: Lists available official journal and conference requirement profiles."""
    # Ensure default profiles are seeded
    for name in DEFAULT_JOURNAL_PROFILES.keys():
        journal_intelligence.get_or_create_journal_profile(db, name)

    query = db.query(JournalProfile)
    if project_id:
        query = query.filter((JournalProfile.project_id == project_id) | (JournalProfile.project_id.is_(None)))
    profiles = query.all()
    return [JournalProfileResponse.from_orm(p) for p in profiles]

@router.post("/profiles", response_model=JournalProfileResponse)
def create_custom_journal_profile(
    data: JournalProfileCreate,
    project_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """FR-21: Creates a custom Journal Profile based on user author guidelines."""
    profile = journal_intelligence.get_or_create_journal_profile(
        db,
        journal_name=data.journal_name,
        project_id=project_id
    )
    if data.publisher:
        profile.publisher = data.publisher
    if data.word_limit:
        profile.word_limit = data.word_limit
    if data.citation_style:
        profile.citation_style = data.citation_style
    if data.required_sections:
        profile.required_sections = json.dumps(data.required_sections)
    db.commit()
    db.refresh(profile)
    return JournalProfileResponse.from_orm(profile)

@router.post("/templates/upload")
async def upload_journal_template(
    profile_id: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """FR-20: Ingests an official DOCX template, extracting font styles, margins, headers, and placeholders."""
    profile = db.query(JournalProfile).filter(JournalProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Journal profile not found")

    safe_filename = Path(file.filename).name
    if not safe_filename.lower().endswith(".docx"):
        raise HTTPException(status_code=400, detail="Only official .docx template files are supported.")

    dest_dir = settings.UPLOAD_DIR / "templates"
    dest_dir.mkdir(parents=True, exist_ok=True)
    file_path = (dest_dir / safe_filename).resolve()
    if not file_path.is_relative_to(dest_dir.resolve()):
        raise HTTPException(status_code=400, detail="Invalid template filename.")

    MAX_SIZE = 25 * 1024 * 1024  # 25 MB
    content = await file.read()
    if len(content) > MAX_SIZE:
        raise HTTPException(status_code=413, detail="Template file exceeds maximum permitted size of 25MB.")

    file_path.write_bytes(content)

    template = journal_intelligence.import_template_file(
        db=db,
        profile_id=profile_id,
        file_path=file_path,
        template_filename=safe_filename
    )

    return {
        "status": "success",
        "template_id": template.id,
        "filename": template.template_filename,
        "format": template.template_format,
        "analysis_status": template.analysis_status,
        "styles_count": len(template.styles)
    }

@router.get("/validate/{manuscript_id}", response_model=ComplianceReportResponse)
def validate_manuscript_compliance(
    manuscript_id: str,
    profile_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """FR-24: Compares manuscript sections, length, abstract, and declarations against journal profile."""
    manuscript = db.query(Manuscript).filter(Manuscript.id == manuscript_id).first()
    if not manuscript:
        raise HTTPException(status_code=404, detail="Manuscript not found")

    profile = None
    if profile_id:
        profile = db.query(JournalProfile).filter(JournalProfile.id == profile_id).first()
    if not profile and manuscript.journal_profile_id:
        profile = db.query(JournalProfile).filter(JournalProfile.id == manuscript.journal_profile_id).first()
    if not profile:
        profile = journal_intelligence.get_or_create_journal_profile(db, "IEEE Transactions")

    report = journal_intelligence.validate_compliance(db, manuscript, profile)
    return report
