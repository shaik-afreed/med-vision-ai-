import axios from "axios";

const API_BASE_URL = "http://127.0.0.1:8000";

const api = axios.create({
  baseURL: API_BASE_URL,
});


// ========================================
// LOGIN
// ========================================

export async function loginUser(email, password) {

  const formData = new URLSearchParams();

  formData.append("username", email);
  formData.append("password", password);

  const response = await api.post(
    "/auth/login",
    formData,
    {
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
    }
  );

  return response.data;
}


// ========================================
// REGISTER
// ========================================

export async function registerUser(
  name,
  email,
  password
) {

  const response = await api.post(
    "/auth/register",
    {
      name,
      email,
      password,
    }
  );

  return response.data;
}


// ========================================
// AUTHENTICATED API REQUEST
// ========================================

api.interceptors.request.use(
  (config) => {

    const token = localStorage.getItem(
      "access_token"
    );

    if (token) {

      config.headers.Authorization =
        `Bearer ${token}`;

    }

    return config;
  }
);


// ========================================
// UPLOAD X-RAY + AI ANALYSIS
// ========================================

export async function uploadXRay(
  patientId,
  reportType,
  file
) {

  const formData = new FormData();

  formData.append(
    "patient_id",
    patientId
  );

  formData.append(
    "report_type",
    reportType
  );

  formData.append(
    "file",
    file
  );

  const response = await api.post(
    "/reports/upload",
    formData
  );

  return response.data;
}


// ========================================
// GET PATIENTS
// ========================================

export async function getPatients() {

  const response = await api.get(
    "/patients/"
  );

  return response.data;
}


// ========================================
// GET REPORTS
// ========================================

export async function getReports() {

  const response = await api.get(
    "/reports/"
  );

  return response.data;
}


export default api;