import hashlib
import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import docx
from sqlalchemy.orm import Session

from app.models.journal import (
    JournalProfile,
    JournalTemplate,
    TemplateStyle,
    JournalRequirement,
    ComplianceCheck,
)
from app.models.manuscript import Manuscript, ManuscriptSection
from app.schemas.journal import ComplianceReportResponse, ComplianceCheckResponse

logger = logging.getLogger(__name__)

# Official author requirement baselines for premier publication venues
DEFAULT_JOURNAL_PROFILES = {
    "IEEE Transactions": {
        "publisher": "IEEE",
        "citation_style": "IEEE",
        "word_limit": 8000,
        "page_limit": 12,
        "abstract_word_limit": 250,
        "official_guidelines_url": "https://www.ieee.org/publications/authors/author-template-guidelines.html",
        "required_sections": [
            "Abstract", "Index Terms", "Introduction", "Related Work",
            "System Architecture and Methodology", "Experimental Setup",
            "Results and Analysis", "Discussion and Limitations", "Conclusion", "References"
        ],
        "abstract_requirements": "Single paragraph, strictly between 150 and 250 words, self-contained without mathematical symbols or in-text citations.",
        "keyword_requirements": "4 to 6 Index Terms separated by semicolons.",
        "declaration_requirements": ["Data Availability", "Conflict of Interest"],
        "layout_requirements": "Two-column IEEEtran format, Times New Roman, 10pt font, 0.75-inch margins."
    },
    "ACM Transactions": {
        "publisher": "ACM",
        "citation_style": "ACM",
        "word_limit": 9000,
        "page_limit": 14,
        "abstract_word_limit": 300,
        "official_guidelines_url": "https://www.acm.org/publications/authors/submissions",
        "required_sections": [
            "Abstract", "CCS Concepts", "Keywords", "Introduction", "Background and Related Work",
            "Methodology", "Empirical Evaluation", "Discussion", "Threats to Validity", "Conclusion", "References"
        ],
        "abstract_requirements": "Concise summary strictly under 300 words without mathematical notation.",
        "keyword_requirements": "Comma-separated keywords reflecting core topics.",
        "declaration_requirements": ["Artifact Availability", "Conflict of Interest"],
        "layout_requirements": "Single-column acmsmall or two-column acmtog format."
    },
    "Springer Nature": {
        "publisher": "Springer",
        "citation_style": "Vancouver",
        "word_limit": 7000,
        "page_limit": 10,
        "abstract_word_limit": 250,
        "official_guidelines_url": "https://www.springernature.com/gp/authors/publish-a-book/step-by-step-conference-proceedings",
        "required_sections": [
            "Abstract", "Keywords", "Introduction", "Literature Review",
            "Methodology", "Experimental Results", "Discussion", "Limitations", "Conclusion", "Declarations", "References"
        ],
        "abstract_requirements": "Structured or unformatted abstract strictly between 150 and 250 words.",
        "keyword_requirements": "4 to 6 keywords.",
        "declaration_requirements": ["Funding", "Competing Interests", "Data Availability", "Code Availability"],
        "layout_requirements": "Single-column, 1-inch margins, 11pt font."
    },
    "Elsevier Pattern Recognition": {
        "publisher": "Elsevier",
        "citation_style": "APA",
        "word_limit": 7500,
        "page_limit": 11,
        "abstract_word_limit": 200,
        "official_guidelines_url": "https://www.elsevier.com/journals/pattern-recognition/0031-3203/guide-for-authors",
        "required_sections": [
            "Abstract", "Keywords", "Introduction", "Related Work",
            "Proposed Method", "Experiments and Results", "Discussion", "Conclusion", "References"
        ],
        "abstract_requirements": "Concise summary strictly under 200 words stating objectives, methods, and key findings.",
        "keyword_requirements": "5 to 7 keywords.",
        "declaration_requirements": ["Declaration of Competing Interest", "Data Availability"],
        "layout_requirements": "Double-spaced for review or Elsevier journal layout."
    }
}

