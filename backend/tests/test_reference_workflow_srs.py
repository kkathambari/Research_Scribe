import io
import pytest
from fastapi.testclient import TestClient
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from pypdf import PdfWriter

from app.services.document_parser import document_parser
from app.services.retrieval import retrieval_service
from app.services.evidence_extractor import evidence_extractor
from app.services.citation_formatter import citation_formatter
from app.services.verification_engine import verification_engine
from app.models.source import Source, Document
from app.models.manuscript import Manuscript, ManuscriptSection


def make_pdf_bytes(pages_text: list[str]) -> bytes:
    """Helper to generate a well-formed PDF with text across multiple pages."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    for p_num, text in enumerate(pages_text, 1):
        c.drawString(72, 720, f"Page {p_num}")
        # Draw multiple lines
        y = 700
        for line in text.split("\n"):
            c.drawString(72, y, line[:90])
            y -= 18
        c.showPage()
    c.save()
    buf.seek(0)
    return buf.getvalue()


def make_blank_pdf_bytes(num_pages: int = 1) -> bytes:
    """Helper to generate a blank PDF with no extractable text layer (simulates scanned paper)."""
    writer = PdfWriter()
    for _ in range(num_pages):
        writer.add_blank_page(width=612, height=792)
    buf = io.BytesIO()
    writer.write(buf)
    buf.seek(0)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Acceptance Criterion 1: Multiple Reference PDF Upload & Status Reporting
# ---------------------------------------------------------------------------
def test_ac01_batch_pdf_upload_and_status(client: TestClient):
    """
    AC 1: A user can upload multiple reference PDFs and see the processing status of each file.
    """
    proj_resp = client.post("/api/v1/projects", json={"title": "AC01 Multi-Upload Project"})
    assert proj_resp.status_code == 200
    proj_id = proj_resp.json()["id"]

    pdf1 = make_pdf_bytes(["Introduction to Cross-Attention\nProblem: High latency in dense attention.\nMethod: Sparse routing."])
    pdf2 = make_pdf_bytes(["Empirical Evaluation of Neural Transformers\nFindings: Achieves 94.2% accuracy.\nLimitation: Memory complexity."])

    files = [
        ("files", ("paper1.pdf", pdf1, "application/pdf")),
        ("files", ("paper2.pdf", pdf2, "application/pdf")),
    ]
    resp = client.post("/api/v1/sources/upload-batch", data={"project_id": proj_id}, files=files)
    assert resp.status_code == 200
    data = resp.json()

    assert data["total_files"] == 2
    assert data["processed_count"] == 2
    assert len(data["results"]) == 2

    for item in data["results"]:
        assert item["status"] in ("processed", "success")
        assert (item.get("page_count") or 0) >= 1
        assert item["source_id"] is not None
        assert item["citation_key"] is not None

    # Verify sources exist in project
    sources_resp = client.get(f"/api/v1/sources?project_id={proj_id}")
    assert sources_resp.status_code == 200
    assert len(sources_resp.json()) == 2


# ---------------------------------------------------------------------------
# Acceptance Criterion 2: Metadata Matching & Mismatch Flagging
# ---------------------------------------------------------------------------
def test_ac02_metadata_matching_and_mismatch_flagging():
    """
    AC 2: A PDF with a DOI is matched to the correct bibliographic record, and metadata mismatches are flagged.
    """
    # 1. Test PDF metadata extraction with embedded DOI
    pdf_with_doi = make_pdf_bytes([
        "Deep Residual Learning for Image Recognition\nKaiming He, Xiangyu Zhang, Shaoqing Ren, Jian Sun\nDOI: 10.1109/CVPR.2016.90\nPublished in 2016."
    ])
    extracted_meta = document_parser.extract_pdf_metadata(pdf_with_doi)
    assert extracted_meta.get("doi") == "10.1109/CVPR.2016.90"

    # 2. Test metadata comparison flagging mismatches
    extracted = {
        "title": "Deep Residual Learning for Image Recognition",
        "authors": "Kaiming He",
        "year": 2016,
        "doi": "10.1109/CVPR.2016.90"
    }
    # Bibliographic record with divergent year and divergent DOI
    mismatched_bib = {
        "title": "Deep Residual Learning for Image Recognition",
        "authors": "Kaiming He",
        "year": 2021,
        "doi": "10.1145/9999999.8888888"
    }
    comp_result = retrieval_service.compare_metadata(extracted, mismatched_bib)
    assert comp_result["is_match"] is False
    mismatches = comp_result["mismatches"]
    assert len(mismatches) >= 2
    assert any("DOI mismatch" in m for m in mismatches)
    assert any("year" in m.lower() for m in mismatches)


# ---------------------------------------------------------------------------
# Acceptance Criterion 3: Duplicate Upload Handling
# ---------------------------------------------------------------------------
def test_ac03_duplicate_upload_prevention(client: TestClient):
    """
    AC 3: Uploading the same paper twice does not silently create duplicate source and reference records.
    """
    proj_resp = client.post("/api/v1/projects", json={"title": "AC03 Duplicate Test"})
    proj_id = proj_resp.json()["id"]

    pdf = make_pdf_bytes(["A Unique Paper on Distributed Training Systems\nAuthor: Jane Doe\nMethod: Sharded data parallelism."])

    # First upload
    files1 = [("files", ("unique_paper.pdf", pdf, "application/pdf"))]
    resp1 = client.post("/api/v1/sources/upload-batch", data={"project_id": proj_id}, files=files1)
    assert resp1.status_code == 200
    assert resp1.json()["processed_count"] == 1

    # Second upload of the identical paper
    files2 = [("files", ("unique_paper.pdf", pdf, "application/pdf"))]
    resp2 = client.post("/api/v1/sources/upload-batch", data={"project_id": proj_id}, files=files2)
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["duplicates_count"] == 1
    assert data2["results"][0]["status"] == "duplicate_detected"
    assert "already exists" in (data2["results"][0].get("warning") or data2["results"][0].get("error") or "")

    # Ensure project still has exactly 1 source, not 2
    sources_resp = client.get(f"/api/v1/sources?project_id={proj_id}")
    assert len(sources_resp.json()) == 1


# ---------------------------------------------------------------------------
# Acceptance Criterion 4: Text & Page Number Extraction
# ---------------------------------------------------------------------------
def test_ac04_text_and_page_number_extraction():
    """
    AC 4: Text and page numbers are extracted correctly from a text-based PDF.
    """
    p1_content = "1. Introduction and Objectives\nThe objective is to reduce parameter count in modern transformer architectures."
    p2_content = "2. Experimental Results and Metrics\nThe model achieved a BLEU score of 34.5 on the WMT-14 benchmark dataset."
    p3_content = "3. Known Limitations and Discussion\nThis method requires substantial GPU memory during sequence generation."

    pdf_bytes = make_pdf_bytes([p1_content, p2_content, p3_content])
    parsed = document_parser.parse_pdf(pdf_bytes)

    assert parsed["page_count"] == 3
    assert len(parsed["pages"]) == 3
    assert parsed["pages"][0]["page_number"] == 1
    assert "reduce parameter count" in parsed["pages"][0]["text"]
    assert parsed["pages"][1]["page_number"] == 2
    assert "BLEU score of 34.5" in parsed["pages"][1]["text"]
    assert parsed["pages"][2]["page_number"] == 3
    assert "substantial GPU memory" in parsed["pages"][2]["text"]


# ---------------------------------------------------------------------------
# Acceptance Criterion 5: Scanned PDF / OCR Warning Handling
# ---------------------------------------------------------------------------
def test_ac05_scanned_pdf_explicit_ocr_warning():
    """
    AC 5: A scanned PDF is identified and explicitly marked as requiring OCR without silent false success.
    """
    blank_pdf = make_blank_pdf_bytes(num_pages=2)
    parsed = document_parser.parse_pdf(blank_pdf)

    assert parsed["page_count"] == 2
    assert parsed["ocr_required"] is True
    # Must explicitly state OCR requirement
    assert "OCR processing required" in parsed["extracted_text"]
    assert any("OCR processing required" in w for w in parsed["warnings"])


# ---------------------------------------------------------------------------
# Acceptance Criterion 6: Evidence Traceability to Paper & Page
# ---------------------------------------------------------------------------
def test_ac06_evidence_traceability():
    """
    AC 6: Extracted findings, limitations, and objectives link to the correct paper and supporting page.
    """
    text_p1 = "Problem Formulation: Current neural networks suffer from catastrophic forgetting.\nMethod: Elastic weight consolidation."
    text_p2 = "Experimental Findings: The retention rate increased by 28.4% on Permuted MNIST.\nLimitation: Computation of the Fisher matrix scales quadratically."

    items = evidence_extractor.extract_from_text(
        text=f"{text_p1}\n{text_p2}",
        source_id="src-999",
        page_number=2,
        section_name="Results & Discussion"
    )

    assert len(items) >= 2
    categories = [it.category for it in items]
    assert "finding" in categories or "limitation" in categories or "problem" in categories

    for it in items:
        assert it.source_id == "src-999"
        assert it.page_number == 2
        assert len(it.passage_text) > 0
        assert it.is_direct_quotation is True


# ---------------------------------------------------------------------------
# Acceptance Criterion 7: Literature Review Generation Grounded in Selected Papers
# ---------------------------------------------------------------------------
def test_ac07_literature_review_generation_selected_sources(client: TestClient):
    """
    AC 7: A generated review uses the selected papers and includes traceable citations for substantive claims.
    """
    proj_resp = client.post("/api/v1/projects", json={"title": "AC07 Lit Review Project"})
    proj_id = proj_resp.json()["id"]
    ms_id = proj_resp.json()["manuscript_id"]

    # Create two verified sources
    s1 = client.post("/api/v1/sources", json={
        "project_id": proj_id,
        "title": "Self-Supervised Masked Autoencoders",
        "authors": "He, K., Chen, X., Xie, S.",
        "year": 2022,
        "venue": "CVPR",
        "citation_key": "He2022",
        "abstract": "We show that masked autoencoders are scalable vision learners. Method: masking random patches."
    }).json()

    s2 = client.post("/api/v1/sources", json={
        "project_id": proj_id,
        "title": "Vision Transformer Scaling Laws",
        "authors": "Zhai, X., Kolesnikov, A.",
        "year": 2022,
        "venue": "NeurIPS",
        "citation_key": "Zhai2022",
        "abstract": "Findings: Scaling parameters and compute yields power-law performance gains across datasets."
    }).json()

    # Create a third source that should NOT be selected
    s3 = client.post("/api/v1/sources", json={
        "project_id": proj_id,
        "title": "Unrelated Quantum Computing Survey",
        "authors": "Nielsen, M.",
        "year": 2020,
        "venue": "Nature Physics",
        "citation_key": "Nielsen2020",
        "abstract": "Comprehensive quantum algorithms overview."
    }).json()

    # Generate literature review selecting only s1 and s2
    gen_resp = client.post(f"/api/v1/manuscripts/{ms_id}/literature-review", json={
        "selected_source_ids": [s1["id"], s2["id"]],
        "focus_guidance": "Compare visual representation methods and scaling limits.",
        "word_target": 400
    })
    assert gen_resp.status_code == 200
    content = gen_resp.json()["content"]

    # Verify citations from selected sources exist
    assert ("He" in content or "He2022" in content)
    assert ("Zhai" in content or "Zhai2022" in content)
    # Verify unselected source is not cited
    assert "Nielsen" not in content


# ---------------------------------------------------------------------------
# Acceptance Criterion 8: Citation Integrity & Verification
# ---------------------------------------------------------------------------
def test_ac08_citation_integrity_resolution(client: TestClient):
    """
    AC 8: Every generated in-text citation resolves to a real project source.
    """
    proj_resp = client.post("/api/v1/projects", json={"title": "AC08 Citation Integrity"})
    proj_id = proj_resp.json()["id"]
    ms_id = proj_resp.json()["manuscript_id"]

    client.post("/api/v1/sources", json={
        "project_id": proj_id,
        "title": "Attention Is All You Need",
        "authors": "Vaswani, A., Shazeer, N., Parmar, N.",
        "year": 2017,
        "venue": "NeurIPS",
        "citation_key": "Vaswani2017",
        "metadata_verification_status": "verified"
    })

    manuscript = client.get(f"/api/v1/manuscripts/{ms_id}").json()
    intro_sec = [s for s in manuscript["sections"] if s["section_type"] == "introduction"][0]

    # Save content with a valid citation key
    client.put(f"/api/v1/manuscripts/{ms_id}/sections/{intro_sec['id']}", json={
        "content": "Modern neural language architectures rely on scaled dot-product attention [Vaswani2017]."
    })

    # Run verification report
    report_resp = client.get(f"/api/v1/verification/report/{ms_id}")
    assert report_resp.status_code == 200
    report = report_resp.json()

    assert report["can_export"] is True
    assert len(report["critical_errors"]) == 0
    assert report["four_level_audit"]["level_1_citations_count"] >= 1
    assert report["integrity_audit"]["missing_references"] == []


# ---------------------------------------------------------------------------
# Acceptance Criterion 9: Reference List & Cited-Only Bibliography
# ---------------------------------------------------------------------------
def test_ac09_cited_only_bibliography_generation():
    """
    AC 9: Every cited source appears in the reference list, uncited sources are excluded by default,
    and no metadata is fabricated.
    """
    s_cited = Source(
        id="s1",
        title="BERT: Pre-training of Deep Bidirectional Transformers",
        authors="Devlin, J., Chang, M., Lee, K., Toutanova, K.",
        year=2019,
        venue="NAACL-HLT",
        citation_key="Devlin2019",
        doi="10.18653/v1/N19-1423"
    )
    s_uncited = Source(
        id="s2",
        title="Uncited Paper on Optimization",
        authors="Smith, A.",
        year=2021,
        citation_key="Smith2021"
    )

    manuscript_text = "Bidirectional transformer contextualization was introduced by [Devlin2019]."
    bib = citation_formatter.format_cited_bibliography(
        sources=[s_cited, s_uncited],
        manuscript_text=manuscript_text,
        style="IEEE"
    )

    bib_str = "\n".join(bib)
    assert "BERT: Pre-training" in bib_str
    assert "Uncited Paper" not in bib_str
    assert "10.18653/v1/N19-1423" in bib_str


# ---------------------------------------------------------------------------
# Acceptance Criterion 10: Citation Style Consistency
# ---------------------------------------------------------------------------
def test_ac10_citation_style_switching(client: TestClient):
    """
    AC 10: Switching between supported citation styles updates both in-text citations and bibliography consistently.
    """
    proj_resp = client.post("/api/v1/projects", json={"title": "AC10 Style Switching"})
    ms_id = proj_resp.json()["manuscript_id"]

    client.post("/api/v1/sources", json={
        "project_id": proj_resp.json()["id"],
        "title": "Convolutional Networks for Visual Recognition",
        "authors": "LeCun, Y., Bengio, Y.",
        "year": 1998,
        "citation_key": "LeCun1998"
    })

    manuscript = client.get(f"/api/v1/manuscripts/{ms_id}").json()
    intro_sec = [s for s in manuscript["sections"] if s["section_type"] == "introduction"][0]

    # Save with author-key citation
    client.put(f"/api/v1/manuscripts/{ms_id}/sections/{intro_sec['id']}", json={
        "content": "Early deep learning relied upon gradient-based learning [LeCun1998]."
    })

    # 1. Switch to IEEE
    patch_ieee = client.patch(f"/api/v1/manuscripts/{ms_id}", json={
        "citation_style": "IEEE",
        "reformat_citations": True
    })
    assert patch_ieee.status_code == 200
    sec_ieee = [s for s in patch_ieee.json()["sections"] if s["id"] == intro_sec["id"]][0]
    assert "[1]" in sec_ieee["content"]

    # 2. Switch to APA
    patch_apa = client.patch(f"/api/v1/manuscripts/{ms_id}", json={
        "citation_style": "APA",
        "reformat_citations": True
    })
    assert patch_apa.status_code == 200
    sec_apa = [s for s in patch_apa.json()["sections"] if s["id"] == intro_sec["id"]][0]
    assert "LeCun" in sec_apa["content"]


# ---------------------------------------------------------------------------
# Acceptance Criterion 11: Weakly Supported & Unsupported Claims Flagged
# ---------------------------------------------------------------------------
def test_ac11_unsupported_claims_flagged(client: TestClient):
    """
    AC 11: Unsupported or weakly supported claims are flagged rather than automatically declared valid.
    """
    proj_resp = client.post("/api/v1/projects", json={"title": "AC11 Verification Audit"})
    ms_id = proj_resp.json()["manuscript_id"]

    manuscript = client.get(f"/api/v1/manuscripts/{ms_id}").json()
    intro_sec = [s for s in manuscript["sections"] if s["section_type"] == "introduction"][0]

    # Write a claim citing a non-existent phantom source
    client.put(f"/api/v1/manuscripts/{ms_id}/sections/{intro_sec['id']}", json={
        "content": "Quantum entanglement accelerates matrix multiplication by 10000x [PhantomRef2099]."
    })

    report_resp = client.get(f"/api/v1/verification/report/{ms_id}")
    report = report_resp.json()

    # Must flag unresolved / missing source
    assert report["can_export"] is False
    missing_cites = [m["in_text_citation"] if isinstance(m, dict) else m for m in report["integrity_audit"]["missing_references"]]
    assert "PhantomRef2099" in missing_cites


# ---------------------------------------------------------------------------
# Acceptance Criterion 12: DOCX and PDF Export with Integrity Safeguards
# ---------------------------------------------------------------------------
def test_ac12_manuscript_export_docx_and_pdf(client: TestClient):
    """
    AC 12: An exported manuscript contains citations and bibliography without unresolved placeholders.
    DOCX and PDF export formats succeed, and blocking occurs when critical errors exist.
    """
    proj_resp = client.post("/api/v1/projects", json={"title": "AC12 Export Validation"})
    proj_id = proj_resp.json()["id"]
    ms_id = proj_resp.json()["manuscript_id"]

    client.post("/api/v1/sources", json={
        "project_id": proj_id,
        "title": "Generative Adversarial Nets",
        "authors": "Goodfellow, I., Pouget-Abadie, J.",
        "year": 2014,
        "venue": "NeurIPS",
        "citation_key": "Goodfellow2014"
    })

    manuscript = client.get(f"/api/v1/manuscripts/{ms_id}").json()
    intro_sec = [s for s in manuscript["sections"] if s["section_type"] == "introduction"][0]

    # Clean text with valid citation
    client.put(f"/api/v1/manuscripts/{ms_id}/sections/{intro_sec['id']}", json={
        "content": "Adversarial training formulates a minimax game between generator and discriminator [Goodfellow2014]."
    })

    # Test DOCX Export
    docx_resp = client.post("/api/v1/export", json={
        "manuscript_id": ms_id,
        "export_format": "docx",
        "citation_style": "IEEE"
    })
    assert docx_resp.status_code == 200
    assert docx_resp.json()["filename"].endswith(".docx")

    # Test PDF Export
    pdf_resp = client.post("/api/v1/export", json={
        "manuscript_id": ms_id,
        "export_format": "pdf",
        "citation_style": "IEEE"
    })
    assert pdf_resp.status_code == 200
    assert pdf_resp.json()["filename"].endswith(".pdf")

    # Test Export Blocking when unresolved placeholder [?] exists
    client.put(f"/api/v1/manuscripts/{ms_id}/sections/{intro_sec['id']}", json={
        "content": "This claim has an unresolved citation placeholder [?] that must block export."
    })
    blocked_resp = client.post("/api/v1/export", json={
        "manuscript_id": ms_id,
        "export_format": "pdf",
        "citation_style": "IEEE",
        "block_on_critical_errors": True
    })
    assert blocked_resp.status_code == 400
    assert "critical citation-integrity errors" in blocked_resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Acceptance Criterion 13: Failure Recovery & File Validation
# ---------------------------------------------------------------------------
def test_ac13_invalid_upload_failure_recovery(client: TestClient):
    """
    AC 13: Invalid uploads, extraction failures, and corrupted files produce clear errors
    and do not leave inconsistent or corrupted database records.
    """
    proj_resp = client.post("/api/v1/projects", json={"title": "AC13 Error Handling"})
    proj_id = proj_resp.json()["id"]

    # 1. Non-PDF extension
    bad_file = ("script.py", b"print('malicious')", "text/plain")
    resp_bad_ext = client.post(
        "/api/v1/sources/upload-batch",
        data={"project_id": proj_id},
        files=[("files", bad_file)]
    )
    assert resp_bad_ext.status_code == 200
    res_list = resp_bad_ext.json()["results"]
    assert res_list[0]["status"] in ("failed", "error")
    assert "Invalid file" in (res_list[0].get("error") or res_list[0].get("message") or "")

    # 2. Corrupted PDF headers
    corrupt_pdf = ("corrupt.pdf", b"NOT_A_VALID_PDF_HEADER_DATA_12345", "application/pdf")
    resp_corrupt = client.post(
        "/api/v1/sources/upload-batch",
        data={"project_id": proj_id},
        files=[("files", corrupt_pdf)]
    )
    assert resp_corrupt.status_code == 200
    res_corrupt = resp_corrupt.json()["results"]
    assert res_corrupt[0]["status"] in ("failed", "error")
    assert "Could not read PDF" in (res_corrupt[0].get("error") or "") or "Failed to parse" in (res_corrupt[0].get("error") or "")

    # Verify no corrupted sources were left in the project
    sources = client.get(f"/api/v1/sources?project_id={proj_id}").json()
    assert len(sources) == 0


# ---------------------------------------------------------------------------
# Acceptance Criterion 14: Regression Testing of Core Platform Capabilities
# ---------------------------------------------------------------------------
def test_ac14_regression_search_and_project_flows(client: TestClient):
    """
    AC 14: Existing source search, manuscript generation, verification, and export functionality continues to work.
    """
    # 1. Academic Search API works and returns structured results
    search_resp = client.post("/api/v1/sources/search", json={
        "query": "transformer attention neural network",
        "limit": 3
    })
    assert search_resp.status_code == 200
    search_data = search_resp.json()
    assert search_data["total"] >= 1
    assert len(search_data["results"]) >= 1

    # 2. Journal profiles endpoint operates correctly
    journals_resp = client.get("/api/v1/journals/profiles")
    assert journals_resp.status_code == 200
    assert len(journals_resp.json()) >= 1
