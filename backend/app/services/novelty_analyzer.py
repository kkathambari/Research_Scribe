import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
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
        supporting_passages = [s.abstract[:200] for s in sources if s.abstract][:2]
        comp_limitation = f"Comparison is based on abstracts of {len(sources)} retrieved paper(s). Full-text ablation verification and author confirmation are required."

        if has_sources and primary_source:
            gap_text = (
                f"Retrieved literature ('{primary_source.title[:65]}') investigates {topic_summary or 'domain principles'}. "
                f"Whether this published formulation covers the specific execution scope of the repository remains a research hypothesis requiring researcher validation."
            )
            rationale_text = (
                f"Analysis compares published scope in '{primary_source.title[:50]}' with {len(components)} "
                f"identified code components ({', '.join(comp_names[:3]) or 'modules'})."
            )
            contrib_text = (
                f"Hypothesized Contribution (Requires Review): Concrete software realization of {', '.join(comp_names[:3]) or 'core modules'} "
                f"grounded in repository commit {snapshot.commit_sha if snapshot else 'HEAD'}."
            )
            g_prob = ResearchGapProposal(
                dimension="Problem Formulation & Scope",
                identified_gap=gap_text,
                comparison_rationale=rationale_text,
                proposed_contribution=contrib_text,
                source_ids=source_ids[:1],
                supporting_passages=supporting_passages,
                comparison_limitations=comp_limitation,
                direct_support=supporting_passages[0] if supporting_passages else f"Direct metadata from '{primary_source.title}'",
                inferred_extrapolation="Inferred hypothesis: repository code expands executable scope beyond published conceptual description.",
                status="hypothesis_requiring_review"
            )
        else:
            g_prob = ResearchGapProposal(
                dimension="Problem Formulation & Scope",
                identified_gap="Comparative literature baseline has not been ingested for this project.",
                comparison_rationale="Novelty claims cannot be independently verified until related peer-reviewed publications are retrieved.",
                proposed_contribution="Insufficient Evidence: Comparative novelty cannot be established without retrieved literature baseline.",
                source_ids=[],
                supporting_passages=[],
                comparison_limitations="Zero literature ingested; comparative baseline absent.",
                direct_support=None,
                inferred_extrapolation=None,
                status="insufficient_evidence"
            )
        proposals.append(g_prob)

        # 2. Model Architecture & Modularity
        top_models = [c.name for c in components if c.component_type == "model"]
        arch_name = top_models[0] if top_models else (comp_names[0] if comp_names else "Core Architecture")
        if has_sources and primary_source:
            arch_gap = (
                f"Prior architectures documented in '{primary_source.title[:50]}' define algorithmic structures for {topic_summary or 'domain tasks'}. "
                f"A direct architectural equivalence with repository components ({', '.join(comp_names[:4]) or 'modular units'}) has not been formally verified."
            )
            arch_rationale = (
                f"Contrasts documented architecture in '{primary_source.title[:45]}' against AST-identified modular components: {', '.join(comp_names[:4]) or 'modules'}."
            )
            arch_contrib = f"Hypothesized Contribution (Requires Review): Modular architecture implementing {arch_name} with explicit AST boundaries."
            g_arch = ResearchGapProposal(
                dimension="Model Architecture & Modularity",
                identified_gap=arch_gap,
                comparison_rationale=arch_rationale,
                proposed_contribution=arch_contrib,
                source_ids=source_ids[:2],
                supporting_passages=supporting_passages,
                comparison_limitations=comp_limitation,
                direct_support=supporting_passages[0] if supporting_passages else f"Direct architectural description in '{primary_source.title}'",
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
                comparison_limitations="No literature ingested.",
                direct_support=None,
                inferred_extrapolation=None,
                status="insufficient_evidence"
            )
        proposals.append(g_arch)

        # 3. Optimization & Core Algorithms
        train_comps = [c.name for c in components if "train" in c.name.lower() or "optim" in c.name.lower()]
        algo_desc = methodology.algorithm_description if methodology else "execution routines"
        if has_sources and primary_source:
            algo_gap = (
                f"Algorithmic routines in retrieved literature ({source_titles[0][:50]}) "
                f"and repository code ({algo_desc[:80]}) require comparative parameter alignment to verify novel optimization characteristics."
            )
            g_algo = ResearchGapProposal(
                dimension="Optimization & Core Algorithms",
                identified_gap=algo_gap,
                comparison_rationale=f"Repository implementation defines concrete execution logic: {algo_desc[:120]}.",
                proposed_contribution=f"Hypothesized Contribution (Requires Review): Execution flow linking optimization operations to concrete code functions ({', '.join(train_comps[:2]) or 'execution pipeline'}).",
                source_ids=source_ids[:1],
                supporting_passages=supporting_passages,
                comparison_limitations=comp_limitation,
                direct_support=supporting_passages[0] if supporting_passages else f"Algorithmic formulation in '{primary_source.title}'",
                inferred_extrapolation="Inferred hypothesis: repository code optimizations provide efficiency gains beyond cited algorithmic description.",
                status="hypothesis_requiring_review"
            )
        else:
            g_algo = ResearchGapProposal(
                dimension="Optimization & Core Algorithms",
                identified_gap="Algorithmic novelty cannot be determined without comparative literature.",
                comparison_rationale="Baseline algorithms have not been retrieved.",
                proposed_contribution="Insufficient Evidence: Comparative algorithmic baseline absent.",
                source_ids=[],
                supporting_passages=[],
                comparison_limitations="No literature ingested.",
                direct_support=None,
                inferred_extrapolation=None,
                status="insufficient_evidence"
            )
        proposals.append(g_algo)

        # 4. Dataset Provenance & Quality
        data_comps = [c.name for c in components if c.component_type == "data_pipeline" or "data" in c.name.lower()]
        if has_sources and primary_source:
            g_data = ResearchGapProposal(
                dimension="Dataset Provenance & Quality",
                identified_gap=(
                    f"Data handling procedures cited in literature ({source_titles[0][:50]}) "
                    f"must be compared against repository data pipeline structures ({', '.join(data_comps[:2]) or 'data handlers'})."
                ),
                comparison_rationale=f"Repository code documents data preprocessing structures ({', '.join(data_comps[:2]) or 'data ingestion handlers'}).",
                proposed_contribution="Hypothesized Contribution (Requires Review): Dataset ingestion and split documentation establishing repeatable data provenance.",
                source_ids=source_ids[:2],
                supporting_passages=supporting_passages,
                comparison_limitations=comp_limitation,
                direct_support=supporting_passages[0] if supporting_passages else f"Dataset description in '{primary_source.title}'",
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
                comparison_limitations="No literature ingested.",
                direct_support=None,
                inferred_extrapolation=None,
                status="insufficient_evidence"
            )
        proposals.append(g_data)

        # 5. Evaluation Setup & Baselines
        eval_comps = [c.name for c in components if c.component_type == "evaluation" or "eval" in c.name.lower()]
        if has_results and has_sources:
            g_eval = ResearchGapProposal(
                dimension="Evaluation Setup & Baselines",
                identified_gap=(
                    f"Baseline evaluations in literature and repository metrics across {len(results)} records require controlled cross-validation under identical splits and hardware."
                ),
                comparison_rationale=f"Extracted evaluation artifacts record specific splits and seed settings across {len(results)} metrics.",
                proposed_contribution="Hypothesized Contribution (Requires Review): Comparative evaluation framework using explicit split assignments and seed controls.",
                source_ids=source_ids[:2],
                supporting_passages=supporting_passages,
                comparison_limitations="Repository metrics are self-reported; comparative replication is pending.",
                direct_support=supporting_passages[0] if supporting_passages else "Evaluation baselines in literature",
                inferred_extrapolation="Inferred hypothesis: repository evaluations provide controlled hardware benchmarks across reported baselines.",
                status="hypothesis_requiring_review"
            )
        elif has_sources:
            g_eval = ResearchGapProposal(
                dimension="Evaluation Setup & Baselines",
                identified_gap="Empirical benchmarking metrics were not identified in repository artifacts.",
                comparison_rationale="No benchmark CSV, JSON, or log files were extracted from the codebase.",
                proposed_contribution="Hypothesized Contribution (Requires Review): Evaluation routines in code; execution artifacts required to establish empirical baseline.",
                source_ids=source_ids[:1],
                supporting_passages=supporting_passages,
                comparison_limitations="Zero empirical artifacts detected in repository.",
                direct_support=supporting_passages[0] if supporting_passages else "Evaluation baselines in literature",
                inferred_extrapolation="Inferred gap: repository defines evaluation code but lacks logged benchmark artifacts.",
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
                comparison_limitations="Zero literature ingested.",
                direct_support=None,
                inferred_extrapolation=None,
                status="insufficient_evidence"
            )
        proposals.append(g_eval)

        # 6. Evaluation Metrics & Numerical Rigor
        if has_results and has_sources:
            metric_names = list(set(r.metric_name for r in results))
            g_metrics = ResearchGapProposal(
                dimension="Evaluation Metrics & Numerical Rigor",
                identified_gap="Extracted numerical results represent internal repository logs; statistical significance tests against baseline papers have not been independently performed.",
                comparison_rationale=f"Extracted {len(results)} distinct result entries across metrics: {', '.join(metric_names[:3])}.",
                proposed_contribution="Hypothesized Contribution (Requires Review): Experimental evidence ledger linking every metric to its source file and row location.",
                source_ids=source_ids[:1],
                supporting_passages=supporting_passages,
                comparison_limitations="Independent statistical significance has not been demonstrated.",
                direct_support=supporting_passages[0] if supporting_passages else "Published evaluation metrics in literature",
                inferred_extrapolation="Inferred hypothesis: repository metrics provide fine-grained telemetry not reported in publications.",
                status="hypothesis_requiring_review"
            )
        elif has_sources:
            g_metrics = ResearchGapProposal(
                dimension="Evaluation Metrics & Numerical Rigor",
                identified_gap="No numerical results detected in repository; quantitative claims cannot be substantiated without experimental artifacts.",
                comparison_rationale="Scientific integrity requires withholding performance claims until empirical logs are provided.",
                proposed_contribution="Hypothesized Contribution (Requires Review): Flagged evidence insufficiency in experimental ledger to prevent unverified claims.",
                source_ids=source_ids[:1],
                supporting_passages=supporting_passages,
                comparison_limitations="No numerical evidence available in repository files.",
                direct_support=supporting_passages[0] if supporting_passages else "Metrics reported in literature",
                inferred_extrapolation="Inferred gap: literature reports metrics but repository contains zero empirical logs.",
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
                comparison_limitations="Zero literature ingested.",
                direct_support=None,
                inferred_extrapolation=None,
                status="insufficient_evidence"
            )
        proposals.append(g_metrics)

        # 7. Handled Limitations & Threats to Validity
        if has_sources:
            g_limits = ResearchGapProposal(
                dimension="Handled Limitations & Threats to Validity",
                identified_gap="Threats to validity include potential distribution shift, unreproduced random seeds, and unverified publisher guideline assumptions.",
                comparison_rationale="Our framework provides explicit claim-to-evidence corroboration and journal guideline compliance audits.",
                proposed_contribution="Hypothesized Contribution (Requires Review): Comprehensive limitation analysis identifying evidence gaps, seed omissions, and verification constraints.",
                source_ids=source_ids,
                supporting_passages=supporting_passages,
                comparison_limitations="Threats to validity analysis is static and requires domain specialist appraisal.",
                direct_support=supporting_passages[0] if supporting_passages else "Scope of literature",
                inferred_extrapolation="Inferred hypothesis: repository mitigates threats to validity through automated audit checks.",
                status="hypothesis_requiring_review"
            )
        else:
            g_limits = ResearchGapProposal(
                dimension="Handled Limitations & Threats to Validity",
                identified_gap="Limitations cannot be evaluated against external literature.",
                comparison_rationale="No literature ingested.",
                proposed_contribution="Insufficient Evidence: External literature constraints absent.",
                source_ids=[],
                supporting_passages=[],
                comparison_limitations="Zero literature ingested.",
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
