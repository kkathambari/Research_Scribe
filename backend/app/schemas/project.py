from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

class ProjectBase(BaseModel):
    title: str = Field(..., description="Title or working topic of the research project")
    repository_url: Optional[str] = Field(None, description="GitHub repository URL")
    topic: Optional[str] = Field(None, description="Detailed domain topic")
    research_topic: Optional[str] = Field(None, description="Detailed research topic")
    research_problem: Optional[str] = Field(None, description="Problem statement")
    research_questions: Optional[str] = Field(None, description="Research questions / hypotheses")
    research_question: Optional[str] = Field(None, description="Primary research question")
    objectives: Optional[str] = Field(None, description="Specific research objectives")
    academic_discipline: Optional[str] = Field("Computer Science", description="Discipline")
    publication_type: Optional[str] = Field("Conference / Journal Article", description="Target format")
    target_publication: Optional[str] = Field(None, description="Target journal or conference")
    target_venue: Optional[str] = Field(None, description="Target journal or conference venue")
    citation_style: Optional[str] = Field("APA", description="APA, IEEE, Harvard, Vancouver, Chicago")
    generation_mode: Optional[str] = Field("automatic", description="automatic or guided")
    word_count_target: Optional[int] = Field(5000, description="Word count goal")

class ProjectCreate(ProjectBase):
    branch_or_tag: Optional[str] = Field("main", description="Branch, tag, or commit SHA")

class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    repository_url: Optional[str] = None
    topic: Optional[str] = None
    research_problem: Optional[str] = None
    research_questions: Optional[str] = None
    objectives: Optional[str] = None
    academic_discipline: Optional[str] = None
    publication_type: Optional[str] = None
    target_publication: Optional[str] = None
    target_venue: Optional[str] = None
    citation_style: Optional[str] = None
    generation_mode: Optional[str] = None
    word_count_target: Optional[int] = None

class ProjectResponse(ProjectBase):
    id: str
    user_id: Optional[str] = None
    status: Optional[str] = "created"
    created_at: datetime
    updated_at: datetime
    sources_count: Optional[int] = 0
    manuscript_id: Optional[str] = None
    repository_id: Optional[str] = None
    snapshot_id: Optional[str] = None

    class Config:
        from_attributes = True
