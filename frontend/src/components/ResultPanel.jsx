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

/**
 * The full "AI screening result" experience: prediction plus the context
 * a clinician needs to judge it (probability, threshold, model version,
 * when it ran) and the disclaimer that this is a screening aid, not a
 * diagnosis. Used by both the X-Ray Analysis page and Medical Reports
 * detail view so the two never drift apart.
 */
export default function ResultPanel({ report, patientName }) {
  if (!report) return null;

  const isPneumonia = report.prediction === "Pneumonia";

  return (
    <div
      className={`ai-result-panel ${
        isPneumonia ? "pneumonia-result" : "normal-result"
      }`}
    >
      <div className="ai-result-header">
        <strong>AI Screening Result</strong>
        <span className="ai-result-badge">{report.prediction || "Pending"}</span>
      </div>

      <div className="ai-result-grid">
        <div>
          <span>Pneumonia probability</span>
          <strong>
            {report.pneumonia_probability != null
              ? `${report.pneumonia_probability}%`
              : "—"}
          </strong>
        </div>

        <div>
          <span>Model confidence</span>
          <strong>{report.confidence != null ? `${report.confidence}%` : "—"}</strong>
        </div>

        <div>
          <span>Operating threshold</span>
          <strong>{report.threshold_used ?? "—"}</strong>
        </div>

        <div>
          <span>Model</span>
          <strong>{report.model_version || "—"}</strong>
        </div>

        {patientName && (
          <div>
            <span>Patient</span>
            <strong>{patientName}</strong>
          </div>
        )}

        <div>
          <span>Analysis date</span>
          <strong>{formatDate(report.created_at)}</strong>
        </div>
      </div>

      <div className="ai-result-disclaimer">
        This is an AI-assisted screening result, not a confirmed medical
        diagnosis. Results should be reviewed by a qualified healthcare
        professional before any clinical decision is made.
      </div>
    </div>
  );
}
