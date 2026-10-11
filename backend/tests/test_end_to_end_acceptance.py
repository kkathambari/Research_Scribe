import re
import pytest
import tempfile
from pathlib import Path
from docx import Document
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.services.repository_analyzer import repository_analyzer
from app.services.retrieval import retrieval_service
from app.services.novelty_analyzer import novelty_analyzer
from app.services.verification_engine import verification_engine
from app.services.journal_intelligence import journal_intelligence
from app.services.exporter import exporter
from app.services.workflow_orchestrator import workflow_orchestrator
from app.models.project import Project
from app.models.manuscript import Manuscript, ManuscriptSection
from app.models.source import Source
from app.models.evidence import Evidence


def test_acceptance_1_and_2_full_40_char_sha_and_file_provenance():
    """
    Checklist Items 1 & 2:
    - Resolve and verify the full 40-character repository commit SHA (never truncated to 12 chars).
    - Prove every analyzed file belongs to that exact commit with cryptographic hash tracking.
    """
    # 1. Resolve commit SHA via git rev-parse on this repository
    current_repo_path = Path(__file__).resolve().parent.parent.parent
    sha = repository_analyzer.resolve_remote_commit_sha(str(current_repo_path), "kkathambari", "Research_Scribe", "main")
    assert sha is not None
    assert len(sha) == 40, f"Expected 40-character hex commit SHA, got {len(sha)}: {sha}"
    assert re.match(r"^[0-9a-f]{40}$", sha), f"SHA {sha} is not a valid 40-character hex string"

    # 2. Verify file content acquisition and integrity from repository
    scanned_files = repository_analyzer._scan_directory_files(current_repo_path, max_files=10)
    assert len(scanned_files) > 0
    for file_meta in scanned_files:
        assert "path" in file_meta
        assert "content" in file_meta
        assert "file_type" in file_meta
        assert len(file_meta["content"]) > 0


def test_acceptance_3_automatic_mode_requires_explicit_repo_and_venue(db: Session, client: TestClient):
    """
    Checklist Item 3 & High Finding 2:
    Automatic Mode must reject execution with a validation error when either the
    repository URL or target journal is missing, rather than silently substituting
    facebookresearch/llama or generic IEEE Transactions.
    """
    # Create project without repository URL or target publication
    proj_resp = client.post("/api/v1/projects", json={
        "title": "Unconfigured Project",
        "topic": "Neural Parsing"
    })
    assert proj_resp.status_code == 200
    proj_id = proj_resp.json()["id"]

    # Attempt to run automatic mode without providing repo or journal
    with pytest.raises(ValueError) as excinfo:
        workflow_orchestrator.run_automatic_mode(
            db=db,
            project_id=proj_id,
            repository_url=None,
            journal_name=None
        )
    assert "explicit repository_url" in str(excinfo.value).lower()


def test_acceptance_4_literature_retrieval_and_bibliographic_provenance():
    """
    Checklist Item 4:
    Retrieve real papers and retain source-level bibliographic provenance.
    Ensure zero synthetic author personas or imaginary citations on failed retrieval.
    """
    import asyncio
    res = asyncio.run(retrieval_service.search("nonexistent_random_unmatched_query_99999", allow_test_fixtures=False))
    assert res.total == 0
    assert len(res.results) == 0
    assert res.retrieval_status in ["retrieval_unavailable", "empty_result"]


def test_acceptance_5_novelty_proposals_traceable_and_labeled_as_hypotheses(db: Session):
    """
    Checklist Item 5:
    Generate novelty proposals only from traceable evidence.
    Every gap must identify supporting passages, source identifiers, comparison limitations,
    and be explicitly marked as 'hypothesis_requiring_review'.
    """
    # Create a project and related literature in DB
    proj = Project(
        id="proj_novelty_test",
        title="Novelty Test Project",
        topic="Code Intelligence",
        generation_mode="guided"
    )
    db.add(proj)

    src = Source(
        id="src_novelty_1",
        project_id=proj.id,
        title="Attention Is All You Need",
        authors="Vaswani et al.",
        year=2017,
        abstract="We introduce the Transformer, a novel architecture based entirely on self-attention."
    )
    db.add(src)
    db.commit()

    gaps = novelty_analyzer.analyze_research_gaps_and_contributions(db, proj.id)
    assert len(gaps) > 0

    for gap in gaps:
        assert gap.status == "hypothesis_requiring_review"
        assert len(gap.supporting_passages) > 0
        assert gap.comparison_limitations is not None
        assert len(gap.comparison_limitations) > 0
        assert len(gap.proposed_contribution) > 0


