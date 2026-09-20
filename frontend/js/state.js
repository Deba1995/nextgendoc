// State Management for DocuNext
export const state = {
  currentStep: 1,
  template: null, // { template_id, filename, width, height, has_acroform, acroform_fields, preview_image }
  data: null, // { data_id, filename, headers, total_rows, preview_rows }
  fields: [],
  selectedFieldId: null,
  previewRowIndex: 0,
  filenamePattern: "{Recipient Name}_{Course Title}.pdf",
  zoomLevel: 1.0,
  isWysiwygPreview: false,
  activeJobId: null,
  jobPollTimer: null,
  listeners: [],

  subscribe(listener) {
    this.listeners.push(listener);
  },

  notify(event, data) {
    this.listeners.forEach((fn) => fn(event, data));
  },

  setStep(step) {
    this.currentStep = step;
    this.notify("stepChange", step);
  },

  setTemplate(tplData) {
    this.template = tplData;
    this.notify("templateLoaded", tplData);
  },

  setData(dataInfo) {
    this.data = dataInfo;
    this.previewRowIndex = 0;
    // Set a sensible default filename pattern based on available headers
    if (dataInfo.headers && dataInfo.headers.length > 0) {
      const h1 = dataInfo.headers[0];
      const h2 = dataInfo.headers.length > 1 ? dataInfo.headers[1] : "Cert";
      this.filenamePattern = `{${h1}}_{${h2}}.pdf`;
    }
    this.notify("dataLoaded", dataInfo);
  },

  addField(fieldProps) {
    const id = "f_" + Math.random().toString(36).substring(2, 9);
    const newField = {
      id,
      name: fieldProps.name || `Field ${this.fields.length + 1}`,
      binding: fieldProps.binding || (this.data?.headers?.[0] ? `{{${this.data.headers[0]}}}` : ""),
      x: fieldProps.x ?? 0.2,
      y: fieldProps.y ?? 0.3,
      width: fieldProps.width ?? 0.6,
      height: fieldProps.height ?? 0.08,
      is_normalized: true,
      font_family: fieldProps.font_family || "sans-serif",
      font_size: fieldProps.font_size || 22,
      auto_shrink: fieldProps.auto_shrink !== undefined ? fieldProps.auto_shrink : true,
      min_font_size: fieldProps.min_font_size || 6,
      bold: fieldProps.bold || false,
      italic: fieldProps.italic || false,
      color: fieldProps.color || "#000000",
      align: fieldProps.align || "center",
      is_acroform: fieldProps.is_acroform || false,
      acroform_name: fieldProps.acroform_name || "",
    };

    this.fields.push(newField);
    this.selectedFieldId = id;
    this.notify("fieldsChanged", this.fields);
    this.notify("fieldSelected", newField);
    return newField;
  },

  removeField(fieldId) {
    this.fields = this.fields.filter((f) => f.id !== fieldId);
    if (this.selectedFieldId === fieldId) {
      this.selectedFieldId = this.fields.length > 0 ? this.fields[0].id : null;
    }
    this.notify("fieldsChanged", this.fields);
    this.notify("fieldSelected", this.getSelectedField());
  },

  updateField(fieldId, updates) {
    const field = this.fields.find((f) => f.id === fieldId);
    if (field) {
      Object.assign(field, updates);
      this.notify("fieldUpdated", field);
    }
  },

  selectField(fieldId) {
    if (this.selectedFieldId === fieldId) return;
    this.selectedFieldId = fieldId;
    this.notify("fieldSelected", this.getSelectedField());
  },

  getSelectedField() {
    return this.fields.find((f) => f.id === this.selectedFieldId) || null;
  },

  getCurrentRowData() {
    if (!this.data || !this.data.preview_rows || this.data.preview_rows.length === 0) {
      return {};
    }
    const idx = Math.min(this.previewRowIndex, this.data.preview_rows.length - 1);
    return this.data.preview_rows[idx] || {};
  },

  nextPreviewRow() {
    if (!this.data?.preview_rows) return;
    if (this.previewRowIndex < this.data.preview_rows.length - 1) {
      this.previewRowIndex++;
      this.notify("previewRowChanged", this.previewRowIndex);
    }
  },

  prevPreviewRow() {
    if (!this.data?.preview_rows) return;
    if (this.previewRowIndex > 0) {
      this.previewRowIndex--;
      this.notify("previewRowChanged", this.previewRowIndex);
    }
  },

  exportProjectJSON() {
    return {
      version: "1.0",
      template_name: this.template?.filename || "",
      filename_pattern: this.filenamePattern,
      fields: this.fields,
    };
  },

  importProjectJSON(jsonObj) {
    if (jsonObj.fields && Array.isArray(jsonObj.fields)) {
      this.fields = jsonObj.fields;
      if (jsonObj.filename_pattern) {
        this.filenamePattern = jsonObj.filename_pattern;
      }
      this.selectedFieldId = this.fields.length > 0 ? this.fields[0].id : null;
      this.notify("fieldsChanged", this.fields);
      this.notify("fieldSelected", this.getSelectedField());
    }
  },
};
