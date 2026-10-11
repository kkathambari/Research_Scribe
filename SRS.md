# SOFTWARE REQUIREMENTS SPECIFICATION (SRS)

# ResearchScribe v3.0
## An Evidence-Grounded GitHub-to-Research-Paper Generation and Journal Formatting System

**Version:** 3.0  
**Document Status:** Consolidated Final Requirements Baseline  
**Product Type:** AI-Powered Research Automation Platform  
**Primary Domains:** Artificial Intelligence, Software Repository Analysis, Scholarly Information Retrieval, Natural Language Processing, Academic Writing, and Document Automation

---

# 1. INTRODUCTION

## 1.1 Purpose

ResearchScribe is an AI-powered research paper generation platform designed to transform software repositories into structured, evidence-grounded academic manuscripts formatted according to the requirements of a selected journal or conference.

The system accepts a GitHub repository URL, analyses the implementation and available experimental evidence, retrieves relevant scholarly literature, reconstructs the methodology, identifies potential research contributions, and generates a research manuscript.

The user may optionally upload a journal's official DOC or DOCX manuscript template, author guidelines, or other publication requirements. ResearchScribe shall analyse those materials and adapt the manuscript's structure, citations, and document formatting to the selected publication venue.

The platform shall provide two operating modes:

1. **Automatic Mode:** Analyses the repository, retrieves related literature, generates an initial manuscript, verifies available evidence and citations, applies the selected journal's requirements, and produces a compliance report.
2. **Guided Mode:** Presents intermediate findings for researcher review and approval before generating the manuscript section by section.

Both modes shall use a shared evidence-management, repository-analysis, literature-retrieval, citation-verification, and document-formatting infrastructure.

The central design principle is that ResearchScribe must generate papers from the actual research implementation and available evidence rather than produce generic academic text from a topic prompt.

## 1.2 Problem Statement

Software projects frequently contain substantial technical work that is distributed across source files, configuration files, notebooks, datasets, model implementations, evaluation scripts, experimental results, and documentation.

Converting such projects into research publications requires several difficult activities:

- Understanding the implementation.
- Reconstructing the actual methodology.
- Identifying the research contribution.
- Finding and comparing related scholarly work.
- Extracting and validating experimental results.
- Designing the manuscript structure.
- Writing coherent academic sections.
- Verifying citations and references.
- Formatting the document according to publication requirements.
- Checking manuscript completeness before submission.

Generic AI writing tools may produce plausible academic prose without accurately understanding the underlying implementation. They may invent results, overstate novelty, misrepresent algorithms, or generate incorrect citations.

Even a technically accurate manuscript may require substantial revision if its formatting does not conform to the intended journal's requirements.

ResearchScribe addresses these problems through repository-aware analysis, evidence-grounded generation, citation verification, researcher review, and journal-specific document assembly.

## 1.3 Scope

ResearchScribe shall support the following end-to-end workflow:

1. Accept a GitHub repository URL and selected revision.
2. Acquire an authorised repository snapshot.
3. Inspect the directory structure, source files, dependencies, and documentation.
4. Reconstruct the implemented software architecture and methodology.
5. Extract available datasets, experimental configurations, metrics, and results.
6. Identify missing evidence, inconsistencies, and potential methodological concerns.
7. Retrieve relevant scholarly literature.
8. Compare the project against existing research.
9. Propose potential research contributions and a manuscript outline.
10. Allow automatic or guided manuscript generation.
11. Associate substantive claims with supporting evidence.
12. Verify scholarly references and assess claim-to-source support.
13. Accept a journal's official template and author guidelines.
14. Extract and apply publication-specific requirements.
15. Assemble the manuscript using the selected template where supported.
16. Validate the document against the approved journal profile.
17. Export the manuscript and supporting files.
18. Preserve repository, evidence, template, and manuscript version history.

The system shall not guarantee that a repository represents novel research, that all extracted results are reproducible, or that a generated manuscript will be accepted by a journal.

## 1.4 Objectives

The objectives of ResearchScribe are to:

- Automate the analysis of software repositories.
- Reconstruct technical methodology from implementation evidence.
- Extract experimental evidence without fabricating missing results.
- Identify potential research gaps through scholarly comparison.
- Generate structured academic manuscripts.
- Support accurate citation and reference management.
- Improve the readability and coherence of academic writing.
- Accept official journal templates and publication guidelines.
- Adapt manuscript content and formatting to journal requirements.
- Validate manuscript compliance before export.
- Maintain claim-level evidence traceability.
- Support both automatic and researcher-guided workflows.
- Preserve reproducibility and document version history.

## 1.5 Intended Users

### Primary users

- Undergraduate and postgraduate students.
- Master's and doctoral researchers.
- Independent researchers.
- Software and machine-learning researchers.
- Academic authors preparing journal or conference submissions.

### Secondary users

- Research supervisors.
- Academic research groups.
- University laboratories.
- Research and writing support teams.

## 1.6 Definitions and Abbreviations

| Term | Definition |
|---|---|
| SRS | Software Requirements Specification |
| AI | Artificial Intelligence |
| LLM | Large Language Model |
| NLP | Natural Language Processing |
| RAG | Retrieval-Augmented Generation |
| GitHub repository | A version-controlled collection of project files |
| Commit SHA | Identifier of a particular Git commit |
| Repository snapshot | A fixed revision of a repository analysed by the system |
| Evidence provenance | Traceability between a claim and its supporting source |
| Scholarly source | An academic publication or other scholarly record |
| Citation verification | Assessment of reference metadata and source support |
| Journal profile | Structured publication requirements extracted from official guidelines or templates |
| DOC | Microsoft Word binary document format |
| DOCX | Microsoft Word Office Open XML document format |
| Automatic Mode | Generation of an initial manuscript with limited interaction |
| Guided Mode | Generation with researcher review and approval checkpoints |
| Template preservation | Retention of applicable styles and structural properties from an uploaded template |
| Compliance report | Report of manuscript requirements that pass, fail, produce warnings, or cannot be verified |

---

# 2. OVERALL SYSTEM DESCRIPTION

