// Canvas Drag-and-Drop & Interactive Overlay Editor Engine
import { state } from "./state.js";

export class CanvasEditor {
  constructor(containerEl, stageEl, bgImgEl) {
    this.container = containerEl;
    this.stage = stageEl;
    this.bgImg = bgImgEl;

    this.pdfWidth = 792;
    this.pdfHeight = 612;
    this.isFitMode = true;

    this.initEvents();
  }

  initEvents() {
    // Drop target for draggable sidebar chips
    this.stage.addEventListener("dragover", (e) => {
      e.preventDefault();
      e.dataTransfer.dropEffect = "copy";
    });

    this.stage.addEventListener("drop", (e) => {
      e.preventDefault();
      const rawData = e.dataTransfer.getData("text/plain");
      if (!rawData) return;

      const rect = this.stage.getBoundingClientRect();
      const clickX = e.clientX - rect.left;
      const clickY = e.clientY - rect.top;

      const normW = 0.45;
      const normH = 0.08;
      // Center the dropped box on the cursor
      const normX = Math.max(0, Math.min(1 - normW, clickX / rect.width - normW / 2));
      const normY = Math.max(0, Math.min(1 - normH, clickY / rect.height - normH / 2));

      state.addField({
        name: rawData,
        binding: `{{${rawData}}}`,
        x: normX,
        y: normY,
        width: normW,
        height: normH,
        font_size: 22,
        align: "center",
      });
    });

    // Auto-fit on window resize if in fit mode
    window.addEventListener("resize", () => {
      if (this.isFitMode && state.template) {
        this.fitToScreen();
      }
    });

    // Click on stage background to deselect active field
    this.stage.addEventListener("pointerdown", (e) => {
      if (e.target === this.stage || e.target === this.bgImg) {
        state.selectField(null);
      }
    });
  }

  setTemplateImage(dataUri, pdfWidth, pdfHeight) {
    this.bgImg.src = dataUri;
    this.pdfWidth = pdfWidth || 792;
    this.pdfHeight = pdfHeight || 612;

    // Fit certificate inside current viewport by default
    this.fitToScreen();
  }

  fitToScreen() {
    if (!this.pdfWidth || !this.pdfHeight) return;

    const viewport = document.getElementById("canvas-scroll-viewport") || this.container;
    const availW = Math.max(160, (viewport.clientWidth || 360) - 24);
    const availH = Math.max(160, (viewport.clientHeight || 360) - 24);

    const scaleW = availW / this.pdfWidth;
    const scaleH = availH / this.pdfHeight;
    const fitScale = Math.min(scaleW, scaleH);

    this.setZoom(fitScale, true);
  }

  setZoom(level, isFit = false) {
    // Clamp zoom between 0.20 (20%) and 2.50 (250%)
    level = Math.max(0.2, Math.min(2.5, level));
    state.zoomLevel = level;
    this.isFitMode = isFit;

    // Set pixel dimensions directly - no transform distortion!
    const stageW = Math.round(this.pdfWidth * level);
    const stageH = Math.round(this.pdfHeight * level);

    this.stage.style.width = `${stageW}px`;
    this.stage.style.height = `${stageH}px`;
    this.stage.style.transform = "none";

    this.render();
    state.notify("zoomChanged", { level, isFit });
  }

