from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class RepositorySubmitRequest(BaseModel):
    project_id: Optional[str] = None
    repository_url: str = Field(..., description="Valid GitHub repository URL (e.g. https://github.com/owner/repo)")
    branch_or_tag: Optional[str] = Field("main", description="Branch, tag, or commit SHA")
    title: Optional[str] = Field(None, description="Project title")
    research_topic: Optional[str] = Field(None, description="Domain topic")
    target_publication: Optional[str] = Field("IEEE Transactions", description="Target journal / conference")
    citation_style: Optional[str] = Field("IEEE", description="Citation style")
    generation_mode: Optional[str] = Field("automatic", description="automatic or guided")
    resolved_commit_sha: Optional[str] = Field(None, description="Explicit commit SHA")
    file_manifest: Optional[List[Dict[str, Any]]] = Field(None, description="Optional explicit file manifest (for test fixtures or custom snapshots)")

class RepositoryFileResponse(BaseModel):
    id: str
    path: str
    file_type: Optional[str] = None
    language: Optional[str] = None
    size_bytes: int = 0
    analysis_status: str = "analyzed"
    relevance_category: str = "core"
    exclusion_reason: Optional[str] = None

    class Config:
        from_attributes = True

class CodeComponentResponse(BaseModel):
    id: str
    name: str
    component_type: str
    file_path: str
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    description: Optional[str] = None
    input_description: Optional[str] = None
    output_description: Optional[str] = None
    dependencies: Optional[str] = None
    confidence: float = 1.0
    evidence_references: Optional[str] = None

    class Config:
        from_attributes = True

class MethodologyResponse(BaseModel):
    id: str
    snapshot_id: str
    problem_description: Optional[str] = None
    algorithm_description: Optional[str] = None
    preprocessing_steps: Optional[str] = None
    architecture_description: Optional[str] = None
    training_procedure: Optional[str] = None
    evaluation_procedure: Optional[str] = None
    hyperparameters: Optional[str] = None
    equations: Optional[str] = None
    pseudocode: Optional[str] = None
    supporting_components: Optional[str] = None
    review_status: str = "unreviewed"

    class Config:
        from_attributes = True

class MethodologyUpdateRequest(BaseModel):
    problem_description: Optional[str] = None
    algorithm_description: Optional[str] = None
    preprocessing_steps: Optional[str] = None
    architecture_description: Optional[str] = None
    training_procedure: Optional[str] = None
    evaluation_procedure: Optional[str] = None
    hyperparameters: Optional[str] = None
    equations: Optional[str] = None
    pseudocode: Optional[str] = None
    review_status: Optional[str] = "approved"

class ExperimentalResultResponse(BaseModel):
    id: str
    experiment_name: Optional[str] = None
    model_name: Optional[str] = None
    dataset_name: Optional[str] = None
    metric_name: str
    metric_value: float
    metric_unit: Optional[str] = None
    split_name: str = "test"
    random_seed: Optional[int] = None
    reported_or_reproduced: str = "reported"
    source_location: Optional[str] = None
    verification_status: str = "extracted"

    class Config:
        from_attributes = True
        protected_namespaces = ()

class EvidenceGapReport(BaseModel):
    snapshot_id: str
    missing_experiments: List[str] = []
    conflicting_metrics: List[str] = []
    unclear_dataset_provenance: List[str] = []
    missing_baselines: List[str] = []
    unspecified_random_seeds: List[str] = []
    data_leakage_indicators: List[str] = []
    unsupported_claims: List[str] = []
    sufficiency_score: float = 1.0  # 0.0 - 1.0
    recommendations: List[str] = []

class RepositorySnapshotResponse(BaseModel):
    id: str
    repository_id: str
    commit_sha: str
    branch_or_tag: str
    acquired_at: datetime
    analysis_status: str
    file_count: int
    excluded_file_count: int
    analysis_summary: Optional[str] = None
    files: List[RepositoryFileResponse] = []
    components: List[CodeComponentResponse] = []
    methodology: Optional[MethodologyResponse] = None

    class Config:
        from_attributes = True

class RepositoryResponse(BaseModel):
    id: str
    project_id: str
    repository_url: str
    owner_name: Optional[str] = None
    repository_name: Optional[str] = None
    default_branch: str = "main"
    selected_revision: str = "main"
    resolved_commit_sha: Optional[str] = None
    acquisition_status: str = "pending"
    last_analysis_at: Optional[datetime] = None

    class Config:
        from_attributes = True
