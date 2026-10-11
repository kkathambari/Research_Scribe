import re
import difflib
from typing import List, Dict, Any
from app.schemas.writing import PolishResponse, DiffSegment

class AcademicRewriterService:
    """Academic prose enhancement preserving factual attributions and citations."""

    ACADEMIC_SUBSTITUTIONS = {
        r'\ba lot of\b': 'a substantial volume of',
        r'\bvery good\b': 'robust',
        r'\bgood\b': 'advantageous',
        r'\bbad\b': 'suboptimal',
        r'\blook into\b': 'investigate',
        r'\bfind out\b': 'determine',
        r'\bget\b': 'obtain',
        r'\bshowed\b': 'demonstrated',
        r'\bbasically\b': 'fundamentally',
        r'\bin order to\b': 'to',
        r'\bit is important to note that\b': 'notably,',
        r'\bdue to the fact that\b': 'because',
        r'\bat the present time\b': 'currently',
        r'\ba big problem\b': 'a significant challenge',
        r'\bmakes it easier\b': 'facilitates',
        r'\bcomes from\b': 'originates from'
    }

    def polish(self, text: str, mode: str = "clarity", preserve_citations: bool = True) -> PolishResponse:
        """
        Refines text according to chosen academic writing dimension while preserving citations.
        """
        # Save citations with placeholders to avoid altering citation keys or numbers
        citation_placeholders = {}
        processed_text = text

        if preserve_citations:
            counter = 0
            # Pattern matching citations
            pat = r'(\([A-Za-z0-9\s,\.&-]+\d{4}[a-z]?\)|\[\d+(?:\s*,\s*\d+)*\]|\[[A-Za-z0-9]+\])'
            def replace_cite(match):
                nonlocal counter
                token = f"__CITE_TOKEN_{counter}__"
                citation_placeholders[token] = match.group(0)
                counter += 1
                return token

            processed_text = re.sub(pat, replace_cite, processed_text)

        revised = processed_text

        if mode == "conciseness":
            revised = self._apply_conciseness(revised)
            summary = "Eliminated redundant phraseology and tightened sentence structures."
        elif mode == "academic_tone":
            revised = self._apply_academic_tone(revised)
            summary = "Elevated colloquial phrasing to formal academic vocabulary."
        elif mode == "coherence":
            revised = self._apply_coherence(revised)
            summary = "Enhanced logical discourse transitions and rhetorical cohesion."
        else: # clarity & sentence variety
            revised = self._apply_clarity(revised)
            summary = "Streamlined clause structures and enhanced syntactic clarity."

        # Restore citation placeholders
        for token, original_cite in citation_placeholders.items():
            revised = revised.replace(token, original_cite)

        # Generate word-level diff segments
        diff_segments = self._generate_diff(text, revised)

        return PolishResponse(
            original_text=text,
            revised_text=revised,
            mode=mode,
            changes_summary=summary,
            diff_segments=diff_segments
        )

    def _apply_academic_tone(self, text: str) -> str:
        for pat, repl in self.ACADEMIC_SUBSTITUTIONS.items():
            text = re.sub(pat, repl, text, flags=re.IGNORECASE)
        return text

    def _apply_conciseness(self, text: str) -> str:
        text = re.sub(r'\bin order to\b', 'to', text, flags=re.IGNORECASE)
        text = re.sub(r'\bit is evident that\b', 'evidently,', text, flags=re.IGNORECASE)
        text = re.sub(r'\ba majority of\b', 'most', text, flags=re.IGNORECASE)
        text = re.sub(r'\bfor the purpose of\b', 'for', text, flags=re.IGNORECASE)
        text = re.sub(r'\bhas the ability to\b', 'can', text, flags=re.IGNORECASE)
        return text

    def _apply_coherence(self, text: str) -> str:
        text = self._apply_academic_tone(text)
        # Smooth abrupt sentences
        sentences = re.split(r'(?<=[.!?])\s+', text)
        if len(sentences) > 2 and not sentences[1].startswith(("However", "Furthermore", "Moreover", "Consequently")):
            sentences[1] = "Furthermore, " + sentences[1][0].lower() + sentences[1][1:]
        return " ".join(sentences)

    def _apply_clarity(self, text: str) -> str:
        text = self._apply_academic_tone(text)
        # Collapse double passive constructions
        text = re.sub(r'\bwas found to be\b', 'was', text, flags=re.IGNORECASE)
        text = re.sub(r'\bis able to be utilized\b', 'can be utilized', text, flags=re.IGNORECASE)
        return text

    def _generate_diff(self, old: str, new: str) -> List[DiffSegment]:
        matcher = difflib.SequenceMatcher(None, old.split(), new.split())
        segments = []
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'equal':
                segments.append(DiffSegment(type="unchanged", text=" ".join(old.split()[i1:i2]) + " "))
            elif tag == 'delete':
                segments.append(DiffSegment(type="removed", text=" ".join(old.split()[i1:i2]) + " "))
            elif tag == 'insert':
                segments.append(DiffSegment(type="added", text=" ".join(new.split()[j1:j2]) + " "))
            elif tag == 'replace':
                segments.append(DiffSegment(type="removed", text=" ".join(old.split()[i1:i2]) + " "))
                segments.append(DiffSegment(type="added", text=" ".join(new.split()[j1:j2]) + " "))
        return segments

academic_rewriter = AcademicRewriterService()