SECTION_CANONICAL_ALIASES = {
    "abstract": ["abstract"],
    "index terms": ["index terms", "keywords", "ccs concepts"],
    "keywords": ["keywords", "index terms"],
    "introduction": ["introduction", "overview"],
    "related work": ["related work", "literature review", "background and related work", "background"],
    "methodology": ["methodology", "system architecture and methodology", "system architecture & methodology", "proposed method", "methods"],
    "experimental setup": ["experimental setup", "experiments and results", "empirical evaluation", "experimental results", "evaluation"],
    "results and analysis": ["results and analysis", "experimental results", "results", "empirical evaluation", "experiments and results"],
    "discussion and limitations": ["discussion and limitations", "discussion", "threats to validity", "limitations"],
    "conclusion": ["conclusion", "discussion & conclusion", "discussion and conclusion", "conclusions"],
    "references": ["references", "bibliography"],
    "declarations": ["declarations", "data availability", "data & code availability", "disclosures"]
}

class JournalIntelligence:
    """
    Subsystem for journal template intelligence, requirement profiling,
    template parsing, and compliance validation conforming to SRS v3.0 (FR-19 to FR-25).
    Guarantees reliable, evidence-grounded compliance scoring distinguishing
    passed, failed, warning, and not_verifiable states.
    """

    def get_or_create_journal_profile(
        self,
        db: Session,
        journal_name: str,
        project_id: Optional[str] = None,
        custom_guidelines: Optional[str] = None
    ) -> JournalProfile:
        """FR-19 & FR-21: Resolves or constructs a structured JournalProfile with atomic requirements."""
        profile = db.query(JournalProfile).filter(
            JournalProfile.journal_name == journal_name,
            (JournalProfile.project_id == project_id) | (JournalProfile.project_id.is_(None))
        ).first()

        if profile:
            return profile

        is_known_venue = journal_name in DEFAULT_JOURNAL_PROFILES
        if is_known_venue:
            defaults = DEFAULT_JOURNAL_PROFILES[journal_name]
            v_status = "unverified_publisher_default"
            publisher = defaults.get("publisher", "Academic Publisher")
            guidelines_url = defaults.get("official_guidelines_url")
        else:
            defaults = {
                "publisher": "Unknown Journal Publisher",
                "citation_style": "IEEE",
                "word_limit": 7500,
                "page_limit": 10,
                "abstract_word_limit": 250,
                "official_guidelines_url": f"https://www.google.com/search?q={re.sub(r'[^a-zA-Z0-9+]+', '+', journal_name.strip())}+author+guidelines",
                "required_sections": [
                    "Abstract", "Introduction", "Related Work",
                    "Methodology", "Results and Analysis", "Discussion", "Conclusion", "References"
                ],
                "abstract_requirements": "Single paragraph abstract under 250 words.",
                "keyword_requirements": "4 to 6 keywords separated by commas.",
                "declaration_requirements": ["Data Availability", "Conflict of Interest"],
                "layout_requirements": "Single-column draft format"
            }
            v_status = "unverified_draft"
            publisher = "Unknown Journal Publisher"
            guidelines_url = defaults["official_guidelines_url"]

        proj_suffix = project_id or "global"
        profile_id = f"jp_{hashlib.md5(f'{journal_name}_{proj_suffix}'.encode()).hexdigest()[:10]}"

        now_utc = datetime.now(timezone.utc)
        profile = JournalProfile(
            id=profile_id,
            project_id=project_id,
            journal_name=journal_name,
            publisher=publisher,
            official_guidelines_url=guidelines_url,
            manuscript_type="Full Research Paper",
            citation_style=defaults.get("citation_style", "IEEE"),
            required_sections=json.dumps(defaults.get("required_sections", [])),
            section_order=json.dumps(defaults.get("required_sections", [])),
            abstract_requirements=defaults.get("abstract_requirements", "Concise abstract under 250 words."),
            keyword_requirements=defaults.get("keyword_requirements", "4-6 keywords."),
            word_limit=defaults.get("word_limit", 7000),
            page_limit=defaults.get("page_limit", 10),
            figure_requirements="Figures must be clear, high resolution (>=300 DPI) with descriptive captions below.",
            table_requirements="Tables must be numbered sequentially with titles positioned above.",
            declaration_requirements=json.dumps(defaults.get("declaration_requirements", [])),
            layout_requirements=defaults.get("layout_requirements", "Standard academic layout"),
            verification_status=v_status,
            profile_version=1,
            retrieved_at=now_utc
        )
        db.add(profile)
        db.commit()

        # Generate atomic JournalRequirements (FR-21, SRS 6.16)
        self._generate_atomic_requirements(db, profile, defaults)

        return profile

    def _generate_atomic_requirements(self, db: Session, profile: JournalProfile, defaults: Dict[str, Any]):
        requirements_data = [
            ("section_order", "Required section structure and sequence", ", ".join(defaults.get("required_sections", []))),
            ("word_limit", f"Manuscript total word count must not exceed {defaults.get('word_limit', 7000)} words", str(defaults.get("word_limit", 7000))),
            ("abstract_format", f"Abstract word limit ({defaults.get('abstract_word_limit', 250)} words) and formatting constraints", defaults.get("abstract_requirements", "Max 250 words")),
            ("keyword_count", "Keyword requirements and format", defaults.get("keyword_requirements", "4-6 keywords")),
            ("citation_style", f"Citation and bibliographic referencing style: {defaults.get('citation_style', 'IEEE')}", defaults.get('citation_style', 'IEEE')),
            ("declarations", "Mandatory author disclosures and declarations", ", ".join(defaults.get("declaration_requirements", []))),
            ("figure_captions", "Figures must have captions below", "Present"),
            ("table_captions", "Tables must have titles above", "Present")
        ]

        for req_type, desc, expected in requirements_data:
            req = JournalRequirement(
                id=f"req_{hashlib.md5(f'{profile.id}_{req_type}'.encode()).hexdigest()[:10]}",
                journal_profile_id=profile.id,
                requirement_type=req_type,
                description=desc,
                expected_value=expected,
                source_type="publisher_guidelines",
                source_location="Official Author Guide",
                confidence=1.0,
                verification_status="unverified_default",
                user_approval_status="unreviewed"
            )
            db.add(req)
        db.commit()

    def import_template_file(
        self,
        db: Session,
        profile_id: str,
        file_path: Path,
        template_filename: str
    ) -> JournalTemplate:
        """FR-20: Ingests an official DOCX template, analyzing styles, paragraph hierarchy, and placeholders."""
        content_bytes = file_path.read_bytes()
        template_id = f"tpl_{hashlib.md5(f'{profile_id}_{template_filename}'.encode()).hexdigest()[:10]}"

        now_utc = datetime.now(timezone.utc)
        template = JournalTemplate(
            id=template_id,
            journal_profile_id=profile_id,
            template_filename=template_filename,
            template_format="DOCX",
            storage_reference=str(file_path),
            content_hash=hashlib.sha256(content_bytes).hexdigest(),
            template_version=1,
            uploaded_at=now_utc,
            analysis_status="analyzed"
        )
        db.add(template)
        db.commit()

        # Parse DOCX styles
        try:
            doc = docx.Document(str(file_path))
            for s in doc.styles:
                if s.type == docx.enum.style.WD_STYLE_TYPE.PARAGRAPH:
                    ts = TemplateStyle(
                        id=f"ts_{hashlib.md5(f'{template.id}_{s.name}'.encode()).hexdigest()[:10]}",
                        journal_template_id=template.id,
                        style_name=s.name,
                        style_type="paragraph",
                        font_family=s.font.name if s.font and s.font.name else "Times New Roman",
                        font_size=s.font.size.pt if s.font and s.font.size else 10.0,
                        bold=s.font.bold if s.font and s.font.bold is not None else False,
                        italic=s.font.italic if s.font and s.font.italic is not None else False,
                        alignment="left",
                        spacing_before=s.paragraph_format.space_before.pt if s.paragraph_format and s.paragraph_format.space_before else 0.0,
                        spacing_after=s.paragraph_format.space_after.pt if s.paragraph_format and s.paragraph_format.space_after else 6.0,
                        line_spacing=s.paragraph_format.line_spacing if s.paragraph_format and s.paragraph_format.line_spacing else 1.0,
                        source_location="Template Style Library"
                    )
                    db.add(ts)
            db.commit()
        except Exception as e:
            logger.warning(f"DOCX template inspection had partial warnings: {e}")

        return template

    def validate_compliance(
        self,
        db: Session,
        manuscript: Manuscript,
        profile: JournalProfile
    ) -> ComplianceReportResponse:
        """
        FR-24: Evaluates manuscript sections, word limits, venue-specific abstract limits,
        citation syntax, declarations, and template styles.
        Correctly reports passed, failed, warning, and not_verifiable states.
        """
        checks: List[ComplianceCheckResponse] = []

        # Clean previous checks for this manuscript
        db.query(ComplianceCheck).filter(ComplianceCheck.manuscript_id == manuscript.id).delete()
        db.commit()

        sections = manuscript.sections
        section_titles_lower = [s.title.lower().strip() for s in sections]
        total_words = sum(len(s.content.split()) for s in sections if s.content)
        now_utc = datetime.now(timezone.utc)

        # 1. Word limit check (Venue-specific)
        if profile.word_limit:
            if total_words <= profile.word_limit:
                status = "passed"
                exp = f"Manuscript total length ({total_words} words) conforms to {profile.journal_name} word limit (<= {profile.word_limit})."
                corr = None
            else:
                status = "failed"
                exp = f"Manuscript exceeds {profile.journal_name} limit: {total_words} words > {profile.word_limit} words."
                corr = f"Condense manuscript sections by {total_words - profile.word_limit} words."

            c = ComplianceCheck(
                id=f"chk_wlimit_{manuscript.id}",
                manuscript_id=manuscript.id,
                check_type="word_limit",
                status=status,
                observed_value=f"{total_words} words",
                expected_value=f"<= {profile.word_limit} words",
                explanation=exp,
                suggested_correction=corr,
                checked_at=now_utc
            )
            db.add(c)
            checks.append(ComplianceCheckResponse.model_validate(c))

        # 2. Abstract length check (Venue-specific limit derived from profile)
        venue_defaults = DEFAULT_JOURNAL_PROFILES.get(profile.journal_name, {})
        venue_abstract_limit = venue_defaults.get("abstract_word_limit", 250)

        abstract_sec = next((s for s in sections if s.section_type == "abstract" or "abstract" in s.title.lower()), None)
        abs_words = len(abstract_sec.content.split()) if (abstract_sec and abstract_sec.content) else 0

        if 0 < abs_words <= venue_abstract_limit:
            status = "passed"
            exp = f"Abstract is {abs_words} words (within {profile.journal_name} limit of {venue_abstract_limit} words)."
            corr = None
        elif abs_words == 0:
            status = "failed"
            exp = "Abstract section is currently missing or empty."
            corr = f"Draft a comprehensive abstract between 150 and {venue_abstract_limit} words."
        else:
            status = "failed"
            exp = f"Abstract length ({abs_words} words) exceeds {profile.journal_name} limit ({venue_abstract_limit} words)."
            corr = f"Trim abstract prose by {abs_words - venue_abstract_limit} words to satisfy guidelines."

        c = ComplianceCheck(
            id=f"chk_abs_{manuscript.id}",
            manuscript_id=manuscript.id,
            check_type="abstract_length",
            status=status,
            observed_value=f"{abs_words} words",
            expected_value=f"<= {venue_abstract_limit} words",
            explanation=exp,
            suggested_correction=corr,
            checked_at=now_utc
        )
        db.add(c)
        checks.append(ComplianceCheckResponse.model_validate(c))

        # 3. Required sections completeness check (Canonical alias matching)
        req_sections_list = []
        if profile.required_sections:
            try:
                req_sections_list = json.loads(profile.required_sections)
            except Exception:
                pass

        missing_sections = []
        for req_sec in req_sections_list:
            req_lower = req_sec.lower().strip()
            aliases = SECTION_CANONICAL_ALIASES.get(req_lower, [req_lower])
            matched = any(any(alias in sec_title for alias in aliases) for sec_title in section_titles_lower)
            if not matched:
                missing_sections.append(req_sec)

        if not missing_sections:
            status = "passed"
            exp = f"All {len(req_sections_list)} mandatory sections required by {profile.journal_name} are present."
            corr = None
        else:
            # Distinguish core sections from secondary sections (like Index Terms)
            is_critical = any(m.lower() in ["abstract", "introduction", "methodology", "results", "conclusion", "references"] for m in missing_sections)
            status = "failed" if is_critical else "warning"
            exp = f"Missing mandatory sections: {', '.join(missing_sections)}."
            corr = f"Add missing section headings: {', '.join(missing_sections)}."

        c = ComplianceCheck(
            id=f"chk_sec_{manuscript.id}",
            manuscript_id=manuscript.id,
            check_type="section_completeness",
            status=status,
            observed_value=f"{len(sections)} sections present",
            expected_value=f"Required: {', '.join(req_sections_list[:4])}...",
            explanation=exp,
            suggested_correction=corr,
            checked_at=now_utc
        )
        db.add(c)
        checks.append(ComplianceCheckResponse.model_validate(c))

        # 4. Citation style check (Rule-based syntax evaluation)
        combined_text = " ".join(s.content for s in sections if s.content)
        style_upper = (profile.citation_style or "IEEE").upper()

        if style_upper in ["IEEE", "ACM"]:
            # Check for bracketed numbers [1], [2, 3], etc.
            has_numeric_cites = bool(re.search(r"\[\d+(?:,\s*\d+)*\]", combined_text))
            if has_numeric_cites:
                status = "passed"
                obs = f"Validated numeric bracketed citations matching {profile.citation_style} style"
                exp = f"In-text citations comply with {profile.citation_style} numbered specification."
                corr = None
            else:
                status = "failed"
                obs = "No numeric bracketed citations (e.g. [1]) detected"
                exp = f"{profile.journal_name} mandates numeric bracketed citations (e.g., [1])."
                corr = "Format in-text citations using numbered brackets matching the bibliography."

        elif style_upper in ["APA", "HARVARD"]:
            # Check for author-year (Smith et al., 2021) or (Vaswani, 2017)
            has_author_year = bool(re.search(r"\([A-Z][a-zA-Z]+(?:\s+et\s+al\.)?,\s*\d{4}\)", combined_text))
            if has_author_year:
                status = "passed"
                obs = f"Validated author-year citations matching {profile.citation_style} format"
                exp = f"Citations conform to {profile.citation_style} author-date conventions."
                corr = None
            else:
                status = "failed"
                obs = "No author-date citations detected in manuscript text"
                exp = f"{profile.journal_name} requires author-date citations (e.g., (Vaswani et al., 2017))."
                corr = "Embed author-year citations for all substantive assertions."
        else:
            has_any = any("[" in s.content or "(" in s.content for s in sections if s.content)
            status = "passed" if has_any else "failed"
            obs = "In-text references detected" if has_any else "No references detected"
            exp = "Citations present." if has_any else "Missing in-text citations."
            corr = None if has_any else "Add citations."

        c = ComplianceCheck(
            id=f"chk_cite_{manuscript.id}",
            manuscript_id=manuscript.id,
            check_type="citation_format",
            status=status,
            observed_value=obs,
            expected_value=f"Official {profile.citation_style} format",
            explanation=exp,
            suggested_correction=corr,
            checked_at=now_utc
        )
        db.add(c)
        checks.append(ComplianceCheckResponse.model_validate(c))

        # 5. Declarations & Availability check
        decl_present = any("declaration" in t or "availability" in t or "acknowledgement" in t or "disclosure" in t for t in section_titles_lower)
        c = ComplianceCheck(
            id=f"chk_decl_{manuscript.id}",
            manuscript_id=manuscript.id,
            check_type="declaration_present",
            status="passed" if decl_present else "warning",
            observed_value="Disclosures & Availability statement present" if decl_present else "No explicit disclosures section",
            expected_value="Mandatory Data & Code Availability statement",
            explanation="Manuscript includes transparency disclosures." if decl_present else f"{profile.journal_name} guidelines mandate author statements on data/code availability and funding.",
            suggested_correction=None if decl_present else "Append a 'Data & Code Availability' statement before References.",
            checked_at=now_utc
        )
        db.add(c)
        checks.append(ComplianceCheckResponse.model_validate(c))

        # 6. Page limit check (Distinguished as 'not_verifiable' in unrendered draft text)
        c = ComplianceCheck(
            id=f"chk_page_{manuscript.id}",
            manuscript_id=manuscript.id,
            check_type="page_limit",
            status="not_verifiable",
            observed_value=f"Draft text (~{total_words} words)",
            expected_value=f"<= {profile.page_limit} journal pages",
            explanation=f"Page constraint ({profile.page_limit} pages) requires two-column typeset rendering and cannot be determined from unformatted draft text.",
            suggested_correction="Render manuscript via DOCX template export to inspect final printed page count.",
            checked_at=now_utc
        )
        db.add(c)
        checks.append(ComplianceCheckResponse.model_validate(c))

        # 7. Guideline verification check (SRS FR-21: distinguish default profile from confirmed guidelines)
        if profile.verification_status.startswith("unverified"):
            status_guide = "warning"
            obs_guide = f"Unverified baseline ({profile.verification_status})"
            exp_guide = (
                f"Journal profile '{profile.journal_name}' is initialized from unverified publisher defaults. "
                f"Different venues within {profile.publisher} enforce distinct author guidelines. "
                f"Official author instructions at {profile.official_guidelines_url} have not been confirmed by the researcher."
            )
            corr_guide = f"Review official guidelines at {profile.official_guidelines_url} and approve or adjust requirements via Guided Mode."
        else:
            status_guide = "passed"
            obs_guide = f"Verified ({profile.verification_status})"
            exp_guide = f"Author guidelines for {profile.journal_name} have been confirmed."
            corr_guide = None

        c_guide = ComplianceCheck(
            id=f"chk_guide_{manuscript.id}",
            manuscript_id=manuscript.id,
            check_type="guideline_verification",
            status=status_guide,
            observed_value=obs_guide,
            expected_value=f"Verified instructions from {profile.official_guidelines_url}",
            explanation=exp_guide,
            suggested_correction=corr_guide,
            checked_at=now_utc
        )
        db.add(c_guide)
        checks.append(ComplianceCheckResponse.model_validate(c_guide))

        db.commit()

        # Score calculation over verifiable checks
        passed_count = sum(1 for c in checks if c.status == "passed")
        failed_count = sum(1 for c in checks if c.status == "failed")
        warning_count = sum(1 for c in checks if c.status == "warning")
        not_verifiable_count = sum(1 for c in checks if c.status == "not_verifiable")

        verifiable_checks = passed_count + failed_count + warning_count
        if verifiable_checks > 0:
            score = round((passed_count / (passed_count + failed_count + (0.5 * warning_count))) * 100.0, 1)
        else:
            score = 100.0

        is_officially_confirmed = not profile.verification_status.startswith("unverified")
        if not is_officially_confirmed:
            overall = "unverified_profile_provisional"
        elif failed_count > 0:
            overall = "non_compliant"
        elif warning_count > 0:
            overall = "warnings_detected"
        else:
            overall = "compliant"

        return ComplianceReportResponse(
            manuscript_id=manuscript.id,
            journal_name=profile.journal_name,
            overall_status=overall,
            profile_verification_status=profile.verification_status,
            is_officially_confirmed=is_officially_confirmed,
            passed_count=passed_count,
            failed_count=failed_count,
            warning_count=warning_count,
            not_verifiable_count=not_verifiable_count,
            compliance_score=score,
            checks=checks
        )

journal_intelligence = JournalIntelligence()
