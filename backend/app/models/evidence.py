from datetime import datetime
from sqlalchemy import Column, String, DateTime, Integer, Float, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base

class Evidence(Base):
    __tablename__ = "evidences"

    id = Column(String, primary_key=True, index=True)
    document_id = Column(String, ForeignKey("documents.id"), nullable=True)
    source_id = Column(String, ForeignKey("sources.id"), nullable=True, index=True)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False, index=True)
    evidence_type = Column(String, default="scholarly_source")  # repository_implementation, experimental_result, scholarly_source, user_provided, system_inference
    source_file_id = Column(String, nullable=True)
    source_artifact_id = Column(String, nullable=True)
    source_location = Column(String, nullable=True)  # e.g., "src/models/transformer.py:L45-80", "results.csv:row 12"
    passage_text = Column(Text, nullable=False)
    evidence_text = Column(Text, nullable=True)
    structured_value = Column(Text, nullable=True)  # JSON representation of metrics or configs
    page_number = Column(Integer, nullable=True)
    section_name = Column(String, nullable=True)  # e.g. "Abstract", "Methodology", "Results"
    category = Column(String, default="finding")  # objective, method, finding, limitation, future_work, repo_impl, metric
    confidence = Column(Float, default=1.0)
    verification_status = Column(String, default="verified")  # verified, unverified
    created_at = Column(DateTime, default=datetime.utcnow)

    document = relationship("Document", back_populates="evidences")
    source = relationship("Source", back_populates="evidences")
    project = relationship("Project", back_populates="evidences")
    citations = relationship("Citation", back_populates="evidence")