## 2.1 Product Perspective

ResearchScribe shall be a modular web application composed of the following major subsystems:

1. User and project management.
2. GitHub repository ingestion.
3. Repository intelligence and code analysis.
4. Methodology reconstruction.
5. Experimental evidence extraction.
6. Scholarly literature retrieval.
7. Research-gap analysis.
8. Manuscript planning and generation.
9. Citation and evidence verification.
10. Journal template intelligence.
11. Template-preserving document assembly.
12. Journal compliance validation.
13. Manuscript versioning and export.

The Automatic and Guided workflows shall share these services and data models.

## 2.2 Operating Environment

The initial implementation shall use the following proposed technology stack.

| Component | Proposed technology |
|---|---|
| Frontend | React and TypeScript |
| Backend | Python and FastAPI |
| Repository integration | GitHub API and controlled Git operations |
| Code analysis | Language-aware parsers and static-analysis utilities |
| Document processing | pypdf and appropriate document-processing libraries |
| Word document processing | python-docx and OOXML-compatible processing |
| Notebook processing | nbformat |
| Data analysis | pandas and NumPy |
| Database | PostgreSQL |
| Semantic retrieval | PostgreSQL with vector support or a compatible vector store |
| AI orchestration | Modular interface for configurable LLM providers |
| Scholarly metadata | Crossref, OpenAlex, arXiv, and other permitted services |
| Citation formatting | Citation Style Language-compatible library |
| Background jobs | Task queue and worker processes |
| Export | DOCX, PDF, Markdown, and supported reference formats |
| Deployment | Containerised development and deployment environment |

Technology selection shall be validated during implementation. The SRS defines requirements and does not mandate that every proposed technology be used.

## 2.3 Operating Modes

### 2.3.1 Automatic Mode

The user supplies a GitHub repository URL, selects a manuscript type, chooses a target publication if known, and supplies an official template or author guidelines when available.

The system shall:

1. Resolve and record the repository revision.
2. Analyse relevant repository files.
3. Reconstruct the implemented methodology.
4. Extract available experimental evidence.
5. Identify evidence gaps and inconsistencies.
6. Retrieve related scholarly literature.
7. Compare the implementation with existing research.
8. Generate a manuscript outline.
9. Generate applicable manuscript sections.
10. Verify available citations and evidence links.
11. Apply the selected journal's requirements.
12. Assemble the document.
13. Generate a compliance report and unresolved-issues report.
14. Produce an editable manuscript draft.

Automatic Mode shall not silently invent missing information to complete the paper.

### 2.3.2 Guided Mode

The system shall present analysis results at defined review checkpoints.

The researcher shall be able to:

- Confirm the relevant repository files.
- Correct the inferred methodology.
- Validate extracted experimental results.
- Review retrieved scholarly sources.
- Approve or reject proposed research gaps.
- Confirm the intended research contribution.
- Approve the manuscript outline.
- Generate and revise sections individually.
- Select or correct journal requirements.
- Review citation and formatting warnings.
- Approve the final draft for export.

The system shall record relevant user corrections and approvals.

## 2.4 Product Boundaries

The system shall analyse files accessible in the selected repository snapshot and supplementary material supplied by the user.

It shall not assume access to:

- Private repositories without authorisation.
- Uncommitted local files.
- Unavailable datasets.
- Experimental logs that were never generated.
- Publisher full texts behind access restrictions.
- Journal requirements that cannot be verified.
- Research findings that are not supported by available evidence.

The system shall communicate these limitations explicitly.

---

# 3. FUNCTIONAL REQUIREMENTS

## 3.1 Repository Ingestion and Analysis

### FR-01: Repository Submission

The system shall accept a GitHub repository URL.

The user may specify:

- Repository URL.
- Branch, tag, or commit SHA.
- Project title.
- Research topic and objectives.
- Manuscript type.
- Target journal or conference.
- Preferred citation style.
- Generation mode.
- Optional supplementary documents and datasets.

The system shall validate the URL and determine whether the requested repository can be accessed.

**Acceptance criteria:** A valid repository creates an analysis job, while invalid or inaccessible repositories produce actionable error messages.

### FR-02: Repository Snapshot Management

The system shall retrieve the requested repository revision and record:

- Repository owner and name.
- Repository URL.
- Selected branch, tag, or revision.
- Resolved commit SHA.
- Acquisition timestamp.
- Snapshot hash where applicable.
- Analysis status.

The system shall analyse a consistent snapshot and preserve its identity for manuscript provenance.

**Acceptance criteria:** Each manuscript can be linked to the exact repository revision used during analysis.

### FR-03: Repository Structure and Codebase Analysis

The system shall inspect relevant repository files and identify:

- Programming languages.
- Source modules and packages.
- Entry points.
- Configuration files.
- Dependency manifests.
- Model definitions.
- Data preprocessing scripts.
- Training and inference code.
- Evaluation scripts.
- Notebooks.
- Tests.
- Documentation.
- Experimental outputs.
- Deployment configuration.

The system shall generate a structured repository inventory and distinguish executable code, documentation, generated artefacts, and third-party dependencies where possible.

**Acceptance criteria:** The user can inspect a file inventory with paths, file types, detected technologies, and analysis status.

### FR-04: Architecture Reconstruction

The system shall infer the software architecture from repository evidence.

It shall identify, where applicable:

- Major components.
- Module responsibilities.
- Class and function relationships.
- Data flow.
- API boundaries.
- Model-training pipelines.
- Inference pipelines.
- External integrations.
- Configuration dependencies.
- Execution flow.

The system shall generate an architecture summary and, where supported, component or data-flow diagrams.

Inferred relationships shall be distinguished from explicitly confirmed implementation details.

**Acceptance criteria:** Major architectural conclusions are linked to relevant source files or code locations.

### FR-05: Methodology Reconstruction

The system shall identify implemented algorithms and reconstruct their execution logic.

For relevant projects, it shall extract:

- Problem formulation.
- Inputs and outputs.
- Preprocessing steps.
- Feature engineering.
- Model architecture.
- Training procedure.
- Optimisation objectives.
- Loss functions.
- Hyperparameters.
- Validation strategy.
- Evaluation procedures.
- Inference logic.

