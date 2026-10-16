// ResearchScribe Frontend Client
const API_BASE = "/api/v1";

let state = {
  currentProject: null,
  currentManuscriptId: null,
  sections: [],
  currentSectionId: null,
  sources: [],
  evidence: [],
  claims: [],
  selectedUploadSourceId: null,
  polishOriginalText: "",
  polishRevisedText: ""
};

// DOM References
const projectSelect = document.getElementById("project-select");
const currentCitationStyle = document.getElementById("current-citation-style");
const sectionOutlineList = document.getElementById("section-outline-list");
const sectionTextarea = document.getElementById("section-textarea");
const editorSectionType = document.getElementById("editor-section-type");
const editorSectionTitle = document.getElementById("editor-section-title");
const claimsListContainer = document.getElementById("claims-list-container");
const drawerClaimsCount = document.getElementById("drawer-claims-count");
const sourcesTableBody = document.getElementById("sources-table-body");
const sourcesCountBadge = document.getElementById("sources-count-badge");
const evidenceCountBadge = document.getElementById("evidence-count-badge");
const evidenceCardsContainer = document.getElementById("evidence-cards-container");
const evidenceStatsText = document.getElementById("evidence-stats-text");
const searchResultsGrid = document.getElementById("search-results-grid");
const searchResultsSection = document.getElementById("search-results-section");

// Verification widget score elements
const globalAccuracyScore = document.getElementById("global-accuracy-score");
const countSupported = document.getElementById("count-supported");
const countPartial = document.getElementById("count-partial");
const countUnverified = document.getElementById("count-unverified");
const countMissing = document.getElementById("count-missing");

// Initialization
document.addEventListener("DOMContentLoaded", async () => {
  setupNavigationTabs();
  setupEventHandlers();
  await loadProjects();
});

// Navigation Tabs
function setupNavigationTabs() {
  document.querySelectorAll(".nav-tab").forEach(tab => {
    tab.addEventListener("click", () => {
      document.querySelectorAll(".nav-tab").forEach(t => t.classList.remove("active"));
      document.querySelectorAll(".view-panel").forEach(p => p.classList.remove("active"));

      tab.classList.add("active");
      const targetId = `panel-${tab.dataset.tab}`;
      const panel = document.getElementById(targetId);
      if (panel) panel.classList.add("active");

      if (tab.dataset.tab === "sources") { loadSources(); loadResearchGaps(); }
      if (tab.dataset.tab === "evidence") loadEvidence();
      if (tab.dataset.tab === "repository") loadRepositoryDashboard();
      if (tab.dataset.tab === "experiments") loadExperimentalMetrics();
      if (tab.dataset.tab === "guided-workflow") loadGuidedCheckpoints();
      if (tab.dataset.tab === "journal") loadJournalCompliance();
    });
  });
}

function setupEventHandlers() {
  // Project switcher
  projectSelect.addEventListener("change", async (e) => {
    await switchProject(e.target.value);
  });

  // New Project Button
  document.getElementById("btn-new-project").addEventListener("click", () => {
    const title = prompt("Enter Research Manuscript Title or Working Topic:");
    if (title && title.trim()) {
      createNewProject(title.trim());
    }
  });

  // Section Save
  document.getElementById("btn-save-section").addEventListener("click", saveCurrentSection);

  // Section Generate Modal
  document.getElementById("btn-generate-section").addEventListener("click", openGenerateModal);
  document.getElementById("btn-close-gen-modal").addEventListener("click", () => closeModal("modal-generate"));
  document.getElementById("btn-cancel-gen").addEventListener("click", () => closeModal("modal-generate"));
  document.getElementById("btn-confirm-generate").addEventListener("click", runSectionGeneration);

  // Section Verify Button
  document.getElementById("btn-verify-section").addEventListener("click", runSectionVerification);

  // Prose Refine Modal
  document.getElementById("btn-polish-prose").addEventListener("click", openPolishModal);
  document.getElementById("btn-close-polish-modal").addEventListener("click", () => closeModal("modal-polish"));
  document.getElementById("btn-cancel-polish").addEventListener("click", () => closeModal("modal-polish"));
  document.getElementById("btn-accept-polish").addEventListener("click", acceptPolishedText);
  document.getElementById("btn-re-polish").addEventListener("click", runProsePolish);

  document.querySelectorAll("#polish-mode-options .pill").forEach(p => {
    p.addEventListener("click", () => {
      document.querySelectorAll("#polish-mode-options .pill").forEach(x => x.classList.remove("active"));
      p.classList.add("active");
      runProsePolish();
    });
  });

  // Export Modal
  document.getElementById("btn-export-modal").addEventListener("click", () => openModal("modal-export"));
  document.getElementById("btn-close-export-modal").addEventListener("click", () => closeModal("modal-export"));
  document.getElementById("btn-cancel-export").addEventListener("click", () => closeModal("modal-export"));
  document.getElementById("btn-confirm-export").addEventListener("click", runExport);

  // v3.0 Auto Run & Intelligence Handlers
  const btnAutoRun = document.getElementById("btn-auto-run");
  if (btnAutoRun) btnAutoRun.addEventListener("click", triggerAutomaticRun);

  const btnReanalyze = document.getElementById("btn-re-analyze-repo");
  if (btnReanalyze) btnReanalyze.addEventListener("click", loadRepositoryDashboard);

  const btnUploadTpl = document.getElementById("btn-upload-template");
  if (btnUploadTpl) btnUploadTpl.addEventListener("click", uploadJournalTemplate);

  const btnRunComp = document.getElementById("btn-run-compliance");
  if (btnRunComp) btnRunComp.addEventListener("click", loadJournalCompliance);

  const btnRefreshGaps = document.getElementById("btn-refresh-gaps");
  if (btnRefreshGaps) btnRefreshGaps.addEventListener("click", loadResearchGaps);

  // Scholarly Search
  document.getElementById("btn-run-scholarly-search").addEventListener("click", runScholarlySearch);
  document.getElementById("scholarly-search-input").addEventListener("keypress", (e) => {
    if (e.key === "Enter") runScholarlySearch();
  });
  document.getElementById("btn-close-search").addEventListener("click", () => {
    searchResultsSection.style.display = "none";
  });

  // Batch PDF Upload & Manual Source Add (FR-02, FR-10)
  const btnOpenBatch = document.getElementById("btn-open-batch-upload");
  if (btnOpenBatch) btnOpenBatch.addEventListener("click", () => openModal("modal-batch-upload"));
  const btnCloseBatch = document.getElementById("btn-close-batch-modal");
  if (btnCloseBatch) btnCloseBatch.addEventListener("click", () => closeModal("modal-batch-upload"));
  const btnCancelBatch = document.getElementById("btn-cancel-batch");
  if (btnCancelBatch) btnCancelBatch.addEventListener("click", () => closeModal("modal-batch-upload"));
  const btnStartBatch = document.getElementById("btn-start-batch-upload");
  if (btnStartBatch) btnStartBatch.addEventListener("click", handleBatchPdfUpload);

  const btnManualAdd = document.getElementById("btn-add-manual-source") || document.getElementById("btn-manual-source");
  if (btnManualAdd) btnManualAdd.addEventListener("click", openAddSourceModal);

  // Edit Source Metadata Modal (FR-03.5)
  const btnCloseEdit = document.getElementById("btn-close-edit-source-modal");
  if (btnCloseEdit) btnCloseEdit.addEventListener("click", () => closeModal("modal-edit-source"));
  const btnCancelEdit = document.getElementById("btn-cancel-edit-source");
  if (btnCancelEdit) btnCancelEdit.addEventListener("click", () => closeModal("modal-edit-source"));
  const btnSaveEdit = document.getElementById("btn-save-edit-source");
  if (btnSaveEdit) btnSaveEdit.addEventListener("click", saveSourceMetadata);
  const btnVerifyOnline = document.getElementById("btn-verify-source-online");
  if (btnVerifyOnline) btnVerifyOnline.addEventListener("click", verifySourceMetadataOnline);

  // 4-Level Verification Audit Button (FR-09)
  const btnRunAudit = document.getElementById("btn-run-full-audit");
  if (btnRunAudit) btnRunAudit.addEventListener("click", loadGlobalVerificationAudit);

  // Upload PDF Modal (Single target)
  const dropZone = document.getElementById("pdf-drop-zone");
  const fileInput = document.getElementById("pdf-file-input");
  if (dropZone && fileInput) {
    dropZone.addEventListener("click", () => fileInput.click());
    fileInput.addEventListener("change", (e) => {
      if (e.target.files.length > 0) handleFileUpload(e.target.files[0]);
    });
    dropZone.addEventListener("dragover", (e) => { e.preventDefault(); dropZone.style.borderColor = "#3B82F6"; });
    dropZone.addEventListener("dragleave", () => { dropZone.style.borderColor = "#334155"; });
    dropZone.addEventListener("drop", (e) => {
      e.preventDefault();
      if (e.dataTransfer.files.length > 0) handleFileUpload(e.dataTransfer.files[0]);
    });
  }
  const btnCloseUpload = document.getElementById("btn-close-upload-modal");
  if (btnCloseUpload) btnCloseUpload.addEventListener("click", () => closeModal("modal-upload-pdf"));
  const btnCancelUpload = document.getElementById("btn-cancel-upload");
  if (btnCancelUpload) btnCancelUpload.addEventListener("click", () => closeModal("modal-upload-pdf"));

  // Evidence Category Filter Pills
  document.querySelectorAll("#evidence-category-filters .pill").forEach(pill => {
    pill.addEventListener("click", () => {
      document.querySelectorAll("#evidence-category-filters .pill").forEach(p => p.classList.remove("active"));
      pill.classList.add("active");
      loadEvidence(pill.dataset.cat);
    });
  });

  // Save Project Settings (FR-02)
  const btnSaveProj = document.getElementById("btn-save-project-settings");
  if (btnSaveProj) btnSaveProj.addEventListener("click", saveProjectSettings);
}

