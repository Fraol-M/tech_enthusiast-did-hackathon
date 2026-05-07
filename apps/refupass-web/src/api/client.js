const API_URL = import.meta.env.VITE_REFUPASS_API_URL || "http://localhost:8000";
export const AUTH_STORAGE_KEY = "refupass-session";
const AUTH_EVENT = "refupass-auth-changed";

let refreshPromise = null;

function emitAuthChange(session) {
  window.dispatchEvent(new CustomEvent(AUTH_EVENT, { detail: session }));
}

export function loadStoredSession() {
  try {
    return JSON.parse(window.localStorage.getItem(AUTH_STORAGE_KEY) || "null");
  } catch (_error) {
    return null;
  }
}

export function saveSession(session, { emit = true } = {}) {
  window.localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(session));
  if (emit) {
    emitAuthChange(session);
  }
}

export function clearSession({ emit = true } = {}) {
  window.localStorage.removeItem(AUTH_STORAGE_KEY);
  if (emit) {
    emitAuthChange(null);
  }
}

export function subscribeToAuthChanges(handler) {
  const listener = (event) => handler(event.detail);
  window.addEventListener(AUTH_EVENT, listener);
  return () => window.removeEventListener(AUTH_EVENT, listener);
}

async function parseError(response) {
  let message = "Request failed";
  try {
    const payload = await response.json();
    message = payload.detail || payload.errorMessage || message;
  } catch (_error) {
    message = response.statusText || message;
  }
  return message;
}

async function performRefresh(session) {
  const response = await fetch(`${API_URL}/auth/refresh`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ refreshToken: session.refreshToken }),
  });

  if (!response.ok) {
    throw new Error(await parseError(response));
  }

  const refreshed = await response.json();
  const nextSession = {
    ...session,
    ...refreshed,
  };
  saveSession(nextSession);
  return nextSession;
}

async function refreshSession(session) {
  if (!refreshPromise) {
    refreshPromise = performRefresh(session).finally(() => {
      refreshPromise = null;
    });
  }
  return refreshPromise;
}

async function request(path, { auth = true, token, ...options } = {}) {
  const headers = {
    ...(options.headers || {}),
  };
  if (!("Content-Type" in headers) && options.body && !(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  const storedSession = loadStoredSession();
  const bearerToken = auth ? storedSession?.accessToken || token : token;
  if (bearerToken) {
    headers.Authorization = `Bearer ${bearerToken}`;
  }

  let response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers,
  });

  if (response.status === 401 && auth) {
    const latestSession = loadStoredSession();
    if (!latestSession?.refreshToken) {
      clearSession();
      throw new Error("Session expired. Please sign in again.");
    }

    try {
      const refreshedSession = await refreshSession(latestSession);
      const retryHeaders = {
        ...headers,
        Authorization: `Bearer ${refreshedSession.accessToken}`,
      };
      response = await fetch(`${API_URL}${path}`, {
        ...options,
        headers: retryHeaders,
      });
    } catch (_error) {
      clearSession();
      throw new Error("Session expired. Please sign in again.");
    }
  }

  if (!response.ok) {
    throw new Error(await parseError(response));
  }

  if (response.status === 204) {
    return null;
  }
  return response.json();
}

export const api = {
  login: (payload) =>
    request("/auth/login", {
      auth: false,
      method: "POST",
      body: JSON.stringify(payload),
    }),
  refreshSession: (refreshToken) =>
    request("/auth/refresh", {
      auth: false,
      method: "POST",
      body: JSON.stringify({ refreshToken }),
    }),
  getPlatformNgos: (_token) => request("/platform/ngos"),
  createPlatformNgo: (_token, payload) =>
    request("/platform/ngos", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  getCurrentCycle: (_token) => request("/aid-cycles/current"),
  getAidWorkers: (_token) => request("/aid-workers"),
  createAidWorker: (_token, payload) =>
    request("/aid-workers", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  getPeople: (_token, search = "") =>
    request(`/people${search ? `?search=${encodeURIComponent(search)}` : ""}`),
  getPrograms: (_token) => request("/programs"),
  startIdentityVerification: (_token, payload) =>
    request("/platform/identity-verifications", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  getIdentityVerification: (_token, sessionToken) =>
    request(`/platform/identity-verifications/${sessionToken}`),
  getProgramEnrollments: (_token, search = "") =>
    request(`/program-enrollments${search ? `?search=${encodeURIComponent(search)}` : ""}`),
  createProgramEnrollment: (_token, payload) =>
    request("/program-enrollments", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  getProgramEnrollment: (_token, id) => request(`/program-enrollments/${id}`),
  updateProgramEnrollmentEligibility: (_token, id, payload) =>
    request(`/program-enrollments/${id}/eligibility`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  createIssuanceSession: (_token, programEnrollmentId) =>
    request("/issuance-sessions", {
      method: "POST",
      body: JSON.stringify({ programEnrollmentId }),
    }),
  getIssuanceSession: (_token, sessionToken) =>
    request(`/issuance-sessions/${sessionToken}`),
  getIssuancePass: (_token, sessionToken) =>
    request(`/issuance-sessions/${sessionToken}/pass`),
  updateIssuanceSessionStatus: (_token, sessionToken, status) =>
    request(`/issuance-sessions/${sessionToken}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    }),
  verifyCredential: (_token, payload) =>
    request("/worker/verify", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  redeem: (_token, payload) =>
    request("/worker/redeem", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  getRedemptions: (_token) => request("/redemptions"),
  getGrievances: (_token) => request("/grievances"),
  createGrievance: (_token, payload) =>
    request("/grievances", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};