The system may generate equations, pseudocode, and algorithm descriptions when supported by the implementation.

It shall not claim that an algorithm is implemented merely because it is mentioned in documentation.

**Acceptance criteria:** The methodology report includes supporting code references and flags uncertain interpretations.

### FR-06: Experimental Evidence Extraction

The system shall inspect available:

- CSV and JSON files.
- Jupyter notebooks.
- Training and evaluation scripts.
- Logs.
- Configuration files.
- Result tables.
- Figures.
- README result sections.
- Supplementary research documents.

It shall attempt to extract:

- Dataset names and date ranges.
- Sample counts.
- Data splits.
- Baseline models.
- Proposed models.
- Hyperparameters.
- Evaluation metrics.
- Numerical results.
- Statistical test outputs.
- Random seeds.
- Runtime and hardware information, where available.
- Documented limitations.

Each extracted result shall retain its source location.

The system shall distinguish between results reported in files and results independently reproduced through an execution procedure.

**Acceptance criteria:** Extracted numerical results remain traceable to their original artefacts and are not silently altered during generation.

### FR-07: Evidence Sufficiency and Consistency Analysis

The system shall assess whether sufficient evidence exists to support the intended manuscript.

It shall identify potential issues such as:

- Missing experimental results.
- Conflicting metrics across files.
- Unclear dataset provenance.
- Missing baseline comparisons.
- Incomplete validation procedures.
- Unspecified random seeds.
- Potential data leakage indicators.
- Unsupported performance claims.
- Inconsistent methodology descriptions.
- Missing reproducibility information.

The system may recommend additional experiments or documentation but shall not describe unperformed experiments as completed work.

**Acceptance criteria:** An evidence-gap report is available before the final manuscript is assembled.

### FR-08: Supplementary Material Ingestion

The system shall allow users to upload supplementary:

- Research reports.
- Experimental datasets.
- Result tables.
- Figures.
- Existing manuscript drafts.
- Research proposals.
- Academic publications.
- Other supporting documents.

The system shall record whether each item originated from the repository or was supplied separately.

## 3.2 Scholarly Research and Novelty Analysis

### FR-09: Academic Literature Retrieval

The system shall retrieve scholarly records through configured academic services.

Potential sources include Crossref, OpenAlex, arXiv, and other authorised scholarly services.

The system shall support retrieval by:

- Research topic.
- Keywords.
- Algorithm or model.
- Problem domain.
- Evaluation method.
- Author.
- Publication year.
- DOI.
- User-provided references.

It shall store available metadata such as title, authors, year, venue, DOI, URL, abstract, access status, and retrieval date.

**Acceptance criteria:** Imported records contain available metadata and an identifiable source reference.

### FR-10: Literature Analysis

The system shall analyse retrieved literature for:

- Research objectives.
- Methods.
- Datasets.
- Evaluation procedures.
- Main findings.
- Limitations.
- Reported future work.
- Relationships to the current project.

It shall distinguish reported findings from its own interpretations.

Where full text is unavailable, the system shall disclose when conclusions are based on abstracts or limited metadata.

### FR-11: Research Contribution and Gap Analysis

The system shall compare the implementation with retrieved literature across relevant dimensions, including:

- Problem formulation.
- Model architecture.
- Algorithms.
- Data sources.
- Experimental design.
- Evaluation metrics.
- Reported limitations.

It shall propose potential research gaps and contribution statements based on the available evidence.

The system shall not claim that a contribution is novel solely because a search did not retrieve an equivalent publication.

**Acceptance criteria:** Proposed research gaps include a comparison rationale and links to relevant sources where available.

## 3.3 Manuscript Generation

### FR-12: Manuscript Planning

The system shall generate an editable manuscript outline based on the repository, available evidence, publication type, and journal requirements.

Supported sections shall include:

- Title.
- Abstract.
- Keywords.
- Introduction.
- Background.
- Related Work or Literature Review.
- Research Gap.
- Research Objectives and Contributions.
- Methodology.
- System Architecture.
- Experimental Setup.
- Results.
- Discussion.
- Limitations.
- Conclusion.
- References.

Optional sections shall include equations, algorithms, appendices, data availability, code availability, funding, acknowledgements, and declarations.

The system shall allow users to add, remove, rename, and reorder sections.

### FR-13: Automatic Manuscript Generation

Automatic Mode shall generate a complete initial manuscript using the repository analysis, approved evidence, scholarly sources, and selected publication requirements.

The system shall:

1. Assemble repository-analysis findings.
2. Select relevant evidence for each section.
3. Retrieve appropriate scholarly sources.
4. Generate sections using section-specific instructions.
5. Insert source-linked citations.
6. Preserve approved numerical results.
7. Run evidence and citation checks.
8. Apply the journal profile.
9. Assemble the document.
10. Generate compliance and unresolved-issues reports.

The output shall be labelled as a draft requiring researcher review.

### FR-14: Guided Manuscript Generation

Guided Mode shall provide review checkpoints for:

1. Repository inventory.
2. Methodology reconstruction.
3. Experimental evidence.
4. Literature selection.
5. Research-gap analysis.
6. Contribution approval.
7. Manuscript outline.
8. Section generation.
9. Citation verification.
10. Journal compliance.
11. Final export.

Users shall be able to correct system inferences and approve or reject proposed content.

### FR-15: Academic Writing and Revision

The system shall assist with:

- Grammar and punctuation.
- Academic tone.
- Clarity.
- Coherence.
- Redundancy reduction.
- Paragraph transitions.
- Terminology consistency.
- Sentence variation.
- Conciseness.
- Section-level consistency.

The system shall preserve technical meaning, equations, numerical results, and source attribution unless the user explicitly approves a substantive change.

Users shall be able to compare revisions and accept or reject them.

The system shall optimise for readable, natural academic prose and shall not guarantee evasion of AI-detection systems.

## 3.4 Evidence and Citation Verification

### FR-16: Claim and Evidence Management

The system shall identify substantive claims in manuscript sections and associate them with relevant evidence.

