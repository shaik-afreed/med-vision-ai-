import { useEffect, useState } from "react";
import axios from "axios";

const API_BASE_URL = "http://127.0.0.1:8000";

function XRayAnalysis() {

  const [patients, setPatients] = useState([]);

  const [selectedPatient, setSelectedPatient] =
    useState("");

  const [selectedFile, setSelectedFile] =
    useState(null);

  const [uploading, setUploading] =
    useState(false);

  const [predictionResult, setPredictionResult] =
    useState(null);

  const [uploadError, setUploadError] =
    useState("");


  // ==============================
  // LOAD PATIENTS
  // ==============================

  async function loadPatients() {

    try {

      const token =
        localStorage.getItem("access_token");

      const response = await axios.get(
        `${API_BASE_URL}/patients/`,
        {
          headers: {
            Authorization:
              `Bearer ${token}`
          }
        }
      );

      setPatients(
        response.data.patients || []
      );

    } catch (error) {

      console.error(
        "Patients API error:",
        error
      );

      setUploadError(
        error.response?.data?.detail ||
        "Unable to load patients."
      );

    }
  }


  useEffect(() => {

    loadPatients();

  }, []);


  // ==============================
  // SELECT X-RAY
  // ==============================

  function handleFileChange(event) {

    const file =
      event.target.files?.[0];

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
  // ANALYZE X-RAY
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


      const token =
        localStorage.getItem("access_token");


      const formData =
        new FormData();


      formData.append(
        "patient_id",
        selectedPatient
      );


      formData.append(
        "report_type",
        "X - Ray"
      );


      formData.append(
        "file",
        selectedFile
      );


      const response =
        await axios.post(
          `${API_BASE_URL}/reports/upload`,
          formData,
          {
            headers: {
              Authorization:
                `Bearer ${token}`
            }
          }
        );


      console.log(
        "AI Prediction Result:",
        response.data
      );


      setPredictionResult(
        response.data.report
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


          {/* DASHBOARD */}

          <button
            className="nav-item"
            onClick={() =>
              window.location.href = "/"
            }
          >

            <span>
              ⌂
            </span>

            Dashboard

          </button>


          {/* PATIENTS */}

          <button
            className="nav-item"
            onClick={() =>
              window.location.href = "/"
            }
          >

            <span>
              ♙
            </span>

            Patients

          </button>


          {/* X-RAY */}

          <button
            className="nav-item active"
          >

            <span>
              ▣
            </span>

            X-Ray Analysis

          </button>


          <button className="nav-item">

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


        <section className="page-header">

          <div>

            <h2>
              X-Ray Analysis
            </h2>

            <p>
              Analyze a chest X-ray using MediVision AI.
            </p>

          </div>


          <span className="status-badge">
            ● AI Online
          </span>

        </section>


        {/* ================= AI ANALYSIS PANEL ================= */}

        <section className="panel analysis-panel">


          <div className="panel-header">

            <div>

              <h3>
                AI X-Ray Analysis
              </h3>

              <p>
                Upload a chest X-ray for AI-powered pneumonia screening.
              </p>

            </div>

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


            {/* PATIENT */}

            <select
              value={selectedPatient}
              onChange={(event) =>
                setSelectedPatient(
                  event.target.value
                )
              }
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

                    #{String(patient.id).padStart(3, "0")}
                    {" - "}
                    {patient.full_name}

                  </option>

                ))

              ) : (

                <option
                  value=""
                  disabled
                >
                  No patients available
                </option>

              )}

            </select>


            {/* FILE */}

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


            {/* ANALYZE */}

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


            {/* RESULT */}

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

        </section>


      </main>

    </div>

  );

}


export default XRayAnalysis;