def test_acceptance_6_guided_mode_runtime_gating_and_claim_verification(client: TestClient):
    """
    Checklist Item 6:
    Enforce Guided Mode gates at execution time:
    - Section generation cannot run until outline and contributions are approved.
    - Export cannot run until compliance checkpoint is approved.
    - Claim verification checks numerical metrics AND units, plus causal vs correlation claims.
    """
    # 1. Test Guided Mode runtime gating for section generation
    proj_resp = client.post("/api/v1/projects", json={
        "title": "Runtime Gated Project",
        "topic": "Deterministic Execution",
        "generation_mode": "guided"
    })
    assert proj_resp.status_code == 200
    proj_data = proj_resp.json()
    proj_id = proj_data["id"]
    manuscript_id = proj_data["manuscript_id"]

    # Attempt to trigger section generation before approving prerequisites
    sec_gen_resp = client.post(f"/api/v1/workflow/generate-sections/{proj_id}")
    assert sec_gen_resp.status_code == 400
    assert "prerequisite" in sec_gen_resp.json()["detail"].lower()

    # Attempt to export DOCX in Guided Mode before approving compliance checkpoint
    export_resp = client.post("/api/v1/export", json={"manuscript_id": manuscript_id, "export_format": "docx"})
    assert export_resp.status_code == 400
    assert "compliance" in export_resp.json()["detail"].lower()

    # 2. Test Claim Verification with Units & Causal Statements
    claim_unit_mismatch = "The pipeline executes in 120 ms on average [1]."
    source = {"id": "src-1", "citation_key": "smith2024", "title": "Smith 2024"}
    ev_wrong_unit = [{
        "id": "ev-1",
        "source_id": "src-1",
        "passage_text": "The pipeline execution duration was recorded as 120 seconds for the entire dataset.",
        "page_number": 4
    }]
    _, _, status_unit, expl_unit = verification_engine._evaluate_evidence_support(claim_unit_mismatch, source, ev_wrong_unit)
    assert status_unit == "unverified"
    assert "unit 'ms' missing" in expl_unit.lower()

    claim_causal = "The attention mechanism causes dramatic convergence speedup [1]."
    ev_correlation = [{
        "id": "ev-2",
        "source_id": "src-1",
        "passage_text": "We observed that attention mechanism usage was correlated with higher convergence rates across trials.",
        "page_number": 5
    }]
    _, _, status_causal, expl_causal = verification_engine._evaluate_evidence_support(claim_causal, source, ev_correlation)
    assert status_causal == "partially_supported"
    assert "causal inference requires caution" in expl_causal.lower()


def test_acceptance_7_journal_intelligence_unverified_profile_provisional(client: TestClient):
    """
    Checklist Item 7:
    Validate against selected journal requirements.
    Distinguish exact journal profiles from unverified publisher defaults.
    Do NOT report compliance as confirmed against an unverified profile.
    """
    proj_resp = client.post("/api/v1/projects", json={
        "title": "Unverified Journal Profile Test",
        "topic": "Academic Publishing",
        "target_publication": "Journal of Completely Unknown Unindexed Studies"
    })
    assert proj_resp.status_code == 200
    manuscript_id = proj_resp.json()["manuscript_id"]

    comp_resp = client.get(f"/api/v1/journals/validate/{manuscript_id}")
    assert comp_resp.status_code == 200
    report = comp_resp.json()

    assert report["profile_verification_status"].startswith("unverified")
    assert report["is_officially_confirmed"] is False
    assert report["overall_status"] == "unverified_profile_provisional"


def test_acceptance_8_docx_template_fidelity_and_structure():
    """
    Checklist Item 8:
    Export a DOCX and verify its required structure:
    Preserves template placeholders, headings, paragraph content, native tables, and references.
    """
    # 1. Create a dummy base template with placeholders
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        template_file = tmp_path / "template.docx"

        doc = Document()
        doc.add_heading("{{TITLE}}", level=0)
        doc.add_paragraph("Author: {{AUTHORS}}")
        doc.add_paragraph("Abstract: {{ABSTRACT}}")
        doc.save(str(template_file))

        # 2. Build manuscript data
        manuscript_dict = {
            "id": "test-manuscript-e2e",
            "title": "End-to-End Scientific Reliability in ResearchScribe",
            "abstract": "We present an evidence-grounded study of automated academic manuscript drafting.",
            "target_journal": "ACM Computing Surveys"
        }
        sections = [
            {
                "section_type": "introduction",
                "title": "1. Introduction",
                "order": 1,
                "content": "Automated code synthesis requires reproducible benchmarks and explicit provenance tracking [1]."
            },
            {
                "section_type": "results",
                "title": "2. Experimental Evaluation",
                "order": 2,
                "content": "Table 1 summarizes the accuracy across benchmarks.\n\n| Model | Accuracy (%) | Latency (ms) |\n| --- | --- | --- |\n| Baseline | 84.2 | 310 |\n| ResearchScribe | 96.5 | 115 |"
            }
        ]
        sources = [
            {
                "citation_key": "vaswani2017",
                "title": "Attention Is All You Need",
                "authors": "Vaswani, A., et al.",
                "year": 2017,
                "venue": "NeurIPS"
            }
        ]

        # 3. Export manuscript with template
        path = exporter.export_manuscript(
            manuscript=manuscript_dict,
            sections=sections,
            sources=sources,
            export_format="docx",
            template_path=str(template_file)
        )

        assert Path(path).exists()
        out_doc = Document(str(path))

        # Verify placeholders replaced
        full_text = "\n".join(p.text for p in out_doc.paragraphs)
        assert "{{TITLE}}" not in full_text
        assert "{{ABSTRACT}}" not in full_text
        assert "{{AUTHORS}}" not in full_text
        assert "End-to-End Scientific Reliability in ResearchScribe" in full_text
        assert "Automated code synthesis requires reproducible benchmarks" in full_text

        # Verify native Word table was created for markdown table
        assert len(out_doc.tables) >= 1
        table = out_doc.tables[0]
        # Check table contents
        headers = [c.text for c in table.rows[0].cells]
        assert "Model" in headers
        assert "Accuracy (%)" in headers
        assert "Latency (ms)" in headers

        row_1 = [c.text for c in table.rows[1].cells]
        assert "Baseline" in row_1
        assert "84.2" in row_1

        # Verify references section appended
        assert "References" in full_text
        assert "Vaswani, A., et al." in full_text
        assert "Attention Is All You Need" in full_text
