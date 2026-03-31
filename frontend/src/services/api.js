const STORAGE_KEYS = {
  access: "jwt_token",
  refresh: "jwt_refresh",
  company: "company_id",
};

function resolveApiBase() {
  const envBase = (import.meta.env.VITE_API_URL || "").trim().replace(/\/$/, "");
  if (envBase) return envBase;
  if (typeof window !== "undefined") {
    const { protocol, hostname, port } = window.location;
    const isLocalHost =
      hostname === "localhost" ||
      hostname === "127.0.0.1" ||
      hostname === "0.0.0.0" ||
      /^10\.\d+\.\d+\.\d+$/.test(hostname) ||
      /^192\.168\.\d+\.\d+$/.test(hostname) ||
      /^172\.(1[6-9]|2\d|3[0-1])\.\d+\.\d+$/.test(hostname);

    if (isLocalHost && port !== "9000") {
      return `${protocol}//${hostname}:9000`;
    }
  }
  return "";
}

const API_BASE = resolveApiBase();

function buildQuery(params = {}) {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === "") return;
    if (Array.isArray(value)) {
      value.forEach((entry) => {
        if (entry !== undefined && entry !== null && entry !== "") {
          search.append(key, String(entry));
        }
      });
      return;
    }
    search.append(key, String(value));
  });
  const queryString = search.toString();
  return queryString ? `?${queryString}` : "";
}

function parseResponseBody(text) {
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch (error) {
    return text;
  }
}

function decodeBase64Url(value) {
  const padded = value.replace(/-/g, "+").replace(/_/g, "/");
  const normalized = padded + "=".repeat((4 - (padded.length % 4 || 4)) % 4);
  return atob(normalized);
}

export function decodeJwtPayload(token) {
  if (!token) return null;
  const parts = token.split(".");
  if (parts.length < 2) return null;
  try {
    return JSON.parse(decodeBase64Url(parts[1]));
  } catch (error) {
    return null;
  }
}

export function getSession() {
  const accessToken = localStorage.getItem(STORAGE_KEYS.access) || "";
  const refreshToken = localStorage.getItem(STORAGE_KEYS.refresh) || "";
  const companyId = localStorage.getItem(STORAGE_KEYS.company) || "";
  const claims = decodeJwtPayload(accessToken) || {};
  return {
    accessToken,
    refreshToken,
    companyId: companyId || String(claims.company_id || ""),
    claims,
  };
}

export function setSession({ access, refresh }) {
  const claims = decodeJwtPayload(access) || {};
  localStorage.setItem(STORAGE_KEYS.access, access || "");
  if (refresh) {
    localStorage.setItem(STORAGE_KEYS.refresh, refresh);
  }
  if (claims.company_id) {
    localStorage.setItem(STORAGE_KEYS.company, String(claims.company_id));
  } else {
    localStorage.removeItem(STORAGE_KEYS.company);
  }
}

export function clearSession() {
  Object.values(STORAGE_KEYS).forEach((key) => localStorage.removeItem(key));
}

export function normalizeList(payload) {
  if (Array.isArray(payload)) return payload;
  if (Array.isArray(payload?.results)) return payload.results;
  if (Array.isArray(payload?.items)) return payload.items;
  if (Array.isArray(payload?.data)) return payload.data;
  return [];
}

async function apiFetch(path, options = {}) {
  const session = getSession();
  const headers = {
    ...(options.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
    ...(options.headers || {}),
  };
  if (options.auth !== false && session.accessToken) {
    headers.Authorization = `Bearer ${session.accessToken}`;
  }
  if (session.companyId) {
    headers["X-Company-ID"] = session.companyId;
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
    body:
      options.body && !(options.body instanceof FormData) && typeof options.body !== "string"
        ? JSON.stringify(options.body)
        : options.body,
  });
  const text = await response.text();
  const payload = parseResponseBody(text);

  if (!response.ok) {
    const message =
      payload?.detail ||
      payload?.message ||
      (typeof payload === "string" ? payload : "") ||
      response.statusText ||
      `Request failed (${response.status})`;
    const error = new Error(message);
    error.status = response.status;
    error.payload = payload;
    throw error;
  }

  return payload;
}