Evidence categories shall include:

- Repository implementation evidence.
- Experimental evidence.
- Scholarly source evidence.
- User-provided evidence.
- System inference.

The system shall maintain links between manuscript claims, citations, and supporting source records.

### FR-17: Citation and Claim Verification

The system shall verify available bibliographic metadata and assess whether cited sources support the associated claims.

Supported verification states shall include:

- `supported`
- `partially_supported`
- `contradicted`
- `unverified`
- `citation_missing`

The system shall assess source relevance, supporting passages, claim specificity, and whether the manuscript overstates the available evidence.

It shall distinguish a reference's existence from whether that reference supports a particular claim.

**Acceptance criteria:** A reviewer can inspect a claim, its source, supporting passage, verification status, and explanation.

### FR-18: Reproducibility and Provenance

The system shall retain relevant provenance information, including:

- Repository URL.
- Commit SHA.
- Source file paths and code locations.
- Experimental artefact identifiers.
- Extracted metric records.
- Scholarly source identifiers.
- Citation mappings.
- Generation configuration.
- User corrections and approvals.
- Verification outcomes.
- Journal profile version.
- Template version.

The system shall distinguish repository-reported results from independently reproduced results.

## 3.5 Journal Template Intelligence and Formatting

### FR-19: Journal and Publication Selection

The system shall allow users to select a target journal or conference and associate it with a research project.

Available information may include:

- Journal or conference name.
- Publisher.
- Manuscript type.
- Official author-guidelines URL.
- Citation style.
- Official template.
- Required declarations.
- Word and page limits.
- Submission requirements.

The system shall distinguish user-selected venues from system recommendations.

### FR-20: Journal Template Import

The system shall support importing official DOCX and DOC templates and supported author-guidelines documents.

It shall inspect, where available:

- Page size and margins.
- Fonts and paragraph styles.
- Heading hierarchy.
- Title formatting.
- Abstract and keyword structure.
- Required manuscript sections.
- Word and page limits.
- Citation and reference style.
- Figure and table caption rules.
- Equation formatting.
- Headers and footers.
- Page numbering.
- Required declarations.
- Template placeholders.

For legacy DOC files, the system may use a compatible conversion process before inspection and modification.

The system shall preserve the source template's identity and record when it was obtained.

### FR-21: Journal Requirement Profile

The system shall create a structured journal profile from the uploaded template and official author guidelines.

The profile shall distinguish:

1. Explicitly documented requirements.
2. Formatting inferred from the template.
3. Requirements requiring confirmation.
4. Requirements that cannot be verified.

Users shall be able to inspect, correct, and approve the profile before final manuscript generation.

When a template and author guidelines conflict, the system shall flag the conflict for review rather than silently choose one.

### FR-22: Journal-Adaptive Manuscript Generation

The system shall adapt manuscript content and structure to the approved journal profile.

Adaptations may include:

- Section order.
- Abstract format.
- Keyword count.
- Heading hierarchy.
- Word limits.
- Citation style.
- Reference formatting.
- Required declarations.
- Table and figure conventions.
- Manuscript-specific structural requirements.

The system shall not remove scientifically necessary information merely to satisfy a formatting constraint. It shall flag conflicts between manuscript completeness and publication limits.

### FR-23: Template-Preserving Document Assembly

The system shall assemble the manuscript using the selected official template when available.

For supported DOCX templates, it shall preserve applicable:

- Document styles.
- Page settings.
- Section properties.
- Headers and footers.
- Heading styles.
- Numbering.
- Table and caption styles.
- Other supported structural elements.

The system shall replace placeholders and insert manuscript content without unnecessarily recreating the document from scratch.

Where a template cannot be modified reliably, the system shall disclose the limitation and offer an alternative export.

**Acceptance criteria:** The output preserves supported template formatting and reports elements that could not be retained.

### FR-24: Journal Compliance Validation

Before export, the system shall compare the manuscript with the approved journal profile.

It shall check applicable requirements such as:

- Required sections and order.
- Word limits.
- Abstract length and structure.
- Keyword constraints.
- Heading hierarchy.
- Citation and bibliography consistency.
- Figure and table numbering.
- Caption presence.
- Required declarations.
- Missing placeholders.
- Available layout and formatting constraints.

Each check shall return one of the following states:

- `passed`
- `failed`
- `warning`
- `not_verifiable`

The compliance report shall identify the requirement, observed condition, and suggested correction.

The system shall not claim complete compliance with requirements it cannot inspect or validate.

### FR-25: Template and Journal Profile Versioning

The system shall associate each manuscript with the journal profile and template version used to generate it.

When a template or requirement profile changes, the system shall preserve the previous version and identify manuscript elements potentially affected by the change.

## 3.6 Export and Project Management

### FR-26: Manuscript Export

The system shall support exporting manuscripts to:

- DOCX.
- PDF.
- Markdown.
- BibTeX or another supported structured reference format.

It shall preserve supported headings, paragraphs, equations, tables, figures, citations, and references.

The system may offer LaTeX export as a future enhancement.

### FR-27: Project and Version Management

The system shall allow users to:

- Create and manage research projects.
- Save repository snapshots and analysis reports.
- Track manuscript versions.
- Compare drafts.
- Restore earlier versions.
- Review unresolved warnings.
- Re-run analysis on a new repository revision.
- Update the journal profile and regenerate the manuscript when required.

Repository and template updates shall not silently overwrite the provenance of previous manuscripts.

### FR-28: Processing Status and Error Handling

The system shall display processing status for:

- Repository acquisition.
- Code analysis.
- Evidence extraction.
- Literature retrieval.
- Manuscript generation.
- Citation verification.
- Template analysis.
- Document assembly.
- Compliance checking.
- Export.

It shall handle invalid URLs, access failures, API rate limits, unsupported files, incomplete extraction, missing evidence, and external-service failures.

Recoverable failures shall not cause previously saved work to be lost.

---

# 4. NON-FUNCTIONAL REQUIREMENTS

## NFR-01: Accuracy and Reliability

The system shall prioritise technical and evidential accuracy over manuscript completeness.

