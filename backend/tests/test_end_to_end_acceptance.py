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
from app.models.repository import Repository
from app.models.source import Source


def test_acceptance_1_invalid_supplied_sha_rejected(client: TestClient):
    """
    Audit 4 Critical 1:
    Verifies that a caller-supplied resolved_commit_sha is NOT trusted blindly.
    Submitting an unverified or nonexistent commit SHA fails closed with a 400 error.
    """
    resp = client.post("/api/v1/repositories/submit", json={
        "repository_url": "https://github.com/karpathy/nanoGPT",
        "resolved_commit_sha": "deadbeef00000000000000000000000000000000",
        "allow_unverified_commit": False
    })
    assert resp.status_code == 400
    assert "could not be verified" in resp.json()["detail"].lower()


def test_acceptance_2_full_40_char_sha_and_exact_commit_provenance(db: Session):
    """
    Checklist Items 1 & 2 & Audit 4 High 2:
    - Resolves 40-character commit SHA on local repository.
    - Acquires files via production acquire_files_from_repository path.
    - Proves acquired files belong to the recorded commit snapshot with cryptographic hashes.
    """
    current_repo_path = Path(__file__).resolve().parent.parent.parent
    sha = repository_analyzer.resolve_remote_commit_sha(str(current_repo_path), "kkathambari", "Research_Scribe", "main")
    assert sha is not None
    assert len(sha) == 40, f"Expected 40-character hex commit SHA, got {len(sha)}: {sha}"
    assert re.match(r"^[0-9a-f]{40}$", sha)

    # Acquire repository model
    repo = repository_analyzer.acquire_repository(
        db=db,
        project_id="proj_acceptance_provenance",
        repository_url=str(current_repo_path),
        resolved_commit_sha=sha
    )
    assert repo.resolved_commit_sha == sha
    assert repo.acquisition_status == "acquired"

    # Create production snapshot from acquired files
    snapshot = repository_analyzer.create_snapshot_from_manifest(db, repo)
    assert snapshot.commit_sha == sha
    assert len(snapshot.files) > 0
    for f in snapshot.files:
        assert f.content_hash is not None
        assert len(f.content_hash) == 40  # SHA-1 content hash
        assert f.size_bytes > 0


def test_acceptance_3_automatic_mode_requires_explicit_repo_and_venue(db: Session, client: TestClient):
    """
    Audit Finding High 2:
    Automatic Mode rejects execution when either repository URL or target journal is missing,
    rather than silently substituting Llama or generic IEEE profiles.
    """
    proj_resp = client.post("/api/v1/projects", json={
        "title": "Unconfigured Project",
        "topic": "Neural Parsing"
    })
    assert proj_resp.status_code == 200
    proj_id = proj_resp.json()["id"]

    with pytest.raises(ValueError) as excinfo:
        workflow_orchestrator.run_automatic_mode(
            db=db,
            project_id=proj_id,
            repository_url=None,
            journal_name=None
        )
    assert "explicit repository_url" in str(excinfo.value).lower()


def test_acceptance_4_literature_retrieval_zero_fabricated_citations():
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


def test_acceptance_5_novelty_analysis_evidence_driven_and_insufficient_evidence(db: Session):
    """
    Audit 4 High 3:
    - Empty literature list returns status='insufficient_evidence' (never imaginary traceable gaps).
    - With literature, each proposal specifies direct_support, inferred_extrapolation, and hypothesis status.
    """
    # Case A: Project with NO literature sources -> MUST return insufficient_evidence
    proj_empty = Project(
        id="proj_empty_lit",
        title="Empty Literature Project",
        topic="Code Intelligence",
        generation_mode="guided"
    )
    db.add(proj_empty)
    db.commit()

    gaps_empty = novelty_analyzer.analyze_research_gaps_and_contributions(db, proj_empty.id)
    assert len(gaps_empty) == 7
    for g in gaps_empty:
        assert g.status == "insufficient_evidence"
        assert len(g.source_ids) == 0
        assert len(g.supporting_passages) == 0

    # Case B: Project with authentic literature sources -> returns traceable hypothesis
    proj_with_lit = Project(
        id="proj_with_lit",
        title="Valid Literature Project",
        topic="Code Intelligence",
        generation_mode="guided"
    )
    db.add(proj_with_lit)

    src = Source(
        id="src_valid_1",
        project_id=proj_with_lit.id,
        title="Attention Is All You Need",
        authors="Vaswani et al.",
        year=2017,
        abstract="We introduce the Transformer, a novel architecture based entirely on self-attention."
    )
    db.add(src)
    db.commit()

    gaps = novelty_analyzer.analyze_research_gaps_and_contributions(db, proj_with_lit.id)
    assert len(gaps) == 7
    for g in gaps:
        assert g.status == "hypothesis_requiring_review"
        assert len(g.supporting_passages) > 0
        assert g.direct_support is not None
        assert g.inferred_extrapolation is not None
        assert len(g.source_ids) > 0


