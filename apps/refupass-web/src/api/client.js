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
  getCurrentCycle: (token) => request("/aid-cycles/current", { token }),
  getBeneficiaries: (token, search = "") =>
    request(`/beneficiaries${search ? `?search=${encodeURIComponent(search)}` : ""}`, { token }),
  getBeneficiary: (token, id) => request(`/beneficiaries/${id}`, { token }),
  createBeneficiary: (token, payload) =>
    request("/beneficiaries", {
      token,
      method: "POST",
      body: JSON.stringify(payload),
    }),
  updateEligibility: (token, id, payload) =>
    request(`/beneficiaries/${id}/eligibility`, {
      token,
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  createIssuanceSession: (token, beneficiaryId) =>
    request("/issuance-sessions", {
      token,
      method: "POST",
      body: JSON.stringify({ beneficiaryId }),
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
