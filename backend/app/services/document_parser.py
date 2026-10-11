import os
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
import pypdf

class DocumentParserService:
    """PDF Text Extraction & Layout Identification with Page Tracking."""

    MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024 # 50 MB

    def parse_pdf(self, file_path: Path) -> Dict[str, Any]:
        """
        Parses a PDF file.
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
            warnings.append("Document appears to be image-based/scanned. OCR processing may be required for full fidelity.")
        if page_count == 0:
            warnings.append("Document contains 0 pages.")

        # Identify structural sections from headers
        sections = self._detect_sections(pages_data)

        return {
            "page_count": page_count,
            "extracted_text": extracted_text,
            "pages": pages_data,
            "sections": sections,
            "ocr_required": ocr_required,
            "warnings": warnings
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
            (r'^\s*(?:3\.?\s+)?(?:III\.?\s+)?methodology\b|methods?\b|proposed\s+approach\b', "Methodology"),
            (r'^\s*(?:4\.?\s+)?(?:IV\.?\s+)?experiments?\b|experimental\s+setup\b', "Experiments"),
            (r'^\s*(?:5\.?\s+)?(?:V\.?\s+)?results?\b|evaluation\b', "Results"),
            (r'^\s*(?:6\.?\s+)?(?:VI\.?\s+)?discussion\b|analysis\b', "Discussion"),
            (r'^\s*(?:7\.?\s+)?(?:VII\.?\s+)?limitations?\b', "Limitations"),
            (r'^\s*(?:8\.?\s+)?(?:VIII\.?\s+)?conclusions?\b|future\s+work\b', "Conclusion"),
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
