import hashlib
import json
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.project import Project
from app.models.repository import Repository, RepositorySnapshot, MethodologyRecord, CodeComponent
from app.models.experimental import ExperimentalArtifact, ExperimentalResult
from app.schemas.repository import (
    RepositorySubmitRequest,
    RepositoryResponse,
    RepositorySnapshotResponse,
    MethodologyResponse,
    MethodologyUpdateRequest,
    ExperimentalResultResponse,
    EvidenceGapReport,
    CodeComponentResponse,
)
from app.services.repository_analyzer import repository_analyzer

router = APIRouter(prefix="/repositories", tags=["Repositories & Codebase Intelligence"])

@router.post("/submit", response_model=RepositoryResponse)
def submit_repository(
    data: RepositorySubmitRequest,
    db: Session = Depends(get_db)
):
    """FR-01: Accepts and validates a GitHub repository URL, resolving an authorized snapshot."""
    project_id = data.project_id
    if not project_id:
        # Create a new project automatically if none provided
        proj = Project(
            id=f"proj_{hashlib.md5(data.repository_url.encode()).hexdigest()[:10]}",
            title=data.title or f"Empirical Study: {data.repository_url.split('/')[-1]}",
            repository_url=data.repository_url,
            research_topic=data.research_topic or "Automated Software & Model Evaluation",
            target_publication=data.target_publication or "IEEE Transactions",
            citation_style=data.citation_style or "IEEE",
            generation_mode=data.generation_mode or "automatic"
        )
        db.add(proj)
        db.commit()
        project_id = proj.id

    try:
        repo = repository_analyzer.acquire_repository(
            db,
            project_id=project_id,
            repository_url=data.repository_url,
            branch_or_tag=data.branch_or_tag or "main",
            resolved_commit_sha=data.resolved_commit_sha,
            allow_unverified_commit=data.allow_unverified_commit
        )
        # Automatically build snapshot from codebase manifest or acquire files
        snapshot = repository_analyzer.create_snapshot_from_manifest(
            db,
            repo,
            file_manifest=data.file_manifest,
            allow_unverified_commit=data.allow_unverified_commit
        )
        return RepositoryResponse.from_orm(repo)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{repo_id}", response_model=RepositoryResponse)
def get_repository(repo_id: str, db: Session = Depends(get_db)):
    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    return RepositoryResponse.from_orm(repo)

@router.get("/{repo_id}/snapshot", response_model=RepositorySnapshotResponse)
def get_repository_snapshot(repo_id: str, db: Session = Depends(get_db)):
    """FR-02 & FR-03: Returns the immutable snapshot, file inventory, and analysis summary."""
    snapshot = db.query(RepositorySnapshot).filter(RepositorySnapshot.repository_id == repo_id).first()
    if not snapshot:
        raise HTTPException(status_code=404, detail="Repository snapshot not found")
    return RepositorySnapshotResponse.from_orm(snapshot)

@router.get("/{repo_id}/architecture", response_model=List[CodeComponentResponse])
def get_architecture_components(repo_id: str, db: Session = Depends(get_db)):
    """FR-04: Returns the reconstructed architecture components and pipelines."""
    snapshot = db.query(RepositorySnapshot).filter(RepositorySnapshot.repository_id == repo_id).first()
    if not snapshot:
        raise HTTPException(status_code=404, detail="Repository snapshot not found")
    return [CodeComponentResponse.from_orm(c) for c in snapshot.components]

@router.get("/{repo_id}/methodology", response_model=MethodologyResponse)
def get_methodology(repo_id: str, db: Session = Depends(get_db)):
    """FR-05: Returns the reconstructed execution logic, loss functions, equations, and pseudocode."""
    snapshot = db.query(RepositorySnapshot).filter(RepositorySnapshot.repository_id == repo_id).first()
    if not snapshot or not snapshot.methodology:
        raise HTTPException(status_code=404, detail="Methodology record not found")
    return MethodologyResponse.from_orm(snapshot.methodology)

@router.put("/{repo_id}/methodology", response_model=MethodologyResponse)
def update_methodology(
    repo_id: str,
    data: MethodologyUpdateRequest,
    db: Session = Depends(get_db)
):
    """FR-05 & FR-14: Allows researchers to correct or approve the inferred methodology in Guided Mode."""
    snapshot = db.query(RepositorySnapshot).filter(RepositorySnapshot.repository_id == repo_id).first()
    if not snapshot or not snapshot.methodology:
        raise HTTPException(status_code=404, detail="Methodology record not found")
    
    meth = snapshot.methodology
    if data.problem_description is not None:
        meth.problem_description = data.problem_description
    if data.algorithm_description is not None:
        meth.algorithm_description = data.algorithm_description
    if data.preprocessing_steps is not None:
        meth.preprocessing_steps = data.preprocessing_steps
    if data.architecture_description is not None:
        meth.architecture_description = data.architecture_description
    if data.training_procedure is not None:
        meth.training_procedure = data.training_procedure
    if data.evaluation_procedure is not None:
        meth.evaluation_procedure = data.evaluation_procedure
    if data.hyperparameters is not None:
        meth.hyperparameters = data.hyperparameters
    if data.equations is not None:
        meth.equations = data.equations
    if data.pseudocode is not None:
        meth.pseudocode = data.pseudocode
    if data.review_status is not None:
        meth.review_status = data.review_status

    db.commit()
    db.refresh(meth)
    return MethodologyResponse.from_orm(meth)

@router.get("/{repo_id}/evidence-gap", response_model=EvidenceGapReport)
def get_evidence_gap_report(repo_id: str, db: Session = Depends(get_db)):
    """FR-07: Produces the Evidence Sufficiency & Consistency Analysis report."""
    snapshot = db.query(RepositorySnapshot).filter(RepositorySnapshot.repository_id == repo_id).first()
    if not snapshot:
        raise HTTPException(status_code=404, detail="Repository snapshot not found")
    return repository_analyzer.analyze_evidence_sufficiency(db, snapshot.id, snapshot.repository.project_id)

@router.get("/{repo_id}/experimental-results", response_model=List[ExperimentalResultResponse])
def get_experimental_results(repo_id: str, db: Session = Depends(get_db)):
    """FR-06: Returns all empirical evaluation metrics extracted from repository artifacts."""
    snapshot = db.query(RepositorySnapshot).filter(RepositorySnapshot.repository_id == repo_id).first()
    if not snapshot:
        raise HTTPException(status_code=404, detail="Repository snapshot not found")
    
    results = (
        db.query(ExperimentalResult)
        .join(ExperimentalArtifact)
        .filter(ExperimentalArtifact.snapshot_id == snapshot.id)
        .all()
    )
    return [ExperimentalResultResponse.from_orm(r) for r in results]
