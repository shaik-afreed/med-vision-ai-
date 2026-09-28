import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

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
// AUTH
// ========================================

export async function loginUser(email, password) {
  const formData = new URLSearchParams();
  formData.append("username", email);
  formData.append("password", password);

  const response = await api.post("/auth/login", formData, {
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
  });

  return response.data;
}

export async function registerUser(name, email, password) {
  const response = await api.post("/auth/register", { name, email, password });
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

export async function updateReport(reportId, payload) {
  const response = await api.patch(`/reports/${reportId}`, payload);
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
