import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.evidence import Evidence
from app.models.source import Source
from app.schemas.evidence import EvidenceCreate, EvidenceUpdate, EvidenceResponse

router = APIRouter(prefix="/evidence", tags=["Evidence"])

@router.get("", response_model=List[EvidenceResponse])
def list_evidence(
    project_id: str = Query(...),
    category: Optional[str] = None,
    source_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Evidence).filter(Evidence.project_id == project_id)
    if category:
        query = query.filter(Evidence.category == category)
    if source_id:
        query = query.filter(Evidence.source_id == source_id)

    evidences = query.order_by(Evidence.category, Evidence.page_number).all()
    results = []
    for ev in evidences:
        resp = EvidenceResponse.from_orm(ev)
        if ev.source:
            resp.source_title = ev.source.title
            resp.source_authors = ev.source.authors
            resp.source_year = ev.source.year
            resp.citation_key = ev.source.citation_key
        results.append(resp)
    return results

@router.post("", response_model=EvidenceResponse)
def create_evidence(payload: EvidenceCreate, db: Session = Depends(get_db)):
    source = db.query(Source).filter(Source.id == payload.source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    ev_id = str(uuid.uuid4())
    ev = Evidence(
        id=ev_id,
        project_id=payload.project_id,
        source_id=payload.source_id,
        document_id=payload.document_id,
        passage_text=payload.passage_text,
        page_number=payload.page_number or 1,
        section_name=payload.section_name or "General",
        category=payload.category or "finding",
        confidence=payload.confidence or 1.0
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)

    resp = EvidenceResponse.from_orm(ev)
    resp.source_title = source.title
    resp.source_authors = source.authors
    resp.source_year = source.year
    resp.citation_key = source.citation_key
    return resp

@router.put("/{evidence_id}", response_model=EvidenceResponse)
def update_evidence(evidence_id: str, payload: EvidenceUpdate, db: Session = Depends(get_db)):
    ev = db.query(Evidence).filter(Evidence.id == evidence_id).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Evidence not found")

    update_data = payload.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(ev, field, value)

    db.commit()
    db.refresh(ev)

    resp = EvidenceResponse.from_orm(ev)
    if ev.source:
        resp.source_title = ev.source.title
        resp.source_authors = ev.source.authors
        resp.source_year = ev.source.year
        resp.citation_key = ev.source.citation_key
    return resp

@router.delete("/{evidence_id}")
def delete_evidence(evidence_id: str, db: Session = Depends(get_db)):
    ev = db.query(Evidence).filter(Evidence.id == evidence_id).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Evidence not found")
    db.delete(ev)
    db.commit()
    return {"status": "success", "message": "Evidence removed"}
