from typing import Optional, List
from pydantic import BaseModel, Field

class PolishRequest(BaseModel):
    text: str
    mode: str = Field("clarity", description="clarity, academic_tone, conciseness, coherence, sentence_variety")
    preserve_citations: bool = True

class DiffSegment(BaseModel):
    type: str # unchanged, added, removed
    text: str

class PolishResponse(BaseModel):
    original_text: str
    revised_text: str
    mode: str
    changes_summary: str
    diff_segments: List[DiffSegment] = []
