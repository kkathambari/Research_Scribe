from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class ReviewActionSubmit(BaseModel):
    checkpoint_name: str
    target_type: str
    target_id: Optional[str] = None
    action_type: str = "approved"  # approved, corrected, rejected
    approved_value: Optional[str] = None
    comment: Optional[str] = None

class LiteratureComparisonResponse(BaseModel):
    id: str
    scholarly_source_id: str
    source_title: Optional[str] = None
    comparison_dimension: str
    related_method: Optional[str] = None
    similarities: Optional[str] = None
    differences: Optional[str] = None
    limitations: Optional[str] = None
    supporting_evidence: Optional[str] = None
    review_status: str = "unreviewed"

    class Config:
        from_attributes = True

class ResearchGapProposal(BaseModel):
    dimension: str
    identified_gap: str
    comparison_rationale: str
    proposed_contribution: str
    source_ids: List[str] = []
    supporting_passages: List[str] = []
    comparison_limitations: Optional[str] = None
    status: str = "hypothesis_requiring_review"

class GuidedCheckpointStatus(BaseModel):
    checkpoint: str
    name: str
    status: str  # pending, ready, approved, skipped
    summary: str
    items_count: int = 0