// Data Fetching: Projects
async function loadProjects() {
  try {
    const res = await fetch(`${API_BASE}/projects`);
    const projects = await res.json();
    projectSelect.innerHTML = "";

    if (projects.length === 0) {
      // Create initial sample research project
      await createNewProject("Evidence-Grounded AI Research Paper Writing and Citation Verification System");
      return;
    }

    projects.forEach(p => {
      const opt = document.createElement("option");
      opt.value = p.id;
      opt.textContent = p.title;
      projectSelect.appendChild(opt);
    });

    await switchProject(projects[0].id);
  } catch (err) {
    showToast("Failed to load projects: " + err.message, "error");
  }
}

async function createNewProject(title) {
  try {
    const res = await fetch(`${API_BASE}/projects`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: title,
        topic: "Automated citation verification and factual traceability in LLMs",
        research_problem: "Hallucinated citations and unverified factual assertions in AI-assisted writing",
        research_questions: "How can sentence-level evidence mapping reduce unsupported claims in generated manuscripts?",
        objectives: "Develop a modular architecture linking generated claims to primary source passages.",
        academic_discipline: "Computer Science / NLP",
        citation_style: "APA"
      })
    });
    const proj = await res.json();
    showToast("Research project created successfully", "success");
    await loadProjects();
    projectSelect.value = proj.id;
    await switchProject(proj.id);
  } catch (err) {
    showToast("Error creating project: " + err.message, "error");
  }
}

async function switchProject(projectId) {
  try {
    const res = await fetch(`${API_BASE}/projects/${projectId}`);
    state.currentProject = await res.json();
    state.currentManuscriptId = state.currentProject.manuscript_id;

    currentCitationStyle.textContent = (state.currentProject.citation_style || "APA") + " 7th";

    // Populate Settings Tab fields
    document.getElementById("setting-title").value = state.currentProject.title || "";
    document.getElementById("setting-topic").value = state.currentProject.topic || "";
    document.getElementById("setting-problem").value = state.currentProject.research_problem || "";
    document.getElementById("setting-questions").value = state.currentProject.research_questions || "";
    document.getElementById("setting-objectives").value = state.currentProject.objectives || "";
    document.getElementById("setting-discipline").value = state.currentProject.academic_discipline || "Computer Science";
    document.getElementById("setting-venue").value = state.currentProject.target_venue || "";
    document.getElementById("setting-citation-style").value = state.currentProject.citation_style || "APA";
    document.getElementById("setting-word-target").value = state.currentProject.word_count_target || 5000;

    await loadManuscript();
    await loadSources();
    await loadEvidence();
  } catch (err) {
    showToast("Error loading project: " + err.message, "error");
  }
}

async function saveProjectSettings() {
  if (!state.currentProject) return;
  try {
    const res = await fetch(`${API_BASE}/projects/${state.currentProject.id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: document.getElementById("setting-title").value,
        topic: document.getElementById("setting-topic").value,
        research_problem: document.getElementById("setting-problem").value,
        research_questions: document.getElementById("setting-questions").value,
        objectives: document.getElementById("setting-objectives").value,
        academic_discipline: document.getElementById("setting-discipline").value,
        target_venue: document.getElementById("setting-venue").value,
        citation_style: document.getElementById("setting-citation-style").value,
        word_count_target: parseInt(document.getElementById("setting-word-target").value) || 5000
      })
    });
    state.currentProject = await res.json();
    currentCitationStyle.textContent = (state.currentProject.citation_style || "APA") + " 7th";
    showToast("Project specifications updated", "success");
  } catch (err) {
    showToast("Error updating project: " + err.message, "error");
  }
}

// Manuscript & Sections
async function loadManuscript() {
  if (!state.currentManuscriptId) return;
  try {
    const res = await fetch(`${API_BASE}/manuscripts/${state.currentManuscriptId}`);
    const data = await res.json();
    state.sections = data.sections || [];

    renderSectionOutline();

    if (state.sections.length > 0) {
      const activeSec = state.sections.find(s => s.id === state.currentSectionId) || state.sections[0];
      selectSection(activeSec.id);
    }
    await loadGlobalVerificationAudit();
  } catch (err) {
    showToast("Error loading manuscript: " + err.message, "error");
  }
}

function renderSectionOutline() {
  sectionOutlineList.innerHTML = "";
  state.sections.forEach(sec => {
    const item = document.createElement("div");
    item.className = `outline-item ${sec.id === state.currentSectionId ? "active" : ""}`;
    item.dataset.id = sec.id;

    const dotClass = sec.content ? (sec.claims_count > 0 ? "has-claims" : "needs-work") : "";
    item.innerHTML = `
      <span>${sec.title}</span>
      <span class="outline-status-dot ${dotClass}" title="${sec.status}"></span>
    `;

    item.addEventListener("click", () => selectSection(sec.id));
    sectionOutlineList.appendChild(item);
  });
}

function selectSection(sectionId) {
  state.currentSectionId = sectionId;
  const sec = state.sections.find(s => s.id === sectionId);
  if (!sec) return;

  renderSectionOutline();

  editorSectionType.textContent = sec.section_type.replace("_", " ");
  editorSectionTitle.textContent = sec.title;
  sectionTextarea.value = sec.content || "";

  loadSectionClaims(sectionId);
}

async function saveCurrentSection() {
  if (!state.currentSectionId || !state.currentManuscriptId) return;
  try {
    const res = await fetch(`${API_BASE}/manuscripts/${state.currentManuscriptId}/sections/${state.currentSectionId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        content: sectionTextarea.value
      })
    });
    const updated = await res.json();
    const idx = state.sections.findIndex(s => s.id === state.currentSectionId);
    if (idx !== -1) state.sections[idx] = updated;
    showToast("Section saved", "success");
    renderSectionOutline();
  } catch (err) {
    showToast("Error saving section: " + err.message, "error");
  }
}

