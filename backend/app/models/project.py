from datetime import datetime
from sqlalchemy import Column, String, DateTime, Integer, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base

class Project(Base):
    __tablename__ = "projects"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    owner_id = Column(String, nullable=True)
    title = Column(String, nullable=False)
    repository_url = Column(String, nullable=True)  # GitHub repo URL
    topic = Column(Text, nullable=True)
    research_topic = Column(Text, nullable=True)
    research_problem = Column(Text, nullable=True)
    research_question = Column(Text, nullable=True)
    research_questions = Column(Text, nullable=True)  # newline/JSON
    objectives = Column(Text, nullable=True)
    academic_discipline = Column(String, default="Computer Science")
    publication_type = Column(String, default="Conference / Journal Article")
    target_publication = Column(String, nullable=True)
    target_venue = Column(String, nullable=True)
    citation_style = Column(String, default="APA")  # APA, IEEE, Harvard, Vancouver, Chicago
    generation_mode = Column(String, default="automatic")  # automatic, guided
    status = Column(String, default="created")  # created, analyzing, analyzed, drafting, completed
    word_count_target = Column(Integer, default=5000)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    sources = relationship("Source", back_populates="project", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="project", cascade="all, delete-orphan")
    manuscripts = relationship("Manuscript", back_populates="project", cascade="all, delete-orphan")
    repositories = relationship("Repository", back_populates="project", cascade="all, delete-orphan")
    experimental_artifacts = relationship("ExperimentalArtifact", back_populates="project", cascade="all, delete-orphan")
    journal_profiles = relationship("JournalProfile", back_populates="project", cascade="all, delete-orphan")
    review_actions = relationship("ReviewAction", back_populates="project", cascade="all, delete-orphan")
    analysis_jobs = relationship("AnalysisJob", back_populates="project", cascade="all, delete-orphan")
    literature_comparisons = relationship("LiteratureComparison", back_populates="project", cascade="all, delete-orphan")
    evidences = relationship("Evidence", back_populates="project", cascade="all, delete-orphan")
