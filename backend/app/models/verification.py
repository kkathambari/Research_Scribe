from datetime import datetime
from sqlalchemy import Column, String, DateTime, Integer, Float, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base

class Claim(Base):
    __tablename__ = "claims"

    id = Column(String, primary_key=True, index=True)
    manuscript_id = Column(String, ForeignKey("manuscripts.id"), nullable=False, index=True)
    section_id = Column(String, ForeignKey("manuscript_sections.id"), nullable=False, index=True)
    manuscript_section_id = Column(String, nullable=True)
    claim_text = Column(Text, nullable=False)
    claim_type = Column(String, default="empirical")  # empirical, architectural, literature, methodology, limitation
    evidence_category = Column(String, default="scholarly_source")  # repository_implementation, experimental, scholarly_source, user_provided, system_inference
    status = Column(String, default="unverified")  # supported, partially_supported, contradicted, unverified, citation_missing
    verification_status = Column(String, default="unverified")  # supported, partially_supported, contradicted, unverified, citation_missing
    confidence = Column(Float, default=0.5)
    explanation = Column(Text, nullable=True)
    verification_explanation = Column(Text, nullable=True)
    reviewer_status = Column(String, default="pending")  # pending, accepted, modified, rejected
    review_status = Column(String, default="pending")  # pending, accepted, modified, rejected
    created_at = Column(DateTime, default=datetime.utcnow)

    manuscript = relationship("Manuscript", back_populates="claims")
    section = relationship("ManuscriptSection", back_populates="claims")
    citations = relationship("Citation", back_populates="claim", cascade="all, delete-orphan")


class Citation(Base):
    __tablename__ = "citations"

    id = Column(String, primary_key=True, index=True)
    claim_id = Column(String, ForeignKey("claims.id"), nullable=False, index=True)
    source_id = Column(String, ForeignKey("sources.id"), nullable=True, index=True)
    scholarly_source_id = Column(String, nullable=True)
    evidence_id = Column(String, ForeignKey("evidences.id"), nullable=True)
    citation_style = Column(String, default="APA")
    formatted_text = Column(String, nullable=True)
    in_text_citation = Column(String, nullable=True)  # e.g., "(Smith et al., 2023)" or "[1]"
    source_location = Column(String, nullable=True)  # Page/line or URL
    metadata_status = Column(String, default="verified")  # verified, unverified
    support_status = Column(String, default="supported")  # supported, partially_supported, contradicted, unverified
    match_score = Column(Float, default=1.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    claim = relationship("Claim", back_populates="citations")
    source = relationship("Source", back_populates="citations")
    evidence = relationship("Evidence", back_populates="citations")
