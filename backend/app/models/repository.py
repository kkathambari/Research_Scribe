from datetime import datetime
from sqlalchemy import Column, String, DateTime, Integer, Text, ForeignKey, Boolean, Float
from sqlalchemy.orm import relationship
from app.db.base import Base

class Repository(Base):
    __tablename__ = "repositories"

    id = Column(String, primary_key=True, index=True)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False, index=True)
    repository_url = Column(String, nullable=False)
    owner_name = Column(String, nullable=True)
    repository_name = Column(String, nullable=True)
    visibility = Column(String, default="public")
    default_branch = Column(String, default="main")
    selected_revision = Column(String, default="main")
    resolved_commit_sha = Column(String, nullable=True)
    acquisition_status = Column(String, default="pending")  # pending, acquired, failed
    last_analysis_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="repositories")
    snapshots = relationship("RepositorySnapshot", back_populates="repository", cascade="all, delete-orphan")


class RepositorySnapshot(Base):
    __tablename__ = "repository_snapshots"

    id = Column(String, primary_key=True, index=True)
    repository_id = Column(String, ForeignKey("repositories.id"), nullable=False, index=True)
    commit_sha = Column(String, nullable=False, index=True)
    branch_or_tag = Column(String, default="main")
    snapshot_hash = Column(String, nullable=True)
    acquired_at = Column(DateTime, default=datetime.utcnow)
    analysis_status = Column(String, default="pending")  # pending, analyzing, completed, failed
    file_count = Column(Integer, default=0)
    excluded_file_count = Column(Integer, default=0)
    analysis_summary = Column(Text, nullable=True)

    repository = relationship("Repository", back_populates="snapshots")
    files = relationship("RepositoryFile", back_populates="snapshot", cascade="all, delete-orphan")
    components = relationship("CodeComponent", back_populates="snapshot", cascade="all, delete-orphan")
    methodology = relationship("MethodologyRecord", back_populates="snapshot", uselist=False, cascade="all, delete-orphan")
    experimental_artifacts = relationship("ExperimentalArtifact", back_populates="snapshot", cascade="all, delete-orphan")
    manuscripts = relationship("Manuscript", back_populates="snapshot")


class RepositoryFile(Base):
    __tablename__ = "repository_files"

    id = Column(String, primary_key=True, index=True)
    snapshot_id = Column(String, ForeignKey("repository_snapshots.id"), nullable=False, index=True)
    path = Column(String, nullable=False)
    file_type = Column(String, nullable=True)  # source, config, data, doc, notebook, test
    language = Column(String, nullable=True)
    content_hash = Column(String, nullable=True)
    size_bytes = Column(Integer, default=0)
    analysis_status = Column(String, default="pending")  # pending, analyzed, excluded
    relevance_category = Column(String, default="core")  # core, model, pipeline, evaluation, utility, test, doc
    exclusion_reason = Column(String, nullable=True)

    snapshot = relationship("RepositorySnapshot", back_populates="files")


class CodeComponent(Base):
    __tablename__ = "code_components"

    id = Column(String, primary_key=True, index=True)
    snapshot_id = Column(String, ForeignKey("repository_snapshots.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    component_type = Column(String, default="module")  # model, pipeline, dataloader, optimizer, loss, evaluation, utility
    file_path = Column(String, nullable=False)
    start_line = Column(Integer, nullable=True)
    end_line = Column(Integer, nullable=True)
    description = Column(Text, nullable=True)
    input_description = Column(Text, nullable=True)
    output_description = Column(Text, nullable=True)
    dependencies = Column(Text, nullable=True)  # JSON or comma-separated
    confidence = Column(Float, default=1.0)
    evidence_references = Column(Text, nullable=True)  # Code snippets or token spans

    snapshot = relationship("RepositorySnapshot", back_populates="components")


class MethodologyRecord(Base):
    __tablename__ = "methodology_records"

    id = Column(String, primary_key=True, index=True)
    snapshot_id = Column(String, ForeignKey("repository_snapshots.id"), nullable=False, unique=True, index=True)
    problem_description = Column(Text, nullable=True)
    algorithm_description = Column(Text, nullable=True)
    preprocessing_steps = Column(Text, nullable=True)
    architecture_description = Column(Text, nullable=True)
    training_procedure = Column(Text, nullable=True)
    evaluation_procedure = Column(Text, nullable=True)
    hyperparameters = Column(Text, nullable=True)  # JSON or key-value list
    equations = Column(Text, nullable=True)  # LaTeX equations extracted/inferred
    pseudocode = Column(Text, nullable=True)  # Algorithmic pseudocode
    supporting_components = Column(Text, nullable=True)  # JSON references
    review_status = Column(String, default="unreviewed")  # unreviewed, approved, modified

    snapshot = relationship("RepositorySnapshot", back_populates="methodology")