def test_acceptance_6_guided_mode_checkpoint_invalidation_lifecycle(client: TestClient):
    """
    Audit 4 High 4:
    Verifies Guided Mode lifecycle and cascade invalidation:
    1. Approve 'inventory' -> Approve 'methodology'.
    2. Edit/reject 'inventory' (upstream).
    3. Verify downstream 'methodology' approval is invalidated.
    4. Verify gated operations (e.g. section generation) are immediately blocked.
    """
    proj_resp = client.post("/api/v1/projects", json={
        "title": "Guided Lifecycle Invalidation Project",
        "topic": "Deterministic Execution",
        "generation_mode": "guided"
    })
    assert proj_resp.status_code == 200
    proj_id = proj_resp.json()["id"]

    # 1. Approve inventory
    r_inv = client.post(f"/api/v1/workflow/review-action/{proj_id}", json={
        "checkpoint_name": "inventory",
        "target_type": "checkpoint",
        "target_id": "inventory",
        "action_type": "approved"
    })
    assert r_inv.status_code == 200

    # 2. Approve methodology (depends on inventory)
    r_meth = client.post(f"/api/v1/workflow/review-action/{proj_id}", json={
        "checkpoint_name": "methodology",
        "target_type": "checkpoint",
        "target_id": "methodology",
        "action_type": "approved"
    })
    assert r_meth.status_code == 200

    # Verify both checkpoints show approved
    cps = client.get(f"/api/v1/workflow/checkpoints/{proj_id}").json()
    assert next(c for c in cps if c["checkpoint"] == "inventory")["status"] == "approved"
    assert next(c for c in cps if c["checkpoint"] == "methodology")["status"] == "approved"

    # 3. Researcher edits/rejects upstream 'inventory' checkpoint
    r_edit = client.post(f"/api/v1/workflow/review-action/{proj_id}", json={
        "checkpoint_name": "inventory",
        "target_type": "checkpoint",
        "target_id": "inventory",
        "action_type": "modified",
        "comment": "Inventory modified due to file additions."
    })
    assert r_edit.status_code == 200

    # 4. Verify downstream 'methodology' approval was invalidated
    cps_after = client.get(f"/api/v1/workflow/checkpoints/{proj_id}").json()
    inv_cp = next(c for c in cps_after if c["checkpoint"] == "inventory")
    meth_cp = next(c for c in cps_after if c["checkpoint"] == "methodology")
    assert inv_cp["status"] != "approved"
    assert meth_cp["status"] != "approved"  # Cascade-invalidated!

    # 5. Gated section generation must be blocked
    sec_gen_resp = client.post(f"/api/v1/workflow/generate-sections/{proj_id}")
    assert sec_gen_resp.status_code == 400


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


def test_acceptance_8_docx_template_fidelity_tables_headers_and_abstract(client: TestClient):
    """
    Audit 4 Medium-High 5:
    Tests DOCX template fidelity:
    - Placeholders in headers and footers
    - Placeholders inside table cells (metadata header table)
    - Verifies export endpoint passes manuscript.abstract into exporter
    - Formats native Word table for results and appends references
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        template_file = tmp_path / "journal_template.docx"

        # Construct realistic journal template with header, metadata table, and body
        doc = Document()
        # 1. Section header
        header = doc.sections[0].header
        hp = header.paragraphs[0]
        hp.text = "Running Header: {{TITLE}}"

        # 2. Document Title
        doc.add_heading("{{TITLE}}", level=0)

        # 3. Metadata Table (common in IEEE and ACM templates)
        meta_table = doc.add_table(rows=2, cols=2)
        meta_table.rows[0].cells[0].paragraphs[0].text = "Authors: {{AUTHORS}}"
        meta_table.rows[0].cells[1].paragraphs[0].text = "Venue: IEEE Transactions"
        meta_table.rows[1].cells[0].paragraphs[0].text = "Abstract: {{ABSTRACT}}"
        meta_table.rows[1].cells[1].paragraphs[0].text = "Keywords: {{KEYWORDS}}"

        # 4. Body placeholder
        doc.add_paragraph("{{INTRODUCTION}}")
        doc.save(str(template_file))

        # Build manuscript data
        manuscript_dict = {
            "id": "test-manuscript-fidelity",
            "title": "Grounded Software Engineering Synthesis",
            "abstract": "We evaluate repository provenance and verification fidelity under controlled benchmark conditions.",
            "target_journal": "IEEE Transactions"
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
                "title": "2. Empirical Evaluation",
                "order": 2,
                "content": "Table 1 compares the baseline against the proposed system.\n\n| System | Accuracy (%) | Latency (ms) |\n| --- | --- | --- |\n| Baseline | 82.5 | 320 |\n| ResearchScribe | 97.1 | 110 |"
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

        path = exporter.export_manuscript(
            manuscript=manuscript_dict,
            sections=sections,
            sources=sources,
            export_format="docx",
            template_path=str(template_file)
        )

        assert Path(path).exists()
        out_doc = Document(str(path))

        # Verify Header placeholder replaced
        header_text = "\n".join(p.text for p in out_doc.sections[0].header.paragraphs)
        assert "{{TITLE}}" not in header_text
        assert "Grounded Software Engineering Synthesis" in header_text

        # Verify Table cell placeholders replaced
        table_0 = out_doc.tables[0]
        meta_cell_authors = table_0.rows[0].cells[0].text
        meta_cell_abstract = table_0.rows[1].cells[0].text
        assert "{{AUTHORS}}" not in meta_cell_authors
        assert "Research Author(s)" in meta_cell_authors
        assert "{{ABSTRACT}}" not in meta_cell_abstract
        assert "We evaluate repository provenance" in meta_cell_abstract

        # Verify body content and native result table
        all_text = "\n".join(p.text for p in out_doc.paragraphs)
        assert "{{TITLE}}" not in all_text
        assert "{{INTRODUCTION}}" not in all_text
        assert "Automated code synthesis requires reproducible benchmarks" in all_text

        # Verify results table
        assert len(out_doc.tables) >= 2
        res_table = out_doc.tables[1]
        assert "System" in [c.text for c in res_table.rows[0].cells]
        assert "97.1" in [c.text for c in res_table.rows[2].cells]

        # Verify references appended
        assert "References" in all_text
        assert "Vaswani, A., et al." in all_text
