// DocuNext Main Application Controller
import { state } from "./state.js";
import { api } from "./api.js";
import { CanvasEditor } from "./canvas.js";

// DOM Elements
const els = {
  // Navigation
  stepBtns: document.querySelectorAll(".step-btn"),
  views: document.querySelectorAll(".view-panel"),
  btnNewProject: document.getElementById("btn-new-project"),
  btnSaveProject: document.getElementById("btn-save-project"),
  btnLoadProject: document.getElementById("btn-load-project"),
  btnLoadDemoFlat: document.getElementById("btn-demo-flat"),
  btnLoadDemoAcro: document.getElementById("btn-demo-acro"),
  demoRowCount: document.getElementById("demo-row-count"),

  // Step 1: Upload
  tplDropzone: document.getElementById("tpl-dropzone"),
  tplFileInput: document.getElementById("tpl-file-input"),
  tplFileInfo: document.getElementById("tpl-file-info"),
  tplName: document.getElementById("tpl-name"),
  tplMeta: document.getElementById("tpl-meta"),

  dataDropzone: document.getElementById("data-dropzone"),
  dataFileInput: document.getElementById("data-file-input"),
  dataFileInfo: document.getElementById("data-file-info"),
  dataName: document.getElementById("data-name"),
  dataMeta: document.getElementById("data-meta"),

  btnProceedStep2: document.getElementById("btn-proceed-step2"),
  mappingContainer: document.getElementById("mapping-container"),
  mappingTableBody: document.getElementById("mapping-table-body"),

  // Step 2: Editor
  columnChipsContainer: document.getElementById("column-chips"),
  placedFieldsList: document.getElementById("placed-fields-list"),
  btnClearFields: document.getElementById("btn-clear-fields"),
  canvasContainer: document.getElementById("canvas-container"),
  canvasStage: document.getElementById("canvas-stage"),
  canvasBgImg: document.getElementById("canvas-bg-img"),
  btnProceedStep3: document.getElementById("btn-proceed-step3"),

  // Canvas Toolbar
  zoomSelect: document.getElementById("zoom-select"),
  btnZoomIn: document.getElementById("btn-zoom-in"),
  btnZoomOut: document.getElementById("btn-zoom-out"),
  btnZoomFit: document.getElementById("btn-zoom-fit"),
  btnPrevRow: document.getElementById("btn-prev-row"),
  btnNextRow: document.getElementById("btn-next-row"),
  previewRowLabel: document.getElementById("preview-row-label"),
  btnWysiwygToggle: document.getElementById("btn-wysiwyg-toggle"),

  // Property Inspector
  inspectorCard: document.getElementById("inspector-card"),
  inputFieldName: document.getElementById("prop-field-name"),
  selectColumnBinding: document.getElementById("prop-column-binding"),
  inputTemplateText: document.getElementById("prop-template-text"),
  selectFontFamily: document.getElementById("prop-font-family"),
  btnFontDec: document.getElementById("btn-font-dec"),
  btnFontInc: document.getElementById("btn-font-inc"),
  inputFontSize: document.getElementById("prop-font-size"),
  sliderFontSize: document.getElementById("prop-font-size-slider"),
  fontPresetsContainer: document.getElementById("font-presets"),
  checkAutoShrink: document.getElementById("prop-auto-shrink"),
  btnBold: document.getElementById("prop-btn-bold"),
  btnItalic: document.getElementById("prop-btn-italic"),
  inputColor: document.getElementById("prop-color"),
  inputColorHex: document.getElementById("prop-color-hex"),
  colorSwatchesContainer: document.getElementById("color-swatches"),
  alignBtns: document.querySelectorAll("[data-align]"),
  btnDeleteField: document.getElementById("btn-delete-field"),
  btnDuplicateField: document.getElementById("btn-duplicate-field"),

  // Step 3: Generate
  inputFilenamePattern: document.getElementById("filename-pattern"),
  filenameTags: document.getElementById("filename-tags"),
  filenamePreview: document.getElementById("filename-preview"),
  generateRowCount: document.getElementById("generate-row-count"),
  btnStartGenerate: document.getElementById("btn-start-generate"),
  genScopeAll: document.getElementById("gen-scope-all"),
  genScopeLimit: document.getElementById("gen-scope-limit"),
  genScopeRange: document.getElementById("gen-scope-range"),
  genScopeAllCount: document.getElementById("gen-scope-all-count"),
  genLimitCount: document.getElementById("gen-limit-count"),
  genRangeStart: document.getElementById("gen-range-start"),
  genRangeEnd: document.getElementById("gen-range-end"),

  progressSection: document.getElementById("progress-section"),
  progressFill: document.getElementById("progress-fill"),
  progressPercent: document.getElementById("progress-percent"),
  statProcessed: document.getElementById("stat-processed"),
  statTotal: document.getElementById("stat-total"),
  statWarnings: document.getElementById("stat-warnings"),
  statFailed: document.getElementById("stat-failed"),
  warningsBox: document.getElementById("warnings-box"),
  warningsList: document.getElementById("warnings-list"),
  btnDownloadZip: document.getElementById("btn-download-zip"),
  filesTableBody: document.getElementById("files-table-body"),

  // Toast & Modals
  toastContainer: document.getElementById("toast-container"),
  modalProjects: document.getElementById("modal-projects"),
  modalProjectsList: document.getElementById("modal-projects-list"),
  btnCloseProjectsModal: document.getElementById("btn-close-projects-modal"),
};