// Grounded Synthesis Generation
function openGenerateModal() {
  const sec = state.sections.find(s => s.id === state.currentSectionId);
  if (!sec) return;

  document.getElementById("gen-instructions").value = sec.instructions || "";
  document.getElementById("gen-word-limit").value = sec.word_limit || 500;

  // Checkboxes for available sources (FR-06.8, FR-10.5)
  const container = document.getElementById("gen-sources-checklist") || document.getElementById("gen-source-checkboxes");
  if (container) {
    container.innerHTML = "";
    if (state.sources.length === 0) {
      container.innerHTML = `<span class="muted-note" style="font-size:0.8rem; color:#94A3B8;">No sources in library yet. Add sources to enable grounded in-text citations.</span>`;
    } else {
      state.sources.forEach(s => {
        const label = document.createElement("label");
        label.className = "checkbox-label";
        label.style.display = "flex";
        label.style.alignItems = "center";
        label.style.gap = "6px";
        label.style.margin = "4px 0";
        label.style.fontSize = "0.85rem";
        label.innerHTML = `
          <input type="checkbox" name="gen-sources" value="${s.id}" checked>
          <span><strong>[${s.citation_key || "Ref"}]</strong> ${escapeHtml(s.title)} (${s.year || "n.d."})</span>
        `;
        container.appendChild(label);
      });
    }
  }

  openModal("modal-generate");
}

