import { useEffect, useState } from "react";
import { getReports, getPatients, getReportImageUrl, updateReport } from "../api/api";
import ResultPanel from "../components/ResultPanel";

function MedicalReports() {
  const [reports, setReports] = useState([]);
  const [patients, setPatients] = useState([]);
  const [selectedReport, setSelectedReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [reportImage, setReportImage] = useState("");
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
      setError(error.response?.data?.detail || "Unable to load medical reports.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadReports();
  }, []);

  function getPatientName(patientId) {
    const patient = patients.find((item) => item.id === patientId);
    return patient?.full_name || `Patient #${String(patientId).padStart(3, "0")}`;
  }

  async function loadReportImage(report) {
    try {
      clearReportImage();
      const imageUrl = await getReportImageUrl(report.id);
      setReportImage(imageUrl);
    } catch (error) {
      console.error("Report image error:", error);
      setReportImage("");
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

  return (
    <>
      <section className="page-header">
        <div>
          <h2>Medical Reports</h2>
          <p>View patient medical reports and AI analysis results.</p>
        </div>
        <span className="status-badge">● AI Online</span>
      </section>

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

        {loading && <div className="empty-state">Loading reports...</div>}

        {error && <div className="upload-error">{error}</div>}

        {!loading && !error && reports.length === 0 && (
          <div className="empty-state">No medical reports found.</div>
        )}

        {!loading && reports.length > 0 && (
          <div className="reports-list">
            {reports.map((report) => (
              <div className="report-item" key={report.id}>
                <div className="report-icon">🩻</div>

                <div className="report-info">
                  <strong>{report.report_name}</strong>
                  <span>Patient: {getPatientName(report.patient_id)}</span>
                  <span>Type: {report.report_type}</span>
                </div>

                <div
                  className={`report-result ${
                    report.prediction?.toLowerCase() === "pneumonia"
                      ? "pneumonia"
                      : report.prediction?.toLowerCase() === "normal"
                        ? "normal"
                        : "pending"
                  }`}
                >
                  <strong>{report.prediction || "Pending"}</strong>
                  {report.confidence != null ? (
                    <span>Confidence: {report.confidence}%</span>
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
            ))}
          </div>
        )}

        {selectedReport && (
          <>
            <div className="report-image-section">
              <h3>X-Ray Image</h3>

              {reportImage ? (
                <img
                  src={reportImage}
                  alt={selectedReport.report_name}
                  className="report-xray-image"
                />
              ) : (
                <p>Unable to load X-Ray image.</p>
              )}
            </div>

            <div className="report-details">
              <div className="panel-header">
                <div>
                  <h3>Report Details</h3>
                  <p>AI analysis information</p>
                </div>
                <button className="text-button" onClick={() => setSelectedReport(null)}>
                  Close
                </button>
              </div>

              <ResultPanel
                report={selectedReport}
                patientName={getPatientName(selectedReport.patient_id)}
              />

              <div className="report-notes">
                <label>Clinical notes</label>
                <textarea
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
          </>
        )}
      </section>
    </>
  );
}

export default MedicalReports;
