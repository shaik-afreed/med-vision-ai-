import { useEffect, useRef, useState } from "react";
import { getPatients, uploadXRay, getErrorMessage } from "../api/api";
import Dropzone from "../components/Dropzone";
import Icon from "../components/Icon";
import PageHeader from "../components/PageHeader";
import ResultPanel from "../components/ResultPanel";
import AiAssistant from "../components/AiAssistant";

const ALLOWED_TYPES = ["image/jpeg", "image/jpg", "image/png"];

function XRayAnalysis() {
  const [patients, setPatients] = useState([]);
  const [selectedPatient, setSelectedPatient] = useState("");
  const [selectedFile, setSelectedFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState("");
  const [uploading, setUploading] = useState(false);
  const [report, setReport] = useState(null);
  const [uploadError, setUploadError] = useState("");
  const [analyzingLong, setAnalyzingLong] = useState(false);
  const resultRef = useRef(null);

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

    loadPatients();
  }, []);

  // The first analysis after the server starts also loads the AI model,
  // which can take a while on small hosting; say so instead of "a few seconds".
  useEffect(() => {
    if (!uploading) {
      setAnalyzingLong(false);
      return undefined;
    }

    const timer = setTimeout(() => setAnalyzingLong(true), 8000);
    return () => clearTimeout(timer);
  }, [uploading]);

  // On narrow screens the result sits below the upload card, out of view.
  useEffect(() => {
    if (report && window.matchMedia("(max-width: 1180px)").matches) {
      resultRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [report]);

  // Local preview of the chosen image; the object URL is released when the
  // selection changes or the page unmounts.
  useEffect(() => {
    if (!selectedFile) {
      setPreviewUrl("");
      return undefined;
    }

    const url = URL.createObjectURL(selectedFile);
    setPreviewUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [selectedFile]);

  function handleFile(file) {
    setUploadError("");
    setReport(null);

    if (!file) {
      setSelectedFile(null);
      return;
    }

    if (!ALLOWED_TYPES.includes(file.type)) {
      setUploadError("Please select a JPG, JPEG or PNG image.");
      setSelectedFile(null);
      return;
    }

    setSelectedFile(file);
  }

  async function handleAnalyzeXRay() {
    setUploadError("");
    setReport(null);

    if (!selectedPatient) {
      setUploadError("Please select a patient first.");
      return;
    }

    if (!selectedFile) {
      setUploadError("Please select an X-Ray image first.");
      return;
    }

    try {
      setUploading(true);

      const result = await uploadXRay(Number(selectedPatient), "X-Ray", selectedFile);
      setReport(result.report);
    } catch (error) {
      console.error("X-Ray upload error:", error);
      setUploadError(getErrorMessage(error, "X-Ray analysis failed."));
    } finally {
      setUploading(false);
    }
  }

  const selectedPatientName = patients.find(
    (patient) => String(patient.id) === selectedPatient
  )?.full_name;

  const step = report ? 3 : selectedFile ? 2 : selectedPatient ? 1 : 0;

  return (
    <>
      <PageHeader title="X-Ray Analysis" subtitle="Analyze a chest X-ray using MediVision AI.">
        <span className="status-badge">
          <span className="status-dot" /> AI Online
        </span>
      </PageHeader>

      <div className="analysis-layout">
        <section className="panel analysis-panel">
          <div className="panel-header">
            <div>
              <h3>AI X-Ray Analysis</h3>
              <p>Upload a chest X-ray for AI-powered pneumonia screening.</p>
            </div>
          </div>

          <ol className="steps" aria-label="Progress">
            <li className={step >= 1 ? "done" : "current"}>
              <span>1</span> Patient
            </li>
            <li className={step >= 2 ? "done" : step === 1 ? "current" : ""}>
              <span>2</span> Image
            </li>
            <li className={step >= 3 ? "done" : step === 2 ? "current" : ""}>
              <span>3</span> Result
            </li>
          </ol>

          <div className="form-group">
            <label htmlFor="xray-patient">Patient</label>
            <select
              id="xray-patient"
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
            accept=".jpg,.jpeg,.png,image/jpeg,image/png"
            file={selectedFile}
            previewUrl={previewUrl}
            onFile={handleFile}
            icon="scan"
            title="Upload Chest X-Ray"
            changeTitle="Change X-Ray"
            hint="Drag and drop, or click to browse. JPG, JPEG or PNG."
          />

          {selectedFile && (
            <div className="selected-file">
              <Icon name="image" size={16} />
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
            onClick={handleAnalyzeXRay}
            disabled={uploading}
          >
            {uploading ? "Analyzing X-Ray..." : "Analyze X-Ray"}
          </button>

          <small className="panel-footnote">
            AI screening aid for pneumonia. Not a diagnosis.
          </small>
        </section>

        <section className="analysis-result" aria-live="polite" ref={resultRef}>
          {report ? (
            <ResultPanel report={report} patientName={selectedPatientName} />
          ) : uploading ? (
            <div className="result-placeholder">
              <span className="spinner" aria-hidden="true" />
              <h3>Analyzing the X-ray</h3>
              <p>
                {analyzingLong
                  ? "Loading the AI model for the first time. This can take up to a minute after the server has been idle; later analyses take only a few seconds."
                  : "Running the model and preparing the heatmap. This usually takes a few seconds."}
              </p>
            </div>
          ) : (
            <div className="result-placeholder">
              <div className="empty-icon">
                <Icon name="sparkles" size={26} />
              </div>
              <h3>Your result will appear here</h3>
              <p>Choose a patient, add an X-ray and press Analyze. You will see:</p>
              <ul>
                <li>The probability on a scale, with the model's cutoff</li>
                <li>A plain-language explanation and an attention heatmap</li>
                <li>A downloadable report for clinician review</li>
              </ul>
            </div>
          )}
        </section>
      </div>

      <AiAssistant report={report} />
    </>
  );
}

export default XRayAnalysis;
