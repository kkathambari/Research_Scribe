import re
from typing import List, Dict, Any, Optional

class EvidenceItem(dict):
    """Dictionary subclass supporting attribute-style access (e.g. item.category, item.passage_text)."""
    def __getattr__(self, name: str) -> Any:
        if name in self:
            return self[name]
        return None

    def __setattr__(self, name: str, value: Any) -> None:
        self[name] = value

class EvidenceExtractorService:
    """Extracts structured research evidence categorized by category with page references."""

    CATEGORY_CUES = {
        "objective": [
            r'\b(?:objective|goal|purpose|aims?)\b:?',
            r'\b(?:we propose|we present|this paper introduces|our goal is|aims to|objective of this study|we investigate)\b',
            r'\b(?:we focus on|in this work, we develop|addressing the problem of|our primary objective)\b'
        ],
        "problem": [
            r'\b(?:problem|challenge|bottleneck|catastrophic forgetting)\b:?',
            r'\b(?:the problem of|a major challenge is|remains a difficult problem|bottleneck in|suffers from)\b',
            r'\b(?:unresolved issue|a core difficulty|fails to address the problem|persistent challenge)\b'
        ],
        "method": [
            r'\b(?:method|methods|methodology|approach|algorithm)\b:?',
            r'\b(?:we utilize|our architecture|we train|we implement|the pipeline includes|algorithmic formulation)\b',
            r'\b(?:based on transformer|using fine-tuning|we employ|methodology comprises|the algorithm is evaluated)\b'
        ],
        "dataset": [
            r'\b(?:dataset|benchmark|corpus|experimental setup)\b:?',
            r'\b(?:evaluated on the|dataset consists of|benchmarked across|corpus comprises|we collect a dataset)\b',
            r'\b(?:training set contains|test split includes|experimental setting uses|samples collected from)\b'
        ],
        "finding": [
            r'\b(?:finding|findings|results?|retention rate|accuracy|f1|bleu|improved|increased by)\b:?',
            r'\b(?:we find that|results demonstrate|outperforms|achieves a new state of the art|statistically significant)\b',
            r'\b(?:shows an improvement of|accuracy of|bleu score of|our model achieves|reduces error by|empirically confirms)\b'
        ],
        "limitation": [
            r'\b(?:limitation|limitations|drawback|overhead|scales quadratically|constrained)\b:?',
            r'\b(?:a limitation of|limited by|however, our approach suffers|computational overhead|one drawback is)\b',
            r'\b(?:requires substantial compute|fails when|susceptible to|our study is constrained by)\b'
        ],
        "gap": [
            r'\b(?:gap|gaps|unexplored|open question)\b:?',
            r'\b(?:remains an open gap|gap in the literature|few studies have examined|little attention has been paid)\b',
            r'\b(?:unexplored domain|lack of empirical investigation|a prominent gap exists|insufficiently addressed)\b'
        ],
        "future_work": [
            r'\b(?:future work|future directions?)\b:?',
            r'\b(?:future work will|we plan to explore|an avenue for future research|promising direction is)\b',
            r'\b(?:remains an open question|further investigation is needed|in prospective studies)\b'
        ]
    }

    def extract_evidence_from_pages(self, pages: List[Dict[str, Any]], source_abstract: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Extracts classified evidence sentences with page numbers and confidence scores.
        Distinguishes direct extracted passages from general interpretations per FR-05.
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

    def extract_from_text(
        self,
        text: str,
        source_id: Optional[str] = None,
        page_number: int = 1,
        section_name: Optional[str] = None
    ) -> List[EvidenceItem]:
        """Public API: extracts classified research evidence from arbitrary text, returning EvidenceItem instances."""
        raw_items = self._extract_from_text(text, page_number=page_number, default_section=section_name)
        res = []
        for it in raw_items:
            if source_id:
                it["source_id"] = source_id
            res.append(EvidenceItem(it))
        return res

    def _extract_from_text(self, text: str, page_number: int = 1, default_section: Optional[str] = None) -> List[Dict[str, Any]]:
        items = []
        # Split into sentences or lines using punctuation boundaries and newlines
        raw_chunks = re.split(r'(?<=[.!?])\s+(?=[A-Z0-9])|\n+', text)

        for sentence in raw_chunks:
            sentence_clean = sentence.strip()
            if len(sentence_clean) < 20 or len(sentence_clean) > 500:
                continue

            # Classify sentence
            category, confidence = self._classify_sentence(sentence_clean)
            if category:
                items.append({
                    "passage_text": sentence_clean,
                    "page_number": page_number,
                    "section_name": default_section or self._guess_section(sentence_clean, category),
                    "category": category,
                    "confidence": confidence,
                    "is_direct_quotation": True
                })

        return items

    def _classify_sentence(self, sentence: str) -> tuple[Optional[str], float]:
        sentence_lower = sentence.lower()
        for cat, patterns in self.CATEGORY_CUES.items():
            for pat in patterns:
                if re.search(pat, sentence_lower):
                    confidence = 0.90 if cat in ["finding", "limitation", "gap"] else 0.85
                    return cat, confidence

        # Default fallback if sentence has key academic action verbs
        if re.search(r'\b(?:demonstrates?|concludes?|reveals?|indicates?)\b', sentence_lower):
            return "finding", 0.78
        if re.search(r'\b(?:proposes?|develops?|introduces?)\b', sentence_lower):
            return "objective", 0.78
        if re.search(r'\b(?:evaluated on|benchmark dataset)\b', sentence_lower):
            return "dataset", 0.80

        return None, 0.0

    def _guess_section(self, sentence: str, category: str) -> str:
        cat_to_section = {
            "objective": "Introduction",
            "problem": "Problem Formulation",
            "method": "Methodology",
            "dataset": "Experimental Setup",
            "finding": "Results & Findings",
            "limitation": "Discussion & Limitations",
            "gap": "Related Work & Gap Analysis",
            "future_work": "Conclusion"
        }
        return cat_to_section.get(category, "General")

evidence_extractor = EvidenceExtractorService()