// Initialize Canvas
let canvasEditor = null;

function init() {
  canvasEditor = new CanvasEditor(els.canvasContainer, els.canvasStage, els.canvasBgImg);

  initNavigation();
  initUploadStep();
  initEditorStep();
  initInspector();
  initGenerateStep();
  initModals();

  // Subscribe to state changes
  state.subscribe((event, data) => {
    if (event === "stepChange") {
      updateStepUI(data);
    } else if (event === "templateLoaded") {
      onTemplateLoaded(data);
    } else if (event === "dataLoaded") {
      onDataLoaded(data);
    } else if (event === "zoomChanged") {
      if (data.isFit) {
        els.zoomSelect.value = "fit";
      } else {
        const matchingOpt = Array.from(els.zoomSelect.options).find(
          (o) => Math.abs(parseFloat(o.value) - data.level) < 0.05
        );
        if (matchingOpt) {
          els.zoomSelect.value = matchingOpt.value;
        }
      }
    } else if (event === "fieldsChanged") {
      updateFieldsList();
      canvasEditor.render();
      updateInspector();
    } else if (event === "fieldSelected") {
      updateInspector();
      canvasEditor.setSelectedField(data ? data.id : null);
      updateFieldsList();
    } else if (event === "fieldUpdated") {
      canvasEditor.updateActiveFieldVisuals(data);
      updateInspectorValues(data);
      updateFieldsList();
    } else if (event === "previewRowChanged") {
      updateRowNavigator();
      canvasEditor.render();
      updateFilenamePreview();
    }
  });

  // Check URL params for quick actions
  const urlParams = new URLSearchParams(window.location.search);
  if (urlParams.get("demo") === "true") {
    loadDemo("flat");
  }
}

// Navigation & Stepper
function initNavigation() {
  els.stepBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      const step = parseInt(btn.dataset.step, 10);
      if (step === 2 && (!state.template || !state.data)) {
        showToast("Please upload both a PDF template and a spreadsheet first.", "warning");
        return;
      }
      if (step === 3 && state.fields.length === 0) {
        showToast("Please place at least one field on the canvas before generating.", "warning");
        return;
      }
      state.setStep(step);
    });
  });

  els.btnProceedStep2.addEventListener("click", () => {
    if (!state.template || !state.data) {
      showToast("Please upload both a PDF template and a spreadsheet.", "warning");
      return;
    }
    state.setStep(2);
  });

  els.btnProceedStep3.addEventListener("click", () => {
    if (state.fields.length === 0) {
      showToast("Please place at least one field on the canvas before proceeding.", "warning");
      return;
    }
    state.setStep(3);
  });
}

function updateStepUI(step) {
  els.stepBtns.forEach((b) => {
    b.classList.toggle("active", parseInt(b.dataset.step, 10) === step);
  });
  els.views.forEach((v) => {
    v.classList.remove("active");
  });
  const currentView = document.getElementById(`view-${step === 1 ? "upload" : step === 2 ? "editor" : "generate"}`);
  if (currentView) currentView.classList.add("active");

  if (step === 2) {
    // Force redraw on resize
    setTimeout(() => canvasEditor.render(), 100);
  } else if (step === 3) {
    setupGenerateView();
  }
}

// Upload Step Handlers
function initUploadStep() {
  setupDropzone(els.tplDropzone, els.tplFileInput, handleTemplateFile);
  setupDropzone(els.dataDropzone, els.dataFileInput, handleDataFile);

  els.btnLoadDemoFlat.addEventListener("click", () => loadDemo("flat"));
  els.btnLoadDemoAcro.addEventListener("click", () => loadDemo("acroform"));
}

function setupDropzone(dropzoneEl, fileInputEl, handleFn) {
  dropzoneEl.addEventListener("click", () => fileInputEl.click());
  fileInputEl.addEventListener("change", (e) => {
    if (e.target.files.length > 0) handleFn(e.target.files[0]);
  });

  dropzoneEl.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropzoneEl.classList.add("dragover");
  });
  dropzoneEl.addEventListener("dragleave", () => dropzoneEl.classList.remove("dragover"));
  dropzoneEl.addEventListener("drop", (e) => {
    e.preventDefault();
    dropzoneEl.classList.remove("dragover");
    if (e.dataTransfer.files.length > 0) handleFn(e.dataTransfer.files[0]);
  });
}

