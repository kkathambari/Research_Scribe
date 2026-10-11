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

    def format_bibliography_entry(self, source: Dict[str, Any], style: str = "APA", index: int = 1) -> str:
        """
        Formats full reference entry according to specified style.
        """
        style = (style or "APA").upper()
        title = source.get("title") or "Untitled work"
        authors = source.get("authors") or "Unknown Author"
        year = source.get("year") or "n.d."
        venue = source.get("venue") or ""
        doi = source.get("doi") or ""
        url = source.get("url") or ""

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

    def format_bibliography(self, sources: List[Dict[str, Any]], style: str = "APA") -> List[str]:
        """Formats a list of sources into bibliography strings."""
        return [self.format_bibliography_entry(s, style=style, index=i) for i, s in enumerate(sources, 1)]

    def generate_bibtex(self, sources: List[Dict[str, Any]]) -> str:
        """Generates standard BibTeX formatted string for all sources."""
        entries = []
        for s in sources:
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
