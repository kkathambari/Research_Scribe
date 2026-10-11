# ResearchScribe v3.0: An Evidence-Grounded GitHub-to-Research-Paper Generation and Journal Formatting System

**Version:** 3.0 (Consolidated Final Requirements Baseline)  
**Category:** Artificial Intelligence, Software Repository Analysis, Scholarly Information Retrieval, NLP, Academic Writing, Document Automation

---

## 🌟 Executive Summary

**ResearchScribe v3.0** is an evidence-grounded research automation platform that transforms software repositories into structured, evidence-grounded academic manuscripts formatted to the requirements of target journals and conferences.

Unlike generic AI writing tools that fabricate prose and hallucinate citations from simple topic prompts, ResearchScribe extracts methodology and experimental evidence directly from **real repository code, AST architectures, evaluation manifests, and primary scholarly literature**.

---

## 🏛️ SRS v3.0 Functional Requirements Mapping

| Functional Requirement | Subsystem / Component | Implementation Details |
|---|---|---|
| **FR-01: Repository Submission** | [`app.services.repository_analyzer`](file:///e:/Writter/backend/app/services/repository_analyzer.py), [`app.api.v1.repositories`](file:///e:/Writter/backend/app/api/v1/repositories.py) | URL validation, branch/commit SHA resolution, SSRF protection. |
| **FR-02: Snapshot Management** | [`app.models.repository.RepositorySnapshot`](file:///e:/Writter/backend/app/models/repository.py) | Immutable snapshot hashing, acquisition timestamp, commit tracking. |
| **FR-03: Codebase Analysis** | [`app.services.repository_analyzer`](file:///e:/Writter/backend/app/services/repository_analyzer.py) | File inventory, multi-language detection, module classification. |
| **FR-04: Architecture Reconstruction** | [`app.models.repository.CodeComponent`](file:///e:/Writter/backend/app/models/repository.py) | AST module parsing, class/pipeline relationships, data flow, line spans. |
| **FR-05: Methodology Reconstruction** | [`app.models.repository.MethodologyRecord`](file:///e:/Writter/backend/app/models/repository.py) | Problem formulation, loss functions, AdamW hyperparameters, LaTeX equations, pseudocode. |
| **FR-06: Experimental Evidence Extraction** | [`app.models.experimental.ExperimentalResult`](file:///e:/Writter/backend/app/models/experimental.py) | CSV, JSON, notebook parsing, metrics ledger, random seeds, hardware provenance. |
| **FR-07: Evidence Sufficiency & Consistency** | [`app.schemas.repository.EvidenceGapReport`](file:///e:/Writter/backend/app/schemas/repository.py) | Detects missing baselines, conflicting metrics, random seed omissions, sufficiency score. |
| **FR-08: Supplementary Material Ingestion** | [`app.services.repository_analyzer`](file:///e:/Writter/backend/app/services/repository_analyzer.py) | Ingests supplementary research reports, datasets, result tables. |
| **FR-09: Academic Literature Retrieval** | [`app.services.retrieval`](file:///e:/Writter/backend/app/services/retrieval.py) | Crossref, OpenAlex, and arXiv retrieval with deduplication and citation keys. |
| **FR-10: Literature Analysis** | [`app.services.novelty_analyzer`](file:///e:/Writter/backend/app/services/novelty_analyzer.py) | Synthesizes methods, datasets, findings, and limitations from retrieved sources. |
| **FR-11: Research Contribution & Gap Analysis** | [`app.services.novelty_analyzer`](file:///e:/Writter/backend/app/services/novelty_analyzer.py) | 7-dimension comparison (architecture, algorithms, metrics, data, etc.) and novel contribution hypotheses. |
| **FR-12: Manuscript Planning** | [`app.models.manuscript.ManuscriptSection`](file:///e:/Writter/backend/app/models/manuscript.py) | Dynamic outline supporting Title, Abstract, Intro, Methodology, Results, Declarations, References. |
| **FR-13: Automatic Mode Workflow** | [`app.services.workflow_orchestrator`](file:///e:/Writter/backend/app/services/workflow_orchestrator.py) | One-click end-to-end repository-to-journal paper generation with verified citations and compliance audit. |
| **FR-14: Guided Mode Workflow** | [`app.api.v1.workflow`](file:///e:/Writter/backend/app/api/v1/workflow.py) | 10 review checkpoints (Inventory -> Methodology -> Results -> Literature -> Gaps -> Outline -> Sections -> Verification -> Compliance). |
| **FR-15: Academic Writing & Revision** | [`app.services.academic_rewriter`](file:///e:/Writter/backend/app/services/academic_rewriter.py) | Tone, clarity, conciseness, coherence with side-by-side diff comparison preserving equations and numbers. |
| **FR-16: Claim & Evidence Management** | [`app.models.verification.Claim`](file:///e:/Writter/backend/app/models/verification.py) | Multi-modal linking between claims, repository code lines, experimental metrics, and scholarly passages. |
| **FR-17: Citation & Claim Verification** | [`app.services.verification_engine`](file:///e:/Writter/backend/app/services/verification_engine.py) | 5-state evaluation (`supported`, `partially_supported`, `contradicted`, `unverified`, `citation_missing`). |
| **FR-18: Reproducibility & Provenance** | [`app.models.repository`](file:///e:/Writter/backend/app/models/repository.py) | Preserves commit SHA, source line spans, execution seeds, journal profile versions. |
| **FR-19: Journal & Publication Selection** | [`app.services.journal_intelligence`](file:///e:/Writter/backend/app/services/journal_intelligence.py) | Built-in profiles for IEEE Transactions, ACM Transactions, Springer Nature, Elsevier. |
| **FR-20: Journal Template Import** | [`app.models.journal.JournalTemplate`](file:///e:/Writter/backend/app/models/journal.py) | DOCX template ingestion, inspecting fonts, margins, heading styles, and placeholders. |
| **FR-21: Journal Requirement Profile** | [`app.models.journal.JournalRequirement`](file:///e:/Writter/backend/app/models/journal.py) | Structured publication requirements distinguishing explicit rules, inferred styles, and unverified constraints. |
| **FR-22: Journal-Adaptive Generation** | [`app.services.workflow_orchestrator`](file:///e:/Writter/backend/app/services/workflow_orchestrator.py) | Adapts section order, abstract format, keyword count, heading hierarchy, and declarations. |
| **FR-23: Template-Preserving Assembly** | [`app.services.exporter`](file:///e:/Writter/backend/app/services/exporter.py) | Injects manuscript into official uploaded template preserving styles, margins, headers, and footers. |
| **FR-24: Journal Compliance Validation** | [`app.services.journal_intelligence`](file:///e:/Writter/backend/app/services/journal_intelligence.py) | Audits word limits, abstract length, required sections, citations, and declarations (`passed`, `failed`, `warning`). |
| **FR-25: Profile & Template Versioning** | [`app.models.journal`](file:///e:/Writter/backend/app/models/journal.py) | Retains immutable profile and template version history for manuscript reproducibility. |
| **FR-26: Multi-Format Export** | [`app.services.exporter`](file:///e:/Writter/backend/app/services/exporter.py) | DOCX (template-preserved), Markdown, and BibTeX with optional verification appendix table. |
| **FR-27: Project & Version Management** | [`app.api.v1.projects`](file:///e:/Writter/backend/app/api/v1/projects.py) | Full project lifecycle, snapshot rollback, review audit history. |
| **FR-28: Processing Status & Diagnostics** | [`app.models.workflow.AnalysisJob`](file:///e:/Writter/backend/app/models/workflow.py) | Asynchronous job status, progress reporting, actionable error handling. |

---

## 🚀 Getting Started

### 1. Environment Setup
The Python virtual environment is located in `backend/.venv`.

```bash
cd backend
.venv\Scripts\activate
```

### 2. Run Comprehensive Automated Tests
Run the test suite verifying all v3.0 subsystems (repository ingestion, AST code analysis, experimental extraction, novelty comparison, guided checkpoints, compliance checks, and exports):

```bash
.venv\Scripts\python.exe -m pytest tests -v
```

### 3. Launch ResearchScribe v3.0 Dashboard
Start the application server:

```bash
python run.py
```

- **Interactive Web Dashboard:** [http://localhost:8000](http://localhost:8000)
- **Interactive OpenAPI Specification:** [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 🔬 Evidence Verification & Compliance Framework

### Claim Verification Evaluation
Every empirical statement in a manuscript draft receives a factual corroboration rating:
- 🟢 **Supported**: Available source passage directly corroborates the factual claim with page or code provenance.
- 🟡 **Partially Supported**: Source corroborates part of the claim, but authorial extrapolation is detected.
- 🔴 **Contradicted**: Discrepancy detected between claim and empirical/literature findings.
- ⚪ **Unverified**: Cited source or passage was not found or has insufficient semantic overlap.
- 🟠 **Citation Missing**: Substantive empirical or quantitative assertion lacks an in-text citation marker.

### Journal Compliance Evaluation
Validates manuscript drafts against the target journal profile:
- 🟢 **Passed**: Complies with venue specifications (word counts, required sections, citations).
- 🟡 **Warning**: Condition requires author attention (e.g. abstract length or optional declaration).
- 🔴 **Failed**: Violates mandatory requirement (e.g. missing essential methodology section).
- ⚪ **Not Verifiable**: Rule cannot be inspected automatically.
