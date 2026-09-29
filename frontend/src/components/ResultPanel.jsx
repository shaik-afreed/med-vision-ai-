import { useEffect, useState } from "react";
import { formatPercent } from "../utils/format";
import { getReportGradcamUrl } from "../api/api";

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
  const [gradcamUrl, setGradcamUrl] = useState("");
  const [gradcamError, setGradcamError] = useState(false);

  useEffect(() => {
    let objectUrl = "";

    setGradcamUrl("");
    setGradcamError(false);

    if (report?.id && report.has_gradcam) {
      getReportGradcamUrl(report.id)
        .then((url) => {
          objectUrl = url;
          setGradcamUrl(url);
        })
        .catch(() => setGradcamError(true));
    }

    return () => {
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [report?.id, report?.has_gradcam]);

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
              ? `${formatPercent(report.pneumonia_probability)}%`
              : "—"}
          </strong>
        </div>

        <div>
          <span>Model confidence</span>
          <strong>
            {report.confidence != null ? `${formatPercent(report.confidence)}%` : "—"}
          </strong>
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

      {report.ai_explanation && (
        <div className="ai-result-explanation">
          <span className="ai-result-explanation-label">What this means</span>
          <p>{report.ai_explanation}</p>
        </div>
      )}

      {report.has_gradcam && (
        <div className="ai-result-heatmap">
          <span className="ai-result-explanation-label">
            Where the AI focused (heatmap)
          </span>

          {gradcamUrl ? (
            <img
              src={gradcamUrl}
              alt="Grad-CAM heatmap showing which regions of the X-ray most influenced the AI's prediction"
              className="report-gradcam-image"
            />
          ) : gradcamError ? (
            <p className="ai-result-heatmap-unavailable">
              Heatmap could not be loaded for this report.
            </p>
          ) : (
            <p className="ai-result-heatmap-unavailable">Loading heatmap...</p>
          )}

          <small>
            Warmer colors (red/yellow) show where the model's attention was
            concentrated. This is a visual explainability aid, not a
            confirmed or precise anatomical finding.
          </small>
        </div>
      )}

      <div className="ai-result-disclaimer">
        This is an AI-assisted screening result, not a confirmed medical
        diagnosis. Results should be reviewed by a qualified healthcare
        professional before any clinical decision is made.
      </div>
    </div>
  );
}