async function handleTemplateFile(file) {
  try {
    showToast(`Uploading template: ${file.name}...`, "info");
    const res = await api.uploadTemplate(file);
    state.setTemplate(res);
    showToast(`Template loaded successfully (${res.page_count} page(s))`, "success");
    checkAutoMatch();
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function handleDataFile(file) {
  try {
    showToast(`Reading spreadsheet: ${file.name}...`, "info");
    const res = await api.uploadData(file);
    state.setData(res);
    showToast(`Spreadsheet loaded: ${res.total_rows} row(s), ${res.headers.length} columns`, "success");
    checkAutoMatch();
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function loadDemo(type) {
  try {
    const rowCount = els.demoRowCount ? parseInt(els.demoRowCount.value, 10) || 50 : 50;
    showToast(`Loading ${type} demo template and ${rowCount} sample rows...`, "info");
    const res = await api.loadDemoSample(type, rowCount);
    state.setTemplate(res.template);
    state.setData(res.data);

    // If flat demo, pre-populate default fields for quick immediate testing!
    if (type === "flat") {
      state.fields = [];
      state.addField({
        name: "Recipient Name",
        binding: "{{Recipient Name}}",
        x: 0.15,
        y: 0.38,
        width: 0.70,
        height: 0.08,
        font_family: "serif",
        font_size: 28,
        bold: true,
        color: "#1E3A8A",
        align: "center",
      });
      state.addField({
        name: "Course Title",
        binding: "{{Course Title}}",
        x: 0.20,
        y: 0.58,
        width: 0.60,
        height: 0.06,
        font_family: "sans-serif",
        font_size: 18,
        bold: true,
        italic: true,
        color: "#111827",
        align: "center",
      });
      state.addField({
        name: "Completion Date",
        binding: "{{Completion Date}}",
        x: 0.15,
        y: 0.78,
        width: 0.23,
        height: 0.05,
        font_family: "sans-serif",
        font_size: 13,
        color: "#374151",
        align: "center",
      });
    }

    showToast("Demo loaded successfully! You can switch to Step 2 Editor or customize fields.", "success");
    checkAutoMatch();
  } catch (err) {
    showToast(err.message, "error");
  }
}

function onTemplateLoaded(tpl) {
  els.tplName.textContent = tpl.filename;
  els.tplMeta.textContent = `${tpl.width} x ${tpl.height} pt | ${tpl.has_acroform ? `${tpl.acroform_fields.length} AcroForm field(s)` : "Flat template"}`;
  els.tplFileInfo.style.display = "flex";

  canvasEditor.setTemplateImage(tpl.preview_image, tpl.width, tpl.height);
  updateProceedButton();
}

function onDataLoaded(data) {
  els.dataName.textContent = data.filename;
  els.dataMeta.textContent = `${data.total_rows} row(s) | Headers: ${data.headers.join(", ")}`;
  els.dataFileInfo.style.display = "flex";

  updateSidebarChips(data.headers);
  updateColumnBindingDropdown(data.headers);
  updateProceedButton();
}

function updateProceedButton() {
  const ready = state.template && state.data;
  els.btnProceedStep2.disabled = !ready;
  if (ready) {
    els.btnProceedStep2.classList.remove("btn-secondary");
    els.btnProceedStep2.classList.add("btn-primary");
  }
}

async function checkAutoMatch() {
  if (!state.template || !state.data) return;

  if (state.template.has_acroform && state.template.acroform_fields.length > 0) {
    const tplFieldNames = state.template.acroform_fields.map((f) => f.name);
    try {
      const matchRes = await api.autoMatch(tplFieldNames, state.data.headers);
      renderAutoMatchTable(matchRes.matches);
    } catch (e) {
      console.error(e);
    }
  } else {
    els.mappingContainer.style.display = "none";
  }
}

function renderAutoMatchTable(matches) {
  els.mappingTableBody.innerHTML = "";
  els.mappingContainer.style.display = "block";

  matches.forEach((m) => {
    const tr = document.createElement("tr");

    // Template Field Name
    const tdField = document.createElement("td");
    tdField.innerHTML = `<strong>${m.field_name}</strong>`;
    tr.appendChild(tdField);

    // Matching Column Dropdown
    const tdSelect = document.createElement("td");
    const select = document.createElement("select");
    select.className = "select-input";

    const optNone = document.createElement("option");
    optNone.value = "";
    optNone.textContent = "-- Unmapped / Skip --";
    select.appendChild(optNone);

    state.data.headers.forEach((h) => {
      const opt = document.createElement("option");
      opt.value = h;
      opt.textContent = h;
      if (h === m.matched_header) opt.selected = true;
      select.appendChild(opt);
    });

    tdSelect.appendChild(select);
    tr.appendChild(tdSelect);

    // Confidence / Action
    const tdStatus = document.createElement("td");
    if (m.matched_header) {
      tdStatus.innerHTML = `<span style="color: var(--success); font-weight:600;">Matched (${Math.round(m.confidence * 100)}%)</span>`;
    } else {
      tdStatus.innerHTML = `<span style="color: var(--text-dim);">No auto-match</span>`;
    }
    tr.appendChild(tdStatus);

    select.addEventListener("change", () => {
      const boundHeader = select.value;
      const acroField = state.template.acroform_fields.find((f) => f.name === m.field_name);
      if (acroField) {
        // Remove or update existing placed field
        let existing = state.fields.find((f) => f.acroform_name === m.field_name);
        if (boundHeader) {
          if (existing) {
            state.updateField(existing.id, { binding: `{{${boundHeader}}}` });
          } else {
            state.addField({
              name: m.field_name,
              binding: `{{${boundHeader}}}`,
              x: acroField.rect.norm_x,
              y: acroField.rect.norm_y,
              width: acroField.rect.norm_w,
              height: acroField.rect.norm_h,
              is_acroform: true,
              acroform_name: m.field_name,
            });
          }
        } else if (existing) {
          state.removeField(existing.id);
        }
      }
    });

    els.mappingTableBody.appendChild(tr);
  });

  // Automatically add matched AcroForm fields if none exist yet
  if (state.fields.length === 0) {
    matches.forEach((m) => {
      if (m.matched_header) {
        const acroField = state.template.acroform_fields.find((f) => f.name === m.field_name);
        if (acroField) {
          state.addField({
            name: m.field_name,
            binding: `{{${m.matched_header}}}`,
            x: acroField.rect.norm_x,
            y: acroField.rect.norm_y,
            width: acroField.rect.norm_w,
            height: acroField.rect.norm_h,
            is_acroform: true,
            acroform_name: m.field_name,
          });
        }
      }
    });
  }
}

// Step 2: Editor & Canvas
function initEditorStep() {
  els.zoomSelect.addEventListener("change", (e) => {
    if (e.target.value === "fit") {
      canvasEditor.fitToScreen();
    } else {
      canvasEditor.setZoom(parseFloat(e.target.value), false);
    }
  });

  els.btnZoomIn.addEventListener("click", () => {
    const current = state.zoomLevel || 1.0;
    canvasEditor.setZoom(Math.min(2.5, current + 0.15), false);
  });

  els.btnZoomOut.addEventListener("click", () => {
    const current = state.zoomLevel || 1.0;
    canvasEditor.setZoom(Math.max(0.25, current - 0.15), false);
  });

  els.btnZoomFit.addEventListener("click", () => {
    canvasEditor.fitToScreen();
  });

  els.btnPrevRow.addEventListener("click", () => state.prevPreviewRow());
  els.btnNextRow.addEventListener("click", () => state.nextPreviewRow());

  if (els.btnClearFields) {
    els.btnClearFields.addEventListener("click", () => {
      if (state.fields.length === 0) {
        showToast("No placed fields to clear.", "info");
        return;
      }
      if (confirm(`Remove all ${state.fields.length} placed field(s) from the canvas?`)) {
        state.fields = [];
        state.selectedFieldId = null;
        state.notify("fieldsChanged", state.fields);
        state.notify("fieldSelected", null);
        showToast("All canvas fields cleared.", "info");
      }
    });
  }

  els.btnWysiwygToggle.addEventListener("click", async () => {
    if (!state.template) {
      showToast("Please upload a PDF template first.", "warning");
      return;
    }
    if (state.fields.length === 0) {
      showToast("Place at least one field on the canvas to preview print output.", "warning");
      return;
    }
    try {
      els.btnWysiwygToggle.textContent = "Rendering...";
      const rowData = state.getCurrentRowData();
      const res = await api.fetchPreview(state.template.template_id, state.fields, rowData, 0);
      els.canvasBgImg.src = res.preview_image;
      els.btnWysiwygToggle.textContent = "✓ Sample Rendered";
      showToast("Sample print preview rendered on canvas background. (Proceed to Generate whenever ready!)", "success");
      setTimeout(() => {
        els.btnWysiwygToggle.textContent = "Sample Print Preview";
      }, 3500);
    } catch (err) {
      showToast(err.message, "error");
      els.btnWysiwygToggle.textContent = "Sample Print Preview";
    }
  });
}

function updateSidebarChips(headers) {
  els.columnChipsContainer.innerHTML = "";
  headers.forEach((h) => {
    const chip = document.createElement("div");
    chip.className = "column-chip";
    chip.draggable = true;
    chip.innerHTML = `<span>${h}</span><span class="chip-handle">&#8942;&#8942;</span>`;

    chip.addEventListener("dragstart", (e) => {
      e.dataTransfer.setData("text/plain", h);
      e.dataTransfer.effectAllowed = "copy";
    });

    // Also support single click to add field directly
    chip.addEventListener("click", () => {
      state.addField({
        name: h,
        binding: `{{${h}}}`,
        x: 0.25,
        y: 0.35 + ((state.fields.length * 0.08) % 0.4),
        width: 0.5,
        height: 0.07,
        font_size: 22,
        align: "center",
      });
      showToast(`Added field for '${h}'`, "info");
    });

    els.columnChipsContainer.appendChild(chip);
  });
}

function updateFieldsList() {
  els.placedFieldsList.innerHTML = "";
  state.fields.forEach((f) => {
    const item = document.createElement("div");
    item.className = `placed-field-item ${f.id === state.selectedFieldId ? "active" : ""}`;
    item.innerHTML = `
      <span style="font-weight: 600; text-overflow: ellipsis; overflow: hidden; white-space: nowrap;">${f.name}</span>
      <button class="btn btn-sm btn-danger" style="padding: 2px 6px;">&times;</button>
    `;

    item.addEventListener("click", (e) => {
      if (e.target.tagName === "BUTTON") {
        state.removeField(f.id);
      } else {
        state.selectField(f.id);
      }
    });

    els.placedFieldsList.appendChild(item);
  });
}

function updateRowNavigator() {
  if (!state.data || !state.data.preview_rows) return;
  const total = state.data.preview_rows.length;
  const curr = state.previewRowIndex + 1;
  els.previewRowLabel.textContent = `Row ${curr} of ${total}`;
  els.btnPrevRow.disabled = curr <= 1;
  els.btnNextRow.disabled = curr >= total;
}

// Property Inspector
function initInspector() {
  els.inputFieldName.addEventListener("input", (e) => {
    const f = state.getSelectedField();
    if (f) {
      f.name = e.target.value;
      canvasEditor.updateActiveFieldVisuals(f);
      updateFieldsList();
    }
  });

  els.selectColumnBinding.addEventListener("change", (e) => {
    const f = state.getSelectedField();
    if (!f) return;
    const col = e.target.value;
    if (col) {
      els.inputTemplateText.value = `{{${col}}}`;
      f.binding = `{{${col}}}`;
      canvasEditor.updateActiveFieldVisuals(f);
      updateFieldsList();
    }
  });

  els.inputTemplateText.addEventListener("input", (e) => {
    const f = state.getSelectedField();
    if (f) {
      f.binding = e.target.value;
      canvasEditor.updateActiveFieldVisuals(f);
      updateFieldsList();
    }
  });

  els.selectFontFamily.addEventListener("change", (e) => {
    const f = state.getSelectedField();
    if (f) {
      f.font_family = e.target.value;
      canvasEditor.updateActiveFieldVisuals(f);
    }
  });

  const setFontSize = (val) => {
    const f = state.getSelectedField();
    if (!f) return;
    const size = Math.max(6, Math.min(120, Math.round(parseFloat(val) || 12)));
    els.inputFontSize.value = size;
    els.sliderFontSize.value = size;
    f.font_size = size;
    canvasEditor.updateActiveFieldVisuals(f);

    if (els.fontPresetsContainer) {
      els.fontPresetsContainer.querySelectorAll(".font-preset-btn").forEach((btn) => {
        btn.classList.toggle("active", parseInt(btn.dataset.size, 10) === size);
      });
    }
  };

  els.inputFontSize.addEventListener("input", (e) => setFontSize(e.target.value));
  els.sliderFontSize.addEventListener("input", (e) => setFontSize(e.target.value));

  if (els.btnFontDec) {
    els.btnFontDec.addEventListener("click", () => {
      const f = state.getSelectedField();
      if (f) setFontSize((f.font_size || 22) - 2);
    });
  }

  if (els.btnFontInc) {
    els.btnFontInc.addEventListener("click", () => {
      const f = state.getSelectedField();
      if (f) setFontSize((f.font_size || 22) + 2);
    });
  }

  if (els.fontPresetsContainer) {
    els.fontPresetsContainer.querySelectorAll(".font-preset-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const s = parseInt(btn.dataset.size, 10);
        setFontSize(s);
      });
    });
  }

  els.checkAutoShrink.addEventListener("change", (e) => {
    const f = state.getSelectedField();
    if (f) {
      f.auto_shrink = e.target.checked;
      canvasEditor.updateActiveFieldVisuals(f);
    }
  });

  els.btnBold.addEventListener("click", () => {
    const f = state.getSelectedField();
    if (f) {
      f.bold = !f.bold;
      els.btnBold.classList.toggle("active", f.bold);
      canvasEditor.updateActiveFieldVisuals(f);
    }
  });

  els.btnItalic.addEventListener("click", () => {
    const f = state.getSelectedField();
    if (f) {
      f.italic = !f.italic;
      els.btnItalic.classList.toggle("active", f.italic);
      canvasEditor.updateActiveFieldVisuals(f);
    }
  });

  const setColor = (hex) => {
    const f = state.getSelectedField();
    if (!f) return;
    els.inputColor.value = hex;
    els.inputColorHex.value = hex.toUpperCase();
    f.color = hex;
    canvasEditor.updateActiveFieldVisuals(f);

    if (els.colorSwatchesContainer) {
      els.colorSwatchesContainer.querySelectorAll(".color-swatch-btn").forEach((btn) => {
        btn.classList.toggle("active", btn.dataset.color.toLowerCase() === hex.toLowerCase());
      });
    }
  };

  els.inputColor.addEventListener("input", (e) => setColor(e.target.value));
  els.inputColorHex.addEventListener("input", (e) => {
    let val = e.target.value.trim();
    if (!val.startsWith("#")) val = "#" + val;
    if (/^#[0-9A-Fa-f]{6}$/.test(val)) {
      setColor(val);
    }
  });

  if (els.colorSwatchesContainer) {
    els.colorSwatchesContainer.querySelectorAll(".color-swatch-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        setColor(btn.dataset.color);
      });
    });
  }

  els.alignBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      const f = state.getSelectedField();
      if (!f) return;
      f.align = btn.dataset.align;
      els.alignBtns.forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      canvasEditor.updateActiveFieldVisuals(f);
    });
  });

  els.btnDeleteField.addEventListener("click", () => {
    const f = state.getSelectedField();
    if (f) state.removeField(f.id);
  });

  els.btnDuplicateField.addEventListener("click", () => {
    const f = state.getSelectedField();
    if (f) {
      state.addField({
        ...f,
        name: `${f.name} Copy`,
        y: Math.min(0.9, f.y + 0.05),
      });
    }
  });
}