  render() {
    if (!state.template) return;

    // Remove existing overlays
    const existing = this.stage.querySelectorAll(".overlay-field, .acroform-outline");
    existing.forEach((el) => el.remove());

    const stageW = this.stage.offsetWidth || Math.round(this.pdfWidth * (state.zoomLevel || 1.0));
    const stageH = this.stage.offsetHeight || Math.round(this.pdfHeight * (state.zoomLevel || 1.0));
    const scaleRatio = stageW / (this.pdfWidth || 800);

    // 1. Render AcroForm detected bounds
    if (state.template.acroform_fields && state.template.acroform_fields.length > 0) {
      state.template.acroform_fields.forEach((af) => {
        const outline = document.createElement("div");
        outline.className = "acroform-outline";
        outline.style.left = `${af.rect.norm_x * stageW}px`;
        outline.style.top = `${af.rect.norm_y * stageH}px`;
        outline.style.width = `${af.rect.norm_w * stageW}px`;
        outline.style.height = `${af.rect.norm_h * stageH}px`;

        const tag = document.createElement("span");
        tag.className = "acroform-outline-tag";
        tag.textContent = af.name;
        outline.appendChild(tag);

        outline.title = `AcroForm Field: ${af.name} (Click to create binding)`;
        outline.style.cursor = "pointer";
        outline.style.pointerEvents = "auto";
        outline.addEventListener("click", () => {
          const existingField = state.fields.find((f) => f.acroform_name === af.name);
          if (existingField) {
            state.selectField(existingField.id);
          } else {
            state.addField({
              name: af.name,
              binding: `{{${af.name}}}`,
              x: af.rect.norm_x,
              y: af.rect.norm_y,
              width: af.rect.norm_w,
              height: af.rect.norm_h,
              is_acroform: true,
              acroform_name: af.name,
            });
          }
        });

        this.stage.appendChild(outline);
      });
    }

    // 2. Render Placed User Fields
    const rowData = state.getCurrentRowData();

    state.fields.forEach((field) => {
      const fieldEl = document.createElement("div");
      const isSelected = field.id === state.selectedFieldId;
      fieldEl.className = `overlay-field ${isSelected ? "active" : ""}`;
      fieldEl.dataset.fieldId = field.id;

      const leftPx = field.x * stageW;
      const topPx = field.y * stageH;
      const widthPx = field.width * stageW;
      const heightPx = field.height * stageH;

      fieldEl.style.left = `${leftPx}px`;
      fieldEl.style.top = `${topPx}px`;
      fieldEl.style.width = `${widthPx}px`;
      fieldEl.style.height = `${heightPx}px`;

      this.applyFieldStylesToElement(fieldEl, field, scaleRatio, rowData);

      // Badge tag
      const badge = document.createElement("div");
      badge.className = "field-badge";
      badge.textContent = field.name || field.binding;
      fieldEl.appendChild(badge);

      // Text Content
      const textSpan = document.createElement("div");
      textSpan.className = "field-text-preview";
      textSpan.textContent = this.resolvePreviewText(field.binding, rowData);
      fieldEl.appendChild(textSpan);

      // Attach resize handles if selected
      if (isSelected) {
        this.ensureResizeHandles(fieldEl, field.id);
      }

      // Attach instantaneous, non-blocking Pointer Events drag listener
      this.attachDragEvents(fieldEl, field);

      this.stage.appendChild(fieldEl);
    });
  }

  setSelectedField(fieldId) {
    const fields = this.stage.querySelectorAll(".overlay-field");
    fields.forEach((el) => {
      const isSelected = el.dataset.fieldId === fieldId;
      el.classList.toggle("active", isSelected);
      if (isSelected) {
        this.ensureResizeHandles(el, fieldId);
      } else {
        this.removeResizeHandles(el);
      }
    });
  }

  ensureResizeHandles(fieldEl, fieldId) {
    if (fieldEl.querySelectorAll(".resize-handle").length > 0) return;
    const field = state.fields.find((f) => f.id === fieldId);
    if (!field) return;

    ["nw", "ne", "se", "sw", "n", "s", "e", "w"].forEach((pos) => {
      const handle = document.createElement("div");
      handle.className = `resize-handle ${pos}`;
      handle.dataset.handle = pos;
      this.attachResizeHandle(handle, pos, field, fieldEl);
      fieldEl.appendChild(handle);
    });
  }

  removeResizeHandles(fieldEl) {
    const handles = fieldEl.querySelectorAll(".resize-handle");
    handles.forEach((h) => h.remove());
  }

