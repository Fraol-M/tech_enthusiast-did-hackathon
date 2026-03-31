const API_URL = import.meta.env.VITE_REFUPASS_API_URL || "http://localhost:8000";

async function request(path, { token, ...options } = {}) {
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let message = "Request failed";
    try {
      const payload = await response.json();
      message = payload.detail || payload.errorMessage || message;
    } catch (_error) {
      message = response.statusText || message;
    }
    throw new Error(message);
  }

  if (response.status === 204) {
    return null;
  }
  return response.json();
}

export const api = {
  login: (payload) =>
    request("/auth/login", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  getPlatformNgos: (token) => request("/platform/ngos", { token }),
  createPlatformNgo: (token, payload) =>
    request("/platform/ngos", {
      token,
      method: "POST",
      body: JSON.stringify(payload),
    }),
  getCurrentCycle: (token) => request("/aid-cycles/current", { token }),
  getAidWorkers: (token) => request("/aid-workers", { token }),
  createAidWorker: (token, payload) =>
    request("/aid-workers", {
      token,
      method: "POST",
      body: JSON.stringify(payload),
    }),
  getPeople: (token, search = "") =>
    request(`/people${search ? `?search=${encodeURIComponent(search)}` : ""}`, { token }),
  startIdentityVerification: (token, payload) =>
    request("/platform/identity-verifications", {
      token,
      method: "POST",
      body: JSON.stringify(payload),
    }),
  getIdentityVerification: (token, sessionToken) =>
    request(`/platform/identity-verifications/${sessionToken}`, { token }),
  getProgramEnrollments: (token, search = "") =>
    request(`/program-enrollments${search ? `?search=${encodeURIComponent(search)}` : ""}`, { token }),
  createProgramEnrollment: (token, payload) =>
    request("/program-enrollments", {
      token,
      method: "POST",
      body: JSON.stringify(payload),
    }),
  getProgramEnrollment: (token, id) => request(`/program-enrollments/${id}`, { token }),
  updateProgramEnrollmentEligibility: (token, id, payload) =>
    request(`/program-enrollments/${id}/eligibility`, {
      token,
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  createIssuanceSession: (token, programEnrollmentId) =>
    request("/issuance-sessions", {
      token,
      method: "POST",
      body: JSON.stringify({ programEnrollmentId }),
    }),
  getIssuanceSession: (token, sessionToken) =>
    request(`/issuance-sessions/${sessionToken}`, { token }),
  updateIssuanceSessionStatus: (token, sessionToken, status) =>
    request(`/issuance-sessions/${sessionToken}/status`, {
      token,
      method: "PATCH",
      body: JSON.stringify({ status }),
    }),
  verifyCredential: (token, payload) =>
    request("/worker/verify", {
      token,
      method: "POST",
      body: JSON.stringify(payload),
    }),
  redeem: (token, payload) =>
    request("/worker/redeem", {
      token,
      method: "POST",
      body: JSON.stringify(payload),
    }),
  getRedemptions: (token) => request("/redemptions", { token }),
  getGrievances: (token) => request("/grievances", { token }),
  createGrievance: (token, payload) =>
    request("/grievances", {
      token,
      method: "POST",
      body: JSON.stringify(payload),
    }),
};