It shall not fabricate citations, experimental results, code behaviour, bibliographic metadata, or scientific contributions.

## NFR-02: Performance

Initial performance targets shall be measured under a defined test environment.

- Standard user-interface requests: response within 2 seconds for at least 95% of requests, excluding long-running tasks.
- Repository analysis: asynchronous processing with visible progress.
- Literature retrieval: configurable timeouts and rate-limit handling.
- Manuscript generation: asynchronous processing for long documents.
- Template analysis and export: completion status and recoverable error reporting.

Performance targets shall be refined using representative repositories and manuscript templates.

## NFR-03: Security

The system shall:

- Use secure authentication and authorisation.
- Validate repository URLs and prevent server-side request forgery.
- Securely store access tokens.
- Validate uploaded files and enforce size limits.
- Prevent unauthorised access to private project content.
- Avoid logging secrets or unnecessary confidential content.
- Treat repository contents as untrusted data.
- Avoid executing repository code by default.
- Use isolated execution environments if code execution is introduced.
- Protect document processing from malicious files.

## NFR-04: Privacy

The system shall disclose how repository contents, manuscripts, and uploaded documents are processed.

Private source code shall be accessible only to authorised users and services.

The system shall not use confidential project content for model training without explicit permission and a disclosed policy.

Users shall be able to delete project data subject to disclosed retention and backup constraints.

## NFR-05: Reproducibility

The system shall retain sufficient provenance to identify the repository revision, supporting evidence, scholarly sources, template version, and generation configuration associated with a manuscript.

## NFR-06: Maintainability

Repository analysis, literature retrieval, generation, verification, template processing, and export shall be modular and independently testable.

## NFR-07: Scalability

Long-running tasks shall use background workers where appropriate. The system shall support configurable repository-size, document-size, and processing limits.

## NFR-08: Usability

The interface shall make complex analysis understandable through evidence links, review checkpoints, clear warnings, and actionable compliance reports.

Users shall be able to distinguish confirmed information, system inferences, and unresolved questions.

## NFR-09: Interoperability

The system shall support standard document and bibliographic formats wherever feasible.

It shall preserve compatibility with supported DOCX templates and clearly report any formatting limitations caused by unsupported Word features.

---

# 5. SYSTEM ARCHITECTURE

## 5.1 Presentation Layer

Provides:

- Repository submission.
- Generation-mode selection.
- Repository-analysis dashboard.
- Experimental evidence review.
- Literature review workspace.
- Journal and template selection.
- Manuscript editor.
- Citation inspection.
- Compliance report.
- Export controls.

## 5.2 API and Workflow Orchestration Layer

Responsible for:

- Authentication.
- Project management.
- Job scheduling.
- Workflow state.
- Service coordination.
- Progress reporting.
- Error recovery.
- Version management.

## 5.3 Repository Intelligence Layer

Contains:

- GitHub connector.
- Snapshot manager.
- File inventory service.
- Language and dependency detector.
- Static-analysis service.
- Architecture reconstruction.
- Methodology extraction.

## 5.4 Experimental Evidence Layer

Contains:

- Notebook parser.
- Configuration extractor.
- Structured data parser.
- Result-table extractor.
- Metric extractor.
- Evidence consistency checker.
- Evidence sufficiency analyser.

## 5.5 Scholarly Research Layer

Contains:

- Academic metadata retrieval.
- Literature deduplication.
- Abstract and accessible full-text processing.
- Semantic retrieval.
- Related-work comparison.
- Research-gap hypothesis generation.

## 5.6 Manuscript Generation Layer

Contains:

- Manuscript outline generator.
- Section planning.
- Evidence retrieval.
- Automatic generation workflow.
- Guided generation workflow.
- Academic prose revision.
- Manuscript assembly.

## 5.7 Evidence Verification Layer

Contains:

- Claim segmentation.
- Repository provenance mapping.
- Experimental result validation.
- Citation metadata verification.
- Claim-to-source assessment.
- Numerical consistency checks.
- Verification report generation.

## 5.8 Journal Template Intelligence Layer

Contains:

- Template importer.
- DOC/DOCX conversion where required.
- Document structure and style inspector.
- Author-guidelines parser.
- Journal profile builder.
- Requirement conflict detector.
- Template-preserving assembler.
- Journal compliance validator.

## 5.9 Persistence and Export Layer

Contains:

- User and project storage.
- Repository snapshot storage.
- Evidence and literature storage.
- Manuscript version storage.
- Journal profile and template version storage.
- Citation and verification storage.
- Document export.

## 5.10 High-Level Data Flow

1. The user creates a project and submits a GitHub repository.
2. The system resolves and stores the selected repository revision.
3. The repository is inventoried and analysed.
4. The methodology and architecture are reconstructed.
5. Experimental evidence is extracted and checked.
6. Related scholarly literature is retrieved.
7. Potential contributions and an outline are proposed.
8. The user selects Automatic or Guided Mode.
9. The target journal and template are selected or imported.
10. The journal requirement profile is generated and reviewed.
11. The manuscript is drafted using repository and scholarly evidence.
12. Claims and citations are verified.
13. The manuscript is assembled using the journal template.
14. Compliance checks are performed.
15. The researcher reviews and exports the document.
16. Repository, template, and manuscript provenance is retained.

---

# 6. DATA REQUIREMENTS

## 6.1 User

Stores account information.

Fields include:

- `id`
- `email`
- `password_hash` or external authentication identifier
- `status`
- `created_at`
- `updated_at`

## 6.2 ResearchProject

Stores the research project.

Fields include:

- `id`
- `owner_id`
- `title`
- `research_topic`
- `research_question`
- `objectives`
- `target_publication`
- `citation_style`
- `generation_mode`
- `status`
- `created_at`
- `updated_at`

## 6.3 Repository

Fields include:

- `id`
- `project_id`
- `repository_url`
- `owner_name`
- `repository_name`
- `visibility`
- `default_branch`
- `selected_revision`
- `resolved_commit_sha`
- `acquisition_status`
- `last_analysis_at`

## 6.4 RepositorySnapshot

