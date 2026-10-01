import { useEffect, useRef, useState } from "react";
import {
  getReports,
  getPatients,
  getReportImageUrl,
  updateReport,
  getErrorMessage,
} from "../api/api";
import ResultPanel from "../components/ResultPanel";
import PageHeader from "../components/PageHeader";
import Icon from "../components/Icon";
import { formatPercent } from "../utils/format";

function MedicalReports() {
  const [reports, setReports] = useState([]);
  const [patients, setPatients] = useState([]);
  const [selectedReport, setSelectedReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [reportImage, setReportImage] = useState("");
  const [reportImageFailed, setReportImageFailed] = useState(false);
  const detailRef = useRef(null);
  const [notesDraft, setNotesDraft] = useState("");
  const [savingNotes, setSavingNotes] = useState(false);

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

      const [reportsData, patientsData] = await Promise.all([
        getReports(),
        getPatients(),
      ]);

      setReports(reportsData.reports || []);
      setPatients(patientsData.patients || []);
    } catch (error) {
      console.error("Reports API error:", error);
      setError(getErrorMessage(error, "Unable to load medical reports."));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadReports();
  }, []);

  // The detail view opens below a long list; bring it into view.
  useEffect(() => {
    if (selectedReport) {
      detailRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [selectedReport?.id]);

  function getPatientName(patientId) {
    const patient = patients.find((item) => item.id === patientId);
    return patient?.full_name || `Patient #${String(patientId).padStart(3, "0")}`;
  }

  async function loadReportImage(report) {
    try {
      clearReportImage();
      setReportImageFailed(false);
      const imageUrl = await getReportImageUrl(report.id);
      setReportImage(imageUrl);
    } catch (error) {
      console.error("Report image error:", error);
      setReportImage("");
      setReportImageFailed(true);
    }
  }

  async function handleSaveNotes() {
    if (!selectedReport) return;

    try {
      setSavingNotes(true);
      const updated = await updateReport(selectedReport.id, { notes: notesDraft });
      setSelectedReport(updated);
      setReports((previous) =>
        previous.map((report) => (report.id === updated.id ? updated : report))
      );
    } catch (error) {
      console.error("Save notes error:", error);
    } finally {
      setSavingNotes(false);
    }
  }

  function toneOf(report) {
    if (["inconclusive", "outside_training_ages"].includes(report.assessment?.category)) return "borderline";
    const prediction = report.prediction?.toLowerCase();
    return prediction === "pneumonia" ? "pneumonia" : prediction === "normal" ? "normal" : "pending";
  }

  return (
    <>
      <PageHeader title="Medical Reports" subtitle="View patient medical reports and AI analysis results.">
        <span className="status-badge">
          <span className="status-dot" /> AI Online
        </span>
      </PageHeader>

      <section className="panel">
        <div className="panel-header">
          <div>
            <h3>All Medical Reports</h3>
            <p>Saved X-Ray analyses and medical records.</p>
          </div>
          <button className="text-button" onClick={loadReports}>
            Refresh
          </button>
        </div>

        {loading && (
          <div className="reports-list">
            {[0, 1, 2].map((key) => (
              <div className="report-item" key={key}>
                <span className="skeleton skeleton-avatar" />
                <div className="report-info">
                  <span className="skeleton skeleton-text" />
                  <span className="skeleton skeleton-text short" />
                </div>
              </div>
            ))}
          </div>
        )}

        {error && <div className="upload-error">{error}</div>}

        {!loading && !error && reports.length === 0 && (
          <div className="empty-state">
            <div className="empty-icon">
              <Icon name="folder" size={26} />
            </div>
            <h3>No medical reports found</h3>
            <p>Analyze an X-ray to create the first report.</p>
          </div>
        )}

        {!loading && reports.length > 0 && (
          <div className="reports-list">
            {reports.map((report) => {
              const tone = toneOf(report);
              return (
                <div
                  className={`report-item ${selectedReport?.id === report.id ? "selected" : ""}`}
                  key={report.id}
                >
                  <div className="report-icon">
                    <Icon name="scan" size={20} />
                  </div>

                  <div className="report-info">
                    <strong>{report.report_name}</strong>
                    <span>Patient: {getPatientName(report.patient_id)}</span>
                    <span>Type: {report.report_type}</span>
                  </div>

                  <div className={`report-result ${tone}`}>
                    <strong>{report.assessment?.category === "outside_training_ages"
                          ? "Unreliable for age"
                          : tone === "borderline"
                            ? "Inconclusive"
                            : report.prediction || "Pending"}</strong>
                    {report.confidence != null ? (
                      <span>Confidence: {formatPercent(report.confidence)}%</span>
                    ) : (
                      <span>No AI confidence</span>
                    )}
                  </div>

                  <button
                    className="text-button"
                    onClick={async () => {
                      setSelectedReport(report);
                      setNotesDraft(report.notes || "");
                      setReportImage("");
                      await loadReportImage(report);
                    }}
                  >
                    View Report
                  </button>
                </div>
              );
            })}
          </div>
        )}

        {selectedReport && (
          <div className="report-detail" ref={detailRef}>
            <div className="report-detail-header">
              <div>
                <h3>Report Details</h3>
                <p>AI analysis information</p>
              </div>
              <button className="secondary-button" onClick={() => setSelectedReport(null)}>
                Close
              </button>
            </div>

            <div className="report-detail-layout">
              <div className="report-image-section">
                <h4>X-Ray Image</h4>

                {reportImage ? (
                  <img
                    src={reportImage}
                    alt={selectedReport.report_name}
                    className="report-xray-image"
                  />
                ) : reportImageFailed ? (
                  <p className="ai-result-heatmap-unavailable">Unable to load the X-Ray image.</p>
                ) : (
                  <div className="skeleton skeleton-image" />
                )}
              </div>

              <div className="report-details">
                <ResultPanel
                  report={selectedReport}
                  patientName={getPatientName(selectedReport.patient_id)}
                />

                <div className="report-notes">
                  <label htmlFor="report-notes-input">Clinical notes</label>
                  <textarea
                    id="report-notes-input"
                    rows={3}
                    value={notesDraft}
                    onChange={(event) => setNotesDraft(event.target.value)}
                    placeholder="Add a note for this report..."
                  />
                  <button
                    className="secondary-button"
                    onClick={handleSaveNotes}
                    disabled={savingNotes}
                  >
                    {savingNotes ? "Saving..." : "Save Notes"}
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </section>
    </>
  );
}

export default MedicalReports;
