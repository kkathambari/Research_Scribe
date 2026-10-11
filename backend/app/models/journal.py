from datetime import datetime
from sqlalchemy import Column, String, DateTime, Integer, Text, ForeignKey, Boolean, Float
from sqlalchemy.orm import relationship
from app.db.base import Base

class JournalProfile(Base):
    __tablename__ = "journal_profiles"

    id = Column(String, primary_key=True, index=True)
    project_id = Column(String, ForeignKey("projects.id"), nullable=True, index=True)
    journal_name = Column(String, nullable=False)
    publisher = Column(String, nullable=True)  # IEEE, ACM, Springer, Elsevier, Nature, PLOS, etc.
    official_guidelines_url = Column(String, nullable=True)
    manuscript_type = Column(String, default="Full Research Paper")  # Full Research Paper, Short Paper, Survey
    citation_style = Column(String, default="IEEE")  # IEEE, APA, Harvard, Nature, Vancouver
    required_sections = Column(Text, nullable=True)  # JSON list of required section titles/types
    section_order = Column(Text, nullable=True)  # JSON ordered list of section types
    abstract_requirements = Column(Text, nullable=True)  # e.g., max 250 words, structured (Background/Methods/Results/Conclusion)
    keyword_requirements = Column(Text, nullable=True)  # e.g., 4-6 keywords, comma separated
    word_limit = Column(Integer, nullable=True)  # max manuscript words
    page_limit = Column(Integer, nullable=True)
    figure_requirements = Column(Text, nullable=True)  # e.g., 300 DPI, TIFF or EPS or PNG, numbered with captions below
    table_requirements = Column(Text, nullable=True)  # e.g., numbered with captions above, three-line table format
    equation_requirements = Column(Text, nullable=True)  # e.g., numbered right-aligned (1)
    declaration_requirements = Column(Text, nullable=True)  # Conflict of Interest, Data Availability, Funding
    layout_requirements = Column(Text, nullable=True)  # Two-column, single-column, 1-inch margins
    verification_status = Column(String, default="approved")  # extracted, user_reviewed, approved
    profile_version = Column(Integer, default=1)
    retrieved_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="journal_profiles")
    templates = relationship("JournalTemplate", back_populates="journal_profile", cascade="all, delete-orphan")
    requirements = relationship("JournalRequirement", back_populates="journal_profile", cascade="all, delete-orphan")
    manuscripts = relationship("Manuscript", back_populates="journal_profile")


class JournalTemplate(Base):
    __tablename__ = "journal_templates"

    id = Column(String, primary_key=True, index=True)
    journal_profile_id = Column(String, ForeignKey("journal_profiles.id"), nullable=False, index=True)
    template_filename = Column(String, nullable=False)
    template_format = Column(String, default="DOCX")  # DOCX, DOC
    storage_reference = Column(String, nullable=False)  # local file path
    content_hash = Column(String, nullable=True)
    template_version = Column(Integer, default=1)
    source_url = Column(String, nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    analysis_status = Column(String, default="analyzed")  # uploaded, analyzed, failed

    journal_profile = relationship("JournalProfile", back_populates="templates")
    styles = relationship("TemplateStyle", back_populates="template", cascade="all, delete-orphan")
    manuscripts = relationship("Manuscript", back_populates="journal_template")


class TemplateStyle(Base):
    __tablename__ = "template_styles"

    id = Column(String, primary_key=True, index=True)
    journal_template_id = Column(String, ForeignKey("journal_templates.id"), nullable=False, index=True)
    style_name = Column(String, nullable=False)  # e.g. "Title", "Heading 1", "Normal", "Affiliation"
    style_type = Column(String, default="paragraph")  # paragraph, character, table
    font_family = Column(String, nullable=True)  # e.g. "Times New Roman", "Calibri"
    font_size = Column(Float, nullable=True)  # e.g. 10.0, 12.0, 24.0
    bold = Column(Boolean, default=False)
    italic = Column(Boolean, default=False)
    alignment = Column(String, nullable=True)  # left, center, right, justify
    spacing_before = Column(Float, nullable=True)
    spacing_after = Column(Float, nullable=True)
    line_spacing = Column(Float, nullable=True)
    numbering_rules = Column(Text, nullable=True)
    section_properties = Column(Text, nullable=True)  # margins, columns, headers
    source_location = Column(String, nullable=True)

    template = relationship("JournalTemplate", back_populates="styles")


class JournalRequirement(Base):
    __tablename__ = "journal_requirements"

    id = Column(String, primary_key=True, index=True)
    journal_profile_id = Column(String, ForeignKey("journal_profiles.id"), nullable=False, index=True)
    requirement_type = Column(String, nullable=False)  # section_order, word_limit, abstract_format, keyword_count, citation_style, declarations, tables, figures
    description = Column(Text, nullable=False)
    expected_value = Column(Text, nullable=True)
    source_type = Column(String, default="template")  # template, author_guidelines, manual_input
    source_location = Column(String, nullable=True)
    confidence = Column(Float, default=1.0)
    verification_status = Column(String, default="confirmed")  # explicit, inferred, unverified
    user_approval_status = Column(String, default="approved")  # pending, approved, modified, rejected

    journal_profile = relationship("JournalProfile", back_populates="requirements")
    compliance_checks = relationship("ComplianceCheck", back_populates="requirement")


class ComplianceCheck(Base):
    __tablename__ = "compliance_checks"

    id = Column(String, primary_key=True, index=True)
    manuscript_id = Column(String, ForeignKey("manuscripts.id"), nullable=False, index=True)
    journal_requirement_id = Column(String, ForeignKey("journal_requirements.id"), nullable=True, index=True)
    check_type = Column(String, nullable=False)  # section_completeness, word_limit, abstract_length, keyword_count, citation_format, declaration_present, style_adherence
    status = Column(String, default="passed")  # passed, failed, warning, not_verifiable
    observed_value = Column(Text, nullable=True)
    expected_value = Column(Text, nullable=True)
    explanation = Column(Text, nullable=True)
    suggested_correction = Column(Text, nullable=True)
    checked_at = Column(DateTime, default=datetime.utcnow)

    manuscript = relationship("Manuscript", back_populates="compliance_checks")
    requirement = relationship("JournalRequirement", back_populates="compliance_checks")