Fields include:

- `id`
- `repository_id`
- `commit_sha`
- `branch_or_tag`
- `snapshot_hash`
- `acquired_at`
- `analysis_status`
- `file_count`
- `excluded_file_count`
- `analysis_summary`

## 6.5 RepositoryFile

Fields include:

- `id`
- `snapshot_id`
- `path`
- `file_type`
- `language`
- `content_hash`
- `size_bytes`
- `analysis_status`
- `relevance_category`
- `exclusion_reason`

## 6.6 CodeComponent

Fields include:

- `id`
- `snapshot_id`
- `name`
- `component_type`
- `file_path`
- `start_line`
- `end_line`
- `description`
- `input_description`
- `output_description`
- `dependencies`
- `confidence`
- `evidence_references`

## 6.7 MethodologyRecord

Fields include:

- `id`
- `snapshot_id`
- `problem_description`
- `algorithm_description`
- `preprocessing_steps`
- `architecture_description`
- `training_procedure`
- `evaluation_procedure`
- `hyperparameters`
- `equations`
- `pseudocode`
- `supporting_components`
- `review_status`

## 6.8 ExperimentalArtifact

Fields include:

- `id`
- `snapshot_id`
- `project_id`
- `file_path`
- `artifact_type`
- `content_hash`
- `source_type`
- `extraction_status`
- `created_at`

## 6.9 ExperimentalResult

Fields include:

- `id`
- `artifact_id`
- `experiment_name`
- `model_name`
- `dataset_name`
- `metric_name`
- `metric_value`
- `metric_unit`
- `split_name`
- `random_seed`
- `reported_or_reproduced`
- `reproduction_run_id`
- `source_location`
- `verification_status`

## 6.10 EvidenceRecord

Fields include:

- `id`
- `project_id`
- `evidence_type`
- `source_file_id`
- `source_artifact_id`
- `source_location`
- `evidence_text`
- `structured_value`
- `confidence`
- `verification_status`
- `created_at`

## 6.11 ScholarlySource

Fields include:

- `id`
- `project_id`
- `title`
- `authors`
- `publication_year`
- `venue`
- `doi`
- `url`
- `abstract`
- `access_status`
- `metadata_source`
- `retrieved_at`
- `metadata_verification_status`

## 6.12 LiteratureComparison

Fields include:

- `id`
- `project_id`
- `scholarly_source_id`
- `comparison_dimension`
- `related_method`
- `similarities`
- `differences`
- `limitations`
- `supporting_evidence`
- `review_status`

## 6.13 JournalProfile

Stores structured publication requirements.

Fields include:

- `id`
- `journal_name`
- `publisher`
- `official_guidelines_url`
- `manuscript_type`
- `citation_style`
- `required_sections`
- `section_order`
- `abstract_requirements`
- `keyword_requirements`
- `word_limit`
- `page_limit`
- `figure_requirements`
- `table_requirements`
- `equation_requirements`
- `declaration_requirements`
- `layout_requirements`
- `verification_status`
- `profile_version`
- `retrieved_at`

## 6.14 JournalTemplate

Fields include:

- `id`
- `journal_profile_id`
- `template_filename`
- `template_format`
- `storage_reference`
- `content_hash`
- `template_version`
- `source_url`
- `uploaded_at`
- `analysis_status`

## 6.15 TemplateStyle

Stores extracted document formatting rules.

Fields include:

- `id`
- `journal_template_id`
- `style_name`
- `style_type`
- `font_family`
- `font_size`
- `bold`
- `italic`
- `alignment`
- `spacing_before`
- `spacing_after`
- `line_spacing`
- `numbering_rules`
- `section_properties`
- `source_location`

## 6.16 JournalRequirement

Stores an individual publication requirement.

Fields include:

- `id`
- `journal_profile_id`
- `requirement_type`
- `description`
- `expected_value`
- `source_type`
- `source_location`
- `confidence`
- `verification_status`
- `user_approval_status`

## 6.17 Manuscript

Fields include:

- `id`
- `project_id`
- `repository_snapshot_id`
- `journal_profile_id`
- `journal_template_id`
- `version_number`
- `title`
- `generation_mode`
- `outline`
- `status`
- `citation_style`
- `generation_configuration`
- `created_at`
- `updated_at`

## 6.18 ManuscriptSection

Fields include:

- `id`
- `manuscript_id`
- `section_type`
- `heading`
- `content`
- `section_order`
- `generation_status`
- `review_status`
- `version_number`

## 6.19 Claim

Fields include:

- `id`
- `manuscript_section_id`
- `claim_text`
- `claim_type`
- `evidence_category`
- `verification_status`
- `verification_explanation`
- `review_status`

## 6.20 Citation

Fields include:

- `id`
- `claim_id`
- `scholarly_source_id`
- `citation_style`
- `formatted_text`
- `source_location`
- `metadata_status`
- `support_status`

## 6.21 ComplianceCheck

Fields include:

- `id`
- `manuscript_id`
- `journal_requirement_id`
- `check_type`
- `status`
- `observed_value`
- `expected_value`
- `explanation`
- `suggested_correction`
- `checked_at`

## 6.22 ReviewAction

Fields include:

- `id`
- `project_id`
- `user_id`
- `target_type`
- `target_id`
- `action_type`
- `previous_value`
- `approved_value`
- `comment`
- `created_at`

## 6.23 AnalysisJob

Fields include:

- `id`
- `project_id`
- `job_type`
- `status`
- `progress`
- `started_at`
- `completed_at`
- `error_code`
- `error_message`

---

# 7. USE CASES

## UC-01: Automatic Research Paper Generation

**Actor:** Researcher

**Preconditions:** A repository is accessible and the user has created a project.

**Main flow:**

1. Submit the GitHub repository URL.
2. Select Automatic Mode.
3. Select the target publication or choose a generic manuscript format.
4. Upload the official template and author guidelines if available.
5. The system acquires the repository snapshot.
6. The system analyses the codebase and reconstructs the methodology.
7. The system extracts experimental evidence and identifies gaps.
8. The system retrieves related scholarly literature.
9. The system creates a manuscript outline.
10. The system generates the manuscript.
11. The system verifies claims and citations.
12. The system applies the journal profile and template.
13. The system validates compliance.
14. The system produces the manuscript and reports.
15. The researcher reviews and exports the draft.