async function runSectionGeneration() {
  const sec = state.sections.find(s => s.id === state.currentSectionId);
  if (!sec) return;

  const instructions = document.getElementById("gen-instructions").value;
  const wordLimit = parseInt(document.getElementById("gen-word-limit").value) || 500;
  const expData = document.getElementById("gen-exp-data").value;

  const checkedSources = Array.from(document.querySelectorAll("input[name='gen-sources']:checked")).map(cb => cb.value);

  closeModal("modal-generate");
  showToast("Synthesizing grounded section with citation verification...", "info");

  try {
    const res = await fetch(`${API_BASE}/manuscripts/${state.currentManuscriptId}/sections/${state.currentSectionId}/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        section_type: sec.section_type,
        title: sec.title,
        instructions: instructions,
        word_limit: wordLimit,
        source_ids: checkedSources,
        experimental_data: expData
      })
    });
    const updated = await res.json();
    sectionTextarea.value = updated.content;
    const idx = state.sections.findIndex(s => s.id === state.currentSectionId);
    if (idx !== -1) state.sections[idx] = updated;

    renderSectionOutline();
    await loadSectionClaims(sec.id);
    await loadGlobalVerificationAudit();
    showToast("Section synthesized & verified with source citations", "success");
  } catch (err) {
    showToast("Generation failed: " + err.message, "error");
  }
}

// Citation & Claim Verification
async function runSectionVerification() {
  if (!state.currentSectionId) return;
  showToast("Evaluating claims and verifying citations...", "info");
  try {
    const res = await fetch(`${API_BASE}/verification/verify-section/${state.currentSectionId}`, {
      method: "POST"
    });
    const report = await res.json();
    renderClaimsDrawer(report.claims);
    await loadGlobalVerificationAudit();
    showToast(`Verification complete. Accuracy: ${report.accuracy_score}%`, "success");
  } catch (err) {
    showToast("Verification failed: " + err.message, "error");
  }
}

async function loadSectionClaims(sectionId) {
  try {
    const res = await fetch(`${API_BASE}/verification/report/${state.currentManuscriptId}?section_id=${sectionId}`);
    const report = await res.json();
    renderClaimsDrawer(report.claims);
  } catch (err) {
    console.error("Failed to load claims:", err);
  }
}

function renderClaimsDrawer(claims) {
  state.claims = claims || [];
  drawerClaimsCount.textContent = `${state.claims.length} Claims`;
  claimsListContainer.innerHTML = "";

  if (state.claims.length === 0) {
    claimsListContainer.innerHTML = `
      <div class="empty-state-card">
        <p>No claims extracted yet. Click 'Verify Citations' or 'Generate' to analyze evidence alignment.</p>
      </div>
    `;
    return;
  }

  state.claims.forEach(c => {
    const card = document.createElement("div");
    card.className = `claim-card status-${c.status}`;

    let statusDisplay = c.status.replace("_", " ");
    let statusClass = "unverified";
    if (c.status === "supported") statusClass = "supported";
    if (c.status === "partially_supported") statusClass = "partially";
    if (c.status === "contradicted") statusClass = "contradicted";
    if (c.status === "citation_missing") statusClass = "missing";

    let evidenceHtml = "";
    if (c.citations && c.citations.length > 0) {
      const cite = c.citations[0];
      const srcTitle = cite.source_title || cite.in_text_citation || "Cited Source";
      const passage = cite.evidence_passage || "Direct passage verified.";
      const pageInfo = cite.page_number ? ` (p. ${cite.page_number})` : "";
      evidenceHtml = `
        <div class="evidence-inspection-box">
          <div class="evidence-source-tag">
            <span>[${cite.citation_key || "Ref"}] ${srcTitle}</span>
            <span>${pageInfo}</span>
          </div>
          <div class="evidence-quote-snippet">"${passage}"</div>
        </div>
      `;
    }

    card.innerHTML = `
      <div class="claim-card-header">
        <span class="status-chip ${statusClass}">${statusDisplay}</span>
        <span class="claim-score">Conf: ${(c.confidence * 100).toFixed(0)}%</span>
      </div>
      <div class="claim-sentence-text">"${c.claim_text}"</div>
      ${evidenceHtml}
      <div class="claim-explanation-note">${c.explanation || ""}</div>
    `;

    claimsListContainer.appendChild(card);
  });
}

async function loadGlobalVerificationAudit() {
  if (!state.currentManuscriptId) return;
  try {
    const res = await fetch(`${API_BASE}/verification/report/${state.currentManuscriptId}`);
    const report = await res.json();
    globalAccuracyScore.textContent = `${report.accuracy_score}%`;
    countSupported.textContent = report.supported_count;
    countPartial.textContent = report.partially_supported_count;
    countUnverified.textContent = report.unverified_count;
    countMissing.textContent = report.citation_missing_count;

    // FR-09: 4-Level Verification Audit Grid
    if (report.four_level_audit) {
      const el1 = document.getElementById("audit-level-1-count");
      const el2 = document.getElementById("audit-level-2-count");
      const el3 = document.getElementById("audit-level-3-count");
      const el4 = document.getElementById("audit-level-4-count");
      if (el1) el1.textContent = report.four_level_audit.level_1_citations_count;
      if (el2) el2.textContent = report.four_level_audit.level_2_metadata_verified_count;
      if (el3) el3.textContent = report.four_level_audit.level_3_evidence_identified_count;
      if (el4) el4.textContent = report.four_level_audit.level_4_claims_verified_count;
    }

    const alertsEl = document.getElementById("audit-integrity-alerts");
    if (alertsEl) {
      alertsEl.innerHTML = "";
      const integrity = report.integrity_audit || {};
      const missingRefs = integrity.missing_references || [];
      const uncitedBib = integrity.uncited_sources || [];
      const unresolved = integrity.unresolved_placeholders || [];
      const criticals = report.critical_errors || [];

      if (criticals.length > 0) {
        alertsEl.innerHTML += `
          <div style="padding: 8px; background: rgba(239, 68, 68, 0.2); border: 1px solid #EF4444; border-radius: 4px; color: #FCA5A5; margin-top: 6px;">
            <strong>Critical Citation Errors (${criticals.length}):</strong> ${criticals.map(e => escapeHtml(e)).join(" • ")}
          </div>
        `;
      } else if (missingRefs.length === 0 && unresolved.length === 0) {
        alertsEl.innerHTML = `
          <div style="color: #10B981; font-weight: 500;">
            ✓ All citations resolve to verified project records. Manuscript is export-ready.
          </div>
        `;
      }
      if (uncitedBib.length > 0) {
        alertsEl.innerHTML += `
          <div style="color: #94A3B8; font-size: 0.78rem; margin-top: 4px;">
            Note: ${uncitedBib.length} library sources are currently uncited in manuscript text and will be omitted from the exported bibliography (FR-08.4).
          </div>
        `;
      }
    }
  } catch (err) {
    console.error("Global audit fetch failed:", err);
  }
}

// Sources & Literature Discovery (FR-01, FR-02, FR-03, FR-10)
async function loadSources() {
  if (!state.currentProject) return;
  try {
    const res = await fetch(`${API_BASE}/sources?project_id=${state.currentProject.id}`);
    state.sources = await res.json();
    sourcesCountBadge.textContent = state.sources.length;

    sourcesTableBody.innerHTML = "";
    if (state.sources.length === 0) {
      sourcesTableBody.innerHTML = `<tr><td colspan="7" style="text-align:center; color:#64748B;">No sources added. Use the search bar above to discover literature or click 'Upload Reference PDFs'.</td></tr>`;
      return;
    }

    state.sources.forEach(s => {
      const tr = document.createElement("tr");

      // FR-04: PDF & OCR status
      let pdfStatusHtml = "";
      if (s.document) {
        const isOcrReq = s.document.text_content && s.document.text_content.includes("OCR processing required");
        if (isOcrReq) {
          pdfStatusHtml = `<span class="status-chip partially" title="${escapeAttr(s.document.text_content)}">⚠️ OCR Required</span>`;
        } else {
          pdfStatusHtml = `<span class="status-chip supported" title="${s.document.character_count} chars extracted">✅ ${s.document.page_count} p (${s.evidence_count || 0} ev)</span>`;
        }
      } else {
        pdfStatusHtml = `<button class="btn btn-secondary btn-sm" onclick="openPdfUploadModal('${s.id}', '${escapeAttr(s.title)}')">Upload PDF</button>`;
      }

      // FR-03: Metadata verification chip
      let metaChip = "";
      const vStatus = s.metadata_verification_status || "unverified";
      if (vStatus === "verified") {
        metaChip = `<span class="status-chip supported">Verified</span>`;
      } else if (vStatus === "flagged_mismatch") {
        metaChip = `<span class="status-chip partially" title="${escapeAttr(s.mismatch_notes || 'Metadata mismatch detected')}">Flagged Mismatch</span>`;
      } else {
        metaChip = `<span class="status-chip unverified">Unverified</span>`;
      }

      // DOI link if available
      const doiHtml = s.doi ? `<div style="font-size:0.75rem;"><a href="https://doi.org/${encodeURIComponent(s.doi)}" target="_blank" style="color:#60A5FA;">doi:${s.doi}</a></div>` : "";

      tr.innerHTML = `
        <td><strong style="color:#60A5FA;">[${escapeHtml(s.citation_key || "Ref")}]</strong></td>
        <td>
          <div style="font-weight:600;">${escapeHtml(s.title)}</div>
          <div style="font-size:0.75rem; color:#64748B;">${escapeHtml(s.venue || "Academic Publication")}</div>
          ${doiHtml}
        </td>
        <td style="font-size:0.8rem; color:#94A3B8;">${escapeHtml(s.authors || "Unknown")}</td>
        <td>${s.year || "n.d."}</td>
        <td>${metaChip}</td>
        <td>${pdfStatusHtml}</td>
        <td style="white-space: nowrap;">
          <button class="btn-link" style="color:#38BDF8; margin-right: 8px;" onclick="openEditSourceModal('${s.id}')">Edit</button>
          <button class="btn-link" style="color:#EF4444;" onclick="deleteSource('${s.id}')">Remove</button>
        </td>
      `;
      sourcesTableBody.appendChild(tr);
    });
  } catch (err) {
    showToast("Error loading sources: " + err.message, "error");
  }
}

async function runScholarlySearch() {
  const query = document.getElementById("scholarly-search-input").value.trim();
  if (!query) return;

  showToast(`Searching OpenAlex & CrossRef for '${query}'...`, "info");
  searchResultsSection.style.display = "block";
  searchResultsGrid.innerHTML = "<p class='muted-note'>Retrieving academic publications and abstracts...</p>";

  try {
    const res = await fetch(`${API_BASE}/sources/search`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: query, limit: 6 })
    });
    const data = await res.json();
    searchResultsGrid.innerHTML = "";

    if (data.results.length === 0) {
      searchResultsGrid.innerHTML = "<p class='muted-note'>No publications matched your search.</p>";
      return;
    }

    data.results.forEach(item => {
      const card = document.createElement("div");
      card.className = "search-result-card";
      card.innerHTML = `
        <div class="result-card-info">
          <div class="result-title">${item.title}</div>
          <div class="result-meta">${item.authors || "Unknown Authors"} • ${item.year || "n.d."} • ${item.venue || "Academic Venue"}</div>
          <div class="result-abstract">${item.abstract ? item.abstract.substring(0, 240) + "..." : "No abstract provided."}</div>
        </div>
        <div>
          <button class="btn btn-primary btn-sm" onclick='importSearchResult(${JSON.stringify(item).replace(/'/g, "&#39;")})'>
            + Add to Library
          </button>
        </div>
      `;
      searchResultsGrid.appendChild(card);
    });
  } catch (err) {
    showToast("Search failed: " + err.message, "error");
  }
}

window.importSearchResult = async function(item) {
  try {
    const res = await fetch(`${API_BASE}/sources`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        project_id: state.currentProject.id,
        title: item.title,
        authors: item.authors,
        year: item.year,
        venue: item.venue,
        doi: item.doi,
        url: item.url,
        abstract: item.abstract,
        citation_key: item.citation_key
      })
    });
    await res.json();
    showToast(`Added [${item.citation_key}] to library`, "success");
    await loadSources();
    await loadEvidence();
  } catch (err) {
    showToast("Error adding source: " + err.message, "error");
  }
};

window.deleteSource = async function(sourceId) {
  if (!confirm("Remove this source and its associated extracted evidence?")) return;
  try {
    await fetch(`${API_BASE}/sources/${sourceId}`, { method: "DELETE" });
    showToast("Source removed", "success");
    await loadSources();
    await loadEvidence();
  } catch (err) {
    showToast("Error deleting source: " + err.message, "error");
  }
};

function promptAddManualSource() {
  const title = prompt("Paper Title:");
  if (!title) return;
  const authors = prompt("Authors (e.g. Smith, J., Doe, A.):");
  const year = parseInt(prompt("Year (e.g. 2023):")) || 2023;
  const venue = prompt("Venue (Journal/Conference):");

  fetch(`${API_BASE}/sources`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      project_id: state.currentProject.id,
      title: title,
      authors: authors,
      year: year,
      venue: venue
    })
  }).then(() => {
    showToast("Manual citation added", "success");
    loadSources();
  });
}

// PDF Ingestion
window.openPdfUploadModal = function(sourceId, sourceTitle) {
  state.selectedUploadSourceId = sourceId;
  document.getElementById("upload-source-title").textContent = `Target Source: "${sourceTitle}"`;
  document.getElementById("upload-status-indicator").style.display = "none";
  openModal("modal-upload-pdf");
};

async function handleFileUpload(file) {
  if (!state.selectedUploadSourceId) return;
  const formData = new FormData();
  formData.append("file", file);

  document.getElementById("upload-status-indicator").style.display = "block";
  try {
    const res = await fetch(`${API_BASE}/sources/${state.selectedUploadSourceId}/upload-pdf`, {
      method: "POST",
      body: formData
    });
    if (!res.ok) throw new Error("Upload processing error");
    const updatedSource = await res.json();

    closeModal("modal-upload-pdf");
    showToast(`PDF processed! Extracted ${updatedSource.document.page_count} pages and structured evidence.`, "success");
    await loadSources();
    await loadEvidence();
  } catch (err) {
    showToast("PDF Upload failed: " + err.message, "error");
  } finally {
    document.getElementById("upload-status-indicator").style.display = "none";
  }
}

// Evidence Passages Browser
async function loadEvidence(category = "") {
  if (!state.currentProject) return;
  try {
    let url = `${API_BASE}/evidence?project_id=${state.currentProject.id}`;
    if (category) url += `&category=${category}`;

    const res = await fetch(url);
    state.evidence = await res.json();
    evidenceCountBadge.textContent = state.evidence.length;
    evidenceStatsText.textContent = `${state.evidence.length} evidence passages cataloged`;

    evidenceCardsContainer.innerHTML = "";
    if (state.evidence.length === 0) {
      evidenceCardsContainer.innerHTML = `<div class="empty-state-card"><p>No evidence passages found. Upload a research PDF or import literature abstracts to populate evidence.</p></div>`;
      return;
    }

    state.evidence.forEach(ev => {
      const card = document.createElement("div");
      card.className = "evidence-card";
      card.innerHTML = `
        <div class="evidence-card-category">${ev.category} • Conf: ${(ev.confidence * 100).toFixed(0)}%</div>
        <div class="evidence-card-text">"${ev.passage_text}"</div>
        <div class="evidence-card-footer">
          <span>[${ev.citation_key || "Ref"}] ${ev.source_title ? ev.source_title.substring(0, 35) + "..." : "Source"}</span>
          <span>Page ${ev.page_number || 1} • ${ev.section_name || "General"}</span>
        </div>
      `;
      evidenceCardsContainer.appendChild(card);
    });
  } catch (err) {
    console.error("Failed to load evidence:", err);
  }
}

// Prose Refinement (FR-10)
function openPolishModal() {
  const currentText = sectionTextarea.value.trim();
  if (!currentText) {
    showToast("Editor is empty. Write or generate text before refining.", "error");
    return;
  }
  state.polishOriginalText = currentText;
  openModal("modal-polish");
  runProsePolish();
}

async function runProsePolish() {
  const activeModePill = document.querySelector("#polish-mode-options .pill.active");
  const mode = activeModePill ? activeModePill.dataset.mode : "clarity";

  document.getElementById("polish-diff-content").innerHTML = "<em>Refining academic prose while preserving citation keys...</em>";
  try {
    const res = await fetch(`${API_BASE}/writing/polish`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        text: state.polishOriginalText,
        mode: mode,
        preserve_citations: true
      })
    });
    const data = await res.json();
    state.polishRevisedText = data.revised_text;

    let diffHtml = "";
    data.diff_segments.forEach(seg => {
      if (seg.type === "added") diffHtml += `<span class="diff-added">${escapeHtml(seg.text)}</span>`;
      else if (seg.type === "removed") diffHtml += `<span class="diff-removed">${escapeHtml(seg.text)}</span>`;
      else diffHtml += `<span>${escapeHtml(seg.text)}</span>`;
    });

    document.getElementById("polish-diff-content").innerHTML = diffHtml;
    document.getElementById("polish-summary-text").textContent = `Dimension: ${data.mode.toUpperCase()} • ${data.changes_summary}`;
  } catch (err) {
    showToast("Prose polish failed: " + err.message, "error");
  }
}

function acceptPolishedText() {
  if (state.polishRevisedText) {
    sectionTextarea.value = state.polishRevisedText;
    saveCurrentSection();
    showToast("Refined prose applied to manuscript", "success");
  }
  closeModal("modal-polish");
}

// Document Export (FR-11, FR-26)
async function runExport() {
  const formatEl = document.getElementById("export-format-select");
  const format = formatEl ? formatEl.value : "docx";
  const styleEl = document.getElementById("export-style-select") || document.getElementById("setting-citation-style");
  const style = styleEl ? styleEl.value : (state.currentProject?.citation_style || "IEEE");
  const appendixEl = document.getElementById("export-include-appendix") || document.getElementById("export-verification-appendix");
  const appendix = appendixEl ? appendixEl.checked : true;
  const blockEl = document.getElementById("export-block-critical");
  const blockCritical = blockEl ? blockEl.checked : true;

  const warningBox = document.getElementById("export-integrity-warning");
  if (warningBox) warningBox.style.display = "none";

  showToast(`Validating integrity & generating ${format.toUpperCase()} (${style})...`, "info");

  try {
    const res = await fetch(`${API_BASE}/export`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        manuscript_id: state.currentManuscriptId,
        export_format: format,
        citation_style: style,
        include_verification_appendix: appendix,
        block_on_critical_errors: blockCritical
      })
    });

    const data = await res.json();

    if (!res.ok) {
      if (warningBox) {
        warningBox.style.display = "block";
        warningBox.innerHTML = `<strong>Export Blocked (FR-11.6):</strong> ${escapeHtml(data.detail || "Critical citation integrity errors remain unresolved.")}`;
      }
      showToast("Export blocked: " + (data.detail || "Citation integrity errors"), "error");
      return;
    }

    closeModal("modal-export");

    // Trigger browser download
    const link = document.createElement("a");
    link.href = data.download_url;
    link.download = data.filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    showToast(`Manuscript exported successfully: ${data.filename}`, "success");
  } catch (err) {
    showToast("Export failed: " + err.message, "error");
  }
}

// Batch PDF Upload Workflow (FR-02)
async function handleBatchPdfUpload() {
  const fileInput = document.getElementById("batch-pdf-input");
  const statusList = document.getElementById("batch-upload-status-list");
  if (!fileInput || !fileInput.files.length) {
    showToast("Please select one or more PDF files to upload.", "error");
    return;
  }

  const formData = new FormData();
  formData.append("project_id", state.currentProject.id);
  for (let i = 0; i < fileInput.files.length; i++) {
    formData.append("files", fileInput.files[i]);
  }

  statusList.innerHTML = `<div style="font-size:0.85rem; color:#60A5FA;">Processing ${fileInput.files.length} PDFs (extracting metadata, page numbers, evidence)...</div>`;

  try {
    const res = await fetch(`${API_BASE}/sources/upload-batch`, {
      method: "POST",
      body: formData
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Batch upload failed");

    statusList.innerHTML = "";
    data.results.forEach(item => {
      const div = document.createElement("div");
      div.style.padding = "8px";
      div.style.borderRadius = "4px";
      div.style.fontSize = "0.8rem";

      if (item.status === "success") {
        div.style.background = "rgba(16, 185, 129, 0.15)";
        div.style.border = "1px solid #10B981";
        div.style.color = "#A7F3D0";
        div.innerHTML = `✓ <strong>${escapeHtml(item.filename)}</strong>: Extracted ${item.pages_extracted} pages, ${item.evidence_extracted} evidence items. [${item.citation_key || "Ref"}]`;
      } else if (item.status === "duplicate") {
        div.style.background = "rgba(245, 158, 11, 0.15)";
        div.style.border = "1px solid #F59E0B";
        div.style.color = "#FDE68A";
        div.innerHTML = `⚠️ <strong>${escapeHtml(item.filename)}</strong>: ${escapeHtml(item.message || "Duplicate detected")}`;
      } else {
        div.style.background = "rgba(239, 68, 68, 0.15)";
        div.style.border = "1px solid #EF4444";
        div.style.color = "#FECACA";
        div.innerHTML = `✕ <strong>${escapeHtml(item.filename)}</strong>: ${escapeHtml(item.message || "Processing failed")}`;
      }
      statusList.appendChild(div);
    });

    showToast(`Processed ${data.total_processed} files (${data.successful_count} succeeded, ${data.duplicate_count} duplicates)`, "success");
    await loadSources();
    await loadEvidence();
  } catch (err) {
    statusList.innerHTML = `<div style="color:#EF4444; font-size:0.85rem;">Upload failed: ${escapeHtml(err.message)}</div>`;
    showToast("Batch upload error: " + err.message, "error");
  }
}

// Source Metadata Review & Editing (FR-03.5, FR-10.2)
function openAddSourceModal() {
  document.getElementById("edit-source-id").value = "";
  document.getElementById("edit-source-title").value = "";
  document.getElementById("edit-source-authors").value = "";
  document.getElementById("edit-source-year").value = new Date().getFullYear();
  document.getElementById("edit-source-doi").value = "";
  document.getElementById("edit-source-venue").value = "";
  document.getElementById("edit-source-status").value = "unverified";
  const mismatchBox = document.getElementById("edit-source-mismatch-alerts");
  if (mismatchBox) mismatchBox.style.display = "none";
  openModal("modal-edit-source");
}

window.openEditSourceModal = function(sourceId) {
  const s = state.sources.find(x => x.id === sourceId);
  if (!s) return;

  document.getElementById("edit-source-id").value = s.id;
  document.getElementById("edit-source-title").value = s.title || "";
  document.getElementById("edit-source-authors").value = s.authors || "";
  document.getElementById("edit-source-year").value = s.year || "";
  document.getElementById("edit-source-doi").value = s.doi || "";
  document.getElementById("edit-source-venue").value = s.venue || "";
  document.getElementById("edit-source-status").value = s.metadata_verification_status || "unverified";

  const mismatchBox = document.getElementById("edit-source-mismatch-alerts");
  if (mismatchBox) {
    if (s.mismatch_notes) {
      mismatchBox.style.display = "block";
      mismatchBox.innerHTML = `<strong>Bibliographic Discrepancy Flagged:</strong> ${escapeHtml(s.mismatch_notes)}`;
    } else {
      mismatchBox.style.display = "none";
    }
  }

  openModal("modal-edit-source");
};

async function saveSourceMetadata() {
  const sourceId = document.getElementById("edit-source-id").value;
  const payload = {
    title: document.getElementById("edit-source-title").value.trim(),
    authors: document.getElementById("edit-source-authors").value.trim(),
    year: parseInt(document.getElementById("edit-source-year").value) || null,
    doi: document.getElementById("edit-source-doi").value.trim() || null,
    venue: document.getElementById("edit-source-venue").value.trim() || null,
    metadata_verification_status: document.getElementById("edit-source-status").value
  };

  if (!payload.title || !payload.authors) {
    showToast("Title and Authors are required.", "error");
    return;
  }

  try {
    if (sourceId) {
      // Update existing
      const res = await fetch(`${API_BASE}/sources/${sourceId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      if (!res.ok) throw new Error("Failed to update source metadata");
      showToast("Bibliographic metadata saved & verified.", "success");
    } else {
      // Create new manual record
      payload.project_id = state.currentProject.id;
      const res = await fetch(`${API_BASE}/sources`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      if (!res.ok) throw new Error("Failed to create source");
      showToast("Source record created.", "success");
    }

    closeModal("modal-edit-source");
    await loadSources();
    await loadGlobalVerificationAudit();
  } catch (err) {
    showToast("Save failed: " + err.message, "error");
  }
}

