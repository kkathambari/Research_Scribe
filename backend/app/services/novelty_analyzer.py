import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.orm import Session

from app.models.source import Source
from app.models.repository import RepositorySnapshot, MethodologyRecord, CodeComponent
from app.models.experimental import ExperimentalResult
from app.models.workflow import LiteratureComparison
from app.schemas.workflow import ResearchGapProposal, LiteratureComparisonResponse

logger = logging.getLogger(__name__)

import re
from collections import Counter

class NoveltyAnalyzer:
    """
    Subsystem for literature analysis, comparative analysis across all 7 dimensions,
    and grounded research gap & contribution generation conforming strictly to SRS v3.0 (FR-10, FR-11).
    Derives novelty claims exclusively from demonstrated repository code and authentic retrieved sources.
    """

    DIMENSIONS = [
        ("problem_formulation", "Problem Formulation & Scope"),
        ("architecture", "Model Architecture & Modularity"),
        ("algorithms", "Optimization & Core Algorithms"),
        ("data_sources", "Dataset Provenance & Quality"),
        ("experimental_design", "Evaluation Setup & Baselines"),
        ("metrics", "Evaluation Metrics & Numerical Rigor"),
        ("limitations", "Handled Limitations & Threats to Validity")
    ]

    def _find_targeted_source_evidence(
        self,
        sources: List[Source],
        keywords: List[str]
    ) -> Tuple[Optional[Source], Optional[str]]:
        """
        Scans retrieved sources and finds the first sentence that specifically
        matches the given topical keywords. Prioritizes abstract passages over titles.
        Returns (matched_source, matched_sentence), or (None, None) if no match.
        """
        # 1. Search abstract sentences first
        for s in sources:
            if s.abstract:
                sentences = [sent.strip() for sent in re.split(r'(?<=[.!?])\s+', s.abstract) if sent.strip()]
                for sent in sentences:
                    sent_lower = sent.lower()
                    if any(kw.lower() in sent_lower for kw in keywords):
                        return s, sent

        # 2. Fall back to title if abstract has no match
        for s in sources:
            if any(kw.lower() in s.title.lower() for kw in keywords):
                return s, s.title

        return None, None

    def _extract_key_phrases(self, text: Optional[str], max_terms: int = 4) -> List[str]:
        if not text:
            return []
        words = re.findall(r'\b[A-Za-z][A-Za-z0-9_\-]{3,}\b', text.lower())
        stopwords = {
            "this", "that", "with", "from", "have", "were", "been", "they", "their", "which",
            "about", "study", "paper", "presents", "propose", "proposed", "method", "results",
            "using", "based", "approach", "model", "models", "learning", "system", "performance",
            "evaluation", "state", "show", "also", "such", "into", "over"
        }
        filtered = [w for w in words if w not in stopwords]
        counts = Counter(filtered)
        return [term for term, _ in counts.most_common(max_terms)]

    def analyze_research_gaps_and_contributions(
        self,
        db: Session,
        project_id: str,
        snapshot: Optional[RepositorySnapshot] = None
    ) -> List[ResearchGapProposal]:
        """
        FR-11: Analyzes implementation against retrieved scholarly sources across all 7 SRS dimensions.
        Avoids generic assertions; derives comparisons directly from source text and repository AST.
        """
        sources = db.query(Source).filter(Source.project_id == project_id).all()
        methodology = snapshot.methodology if snapshot else None
        components = snapshot.components if snapshot else []
        results = (
            db.query(ExperimentalResult)
            .join(ExperimentalResult.artifact)
            .filter(ExperimentalResult.artifact.has(snapshot_id=snapshot.id))
            .all()
            if snapshot
            else []
        )

        proposals: List[ResearchGapProposal] = []

        # Clear previous comparisons for project
        db.query(LiteratureComparison).filter(LiteratureComparison.project_id == project_id).delete()
        db.commit()

        source_ids = [s.id for s in sources]
        source_titles = [s.title for s in sources]
        comp_names = [c.name for c in components]
        has_sources = len(sources) > 0
        has_results = len(results) > 0

        # Extract topical focus of primary retrieved literature
        primary_source = sources[0] if has_sources else None
        source_topics = self._extract_key_phrases(
            f"{primary_source.title} {primary_source.abstract or ''}" if primary_source else ""
        )
        topic_summary = ", ".join(source_topics) if source_topics else (primary_source.title[:50] if primary_source else "")

        # 1. Problem Formulation & Scope
        src_prob, pass_prob = self._find_targeted_source_evidence(
            sources, ["problem", "challenge", "objective", "task", "formulation", "scope", "propose", "investigate", "framework", "focus"]
        )
        if src_prob and pass_prob:
            g_prob = ResearchGapProposal(
                dimension="Problem Formulation & Scope",
                identified_gap=f"Retrieved literature ('{src_prob.title[:65]}') states: \"{pass_prob[:120]}\". Whether this published formulation covers the specific execution scope of the repository remains a research hypothesis requiring researcher validation.",
                comparison_rationale=f"Analysis compares scope in '{src_prob.title[:50]}' against {len(components)} identified code components ({', '.join(comp_names[:3]) or 'modules'}).",
                proposed_contribution=f"Hypothesized Contribution (Requires Review): Concrete software realization of {', '.join(comp_names[:3]) or 'core modules'} grounded in repository commit {snapshot.commit_sha if snapshot else 'HEAD'}.",
                source_ids=[src_prob.id],
                supporting_passages=[pass_prob],
                comparison_limitations=f"Comparison is based on retrieved passage from '{src_prob.title}'. Full-text ablation verification and author confirmation are required.",
                direct_support=f"Source '{src_prob.title}': \"{pass_prob}\"",
                inferred_extrapolation="Inferred hypothesis: repository code expands executable scope beyond published conceptual description.",
                status="hypothesis_requiring_review"
            )
        else:
            g_prob = ResearchGapProposal(
                dimension="Problem Formulation & Scope",
                identified_gap="Retrieved literature does not contain explicit discussion of problem formulation or scope relevant to this repository.",
                comparison_rationale="Novelty claims cannot be independently verified without literature addressing this specific dimension.",
                proposed_contribution="Insufficient Evidence: Comparative problem formulation baseline absent in retrieved literature.",
                source_ids=[],
                supporting_passages=[],
                comparison_limitations="No literature passage directly supports a problem formulation comparison.",
                direct_support=None,
                inferred_extrapolation=None,
                status="insufficient_evidence"
            )
        proposals.append(g_prob)

        # 2. Model Architecture & Modularity
        top_models = [c.name for c in components if c.component_type == "model"]
        arch_name = top_models[0] if top_models else (comp_names[0] if comp_names else "Core Architecture")
        src_arch, pass_arch = self._find_targeted_source_evidence(
            sources, ["architecture", "model", "layer", "transformer", "neural", "module", "component", "network", "encoder", "decoder", "attention"]
        )
        if src_arch and pass_arch:
            g_arch = ResearchGapProposal(
                dimension="Model Architecture & Modularity",
                identified_gap=f"Prior architecture in '{src_arch.title[:50]}' states: \"{pass_arch[:120]}\". A direct structural equivalence with repository components ({', '.join(comp_names[:4]) or 'modular units'}) has not been formally proven.",
                comparison_rationale=f"Contrasts documented architecture in '{src_arch.title[:45]}' against AST-identified modular components: {', '.join(comp_names[:4]) or 'modules'}.",
                proposed_contribution=f"Hypothesized Contribution (Requires Review): Modular architecture implementing {arch_name} with explicit AST boundaries.",
                source_ids=[src_arch.id],
                supporting_passages=[pass_arch],
                comparison_limitations=f"Comparison is based on retrieved passage from '{src_arch.title}'.",
                direct_support=f"Source '{src_arch.title}': \"{pass_arch}\"",
                inferred_extrapolation=f"Inferred hypothesis: repository implements modular architecture {arch_name} not directly specified in cited paper.",
                status="hypothesis_requiring_review"
            )
        else:
            g_arch = ResearchGapProposal(
                dimension="Model Architecture & Modularity",
                identified_gap="Architectural novelty requires comparative evaluation against published models in the target domain.",
                comparison_rationale="Literature search has not yet retrieved comparative baseline architectures.",
                proposed_contribution="Insufficient Evidence: Baseline model architectures not available for comparative alignment.",
                source_ids=[],
                supporting_passages=[],
                comparison_limitations="No literature passage directly discusses baseline model architectures.",
                direct_support=None,
                inferred_extrapolation=None,
                status="insufficient_evidence"
            )
        proposals.append(g_arch)

        # 3. Optimization & Core Algorithms
        train_comps = [c.name for c in components if "train" in c.name.lower() or "optim" in c.name.lower()]
        algo_desc = methodology.algorithm_description if methodology else "execution routines"
        src_algo, pass_algo = self._find_targeted_source_evidence(
            sources, ["algorithm", "optimization", "optimizer", "loss", "training", "convergence", "gradient", "stochastic", "backpropagation", "learning rate", "fit", "step"]
        )
        if src_algo and pass_algo:
            g_algo = ResearchGapProposal(
                dimension="Optimization & Core Algorithms",
                identified_gap=f"Algorithmic routines cited in '{src_algo.title[:50]}' describe: \"{pass_algo[:120]}\". Parameter alignment against repository execution ({algo_desc[:80]}) is required to substantiate optimization novelty.",
                comparison_rationale=f"Repository implementation defines concrete execution logic: {algo_desc[:120]}.",
                proposed_contribution=f"Hypothesized Contribution (Requires Review): Execution flow linking optimization operations to concrete code functions ({', '.join(train_comps[:2]) or 'execution pipeline'}).",
                source_ids=[src_algo.id],
                supporting_passages=[pass_algo],
                comparison_limitations=f"Comparison is based on retrieved passage from '{src_algo.title}'.",
                direct_support=f"Source '{src_algo.title}': \"{pass_algo}\"",
                inferred_extrapolation="Inferred hypothesis: repository code optimizations provide efficiency gains beyond cited algorithmic description.",
                status="hypothesis_requiring_review"
            )
        else:
            g_algo = ResearchGapProposal(
                dimension="Optimization & Core Algorithms",
                identified_gap="Algorithmic novelty cannot be determined without comparative literature.",
                comparison_rationale="Baseline algorithms have not been retrieved in literature.",
                proposed_contribution="Insufficient Evidence: Comparative algorithmic baseline absent.",
                source_ids=[],
                supporting_passages=[],
                comparison_limitations="No literature passage addresses algorithmic formulations.",
                direct_support=None,
                inferred_extrapolation=None,
                status="insufficient_evidence"
            )
        proposals.append(g_algo)

        # 4. Dataset Provenance & Quality
        data_comps = [c.name for c in components if c.component_type == "data_pipeline" or "data" in c.name.lower()]
        src_data, pass_data = self._find_targeted_source_evidence(
            sources, ["dataset", "corpus", "data", "benchmark", "split", "annotation", "preprocessing", "token", "sample", "collection", "ingestion"]
        )
        if src_data and pass_data:
            g_data = ResearchGapProposal(
                dimension="Dataset Provenance & Quality",
                identified_gap=f"Data procedures in literature ('{src_data.title[:50]}') describe: \"{pass_data[:120]}\". Comparison against repository data pipeline ({', '.join(data_comps[:2]) or 'data handlers'}) requires validation.",
                comparison_rationale=f"Repository code documents data preprocessing structures ({', '.join(data_comps[:2]) or 'data ingestion handlers'}).",
                proposed_contribution="Hypothesized Contribution (Requires Review): Dataset ingestion and split documentation establishing repeatable data provenance.",
                source_ids=[src_data.id],
                supporting_passages=[pass_data],
                comparison_limitations=f"Comparison is based on retrieved passage from '{src_data.title}'.",
                direct_support=f"Source '{src_data.title}': \"{pass_data}\"",
                inferred_extrapolation="Inferred hypothesis: repository preprocessing artifacts provide reproducible data splits not documented in literature.",
                status="hypothesis_requiring_review"
            )
        else:
            g_data = ResearchGapProposal(
                dimension="Dataset Provenance & Quality",
                identified_gap="Data pipeline comparison requires retrieved benchmark datasets from literature.",
                comparison_rationale="Comparative data pipelines absent.",
                proposed_contribution="Insufficient Evidence: Literature dataset baselines not available.",
                source_ids=[],
                supporting_passages=[],
                comparison_limitations="No literature passage discusses dataset provenance or splits.",
                direct_support=None,
                inferred_extrapolation=None,
                status="insufficient_evidence"
            )
        proposals.append(g_data)

        # 5. Evaluation Setup & Baselines
        eval_comps = [c.name for c in components if c.component_type == "evaluation" or "eval" in c.name.lower()]
        src_eval, pass_eval = self._find_targeted_source_evidence(
            sources, ["baseline", "evaluation", "setup", "comparison", "experiment", "benchmark", "test", "hardware", "hyperparameter", "protocol"]
        )
        if src_eval and pass_eval:
            g_eval = ResearchGapProposal(
                dimension="Evaluation Setup & Baselines",
                identified_gap=f"Literature baseline setup in '{src_eval.title[:50]}' notes: \"{pass_eval[:120]}\". Evaluation against repository experimental configuration requires cross-validation under identical splits.",
                comparison_rationale=f"Evaluations in literature compared against repository code ({', '.join(eval_comps[:2]) or 'evaluation modules'}).",
                proposed_contribution="Hypothesized Contribution (Requires Review): Comparative evaluation framework using explicit split assignments and seed controls.",
                source_ids=[src_eval.id],
                supporting_passages=[pass_eval],
                comparison_limitations=f"Comparison is based on retrieved passage from '{src_eval.title}'.",
                direct_support=f"Source '{src_eval.title}': \"{pass_eval}\"",
                inferred_extrapolation="Inferred hypothesis: repository evaluations provide controlled hardware benchmarks across reported baselines.",
                status="hypothesis_requiring_review"
            )
        else:
            g_eval = ResearchGapProposal(
                dimension="Evaluation Setup & Baselines",
                identified_gap="Evaluation baselines cannot be established without literature benchmarks.",
                comparison_rationale="Neither literature nor repository evaluation artifacts are present.",
                proposed_contribution="Insufficient Evidence: Comparative baselines unavailable.",
                source_ids=[],
                supporting_passages=[],
                comparison_limitations="No literature passage addresses evaluation setups or baselines.",
                direct_support=None,
                inferred_extrapolation=None,
                status="insufficient_evidence"
            )
        proposals.append(g_eval)

        # 6. Evaluation Metrics & Numerical Rigor
        src_metrics, pass_metrics = self._find_targeted_source_evidence(
            sources, ["metric", "accuracy", "f1", "bleu", "rouge", "loss", "score", "performance", "speed", "throughput", "latency", "statist", "error"]
        )
        if src_metrics and pass_metrics:
            g_metrics = ResearchGapProposal(
                dimension="Evaluation Metrics & Numerical Rigor",
                identified_gap=f"Published evaluation in '{src_metrics.title[:50]}' reports: \"{pass_metrics[:120]}\". Internal repository logs require statistical significance tests against baseline metrics.",
                comparison_rationale=f"Contrasts numerical metrics in '{src_metrics.title[:45]}' with repository empirical evidence ledger.",
                proposed_contribution="Hypothesized Contribution (Requires Review): Experimental evidence ledger linking every metric to its source file and row location.",
                source_ids=[src_metrics.id],
                supporting_passages=[pass_metrics],
                comparison_limitations=f"Comparison is based on retrieved passage from '{src_metrics.title}'.",
                direct_support=f"Source '{src_metrics.title}': \"{pass_metrics}\"",
                inferred_extrapolation="Inferred hypothesis: repository metrics provide fine-grained telemetry not reported in publications.",
                status="hypothesis_requiring_review"
            )
        else:
            g_metrics = ResearchGapProposal(
                dimension="Evaluation Metrics & Numerical Rigor",
                identified_gap="Numerical metrics comparison requires published baselines.",
                comparison_rationale="Baseline metrics unavailable.",
                proposed_contribution="Insufficient Evidence: No published literature metrics for comparison.",
                source_ids=[],
                supporting_passages=[],
                comparison_limitations="No literature passage discusses evaluation metrics or quantitative scores.",
                direct_support=None,
                inferred_extrapolation=None,
                status="insufficient_evidence"
            )
        proposals.append(g_metrics)

        # 7. Handled Limitations & Threats to Validity
        src_limits, pass_limits = self._find_targeted_source_evidence(
            sources, ["limitation", "threat", "validity", "bias", "failure", "constraint", "bottleneck", "assumption", "vulnerability", "robust", "degradation", "drawback"]
        )
        if src_limits and pass_limits:
            g_limits = ResearchGapProposal(
                dimension="Handled Limitations & Threats to Validity",
                identified_gap=f"Literature discusses constraints in '{src_limits.title[:50]}': \"{pass_limits[:120]}\". Potential distribution shifts and unreproduced random seeds remain research threats to validity.",
                comparison_rationale="Our framework provides explicit claim-to-evidence corroboration and journal guideline compliance audits.",
                proposed_contribution="Hypothesized Contribution (Requires Review): Comprehensive limitation analysis identifying evidence gaps, seed omissions, and verification constraints.",
                source_ids=[src_limits.id],
                supporting_passages=[pass_limits],
                comparison_limitations=f"Comparison is based on retrieved passage from '{src_limits.title}'.",
                direct_support=f"Source '{src_limits.title}': \"{pass_limits}\"",
                inferred_extrapolation="Inferred hypothesis: repository mitigates threats to validity through automated audit checks.",
                status="hypothesis_requiring_review"
            )
        else:
            g_limits = ResearchGapProposal(
                dimension="Handled Limitations & Threats to Validity",
                identified_gap="Limitations cannot be evaluated against external literature.",
                comparison_rationale="No literature passage discusses limitations or threats to validity.",
                proposed_contribution="Insufficient Evidence: External literature constraints absent.",
                source_ids=[],
                supporting_passages=[],
                comparison_limitations="No literature passage addresses limitations or failure modes.",
                direct_support=None,
                inferred_extrapolation=None,
                status="insufficient_evidence"
            )
        proposals.append(g_limits)

        # Generate atomic LiteratureComparison records for each retrieved source (FR-10, SRS 6.12)
        comp_summary = ", ".join(comp_names[:4]) if comp_names else "core modules"
        for s in sources:
            s_topics = self._extract_key_phrases(f"{s.title} {s.abstract or ''}", max_terms=3)
            topic_str = ", ".join(s_topics) if s_topics else "domain problem"
            
            diff_text = (
                f"The cited paper focuses on '{s.title[:60]}' ({topic_str}), "
                f"whereas our implementation provides concrete software artifacts for {comp_summary}."
            )
            lim_text = (
                "Source abstract documents theoretical or empirical findings without providing verified codebase AST links."
                if s.abstract else "Abstract not available; comparison restricted to title and bibliographic metadata."
            )
            comp = LiteratureComparison(
                id=f"comp_{hashlib.md5(f'{project_id}_{s.id}'.encode()).hexdigest()[:10]}",
                project_id=project_id,
                scholarly_source_id=s.id,
                comparison_dimension="architecture",
                related_method=s.title[:80],
                similarities=f"Addresses relevant domain themes ({topic_str}) cited in '{s.title[:60]}'.",
                differences=diff_text,
                limitations=lim_text,
                supporting_evidence=s.abstract[:250] if s.abstract else f"Bibliographic entry for '{s.title}' (Published: {s.publication_year or s.year or 'n/a'}).",
                review_status="unreviewed"
            )
            db.add(comp)
        db.commit()

        return proposals

    def get_literature_comparisons(self, db: Session, project_id: str) -> List[LiteratureComparisonResponse]:
        comparisons = db.query(LiteratureComparison).filter(LiteratureComparison.project_id == project_id).all()
        return [
            LiteratureComparisonResponse(
                id=c.id,
                scholarly_source_id=c.scholarly_source_id,
                source_title=c.source.title if c.source else None,
                comparison_dimension=c.comparison_dimension,
                related_method=c.related_method,
                similarities=c.similarities,
                differences=c.differences,
                limitations=c.limitations,
                supporting_evidence=c.supporting_evidence,
                review_status=c.review_status
            )
            for c in comparisons
        ]

novelty_analyzer = NoveltyAnalyzer()
