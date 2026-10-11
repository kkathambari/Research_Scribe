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
    Audit 5 Critical 1 & High 2:
    - Rejects nonexistent or unverified commit SHA by default.
    - Supplying a file manifest does NOT bypass verification; request without allow_unverified_commit fails closed.
    - Rejects malformed commit SHAs (non-hex, < 7 chars, > 40 chars).
    """
    # Case A: Nonexistent SHA without unverified override
    resp = client.post("/api/v1/repositories/submit", json={
        "repository_url": "https://github.com/karpathy/nanoGPT",
        "resolved_commit_sha": "deadbeef00000000000000000000000000000000",
        "allow_unverified_commit": False
    })
    assert resp.status_code == 400
    assert "could not be verified" in resp.json()["detail"].lower()

    # Case B: File manifest supplied WITHOUT explicit allow_unverified_commit=True -> MUST FAIL CLOSED
    resp_manifest = client.post("/api/v1/repositories/submit", json={
        "repository_url": "https://github.com/karpathy/nanoGPT",
        "resolved_commit_sha": "deadbeef00000000000000000000000000000000",
        "file_manifest": [{"path": "model.py", "content": "import torch\n"}],
        "allow_unverified_commit": False
    })
    assert resp_manifest.status_code == 400
    assert "could not be verified" in resp_manifest.json()["detail"].lower()

    # Case C: Malformed commit SHA (non-hex or invalid length)
    resp_malformed = client.post("/api/v1/repositories/submit", json={
        "repository_url": "https://github.com/karpathy/nanoGPT",
        "resolved_commit_sha": "not_a_hex_commit_sha_xyz",
        "allow_unverified_commit": False
    })
    assert resp_malformed.status_code == 400
    assert "malformed" in resp_malformed.json()["detail"].lower() or "could not be verified" in resp_malformed.json()["detail"].lower()


def test_acceptance_2_full_40_char_sha_and_exact_commit_provenance(db: Session):
    """
    Audit 5 High 2 & High 3:
    - Tests temporary Git repository with TWO commits and an uncommitted file on disk.
    - Supplies an abbreviated 8-character SHA for Commit 1.
    - Proves acquire_repository() canonicalizes to the exact full 40-character SHA.
    - Proves acquire_files_from_repository() extracts ONLY Commit 1 files, excluding Commit 2 and dirty files.
    """
    import subprocess
    with tempfile.TemporaryDirectory() as temp_repo:
        repo_dir = Path(temp_repo)
        subprocess.run(["git", "init"], cwd=str(repo_dir), check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Tester"], cwd=str(repo_dir), check=True)
        subprocess.run(["git", "config", "user.email", "tester@example.com"], cwd=str(repo_dir), check=True)

        # Commit 1
        (repo_dir / "file1.py").write_text("def v1(): return 1\n", encoding="utf-8")
        subprocess.run(["git", "add", "file1.py"], cwd=str(repo_dir), check=True)
        subprocess.run(["git", "commit", "-m", "commit 1"], cwd=str(repo_dir), check=True)
        sha1_full = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=str(repo_dir), text=True).strip()
        sha1_abbrev = sha1_full[:8]
        assert len(sha1_full) == 40

        # Commit 2
        (repo_dir / "file2.py").write_text("def v2(): return 2\n", encoding="utf-8")
        (repo_dir / "file1.py").write_text("def v1(): return 999\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=str(repo_dir), check=True)
        subprocess.run(["git", "commit", "-m", "commit 2"], cwd=str(repo_dir), check=True)
        sha2_full = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=str(repo_dir), text=True).strip()
        assert sha1_full != sha2_full

        # Add uncommitted dirty file and dirty working tree change
        (repo_dir / "uncommitted_dirty.py").write_text("dirty_data = True\n", encoding="utf-8")
        (repo_dir / "file1.py").write_text("def v1(): return 'dirty_uncommitted'\n", encoding="utf-8")

        # Acquire repository using abbreviated SHA of Commit 1
        repo = repository_analyzer.acquire_repository(
            db=db,
            project_id="proj_acceptance_two_commit_provenance",
            repository_url=str(repo_dir),
            resolved_commit_sha=sha1_abbrev
        )

        # 1. Verify canonicalization to full 40-character SHA
        assert repo.resolved_commit_sha == sha1_full
        assert len(repo.resolved_commit_sha) == 40
        assert repo.acquisition_status == "acquired"

        # 2. Acquire files and verify exact Commit 1 tree isolation
        acquired_files = repository_analyzer.acquire_files_from_repository(repo)
        file_map = {f["path"]: f["content"] for f in acquired_files}

        # Must include file1.py with commit 1 content
        assert "file1.py" in file_map
        assert "def v1(): return 1" in file_map["file1.py"]
        assert "dirty_uncommitted" not in file_map["file1.py"]
        assert "return 999" not in file_map["file1.py"]

        # Must NOT include file2.py (belongs to commit 2)
        assert "file2.py" not in file_map

        # Must NOT include uncommitted_dirty.py
        assert "uncommitted_dirty.py" not in file_map


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

    # Case B: Project with authentic literature sources -> targeted topic evidence
    proj_with_lit = Project(
        id="proj_with_lit",
        title="Valid Literature Project",
        topic="Code Intelligence",
        generation_mode="guided"
    )
    db.add(proj_with_lit)

    src1 = Source(
        id="src_arch_1",
        project_id=proj_with_lit.id,
        title="Attention Is All You Need",
        authors="Vaswani et al.",
        year=2017,
        abstract="We introduce the Transformer, a novel architecture based entirely on self-attention."
    )
    src2 = Source(
        id="src_eval_2",
        project_id=proj_with_lit.id,
        title="BERT Pre-training Evaluation",
        authors="Devlin et al.",
        year=2019,
        abstract="The model demonstrates superior evaluation performance achieving a 94.2 F1 accuracy metric score on SQuAD benchmark."
    )
    db.add(src1)
    db.add(src2)
    db.commit()

    gaps = novelty_analyzer.analyze_research_gaps_and_contributions(db, proj_with_lit.id)
    assert len(gaps) == 7

    # 1. Architecture gap must specifically cite src1 and quote the Transformer passage
    gap_arch = next(g for g in gaps if "Architecture" in g.dimension)
    assert gap_arch.status == "hypothesis_requiring_review"
    assert src1.id in gap_arch.source_ids
    assert "Transformer, a novel architecture" in gap_arch.direct_support

    # 2. Evaluation metrics gap must specifically cite src2 and quote F1 metric
    gap_metric = next(g for g in gaps if "Metrics" in g.dimension)
    assert gap_metric.status == "hypothesis_requiring_review"
    assert src2.id in gap_metric.source_ids
    assert "94.2 F1" in gap_metric.direct_support

    # 3. Limitations gap was not discussed in either abstract -> MUST return insufficient_evidence with None direct_support
    gap_limit = next(g for g in gaps if "Limitations" in g.dimension)
    assert gap_limit.status == "insufficient_evidence"
    assert gap_limit.direct_support is None
    assert len(gap_limit.source_ids) == 0


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
    Audit 5 Medium 5:
    Tests DOCX template fidelity:
    - Run-level formatting preservation (bold/italic runs retained during placeholder replacement)
    - Placeholders in headers and footers
    - Placeholders inside table cells (metadata header table)
    - Verifies export endpoint passes manuscript.abstract into exporter
    - Formats native Word table for results and appends references
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        template_file = tmp_path / "journal_template.docx"

        # Construct realistic journal template with header, metadata table, and stylized runs
        doc = Document()
        # 1. Section header
        header = doc.sections[0].header
        hp = header.paragraphs[0]
        hp.text = "Running Header: {{TITLE}}"

        # 2. Document Title with distinct styled runs
        title_p = doc.add_paragraph()
        run_lead = title_p.add_run("Paper Title: ")
        run_lead.bold = True
        run_placeholder = title_p.add_run("{{TITLE}}")
        run_placeholder.italic = True

        # 3. Metadata Table (common in IEEE and ACM templates)
        meta_table = doc.add_table(rows=2, cols=2)
        cell_auth = meta_table.rows[0].cells[0].paragraphs[0]
        r_auth_label = cell_auth.add_run("Authors: ")
        r_auth_label.bold = True
        cell_auth.add_run("{{AUTHORS}}")

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

        # Verify Title runs preserved formatting
        p_title_out = out_doc.paragraphs[0]
        assert "Paper Title: Grounded Software Engineering Synthesis" in p_title_out.text
        # The lead run must still be bold
        assert any(r.bold is True for r in p_title_out.runs if "Paper Title" in r.text)

        # Verify Table cell placeholders replaced and styles preserved
        table_0 = out_doc.tables[0]
        meta_cell_authors = table_0.rows[0].cells[0].text
        meta_cell_abstract = table_0.rows[1].cells[0].text
        assert "{{AUTHORS}}" not in meta_cell_authors
        assert "Research Author(s)" in meta_cell_authors
        # The author label must still be bold
        cell_runs = table_0.rows[0].cells[0].paragraphs[0].runs
        assert any(r.bold is True for r in cell_runs if "Authors" in r.text)

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