function updateColumnBindingDropdown(headers) {
  els.selectColumnBinding.innerHTML = '<option value="">-- Custom Template / Static --</option>';
  headers.forEach((h) => {
    const opt = document.createElement("option");
    opt.value = h;
    opt.textContent = h;
    els.selectColumnBinding.appendChild(opt);
  });
}

function updateInspector() {
  const f = state.getSelectedField();
  if (!f) {
    els.inspectorCard.style.opacity = "0.5";
    els.inspectorCard.style.pointerEvents = "none";
    return;
  }

  els.inspectorCard.style.opacity = "1";
  els.inspectorCard.style.pointerEvents = "auto";
  updateInspectorValues(f);
}

function updateInspectorValues(f) {
  els.inputFieldName.value = f.name || "";
  els.inputTemplateText.value = f.binding || "";

  // Set dropdown if matches exact column {{Header}}
  const colMatch = f.binding ? f.binding.match(/^\{\{([^}]+)\}\}$/) : null;
  els.selectColumnBinding.value = colMatch ? colMatch[1] : "";

  els.selectFontFamily.value = f.font_family || "sans-serif";
  const size = f.font_size || 22;
  els.inputFontSize.value = size;
  els.sliderFontSize.value = size;

  if (els.fontPresetsContainer) {
    els.fontPresetsContainer.querySelectorAll(".font-preset-btn").forEach((btn) => {
      btn.classList.toggle("active", parseInt(btn.dataset.size, 10) === size);
    });
  }

  els.checkAutoShrink.checked = f.auto_shrink !== undefined ? f.auto_shrink : true;
  els.btnBold.classList.toggle("active", Boolean(f.bold));
  els.btnItalic.classList.toggle("active", Boolean(f.italic));

  const col = f.color || "#000000";
  els.inputColor.value = col;
  els.inputColorHex.value = col.toUpperCase();

  if (els.colorSwatchesContainer) {
    els.colorSwatchesContainer.querySelectorAll(".color-swatch-btn").forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.color.toLowerCase() === col.toLowerCase());
    });
  }

  els.alignBtns.forEach((b) => {
    b.classList.toggle("active", b.dataset.align === (f.align || "center"));
  });
}

