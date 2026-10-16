import re
import logging
from typing import List, Dict, Any, Optional
import httpx
from app.schemas.source import ScholarlySearchResultItem, ScholarlySearchResponse

logger = logging.getLogger(__name__)

def generate_citation_key(authors: Optional[str], year: Optional[int], title: str) -> str:
    """Generate a clean BibTeX/citation key, e.g. 'Vaswani2017' or 'Devlin2019'"""
    first_author = "Unknown"
    if authors:
        # Extract first author surname
        first_part = authors.split(",")[0].strip()
        parts = first_part.split()
        if parts:
            first_author = parts[-1]
    # Clean non-alphanumeric
    clean_author = re.sub(r'[^a-zA-Z]', '', first_author)
    clean_author = clean_author.capitalize() if clean_author else "Author"

    yr = str(year) if year else "n.d."
    return f"{clean_author}{yr}"

class ScholarlyRetrievalService:
    """
    Retrieves academic papers from OpenAlex and CrossRef APIs conforming to SRS v3.0 (FR-09).
    Guarantees strict compliance with the 'No-Fabricated-Citations' principle:
    never returns invented or simulated bibliographic records when searches fail.
    """

    OPENALEX_URL = "https://api.openalex.org/works"
    CROSSREF_URL = "https://api.crossref.org/works"

    # Verifiable landmark open-access publications strictly reserved for offline testing fixtures
    TEST_FIXTURE_ARCHIVE = [
        ScholarlySearchResultItem(
            title="Attention Is All You Need",
            authors="Ashish Vaswani, Noam Shazeer, Niki Parmar, Jakob Uszkoreit, Llion Jones, Aidan N. Gomez, Łukasz Kaiser, Illia Polosukhin",
            year=2017,
            venue="Advances in Neural Information Processing Systems (NeurIPS 2017)",
            doi="https://doi.org/10.48550/arXiv.1706.03762",
            url="https://arxiv.org/abs/1706.03762",
            abstract="The dominant sequence transduction models are based on complex recurrent or convolutional neural networks. We propose the Transformer, a model architecture eschewing recurrence and relying entirely on an attention mechanism to draw global dependencies between input and output.",
            access_status="open",
            citation_count=105000,
            source_provider="verified_archive",
            citation_key="Vaswani2017"
        ),
        ScholarlySearchResultItem(
            title="BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding",
            authors="Jacob Devlin, Ming-Wei Chang, Kenton Lee, Kristina Toutanova",
            year=2019,
            venue="Proceedings of NAACL-HLT 2019",
            doi="https://doi.org/10.18653/v1/N19-1423",
            url="https://arxiv.org/abs/1810.04805",
            abstract="We introduce a new language representation model called BERT, which stands for Bidirectional Encoder Representations from Transformers. Unlike recent language representation models, BERT is designed to pre-train deep bidirectional representations from unlabeled text.",
            access_status="open",
            citation_count=92000,
            source_provider="verified_archive",
            citation_key="Devlin2019"
        ),
        ScholarlySearchResultItem(
            title="Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks",
            authors="Patrick Lewis, Ethan Perez, Aleksandara Piktus, Fabio Petroni, Vladimir Karpukhin, Naman Goyal, Heinrich Küttler, Mike Lewis, Wen-tau Yih, Tim Rocktäschel, Sebastian Riedel, Douwe Kiela",
            year=2020,
            venue="Advances in Neural Information Processing Systems (NeurIPS 2020)",
            doi="https://doi.org/10.48550/arXiv.2005.11401",
            url="https://arxiv.org/abs/2005.11401",
            abstract="Large pre-trained language models have been shown to store factual knowledge in their parameters. However, their ability to access and precisely manipulate knowledge is still limited. We explore retrieval-augmented generation (RAG) architectures that combine parametric and non-parametric memory.",
            access_status="open",
            citation_count=8500,
            source_provider="verified_archive",
            citation_key="Lewis2020"
        )
    ]

    async def lookup_doi(self, doi: str, allow_test_fixtures: bool = False) -> Optional[ScholarlySearchResultItem]:
        """Directly queries Crossref and OpenAlex for an exact DOI resolution."""
        if not doi:
            return None
        # Normalize DOI
        clean_doi = re.sub(r'^(?:https?://(?:dx\.)?doi\.org/|doi:)', '', doi.strip(), flags=re.IGNORECASE).strip()
        if not clean_doi:
            return None

        # Check offline fixtures first if permitted
        if allow_test_fixtures:
            for fix in self.TEST_FIXTURE_ARCHIVE:
                if fix.doi and clean_doi.lower() in fix.doi.lower():
                    return fix

        headers = {"User-Agent": "ResearchScribe/3.0 (mailto:authors@researchscribe.org)"}

        # 1. Try Crossref direct DOI endpoint
        try:
            url = f"{self.CROSSREF_URL}/{clean_doi}"
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(url, headers=headers)
                if resp.status_code == 200:
                    data = resp.json().get("message", {})
                    title_list = data.get("title", [])
                    title = title_list[0] if title_list else "Untitled"
                    authors_list = []
                    for auth in data.get("author", []):
                        given = auth.get("given", "")
                        family = auth.get("family", "")
                        name = f"{given} {family}".strip()
                        if name:
                            authors_list.append(name)
                    authors_str = ", ".join(authors_list) if authors_list else "Unknown Authors"
                    issued = data.get("issued", {}).get("date-parts", [[]])[0]
                    year = issued[0] if issued else None
                    venue_list = data.get("container-title", [])
                    venue = venue_list[0] if venue_list else "Scholarly Publication"
                    cit_key = generate_citation_key(authors_str, year, title)

                    return ScholarlySearchResultItem(
                        title=title,
                        authors=authors_str,
                        year=year,
                        venue=venue,
                        doi=f"https://doi.org/{clean_doi}",
                        url=data.get("URL") or f"https://doi.org/{clean_doi}",
                        abstract=re.sub(r'<[^>]+>', '', data.get("abstract", "")).strip() or None,
                        access_status="open",
                        citation_count=data.get("is-referenced-by-count", 0),
                        source_provider="crossref",
                        citation_key=cit_key,
                        verified_metadata=True
                    )
        except Exception as e:
            logger.debug(f"Direct Crossref DOI lookup failed: {e}")

        # 2. Try OpenAlex direct DOI
        try:
            url = f"{self.OPENALEX_URL}/https://doi.org/{clean_doi}"
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(url, headers=headers)
                if resp.status_code == 200:
                    work = resp.json()
                    title = work.get("title") or "Untitled"
                    authors_list = [auth.get("author", {}).get("display_name") for auth in work.get("authorships", []) if auth.get("author", {}).get("display_name")]
                    authors_str = ", ".join(authors_list) if authors_list else "Unknown Authors"
                    year = work.get("publication_year")
                    venue = work.get("primary_location", {}).get("source", {}).get("display_name") or "Scholarly Publication"
                    cit_key = generate_citation_key(authors_str, year, title)
                    abstract = self._reconstruct_openalex_abstract(work.get("abstract_inverted_index"))

                    return ScholarlySearchResultItem(
                        title=title,
                        authors=authors_str,
                        year=year,
                        venue=venue,
                        doi=f"https://doi.org/{clean_doi}",
                        url=work.get("primary_location", {}).get("landing_page_url") or f"https://doi.org/{clean_doi}",
                        abstract=abstract,
                        access_status="open" if work.get("open_access", {}).get("is_oa") else "restricted",
                        citation_count=work.get("cited_by_count", 0),
                        source_provider="openalex",
                        citation_key=cit_key,
                        verified_metadata=True
                    )
        except Exception as e:
            logger.debug(f"Direct OpenAlex DOI lookup failed: {e}")

        return None

    def compare_metadata(self, extracted: Dict[str, Any], bibliographic: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compares metadata extracted from a PDF against stored/authoritative bibliographic metadata.
        Returns match status and any identified discrepancies.
        """
        mismatches = []
        ext_doi = extracted.get("doi")
        bib_doi = bibliographic.get("doi")

        if ext_doi and bib_doi:
            clean_ext = re.sub(r'^(?:https?://(?:dx\.)?doi\.org/|doi:)', '', ext_doi.strip(), flags=re.IGNORECASE).strip().lower()
            clean_bib = re.sub(r'^(?:https?://(?:dx\.)?doi\.org/|doi:)', '', bib_doi.strip(), flags=re.IGNORECASE).strip().lower()
            if clean_ext != clean_bib:
                mismatches.append(f"DOI mismatch: Extracted '{ext_doi}' differs from bibliographic DOI '{bib_doi}'.")

        ext_year = extracted.get("year")
        bib_year = bibliographic.get("year")
        if ext_year and bib_year:
            try:
                if abs(int(ext_year) - int(bib_year)) > 1:
                    mismatches.append(f"Publication year discrepancy: PDF indicates {ext_year} while record indicates {bib_year}.")
            except (ValueError, TypeError):
                pass

        ext_title = (extracted.get("title") or "").strip().lower()
        bib_title = (bibliographic.get("title") or "").strip().lower()
        if ext_title and bib_title and len(ext_title) > 10 and len(bib_title) > 10:
            words_ext = set(re.findall(r'\b[a-z]{3,}\b', ext_title))
            words_bib = set(re.findall(r'\b[a-z]{3,}\b', bib_title))
            if words_ext and words_bib:
                overlap = len(words_ext.intersection(words_bib)) / max(len(words_ext), len(words_bib))
                if overlap < 0.25:
                    mismatches.append(f"Title divergence: Extracted title '{extracted.get('title')}' has low similarity with '{bibliographic.get('title')}'.")

        is_match = len(mismatches) == 0
        status = "verified" if is_match else "mismatch_flagged"
        return {
            "is_match": is_match,
            "status": status,
            "mismatches": mismatches,
            "explanation": "; ".join(mismatches) if mismatches else "Metadata verified and aligned."
        }

    async def search(
        self,
        query: str,
        limit: int = 10,
        year_start: Optional[int] = None,
        year_end: Optional[int] = None,
        allow_test_fixtures: bool = False
    ) -> ScholarlySearchResponse:
        """
        Executes scholarly literature search against OpenAlex and Crossref.
        Returns an explicit retrieval_unavailable or empty list if no genuine papers are found.
        """
        results: List[ScholarlySearchResultItem] = []
        apis_reached = False

        # If query is a DOI, attempt exact DOI resolution first
        if "10." in query and "/" in query:
            doi_candidate = re.search(r'10\.\d{4,9}/[^\s"<>]+', query)
            if doi_candidate:
                exact_paper = await self.lookup_doi(doi_candidate.group(0), allow_test_fixtures=allow_test_fixtures)
                if exact_paper:
                    return ScholarlySearchResponse(
                        query=query,
                        total=1,
                        results=[exact_paper],
                        retrieval_status="success"
                    )

        # 1. Query OpenAlex (rich metadata, open access links, inverted index abstracts)
        try:
            openalex_results = await self._search_openalex(query, limit, year_start, year_end)
            if openalex_results:
                results.extend(openalex_results)
                apis_reached = True
        except Exception as e:
            logger.debug(f"OpenAlex query failed: {e}")

        # 2. Query Crossref if additional records needed
        if len(results) < limit:
            try:
                crossref_results = await self._search_crossref(query, limit - len(results), year_start, year_end)
                if crossref_results:
                    apis_reached = True
                # Deduplicate by DOI and normalized title
                existing_dois = {r.doi.lower().strip() for r in results if r.doi}
                existing_titles = {r.title.lower().strip() for r in results}
                for cr in crossref_results:
                    if cr.doi and cr.doi.lower().strip() in existing_dois:
                        continue
                    if cr.title.lower().strip() in existing_titles:
                        continue
                    results.append(cr)
            except Exception as e:
                logger.debug(f"Crossref query failed: {e}")

        # Critical Integrity: If APIs were unreachable or returned no genuine publications,
        # never fabricate imaginary authors or papers.
        if not results:
            if allow_test_fixtures:
                q_lower = query.lower()
                matched_fixtures = [
                    f for f in self.TEST_FIXTURE_ARCHIVE
                    if any(w in f.title.lower() or w in (f.abstract or "").lower() for w in q_lower.split() if len(w) > 3)
                ]
                if matched_fixtures:
                    labeled_fixtures = []
                    for fix in matched_fixtures[:limit]:
                        labeled_fixtures.append(ScholarlySearchResultItem(
                            title=f"[Archive Fallback] {fix.title}",
                            authors=fix.authors,
                            year=fix.year,
                            venue=f"{fix.venue} (Offline Archive)",
                            doi=fix.doi,
                            citation_key=fix.citation_key,
                            abstract=fix.abstract,
                            citation_count=fix.citation_count,
                            access_status=fix.access_status,
                            url=fix.url
                        ))
                    return ScholarlySearchResponse(
                        query=query,
                        total=len(labeled_fixtures),
                        results=labeled_fixtures,
                        retrieval_status="verified_archive_fallback"
                    )

            status = "no_results_found" if apis_reached else "retrieval_unavailable"
            return ScholarlySearchResponse(
                query=query,
                total=0,
                results=[],
                retrieval_status=status
            )

        return ScholarlySearchResponse(
            query=query,
            total=len(results),
            results=results[:limit],
            retrieval_status="success"
        )

    async def _search_openalex(self, query: str, limit: int, year_start: Optional[int], year_end: Optional[int]) -> List[ScholarlySearchResultItem]:
        params: Dict[str, Any] = {
            "search": query,
            "per-page": limit,
            "sort": "relevance_score:desc"
        }
        filters = []
        if year_start and year_end:
            filters.append(f"publication_year:{year_start}-{year_end}")
        elif year_start:
            filters.append(f"from_publication_date:{year_start}-01-01")
        elif year_end:
            filters.append(f"to_publication_date:{year_end}-12-31")

        if filters:
            params["filter"] = ",".join(filters)

        headers = {"User-Agent": "ResearchScribe/3.0 (mailto:authors@researchscribe.org)"}

        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(self.OPENALEX_URL, params=params, headers=headers)
            if resp.status_code != 200:
                return []

            data = resp.json()
            items = []
            for work in data.get("results", []):
                title = work.get("title") or "Untitled"
                authors_list = []
                for auth in work.get("authorships", []):
                    raw_name = auth.get("author", {}).get("display_name")
                    if raw_name:
                        authors_list.append(raw_name)
                authors_str = ", ".join(authors_list) if authors_list else "Unknown Authors"

                year = work.get("publication_year")
                venue = work.get("primary_location", {}).get("source", {}).get("display_name") or "Scholarly Publication"
                doi = work.get("doi")
                url = work.get("primary_location", {}).get("landing_page_url") or doi
                citation_count = work.get("cited_by_count", 0)

                abstract = self._reconstruct_openalex_abstract(work.get("abstract_inverted_index"))
                access_status = "open" if work.get("open_access", {}).get("is_oa") else "restricted"
                citation_key = generate_citation_key(authors_str, year, title)

                items.append(ScholarlySearchResultItem(
                    title=title,
                    authors=authors_str,
                    year=year,
                    venue=venue,
                    doi=doi,
                    url=url,
                    abstract=abstract,
                    access_status=access_status,
                    citation_count=citation_count,
                    source_provider="openalex",
                    citation_key=citation_key
                ))
            return items

    def _reconstruct_openalex_abstract(self, inverted_index: Optional[Dict[str, List[int]]]) -> Optional[str]:
        if not inverted_index:
            return None
        try:
            position_word = {}
            for word, positions in inverted_index.items():
                for pos in positions:
                    position_word[pos] = word
            sorted_words = [position_word[pos] for pos in sorted(position_word.keys())]
            return " ".join(sorted_words)
        except Exception:
            return None

    async def _search_crossref(self, query: str, limit: int, year_start: Optional[int], year_end: Optional[int]) -> List[ScholarlySearchResultItem]:
        params: Dict[str, Any] = {
            "query": query,
            "rows": limit
        }
        headers = {"User-Agent": "ResearchScribe/3.0 (mailto:authors@researchscribe.org)"}

        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(self.CROSSREF_URL, params=params, headers=headers)
            if resp.status_code != 200:
                return []

            data = resp.json()
            items = []
            for work in data.get("message", {}).get("items", []):
                title_list = work.get("title", [])
                title = title_list[0] if title_list else "Untitled"

                authors_list = []
                for auth in work.get("author", []):
                    given = auth.get("given", "")
                    family = auth.get("family", "")
                    name = f"{given} {family}".strip()
                    if name:
                        authors_list.append(name)
                authors_str = ", ".join(authors_list) if authors_list else "Unknown Authors"

                issued = work.get("issued", {}).get("date-parts", [[]])[0]
                year = issued[0] if issued else None

                venue_list = work.get("container-title", [])
                venue = venue_list[0] if venue_list else "Scholarly Publication"
                doi = work.get("DOI")
                if doi and not doi.startswith("http"):
                    doi = f"https://doi.org/{doi}"
                url = work.get("URL") or doi
                abstract = work.get("abstract", "")
                if abstract:
                    abstract = re.sub(r'<[^>]+>', '', abstract)

                citation_count = work.get("is-referenced-by-count", 0)
                citation_key = generate_citation_key(authors_str, year, title)

                items.append(ScholarlySearchResultItem(
                    title=title,
                    authors=authors_str,
                    year=year,
                    venue=venue,
                    doi=doi,
                    url=url,
                    abstract=abstract if abstract else None,
                    access_status="open",
                    citation_count=citation_count,
                    source_provider="crossref",
                    citation_key=citation_key
                ))
            return items

retrieval_service = ScholarlyRetrievalService()
