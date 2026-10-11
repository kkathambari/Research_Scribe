from app.services.verification_engine import citation_verifier

def test_verification_engine_scenarios():
    sources = [{
        "id": "src-1",
        "citation_key": "Vaswani2017",
        "title": "Attention Is All You Need",
        "authors": "Ashish Vaswani, Noam Shazeer",
        "year": 2017,
        "abstract": "We propose the Transformer, a model architecture eschewing recurrence and relying entirely on an attention mechanism."
    }]

    evidences = [{
        "id": "ev-1",
        "source_id": "src-1",
        "passage_text": "The Transformer achieves 28.4 BLEU on the WMT 2014 English-to-German translation task, improving over the existing best results.",
        "page_number": 6,
        "category": "finding",
        "confidence": 0.95
    }]

    # Scenario 1: Supported claim with verbatim citation
    text_supported = "The model establishes state-of-the-art results, achieving 28.4 BLEU on the English-to-German translation task (Vaswani et al., 2017)."
    res1 = citation_verifier.verify_section_content("m1", "s1", text_supported, sources, evidences)
    assert res1["supported_count"] >= 1
    assert res1["claims"][0]["status"] == "supported"
    assert res1["claims"][0]["citations"][0]["evidence_id"] == "ev-1"

    # Scenario 2: Citation missing on empirical statement
    text_missing = "Empirical benchmarks indicate that the framework outperforms existing baselines by 45% in translation accuracy."
    res2 = citation_verifier.verify_section_content("m1", "s1", text_missing, sources, evidences)
    assert res2["citation_missing_count"] >= 1
    assert res2["claims"][0]["status"] == "citation_missing"

    # Scenario 3: Unverified / unknown citation
    text_unknown = "The model was pre-trained using masked language modeling on 100GB of text (Smith et al., 2025)."
    res3 = citation_verifier.verify_section_content("m1", "s1", text_unknown, sources, evidences)
    assert res3["unverified_count"] >= 1
    assert res3["claims"][0]["status"] == "unverified"