// Step 3: Generate
function initGenerateStep() {
  els.inputFilenamePattern.addEventListener("input", (e) => {
    state.filenamePattern = e.target.value;
    updateFilenamePreview();
  });

  // Scope radio and input event listeners
  const scopeInputs = [
    els.genScopeAll,
    els.genScopeLimit,
    els.genScopeRange,
    els.genLimitCount,
    els.genRangeStart,
    els.genRangeEnd,
  ];

  scopeInputs.forEach((input) => {
    if (!input) return;
    input.addEventListener("input", () => {
      if (input === els.genLimitCount && els.genScopeLimit) {
        els.genScopeLimit.checked = true;
      } else if ((input === els.genRangeStart || input === els.genRangeEnd) && els.genScopeRange) {
        els.genScopeRange.checked = true;
      }
      updateGenerateButtonCount();
    });
    input.addEventListener("change", () => updateGenerateButtonCount());
  });

  els.btnStartGenerate.addEventListener("click", () => triggerBulkGeneration());
}

function getSelectedRowScope() {
  const totalRows = state.data?.total_rows || 0;
  if (!totalRows) return { count: 0, start: 0, limit: null };

  if (els.genScopeLimit && els.genScopeLimit.checked) {
    const limit = Math.max(1, parseInt(els.genLimitCount.value, 10) || 10);
    const count = Math.min(limit, totalRows);
    return { count, start: 0, limit: count };
  }

  if (els.genScopeRange && els.genScopeRange.checked) {
    const rStart = Math.max(1, parseInt(els.genRangeStart.value, 10) || 1);
    const rEnd = Math.max(rStart, parseInt(els.genRangeEnd.value, 10) || rStart);
    const clampedStart = Math.min(rStart, totalRows);
    const clampedEnd = Math.min(rEnd, totalRows);
    const count = Math.max(1, clampedEnd - clampedStart + 1);
    return { count, start: clampedStart - 1, limit: count };
  }

  // Default: All Rows
  return { count: totalRows, start: 0, limit: null };
}

