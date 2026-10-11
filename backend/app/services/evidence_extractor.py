import re
from typing import List, Dict, Any, Optional

class EvidenceExtractorService:
    """Extracts structured research evidence categorized by category with page references."""

    CATEGORY_CUES = {
        "objective": [
            r'\b(?:we propose|we present|this paper introduces|our goal is|aims to|objective of this study|we investigate)\b',
            r'\b(?:we focus on|in this work, we develop|addressing the problem of)\b'
        ],
        "method": [
            r'\b(?:we utilize|our architecture|we train|the dataset consists of|we implement|the pipeline includes)\b',
            r'\b(?:based on transformer|using fine-tuning|we employ|methodology comprises|the algorithm is evaluated)\b'
        ],
        "finding": [
            r'\b(?:we find that|results demonstrate|outperforms|achieves a new state of the art|statistically significant)\b',
            r'\b(?:shows an improvement of|accuracy of|bleu score of|our model achieves|reduces error by|empirically confirms)\b'
        ],
        "limitation": [
            r'\b(?:a limitation of|limited by|however, our approach suffers|computational overhead|one drawback is)\b',
            r'\b(?:requires substantial compute|fails when|susceptible to|our study is constrained by)\b'
        ],
        "future_work": [
            r'\b(?:future work will|we plan to explore|an avenue for future research|promising direction is)\b',
            r'\b(?:remains an open question|further investigation is needed)\b'
        ]
    }

    def extract_evidence_from_pages(self, pages: List[Dict[str, Any]], source_abstract: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Extracts classified evidence sentences with page numbers and confidence scores.
        """
        extracted: List[Dict[str, Any]] = []
        seen_passages = set()

        # 1. First process abstract if provided
        if source_abstract:
            abstract_items = self._extract_from_text(source_abstract, page_number=1, default_section="Abstract")
            for item in abstract_items:
                if item["passage_text"] not in seen_passages:
                    seen_passages.add(item["passage_text"])
                    extracted.append(item)

        # 2. Process all parsed pages
        for p in pages:
            page_num = p.get("page_number", 1)
            page_text = p.get("text", "")
            if not page_text:
                continue

            page_items = self._extract_from_text(page_text, page_number=page_num)
            for item in page_items:
                # Deduplicate similar passages
                simplified = " ".join(item["passage_text"].lower().split()[:10])
                if simplified not in seen_passages and len(item["passage_text"]) >= 40:
                    seen_passages.add(simplified)
                    extracted.append(item)

        return extracted

    def _extract_from_text(self, text: str, page_number: int = 1, default_section: Optional[str] = None) -> List[Dict[str, Any]]:
        items = []
        # Split into sentences using punctuation boundaries
        sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z0-9])', text)

        for sentence in sentences:
            sentence_clean = sentence.strip()
            if len(sentence_clean) < 30 or len(sentence_clean) > 500:
                continue

            # Classify sentence
            category, confidence = self._classify_sentence(sentence_clean)
            if category:
                items.append({
                    "passage_text": sentence_clean,
                    "page_number": page_number,
                    "section_name": default_section or self._guess_section(sentence_clean, category),
                    "category": category,
                    "confidence": confidence
                })

        return items

    def _classify_sentence(self, sentence: str) -> tuple[Optional[str], float]:
        sentence_lower = sentence.lower()
        for cat, patterns in self.CATEGORY_CUES.items():
            for pat in patterns:
                if re.search(pat, sentence_lower):
                    confidence = 0.88 if cat in ["finding", "limitation"] else 0.82
                    return cat, confidence

        # Default fallback if sentence has key academic action verbs
        if re.search(r'\b(?:demonstrates?|concludes?|reveals?|indicates?)\b', sentence_lower):
            return "finding", 0.75
        if re.search(r'\b(?:proposes?|develops?|introduces?)\b', sentence_lower):
            return "objective", 0.75

        return None, 0.0

    def _guess_section(self, sentence: str, category: str) -> str:
        cat_to_section = {
            "objective": "Introduction",
            "method": "Methodology",
            "finding": "Results & Findings",
            "limitation": "Discussion & Limitations",
            "future_work": "Conclusion"
        }
        return cat_to_section.get(category, "General")

evidence_extractor = EvidenceExtractorService()