**Postcondition:** A versioned manuscript exists with evidence provenance, journal-profile linkage, and unresolved-issue reporting.

## UC-02: Guided Research Paper Generation

**Actor:** Researcher

**Main flow:**

1. Submit the repository.
2. Select Guided Mode.
3. Review the repository inventory.
4. Approve or correct the methodology reconstruction.
5. Review extracted experimental evidence.
6. Approve or correct the results.
7. Review the related literature.
8. Approve or revise the proposed research contribution.
9. Select the journal and template.
10. Review the extracted journal profile.
11. Approve the manuscript outline.
12. Generate and review sections individually.
13. Verify citations and evidence.
14. Review journal compliance.
15. Export the approved manuscript.

**Postcondition:** The generated manuscript incorporates researcher-approved findings and records relevant review decisions.

## UC-03: Repository Analysis Without Paper Generation

**Actor:** Researcher

**Main flow:**

1. Submit a repository.
2. Run repository analysis.
3. Inspect the codebase inventory.
4. Review architecture and methodology reports.
5. Inspect extracted experimental evidence.
6. Review identified evidence gaps.

**Postcondition:** A structured repository-analysis report is available for independent review.

## UC-04: Journal Template Import

**Actor:** Researcher

**Main flow:**

1. Select a journal or create a publication profile.
2. Upload its official DOCX/DOC template or author guidelines.
3. The system inspects document styles and requirements.
4. The system extracts a structured journal profile.
5. The system identifies uncertain or conflicting requirements.
6. The researcher reviews and corrects the profile.
7. The system saves an approved profile version.

**Postcondition:** An approved journal profile and, where available, an associated template are ready for manuscript generation.

## UC-05: Citation and Evidence Review

**Actor:** Researcher

**Main flow:**

1. Select a manuscript claim.
2. Inspect its associated evidence.
3. Review the supporting repository location, result record, or scholarly passage.
4. Inspect the verification status.
5. Correct, approve, or replace the claim.
6. Save the review action.

**Postcondition:** The claim has a recorded verification result and review history.

## UC-06: Journal Compliance Validation

**Actor:** Researcher

**Main flow:**

1. Select a manuscript and approved journal profile.
2. Run compliance validation.
3. Inspect passed checks, failures, warnings, and unverifiable requirements.
4. Review recommended corrections.
5. Apply or reject changes.
6. Re-run validation.
7. Export the updated manuscript and compliance report.

**Postcondition:** The manuscript has a current compliance report linked to the relevant journal profile.

## UC-07: Update After a Repository Change

**Actor:** Researcher

**Main flow:**

1. Select a new repository revision.
2. Acquire and analyse the new snapshot.
3. Compare relevant files and components.
4. Identify potentially affected manuscript claims.
5. Propose content updates.
6. Revalidate the manuscript.
7. Save a new version.

**Postcondition:** The new manuscript is linked to the updated repository revision without destroying the previous version's provenance.

---

# 8. EXTERNAL INTERFACES

The system may integrate with:

- GitHub APIs and controlled Git operations.
- Crossref.
- OpenAlex.
- arXiv.
- Other permitted scholarly metadata services.
- Open-access discovery services.
- LLM APIs or locally hosted models.
- PDF and Word document-processing libraries.
- OCR services where required.
- Citation-formatting libraries.
- Document-export libraries.
- Optional code-analysis tools.

Each integration shall comply with applicable access controls, API terms, rate limits, privacy requirements, and licensing restrictions.

The system shall not bypass publisher access restrictions.

---

# 9. TESTING AND ACCEPTANCE STRATEGY

## 9.1 Repository Analysis Testing

Evaluate whether the system correctly identifies:

- Relevant files.
- Programming languages.
- Dependencies.
- Model definitions.
- Data pipelines.
- Architecture components.
- Execution flow.

The reference set shall consist of manually inspected repositories.

## 9.2 Methodology Reconstruction Testing

Compare generated descriptions with actual source implementations.

Evaluate algorithm identification, input/output descriptions, preprocessing accuracy, architecture fidelity, equations, and unsupported technical claims.

## 9.3 Experimental Evidence Testing

Compare extracted numerical values and configurations against their original artefacts.

Measure numerical extraction accuracy, source-location accuracy, dataset identification, split identification, and consistency detection.

## 9.4 Citation Verification Testing

Evaluate bibliographic metadata accuracy, citation-to-reference matching, claim-support classification, and unsupported-claim detection.

## 9.5 Manuscript Quality Testing

Use human review to assess:

- Technical fidelity.
- Citation correctness.
- Evidence coverage.
- Logical coherence.
- Readability.
- Consistency across sections.
- Reproducibility information.
- Accuracy of limitations and conclusions.

## 9.6 Template Extraction Testing

Compare the extracted journal profile against manually inspected templates and author guidelines.

Evaluate:

- Style extraction.
- Page-layout extraction.
- Section requirements.
- Word-limit extraction.
- Citation-style identification.
- Table and figure rules.
- Declaration requirements.
- Handling of conflicting or missing instructions.

## 9.7 Document Formatting Testing

Generate test manuscripts from multiple supported templates.

Evaluate whether the output preserves applicable styles, section properties, headers, footers, numbering, tables, captions, references, and other supported elements.

Formatting tests shall include templates with complex layouts and unsupported features to ensure that limitations are reported correctly.

## 9.8 Compliance Validation Testing

Use manually reviewed manuscripts and journal profiles to test whether the compliance engine correctly identifies passing, failing, warning, and unverifiable conditions.

## 9.9 Workflow Testing

Test complete Automatic and Guided workflows, including repository-access failures, missing evidence, unavailable scholarly sources, template parsing failures, conflicting requirements, and recoverable export errors.

---

# 10. MINIMUM VIABLE PRODUCT

The MVP shall deliver one complete GitHub-to-journal-formatted-manuscript workflow.

