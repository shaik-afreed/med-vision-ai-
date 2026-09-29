import { useEffect, useState } from "react";
import { getPatients, uploadXRay, getErrorMessage } from "../api/api";
import ResultPanel from "../components/ResultPanel";
import XRayChatbot from "../components/XRayChatbot";

function XRayAnalysis() {
  const [patients, setPatients] = useState([]);
  const [selectedPatient, setSelectedPatient] = useState("");
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [report, setReport] = useState(null);
  const [uploadError, setUploadError] = useState("");

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

  function handleFileChange(event) {
    const file = event.target.files?.[0];

    setUploadError("");
    setReport(null);

    if (!file) {
      setSelectedFile(null);
      return;
    }

    const allowedTypes = ["image/jpeg", "image/jpg", "image/png"];

    if (!allowedTypes.includes(file.type)) {
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

  return (
    <>
      <section className="page-header">
        <div>
          <h2>X-Ray Analysis</h2>
          <p>Analyze a chest X-ray using MediVision AI.</p>
        </div>
        <span className="status-badge">● AI Online</span>
      </section>

      <section className="panel analysis-panel">
        <div className="panel-header">
          <div>
            <h3>AI X-Ray Analysis</h3>
            <p>Upload a chest X-ray for AI-powered pneumonia screening.</p>
          </div>
        </div>

        <div className="upload-area">
          <div className="upload-icon">🩻</div>
          <h4>Upload Chest X-Ray</h4>
          <p>Upload a JPG, JPEG or PNG chest X-ray for AI analysis.</p>

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
            {selectedFile ? "Change X-Ray" : "Select X-Ray"}
            <input
              type="file"
              accept=".jpg,.jpeg,.png,image/jpeg,image/png"
              onChange={handleFileChange}
              hidden
            />
          </label>

          {selectedFile && <div className="selected-file">📄 {selectedFile.name}</div>}

          {uploadError && <div className="upload-error">{uploadError}</div>}

          <button
            className="primary-button"
            onClick={handleAnalyzeXRay}
            disabled={uploading}
          >
            {uploading ? "Analyzing X-Ray..." : "Analyze X-Ray"}
          </button>

          <small>AI prediction • Pneumonia screening</small>

          <ResultPanel report={report} patientName={selectedPatientName} />
        </div>
      </section>

      <XRayChatbot report={report} />
    </>
  );
}

export default XRayAnalysis;