function updateGenerateButtonCount() {
  const { count } = getSelectedRowScope();
  if (els.generateRowCount) {
    els.generateRowCount.textContent = `${count} certificate${count === 1 ? "" : "s"}`;
  }
}

function setupGenerateView() {
  const totalRows = state.data?.total_rows || 0;
  if (els.genScopeAllCount) {
    els.genScopeAllCount.textContent = totalRows;
  }
  if (els.genLimitCount) {
    els.genLimitCount.max = totalRows;
    if (!els.genLimitCount.value || parseInt(els.genLimitCount.value, 10) > totalRows) {
      els.genLimitCount.value = Math.min(50, totalRows || 10);
    }
  }
  if (els.genRangeStart && els.genRangeEnd) {
    els.genRangeStart.max = totalRows;
    els.genRangeEnd.max = totalRows;
    if (!els.genRangeEnd.value || parseInt(els.genRangeEnd.value, 10) === 0) {
      els.genRangeEnd.value = totalRows || 10;
    }
  }

  updateGenerateButtonCount();
  els.inputFilenamePattern.value = state.filenamePattern;

  // Populate suggestion tags
  els.filenameTags.innerHTML = "";
  const standardTags = (state.data?.headers || []).concat(["Row"]);
  standardTags.forEach((tag) => {
    const chip = document.createElement("span");
    chip.className = "tag-chip";
    chip.textContent = `+ {${tag}}`;
    chip.addEventListener("click", () => {
      els.inputFilenamePattern.value += `_{${tag}}`;
      state.filenamePattern = els.inputFilenamePattern.value;
      updateFilenamePreview();
    });
    els.filenameTags.appendChild(chip);
  });

  updateFilenamePreview();
}

