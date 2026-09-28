import { useState, useEffect } from "react";
import "./App.css";
import Login from "./pages/Login";
import Patients from "./pages/Patients";
import XRayAnalysis from "./pages/XRayAnalysis";
import MedicalReports from "./pages/MedicalReports";

import {
  getPatients,
  getReports,
   uploadXRay
} from "./api/api";


function App() {

  const [currentPage, setCurrentPage] =
  useState("dashboard");

  const [isAuthenticated, setIsAuthenticated] =
    useState(
      Boolean(
        localStorage.getItem("access_token")
      )
    );


  // ==============================
  // DASHBOARD DATA
  // ==============================

  const [patients, setPatients] = useState([]);
  const [reports, setReports] = useState([]);

  const [patientCount, setPatientCount] = useState(0);
  const [reportCount, setReportCount] = useState(0);

  const [loadingData, setLoadingData] = useState(true);
  const [apiError, setApiError] = useState("");

  // ==============================
// X-RAY UPLOAD
// ==============================

const [selectedFile, setSelectedFile] = useState(null);

const [selectedPatient, setSelectedPatient] =
  useState("");

const [uploading, setUploading] =
  useState(false);

const [predictionResult, setPredictionResult] =
  useState(null);

const [uploadError, setUploadError] =
  useState("");


 // ==============================
// LOAD DASHBOARD DATA
// ==============================

useEffect(() => {

  if (!isAuthenticated) {
    return;
  }

  async function loadDashboardData() {

    try {

      setLoadingData(true);
      setApiError("");

      const [
        patientsData,
        reportsData
      ] = await Promise.all([
        getPatients(),
        getReports()
      ]);

      console.log(
        "Patients API:",
        patientsData
      );

      console.log(
        "Reports API:",
        reportsData
      );

      setPatients(
        patientsData.patients || []
      );

      console.log(
        "Patients array:",
        patientsData.patients
      );

      setReports(
        reportsData.reports || []
      );

      setPatientCount(
        patientsData.total || 0
      );

      setReportCount(
        reportsData.total || 0
      );

    } catch (error) {

      console.error(
        "Dashboard API error:",
        error
      );

      setApiError(
        error.response?.data?.detail ||
        "Unable to load dashboard data."
      );

    } finally {

      setLoadingData(false);

    }

  }

  loadDashboardData();

}, [isAuthenticated]);
  // ==============================
// SELECT X-RAY
// ==============================

function handleFileChange(event) {

  const file = event.target.files?.[0];

  setUploadError("");
  setPredictionResult(null);

  if (!file) {
    setSelectedFile(null);
    return;
  }

  const allowedTypes = [
    "image/jpeg",
    "image/jpg",
    "image/png"
  ];

  if (!allowedTypes.includes(file.type)) {

    setUploadError(
      "Please select a JPG, JPEG or PNG image."
    );

    setSelectedFile(null);
    return;
  }

  setSelectedFile(file);
}


// ==============================
// UPLOAD + AI PREDICTION
// ==============================

async function handleAnalyzeXRay() {

  setUploadError("");
  setPredictionResult(null);

  if (!selectedPatient) {

    setUploadError(
      "Please select a patient first."
    );

    return;
  }

  if (!selectedFile) {

    setUploadError(
      "Please select an X-Ray image first."
    );

    return;
  }

  try {

    setUploading(true);

    const result = await uploadXRay(
      Number(selectedPatient),
      "X - Ray",
      selectedFile
    );

    console.log(
      "AI Prediction Result:",
      result
    );

    setPredictionResult(
      result.report
    );

    // Refresh reports
    const updatedReports =
      await getReports();

    setReports(
      updatedReports.reports || []
    );

    setReportCount(
      updatedReports.total || 0
    );

  } catch (error) {

    console.error(
      "X-Ray upload error:",
      error
    );

    setUploadError(
      error.response?.data?.detail ||
      "X-Ray analysis failed."
    );

  } finally {

    setUploading(false);

  }
}


  // ==============================
  // LOGIN
  // ==============================

  if (!isAuthenticated) {

    return (
      <Login
        onLogin={() => setIsAuthenticated(true)}
      />
    );

  }
  // ==============================
// X-RAY ANALYSIS PAGE
// ==============================

if (currentPage === "xray") {

  return (
    <XRayAnalysis />
  );

}

// ==============================
// MEDICAL REPORTS PAGE
// ==============================

if (currentPage === "reports") {

  return (
    <MedicalReports />
  );

}


    // ==============================
  // PATIENTS PAGE
  // ==============================

  if (currentPage === "patients") {

    return (
      <div className="app">

        {/* SIDEBAR */}

        <aside className="sidebar">

          <div className="brand">

            <div className="brand-icon">
              M
            </div>

            <div>

              <h1>MediVision</h1>

              <span>
                AI Healthcare
              </span>

            </div>

          </div>


          <nav className="navigation">

            <button
              className="nav-item"
              onClick={() =>
                setCurrentPage("dashboard")
              }
            >

              <span>
                ⌂
              </span>

              Dashboard

            </button>


            <button
              className="nav-item active"
            >

              <span>
                ♙
              </span>

              Patients

            </button>


           <button
  className={
    `nav-item ${
      currentPage === "xray"
        ? "active"
        : ""
    }`
  }
  onClick={() =>
    setCurrentPage("xray")
  }
>

  <span>
    ▣
  </span>

  X-Ray Analysis


            </button>


          <button
  className={
    `nav-item ${
      currentPage === "reports"
        ? "active"
        : ""
    }`
  }
  onClick={() =>
    setCurrentPage("reports")
  }
>

  <span>
    ▤
  </span>

  Medical Reports

</button>


            <button className="nav-item">

              <span>
                ⚙
              </span>

              Settings

            </button>

          </nav>


          <div className="sidebar-bottom">

            <div className="user-card">

              <div className="avatar">
                DR
              </div>

              <div>

                <strong>
                  Doctor
                </strong>

                <span>
                  Medical Staff
                </span>

              </div>

            </div>

          </div>

        </aside>


        {/* PATIENTS CONTENT */}

        <main className="main-content">

          <Patients />

        </main>

      </div>
    );

  }


  // ==============================
  // X-RAY COUNT
  // ==============================

 const xrayCount = reports.filter(
  (report) => {

    const type =
      report.report_type?.toLowerCase() || "";

    return (
      type.includes("x-ray") ||
      type.includes("xray") ||
      type.includes("x ray") ||
      type.includes("x - ray")
    );

  }
).length;


  // ==============================
  // DASHBOARD
  // ==============================

  return (

    <div className="app">


      {/* ================= SIDEBAR ================= */}

      <aside className="sidebar">


        <div className="brand">

          <div className="brand-icon">
            M
          </div>

          <div>

            <h1>MediVision</h1>

            <span>
              AI Healthcare
            </span>

          </div>

        </div>


        <nav className="navigation">

<button
  className={
    `nav-item ${
      currentPage === "dashboard"
        ? "active"
        : ""
    }`
  }
  onClick={() =>
    setCurrentPage("dashboard")
}
>
  <span>
    ⌂
  </span>

  Dashboard

</button>


       <button
  className={
    `nav-item ${
      currentPage === "patients"
        ? "active"
        : ""
    }`
  }
  onClick={() =>
    setCurrentPage("patients")
  }
>
  <span>♙</span>
  Patients
</button>

        <button
  className={
    `nav-item ${
      currentPage === "xray"
        ? "active"
        : ""
    }`
  }
  onClick={() =>
    setCurrentPage("xray")
  }
>

  <span>
    ▣
  </span>

  X-Ray Analysis

</button>


         <button
  className={
    `nav-item ${
      currentPage === "reports"
        ? "active"
        : ""
    }`
  }
  onClick={() =>
    setCurrentPage("reports")
  }
>

  <span>
    ▤
  </span>

  Medical Reports

</button>


          <button className="nav-item">

            <span>
              ⚙
            </span>

            Settings

          </button>


        </nav>


        <div className="sidebar-bottom">

          <div className="user-card">

            <div className="avatar">
              DR
            </div>

            <div>

              <strong>
                Doctor
              </strong>

              <span>
                Medical Staff
              </span>

            </div>

          </div>

        </div>


      </aside>


      {/* ================= MAIN CONTENT ================= */}

      <main className="main-content">


        {/* ================= HEADER ================= */}

        <header className="topbar">


          <div>

            <h2>
              Dashboard
            </h2>

            <p>
              Welcome back. Here's your healthcare overview.
            </p>

          </div>


          <div className="topbar-actions">


            <button className="notification">
              🔔
            </button>


            <div className="profile">


              <div className="avatar">
                DR
              </div>


              <div>

                <strong>
                  Doctor
                </strong>

                <span>
                  Administrator
                </span>

              </div>


            </div>


          </div>


        </header>


        {/* ================= API ERROR ================= */}

        {apiError && (

          <div className="medical-disclaimer">

            <strong>
              ⚠ API Notice
            </strong>

            <span>
              {apiError}
            </span>

          </div>

        )}


        {/* ================= STAT CARDS ================= */}

        <section className="stats-grid">


          {/* TOTAL PATIENTS */}

          <div className="stat-card">


            <div className="stat-icon patients-icon">
              ♙
            </div>


            <div>

              <span>
                Total Patients
              </span>


              <h3>

                {loadingData
                  ? "..."
                  : patientCount
                }

              </h3>


              <small>
                Database records
              </small>

            </div>


          </div>


          {/* MEDICAL REPORTS */}

          <div className="stat-card">


            <div className="stat-icon reports-icon">
              ▤
            </div>


            <div>

              <span>
                Medical Reports
              </span>


              <h3>

                {loadingData
                  ? "..."
                  : reportCount
                }

              </h3>


              <small>
                Database records
              </small>

            </div>


          </div>


          {/* X-RAY ANALYSES */}

          <div className="stat-card">


            <div className="stat-icon xray-icon">
              🩻
            </div>


            <div>

              <span>
                X-Ray Analyses
              </span>


              <h3>

                {loadingData
                  ? "..."
                  : xrayCount
                }

              </h3>


              <small>
                AI powered
              </small>

            </div>


          </div>


          {/* AI MODEL AUC */}

          <div className="stat-card">


            <div className="stat-icon accuracy-icon">
              ✓
            </div>


            <div>

              <span>
                AI Model AUC
              </span>


              <h3>
                96.6%
              </h3>


              <small>
                Current model
              </small>

            </div>


          </div>


        </section>


        {/* ================= MAIN GRID ================= */}

        <section className="dashboard-grid">


          {/* ================= AI ANALYSIS ================= */}

          <div className="panel analysis-panel">


            <div className="panel-header">


              <div>

                <h3>
                  AI X-Ray Analysis
                </h3>


                <p>
                  Analyze a chest X-ray using MediVision AI.
                </p>

              </div>


              <span className="status-badge">
                ● AI Online
              </span>


            </div>

<div className="upload-area">

  <div className="upload-icon">
    🩻
  </div>

  <h4>
    Upload Chest X-Ray
  </h4>

  <p>
    Upload a JPG, JPEG or PNG chest X-ray
    for AI analysis.
  </p>


  {/* ==============================
      PATIENT SELECTION
  ============================== */}

  <select
  value={selectedPatient}
  onChange={(event) => {
    setSelectedPatient(event.target.value);
  }}
  className="patient-select"
>
  <option value="">
    Select Patient
  </option>

  {patients.length > 0 ? (
    patients.map((patient) => (
      <option
        key={patient.id}
        value={String(patient.id)}
      >
        #{String(patient.id).padStart(3, "0")} - {patient.full_name}
      </option>
    ))
  ) : (
    <option value="" disabled>
      No patients available
    </option>
  )}
</select>

  {/* ==============================
      FILE SELECTION
  ============================== */}

  <label className="file-select-button">

    {selectedFile
      ? "Change X-Ray"
      : "Select X-Ray"
    }

    <input
      type="file"
      accept=".jpg,.jpeg,.png,image/jpeg,image/png"
      onChange={handleFileChange}
      hidden
    />

  </label>


  {/* SELECTED FILE */}

  {selectedFile && (

    <div className="selected-file">

      📄 {selectedFile.name}

    </div>

  )}


  {/* ERROR */}

  {uploadError && (

    <div className="upload-error">

      {uploadError}

    </div>

  )}


  {/* ==============================
      ANALYZE BUTTON
  ============================== */}

  <button
    className="primary-button"
    onClick={handleAnalyzeXRay}
    disabled={uploading}
  >

    {uploading
      ? "Analyzing X-Ray..."
      : "Analyze X-Ray"
    }

  </button>


  <small>
    AI prediction • Pneumonia screening
  </small>


  {/* ==============================
      RESULT
  ============================== */}

  {predictionResult && (

    <div
      className={
        predictionResult.prediction === "Pneumonia"
          ? "prediction-result pneumonia-result"
          : "prediction-result normal-result"
      }
    >

      <strong>
        AI Analysis Complete
      </strong>

      <span>
        Prediction:{" "}
        {predictionResult.prediction}
      </span>

      <span>
        Confidence:{" "}
        {predictionResult.confidence}%
      </span>

    </div>

  )}

</div>

</div>

          {/* ================= RECENT REPORTS ================= */}

          <div className="panel">


            <div className="panel-header">


              <div>

                <h3>
                  Recent Reports
                </h3>


                <p>
                  Latest patient analyses
                </p>

              </div>


              <button className="text-button">
                View All
              </button>


            </div>


            <div className="reports-list">


              {loadingData ? (

                <div className="report-item">

                  <div className="report-info">

                    <strong>
                      Loading reports...
                    </strong>

                    <span>
                      Please wait
                    </span>

                  </div>

                </div>

              ) : reports.length === 0 ? (

                <div className="report-item">

                  <div className="report-info">

                    <strong>
                      No reports found
                    </strong>

                    <span>
                      Upload an X-ray to begin analysis
                    </span>

                  </div>

                </div>

              ) : (

                reports
                  .slice(0, 5)
                  .map((report) => (

                    <div
                      className="report-item"
                      key={report.id}
                    >


                      <div className="report-avatar">

                        P{report.patient_id}

                      </div>


                      <div className="report-info">


                        <strong>

                          Patient #{String(
                            report.patient_id
                          ).padStart(3, "0")}

                        </strong>


                        <span>

                          {report.report_type}

                        </span>


                      </div>


                      <div
                        className={
                          report.prediction === "Pneumonia"
                            ? "report-result pneumonia"
                            : "report-result normal"
                        }
                      >

                        {report.prediction || "Pending"}

                      </div>


                    </div>

                  ))

              )}


            </div>


          </div>


        </section>


        {/* ================= DISCLAIMER ================= */}

        <div className="medical-disclaimer">


          <strong>
            ⚠ AI Analysis Notice
          </strong>


          <span>

            MediVision AI provides an automated research-support
            prediction and is not a confirmed medical diagnosis.
            Results should be reviewed by a qualified healthcare
            professional.

          </span>


        </div>


      </main>


    </div>

  );

}


export default App;