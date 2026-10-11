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

@pytest.mark.asyncio
async def test_audit_literature_retrieval_zero_fabricated_citations():
    """
    Audit Finding Critical 3: Verifies that external literature search queries
    yielding no results return an empty result set and never invent imaginary author personas.
    """
    res = await retrieval_service.search(
        query="unlikely_random_query_xyz_987654321",
        limit=5,
        allow_test_fixtures=False
    )
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