  attachDragEvents(fieldEl, field) {
    let isDragging = false;
    let startPointerX = 0;
    let startPointerY = 0;
    let startLeftPx = 0;
    let startTopPx = 0;
    let stageW = 0;
    let stageH = 0;
    let fieldW = 0;
    let fieldH = 0;

    fieldEl.addEventListener("pointerdown", (e) => {
      // Don't drag if clicking a resize handle
      if (e.target.classList.contains("resize-handle")) return;

      e.preventDefault();
      e.stopPropagation();

      fieldEl.style.zIndex = "25";

      // Select this field
      if (state.selectedFieldId !== field.id) {
        state.selectField(field.id);
      } else {
        this.setSelectedField(field.id);
      }

      isDragging = true;
      try {
        fieldEl.setPointerCapture(e.pointerId);
      } catch (_) {}

      startPointerX = e.clientX;
      startPointerY = e.clientY;

      stageW = this.stage.offsetWidth || 800;
      stageH = this.stage.offsetHeight || 600;

      startLeftPx = parseFloat(fieldEl.style.left) || (field.x * stageW);
      startTopPx = parseFloat(fieldEl.style.top) || (field.y * stageH);
      fieldW = parseFloat(fieldEl.style.width) || (field.width * stageW);
      fieldH = parseFloat(fieldEl.style.height) || (field.height * stageH);
    });

    fieldEl.addEventListener("pointermove", (e) => {
      if (!isDragging) return;
      e.preventDefault();
      e.stopPropagation();

      const dx = e.clientX - startPointerX;
      const dy = e.clientY - startPointerY;

      let newLeft = startLeftPx + dx;
      let newTop = startTopPx + dy;

      // Clamp inside canvas bounds
      newLeft = Math.max(0, Math.min(stageW - fieldW, newLeft));
      newTop = Math.max(0, Math.min(stageH - fieldH, newTop));

      // Direct inline update - 0ms latency, runs at native refresh rate
      fieldEl.style.left = `${newLeft}px`;
      fieldEl.style.top = `${newTop}px`;
    });

    const finishDrag = (e) => {
      if (!isDragging) return;
      isDragging = false;
      fieldEl.style.zIndex = field.id === state.selectedFieldId ? "20" : "10";

      try {
        if (fieldEl.hasPointerCapture(e.pointerId)) {
          fieldEl.releasePointerCapture(e.pointerId);
        }
      } catch (_) {}

      const curLeft = parseFloat(fieldEl.style.left) || 0;
      const curTop = parseFloat(fieldEl.style.top) || 0;

      const normX = Math.max(0, Math.min(1 - field.width, curLeft / stageW));
      const normY = Math.max(0, Math.min(1 - field.height, curTop / stageH));

      field.x = normX;
      field.y = normY;
      state.updateField(field.id, { x: normX, y: normY });
    };

    fieldEl.addEventListener("pointerup", finishDrag);
    fieldEl.addEventListener("pointercancel", finishDrag);
  }

  attachResizeHandle(handle, pos, field, fieldEl) {
    let isResizing = false;
    let startPointerX = 0;
    let startPointerY = 0;
    let startLeft = 0;
    let startTop = 0;
    let startWidth = 0;
    let startHeight = 0;
    let stageW = 0;
    let stageH = 0;

    handle.addEventListener("pointerdown", (e) => {
      e.preventDefault();
      e.stopPropagation();

      try {
        handle.setPointerCapture(e.pointerId);
      } catch (_) {}

      isResizing = true;
      startPointerX = e.clientX;
      startPointerY = e.clientY;

      stageW = this.stage.offsetWidth || 800;
      stageH = this.stage.offsetHeight || 600;

      startLeft = parseFloat(fieldEl.style.left) || (field.x * stageW);
      startTop = parseFloat(fieldEl.style.top) || (field.y * stageH);
      startWidth = parseFloat(fieldEl.style.width) || (field.width * stageW);
      startHeight = parseFloat(fieldEl.style.height) || (field.height * stageH);
    });

    handle.addEventListener("pointermove", (e) => {
      if (!isResizing) return;
      e.preventDefault();
      e.stopPropagation();

      const dx = e.clientX - startPointerX;
      const dy = e.clientY - startPointerY;

      let newL = startLeft;
      let newT = startTop;
      let newW = startWidth;
      let newH = startHeight;

      const minW = 20;
      const minH = 15;

      if (pos.includes("e")) {
        newW = Math.max(minW, Math.min(stageW - newL, startWidth + dx));
      }
      if (pos.includes("s")) {
        newH = Math.max(minH, Math.min(stageH - newT, startHeight + dy));
      }
      if (pos.includes("w")) {
        const potW = startWidth - dx;
        if (potW >= minW && startLeft + dx >= 0) {
          newL = startLeft + dx;
          newW = potW;
        }
      }
      if (pos.includes("n")) {
        const potH = startHeight - dy;
        if (potH >= minH && startTop + dy >= 0) {
          newT = startTop + dy;
          newH = potH;
        }
      }

      fieldEl.style.left = `${newL}px`;
      fieldEl.style.top = `${newT}px`;
      fieldEl.style.width = `${newW}px`;
      fieldEl.style.height = `${newH}px`;
    });

    const finishResize = (e) => {
      if (!isResizing) return;
      isResizing = false;

      try {
        if (handle.hasPointerCapture(e.pointerId)) {
          handle.releasePointerCapture(e.pointerId);
        }
      } catch (_) {}

      const curL = parseFloat(fieldEl.style.left) || 0;
      const curT = parseFloat(fieldEl.style.top) || 0;
      const curW = parseFloat(fieldEl.style.width) || 20;
      const curH = parseFloat(fieldEl.style.height) || 15;

      const normX = Math.max(0, curL / stageW);
      const normY = Math.max(0, curT / stageH);
      const normW = Math.min(1 - normX, curW / stageW);
      const normH = Math.min(1 - normY, curH / stageH);

      field.x = normX;
      field.y = normY;
      field.width = normW;
      field.height = normH;
      state.updateField(field.id, { x: normX, y: normY, width: normW, height: normH });
    };

    handle.addEventListener("pointerup", finishResize);
    handle.addEventListener("pointercancel", finishResize);
  }

