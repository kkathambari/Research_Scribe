from datetime import datetime
from sqlalchemy import Column, String, DateTime, Integer, Text, ForeignKey, Float
from sqlalchemy.orm import relationship
from app.db.base import Base

class ReviewAction(Base):
    __tablename__ = "review_actions"

    id = Column(String, primary_key=True, index=True)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    checkpoint_name = Column(String, nullable=False)  # inventory, methodology, results, literature, gap_analysis, contributions, outline, sections, verification, compliance
    target_type = Column(String, nullable=False)  # component, methodology, result, source, gap, outline, claim, compliance
    target_id = Column(String, nullable=True)
    action_type = Column(String, nullable=False)  # approved, corrected, rejected, skipped
    previous_value = Column(Text, nullable=True)
    approved_value = Column(Text, nullable=True)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="review_actions")


class AnalysisJob(Base):
    __tablename__ = "analysis_jobs"

    id = Column(String, primary_key=True, index=True)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False, index=True)
    job_type = Column(String, nullable=False)  # repo_acquisition, code_analysis, evidence_extraction, literature_retrieval, manuscript_generation, compliance_check, template_assembly
    status = Column(String, default="pending")  # pending, running, completed, failed
    progress = Column(Float, default=0.0)  # 0.0 - 100.0
    stage_message = Column(String, nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    error_code = Column(String, nullable=True)
    error_message = Column(Text, nullable=True)

    project = relationship("Project", back_populates="analysis_jobs")


class LiteratureComparison(Base):
    __tablename__ = "literature_comparisons"

    id = Column(String, primary_key=True, index=True)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False, index=True)
    scholarly_source_id = Column(String, ForeignKey("sources.id"), nullable=False, index=True)
    comparison_dimension = Column(String, nullable=False)  # problem_formulation, architecture, algorithms, data_sources, experimental_design, metrics, limitations
    related_method = Column(String, nullable=True)
    similarities = Column(Text, nullable=True)
    differences = Column(Text, nullable=True)
    limitations = Column(Text, nullable=True)
    supporting_evidence = Column(Text, nullable=True)
    review_status = Column(String, default="unreviewed")  # unreviewed, approved, modified

    project = relationship("Project", back_populates="literature_comparisons")
    source = relationship("Source", back_populates="comparisons")
