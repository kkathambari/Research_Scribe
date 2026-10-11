from app.services.citation_formatter import citation_formatter

def test_in_text_citations():
    authors = "Ashish Vaswani, Noam Shazeer, Niki Parmar"
    year = 2017
    key = "Vaswani2017"

    # APA
    apa = citation_formatter.format_in_text(key, authors, year, "APA")
    assert apa == "(Vaswani et al., 2017)"

    # IEEE
    ieee = citation_formatter.format_in_text(key, authors, year, "IEEE", index=1)
    assert ieee == "[1]"

    # Harvard
    harvard = citation_formatter.format_in_text(key, authors, year, "Harvard")
    assert harvard == "(Vaswani et al. 2017)"

    # Vancouver
    vancouver = citation_formatter.format_in_text(key, authors, year, "Vancouver", index=1)
    assert vancouver == "(1)"

def test_bibliography_formatting():
    source = {
        "title": "Attention Is All You Need",
        "authors": "Ashish Vaswani, Noam Shazeer",
        "year": 2017,
        "venue": "NeurIPS",
        "doi": "https://doi.org/10.48550/arXiv.1706.03762"
    }

    entry_apa = citation_formatter.format_bibliography_entry(source, "APA")
    assert "Attention Is All You Need" in entry_apa
    assert "(2017)" in entry_apa

    entry_ieee = citation_formatter.format_bibliography_entry(source, "IEEE", index=1)
    assert "[1]" in entry_ieee
    assert "Attention Is All You Need" in entry_ieee

def test_bibtex_generation():
    sources = [{
        "citation_key": "Vaswani2017",
        "title": "Attention Is All You Need",
        "authors": "Ashish Vaswani, Noam Shazeer",
        "year": 2017,
        "venue": "NeurIPS"
    }]
    bib = citation_formatter.generate_bibtex(sources)
    assert "@article{Vaswani2017," in bib
    assert "Attention Is All You Need" in bib
