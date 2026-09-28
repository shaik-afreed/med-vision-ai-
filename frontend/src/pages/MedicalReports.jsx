import { useEffect, useState } from "react";
import axios from "axios";

const API_BASE_URL = "http://127.0.0.1:8000";

function MedicalReports() {

  const [reports, setReports] = useState([]);
  const [patients, setPatients] = useState([]);
  const [selectedReport, setSelectedReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [reportImage, setReportImage] = useState("");
  const [reportImageLoading, setReportImageLoading] = useState(false);

  function clearReportImage() {
    if (reportImage) {
      URL.revokeObjectURL(reportImage);
    }
    setReportImage("");
  }

  async function loadReports() {
    try {
      setLoading(true);
      setError("");
      const token =
        localStorage.getItem("access_token");
      const headers = {
        Authorization: `Bearer ${token}`
      };
      // ==============================
      // LOAD REPORTS
      // ==============================
      const reportsResponse = await axios.get(
        `${API_BASE_URL}/reports/`,
        {
          headers
        }
      );
      // ==============================
      // LOAD PATIENTS
      // ==============================
      const patientsResponse = await axios.get(
        `${API_BASE_URL}/patients/`,
        {
          headers
        }
      );
      setReports(
        reportsResponse.data.reports || []
      );
      setPatients(
        patientsResponse.data.patients || []
      );
    } catch (error) {
      console.error(
        "Reports API error:",
        error
      );
      setError(
        error.response?.data?.detail ||
        "Unable to load medical reports."
      );
    } finally {
      setLoading(false);
    }
  }


  useEffect(() => {

    loadReports();

  }, []);


  function getPatientName(patientId) {
    const patient =
      patients.find(
        (item) => item.id === patientId
      );
    return patient?.full_name ||
      `Patient #${String(patientId).padStart(3, "0")}`;
  }

  async function loadReportImage(report) {
    try {
      clearReportImage();
      const token =
        localStorage.getItem("access_token");
      const response = await axios.get(
        `${API_BASE_URL}/reports/${report.id}/image`,
        {
          headers: {
            Authorization: `Bearer ${token}`
          },
          responseType: "blob"
        }
      );
      const imageUrl =
        URL.createObjectURL(response.data);
      setReportImage(imageUrl);
    } catch (error) {
      console.error(
        "Report image error:",
        error
      );
      setReportImage("");
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


          <button className="nav-item">

            <span>
              ▣
            </span>

            X-Ray Analysis

          </button>


          <button className="nav-item active">

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
              Medical Reports
            </h2>

            <p>
              View patient medical reports and AI analysis results.
            </p>

          </div>


          <span className="status-badge">
            ● AI Online
          </span>

        </section>


        {/* ================= REPORTS ================= */}

        <section className="panel">

          <div className="panel-header">

            <div>

              <h3>
                All Medical Reports
              </h3>

              <p>
                Saved X-Ray analyses and medical records.
              </p>

            </div>


            <button
              className="text-button"
              onClick={loadReports}
            >
              Refresh
            </button>

          </div>


          {loading && (

            <div className="empty-state">
              Loading reports...
            </div>

          )}


          {error && (

            <div className="upload-error">
              {error}
            </div>

          )}


          {!loading &&
            !error &&
            reports.length === 0 && (

              <div className="empty-state">
                No medical reports found.
              </div>

            )}


          {!loading &&
            reports.length > 0 && (

              <div className="reports-list">

                {reports.map((report) => (

                  <div
                    className="report-item"
                    key={report.id}
                  >

                    <div className="report-icon">
                      🩻
                    </div>


                    <div className="report-info">

                      <strong>
                        {report.report_name}
                      </strong>

                    <span>
                     Patient: {getPatientName(report.patient_id)}
                     </span>

                      <span>
                        Type: {report.report_type}
                      </span>

                    </div>


                    <div
  className={
    `report-result ${
      report.prediction?.toLowerCase() === "pneumonia"
        ? "pneumonia"
        : report.prediction?.toLowerCase() === "normal"
          ? "normal"
          : "pending"
    }`
  }
>

  <strong>
    {report.prediction || "Pending"}
  </strong>

  {report.confidence !== null &&
   report.confidence !== undefined &&
   report.confidence !== "" ? (

    <span>
      Confidence: {report.confidence}%
    </span>

  ) : (

    <span>
      No AI confidence
    </span>

  )}

</div>

<button
  className="text-button"
  onClick={async () => {

  setSelectedReport(report);

  setReportImage("");

  await loadReportImage(report);

}}
>
  View Report
</button>
                  </div>

                ))}

              </div>

            )}

           {selectedReport && (
  <>
    <div className="report-image-section">

      <h3>
        X-Ray Image
      </h3>

      {reportImage ? (

        <img
          src={reportImage}
          alt={selectedReport.report_name}
          className="report-xray-image"
        />

      ) : (

        <p>
          Unable to load X-Ray image.
        </p>

      )}

    </div>

    <div className="report-details">

      <div className="panel-header">

        <div>

          <h3>
            Report Details
          </h3>

          <p>
            AI analysis information
          </p>

        </div>

        <button
          className="text-button"
          onClick={() => setSelectedReport(null)}
        >
          Close
        </button>

      </div>

      <div className="report-details-grid">

        <div>
          <span>Patient</span>
          <strong>
            {getPatientName(
              selectedReport.patient_id
            )}
          </strong>
        </div>

        <div>
          <span>Report Type</span>
          <strong>
            {selectedReport.report_type}
          </strong>
        </div>

        <div>
          <span>Report File</span>
          <strong>
            {selectedReport.report_name}
          </strong>
        </div>

        <div>
          <span>AI Prediction</span>
          <strong>
            {selectedReport.prediction || "Pending"}
          </strong>
        </div>

        <div>
          <span>Confidence</span>
          <strong>
            {selectedReport.confidence !== null &&
             selectedReport.confidence !== undefined &&
             selectedReport.confidence !== ""
              ? `${selectedReport.confidence}%`
              : "Not available"}
          </strong>
        </div>

        <div>
          <span>Report ID</span>
          <strong>
            #{selectedReport.id}
          </strong>
        </div>

      </div>
    </div>
  </>
)}

        </section>

      </main>

    </div>

  );

}


export default MedicalReports;