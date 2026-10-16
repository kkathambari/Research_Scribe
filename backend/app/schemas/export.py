from typing import Optional, List
from pydantic import BaseModel, Field

class ExportRequest(BaseModel):
    manuscript_id: str
    export_format: str = Field("docx", description="docx, pdf, markdown, bibtex")
    citation_style: Optional[str] = Field("IEEE", description="IEEE, APA, Harvard, Vancouver, Chicago")
    include_verification_appendix: bool = False
    include_compliance_report: bool = False
    template_id: Optional[str] = None
    block_on_critical_errors: bool = False

class ExportResponse(BaseModel):
    download_url: str
    filename: str
    format: str
    citation_style: str
    unresolved_warnings_count: int = 0
    template_applied: bool = False
    critical_errors: Optional[List[str]] = []
