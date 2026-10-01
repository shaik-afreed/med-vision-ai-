import { useEffect, useRef, useState } from "react";
import {
  getPatients,
  uploadDocument,
  getDocuments,
  getDocumentFileUrl,
  getErrorMessage,
} from "../api/api";
import AiAssistant from "../components/AiAssistant";
import Dropzone from "../components/Dropzone";
import Icon from "../components/Icon";
import PageHeader from "../components/PageHeader";

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
  const resultRef = useRef(null);

  const [pastDocuments, setPastDocuments] = useState([]);
  const [loadingPast, setLoadingPast] = useState(true);

  // On narrow screens the result sits below the upload card, out of view.
  useEffect(() => {
    if (document && window.matchMedia("(max-width: 1180px)").matches) {
      resultRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [document]);

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

  function handleFile(file) {
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
      <PageHeader
        title="Medical Report Analysis"
        subtitle="Upload a written medical/lab report (PDF or text) to extract and flag its lab values."
      >
        <span className="status-badge">
          <span className="status-dot" /> Analyzer Online
        </span>
      </PageHeader>

      <div className="analysis-layout">
        <section className="panel analysis-panel">
          <div className="panel-header">
            <div>
              <h3>Analyze a Medical Report</h3>
              <p>Supports text-based PDF and .txt files. Scanned/image-only PDFs have no text layer to read.</p>
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="document-patient">Patient</label>
            <select
              id="document-patient"
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
          </div>

          <Dropzone
            accept=".pdf,.txt,application/pdf,text/plain"
            file={selectedFile}
            onFile={handleFile}
            icon="fileText"
            title="Upload Medical Report"
            changeTitle="Change Report"
            hint="Drag and drop, or click to browse. PDF or .txt."
          />

          {selectedFile && (
            <div className="selected-file">
              <Icon name="fileText" size={16} />
              {selectedFile.name}
            </div>
          )}

          {uploadError && (
            <div className="upload-error" role="alert">
              {uploadError}
            </div>
          )}

          <button
            className="primary-button button-block"
            onClick={handleAnalyzeDocument}
            disabled={uploading}
          >
            {uploading ? "Analyzing Report..." : "Analyze Report"}
          </button>

          <small className="panel-footnote">Text extraction and reference-range flagging.</small>
        </section>

        <section className="analysis-result" aria-live="polite" ref={resultRef}>
          {document ? (
            <DocumentResult document={document} patientName={selectedPatientName} />
          ) : uploading ? (
            <div className="result-placeholder">
              <span className="spinner" aria-hidden="true" />
              <h3>Reading the report</h3>
              <p>Extracting text and checking each value against its reference range.</p>
            </div>
          ) : (
            <div className="result-placeholder">
              <div className="empty-icon">
                <Icon name="sparkles" size={26} />
              </div>
              <h3>Your analysis will appear here</h3>
              <p>Upload a lab report and you will see:</p>
              <ul>
                <li>Every recognized value with its reference range</li>
                <li>Which values are low or high, and the source of the range</li>
                <li>A short summary and the extracted text</li>
              </ul>
            </div>
          )}
        </section>
      </div>

      <section className="panel">
        <div className="panel-header">
          <div>
            <h3>Past Medical Reports</h3>
            <p>Previously analyzed PDF/text reports.</p>
          </div>
        </div>

        {loadingPast && (
          <div className="reports-list">
            {[0, 1].map((key) => (
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

        {!loadingPast && pastDocuments.length === 0 && (
          <div className="empty-state">
            <div className="empty-icon">
              <Icon name="fileText" size={26} />
            </div>
            <h3>No medical reports analyzed yet</h3>
            <p>Upload a lab report above to get started.</p>
          </div>
        )}

        {!loadingPast && pastDocuments.length > 0 && (
          <div className="reports-list">
            {pastDocuments.map((pastDocument) => (
              <div
                className={`report-item ${document?.id === pastDocument.id ? "selected" : ""}`}
                key={pastDocument.id}
              >
                <div className="report-icon">
                  <Icon name="fileText" size={20} />
                </div>

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

      <AiAssistant mode="document" document={document} />
    </>
  );
}

export default DocumentAnalysis;