## 10.1 Included Features

1. GitHub repository submission.
2. Public repository acquisition and commit tracking.
3. Repository inventory and language detection.
4. Analysis of Python source files and common project artefacts.
5. README, notebook, CSV, configuration, and dependency-file inspection.
6. Basic architecture and methodology reconstruction.
7. Experimental result extraction.
8. Evidence-gap reporting.
9. Scholarly metadata retrieval.
10. Basic related-work synthesis.
11. Automatic manuscript generation.
12. Guided manuscript generation.
13. Claim-to-source traceability.
14. Citation metadata verification.
15. Journal profile creation.
16. DOCX template upload and analysis.
17. Basic author-guidelines ingestion.
18. Journal-adaptive manuscript assembly.
19. DOCX and Markdown export.
20. Basic journal compliance validation.
21. Repository and manuscript version tracking.
22. Unresolved-issues and compliance reports.

## 10.2 Deferred Features

The following shall be considered for later releases:

- Comprehensive multi-language code analysis.
- Arbitrary repository execution.
- Autonomous scientific experimentation.
- Guaranteed novelty determination.
- Guaranteed publication readiness.
- Full support for every Word template feature.
- Universal journal-template coverage.
- Advanced LaTeX generation.
- Extensive similarity-detection integrations.
- Enterprise-scale collaborative editing.
- Automated submission to journal portals.

---

# 11. RISKS AND MITIGATION

| Risk | Mitigation |
|---|---|
| Incorrect code interpretation | Link technical conclusions to source locations and allow corrections. |
| Fabricated experimental results | Extract results from actual artefacts and flag missing information. |
| Unsupported novelty claims | Compare against retrieved literature and disclose search limitations. |
| Incorrect citations | Validate bibliographic records and inspect source support. |
| Irrelevant literature | Use targeted retrieval and researcher review. |
| Private-code exposure | Enforce access controls and disclose external-provider processing. |
| Malicious repository instructions | Treat repository contents as untrusted data. |
| Unsafe code execution | Do not execute code by default; sandbox optional execution. |
| Incorrect journal profile | Retain requirement provenance and provide manual confirmation. |
| Template corruption | Validate template structure and report unsupported elements. |
| Conflicting publication rules | Flag conflicts for researcher resolution. |
| Formatting loss | Test exported documents and preserve supported template properties. |
| Overstated compliance | Distinguish passed, failed, warning, and unverifiable requirements. |
| Changed repository contents | Preserve immutable snapshot identifiers. |
| Changed journal requirements | Version profiles and identify potentially affected manuscripts. |

---

# 12. SUCCESS METRICS

The system shall be evaluated using measurable criteria, including:

- Repository file-classification accuracy.
- Methodology reconstruction fidelity.
- Experimental-result extraction accuracy.
- Percentage of substantive claims linked to evidence.
- Citation metadata accuracy.
- Citation-support verification performance.
- Frequency of fabricated or unsupported claims.
- Human-rated manuscript readability and coherence.
- Journal requirement extraction accuracy.
- Template-preservation success rate.
- Compliance-check precision and recall.
- Successful completion rate for Automatic and Guided workflows.
- Document export correctness.
- Provenance completeness.
- Recovery from external-service failures.

Specific numerical acceptance thresholds shall be established after constructing a manually reviewed evaluation dataset and measuring baseline performance.

---

# 13. FUTURE ENHANCEMENTS

Potential future capabilities include:

- Broader programming-language support.
- Sandboxed experiment reproduction.
- Automated statistical consistency checks.
- Research architecture diagram generation.
- More advanced research-gap analysis.
- Journal-specific submission checklists.
- LaTeX export.
- Figure and table reconstruction.
- Reference-manager integrations.
- Collaborative researcher-supervisor review.
- Systematic literature review support.
- Reproducibility audits.
- Multi-agent analysis for code, literature, experiments, and journal compliance.
- More comprehensive journal-template coverage.
- Integration with manuscript submission platforms where permitted.

---

# 14. CORE DESIGN PRINCIPLES

ResearchScribe shall follow these principles:

1. **Repository-first:** Analyse the implementation before writing about the methodology.
2. **Evidence before prose:** Substantive claims require supporting evidence or an explicit uncertainty label.
3. **No invented results:** Missing experiments remain missing until valid evidence is supplied or generated.
4. **Honest novelty analysis:** Failure to retrieve related work is not proof of originality.
5. **Citation traceability:** Important literature-based claims remain linked to their sources.
6. **Journal-aware generation:** Use the selected publication's verified requirements when drafting and formatting.
7. **Template preservation:** Reuse supported template styles and structures rather than imitate them without verification.
8. **Human control:** Researchers can inspect, correct, and approve generated content.
9. **Versioned provenance:** Manuscripts retain their repository, evidence, and template identities.
10. **Natural academic writing:** Prioritise precision, clarity, coherence, and readable prose without promising AI-detector evasion.
11. **Secure processing:** Treat repositories and uploaded files as untrusted inputs.
12. **Researcher responsibility:** The system assists with manuscript preparation but does not replace scientific judgement or publication-policy compliance.

---

# 15. CONCLUSION

ResearchScribe v3.0 defines an evidence-grounded platform for converting GitHub repositories into research manuscripts prepared according to the requirements of a selected journal or conference.

The platform combines repository intelligence, methodology reconstruction, experimental evidence extraction, scholarly literature retrieval, manuscript generation, citation verification, journal template analysis, document assembly, and compliance validation.

Automatic Mode provides a complete initial draft, while Guided Mode gives researchers greater control over methodology, experimental evidence, research contributions, journal requirements, and manuscript content.

Both modes share a common provenance system so that manuscript claims can be inspected and corrected.

The final objective is to generate manuscripts that are not only readable and appropriately formatted but also technically faithful to the implementation, transparent about experimental evidence, supported by verifiable scholarly references, and aligned with the selected publication's documented requirements.

ResearchScribe shall be evaluated on technical accuracy, evidence traceability, citation correctness, reproducibility, document fidelity, and journal compliance rather than manuscript fluency alone.
