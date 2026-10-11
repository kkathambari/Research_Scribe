import re
import uuid
from typing import List, Dict, Any, Optional, Tuple

class CitationVerificationService:
    """Evaluates claims and in-text citations for factual alignment and evidence provenance."""

    CITATION_PATTERNS = [
        # Author-date: (Vaswani et al., 2017) or (Devlin, 2019) or (Smith & Jones 2020)
        r'\(([A-Z][a-zA-Z]+(?:\s+et\s+al\.)?(?:\s*&\s*[A-Z][a-zA-Z]+)?(?:,?\s+\d{4}[a-z]?))\)',
        # Bracket keys: [Vaswani2017] or [Smith2020]
        r'\[([A-Z][a-zA-Z]+\d{4}[a-z]?)\]',
        # Numeric bracket: [1], [2], [1, 2]
        r'\[(\d+(?:\s*,\s*\d+)*)\]',
        # Numeric paren: (1), (2)
        r'\((\d+)\)'
    ]

    FACTUAL_ASSERTION_CUES = [
        r'\b(?:demonstrates?|proves?|shows?|indicates?|reveals?|achieved|outperformed|increased|decreased|improved)\b',
        r'\b(?:statistically significant|empirical results|state of the art|benchmark|accuracy|f1-score|bleu)\b',
        r'\b(?:\d+(?:\.\d+)?%|\d+\s*(?:times|folds?|participants|samples))\b'
    ]

    def verify_section_content(
        self,
        manuscript_id: str,
        section_id: str,
        content: str,
        sources: List[Dict[str, Any]],
        evidences: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Decomposes section text into claims, maps citations, verifies against evidence passages.
        Returns:
            {
                "manuscript_id": str,
                "section_id": str,
                "total_claims": int,
                "supported_count": int,
                "partially_supported_count": int,
                "contradicted_count": int,
                "unverified_count": int,
                "citation_missing_count": int,
                "accuracy_score": float,
                "claims": List[Dict[str, Any]]
            }
        """
        # Map sources by various lookup keys: ID, citation_key, author surname, index
        source_by_id = {s["id"]: s for s in sources}
        source_by_key = {}
        source_by_author = {}
        for idx, s in enumerate(sources):
            index_num = str(idx + 1)
            source_by_key[index_num] = s # for [1]
            if s.get("citation_key"):
                source_by_key[s["citation_key"].lower()] = s
            authors = s.get("authors") or ""
            for a in authors.split(","):
                surname = a.strip().split()[-1].lower() if a.strip().split() else ""
                if surname:
                    source_by_author[surname] = s

        # Group evidences by source_id
        evidences_by_source: Dict[str, List[Dict[str, Any]]] = {}
        for ev in evidences:
            src_id = ev.get("source_id")
            if src_id not in evidences_by_source:
                evidences_by_source[src_id] = []
            evidences_by_source[src_id].append(ev)

        # 1. Segment text into sentences
        sentences = self._segment_into_claim_sentences(content)
        
        claims_list = []
        counts = {
            "supported": 0,
            "partially_supported": 0,
            "contradicted": 0,
            "unverified": 0,
            "citation_missing": 0
        }

        for sentence in sentences:
            claim_id = str(uuid.uuid4())
            citations_found = self._extract_citations(sentence)
            is_factual = self._is_factual_assertion(sentence)

            # Case A: Factual claim with NO citations
            if not citations_found and is_factual:
                status = "citation_missing"
                confidence = 0.85
                explanation = "Claim makes empirical or quantitative assertions without an identifiable in-text citation."
                counts[status] += 1
                claims_list.append({
                    "id": claim_id,
                    "manuscript_id": manuscript_id,
                    "section_id": section_id,
                    "claim_text": sentence,
                    "status": status,
                    "confidence": confidence,
                    "explanation": explanation,
                    "reviewer_status": "pending",
                    "citations": []
                })
                continue

            # Case B: Sentence has citations
            if citations_found:
                best_status = "unverified"
                best_confidence = 0.5
                best_explanation = ""
                resolved_citations = []

                for cite_str in citations_found:
                    citation_obj_id = str(uuid.uuid4())
                    matched_source = self._resolve_source(cite_str, source_by_key, source_by_author, sources)
                    
                    if not matched_source:
                        status = "unverified"
                        explanation = f"Referenced source '{cite_str}' could not be resolved to any paper in the project library."
                        resolved_citations.append({
                            "id": citation_obj_id,
                            "claim_id": claim_id,
                            "source_id": None,
                            "evidence_id": None,
                            "in_text_citation": cite_str,
                            "match_score": 0.0,
                            "source_title": None,
                            "source_authors": None,
                            "source_year": None,
                            "citation_key": None,
                            "evidence_passage": None,
                            "page_number": None
                        })
                        best_status = "unverified"
                        best_explanation = explanation
                        continue

                    # Search matching evidence passages for this source
                    src_evs = evidences_by_source.get(matched_source["id"], [])
                    best_ev, match_score, status_type, reasoning = self._evaluate_evidence_support(
                        sentence, matched_source, src_evs
                    )

                    resolved_citations.append({
                        "id": citation_obj_id,
                        "claim_id": claim_id,
                        "source_id": matched_source["id"],
                        "evidence_id": best_ev["id"] if best_ev else None,
                        "in_text_citation": cite_str,
                        "match_score": match_score,
                        "source_title": matched_source.get("title"),
                        "source_authors": matched_source.get("authors"),
                        "source_year": matched_source.get("year"),
                        "citation_key": matched_source.get("citation_key"),
                        "evidence_passage": best_ev.get("passage_text") if best_ev else (matched_source.get("abstract") or "Source record verified without full-text excerpt."),
                        "page_number": best_ev.get("page_number") if best_ev else 1
                    })

                    best_status = status_type
                    best_confidence = match_score
                    best_explanation = reasoning

                counts[best_status] += 1
                claims_list.append({
                    "id": claim_id,
                    "manuscript_id": manuscript_id,
                    "section_id": section_id,
                    "claim_text": sentence,
                    "status": best_status,
                    "confidence": best_confidence,
                    "explanation": best_explanation,
                    "reviewer_status": "pending",
                    "citations": resolved_citations
                })
            else:
                # Non-factual general sentence without citations (e.g. organizational transition)
                pass

        total = len(claims_list)
        supported_total = counts["supported"] + counts["partially_supported"]
        accuracy = round((supported_total / total * 100), 1) if total > 0 else 100.0

        return {
            "manuscript_id": manuscript_id,
            "section_id": section_id,
            "total_claims": total,
            "supported_count": counts["supported"],
            "partially_supported_count": counts["partially_supported"],
            "contradicted_count": counts["contradicted"],
            "unverified_count": counts["unverified"],
            "citation_missing_count": counts["citation_missing"],
            "accuracy_score": accuracy,
            "claims": claims_list
        }

    def _segment_into_claim_sentences(self, text: str) -> List[str]:
        # Filter out markdown headings
        lines = [line.strip() for line in text.split("\n") if line.strip() and not line.strip().startswith("#")]
        body_text = " ".join(lines)
        # Split on sentence boundaries
        raw_sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z0-9\[\(])', body_text)
        
        valid = []
        for s in raw_sentences:
            s_clean = s.strip()
            # Must be substantial sentence
            if len(s_clean) >= 25 and not s_clean.lower().startswith("section"):
                valid.append(s_clean)
        return valid

    def _extract_citations(self, sentence: str) -> List[str]:
        found = []
        for pat in self.CITATION_PATTERNS:
            matches = re.findall(pat, sentence)
            for m in matches:
                # Handle comma separated numbers like [1, 2]
                if "," in m and all(part.strip().isdigit() for part in m.split(",")):
                    for sub in m.split(","):
                        if sub.strip():
                            found.append(f"[{sub.strip()}]")
                else:
                    found.append(m.strip())
        return list(dict.fromkeys(found)) # unique preserve order

    def _is_factual_assertion(self, sentence: str) -> bool:
        s_lower = sentence.lower()
        for cue in self.FACTUAL_ASSERTION_CUES:
            if re.search(cue, s_lower):
                return True
        return False

    def _resolve_source(
        self,
        cite_str: str,
        source_by_key: Dict[str, Any],
        source_by_author: Dict[str, Any],
        sources: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        clean = re.sub(r'[\[\]\(\),]', '', cite_str).strip()
        
        # 1. Numeric index
        if clean.isdigit():
            idx = int(clean) - 1
            if 0 <= idx < len(sources):
                return sources[idx]
        
        # 2. Key lookup
        if clean.lower() in source_by_key:
            return source_by_key[clean.lower()]

        # 3. Author surname match
        words = clean.split()
        for w in words:
            w_lower = w.lower()
            if w_lower in source_by_author:
                return source_by_author[w_lower]

        # 4. Fallback: partial match on citation_key
        for s in sources:
            key = s.get("citation_key") or ""
            if key and (key.lower() in clean.lower() or clean.lower() in key.lower()):
                return s

        return None

    def _evaluate_evidence_support(
        self,
        claim_text: str,
        source: Dict[str, Any],
        evidences: List[Dict[str, Any]]
    ) -> Tuple[Optional[Dict[str, Any]], float, str, str]:
        """
        Calculates factual semantic support between claim and evidence passages.
        """
        claim_clean = re.sub(r'[\(\[\{].*?[\)\]\}]', '', claim_text).lower() # Strip citation markers
        claim_words = set(re.findall(r'\b[a-z]{3,}\b', claim_clean))
        stop_words = {"this", "that", "with", "from", "have", "were", "been", "they", "their", "which", "about", "study", "paper"}
        claim_keywords = claim_words - stop_words

        # Check for direct quotes
        direct_quote_match = re.search(r'"([^"]{15,})"', claim_text)
        if direct_quote_match:
            quote_text = direct_quote_match.group(1).lower()
            for ev in evidences:
                if quote_text in ev["passage_text"].lower():
                    return ev, 0.98, "supported", f"Direct verbatim passage verified in source (Page {ev.get('page_number', 1)})."

        best_ev = None
        max_overlap_score = 0.0

        for ev in evidences:
            ev_text = ev["passage_text"].lower()
            ev_words = set(re.findall(r'\b[a-z]{3,}\b', ev_text)) - stop_words
            if not ev_words or not claim_keywords:
                continue

            intersection = claim_keywords.intersection(ev_words)
            union = claim_keywords.union(ev_words)
            # Weighted recall on claim keywords
            keyword_recall = len(intersection) / len(claim_keywords)
            jaccard = len(intersection) / len(union)
            score = 0.7 * keyword_recall + 0.3 * jaccard

            if score > max_overlap_score:
                max_overlap_score = score
                best_ev = ev

        # If no explicit evidence passages, evaluate against source abstract
        if not best_ev and source.get("abstract"):
            abs_text = source["abstract"].lower()
            abs_words = set(re.findall(r'\b[a-z]{3,}\b', abs_text)) - stop_words
            if claim_keywords and abs_words:
                intersection = claim_keywords.intersection(abs_words)
                keyword_recall = len(intersection) / len(claim_keywords)
                if keyword_recall >= 0.3:
                    best_ev = {
                        "id": None,
                        "passage_text": source["abstract"],
                        "page_number": 1,
                        "category": "abstract"
                    }
                    max_overlap_score = min(0.85, keyword_recall)

        # Check for contradiction cues
        contradiction_cues = ["fails", "unable", "ineffective", "inferior", "degrades", "negative correlation"]
        claim_has_contradiction = any(cue in claim_clean for cue in contradiction_cues)
        ev_has_positive = best_ev and any(p in best_ev["passage_text"].lower() for p in ["outperforms", "superior", "improves", "effective"])
        if claim_has_contradiction and ev_has_positive:
            return best_ev, 0.85, "contradicted", "Discrepancy detected: Claim asserts negative/inferior finding while source passage reports positive improvement."

        # Numerical & Unit fact-checking: claims asserting specific numbers and units must be corroborated
        claim_number_matches = re.findall(r'\b(\d+(?:\.\d+)?)\s*(%|ms|s|sec|seconds|gb|mb|kb|tokens|parameters|params|folds?|times|x)?(?=\b|\s|$|[.,;!?])', claim_text, re.IGNORECASE)
        substantive_numbers = []
        for val, unit in claim_number_matches:
            # Exclude citation years (e.g. 2017, 2024) and single digit bracket references [1]
            if val.isdigit() and len(val) == 4 and 1900 <= int(val) <= 2030:
                continue
            if val.isdigit() and int(val) <= 10 and f"[{val}]" in claim_text:
                continue
            unit_norm = unit.strip().lower() if unit else ""
            substantive_numbers.append((val, unit_norm))

        if substantive_numbers and best_ev:
            ev_text = best_ev["passage_text"].lower()
            missing_or_mismatched = []
            for num_val, unit_str in substantive_numbers:
                if num_val not in ev_text:
                    missing_or_mismatched.append(f"{num_val}{unit_str}")
                elif unit_str and unit_str not in ["x", "times"]:
                    # Ensure the unit is also present in proximity or within passage
                    if unit_str not in ev_text:
                        missing_or_mismatched.append(f"{num_val} (unit '{unit_str}' missing in evidence)")
            if missing_or_mismatched:
                return (
                    best_ev,
                    min(0.35, round(max_overlap_score, 2)),
                    "unverified",
                    f"Numerical discrepancy: The claim asserts numerical metrics ({', '.join(missing_or_mismatched)}) that are not corroborated in the cited evidence passage."
                )

        # Causal assertion vs correlation check
        causal_cues = ["causes", "caused", "leads to", "results in", "proves that", "demonstrates that", "attributable to"]
        claim_has_causal = any(cue in claim_clean for cue in causal_cues)
        if claim_has_causal and best_ev:
            ev_lower = best_ev["passage_text"].lower()
            correlation_only = any(c in ev_lower for c in ["correlated", "associated with", "linked to", "suggests", "co-occurs"])
            has_direct_causal = any(c in ev_lower for c in ["demonstrates causal", "mechanistic", "proves that", "directly causes", "experimentally verified"])
            if correlation_only and not has_direct_causal:
                return (
                    best_ev,
                    min(0.40, round(max_overlap_score, 2)),
                    "partially_supported",
                    "Causal inference requires caution: Source reports associative or observational findings rather than proven causal mechanisms."
                )

        # Comparative claim check: claims of superiority require comparative evidence
        superiority_cues = ["outperforms", "superior to", "higher accuracy than", "better performance than", "surpasses"]
        if any(cue in claim_clean for cue in superiority_cues) and best_ev:
            ev_has_comp = any(c in best_ev["passage_text"].lower() for c in ["outperform", "superior", "baseline", "compared to", "exceed", "higher"])
            if not ev_has_comp:
                return (
                    best_ev,
                    min(0.40, round(max_overlap_score, 2)),
                    "partially_supported",
                    "Comparative claim requires caution: The source describes the method but does not contain comparative benchmark data supporting superiority."
                )

        # Assign status based on overlap threshold
        if max_overlap_score >= 0.50:
            page_info = f" (Page {best_ev.get('page_number', 1)})" if best_ev and best_ev.get('page_number') else ""
            return best_ev, round(max_overlap_score, 2), "supported", f"Source passage directly supports the asserted statement{page_info}."
        elif max_overlap_score >= 0.25:
            return best_ev, round(max_overlap_score, 2), "partially_supported", "Source evidence partially corroborates the claim, but authorial generalization or extrapolation is present."
        elif best_ev:
            return best_ev, round(max_overlap_score, 2), "unverified", "Evidence passage was located in source, but lexical and semantic alignment is too weak to confirm factual support."
        else:
            return None, 0.0, "unverified", "No relevant textual passage in the source could be matched to the claim."

    def verify_manuscript(self, db, manuscript_id: str) -> Dict[str, Any]:
        """Runs citation and claim verification across all sections of a manuscript."""
        from app.models.manuscript import Manuscript
        from app.models.source import Source
        from app.models.evidence import Evidence

        manuscript = db.query(Manuscript).filter(Manuscript.id == manuscript_id).first()
        if not manuscript:
            return {"accuracy_score": 100.0, "total_claims": 0}

        sources = db.query(Source).filter(Source.project_id == manuscript.project_id).all()
        sources_list = [{"id": s.id, "title": s.title, "citation_key": s.citation_key} for s in sources]
        evidences = db.query(Evidence).filter(Evidence.project_id == manuscript.project_id).all()
        ev_list = [{"id": e.id, "source_id": e.source_id, "passage_text": e.passage_text} for e in evidences]

        total_claims = 0
        supported = 0
        for sec in manuscript.sections:
            if not sec.content:
                continue
            rep = self.verify_section_content(manuscript_id, sec.id, sec.content, sources_list, ev_list)
            total_claims += rep.get("total_claims", 0)
            supported += rep.get("supported_count", 0)

        acc = round((supported / total_claims) * 100.0, 1) if total_claims > 0 else 100.0
        return {"accuracy_score": acc, "total_claims": total_claims, "supported_count": supported}

citation_verifier = CitationVerificationService()
verification_engine = citation_verifier
