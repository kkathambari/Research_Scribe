import pytest
from fastapi.testclient import TestClient
from pathlib import Path
from app.services.retrieval import retrieval_service
from app.services.repository_analyzer import repository_analyzer
from app.models.journal import JournalProfile

def test_audit_repository_integrity_no_silent_synthetic_manifest(client: TestClient):
    """
    Audit Finding P0: Verifies that submitting an invalid or unreachable repository URL
    fails visibly and does NOT silently synthesize an imaginary attention model or metrics.
    """
    submit_resp = client.post("/api/v1/repositories/submit", json={
        "repository_url": "https://github.com/nonexistent_user_99999/nonexistent_repo_99999",
        "branch_or_tag": "main",
        "title": "Invalid Repository Test"
    })
    # Must fail with 400 Bad Request, never 200 with fake attention models
    assert submit_resp.status_code == 400
    assert "failed" in submit_resp.json()["detail"].lower() or "not acquire" in submit_resp.json()["detail"].lower()

def test_audit_literature_retrieval_zero_fabricated_citations():
    """
    Audit Finding Critical 3: Verifies that external literature search queries
    yielding no results return an empty result set and never invent imaginary author personas.
    """
    import asyncio
    res = asyncio.run(retrieval_service.search(
        query="unlikely_random_query_xyz_987654321",
        limit=5,
        allow_test_fixtures=False
    ))
    assert res.total == 0
    assert len(res.results) == 0
    # Must not contain imaginary names
    for item in res.results:
        assert "Elena Rostova" not in (item.authors or "")
        assert "David K. Chen" not in (item.authors or "")

def test_audit_export_path_traversal_prevention(client: TestClient):
    """
    Audit Finding Security High: Verifies path traversal protection on /export/download/{filename}.
    """
    # Attempt directory traversal
    resp = client.get("/api/v1/export/download/../../etc/passwd")
    assert resp.status_code == 404

    resp_win = client.get("/api/v1/export/download/..\\..\\Windows\\win.ini")
    assert resp_win.status_code == 404

def test_audit_template_upload_validation(client: TestClient):
    """
    Audit Finding Security High: Verifies that template upload enforces .docx extension.
    """
    # Create or fetch a journal profile
    prof_resp = client.get("/api/v1/journals/profiles")
    assert prof_resp.status_code == 200
    profile_id = prof_resp.json()[0]["id"]

    # Upload invalid file type (.exe / .sh)
    files = {"file": ("malicious.sh", b"#!/bin/bash\necho test\n", "text/plain")}
    resp = client.post(
        "/api/v1/journals/templates/upload",
        data={"profile_id": profile_id},
        files=files
    )
    assert resp.status_code == 400
    assert "docx" in resp.json()["detail"].lower()

def test_audit_manual_source_unverified_by_default(client: TestClient):
    """
    Audit Finding High: Verifies that user-added sources default to unverified metadata (False).
    """
    proj_resp = client.post("/api/v1/projects", json={
        "title": "Manual Source Verification Test",
        "topic": "Bibliographic provenance"
    })
    assert proj_resp.status_code == 200
    proj_id = proj_resp.json()["id"]

    add_resp = client.post("/api/v1/sources", json={
        "project_id": proj_id,
        "title": "Manual Source Entry Without Prior Verification",
        "authors": "Unverified Author",
        "year": 2024
    })
    assert add_resp.status_code == 200
    source_data = add_resp.json()
    assert source_data["verified_metadata"] is False

def test_audit_compliance_not_verifiable_page_limit(client: TestClient):
    """
    Audit Finding Critical 5: Verifies that compliance checking correctly distinguishes
    'not_verifiable' for unrendered draft page limits rather than falsely reporting passed.
    """
    proj_resp = client.post("/api/v1/projects", json={
        "title": "Compliance Audit Verification",
        "topic": "Academic standards",
        "target_publication": "Elsevier Pattern Recognition"
    })
    assert proj_resp.status_code == 200
    manuscript_id = proj_resp.json()["manuscript_id"]

    comp_resp = client.get(f"/api/v1/journals/validate/{manuscript_id}")
    assert comp_resp.status_code == 200
    report = comp_resp.json()

    # Find page_limit check
    page_check = next((c for c in report["checks"] if c["check_type"] == "page_limit"), None)
    assert page_check is not None
    assert page_check["status"] == "not_verifiable"
    assert report["not_verifiable_count"] >= 1

