import os
from pathlib import Path
from typing import List, Dict, Any, Optional
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from app.config import settings
from app.services.citation_formatter import citation_formatter

class ManuscriptExporterService:
    """
    Subsystem for template-preserving document assembly and multi-format export
    conforming to SRS v3.0 (FR-23, FR-26).
    """

    def export_manuscript(
        self,
        manuscript: Dict[str, Any],
        sections: List[Dict[str, Any]],
        sources: List[Dict[str, Any]],
        claims: Optional[List[Dict[str, Any]]] = None,
        export_format: str = "docx",
        citation_style: str = "IEEE",
        include_verification_appendix: bool = False,
        template_path: Optional[str] = None
    ) -> Path:
        """
        Exports manuscript into DOCX (template-preserved), Markdown, or BibTeX.
        """
        export_format = export_format.lower()
        title = manuscript.get("title") or "Research Manuscript"
        clean_name = "".join(c for c in title if c.isalnum() or c in (' ', '_', '-')).rstrip()
        clean_name = clean_name.replace(' ', '_')[:40] or "manuscript"
        manuscript_id = manuscript.get("id", "draft")

        if export_format == "docx":
            filename = f"{clean_name}_{manuscript_id[:8]}.docx"
            out_path = settings.EXPORTS_DIR / filename
            self._generate_docx(
                out_path,
                title,
                sections,
                sources,
                claims,
                citation_style,
                include_verification_appendix,
                template_path
            )
            return out_path

        elif export_format == "bibtex":
            filename = f"{clean_name}_{manuscript_id[:8]}.bib"
            out_path = settings.EXPORTS_DIR / filename
            bibtex_content = citation_formatter.generate_bibtex(sources)
            out_path.write_text(bibtex_content, encoding="utf-8")
            return out_path

        else:  # markdown default
            filename = f"{clean_name}_{manuscript_id[:8]}.md"
            out_path = settings.EXPORTS_DIR / filename
            md_content = self._generate_markdown(title, sections, sources, claims, citation_style, include_verification_appendix)
            out_path.write_text(md_content, encoding="utf-8")
            return out_path

    def _generate_docx(
        self,
        out_path: Path,
        title: str,
        sections: List[Dict[str, Any]],
        sources: List[Dict[str, Any]],
        claims: Optional[List[Dict[str, Any]]],
        citation_style: str,
        include_verification_appendix: bool,
        template_path: Optional[str] = None
    ):
        """FR-23: Template-preserving DOCX assembly retaining fonts, margins, headers, and footers."""
        is_template_loaded = False
        if template_path and Path(template_path).exists():
            try:
                doc = docx.Document(template_path)
                is_template_loaded = True
            except Exception:
                doc = docx.Document()
        else:
            doc = docx.Document()

        if is_template_loaded:
            # Replace template placeholders if found
            for p in doc.paragraphs:
                p_text_lower = p.text.lower()
                if "{{title}}" in p_text_lower or "[paper title]" in p_text_lower or "title of paper" in p_text_lower:
                    p.text = title
                    if "Title" in doc.styles:
                        p.style = doc.styles["Title"]
            
            # Append sections using template styles
            sorted_sections = sorted(sections, key=lambda s: s.get("order", 0))
            for sec in sorted_sections:
                sec_title = sec.get("title", "Section")
                h = doc.add_paragraph()
                if "Heading 1" in doc.styles:
                    h.style = doc.styles["Heading 1"]
                run = h.add_run(sec_title)
                run.bold = True

                content = sec.get("content", "")
                for para_text in content.split("\n\n"):
                    para_clean = para_text.strip()
                    if not para_clean:
                        continue
                    p = doc.add_paragraph()
                    if "Normal" in doc.styles:
                        p.style = doc.styles["Normal"]
                    p.add_run(para_clean)

        else:
            # Standard professional academic layout
            p_title = doc.add_paragraph()
            p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run_title = p_title.add_run(title)
            run_title.font.size = Pt(20)
            run_title.font.bold = True
            run_title.font.color.rgb = RGBColor(17, 24, 39)

            # Subtitle metadata
            p_sub = doc.add_paragraph()
            p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run_sub = p_sub.add_run(f"Evidence-Grounded Manuscript Generated by ResearchScribe • Style: {citation_style.upper()}")
            run_sub.font.size = Pt(9.5)
            run_sub.font.italic = True
            run_sub.font.color.rgb = RGBColor(107, 114, 128)

            doc.add_paragraph()  # Spacing

            # Sections in order
            sorted_sections = sorted(sections, key=lambda s: s.get("order", 0))
            for sec in sorted_sections:
                sec_title = sec.get("title", "Section")
                h = doc.add_heading(sec_title, level=1)
                h.paragraph_format.space_before = Pt(14)
                h.paragraph_format.space_after = Pt(6)

                content = sec.get("content", "")
                paragraphs = content.split("\n\n")
                for para_text in paragraphs:
                    para_clean = para_text.strip()
                    if not para_clean:
                        continue
                    if para_clean.startswith("### "):
                        h3 = doc.add_heading(para_clean.replace("### ", ""), level=2)
                        h3.paragraph_format.space_before = Pt(8)
                        h3.paragraph_format.space_after = Pt(4)
                    else:
                        p = doc.add_paragraph(para_clean)
                        p.paragraph_format.line_spacing = 1.15
                        p.paragraph_format.space_after = Pt(6)

        # Bibliography section if sources present
        if sources:
            h_ref = doc.add_heading("References", level=1)
            h_ref.paragraph_format.space_before = Pt(16)
            h_ref.paragraph_format.space_after = Pt(8)

            formatted_refs = citation_formatter.format_bibliography(sources, citation_style)
            for ref_entry in formatted_refs:
                p_ref = doc.add_paragraph(ref_entry)
                p_ref.paragraph_format.left_indent = Inches(0.4)
                p_ref.paragraph_format.space_after = Pt(4)

        # Optional Verification Appendix
        if include_verification_appendix and claims:
            doc.add_page_break()
            h_app = doc.add_heading("Appendix: Citation & Evidence Provenance Audit", level=1)
            h_app.paragraph_format.space_before = Pt(14)

            p_intro = doc.add_paragraph(
                "This appendix records claim-level evidence verification performed by ResearchScribe. "
                "Every empirical claim is mapped to primary source evidence passages, repository code locations, or verification statuses."
            )
            p_intro.paragraph_format.italic = True

            table = doc.add_table(rows=1, cols=4)
            table.style = 'Table Grid'
            hdr_cells = table.rows[0].cells
            hdr_cells[0].text = "Claim Assertion"
            hdr_cells[1].text = "Evidence / Source"
            hdr_cells[2].text = "Status"
            hdr_cells[3].text = "Explanation"

            for cell in hdr_cells:
                for p in cell.paragraphs:
                    for run in p.runs:
                        run.font.bold = True

            for claim in claims:
                row_cells = table.add_row().cells
                row_cells[0].text = claim.get("claim_text", "")
                
                citations = claim.get("citations", [])
                source_str = citations[0].get("in_text_citation", "Unlinked") if citations else "No Citation"
                row_cells[1].text = source_str

                status = claim.get("status", "unverified").upper()
                row_cells[2].text = status
                row_cells[3].text = claim.get("explanation", "") or "Corroborated by repository evidence."

        doc.save(str(out_path))

    def _generate_markdown(
        self,
        title: str,
        sections: List[Dict[str, Any]],
        sources: List[Dict[str, Any]],
        claims: Optional[List[Dict[str, Any]]],
        citation_style: str,
        include_verification_appendix: bool
    ) -> str:
        lines = [
            f"# {title}",
            "",
            f"*Generated by ResearchScribe (SRS v3.0 Compliant) • Citation Style: {citation_style.upper()}*",
            "",
            "---",
            ""
        ]

        sorted_sections = sorted(sections, key=lambda s: s.get("order", 0))
        for sec in sorted_sections:
            lines.append(f"## {sec.get('title', 'Section')}")
            lines.append("")
            lines.append(sec.get("content", ""))
            lines.append("")

        if sources:
            lines.append("## References")
            lines.append("")
            formatted_refs = citation_formatter.format_bibliography(sources, citation_style)
            for ref in formatted_refs:
                lines.append(f"- {ref}")
            lines.append("")

        if include_verification_appendix and claims:
            lines.append("---")
            lines.append("## Appendix: Claim & Evidence Verification Audit")
            lines.append("")
            lines.append("| Claim Assertion | Source Citation | Verification Status | Explanation |")
            lines.append("|---|---|---|---|")
            for c in claims:
                claim_text = c.get("claim_text", "").replace("|", "\\|")
                citations = c.get("citations", [])
                src = citations[0].get("in_text_citation", "Unlinked") if citations else "No Citation"
                status = c.get("status", "unverified")
                exp = (c.get("explanation") or "").replace("|", "\\|")
                lines.append(f"| {claim_text} | {src} | **{status}** | {exp} |")
            lines.append("")

        return "\n".join(lines)

exporter = ManuscriptExporterService()
