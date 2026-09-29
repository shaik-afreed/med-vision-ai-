import { useEffect, useState } from "react";
import {
  getPatients,
  uploadDocument,
  getDocuments,
  getDocumentFileUrl,
  getErrorMessage,
} from "../api/api";

function formatDate(value) {
  if (!value) return "—";

  try {
    return new Date(value).toLocaleString(undefined, {
      dateStyle: "medium",
      timeStyle: "short",
    });
  } catch {
    return value;
  }
}

function statusClass(status) {
  if (status === "High" || status === "Low") return "finding-status-flag";
  if (status === "Normal") return "finding-status-normal";
  return "finding-status-unknown";
}

/**
 * Displays a single analyzed document's summary, flagged lab findings and
 * raw extracted text. Shared between the "just analyzed" result and the
 * "view a past document" flow below, so the two never drift apart.
 */
function DocumentResult({ document, patientName }) {
  const [showRawText, setShowRawText] = useState(false);
  const [downloadError, setDownloadError] = useState("");

  if (!document) return null;

  async function handleDownloadOriginal() {
    setDownloadError("");
    try {
      const url = await getDocumentFileUrl(document.id);
      const link = window.document.createElement("a");
      link.href = url;
      link.download = document.file_name;
      link.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error("Document download error:", error);
      setDownloadError("Unable to download the original file.");
    }
  }

  return (
    <div className="document-result-panel">
      <div className="document-result-header">
        <strong>{document.file_name}</strong>
        {patientName && <span>Patient: {patientName}</span>}
        <span>Analyzed: {formatDate(document.created_at)}</span>
        <button type="button" className="text-button" onClick={handleDownloadOriginal}>
          Download original
        </button>
      </div>

      {downloadError && <div className="upload-error">{downloadError}</div>}

      {document.summary && (
        <div className="ai-result-explanation">
          <span className="ai-result-explanation-label">Summary</span>
          <p>{document.summary}</p>
        </div>
      )}

      {document.findings?.length > 0 && (
        <div className="document-findings">
          <span className="ai-result-explanation-label">
            Recognized lab values
          </span>
          <table className="document-findings-table">
            <thead>
              <tr>
                <th>Test</th>
                <th>Value</th>
                <th>Reference range</th>
                <th>Source</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {document.findings.map((finding, index) => (
                <tr key={index}>
                  <td data-label="Test">{finding.test}</td>
                  <td data-label="Value">
                    {finding.value}
                    {finding.unit ? ` ${finding.unit}` : ""}
                  </td>
                  <td data-label="Reference range">{finding.reference_range || "—"}</td>
                  <td data-label="Source">
                    {finding.reference_source === "report"
                      ? "This report"
                      : "General fallback"}
                  </td>
                  <td data-label="Status" className={statusClass(finding.status)}>
                    {finding.status}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="document-raw-text">
        <button
          type="button"
          className="text-button"
          onClick={() => setShowRawText((value) => !value)}
        >
          {showRawText ? "Hide extracted text" : "Show extracted text"}
        </button>

        {showRawText && (
          <pre className="document-raw-text-content">
            {document.raw_text || "(no text available)"}
          </pre>
        )}
      </div>

      <div className="ai-result-disclaimer">
        This is an automated text-extraction and reference-range check, not
        a clinical interpretation or diagnosis. A qualified healthcare
        professional should review the original document before any
        clinical decision is made.
      </div>
    </div>
  );
}

function DocumentAnalysis() {
  const [patients, setPatients] = useState([]);
  const [selectedPatient, setSelectedPatient] = useState("");
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [document, setDocument] = useState(null);
  const [uploadError, setUploadError] = useState("");

  const [pastDocuments, setPastDocuments] = useState([]);
  const [loadingPast, setLoadingPast] = useState(true);

  useEffect(() => {
    async function loadPatients() {
      try {
        const data = await getPatients();
        setPatients(data.patients || []);
      } catch (error) {
        console.error("Patients API error:", error);
        setUploadError(getErrorMessage(error, "Unable to load patients."));
      }
    }

    async function loadPastDocuments() {
      try {
        setLoadingPast(true);
        const data = await getDocuments();
        setPastDocuments(data.documents || []);
      } catch (error) {
        console.error("Documents API error:", error);
      } finally {
        setLoadingPast(false);
      }
    }

    loadPatients();
    loadPastDocuments();
  }, []);

  function handleFileChange(event) {
    const file = event.target.files?.[0];

    setUploadError("");
    setDocument(null);

    if (!file) {
      setSelectedFile(null);
      return;
    }

    const allowedTypes = ["application/pdf", "text/plain"];

    if (!allowedTypes.includes(file.type)) {
      setUploadError("Please select a PDF or plain text (.txt) file.");
      setSelectedFile(null);
      return;
    }

    setSelectedFile(file);
  }

  async function handleAnalyzeDocument() {
    setUploadError("");
    setDocument(null);

    if (!selectedPatient) {
      setUploadError("Please select a patient first.");
      return;
    }

    if (!selectedFile) {
      setUploadError("Please select a PDF or text medical report first.");
      return;
    }

    try {
      setUploading(true);

      const result = await uploadDocument(Number(selectedPatient), selectedFile);
      setDocument(result.document);
      setPastDocuments((previous) => [result.document, ...previous]);
    } catch (error) {
      console.error("Document upload error:", error);
      setUploadError(getErrorMessage(error, "Document analysis failed."));
    } finally {
      setUploading(false);
    }
  }

  function handleViewPastDocument(pastDocument) {
    setUploadError("");
    setDocument(pastDocument);
  }

  function getPatientName(patientId) {
    const patient = patients.find((item) => item.id === patientId);
    return patient?.full_name || `Patient #${String(patientId).padStart(3, "0")}`;
  }

  const selectedPatientName = patients.find(
    (patient) => String(patient.id) === selectedPatient
  )?.full_name;

  return (
    <>
      <section className="page-header">
        <div>
          <h2>Medical Report Analysis</h2>
          <p>
            Upload a written medical/lab report (PDF or text) to extract and
            flag its lab values.
          </p>
        </div>
        <span className="status-badge">● Analyzer Online</span>
      </section>

      <section className="panel analysis-panel">
        <div className="panel-header">
          <div>
            <h3>Analyze a Medical Report</h3>
            <p>
              Supports text-based PDF and .txt files. Scanned/image-only
              PDFs have no text layer to extract from (no OCR).
            </p>
          </div>
        </div>

        <div className="upload-area">
          <div className="upload-icon">📄</div>
          <h4>Upload Medical Report</h4>
          <p>Upload a PDF or plain text lab/medical report for analysis.</p>

          <select
            value={selectedPatient}
            onChange={(event) => setSelectedPatient(event.target.value)}
            className="patient-select"
          >
            <option value="">Select Patient</option>

            {patients.length > 0 ? (
              patients.map((patient) => (
                <option key={patient.id} value={String(patient.id)}>
                  #{String(patient.id).padStart(3, "0")} - {patient.full_name}
                </option>
              ))
            ) : (
              <option value="" disabled>
                No patients available
              </option>
            )}
          </select>

          <label className="file-select-button">
            {selectedFile ? "Change Report" : "Select Report"}
            <input
              type="file"
              accept=".pdf,.txt,application/pdf,text/plain"
              onChange={handleFileChange}
              hidden
            />
          </label>

          {selectedFile && <div className="selected-file">📄 {selectedFile.name}</div>}

          {uploadError && <div className="upload-error">{uploadError}</div>}

          <button
            className="primary-button"
            onClick={handleAnalyzeDocument}
            disabled={uploading}
          >
            {uploading ? "Analyzing Report..." : "Analyze Report"}
          </button>

          <small>Text extraction • Reference-range flagging</small>

          <DocumentResult document={document} patientName={selectedPatientName} />
        </div>
      </section>

      <section className="panel">
        <div className="panel-header">
          <div>
            <h3>Past Medical Reports</h3>
            <p>Previously analyzed PDF/text reports.</p>
          </div>
        </div>

        {loadingPast && <div className="empty-state">Loading reports...</div>}

        {!loadingPast && pastDocuments.length === 0 && (
          <div className="empty-state">No medical reports analyzed yet.</div>
        )}

        {!loadingPast && pastDocuments.length > 0 && (
          <div className="reports-list">
            {pastDocuments.map((pastDocument) => (
              <div className="report-item" key={pastDocument.id}>
                <div className="report-icon">📄</div>

                <div className="report-info">
                  <strong>{pastDocument.file_name}</strong>
                  <span>Patient: {getPatientName(pastDocument.patient_id)}</span>
                  <span>{formatDate(pastDocument.created_at)}</span>
                </div>

                <button
                  className="text-button"
                  onClick={() => handleViewPastDocument(pastDocument)}
                >
                  View Report
                </button>
              </div>
            ))}
          </div>
        )}
      </section>
    </>
  );
}

export default DocumentAnalysis;