  applyFieldStylesToElement(fieldEl, field, scaleRatio, rowData) {
    if (!scaleRatio) {
      const stageW = this.stage.offsetWidth || 800;
      scaleRatio = stageW / (this.pdfWidth || 800);
    }
    const displaySize = Math.max(9, Math.round(field.font_size * scaleRatio));
    fieldEl.style.fontSize = `${displaySize}px`;
    fieldEl.style.color = field.color || "#000000";
    fieldEl.style.fontWeight = field.bold ? "bold" : "normal";
    fieldEl.style.fontStyle = field.italic ? "italic" : "normal";
    fieldEl.style.justifyContent =
      field.align === "center" ? "center" : field.align === "right" ? "flex-end" : "flex-start";
    fieldEl.style.textAlign = field.align || "left";

    const fam = (field.font_family || "sans-serif").toLowerCase();
    if (fam.includes("serif") && !fam.includes("sans")) {
      fieldEl.style.fontFamily = '"Times New Roman", Times, Georgia, serif';
    } else if (fam.includes("cursive") || fam.includes("script") || fam.includes("brush")) {
      fieldEl.style.fontFamily = '"Brush Script MT", "Great Vibes", "Lucida Calligraphy", cursive';
    } else if (fam.includes("display")) {
      fieldEl.style.fontFamily = 'Georgia, "Playfair Display", serif';
    } else if (fam.includes("mono") || fam.includes("cour")) {
      fieldEl.style.fontFamily = '"Courier New", Courier, monospace';
    } else {
      fieldEl.style.fontFamily = '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif';
    }

    const textSpan = fieldEl.querySelector(".field-text-preview");
    if (textSpan && rowData) {
      textSpan.textContent = this.resolvePreviewText(field.binding, rowData);
    }
  }

  updateActiveFieldVisuals(field) {
    if (!field) return;
    const fieldEl = this.stage.querySelector(`.overlay-field[data-field-id="${field.id}"]`);
    if (fieldEl) {
      const stageW = this.stage.offsetWidth || 800;
      const stageH = this.stage.offsetHeight || 600;
      const scaleRatio = stageW / (this.pdfWidth || 800);
      const rowData = state.getCurrentRowData();

      fieldEl.style.left = `${field.x * stageW}px`;
      fieldEl.style.top = `${field.y * stageH}px`;
      fieldEl.style.width = `${field.width * stageW}px`;
      fieldEl.style.height = `${field.height * stageH}px`;

      this.applyFieldStylesToElement(fieldEl, field, scaleRatio, rowData);

      const badge = fieldEl.querySelector(".field-badge");
      if (badge) {
        badge.textContent = field.name || field.binding;
      }
    }
  }

  resolvePreviewText(binding, rowData) {
    if (!binding) return "[Empty]";
    if (binding in rowData) return rowData[binding] || `[${binding} is blank]`;

    let res = binding.replace(/\{\{([^}]+)\}\}/g, (match, p1) => {
      const k = p1.trim();
      return rowData[k] !== undefined ? rowData[k] : match;
    });
    res = res.replace(/\{([^{}]+)\}/g, (match, p1) => {
      const k = p1.trim();
      return rowData[k] !== undefined ? rowData[k] : match;
    });
    return res;
  }
}
