from datetime import datetime
from sqlalchemy import Column, String, DateTime, Integer, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base

class Manuscript(Base):
    __tablename__ = "manuscripts"

    id = Column(String, primary_key=True, index=True)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False, index=True)
    repository_snapshot_id = Column(String, ForeignKey("repository_snapshots.id"), nullable=True, index=True)
    journal_profile_id = Column(String, ForeignKey("journal_profiles.id"), nullable=True, index=True)
    journal_template_id = Column(String, ForeignKey("journal_templates.id"), nullable=True, index=True)
    title = Column(String, nullable=False)
    citation_style = Column(String, default="APA")
    version = Column(Integer, default=1)
    version_number = Column(Integer, default=1)
    generation_mode = Column(String, default="automatic")  # automatic, guided
    outline = Column(Text, nullable=True)  # JSON outline
    status = Column(String, default="draft")  # draft, generated, validated, finalized
    generation_configuration = Column(Text, nullable=True)  # JSON configuration
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("Project", back_populates="manuscripts")
    snapshot = relationship("RepositorySnapshot", back_populates="manuscripts")
    journal_profile = relationship("JournalProfile", back_populates="manuscripts")
    journal_template = relationship("JournalTemplate", back_populates="manuscripts")
    sections = relationship("ManuscriptSection", back_populates="manuscript", cascade="all, delete-orphan", order_by="ManuscriptSection.order")
    claims = relationship("Claim", back_populates="manuscript", cascade="all, delete-orphan")
    compliance_checks = relationship("ComplianceCheck", back_populates="manuscript", cascade="all, delete-orphan")


class ManuscriptSection(Base):
    __tablename__ = "manuscript_sections"

    id = Column(String, primary_key=True, index=True)
    manuscript_id = Column(String, ForeignKey("manuscripts.id"), nullable=False, index=True)
    section_type = Column(String, nullable=False)  # abstract, introduction, related_work, methodology, architecture, experimental_setup, results, discussion, limitations, conclusion, references
    title = Column(String, nullable=False)
    heading = Column(String, nullable=True)
    order = Column(Integer, default=0)
    section_order = Column(Integer, default=0)
    content = Column(Text, default="")
    instructions = Column(Text, nullable=True)
    word_limit = Column(Integer, nullable=True)
    status = Column(String, default="draft")  # draft, generated, reviewed
    generation_status = Column(String, default="pending")  # pending, generated, approved
    review_status = Column(String, default="unreviewed")  # unreviewed, approved, modified, rejected
    version_number = Column(Integer, default=1)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    manuscript = relationship("Manuscript", back_populates="sections")
    claims = relationship("Claim", back_populates="section", cascade="all, delete-orphan")
