import re
from typing import List, Dict, Any, Optional

class CitationFormatterService:
    """Formats in-text citations and reference lists in APA, IEEE, Harvard, Vancouver, Chicago."""

    def format_in_text(self, citation_key: str, authors: Optional[str], year: Optional[int], style: str = "APA", index: int = 1) -> str:
        """
        Generates in-text citation string.
        e.g., APA -> (Vaswani et al., 2017)
              IEEE -> [1]
              Vancouver -> (1)
              Harvard -> (Vaswani et al. 2017)
              Chicago -> (Vaswani et al. 2017)
        """
        style = (style or "APA").upper()
        if style in ["IEEE"]:
            return f"[{index}]"
        elif style in ["VANCOUVER"]:
            return f"({index})"

        # Author-date family
        lead_author = self._get_short_author(authors)
        yr = str(year) if year else "n.d."

        if style == "HARVARD" or style == "CHICAGO":
            return f"({lead_author} {yr})"
        
        # Default APA
        return f"({lead_author}, {yr})"

    def _normalize_source_dict(self, s: Any) -> Dict[str, Any]:
        if isinstance(s, dict):
            return s
        d = {}
        for attr in ["id", "title", "authors", "year", "venue", "doi", "url", "citation_key"]:
            d[attr] = getattr(s, attr, None)
        return d

    def format_bibliography_entry(self, source: Any, style: str = "APA", index: int = 1) -> str:
        """
        Formats full reference entry according to specified style.
        """
        s_dict = self._normalize_source_dict(source)
        style = (style or "APA").upper()
        title = s_dict.get("title") or "Untitled work"
        authors = s_dict.get("authors") or "Unknown Author"
        year = s_dict.get("year") or "n.d."
        venue = s_dict.get("venue") or ""
        doi = s_dict.get("doi") or ""
        url = s_dict.get("url") or ""

        if style == "IEEE":
            formatted_authors = self._format_ieee_authors(authors)
            venue_part = f', {venue}' if venue else ''
            year_part = f', {year}.' if year != 'n.d.' else '.'
            doi_part = f' doi: {doi}.' if doi else ''
            return f"[{index}] {formatted_authors}, \"{title},\"{venue_part}{year_part}{doi_part}"

        elif style == "VANCOUVER":
            year_part = f'{year};' if year != 'n.d.' else 'n.d.;'
            venue_part = f' {venue}.' if venue else ''
            doi_part = f' Available from: {url or doi}' if (url or doi) else ''
            return f"{index}. {authors}. {title}.{venue_part} {year_part}{doi_part}"

        elif style == "HARVARD":
            venue_part = f', {venue}' if venue else ''
            url_part = f', viewed from <{url or doi}>' if (url or doi) else ''
            return f"{authors} ({year}) '{title}'{venue_part}{url_part}."

        elif style == "CHICAGO":
            venue_part = f' {venue}.' if venue else ''
            doi_part = f' {doi or url}.' if (doi or url) else ''
            return f"{authors}. {year}. \"{title}.\"{venue_part}{doi_part}"

        # Default APA 7th Edition
        venue_part = f" *{venue}*." if venue else ""
        doi_part = f" {doi}" if doi else (f" {url}" if url else "")
        return f"{authors} ({year}). {title}.{venue_part}{doi_part}"

    def format_bibliography(self, sources: List[Any], style: str = "APA") -> List[str]:
        """Formats a list of sources into bibliography strings with deduplication."""
        norm_sources = [self._normalize_source_dict(s) for s in sources]
        deduped = self._deduplicate_sources(norm_sources)
        return [self.format_bibliography_entry(s, style=style, index=i) for i, s in enumerate(deduped, 1)]

    def format_cited_bibliography(
        self,
        sources: List[Any],
        cited_identifiers: Optional[set] = None,
        manuscript_text: Optional[str] = None,
        style: str = "APA",
        include_all: bool = False
    ) -> List[str]:
        """
        FR-08.4: Formats reference list containing every source cited in the manuscript.
        Sources not cited in the manuscript are excluded by default unless include_all is True.
        Prevents duplicate bibliography entries.
        """
        norm_sources = [self._normalize_source_dict(s) for s in sources]
        
        if manuscript_text and not cited_identifiers:
            cited_identifiers = set(re.findall(r'\[([a-zA-Z0-9_\-]+)\]', manuscript_text))
            author_date_matches = re.findall(r'\(([A-Za-z0-9_\-]+)(?:\s+et\s+al\.?)?(?:,?\s*\d{4}[a-z]?)?\)', manuscript_text)
            cited_identifiers.update(author_date_matches)

        if include_all or not cited_identifiers:
            target_sources = norm_sources
        else:
            # Match cited_identifiers by ID, citation_key, author surname, or 1-based index
            target_sources = []
            id_set = {str(i).lower() for i in cited_identifiers}
            for idx, s in enumerate(norm_sources):
                key = (s.get("citation_key") or "").lower()
                s_id = (s.get("id") or "").lower()
                authors = (s.get("authors") or "").lower()
                index_str = str(idx + 1)
                
                matched = False
                if s_id in id_set or key in id_set or index_str in id_set:
                    matched = True
                else:
                    for author in authors.split(","):
                        surname = author.strip().split()[-1] if author.strip().split() else ""
                        if surname and surname in id_set:
                            matched = True
                            break
                if matched:
                    target_sources.append(s)

        deduped = self._deduplicate_sources(target_sources)
        return [self.format_bibliography_entry(s, style=style, index=i) for i, s in enumerate(deduped, 1)]

    def _deduplicate_sources(self, sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """FR-08.6: Identifies duplicate references and prevents duplicate bibliography entries."""
        unique_sources = []
        seen_dois = set()
        seen_titles = set()

        for s in sources:
            doi = (s.get("doi") or "").strip().lower()
            if doi.startswith("https://doi.org/"):
                doi = doi.replace("https://doi.org/", "")
            elif doi.startswith("http://dx.doi.org/"):
                doi = doi.replace("http://dx.doi.org/", "")

            title_norm = re.sub(r'[^a-z0-9]', '', (s.get("title") or "").lower())

            if doi and doi in seen_dois:
                continue
            if title_norm and len(title_norm) > 10 and title_norm in seen_titles:
                continue

            if doi:
                seen_dois.add(doi)
            if title_norm:
                seen_titles.add(title_norm)
            unique_sources.append(s)

        return unique_sources

    def reformat_manuscript_citations(
        self,
        text: str,
        old_style: str,
        new_style: str,
        sources: List[Dict[str, Any]]
    ) -> str:
        """
        Acceptance Criterion 10: Switching between supported citation styles updates
        both in-text citations and the bibliography consistently.
        """
        old_style = (old_style or "APA").upper()
        new_style = (new_style or "APA").upper()
        if old_style == new_style or not text:
            return text

        # Map each source to old in-text patterns and new in-text representation
        for idx, s in enumerate(sources):
            key = s.get("citation_key") or f"Src{idx+1}"
            lead_author = self._get_short_author(s.get("authors"))
            yr = str(s.get("year")) if s.get("year") else "n.d."

            new_in_text = self.format_in_text(key, s.get("authors"), s.get("year"), style=new_style, index=idx+1)

            # Build patterns matching the old citation for this source
            patterns_to_replace = [
                # APA: (Author et al., Year)
                rf'\({re.escape(lead_author)}(?:,?\s+et\s+al\.)?,\s+{re.escape(yr)}\)',
                # Harvard / Chicago: (Author et al. Year)
                rf'\({re.escape(lead_author)}(?:,?\s+et\s+al\.)?\s+{re.escape(yr)}\)',
                # Bracket key: [Key]
                rf'\[{re.escape(key)}\]',
                # Numeric index if changing from IEEE / Vancouver
                rf'\[{idx+1}\]',
                rf'\({idx+1}\)'
            ]

            for pat in patterns_to_replace:
                text = re.sub(pat, new_in_text, text)

        return text

    def generate_bibtex(self, sources: List[Dict[str, Any]]) -> str:
        """Generates standard BibTeX formatted string for all sources without duplicate entries."""
        deduped = self._deduplicate_sources(sources)
        entries = []
        for s in deduped:
            key = s.get("citation_key") or f"source_{s.get('id', 'item')}"
            title = s.get("title", "Untitled")
            authors = s.get("authors", "Unknown")
            year = s.get("year", "")
            venue = s.get("venue", "")
            doi = s.get("doi", "")
            url = s.get("url", "")

            entry = [
                f"@article{{{key},",
                f"  title = {{{{{title}}}}},",
                f"  author = {{{authors}}},"
            ]
            if year:
                entry.append(f"  year = {{{year}}},")
            if venue:
                entry.append(f"  journal = {{{venue}}},")
            if doi:
                entry.append(f"  doi = {{{doi}}},")
            if url:
                entry.append(f"  url = {{{url}}},")
            
            # Remove trailing comma on last item
            entry[-1] = entry[-1].rstrip(",")
            entry.append("}")
            entries.append("\n".join(entry))

        return "\n\n".join(entries)

    def _get_short_author(self, authors: Optional[str]) -> str:
        if not authors:
            return "Unknown"
        author_list = [a.strip() for a in authors.split(",") if a.strip()]
        if not author_list:
            return "Unknown"
        first_author = author_list[0].split()[-1] # Surname
        if len(author_list) == 1:
            return first_author
        elif len(author_list) == 2:
            second_author = author_list[1].split()[-1]
            return f"{first_author} & {second_author}"
        else:
            return f"{first_author} et al."

    def _format_ieee_authors(self, authors: Optional[str]) -> str:
        if not authors:
            return "Unknown Author"
        author_list = [a.strip() for a in authors.split(",") if a.strip()]
        if len(author_list) > 3:
            return f"{author_list[0]} et al."
        return ", ".join(author_list)

citation_formatter = CitationFormatterService()