export const Api = {
  baseUrl: API_BASE,
  getSession,
  setSession,
  clearSession,
  normalizeList,
  decodeJwtPayload,

  login: (credentials) =>
    apiFetch("/api/auth/token/", {
      method: "POST",
      auth: false,
      body: credentials,
    }),

  fetchMe: () => apiFetch("/api/v1/users/me/"),
  fetchSummaryReport: () => apiFetch("/api/v1/reports/summary/"),
  fetchLeadDashboard: (params = {}) => apiFetch(`/api/v1/leads/leads/dashboard_summary/${buildQuery(params)}`),
  fetchLeadMonitoring: (params = {}) => apiFetch(`/api/v1/leads/leads/monitoring/${buildQuery(params)}`),
  fetchLeadKanban: (params = {}) => apiFetch(`/api/v1/leads/leads/kanban/${buildQuery(params)}`),
  fetchLeads: (params = {}) => apiFetch(`/api/v1/leads/leads/${buildQuery(params)}`),
  createLead: (payload) =>
    apiFetch("/api/v1/leads/leads/", {
      method: "POST",
      body: payload,
    }),
  updateLeadStatus: (leadId, payload) =>
    apiFetch(`/api/v1/leads/leads/${leadId}/status/`, {
      method: "POST",
      body: payload,
    }),
  assignLead: (leadId, agent) =>
    apiFetch(`/api/v1/leads/leads/${leadId}/assign/`, {
      method: "POST",
      body: { agent },
    }),
  addLeadNote: (leadId, note) =>
    apiFetch(`/api/v1/leads/leads/${leadId}/add_note/`, {
      method: "POST",
      body: { note },
    }),
  contactLead: (leadId, payload) =>
    apiFetch(`/api/v1/leads/leads/${leadId}/contact/`, {
      method: "POST",
      body: payload,
    }),
  convertLead: (leadId, payload) =>
    apiFetch(`/api/v1/leads/leads/${leadId}/convert/`, {
      method: "POST",
      body: payload,
    }),
  fetchLeadTimeline: (leadId) => apiFetch(`/api/v1/leads/leads/${leadId}/timeline/`),
  bulkAssignLeads: (payload) =>
    apiFetch("/api/v1/leads/leads/bulk_assign/", {
      method: "POST",
      body: payload,
    }),
  importLeadsCsv: (formData) =>
    apiFetch("/api/v1/leads/leads/import_csv/", {
      method: "POST",
      body: formData,
    }),
  logLeadCall: (leadId, payload) =>
    apiFetch(`/api/v1/leads/leads/${leadId}/log_call/`, {
      method: "POST",
      body: payload,
    }),
  fetchLeadActivities: () => apiFetch("/api/v1/leads/lead-activities/"),
  fetchCurrentAssignments: () => apiFetch("/api/v1/leads/assignments/"),
  fetchLeadAssignments: () => apiFetch("/api/v1/leads/lead-assignments/"),
  fetchLeadSources: () => apiFetch("/api/v1/leads/sources/"),
  fetchLeadImportBatches: () => apiFetch("/api/v1/leads/import-batches/"),

  fetchProperties: (params = {}) => apiFetch(`/api/v1/leads/properties/${buildQuery(params)}`),
  createProperty: (payload) =>
    apiFetch("/api/v1/leads/properties/", {
      method: "POST",
      body: payload,
    }),
  approveProperty: (propertyId) =>
    apiFetch(`/api/v1/leads/properties/${propertyId}/approve/`, {
      method: "POST",
    }),
  rejectProperty: (propertyId) =>
    apiFetch(`/api/v1/leads/properties/${propertyId}/reject/`, {
      method: "POST",
    }),
  toggleWishlist: (propertyId) =>
    apiFetch(`/api/v1/leads/properties/${propertyId}/wishlist/`, {
      method: "POST",
    }),
  fetchWishlist: () => apiFetch("/api/v1/leads/properties/my_wishlist/"),
  compareProperties: (ids) => apiFetch(`/api/v1/leads/properties/compare/${buildQuery({ ids: ids.join(",") })}`),
  scheduleVisit: (propertyId, payload) =>
    apiFetch(`/api/v1/leads/properties/${propertyId}/schedule_visit/`, {
      method: "POST",
      body: payload,
    }),
  fetchBuilders: () => apiFetch("/api/v1/leads/builders/"),
  fetchProjects: () => apiFetch("/api/v1/leads/projects/"),

  fetchAgents: () => apiFetch("/api/v1/agents/agents/"),
  fetchAgentDashboard: () => apiFetch("/api/v1/agents/agents/dashboard/"),
  fetchCustomersDashboard: () => apiFetch("/api/v1/customers/customers/dashboard/"),
  fetchVisits: () => apiFetch("/api/v1/visits/visits/"),
  fetchCalls: () => apiFetch("/api/v1/crm/calls/"),
  fetchVoiceCalls: () => apiFetch("/api/v1/voice/calls/"),
  fetchDeals: () => apiFetch("/api/v1/deals/deals/"),
  fetchDealPayments: () => apiFetch("/api/v1/deals/payments/"),
  approveDealPayment: (paymentId) =>
    apiFetch(`/api/v1/deals/payments/${paymentId}/approve/`, {
      method: "POST",
    }),
  markDealPaymentPaid: (paymentId) =>
    apiFetch(`/api/v1/deals/payments/${paymentId}/mark_paid/`, {
      method: "POST",
    }),

  fetchWallets: () => apiFetch("/api/v1/wallet/wallets/"),
  fetchWalletTransactions: () => apiFetch("/api/v1/wallet/transactions/"),
  fetchWithdrawRequests: () => apiFetch("/api/v1/wallet/withdraw-requests/"),
  createWithdrawRequest: (payload) =>
    apiFetch("/api/v1/wallet/withdraw-requests/", {
      method: "POST",
      body: payload,
    }),

  fetchPlans: () => apiFetch("/api/v1/subscription/plans/"),
  fetchSubscriptions: () => apiFetch("/api/v1/subscription/subscriptions/"),
  subscribeToPlan: (plan) =>
    apiFetch("/api/v1/subscription/subscriptions/", {
      method: "POST",
      body: { plan },
    }),
  activateFreePlan: () =>
    apiFetch("/api/v1/subscription/subscriptions/free/", {
      method: "POST",
    }),

  fetchNotifications: () => apiFetch("/api/v1/notifications/notifications/"),
  markAllNotificationsRead: () =>
    apiFetch("/api/v1/notifications/notifications/mark_all_read/", {
      method: "POST",
    }),
  markNotificationRead: (notificationId) =>
    apiFetch(`/api/v1/notifications/notifications/${notificationId}/mark_read/`, {
      method: "POST",
    }),

  fetchIntelligenceDashboard: () => apiFetch("/api/v1/intelligence/dashboard/"),
  fetchAggregatedProperties: (params = {}) => apiFetch(`/api/v1/intelligence/aggregated-properties/${buildQuery(params)}`),
  fetchHeatmaps: (params = {}) => apiFetch(`/api/v1/intelligence/heatmaps/${buildQuery(params)}`),
  fetchPriceTrends: (params = {}) => apiFetch(`/api/v1/intelligence/price-trends/${buildQuery(params)}`),
  fetchInvestorMatches: (params = {}) => apiFetch(`/api/v1/intelligence/investor-matches/${buildQuery(params)}`),
  fetchAlerts: (params = {}) => apiFetch(`/api/v1/intelligence/alerts/${buildQuery(params)}`),
  fetchPremiumLeads: (params = {}) => apiFetch(`/api/v1/intelligence/premium-leads/${buildQuery(params)}`),
  fetchDocuments: (params = {}) => apiFetch(`/api/v1/intelligence/documents/${buildQuery(params)}`),
};
