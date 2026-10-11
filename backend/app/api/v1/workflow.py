from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.project import Project
from app.models.repository import RepositorySnapshot
from app.schemas.workflow import (
    GuidedCheckpointStatus,
    ReviewActionSubmit,
    ResearchGapProposal,
    LiteratureComparisonResponse,
)
from app.services.workflow_orchestrator import workflow_orchestrator
from app.services.novelty_analyzer import novelty_analyzer

router = APIRouter(prefix="/workflow", tags=["Operating Modes & Workflow Orchestration"])

@router.get("/checkpoints/{project_id}", response_model=List[GuidedCheckpointStatus])
def get_guided_checkpoints(project_id: str, db: Session = Depends(get_db)):
    """FR-14: Retrieves the progress and review statuses across all 10 Guided Mode checkpoints."""
    return workflow_orchestrator.get_guided_checkpoints(db, project_id)

@router.post("/review-action/{project_id}")
def record_review_action(
    project_id: str,
    action_data: ReviewActionSubmit,
    db: Session = Depends(get_db)
):
    """FR-14 & FR-27: Records an explicit researcher approval or correction at a review checkpoint."""
    try:
        action = workflow_orchestrator.record_review_action(db, project_id, action_data)
        return {
            "status": "success",
            "action_id": action.id,
            "checkpoint": action.checkpoint_name,
            "action": action.action_type
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/check-gate/{project_id}/{checkpoint_code}")
def check_checkpoint_gate(
    project_id: str,
    checkpoint_code: str,
    db: Session = Depends(get_db)
):
    """Checks whether the specified checkpoint is accessible or blocked by unmet prerequisites."""
    try:
        workflow_orchestrator.assert_checkpoint_accessible(db, project_id, checkpoint_code)
        return {"status": "unblocked", "checkpoint": checkpoint_code}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/research-gaps/{project_id}", response_model=List[ResearchGapProposal])
def get_research_gaps_and_contributions(
    project_id: str,
    snapshot_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """FR-11: Formulates 7-dimension comparative research gaps and contribution hypotheses."""
    snapshot = None
    if snapshot_id:
        snapshot = db.query(RepositorySnapshot).filter(RepositorySnapshot.id == snapshot_id).first()
    return novelty_analyzer.analyze_research_gaps_and_contributions(db, project_id, snapshot)

@router.get("/literature-comparisons/{project_id}", response_model=List[LiteratureComparisonResponse])
def get_literature_comparisons(project_id: str, db: Session = Depends(get_db)):
    """FR-10 & FR-11: Retrieves literature comparison records across methods, datasets, and limitations."""
    return novelty_analyzer.get_literature_comparisons(db, project_id)

@router.post("/generate-sections/{project_id}")
def generate_sections(project_id: str, db: Session = Depends(get_db)):
    """Gated section generation execution for Guided Mode."""
    try:
        manuscript = workflow_orchestrator.generate_guided_sections(db, project_id)
        return {
            "status": "success",
            "manuscript_id": manuscript.id,
            "sections_count": len(manuscript.sections)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/run-automatic/{project_id}")
def run_automatic_generation(
    project_id: str,
    repository_url: Optional[str] = Query(None),
    journal_name: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    FR-13: One-click Automatic Mode executing end-to-end repository analysis,
    literature retrieval, grounded section generation, citation verification,
    and journal compliance audit.
    """
    try:
        result = workflow_orchestrator.run_automatic_mode(
            db=db,
            project_id=project_id,
            repository_url=repository_url,
            journal_name=journal_name
        )
        return {
            "status": "completed",
            "summary": result
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
