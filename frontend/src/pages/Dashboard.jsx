import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { getPatients, getReports, getModelInfo, getErrorMessage } from "../api/api";
import { useAuth } from "../context/AuthContext";
import Icon from "../components/Icon";
import PageHeader from "../components/PageHeader";

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

function greeting() {
  const hour = new Date().getHours();
  if (hour < 12) return "Good morning";
  if (hour < 18) return "Good afternoon";
  return "Good evening";
}

function firstName(name) {
  if (!name) return "";
  const withoutTitle = name.replace(/^dr\.?\s+/i, "").trim();
  return `${/^dr\.?\s+/i.test(name) ? "Dr. " : ""}${withoutTitle.split(/\s+/)[0]}`;
}

function formatShortDate(value) {
  if (!value) return "";
  try {
    return new Date(value).toLocaleDateString(undefined, { month: "short", day: "numeric" });
  } catch {
    return "";
  }
}

function resultTone(report) {
  if (["inconclusive", "outside_training_ages", "unlike_training_images"].includes(report.assessment?.category)) return "borderline";
  return report.prediction === "Pneumonia" ? "pneumonia" : "normal";
}

function Dashboard() {
  const { user } = useAuth();

  const [patients, setPatients] = useState([]);
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

        setPatients(patientsData.patients || []);
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

  const patientNames = useMemo(
    () => Object.fromEntries(patients.map((patient) => [patient.id, patient.full_name])),
    [patients]
  );

  const xrayCount = xrayCountFrom(reports);

  const aucDisplay =
    modelInfo?.evaluation_available && modelInfo.auc != null
      ? `${(modelInfo.auc * 100).toFixed(1)}%`
      : "N/A";

  const value = (content) => (loadingData ? <span className="skeleton skeleton-text" /> : content);

  return (
    <>
      <PageHeader title="Dashboard" subtitle="Welcome back. Here's your healthcare overview.">
        <span className="status-badge">
          <span className="status-dot" /> AI Online
        </span>
      </PageHeader>

      {apiError && (
        <div className="api-error" role="alert">
          <Icon name="alert" size={18} />
          <span>{apiError}</span>
        </div>
      )}

      <section className="hero-card">
        <div className="hero-copy">
          <span className="hero-eyebrow">
            <Icon name="sparkles" size={14} /> AI-assisted screening
          </span>
          <h3>
            {greeting()}
            {user?.name ? `, ${firstName(user.name)}` : ""}.
          </h3>
          <p>
            Analyze a chest X-ray or a lab report and get an explained, reviewable result in seconds.
          </p>
          <div className="hero-actions">
            <Link to="/xray" className="hero-button hero-button-primary">
              <Icon name="scan" size={18} /> Analyze X-ray
            </Link>
            <Link to="/documents" className="hero-button hero-button-ghost">
              <Icon name="fileText" size={18} /> Analyze lab report
            </Link>
          </div>
        </div>

        <svg className="hero-pulse" viewBox="0 0 320 120" fill="none" aria-hidden="true">
          <path
            d="M0 70h60l16-34 22 70 20-58 14 22h52l18-26 18 26h100"
            stroke="currentColor"
            strokeWidth="3"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </section>

      <section className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon patients-icon">
            <Icon name="users" size={22} />
          </div>
          <div className="stat-body">
            <span>Total Patients</span>
            <h3>{value(patients.length)}</h3>
            <small>Registered records</small>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon reports-icon">
            <Icon name="folder" size={22} />
          </div>
          <div className="stat-body">
            <span>Medical Reports</span>
            <h3>{value(reportCount)}</h3>
            <small>Saved analyses</small>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon xray-icon">
            <Icon name="scan" size={22} />
          </div>
          <div className="stat-body">
            <span>X-Ray Analyses</span>
            <h3>{value(xrayCount)}</h3>
            <small>AI powered</small>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon accuracy-icon">
            <Icon name="activity" size={22} />
          </div>
          <div className="stat-body">
            <span>AI Model AUC</span>
            <h3>{value(aucDisplay)}</h3>
            <small>
              {modelInfo?.evaluation_available
                ? `On ${modelInfo.evaluated_on_images} held-out test images`
                : "Evaluation report not found"}
            </small>
          </div>
        </div>
      </section>

      <section className="dashboard-grid">
        <div className="panel">
          <div className="panel-header">
            <div>
              <h3>Recent Reports</h3>
              <p>Latest patient analyses</p>
            </div>
            <Link to="/reports" className="text-button">
              View All <Icon name="arrowRight" size={15} />
            </Link>
          </div>

          <div className="reports-list">
            {loadingData ? (
              [0, 1, 2].map((key) => (
                <div className="report-item" key={key}>
                  <span className="skeleton skeleton-avatar" />
                  <div className="report-info">
                    <span className="skeleton skeleton-text" />
                    <span className="skeleton skeleton-text short" />
                  </div>
                </div>
              ))
            ) : reports.length === 0 ? (
              <div className="empty-state">
                <div className="empty-icon">
                  <Icon name="scan" size={26} />
                </div>
                <h3>No reports yet</h3>
                <p>Upload an X-ray to begin analysis.</p>
                <Link to="/xray" className="primary-button">
                  Analyze X-ray
                </Link>
              </div>
            ) : (
              reports.slice(0, 5).map((report) => {
                const name = patientNames[report.patient_id];
                const tone = resultTone(report);
                return (
                  <div className="report-item" key={report.id}>
                    <div className="report-avatar">
                      {(name || `P${report.patient_id}`).slice(0, 2).toUpperCase()}
                    </div>
                    <div className="report-info">
                      <strong>{name || `Patient #${String(report.patient_id).padStart(3, "0")}`}</strong>
                      <span>
                        {report.report_type} · {formatShortDate(report.created_at)}
                      </span>
                    </div>
                    <div className={`report-result ${tone}`}>
                      <strong>
                        {["outside_training_ages", "unlike_training_images"].includes(report.assessment?.category)
                          ? "Unreliable result"
                          : tone === "borderline"
                            ? "Inconclusive"
                            : report.prediction || "Pending"}
                      </strong>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        <div className="panel how-panel">
          <div className="panel-header">
            <div>
              <h3>How it works</h3>
              <p>Three steps to a reviewable result</p>
            </div>
          </div>

          <ol className="how-steps">
            <li>
              <span className="how-number">1</span>
              <div>
                <strong>Upload</strong>
                <p>Add a chest X-ray for a patient, or a lab report in PDF or text.</p>
              </div>
            </li>
            <li>
              <span className="how-number">2</span>
              <div>
                <strong>Understand</strong>
                <p>See the probability on a scale, the heatmap and what the score has meant before.</p>
              </div>
            </li>
            <li>
              <span className="how-number">3</span>
              <div>
                <strong>Review and report</strong>
                <p>Download a report with a section for the clinician to sign off.</p>
              </div>
            </li>
          </ol>
        </div>
      </section>

      <div className="medical-disclaimer">
        <Icon name="info" size={18} />
        <span>
          <strong>AI analysis notice.</strong> MediVision AI provides an automated research-support prediction and
          is not a confirmed medical diagnosis. Results should be reviewed by a qualified healthcare professional.
        </span>
      </div>
    </>
  );
}

export default Dashboard;
