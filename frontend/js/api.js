// API Client for DocuNext Backend
export const api = {
  async uploadTemplate(file) {
    const fd = new FormData();
    fd.append("file", file);
    const res = await fetch("/api/upload/template", { method: "POST", body: fd });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Upload failed" }));
      throw new Error(err.detail || "Failed to upload template");
    }
    return await res.json();
  },

  async uploadData(file) {
    const fd = new FormData();
    fd.append("file", file);
    const res = await fetch("/api/upload/data", { method: "POST", body: fd });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Upload failed" }));
      throw new Error(err.detail || "Failed to upload spreadsheet");
    }
    return await res.json();
  },

  async autoMatch(templateFields, spreadsheetHeaders) {
    const res = await fetch("/api/automatch", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        template_fields: templateFields,
        spreadsheet_headers: spreadsheetHeaders,
      }),
    });
    if (!res.ok) throw new Error("Auto-matching failed");
    return await res.json();
  },

  async fetchPreview(templateId, fields, rowData, pageNum = 0) {
    const res = await fetch("/api/preview/sample", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        template_id: templateId,
        fields,
        row_data: rowData,
        page_num: pageNum,
      }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Preview generation failed" }));
      throw new Error(err.detail || "Preview failed");
    }
    return await res.json();
  },

  async saveProject(name, projectData) {
    const res = await fetch("/api/projects/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, project_data: projectData }),
    });
    if (!res.ok) throw new Error("Failed to save project");
    return await res.json();
  },

  async listProjects() {
    const res = await fetch("/api/projects/list");
    if (!res.ok) throw new Error("Failed to list projects");
    return await res.json();
  },

  async loadProject(name) {
    const res = await fetch(`/api/projects/${encodeURIComponent(name)}`);
    if (!res.ok) throw new Error("Failed to load project");
    return await res.json();
  },

  async startGeneration(templateId, dataId, fields, filenamePattern, pageNum = 0, rowStart = 0, rowLimit = null) {
    const res = await fetch("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        template_id: templateId,
        data_id: dataId,
        fields,
        filename_pattern: filenamePattern,
        page_num: pageNum,
        row_start: rowStart,
        row_limit: rowLimit,
      }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Generation trigger failed" }));
      throw new Error(err.detail || "Failed to start generation");
    }
    return await res.json();
  },

  async getJobStatus(jobId) {
    const res = await fetch(`/api/jobs/${encodeURIComponent(jobId)}/status`);
    if (!res.ok) throw new Error("Failed to fetch job status");
    return await res.json();
  },

  async getJobFiles(jobId) {
    const res = await fetch(`/api/jobs/${encodeURIComponent(jobId)}/files`);
    if (!res.ok) throw new Error("Failed to fetch generated files");
    return await res.json();
  },

  async loadDemoSample(type = "flat", rowCount = 50) {
    const res = await fetch(`/api/sample/load?sample_type=${encodeURIComponent(type)}&row_count=${rowCount}`, {
      method: "POST",
    });
    if (!res.ok) throw new Error("Failed to load sample assets");
    return await res.json();
  },

  async testSmtp(smtpConfig) {
    const res = await fetch("/api/email/test-connection", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(smtpConfig),
    });
    if (!res.ok) throw new Error("Failed to connect to SMTP server");
    return await res.json();
  },

  async startEmailBatch(payload) {
    const res = await fetch("/api/email/send-batch", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Failed to start email batch" }));
      throw new Error(err.detail || "Email dispatch failed");
    }
    return await res.json();
  },

  async getEmailJobStatus(jobId) {
    const res = await fetch(`/api/email/status/${encodeURIComponent(jobId)}`);
    if (!res.ok) throw new Error("Failed to fetch email job status");
    return await res.json();
  },

  async cancelEmailJob(jobId) {
    const res = await fetch(`/api/email/cancel/${encodeURIComponent(jobId)}`, {
      method: "POST",
    });
    if (!res.ok) throw new Error("Failed to cancel email job");
    return await res.json();
  },
};
