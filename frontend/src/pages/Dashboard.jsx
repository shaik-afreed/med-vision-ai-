import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getPatients, getReports, getModelInfo, getErrorMessage } from "../api/api";

function xrayCountFrom(reports) {
  return reports.filter((report) => {
    const type = report.report_type?.toLowerCase() || "";
    return (
      type.includes("x-ray") ||
      type.includes("xray") ||
      type.includes("x ray") ||
      type.includes("x - ray")
    );
  }).length;
}

function Dashboard() {
  const [patientCount, setPatientCount] = useState(0);
  const [reportCount, setReportCount] = useState(0);
  const [reports, setReports] = useState([]);
  const [modelInfo, setModelInfo] = useState(null);

  const [loadingData, setLoadingData] = useState(true);
  const [apiError, setApiError] = useState("");

  useEffect(() => {
    async function loadDashboardData() {
      try {
        setLoadingData(true);
        setApiError("");

        const [patientsData, reportsData, modelInfoData] = await Promise.all([
          getPatients(),
          getReports(),
          getModelInfo().catch(() => null), // dashboard still works without it
        ]);

        setPatientCount(patientsData.total || 0);
        setReports(reportsData.reports || []);
        setReportCount(reportsData.total || 0);
        setModelInfo(modelInfoData);
      } catch (error) {
        console.error("Dashboard API error:", error);
        setApiError(getErrorMessage(error, "Unable to load dashboard data."));
      } finally {
        setLoadingData(false);
      }
    }

    loadDashboardData();
  }, []);

  const xrayCount = xrayCountFrom(reports);

  const aucDisplay =
    modelInfo?.evaluation_available && modelInfo.auc != null
      ? `${(modelInfo.auc * 100).toFixed(1)}%`
      : "N/A";

  return (
    <>
      <header className="topbar">
        <div>
          <h2>Dashboard</h2>
          <p>Welcome back. Here's your healthcare overview.</p>
        </div>

        <div className="topbar-actions">
          <button className="notification">🔔</button>
          <div className="profile">
            <div className="avatar">DR</div>
            <div>
              <strong>Doctor</strong>
              <span>Administrator</span>
            </div>
          </div>
        </div>
      </header>

      {apiError && (
        <div className="medical-disclaimer">
          <strong>⚠ API Notice</strong>
          <span>{apiError}</span>
        </div>
      )}

      <section className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon patients-icon">♙</div>
          <div>
            <span>Total Patients</span>
            <h3>{loadingData ? "..." : patientCount}</h3>
            <small>Database records</small>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon reports-icon">▤</div>
          <div>
            <span>Medical Reports</span>
            <h3>{loadingData ? "..." : reportCount}</h3>
            <small>Database records</small>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon xray-icon">🩻</div>
          <div>
            <span>X-Ray Analyses</span>
            <h3>{loadingData ? "..." : xrayCount}</h3>
            <small>AI powered</small>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon accuracy-icon">✓</div>
          <div>
            <span>AI Model AUC</span>
            <h3>{loadingData ? "..." : aucDisplay}</h3>
            <small>
              {modelInfo?.evaluation_available
                ? `On ${modelInfo.evaluated_on_images} held-out test images`
                : "Evaluation report not found"}
            </small>
          </div>
        </div>
      </section>

      <section className="dashboard-grid">
        <div className="panel analysis-panel">
          <div className="panel-header">
            <div>
              <h3>AI X-Ray Analysis</h3>
              <p>Run a screening on a new chest X-ray.</p>
            </div>
            <span className="status-badge">● AI Online</span>
          </div>

          <div className="upload-area">
            <div className="upload-icon">🩻</div>
            <h4>Analyze a Chest X-Ray</h4>
            <p>
              Upload a chest X-ray from the X-Ray Analysis page to run
              MediVision AI's pneumonia screening.
            </p>
            <Link to="/xray" className="primary-button" style={{ textDecoration: "none" }}>
              Go to X-Ray Analysis
            </Link>
          </div>
        </div>

        <div className="panel">
          <div className="panel-header">
            <div>
              <h3>Recent Reports</h3>
              <p>Latest patient analyses</p>
            </div>
            <Link to="/reports" className="text-button">
              View All
            </Link>
          </div>

          <div className="reports-list">
            {loadingData ? (
              <div className="report-item">
                <div className="report-info">
                  <strong>Loading reports...</strong>
                  <span>Please wait</span>
                </div>
              </div>
            ) : reports.length === 0 ? (
              <div className="report-item">
                <div className="report-info">
                  <strong>No reports found</strong>
                  <span>Upload an X-ray to begin analysis</span>
                </div>
              </div>
            ) : (
              reports.slice(0, 5).map((report) => (
                <div className="report-item" key={report.id}>
                  <div className="report-avatar">P{report.patient_id}</div>
                  <div className="report-info">
                    <strong>Patient #{String(report.patient_id).padStart(3, "0")}</strong>
                    <span>{report.report_type}</span>
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

      <div className="medical-disclaimer">
        <strong>⚠ AI Analysis Notice</strong>
        <span>
          MediVision AI provides an automated research-support prediction and
          is not a confirmed medical diagnosis. Results should be reviewed by
          a qualified healthcare professional.
        </span>
      </div>
    </>
  );
}

export default Dashboard;