function updateFilenamePreview() {
  const pattern = state.filenamePattern || "{Recipient Name}.pdf";
  const row = state.getCurrentRowData();
  let rendered = pattern.replace(/\{\{([^}]+)\}\}/g, (m, k) => row[k.trim()] || `[${k}]`);
  rendered = rendered.replace(/\{([^{}]+)\}/g, (m, k) => row[k.trim()] || `[${k}]`);
  rendered = rendered.replace(/_pdf$/i, "").replace(/\.pdf$/i, "");
  els.filenamePreview.textContent = `${rendered}.pdf`;
}

async function triggerBulkGeneration() {
  if (!state.template || !state.data) return;

  const { count, start, limit } = getSelectedRowScope();
  if (count <= 0) {
    showToast("No rows selected for generation.", "warning");
    return;
  }

  try {
    els.btnStartGenerate.disabled = true;
    els.progressSection.style.display = "block";
    els.warningsBox.style.display = "none";
    els.btnDownloadZip.style.display = "none";
    els.filesTableBody.innerHTML = "";

    showToast(`Starting background generation job for ${count} certificate(s)...`, "info");
    const jobRes = await api.startGeneration(
      state.template.template_id,
      state.data.data_id,
      state.fields,
      state.filenamePattern,
      0,
      start,
      limit
    );

    state.activeJobId = jobRes.job_id;
    pollJobProgress(jobRes.job_id);
  } catch (err) {
    els.btnStartGenerate.disabled = false;
    showToast(err.message, "error");
  }
}

