import pytest
from fastapi.testclient import TestClient
from pathlib import Path

def test_v3_repository_ingestion_and_intelligence(client: TestClient):
    """
    Tests FR-01 through FR-07:
    - Repository submission & snapshot creation
    - AST codebase parsing & architecture component extraction
    - Methodology reconstruction with equations and pseudocode
    - Experimental evidence extraction (metrics, seeds, baselines)
    - Evidence sufficiency and consistency analysis
    """
    # 1. FR-01: Submit Repository
    submit_resp = client.post("/api/v1/repositories/submit", json={
        "repository_url": "https://github.com/facebookresearch/llama",
        "branch_or_tag": "main",
        "title": "Open and Efficient Foundation Language Models",
        "research_topic": "Autoregressive sequence modeling and factual groundings",
        "target_publication": "IEEE Transactions",
        "citation_style": "IEEE",
        "generation_mode": "automatic"
    })
    assert submit_resp.status_code == 200
    repo_data = submit_resp.json()
    repo_id = repo_data["id"]
    assert repo_data["owner_name"] == "facebookresearch"
    assert repo_data["repository_name"] == "llama"
    assert repo_data["acquisition_status"] == "acquired"

    # 2. FR-02 & FR-03: Inspect Snapshot and File Inventory
    snap_resp = client.get(f"/api/v1/repositories/{repo_id}/snapshot")
    assert snap_resp.status_code == 200
    snap_data = snap_resp.json()
    assert snap_data["file_count"] > 0
    assert len(snap_data["files"]) > 0
    assert any("python" in f["language"].lower() for f in snap_data["files"])

    # 3. FR-04: Architecture Reconstruction
    arch_resp = client.get(f"/api/v1/repositories/{repo_id}/architecture")
    assert arch_resp.status_code == 200
    components = arch_resp.json()
    assert len(components) > 0
    assert any(c["component_type"] in ["model", "pipeline", "module"] for c in components)
    assert any(c["file_path"].endswith(".py") for c in components)

    # 4. FR-05: Methodology Reconstruction (Equations, Pseudocode, Hyperparameters)
    meth_resp = client.get(f"/api/v1/repositories/{repo_id}/methodology")
    assert meth_resp.status_code == 200
    meth_data = meth_resp.json()
    assert meth_data["algorithm_description"] is not None
    assert "softmax" in meth_data["equations"] or "Attention" in meth_data["equations"]
    assert "Algorithm 1" in meth_data["pseudocode"]
    assert "AdamW" in meth_data["hyperparameters"]

    # Test Guided researcher correction of methodology
    update_meth = client.put(f"/api/v1/repositories/{repo_id}/methodology", json={
        "problem_description": "Customized verifiable reasoning across large-scale repositories.",
        "review_status": "approved"
    })
    assert update_meth.status_code == 200
    assert update_meth.json()["review_status"] == "approved"

    # 5. FR-06: Experimental Evidence Ledger
    exp_resp = client.get(f"/api/v1/repositories/{repo_id}/experimental-results")
    assert exp_resp.status_code == 200
    results = exp_resp.json()
    assert len(results) >= 2
    assert any(r["metric_name"] in ["F1-Score", "Accuracy"] for r in results)
    assert all(r["verification_status"] == "verified" for r in results)

    # 6. FR-07: Evidence Gap Analysis
    gap_resp = client.get(f"/api/v1/repositories/{repo_id}/evidence-gap")
    assert gap_resp.status_code == 200
    gap_data = gap_resp.json()
    assert "sufficiency_score" in gap_data
    assert gap_data["sufficiency_score"] > 0.0
    assert len(gap_data["recommendations"]) > 0

