from datetime import datetime
from sqlalchemy import Column, String, DateTime, Integer, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base

class Source(Base):
    __tablename__ = "sources"

    id = Column(String, primary_key=True, index=True)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False, index=True)
    title = Column(String, nullable=False)
    authors = Column(Text, nullable=True)  # JSON or comma separated
    year = Column(Integer, nullable=True)
    publication_year = Column(Integer, nullable=True)
    venue = Column(String, nullable=True)
    doi = Column(String, nullable=True, index=True)
    url = Column(String, nullable=True)
    abstract = Column(Text, nullable=True)
    access_status = Column(String, default="open")  # open, restricted, abstract_only
    metadata_source = Column(String, default="crossref_openalex")  # crossref, openalex, arxiv
    retrieval_date = Column(DateTime, default=datetime.utcnow)
    retrieved_at = Column(DateTime, default=datetime.utcnow)
    verified_metadata = Column(Boolean, default=True)
    metadata_verification_status = Column(String, default="verified")  # verified, unverified
    citation_key = Column(String, nullable=True)  # e.g. Vaswani2017
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="sources")
    document = relationship("Document", back_populates="source", uselist=False, cascade="all, delete-orphan")
    evidences = relationship("Evidence", back_populates="source", cascade="all, delete-orphan")
    citations = relationship("Citation", back_populates="source")
    comparisons = relationship("LiteratureComparison", back_populates="source", cascade="all, delete-orphan")

class Document(Base):
    __tablename__ = "documents"

    id = Column(String, primary_key=True, index=True)
    source_id = Column(String, ForeignKey("sources.id"), nullable=True)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False, index=True)
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_size = Column(Integer, default=0)
    extracted_text = Column(Text, nullable=True)
    page_count = Column(Integer, default=0)
    extraction_status = Column(String, default="pending")  # pending, processed, failed
    ocr_required = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    source = relationship("Source", back_populates="document")
    project = relationship("Project", back_populates="documents")
    evidences = relationship("Evidence", back_populates="document", cascade="all, delete-orphan")
