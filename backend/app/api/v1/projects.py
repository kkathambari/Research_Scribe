import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.project import Project
from app.models.source import Source
from app.models.repository import Repository, RepositorySnapshot
from app.models.manuscript import Manuscript, ManuscriptSection
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse
from app.services.synthesis_engine import synthesis_engine
from app.services.repository_analyzer import repository_analyzer

router = APIRouter(prefix="/projects", tags=["Projects"])

@router.post("", response_model=ProjectResponse)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)):
    project_id = str(uuid.uuid4())
    project = Project(
        id=project_id,
        title=payload.title,
        repository_url=payload.repository_url,
        topic=payload.topic or payload.research_topic,
        research_topic=payload.research_topic or payload.topic,
        research_problem=payload.research_problem,
        research_questions=payload.research_questions or payload.research_question,
        research_question=payload.research_question or payload.research_questions,
        objectives=payload.objectives,
        academic_discipline=payload.academic_discipline or "Computer Science",
        publication_type=payload.publication_type or "Conference / Journal Article",
        target_venue=payload.target_venue or payload.target_publication,
        target_publication=payload.target_publication or payload.target_venue,
        citation_style=payload.citation_style or "APA",
        generation_mode=payload.generation_mode or "automatic",
        word_count_target=payload.word_count_target or 5000,
        status="created"
    )
    db.add(project)
    db.commit()

    repo_id = None
    snapshot_id = None

    # If GitHub repository URL provided, ingest it (FR-01, FR-02)
    if payload.repository_url:
        try:
            allow_unverified = bool(payload.allow_unverified_commit)
            repo = repository_analyzer.acquire_repository(
                db=db,
                project_id=project_id,
                repository_url=payload.repository_url,
                branch_or_tag=payload.branch_or_tag or "main",
                resolved_commit_sha=payload.resolved_commit_sha,
                allow_unverified_commit=allow_unverified
            )
            snapshot = repository_analyzer.create_snapshot_from_manifest(
                db=db,
                repository=repo,
                file_manifest=payload.file_manifest,
                allow_unverified_commit=allow_unverified
            )
            repo_id = repo.id
            snapshot_id = snapshot.id
            project.status = "analyzed"
            db.commit()
        except Exception as e:
            project.status = "acquisition_failed"
            db.commit()

    # Automatically create initial manuscript draft
    manuscript_id = str(uuid.uuid4())
    manuscript = Manuscript(
        id=manuscript_id,
        project_id=project_id,
        repository_snapshot_id=snapshot_id,
        title=payload.title,
        citation_style=payload.citation_style or "APA",
        generation_mode=payload.generation_mode or "automatic",
        version=1,
        version_number=1,
        status="draft"
    )
    db.add(manuscript)

    # Initialize standard manuscript outline
    outline = synthesis_engine.generate_outline(payload.dict())
    for item in outline:
        sec = ManuscriptSection(
            id=str(uuid.uuid4()),
            manuscript_id=manuscript_id,
            section_type=item["section_type"],
            title=item["title"],
            order=item["order"],
            instructions=item.get("instructions"),
            word_limit=item.get("word_limit"),
            content="",
            status="draft"
        )
        db.add(sec)

    db.commit()
    db.refresh(project)

    resp = ProjectResponse.from_orm(project)
    resp.sources_count = 0
    resp.manuscript_id = manuscript_id
    resp.repository_id = repo_id
    resp.snapshot_id = snapshot_id
    return resp

@router.get("", response_model=List[ProjectResponse])
def list_projects(db: Session = Depends(get_db)):
    projects = db.query(Project).order_by(Project.created_at.desc()).all()
    results = []
    for p in projects:
        resp = ProjectResponse.from_orm(p)
        resp.sources_count = db.query(Source).filter(Source.project_id == p.id).count()
        first_m = db.query(Manuscript).filter(Manuscript.project_id == p.id).first()
        first_repo = db.query(Repository).filter(Repository.project_id == p.id).first()
        first_snap = db.query(RepositorySnapshot).join(Repository).filter(Repository.project_id == p.id).first()
        resp.manuscript_id = first_m.id if first_m else None
        resp.repository_id = first_repo.id if first_repo else None
        resp.snapshot_id = first_snap.id if first_snap else None
        results.append(resp)
    return results

@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    resp = ProjectResponse.from_orm(project)
    resp.sources_count = db.query(Source).filter(Source.project_id == project.id).count()
    first_m = db.query(Manuscript).filter(Manuscript.project_id == project.id).first()
    first_repo = db.query(Repository).filter(Repository.project_id == project.id).first()
    first_snap = db.query(RepositorySnapshot).join(Repository).filter(Repository.project_id == project.id).first()
    resp.manuscript_id = first_m.id if first_m else None
    resp.repository_id = first_repo.id if first_repo else None
    resp.snapshot_id = first_snap.id if first_snap else None
    return resp

@router.put("/{project_id}", response_model=ProjectResponse)
def update_project(project_id: str, payload: ProjectUpdate, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    update_data = payload.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(project, field, value)

    db.commit()
    db.refresh(project)
    resp = ProjectResponse.from_orm(project)
    resp.sources_count = db.query(Source).filter(Source.project_id == project.id).count()
    first_m = db.query(Manuscript).filter(Manuscript.project_id == project.id).first()
    resp.manuscript_id = first_m.id if first_m else None
    return resp

@router.delete("/{project_id}")
def delete_project(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    db.delete(project)
    db.commit()
    return {"message": "Project deleted successfully", "id": project_id}
