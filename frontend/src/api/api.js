import axios from "axios";

// Set VITE_API_BASE_URL at build time (e.g. in Vercel's project settings) to
// the deployed backend URL. A pasted trailing slash is stripped so request
// paths don't become "//patients".
const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000").replace(
  /\/+$/,
  ""
);

const api = axios.create({
  baseURL: API_BASE_URL,
});

// ========================================
// AUTHENTICATED REQUEST
// ========================================

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");

  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  return config;
});

// ========================================
// AUTO-LOGOUT ON EXPIRED/INVALID TOKEN
// ========================================
// A single place for this instead of every page handling 401 itself.
// AuthContext listens for this event to clear state and redirect.

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("access_token");
      window.dispatchEvent(new Event("medivision:unauthorized"));
    }

    return Promise.reject(error);
  }
);

// ========================================
// USER-FACING ERROR MESSAGES
// ========================================
// No `response` means the request never reached the backend (server not
// running, wrong URL, network down) - say that instead of a vague failure.
// FastAPI's `detail` is a string for most errors but a list of objects for
// validation (422) errors; rendering that list directly would crash React.

export function getErrorMessage(error, fallback) {
  if (error?.code === "ECONNABORTED") {
    return "The server took too long to respond. It may be waking up - please try again in a moment.";
  }

  if (!error?.response) {
    return `Cannot reach the MediVision server at ${API_BASE_URL}. Make sure the backend is running, then try again.`;
  }

  const detail = error.response.data?.detail;

  if (typeof detail === "string" && detail) return detail;
  if (Array.isArray(detail) && detail[0]?.msg) return detail[0].msg;

  return fallback;
}

// ========================================
// SERVER WAKE-UP
// ========================================
// Free hosting puts an idle backend to sleep; the first request then waits
// for it to start. The sign-in page pings /health as soon as it opens so the
// server is already waking while the user types their credentials.

export async function pingServer() {
  const response = await fetch(`${API_BASE_URL}/health`, { cache: "no-store" });
  if (!response.ok) throw new Error(`Health check returned ${response.status}`);
}

// Starts loading the AI model on the server in the background so the first
// X-ray analysis doesn't wait for it. Fire-and-forget.
export async function warmUpModel() {
  await api.post("/model/warmup");
}

// ========================================
// AUTH
// ========================================

// A sleeping free-tier backend can need about a minute on the first request.
const AUTH_TIMEOUT_MS = 120000;

export async function loginUser(email, password) {
  const formData = new URLSearchParams();
  formData.append("username", email);
  formData.append("password", password);

  const response = await api.post("/auth/login", formData, {
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    timeout: AUTH_TIMEOUT_MS,
  });

  return response.data;
}

export async function registerUser(name, email, password) {
  const response = await api.post(
    "/auth/register",
    { name, email, password },
    { timeout: AUTH_TIMEOUT_MS }
  );
  return response.data;
}

export async function getProfile() {
  const response = await api.get("/auth/profile");
  return response.data;
}

// ========================================
// PATIENTS
// ========================================

export async function getPatients() {
  const response = await api.get("/patients/");
  return response.data;
}

export async function createPatient(patient) {
  const response = await api.post("/patients/", patient);
  return response.data;
}

export async function updatePatient(patientId, patient) {
  const response = await api.put(`/patients/${patientId}`, patient);
  return response.data;
}

export async function deletePatient(patientId) {
  const response = await api.delete(`/patients/${patientId}`);
  return response.data;
}

// ========================================
// X-RAY UPLOAD + AI ANALYSIS
// ========================================

export async function uploadXRay(patientId, reportType, file) {
  const formData = new FormData();
  formData.append("patient_id", patientId);
  formData.append("report_type", reportType);
  formData.append("file", file);

  const response = await api.post("/reports/upload", formData);
  return response.data;
}

// ========================================
// REPORTS
// ========================================

export async function getReports() {
  const response = await api.get("/reports/");
  return response.data;
}

export async function getReportImageUrl(reportId) {
  const response = await api.get(`/reports/${reportId}/image`, {
    responseType: "blob",
  });
  return URL.createObjectURL(response.data);
}

export async function getReportGradcamUrl(reportId) {
  const response = await api.get(`/reports/${reportId}/gradcam`, {
    responseType: "blob",
  });
  return URL.createObjectURL(response.data);
}

export async function downloadReportPdf(reportId, fileName) {
  const response = await api.get(`/reports/${reportId}/pdf`, { responseType: "blob" });
  const url = URL.createObjectURL(response.data);
  const link = window.document.createElement("a");
  link.href = url;
  link.download = fileName || `MediVision-report-${reportId}.pdf`;
  link.click();
  URL.revokeObjectURL(url);
}

export async function updateReport(reportId, payload) {
  const response = await api.patch(`/reports/${reportId}`, payload);
  return response.data;
}

// ========================================
// WRITTEN MEDICAL REPORT (PDF/TEXT) ANALYSIS
// ========================================

export async function uploadDocument(patientId, file) {
  const formData = new FormData();
  formData.append("patient_id", patientId);
  formData.append("file", file);

  const response = await api.post("/documents/upload", formData);
  return response.data;
}

export async function getDocuments() {
  const response = await api.get("/documents/");
  return response.data;
}

export async function updateDocument(documentId, payload) {
  const response = await api.patch(`/documents/${documentId}`, payload);
  return response.data;
}

export async function getDocumentFileUrl(documentId) {
  const response = await api.get(`/documents/${documentId}/file`, {
    responseType: "blob",
  });
  return URL.createObjectURL(response.data);
}

// ========================================
// AI ASSISTANT (X-ray results and lab reports)
// ========================================
// The browser only talks to our backend, which picks the model (hosted,
// local, or built-in answers) and sends it only the result's data.

export async function getChatStatus() {
  const response = await api.get("/chat/status");
  return response.data;
}

export async function sendChatMessage({ reportId = null, documentId = null }, messages) {
  const response = await api.post("/chat", {
    report_id: reportId ?? null,
    document_id: documentId ?? null,
    messages,
  });
  return response.data;
}

// AI Doctor: general guidance for everyday health concerns. A plain
// conversation; no patient record or report is attached.
export async function sendHealthMessage(messages) {
  const response = await api.post("/chat/health", { messages });
  return response.data;
}

// ========================================
// MODEL INFO
// ========================================

export async function getModelInfo() {
  const response = await api.get("/model/info");
  return response.data;
}

export default api;