function pollJobProgress(jobId) {
  if (state.jobPollTimer) clearInterval(state.jobPollTimer);

  state.jobPollTimer = setInterval(async () => {
    try {
      const job = await api.getJobStatus(jobId);

      // Update UI stats
      els.progressFill.style.width = `${job.percent}%`;
      els.progressPercent.textContent = `${job.percent}%`;
      els.statProcessed.textContent = job.processed_rows;
      els.statTotal.textContent = job.total_rows;
      els.statWarnings.textContent = job.warnings.length;
      els.statFailed.textContent = job.failed_rows;

      // Update Warnings
      if (job.warnings && job.warnings.length > 0) {
        els.warningsBox.style.display = "block";
        els.warningsList.innerHTML = job.warnings.map((w) => `<li>${w}</li>`).join("");
      }

      // Check if finished
      if (job.status === "completed" || job.status === "failed") {
        clearInterval(state.jobPollTimer);
        els.btnStartGenerate.disabled = false;

        if (job.status === "completed") {
          showToast(`Bulk generation complete! ${job.processed_rows} files generated.`, "success");
          setupCompletedJob(jobId, job);
        } else {
          showToast(`Generation failed: ${job.error || "Unknown error"}`, "error");
        }
      }
    } catch (e) {
      console.error("Poll error:", e);
    }
  }, 350);
}

function setupCompletedJob(jobId, job) {
  // Setup ZIP download button
  els.btnDownloadZip.style.display = "inline-flex";
  els.btnDownloadZip.href = `/api/jobs/${jobId}/download-zip`;

  // Render generated files table
  els.filesTableBody.innerHTML = "";
  (job.generated_files || []).forEach((f) => {
    const tr = document.createElement("tr");
    const kb = (f.size_bytes / 1024).toFixed(1);
    tr.style.backgroundColor = "#FFFFFF";
    tr.innerHTML = `
      <td style="padding: 10px 12px; border-bottom: 2px solid #000; border-right: 1px solid #000; font-weight: 700;">${f.filename}</td>
      <td style="padding: 10px 12px; border-bottom: 2px solid #000; border-right: 1px solid #000; font-weight: 600; color: #444;">${kb} KB</td>
      <td style="padding: 10px 12px; border-bottom: 2px solid #000; text-align: right;">
        <a href="/api/jobs/${jobId}/download/${encodeURIComponent(f.filename)}" class="btn btn-sm btn-neo-yellow" target="_blank">Download</a>
      </td>
    `;
    els.filesTableBody.appendChild(tr);
  });
}

// Project Save & Load Modals
function initModals() {
  els.btnSaveProject.addEventListener("click", async () => {
    const name = prompt("Enter a name for this project:", state.template?.filename || "certificate_design");
    if (!name) return;

    try {
      const projectData = state.exportProjectJSON();
      await api.saveProject(name, projectData);
      showToast(`Project '${name}' saved successfully!`, "success");
    } catch (err) {
      showToast(err.message, "error");
    }
  });

  els.btnLoadProject.addEventListener("click", async () => {
    try {
      const res = await api.listProjects();
      renderProjectsList(res.projects);
      els.modalProjects.classList.add("active");
    } catch (err) {
      showToast(err.message, "error");
    }
  });

  els.btnCloseProjectsModal.addEventListener("click", () => {
    els.modalProjects.classList.remove("active");
  });

  els.btnNewProject.addEventListener("click", () => {
    if (confirm("Start a new project? Any unsaved layout changes will be cleared.")) {
      window.location.reload();
    }
  });
}

function renderProjectsList(projects) {
  els.modalProjectsList.innerHTML = "";
  if (!projects || projects.length === 0) {
    els.modalProjectsList.innerHTML = `<p style="color: #444; font-weight: 700; padding: 12px;">No saved projects found.</p>`;
    return;
  }

  projects.forEach((p) => {
    const item = document.createElement("div");
    item.className = "file-info-badge";
    item.style.cursor = "pointer";
    item.style.marginBottom = "8px";
    item.style.backgroundColor = "#FAF7F0";
    item.innerHTML = `
      <div>
        <strong style="font-size: 0.95rem;">${p.name}</strong>
        <div style="font-size: 0.75rem; color: #444; font-weight: 600;">${p.fields_count} field(s) | ${p.filename_pattern || "Default pattern"}</div>
      </div>
      <button class="btn btn-sm btn-primary">Load</button>
    `;

    item.addEventListener("click", async () => {
      try {
        const loaded = await api.loadProject(p.name);
        state.importProjectJSON(loaded.project_data);
        els.modalProjects.classList.remove("active");
        showToast(`Project '${p.name}' loaded!`, "success");
        if (state.template) state.setStep(2);
      } catch (err) {
        showToast(err.message, "error");
      }
    });

    els.modalProjectsList.appendChild(item);
  });
}

// Toast Notifications
function showToast(message, type = "info") {
  const toast = document.createElement("div");
  toast.className = `toast toast-${type} ${type}`;
  toast.textContent = message;
  els.toastContainer.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

// Bootstrapping
window.addEventListener("DOMContentLoaded", init);
