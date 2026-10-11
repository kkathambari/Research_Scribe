from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.manuscript import Manuscript, ManuscriptSection
from app.models.source import Source
from app.models.evidence import Evidence
from app.models.verification import Claim, Citation
from app.schemas.verification import (
    VerificationReportResponse, ClaimResponse, CitationResponse, ClaimReviewUpdate
)
from app.services.verification_engine import citation_verifier

router = APIRouter(prefix="/verification", tags=["Verification"])

@router.post("/verify-section/{section_id}", response_model=VerificationReportResponse)
def verify_section(section_id: str, db: Session = Depends(get_db)):
    sec = db.query(ManuscriptSection).filter(ManuscriptSection.id == section_id).first()
    if not sec:
        raise HTTPException(status_code=404, detail="Section not found")

    manuscript = db.query(Manuscript).filter(Manuscript.id == sec.manuscript_id).first()
    if not manuscript:
        raise HTTPException(status_code=404, detail="Manuscript not found")

    # Fetch sources & evidences
    sources_db = db.query(Source).filter(Source.project_id == manuscript.project_id).all()
    sources_list = [
        {
            "id": s.id,
            "title": s.title,
            "authors": s.authors,
            "year": s.year,
            "venue": s.venue,
            "doi": s.doi,
            "abstract": s.abstract,
            "citation_key": s.citation_key
        }
        for s in sources_db
    ]

    evidences_db = db.query(Evidence).filter(Evidence.project_id == manuscript.project_id).all()
    evidences_list = [
        {
            "id": e.id,
            "source_id": e.source_id,
            "passage_text": e.passage_text,
            "page_number": e.page_number,
            "section_name": e.section_name,
            "category": e.category,
            "confidence": e.confidence
        }
        for e in evidences_db
    ]

    # Delete previous claims for section
    db.query(Claim).filter(Claim.section_id == sec.id).delete()

    verification_result = citation_verifier.verify_section_content(
        manuscript_id=manuscript.id,
        section_id=sec.id,
        content=sec.content or "",
        sources=sources_list,
        evidences=evidences_list
    )

    claims_responses: List[ClaimResponse] = []

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

        cite_resps: List[CitationResponse] = []
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

            cite_resps.append(CitationResponse(
                id=cite_data["id"],
                claim_id=c_data["id"],
                source_id=cite_data.get("source_id"),
                evidence_id=cite_data.get("evidence_id"),
                in_text_citation=cite_data.get("in_text_citation"),
                match_score=cite_data.get("match_score", 1.0),
                source_title=cite_data.get("source_title"),
                source_authors=cite_data.get("source_authors"),
                source_year=cite_data.get("source_year"),
                citation_key=cite_data.get("citation_key"),
                evidence_passage=cite_data.get("evidence_passage"),
                page_number=cite_data.get("page_number")
            ))

        claims_responses.append(ClaimResponse(
            id=c_data["id"],
            manuscript_id=manuscript.id,
            section_id=sec.id,
            claim_text=c_data["claim_text"],
            status=c_data["status"],
            confidence=c_data["confidence"],
            explanation=c_data["explanation"],
            reviewer_status=c_data.get("reviewer_status", "pending"),
            created_at=claim_obj.created_at,
            citations=cite_resps
        ))

    db.commit()

    return VerificationReportResponse(
        manuscript_id=manuscript.id,
        section_id=sec.id,
        total_claims=verification_result["total_claims"],
        supported_count=verification_result["supported_count"],
        partially_supported_count=verification_result["partially_supported_count"],
        contradicted_count=verification_result["contradicted_count"],
        unverified_count=verification_result["unverified_count"],
        citation_missing_count=verification_result["citation_missing_count"],
        accuracy_score=verification_result["accuracy_score"],
        claims=claims_responses
    )

@router.get("/report/{manuscript_id}", response_model=VerificationReportResponse)
def get_verification_report(
    manuscript_id: str,
    section_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Claim).filter(Claim.manuscript_id == manuscript_id)
    if section_id:
        query = query.filter(Claim.section_id == section_id)
    
    claims = query.all()
    
    counts = {
        "supported": 0,
        "partially_supported": 0,
        "contradicted": 0,
        "unverified": 0,
        "citation_missing": 0
    }

    claim_responses = []
    for c in claims:
        status_key = c.status if c.status in counts else "unverified"
        counts[status_key] += 1

        cites = []
        for cite in c.citations:
            cites.append(CitationResponse(
                id=cite.id,
                claim_id=c.id,
                source_id=cite.source_id,
                evidence_id=cite.evidence_id,
                in_text_citation=cite.in_text_citation,
                match_score=cite.match_score,
                source_title=cite.source.title if cite.source else None,
                source_authors=cite.source.authors if cite.source else None,
                source_year=cite.source.year if cite.source else None,
                citation_key=cite.source.citation_key if cite.source else None,
                evidence_passage=cite.evidence.passage_text if cite.evidence else (cite.source.abstract if cite.source else None),
                page_number=cite.evidence.page_number if cite.evidence else 1
            ))

        claim_responses.append(ClaimResponse(
            id=c.id,
            manuscript_id=c.manuscript_id,
            section_id=c.section_id,
            claim_text=c.claim_text,
            status=c.status,
            confidence=c.confidence,
            explanation=c.explanation,
            reviewer_status=c.reviewer_status,
            created_at=c.created_at,
            citations=cites
        ))

    total = len(claims)
    supported_total = counts["supported"] + counts["partially_supported"]
    accuracy = round((supported_total / total * 100), 1) if total > 0 else 100.0

    return VerificationReportResponse(
        manuscript_id=manuscript_id,
        section_id=section_id,
        total_claims=total,
        supported_count=counts["supported"],
        partially_supported_count=counts["partially_supported"],
        contradicted_count=counts["contradicted"],
        unverified_count=counts["unverified"],
        citation_missing_count=counts["citation_missing"],
        accuracy_score=accuracy,
        claims=claim_responses
    )

@router.put("/claims/{claim_id}/review", response_model=ClaimResponse)
def review_claim(claim_id: str, payload: ClaimReviewUpdate, db: Session = Depends(get_db)):
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    claim.reviewer_status = payload.reviewer_status
    if payload.updated_claim_text:
        claim.claim_text = payload.updated_claim_text

    db.commit()
    db.refresh(claim)

    cites = []
    for cite in claim.citations:
        cites.append(CitationResponse(
            id=cite.id,
            claim_id=claim.id,
            source_id=cite.source_id,
            evidence_id=cite.evidence_id,
            in_text_citation=cite.in_text_citation,
            match_score=cite.match_score,
            source_title=cite.source.title if cite.source else None,
            source_authors=cite.source.authors if cite.source else None,
            source_year=cite.source.year if cite.source else None,
            citation_key=cite.source.citation_key if cite.source else None,
            evidence_passage=cite.evidence.passage_text if cite.evidence else (cite.source.abstract if cite.source else None),
            page_number=cite.evidence.page_number if cite.evidence else 1
        ))

    return ClaimResponse(
        id=claim.id,
        manuscript_id=claim.manuscript_id,
        section_id=claim.section_id,
        claim_text=claim.claim_text,
        status=claim.status,
        confidence=claim.confidence,
        explanation=claim.explanation,
        reviewer_status=claim.reviewer_status,
        created_at=claim.created_at,
        citations=cites
    )
