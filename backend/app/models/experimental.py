from datetime import datetime
from sqlalchemy import Column, String, DateTime, Integer, Text, ForeignKey, Float
from sqlalchemy.orm import relationship
from app.db.base import Base

class ExperimentalArtifact(Base):
    __tablename__ = "experimental_artifacts"

    id = Column(String, primary_key=True, index=True)
    snapshot_id = Column(String, ForeignKey("repository_snapshots.id"), nullable=False, index=True)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False, index=True)
    file_path = Column(String, nullable=False)
    artifact_type = Column(String, default="metrics_csv")  # metrics_csv, results_json, notebook, log_file, readme_table, figure
    content_hash = Column(String, nullable=True)
    source_type = Column(String, default="repository")  # repository, supplementary_upload
    extraction_status = Column(String, default="extracted")  # extracted, partial, failed
    created_at = Column(DateTime, default=datetime.utcnow)

    snapshot = relationship("RepositorySnapshot", back_populates="experimental_artifacts")
    project = relationship("Project", back_populates="experimental_artifacts")
    results = relationship("ExperimentalResult", back_populates="artifact", cascade="all, delete-orphan")


class ExperimentalResult(Base):
    __tablename__ = "experimental_results"

    id = Column(String, primary_key=True, index=True)
    artifact_id = Column(String, ForeignKey("experimental_artifacts.id"), nullable=False, index=True)
    experiment_name = Column(String, nullable=True)
    model_name = Column(String, nullable=True)  # e.g., "Proposed (ResearchScribe)", "Baseline (Transformer)"
    dataset_name = Column(String, nullable=True)
    metric_name = Column(String, nullable=False)  # e.g., "Accuracy", "BLEU", "F1-Score", "Perplexity"
    metric_value = Column(Float, nullable=False)
    metric_unit = Column(String, nullable=True)  # e.g., "%", "points", "ms"
    split_name = Column(String, default="test")  # train, val, test
    random_seed = Column(Integer, nullable=True)
    reported_or_reproduced = Column(String, default="reported")  # reported, reproduced
    reproduction_run_id = Column(String, nullable=True)
    source_location = Column(String, nullable=True)  # e.g., "results/eval.csv:Row 4", "README.md:Table 2"
    verification_status = Column(String, default="verified")  # verified, conflicting, unverified

    artifact = relationship("ExperimentalArtifact", back_populates="results")