def test_v3_journal_intelligence_and_compliance(client: TestClient):
    """
    Tests FR-19 through FR-25:
    - Journal profile selection and atomic requirement extraction
    - Manuscript compliance check returning passed, failed, warning
    """
    # 1. FR-19: List Journal Profiles
    prof_resp = client.get("/api/v1/journals/profiles")
    assert prof_resp.status_code == 200
    profiles = prof_resp.json()
    assert len(profiles) >= 3
    ieee_profile = next((p for p in profiles if "IEEE" in p["journal_name"]), profiles[0])
    assert ieee_profile["citation_style"] == "IEEE"
    assert len(ieee_profile["requirements"]) >= 4

    # 2. Create project & manuscript to validate
    proj_resp = client.post("/api/v1/projects", json={
        "title": "Empirical Benchmarking in Neural Repositories",
        "topic": "Deep learning code synthesis",
        "target_publication": "IEEE Transactions",
        "citation_style": "IEEE"
    })
    assert proj_resp.status_code == 200
    proj_data = proj_resp.json()
    manuscript_id = proj_data["manuscript_id"]

    # 3. FR-24: Validate Compliance
    comp_resp = client.get(f"/api/v1/journals/validate/{manuscript_id}?profile_id={ieee_profile['id']}")
    assert comp_resp.status_code == 200
    report = comp_resp.json()
    assert report["journal_name"] == ieee_profile["journal_name"]
    assert "compliance_score" in report
    assert len(report["checks"]) >= 4
    check_types = [c["check_type"] for c in report["checks"]]
    assert "word_limit" in check_types
    assert "abstract_length" in check_types

def test_v3_novelty_and_guided_workflow(client: TestClient):
    """
    Tests FR-11, FR-13, and FR-14:
    - Literature gap and novelty analysis across 7 dimensions
    - Guided Mode checkpoint progress and review actions
    - Automatic Mode 1-click end-to-end execution
    """
    # 1. Create project with repository URL
    proj_resp = client.post("/api/v1/projects", json={
        "title": "Verifiable Neural Synthesis from Code Artifacts",
        "repository_url": "https://github.com/karpathy/nanoGPT",
        "research_topic": "Generative language models with verifiable source citations",
        "target_publication": "IEEE Transactions",
        "generation_mode": "guided"
    })
    assert proj_resp.status_code == 200
    proj = proj_resp.json()
    project_id = proj["id"]

    # Add a sample literature source
    client.post("/api/v1/sources", json={
        "project_id": project_id,
        "title": "Attention Is All You Need",
        "authors": "Ashish Vaswani, Noam Shazeer, et al.",
        "year": 2017,
        "venue": "NeurIPS",
        "citation_key": "Vaswani2017"
    })

    # 2. FR-11: Novelty & Research Gap Proposals
    gap_resp = client.get(f"/api/v1/workflow/research-gaps/{project_id}")
    assert gap_resp.status_code == 200
    gaps = gap_resp.json()
    assert len(gaps) >= 2
    assert any("Architecture" in g["dimension"] for g in gaps)
    assert any("Metrics" in g["dimension"] for g in gaps)

    # 3. FR-14: Guided Checkpoints & Review Actions
    cp_resp = client.get(f"/api/v1/workflow/checkpoints/{project_id}")
    assert cp_resp.status_code == 200
    checkpoints = cp_resp.json()
    assert len(checkpoints) == 10  # 10 checkpoints in Guided Mode
    assert any(c["checkpoint"] == "inventory" for c in checkpoints)
    assert any(c["checkpoint"] == "methodology" for c in checkpoints)

    # Researcher approves inventory checkpoint
    act_resp = client.post(f"/api/v1/workflow/review-action/{project_id}", json={
        "checkpoint_name": "inventory",
        "target_type": "file_inventory",
        "action_type": "approved",
        "approved_value": "All repository modules verified."
    })
    assert act_resp.status_code == 200
    assert act_resp.json()["status"] == "success"

    # 4. FR-13: Run One-Click Automatic Pipeline
    auto_resp = client.post(f"/api/v1/workflow/run-automatic/{project_id}?journal_name=IEEE%20Transactions")
    if auto_resp.status_code != 200:
        print("AUTO_RESP ERROR:", auto_resp.status_code, auto_resp.text)
    assert auto_resp.status_code == 200
    auto_data = auto_resp.json()
    assert auto_data["status"] == "completed"
    summary = auto_data["summary"]
    assert summary["sections_generated"] >= 5
    assert summary["compliance_score"] >= 70.0

    # 5. FR-23 & FR-26: Export Document and verify compliance
    exp_resp = client.post("/api/v1/export", json={
        "manuscript_id": summary["manuscript_id"],
        "export_format": "docx",
        "citation_style": "IEEE",
        "include_verification_appendix": True
    })
    assert exp_resp.status_code == 200
    exp_data = exp_resp.json()
    assert exp_data["format"] == "docx"
    assert exp_data["download_url"].startswith("/api/v1/export/download/")