async function verifySourceMetadataOnline() {
  const sourceId = document.getElementById("edit-source-id").value;
  if (!sourceId) {
    showToast("Save record first or provide a DOI/Title to verify online.", "info");
    return;
  }

  showToast("Comparing metadata with OpenAlex and Crossref records...", "info");
  try {
    const res = await fetch(`${API_BASE}/sources/${sourceId}/verify-metadata`);
    const data = await res.json();

    const mismatchBox = document.getElementById("edit-source-mismatch-alerts");
    if (data.mismatches && data.mismatches.length > 0) {
      if (mismatchBox) {
        mismatchBox.style.display = "block";
        mismatchBox.innerHTML = `<strong>Mismatches Detected (${data.mismatches.length}):</strong><br>${data.mismatches.map(m => escapeHtml(m)).join("<br>")}`;
      }
      document.getElementById("edit-source-status").value = "flagged_mismatch";
      showToast("Metadata discrepancies flagged against Crossref/OpenAlex", "warning");
    } else if (data.verified) {
      if (mismatchBox) mismatchBox.style.display = "none";
      document.getElementById("edit-source-status").value = "verified";
      showToast("Bibliographic metadata verified successfully against scholarly records!", "success");
    } else {
      showToast(data.message || "Online record lookup did not yield exact matches.", "info");
    }
  } catch (err) {
    showToast("Online verification error: " + err.message, "error");
  }
}