def test_audit_commit_provenance_rejection(client: TestClient):
    """
    Audit 2 Critical A: Verifies that unreachable repository fails without
    producing an unverified commit fallback unless explicitly permitted.
    """
    resp = client.post("/api/v1/repositories/submit", json={
        "repository_url": "https://github.com/nonexistent_org/nonexistent_repo",
        "branch_or_tag": "main",
        "title": "Unreachable Repo Test",
        "allow_unverified_commit": False
    })
    assert resp.status_code == 400
    assert "commit sha could not be verified" in resp.json()["detail"].lower()

def test_audit_guided_mode_checkpoint_gating(client: TestClient):
    """
    Audit 2 Medium: Verifies that unapproved checkpoints block dependent operations
    and cannot be approved until prerequisites are met.
    """
    proj_resp = client.post("/api/v1/projects", json={
        "title": "Guided Gating Test Project",
        "topic": "Checkpoint prerequisite gating",
        "generation_mode": "guided"
    })
    assert proj_resp.status_code == 200
    proj_id = proj_resp.json()["id"]

    # Attempt to approve 'methodology' checkpoint before 'inventory' is approved
    rev_resp = client.post(f"/api/v1/workflow/review-action/{proj_id}", json={
        "checkpoint_name": "methodology",
        "target_type": "checkpoint",
        "target_id": "methodology",
        "action_type": "approved"
    })
    assert rev_resp.status_code == 400
    assert "prerequisite checkpoint" in rev_resp.json()["detail"].lower()

    # Now approve 'inventory' first
    rev_inv = client.post(f"/api/v1/workflow/review-action/{proj_id}", json={
        "checkpoint_name": "inventory",
        "target_type": "checkpoint",
        "target_id": "inventory",
        "action_type": "approved"
    })
    assert rev_inv.status_code == 200
    assert rev_inv.json()["status"] == "success"

    # Now approve 'methodology' - should succeed
    rev_meth = client.post(f"/api/v1/workflow/review-action/{proj_id}", json={
        "checkpoint_name": "methodology",
        "target_type": "checkpoint",
        "target_id": "methodology",
        "action_type": "approved"
    })
    assert rev_meth.status_code == 200
    assert rev_meth.json()["status"] == "success"

def test_audit_numerical_claim_verification():
    """
    Audit 2 High: Verifies that numerical claims whose values do not appear
    in the cited evidence passage are flagged as unverified.
    """
    from app.services.verification_engine import verification_engine

    claim_with_number = "The proposed transformer achieves 96.8% accuracy on the test set [1]."
    source = {"id": "src_1", "citation_key": "test2024", "title": "Test Paper", "abstract": "We evaluate transformer architectures."}
    evidences = [{
        "id": "ev_1",
        "source_id": "src_1",
        "passage_text": "We evaluate transformer architectures across test sets, observing solid accuracy and fast convergence.",
        "page_number": 3
    }]

    best_ev, score, status, expl = verification_engine._evaluate_evidence_support(claim_with_number, source, evidences)
    assert status == "unverified"
    assert "numerical discrepancy" in expl.lower()
    assert "96.8%" in expl

def test_audit_journal_guideline_verification_check(client: TestClient):
    """
    Audit 2 High: Verifies that default publisher profiles generate a guideline_verification
    warning so the researcher is aware that venue-specific rules have not been confirmed.
    """
    proj_resp = client.post("/api/v1/projects", json={
        "title": "Journal Default Warning Test",
        "topic": "Journal guidelines audit",
        "target_publication": "IEEE Transactions"
    })
    assert proj_resp.status_code == 200
    manuscript_id = proj_resp.json()["manuscript_id"]

    comp_resp = client.get(f"/api/v1/journals/validate/{manuscript_id}")
    assert comp_resp.status_code == 200
    report = comp_resp.json()

    guide_check = next((c for c in report["checks"] if c["check_type"] == "guideline_verification"), None)
    assert guide_check is not None
    assert guide_check["status"] == "warning"
    assert "unverified publisher defaults" in guide_check["explanation"].lower()
