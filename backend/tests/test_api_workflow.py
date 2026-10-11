import pytest
from fastapi.testclient import TestClient

def test_health_check(client: TestClient):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"

def test_frontend_index(client: TestClient):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "ResearchScribe" in resp.text

def test_full_research_workflow(client: TestClient):
    # 1. FR-01 & FR-02: Create Research Project
    proj_resp = client.post("/api/v1/projects", json={
        "title": "Evidence-Grounded Neural Verification in Automated Research Writing",
        "topic": "Automated citation verification and factual traceability in LLMs",
        "research_problem": "Hallucinated citations and unverified factual assertions in AI-assisted writing",
        "research_questions": "How can sentence-level evidence mapping reduce unsupported claims in generated manuscripts?",
        "objectives": "Develop a modular architecture linking generated claims to primary source passages.",
        "academic_discipline": "Computer Science / NLP",
        "publication_type": "Conference / Journal Article",
        "citation_style": "APA",
        "word_count_target": 4500
    })
    assert proj_resp.status_code == 200
    project = proj_resp.json()
    project_id = project["id"]
    manuscript_id = project["manuscript_id"]
    assert manuscript_id is not None

    # 2. FR-03: Search Literature
    search_resp = client.post("/api/v1/sources/search", json={
        "query": "transformer attention deep learning",
        "limit": 3
    })
    assert search_resp.status_code == 200
    search_data = search_resp.json()
    assert len(search_data["results"]) > 0

    first_search_result = search_data["results"][0]

    # 3. Add Source to Project Library
    source_resp = client.post("/api/v1/sources", json={
        "project_id": project_id,
        "title": first_search_result["title"],
        "authors": first_search_result["authors"],
        "year": first_search_result["year"],
        "venue": first_search_result["venue"],
        "doi": first_search_result["doi"],
        "url": first_search_result["url"],
        "abstract": first_search_result["abstract"],
        "citation_key": first_search_result["citation_key"]
    })
    assert source_resp.status_code == 200
    source = source_resp.json()
    source_id = source["id"]

    # 4. FR-05: Inspect Extracted Evidence
    ev_resp = client.get(f"/api/v1/evidence?project_id={project_id}")
    assert ev_resp.status_code == 200
    evidences = ev_resp.json()
    assert len(evidences) >= 0

    # 5. FR-07: Get Manuscript Outline and Generate a Section
    ms_resp = client.get(f"/api/v1/manuscripts/{manuscript_id}")
    assert ms_resp.status_code == 200
    ms_data = ms_resp.json()
    sections = ms_data["sections"]
    assert len(sections) >= 5 # standard sections initialized

    # Find the Literature Review section
    lit_sec = next((s for s in sections if s["section_type"] == "literature_review"), sections[1])

    gen_resp = client.post(f"/api/v1/manuscripts/{manuscript_id}/sections/{lit_sec['id']}/generate", json={
        "section_type": lit_sec["section_type"],
        "title": lit_sec["title"],
        "word_limit": 600,
        "instructions": "Synthesize the foundational mechanisms and emphasize factual traceability.",
        "source_ids": [source_id]
    })
    assert gen_resp.status_code == 200
    gen_data = gen_resp.json()
    assert len(gen_data["content"]) > 100
    assert gen_data["status"] == "generated"

    # 6. FR-09: Inspect Verification Report
    verif_resp = client.get(f"/api/v1/verification/report/{manuscript_id}?section_id={lit_sec['id']}")
    assert verif_resp.status_code == 200
    report = verif_resp.json()
    assert report["total_claims"] > 0
    assert "accuracy_score" in report

    # 7. FR-10: Polish Prose with Academic Writing Assistance
    sample_text = "It is important to note that basically our method showed very good results due to the fact that we look into evidence."
    polish_resp = client.post("/api/v1/writing/polish", json={
        "text": sample_text,
        "mode": "academic_tone",
        "preserve_citations": True
    })
    assert polish_resp.status_code == 200
    polished = polish_resp.json()
    assert "robust" in polished["revised_text"] or "investigate" in polished["revised_text"]
    assert len(polished["diff_segments"]) > 0

    # 8. FR-15: Export Manuscript in DOCX, Markdown, and BibTeX
    # DOCX
    docx_resp = client.post("/api/v1/export", json={
        "manuscript_id": manuscript_id,
        "export_format": "docx",
        "citation_style": "APA",
        "include_verification_appendix": True
    })
    assert docx_resp.status_code == 200
    docx_data = docx_resp.json()
    assert docx_data["filename"].endswith(".docx")

    # Download DOCX
    download_resp = client.get(docx_data["download_url"])
    assert download_resp.status_code == 200

    # Markdown
    md_resp = client.post("/api/v1/export", json={
        "manuscript_id": manuscript_id,
        "export_format": "markdown",
        "citation_style": "IEEE",
        "include_verification_appendix": True
    })
    assert md_resp.status_code == 200
    md_data = md_resp.json()
    assert md_data["filename"].endswith(".md")

    # BibTeX
    bib_resp = client.post("/api/v1/export", json={
        "manuscript_id": manuscript_id,
        "export_format": "bibtex"
    })
    assert bib_resp.status_code == 200
    bib_data = bib_resp.json()
    assert bib_data["filename"].endswith(".bib")
