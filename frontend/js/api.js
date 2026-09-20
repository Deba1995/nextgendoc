// API Client for DocuNext Backend with Access Key Authentication

let authToken = localStorage.getItem("docunext_token") || sessionStorage.getItem("docunext_token") || "";
let onUnauthorizedCallback = null;

export function setUnauthorizedHandler(fn) {
  onUnauthorizedCallback = fn;
}

export function getAuthToken() {
  return authToken || localStorage.getItem("docunext_token") || sessionStorage.getItem("docunext_token") || "";
}

export function setAuthToken(token, remember = true) {
  authToken = token || "";
  if (token) {
    if (remember) {
      localStorage.setItem("docunext_token", token);
    } else {
      sessionStorage.setItem("docunext_token", token);
    }
  } else {
    localStorage.removeItem("docunext_token");
    sessionStorage.removeItem("docunext_token");
  }
}

export function clearAuthToken() {
  authToken = "";
  localStorage.removeItem("docunext_token");
  sessionStorage.removeItem("docunext_token");
}

async function authFetch(url, options = {}) {
  const token = getAuthToken();
  const headers = new Headers(options.headers || {});
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
    headers.set("X-Access-Token", token);
  }

  const res = await fetch(url, { ...options, headers });
  if (res.status === 401) {
    clearAuthToken();
    if (typeof onUnauthorizedCallback === "function") {
      onUnauthorizedCallback();
    }
  }
  return res;
}

export const api = {
  getAuthToken,
  setAuthToken,
  clearAuthToken,

  getDownloadUrl(basePath) {
    const token = getAuthToken();
    if (!token) return basePath;
    const separator = basePath.includes("?") ? "&" : "?";
    return `${basePath}${separator}token=${encodeURIComponent(token)}`;
  },

  async getAuthStatus() {
    const res = await fetch("/api/auth/status");
    if (!res.ok) return { auth_required: false };
    return await res.json();
  },

  async login(accessKey) {
    const res = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ access_key: accessKey }),
    });
    const data = await res.json().catch(() => ({ success: false, detail: "Login request failed" }));
    if (res.ok && data.token) {
      setAuthToken(data.token, true);
    }
    return { ok: res.ok, status: res.status, ...data };
  },

  async logout() {
    clearAuthToken();
    try {
      await fetch("/api/auth/logout", { method: "POST" });
    } catch (_) {}
    return { success: true };
  },

  async uploadTemplate(file) {
    const fd = new FormData();
    fd.append("file", file);
    const res = await authFetch("/api/upload/template", { method: "POST", body: fd });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Upload failed" }));
      throw new Error(err.detail || "Failed to upload template");
    }
    return await res.json();
  },

  async uploadData(file) {
    const fd = new FormData();
    fd.append("file", file);
    const res = await authFetch("/api/upload/data", { method: "POST", body: fd });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Upload failed" }));
      throw new Error(err.detail || "Failed to upload spreadsheet");
    }
    return await res.json();
  },

  async autoMatch(templateFields, spreadsheetHeaders) {
    const res = await authFetch("/api/automatch", {
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
    const res = await authFetch("/api/preview/sample", {
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
    const res = await authFetch("/api/projects/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, project_data: projectData }),
    });
    if (!res.ok) throw new Error("Failed to save project");
    return await res.json();
  },

  async listProjects() {
    const res = await authFetch("/api/projects/list");
    if (!res.ok) throw new Error("Failed to list projects");
    return await res.json();
  },

  async loadProject(name) {
    const res = await authFetch(`/api/projects/${encodeURIComponent(name)}`);
    if (!res.ok) throw new Error("Failed to load project");
    return await res.json();
  },

  async startGeneration(templateId, dataId, fields, filenamePattern, pageNum = 0, rowStart = 0, rowLimit = null) {
    const res = await authFetch("/api/generate", {
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
    const res = await authFetch(`/api/jobs/${encodeURIComponent(jobId)}/status`);
    if (!res.ok) throw new Error("Failed to fetch job status");
    return await res.json();
  },

  async getJobFiles(jobId) {
    const res = await authFetch(`/api/jobs/${encodeURIComponent(jobId)}/files`);
    if (!res.ok) throw new Error("Failed to fetch generated files");
    return await res.json();
  },

  async loadDemoSample(type = "flat", rowCount = 50) {
    const res = await authFetch(`/api/sample/load?sample_type=${encodeURIComponent(type)}&row_count=${rowCount}`, {
      method: "POST",
    });
    if (!res.ok) throw new Error("Failed to load sample assets");
    return await res.json();
  },

  async testSmtp(smtpConfig) {
    const res = await authFetch("/api/email/test-connection", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(smtpConfig),
    });
    if (!res.ok) throw new Error("Failed to connect to SMTP server");
    return await res.json();
  },

  async startEmailBatch(payload) {
    const res = await authFetch("/api/email/send-batch", {
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
    const res = await authFetch(`/api/email/status/${encodeURIComponent(jobId)}`);
    if (!res.ok) throw new Error("Failed to fetch email job status");
    return await res.json();
  },

  async getEmailReport(jobId) {
    const res = await authFetch(`/api/email/report/${encodeURIComponent(jobId)}`);
    if (!res.ok) return null;
    return await res.json();
  },

  async cancelEmailJob(jobId) {
    const res = await authFetch(`/api/email/cancel/${encodeURIComponent(jobId)}`, {
      method: "POST",
    });
    if (!res.ok) throw new Error("Failed to cancel email job");
    return await res.json();
  },
};
