import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.manuscript import Manuscript, ManuscriptSection
from app.models.project import Project
from app.models.source import Source
from app.models.evidence import Evidence
from app.models.verification import Claim, Citation
from app.schemas.manuscript import (
    ManuscriptResponse, ManuscriptSectionResponse,
    ManuscriptSectionUpdate, SectionGenerateRequest
)
from app.services.synthesis_engine import synthesis_engine
from app.services.verification_engine import citation_verifier
from app.services.citation_formatter import citation_formatter

router = APIRouter(prefix="/manuscripts", tags=["Manuscripts"])

@router.get("/{manuscript_id}", response_model=ManuscriptResponse)
def get_manuscript(manuscript_id: str, db: Session = Depends(get_db)):
    manuscript = db.query(Manuscript).filter(Manuscript.id == manuscript_id).first()
    if not manuscript:
        raise HTTPException(status_code=404, detail="Manuscript not found")

    sections_res = []
    for sec in manuscript.sections:
        sec_resp = ManuscriptSectionResponse.from_orm(sec)
        claims = db.query(Claim).filter(Claim.section_id == sec.id).all()
        sec_resp.claims_count = len(claims)
        sec_resp.verified_claims_count = len([c for c in claims if c.status in ["supported", "partially_supported"]])
        sections_res.append(sec_resp)

    resp = ManuscriptResponse.from_orm(manuscript)
    resp.sections = sections_res
    return resp

@router.put("/{manuscript_id}/sections/{section_id}", response_model=ManuscriptSectionResponse)
def update_section(
    manuscript_id: str,
    section_id: str,
    payload: ManuscriptSectionUpdate,
    db: Session = Depends(get_db)
):
    sec = db.query(ManuscriptSection).filter(
        ManuscriptSection.id == section_id,
        ManuscriptSection.manuscript_id == manuscript_id
    ).first()
    if not sec:
        raise HTTPException(status_code=404, detail="Section not found")

    update_data = payload.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(sec, field, value)

    db.commit()
    db.refresh(sec)

    resp = ManuscriptSectionResponse.from_orm(sec)
    claims = db.query(Claim).filter(Claim.section_id == sec.id).all()
    resp.claims_count = len(claims)
    resp.verified_claims_count = len([c for c in claims if c.status in ["supported", "partially_supported"]])
    return resp

@router.post("/{manuscript_id}/sections/{section_id}/generate", response_model=ManuscriptSectionResponse)
async def generate_section(
    manuscript_id: str,
    section_id: str,
    payload: SectionGenerateRequest,
    db: Session = Depends(get_db)
):
    manuscript = db.query(Manuscript).filter(Manuscript.id == manuscript_id).first()
    if not manuscript:
        raise HTTPException(status_code=404, detail="Manuscript not found")

    sec = db.query(ManuscriptSection).filter(
        ManuscriptSection.id == section_id,
        ManuscriptSection.manuscript_id == manuscript_id
    ).first()
    if not sec:
        raise HTTPException(status_code=404, detail="Section not found")

    project = db.query(Project).filter(Project.id == manuscript.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Associated project not found")

    # Fetch sources
    src_query = db.query(Source).filter(Source.project_id == project.id)
    if payload.source_ids:
        src_query = src_query.filter(Source.id.in_(payload.source_ids))
    sources_db = src_query.all()
    sources_list = [
        {
            "id": s.id,
            "title": s.title,
            "authors": s.authors,
            "year": s.year,
            "venue": s.venue,
            "doi": s.doi,
            "url": s.url,
            "abstract": s.abstract,
            "citation_key": s.citation_key
        }
        for s in sources_db
    ]

    # Fetch evidence passages
    ev_query = db.query(Evidence).filter(Evidence.project_id == project.id)
    if payload.source_ids:
        ev_query = ev_query.filter(Evidence.source_id.in_(payload.source_ids))
    evidences_db = ev_query.all()
    evidences_list = [
        {
            "id": e.id,
            "source_id": e.source_id,
            "passage_text": e.passage_text,
            "page_number": e.page_number,
            "section_name": e.section_name,
            "category": e.category,
            "confidence": e.confidence,
            "citation_key": e.source.citation_key if e.source else "Ref"
        }
        for e in evidences_db
    ]

    # Generate section content
    generated_text = await synthesis_engine.generate_section(
        project={
            "title": project.title,
            "topic": project.topic,
            "research_problem": project.research_problem,
            "research_questions": project.research_questions,
            "objectives": project.objectives,
            "academic_discipline": project.academic_discipline,
            "publication_type": project.publication_type,
            "citation_style": manuscript.citation_style
        },
        section_type=payload.section_type or sec.section_type,
        section_title=payload.title or sec.title,
        sources=sources_list,
        evidences=evidences_list,
        instructions=payload.instructions or sec.instructions,
        word_limit=payload.word_limit or sec.word_limit,
        experimental_data=payload.experimental_data
    )

    sec.content = generated_text
    sec.status = "generated"
    if payload.instructions:
        sec.instructions = payload.instructions
    if payload.word_limit:
        sec.word_limit = payload.word_limit

    # Run immediate automated claim and citation verification
    # Clean previous claims for this section
    db.query(Claim).filter(Claim.section_id == sec.id).delete()

    verification_result = citation_verifier.verify_section_content(
        manuscript_id=manuscript.id,
        section_id=sec.id,
        content=generated_text,
        sources=sources_list,
        evidences=evidences_list
    )

    # Persist claim and citation records
    for c_data in verification_result["claims"]:
        claim_obj = Claim(
            id=c_data["id"],
            manuscript_id=manuscript.id,
            section_id=sec.id,
            claim_text=c_data["claim_text"],
            status=c_data["status"],
            confidence=c_data["confidence"],
            explanation=c_data["explanation"],
            reviewer_status=c_data.get("reviewer_status", "pending")
        )
        db.add(claim_obj)

        for cite_data in c_data.get("citations", []):
            cite_obj = Citation(
                id=cite_data["id"],
                claim_id=c_data["id"],
                source_id=cite_data.get("source_id"),
                evidence_id=cite_data.get("evidence_id"),
                in_text_citation=cite_data.get("in_text_citation"),
                match_score=cite_data.get("match_score", 1.0)
            )
            db.add(cite_obj)

    db.commit()
    db.refresh(sec)

    resp = ManuscriptSectionResponse.from_orm(sec)
    resp.claims_count = len(verification_result["claims"])
    resp.verified_claims_count = verification_result["supported_count"] + verification_result["partially_supported_count"]
    return resp
