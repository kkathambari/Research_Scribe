import os
import io
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
import pypdf

class DocumentParserService:
    """PDF Text Extraction & Layout Identification with Page Tracking."""

    MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024 # 50 MB

    def parse_pdf(self, file_path_or_bytes: Union[Path, str, bytes]) -> Dict[str, Any]:
        """
        Parses a PDF file from Path or in-memory bytes.
        Returns:
            {
                "page_count": int,
                "extracted_text": str,
                "pages": [{"page_number": int, "text": str}],
                "sections": [{"title": str, "page_number": int, "content": str}],
                "ocr_required": bool,
                "warnings": list[str]
            }
        """
        reader = None
        file_path = None
        if isinstance(file_path_or_bytes, bytes):
            if len(file_path_or_bytes) > self.MAX_FILE_SIZE_BYTES:
                raise ValueError(f"File exceeds maximum allowed size of 50MB ({len(file_path_or_bytes)} bytes)")
            try:
                reader = pypdf.PdfReader(io.BytesIO(file_path_or_bytes))
            except Exception as e:
                raise ValueError(f"Could not read PDF: {str(e)}")
        else:
            file_path = Path(file_path_or_bytes)
            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            file_size = os.path.getsize(file_path)
            if file_size > self.MAX_FILE_SIZE_BYTES:
                raise ValueError(f"File exceeds maximum allowed size of 50MB ({file_size} bytes)")
            try:
                reader = pypdf.PdfReader(str(file_path))
            except Exception as e:
                raise ValueError(f"Could not read PDF: {str(e)}")

        page_count = len(reader.pages)
        pages_data = []
        full_text_parts = []
        total_chars = 0
        low_text_pages = 0

        for i, page in enumerate(reader.pages):
            page_num = i + 1
            try:
                page_text = page.extract_text() or ""
            except Exception:
                page_text = ""

            cleaned_text = self._clean_text(page_text)
            pages_data.append({
                "page_number": page_num,
                "text": cleaned_text
            })
            if cleaned_text:
                full_text_parts.append(f"--- [Page {page_num}] ---\n" + cleaned_text)
                total_chars += len(cleaned_text)
            
            if len(cleaned_text.strip()) < 50:
                low_text_pages += 1

        extracted_text = "\n\n".join(full_text_parts)
        
        # Scanned PDF detection (if more than 60% of pages have less than 50 characters)
        ocr_required = (page_count > 0 and (low_text_pages / page_count) > 0.6) or (total_chars < 100 and page_count > 0)
        
        warnings = []
        if ocr_required:
            ocr_msg = "OCR processing required: Document appears to be image-based/scanned with no extractable text layer. Automatic OCR engine is required but currently unavailable."
            warnings.append(ocr_msg)
            if not extracted_text.strip():
                extracted_text = ocr_msg
        if page_count == 0:
            warnings.append("Document contains 0 pages.")

        # Identify structural sections from headers
        sections = self._detect_sections(pages_data)

        # Extract bibliographic metadata from the first few pages
        first_pages_text = "\n".join(p["text"] for p in pages_data[:3])
        metadata = self.extract_pdf_metadata(file_path_or_bytes if isinstance(file_path_or_bytes, bytes) else file_path, first_pages_text=first_pages_text)

        return {
            "page_count": page_count,
            "extracted_text": extracted_text,
            "pages": pages_data,
            "sections": sections,
            "ocr_required": ocr_required,
            "warnings": warnings,
            "metadata": metadata
        }

    def extract_pdf_metadata(self, file_path_or_bytes: Optional[Union[Path, str, bytes]] = None, first_pages_text: Optional[str] = None) -> Dict[str, Any]:
        """Extracts DOI, title, authors, and year heuristics from PDF first pages and document info."""
        doi = None
        title = None
        year = None
        authors = None

        text_to_search = first_pages_text or ""
        reader = None
        if isinstance(file_path_or_bytes, bytes):
            try:
                reader = pypdf.PdfReader(io.BytesIO(file_path_or_bytes))
            except Exception:
                pass
        elif file_path_or_bytes is not None:
            fp = Path(file_path_or_bytes)
            if fp.exists():
                try:
                    reader = pypdf.PdfReader(str(fp))
                except Exception:
                    pass

        if reader:
            if not text_to_search:
                parts = []
                for p in reader.pages[:3]:
                    parts.append(p.extract_text() or "")
                text_to_search = "\n".join(parts)

            # Check pypdf metadata dictionary
            if reader.metadata:
                if reader.metadata.title and str(reader.metadata.title).strip().lower() not in ("untitled", "document", "none", ""):
                    title = str(reader.metadata.title).strip()
                if reader.metadata.author:
                    authors = str(reader.metadata.author).strip()

        # 1. DOI regex extraction (e.g. 10.1145/..., 10.1016/..., 10.48550/arXiv...)
        doi_match = re.search(r'\b(10\.\d{4,9}/[^\s"<>]+)', text_to_search)
        if doi_match:
            raw_doi = doi_match.group(1).rstrip('.,;()[]{}')
            doi = raw_doi

        # 2. Year extraction
        year_matches = re.findall(r'\b(19\d\d|20[0-2]\d)\b', text_to_search)
        if year_matches:
            # Prefer recent year
            valid_years = [int(y) for y in year_matches if 1970 <= int(y) <= 2030]
            if valid_years:
                year = valid_years[0]

        # 3. Title heuristic from text if not extracted from PDF metadata
        if not title and text_to_search:
            lines = [l.strip() for l in text_to_search.split("\n") if l.strip()]
            for line in lines[:10]:
                # Skip common journal headers / metadata lines
                if re.match(r'^(?:doi|arxiv|issn|volume|issue|proceedings|http|page|\d+)\b', line, re.IGNORECASE):
                    continue
                if len(line.split()) >= 3 and len(line) <= 200:
                    title = line
                    break

        return {
            "doi": doi,
            "title": title,
            "year": year,
            "authors": authors
        }

    def _clean_text(self, text: str) -> str:
        if not text:
            return ""
        # Remove null bytes and non-printable characters
        text = text.replace("\x00", "")
        # Normalize newlines
        text = re.sub(r'\r\n|\r', '\n', text)
        # Fix hyphenated line breaks (e.g. trans-\nformation -> transformation)
        text = re.sub(r'(\w+)-\n(\w+)', r'\1\2', text)
        # Collapse excessive whitespace
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()

    def _detect_sections(self, pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identifies standard academic sections (Abstract, Introduction, Method, etc.)."""
        section_patterns = [
            (r'^\s*(?:1\.?\s+)?(?:I\.?\s+)?abstract\b', "Abstract"),
            (r'^\s*(?:1\.?\s+)?(?:I\.?\s+)?introduction\b', "Introduction"),
            (r'^\s*(?:2\.?\s+)?(?:II\.?\s+)?related\s+work\b|literature\s+review\b', "Related Work"),
            (r'^\s*(?:3\.?\s+)?(?:III\.?\s+)?research\s+problems?|problem\s+formulation\b', "Research Problem"),
            (r'^\s*(?:3\.?\s+)?(?:III\.?\s+)?methodology\b|methods?\b|proposed\s+approach\b', "Methodology"),
            (r'^\s*(?:4\.?\s+)?(?:IV\.?\s+)?experiments?\b|experimental\s+setup\b|datasets?\b', "Experiments"),
            (r'^\s*(?:5\.?\s+)?(?:V\.?\s+)?results?\b|evaluation\b|findings\b', "Results"),
            (r'^\s*(?:6\.?\s+)?(?:VI\.?\s+)?discussion\b|analysis\b', "Discussion"),
            (r'^\s*(?:7\.?\s+)?(?:VII\.?\s+)?limitations?\b|research\s+gaps?\b', "Limitations"),
            (r'^\s*(?:8\.?\s+)?(?:VIII\.?\s+)?conclusions?\b|future\s+(?:work|directions?)\b', "Conclusion"),
            (r'^\s*(?:references?|bibliography)\b', "References")
        ]

        detected = []
        current_section = "Introductory Material"
        current_content = []
        start_page = 1

        for p in pages:
            lines = p["text"].split("\n")
            for line in lines:
                matched_title = None
                for pat, title in section_patterns:
                    if re.match(pat, line.strip(), re.IGNORECASE):
                        matched_title = title
                        break
                
                if matched_title:
                    if current_content:
                        detected.append({
                            "title": current_section,
                            "page_number": start_page,
                            "content": "\n".join(current_content).strip()
                        })
                    current_section = matched_title
                    current_content = []
                    start_page = p["page_number"]
                else:
                    current_content.append(line)

        if current_content:
            detected.append({
                "title": current_section,
                "page_number": start_page,
                "content": "\n".join(current_content).strip()
            })

        return detected

document_parser = DocumentParserService()