// Utilities & Modal Helpers
function openModal(id) {
  const el = document.getElementById(id);
  if (el) el.classList.add("active");
}

function closeModal(id) {
  const el = document.getElementById(id);
  if (el) el.classList.remove("active");
}

function showToast(message, type = "info") {
  const container = document.getElementById("toast-container");
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.textContent = message;
  container.appendChild(toast);
  setTimeout(() => {
    toast.remove();
  }, 4000);
}

function escapeHtml(text) {
  const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
  return text.replace(/[&<>"']/g, m => map[m]);
}

function escapeAttr(text) {
  return (text || "").replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

// --- ResearchScribe v3.0 Core Services Integration ---

async function loadRepositoryDashboard() {
  if (!state.currentProject) return;
  const repoId = state.currentProject.repository_id;
  const repoUrlText = document.getElementById("repo-url-text");
  const repoShaBadge = document.getElementById("repo-sha-badge");

  if (!repoId) {
    if (repoUrlText) repoUrlText.textContent = state.currentProject.repository_url || "No GitHub repository linked";
    return;
  }

  try {
    const res = await fetch(`${API_BASE}/repositories/${repoId}/snapshot`);
    if (!res.ok) return;
    const snap = await res.json();

    if (repoUrlText) repoUrlText.textContent = state.currentProject.repository_url;
    if (repoShaBadge) repoShaBadge.textContent = `Commit: ${snap.commit_sha} (${snap.branch_or_tag})`;

    // File inventory
    const tbody = document.getElementById("repo-files-table-body");
    const badge = document.getElementById("repo-files-badge");
    if (badge) badge.textContent = snap.files.length;
    if (tbody) {
      tbody.innerHTML = "";
      snap.files.forEach(f => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td><code style="color: #60A5FA;">${escapeHtml(f.path)}</code></td>
          <td><span class="category-pill">${f.file_type || 'file'}</span></td>
          <td>${f.language || 'Plain'}</td>
          <td><span class="status-chip supported">${f.relevance_category || 'core'}</span></td>
          <td>${(f.size_bytes / 1024).toFixed(1)} KB</td>
        `;
        tbody.appendChild(tr);
      });
    }

    // Architecture components
    const compRes = await fetch(`${API_BASE}/repositories/${repoId}/architecture`);
    if (compRes.ok) {
      const components = await compRes.json();
      const compList = document.getElementById("architecture-components-list");
      const compBadge = document.getElementById("components-count-badge");
      if (compBadge) compBadge.textContent = components.length;
      if (compList) {
        compList.innerHTML = "";
        components.forEach(c => {
          const div = document.createElement("div");
          div.className = "component-item";
          div.innerHTML = `
            <div class="component-item-header">
              <span>${escapeHtml(c.name)}</span>
              <span class="status-chip partially">${escapeHtml(c.component_type)}</span>
            </div>
            <div class="component-item-desc">${escapeHtml(c.description || 'Module pipeline element')}</div>
            <div style="font-size: 0.72rem; color: #64748B; margin-top: 4px;"><code>${escapeHtml(c.file_path)}:${c.start_line || 1}</code></div>
          `;
          compList.appendChild(div);
        });
      }
    }

    // Methodology
    const methRes = await fetch(`${API_BASE}/repositories/${repoId}/methodology`);
    if (methRes.ok) {
      const meth = await methRes.json();
      document.getElementById("meth-problem-text").textContent = meth.problem_description || "Not specified";
      document.getElementById("meth-algo-text").textContent = meth.algorithm_description || "Not specified";
      document.getElementById("meth-equations-box").textContent = meth.equations || "No equations extracted";
      document.getElementById("meth-pseudo-box").textContent = meth.pseudocode || "No pseudocode extracted";
    }
  } catch (err) {
    console.error("Repository dashboard load error:", err);
  }
}

async function loadExperimentalMetrics() {
  if (!state.currentProject || !state.currentProject.repository_id) return;
  const repoId = state.currentProject.repository_id;

  try {
    // Load extracted metrics
    const res = await fetch(`${API_BASE}/repositories/${repoId}/experimental-results`);
    if (res.ok) {
      const results = await res.json();
      const badge = document.getElementById("metrics-count-badge");
      if (badge) badge.textContent = results.length;
      const tbody = document.getElementById("metrics-table-body");
      if (tbody) {
        tbody.innerHTML = "";
        results.forEach(r => {
          const tr = document.createElement("tr");
          tr.innerHTML = `
            <td><strong>${escapeHtml(r.model_name || 'Proposed')}</strong></td>
            <td>${escapeHtml(r.dataset_name || 'Benchmark')}</td>
            <td><span class="category-pill">${escapeHtml(r.split_name || 'test')}</span></td>
            <td>${escapeHtml(r.metric_name)}</td>
            <td><strong style="color: #10B981;">${r.metric_value}${r.metric_unit || ''}</strong></td>
            <td><code>${r.random_seed || '42'}</code></td>
            <td><code style="color: #94A3B8;">${escapeHtml(r.source_location || 'Artifact')}</code></td>
            <td><span class="status-chip supported">${escapeHtml(r.verification_status)}</span></td>
          `;
          tbody.appendChild(tr);
        });
      }
    }

    // Load Evidence Gap Report
    const gapRes = await fetch(`${API_BASE}/repositories/${repoId}/evidence-gap`);
    if (gapRes.ok) {
      const gap = await gapRes.json();
      const scoreBadge = document.getElementById("gap-score-badge");
      if (scoreBadge) scoreBadge.textContent = `${Math.round(gap.sufficiency_score * 100)}% Evidence Sufficiency`;

      const list = document.getElementById("gap-recommendations-list");
      if (list) {
        list.innerHTML = "";
        gap.recommendations.forEach(rec => {
          const p = document.createElement("p");
          p.style.fontSize = "0.82rem";
          p.style.color = "#CBD5E1";
          p.style.margin = "4px 0";
          p.innerHTML = `&#10003; ${escapeHtml(rec)}`;
          list.appendChild(p);
        });
        if (gap.missing_baselines.length > 0) {
          const w = document.createElement("p");
          w.style.fontSize = "0.82rem";
          w.style.color = "#F59E0B";
          w.innerHTML = `&#9888; ${gap.missing_baselines.join(', ')}`;
          list.appendChild(w);
        }
      }
    }
  } catch (err) {
    console.error("Metrics load error:", err);
  }
}

async function loadGuidedCheckpoints() {
  if (!state.currentProject) return;
  const container = document.getElementById("checkpoints-timeline-container");
  if (!container) return;

  try {
    const res = await fetch(`${API_BASE}/workflow/checkpoints/${state.currentProject.id}`);
    if (!res.ok) return;
    const checkpoints = await res.json();

    container.innerHTML = "";
    checkpoints.forEach((cp, idx) => {
      const card = document.createElement("div");
      card.className = "checkpoint-card";
      const isApproved = cp.status === "approved";
      card.innerHTML = `
        <div class="checkpoint-top">
          <span class="checkpoint-num">STAGE 0${idx + 1}</span>
          <span class="status-chip ${isApproved ? 'supported' : 'partially'}">${escapeHtml(cp.status.toUpperCase())}</span>
        </div>
        <div>
          <h4 class="checkpoint-name">${escapeHtml(cp.name)}</h4>
          <p class="checkpoint-summary">${escapeHtml(cp.summary)}</p>
        </div>
        <div class="checkpoint-actions">
          <span style="font-size: 0.75rem; color: #94A3B8;">${cp.items_count} items analyzed</span>
          <button class="btn btn-sm ${isApproved ? 'btn-secondary' : 'btn-primary'}" onclick="approveCheckpoint('${cp.checkpoint}')">
            ${isApproved ? 'Approved &#10003;' : 'Approve Stage'}
          </button>
        </div>
      `;
      container.appendChild(card);
    });
  } catch (err) {
    console.error("Checkpoints load error:", err);
  }
}

async function approveCheckpoint(checkpointName) {
  if (!state.currentProject) return;
  try {
    const res = await fetch(`${API_BASE}/workflow/review-action/${state.currentProject.id}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        checkpoint_name: checkpointName,
        target_type: "checkpoint_stage",
        action_type: "approved",
        approved_value: "Researcher approved"
      })
    });
    if (res.ok) {
      showToast(`Checkpoint '${checkpointName}' approved.`, "success");
      await loadGuidedCheckpoints();
    }
  } catch (err) {
    showToast("Approval failed: " + err.message, "error");
  }
}

async function loadJournalCompliance() {
  if (!state.currentProject || !state.currentManuscriptId) return;
  const overallBadge = document.getElementById("compliance-overall-badge");
  const overallScore = document.getElementById("compliance-overall-score");
  const checksList = document.getElementById("compliance-checks-list");

  try {
    const res = await fetch(`${API_BASE}/journals/validate/${state.currentManuscriptId}`);
    if (!res.ok) return;
    const report = await res.json();

    if (overallScore) overallScore.textContent = `${report.compliance_score}%`;
    if (overallBadge) {
      overallBadge.textContent = report.overall_status.toUpperCase().replace('_', ' ');
      overallBadge.className = `status-chip ${report.overall_status === 'compliant' ? 'supported' : 'partially'}`;
    }

    if (checksList) {
      checksList.innerHTML = "";
      report.checks.forEach(c => {
        const item = document.createElement("div");
        item.className = `compliance-check-item ${c.status}`;
        item.innerHTML = `
          <div class="compliance-check-header">
            <span>${escapeHtml(c.check_type.replace('_', ' ').toUpperCase())}</span>
            <span class="status-chip ${c.status === 'passed' ? 'supported' : (c.status === 'warning' ? 'partially' : 'contradicted')}">${escapeHtml(c.status)}</span>
          </div>
          <div class="compliance-check-exp">${escapeHtml(c.explanation || '')}</div>
          ${c.suggested_correction ? `<div class="compliance-check-corr">&#9888; ${escapeHtml(c.suggested_correction)}</div>` : ''}
        `;
        checksList.appendChild(item);
      });
    }
  } catch (err) {
    console.error("Compliance load error:", err);
  }
}

async function uploadJournalTemplate() {
  const fileInput = document.getElementById("template-file-input");
  const statusMsg = document.getElementById("template-upload-status");
  if (!fileInput || !fileInput.files.length) {
    showToast("Please choose a DOCX template file first.", "error");
    return;
  }

  const formData = new FormData();
  formData.append("profile_id", "jp_global");
  formData.append("file", fileInput.files[0]);

  try {
    statusMsg.textContent = "Uploading and inspecting DOCX template styles...";
    const res = await fetch(`${API_BASE}/journals/templates/upload`, {
      method: "POST",
      body: formData
    });
    const data = await res.json();
    if (res.ok) {
      statusMsg.textContent = `Template uploaded: ${data.filename} (${data.styles_count} styles parsed)`;
      showToast("DOCX template parsed and active for document assembly.", "success");
    } else {
      statusMsg.textContent = "Upload failed: " + (data.detail || "Error");
    }
  } catch (err) {
    statusMsg.textContent = "Error: " + err.message;
  }
}

async function loadResearchGaps() {
  if (!state.currentProject) return;
  const container = document.getElementById("research-gaps-container");
  if (!container) return;

  try {
    const res = await fetch(`${API_BASE}/workflow/research-gaps/${state.currentProject.id}`);
    if (!res.ok) return;
    const gaps = await res.json();

    container.innerHTML = "";
    gaps.forEach(g => {
      const card = document.createElement("div");
      card.className = "component-item";
      card.style.marginBottom = "10px";
      card.innerHTML = `
        <div class="component-item-header">
          <span>${escapeHtml(g.dimension)}</span>
          <span class="status-chip supported">Research Gap</span>
        </div>
        <div style="font-size: 0.8rem; color: #E2E8F0; margin-top: 4px;"><strong>Identified Gap:</strong> ${escapeHtml(g.identified_gap)}</div>
        <div style="font-size: 0.78rem; color: #94A3B8; margin-top: 4px;"><strong>Rationale:</strong> ${escapeHtml(g.comparison_rationale)}</div>
        <div style="font-size: 0.78rem; color: #34D399; margin-top: 4px;"><strong>Proposed Contribution:</strong> ${escapeHtml(g.proposed_contribution)}</div>
      `;
      container.appendChild(card);
    });
  } catch (err) {
    console.error("Gaps load error:", err);
  }
}

async function triggerAutomaticRun() {
  if (!state.currentProject) return;
  const btn = document.getElementById("btn-auto-run");
  if (btn) btn.disabled = true;

  showToast("Executing 1-Click GitHub-to-Paper Pipeline (FR-13)...", "info");
  try {
    const res = await fetch(`${API_BASE}/workflow/run-automatic/${state.currentProject.id}?journal_name=IEEE%20Transactions`, {
      method: "POST"
    });
    const data = await res.json();
    if (res.ok) {
      showToast("Manuscript generated, verified, and formatted according to IEEE Transactions requirements!", "success");
      await loadManuscript();
      await loadRepositoryDashboard();
      await loadJournalCompliance();
    } else {
      showToast("Auto-run failed: " + (data.detail || "Error"), "error");
    }
  } catch (err) {
    showToast("Pipeline error: " + err.message, "error");
  } finally {
    if (btn) btn.disabled = false;
  }
}

