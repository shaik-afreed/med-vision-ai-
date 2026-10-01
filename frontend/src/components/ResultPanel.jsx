import { useEffect, useState } from "react";
import { formatPercent } from "../utils/format";
import { getReportGradcamUrl, downloadReportPdf, getErrorMessage } from "../api/api";
import Icon from "./Icon";
import ProbabilityMeter from "./ProbabilityMeter";

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
  const [pdfBusy, setPdfBusy] = useState(false);
  const [pdfError, setPdfError] = useState("");

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
  const assessment = report.assessment;
  // A borderline score is not a reassuring "Normal" and must not look like
  // one; for a patient outside the model's training ages (adults) the score
  // is unreliable whichever way it points.
  const isOutsideAges = assessment?.category === "outside_training_ages";
  const isUnlikeTraining = assessment?.category === "unlike_training_images";
  const isUnreliable = isOutsideAges || isUnlikeTraining;
  const isBorderline = assessment?.category === "inconclusive" || isUnreliable;
  const panelTone = isBorderline ? "borderline-result" : isPneumonia ? "pneumonia-result" : "normal-result";
  const toneIcon = isBorderline ? "alert" : isPneumonia ? "alert" : "check";

  async function handleDownloadPdf() {
    setPdfError("");
    setPdfBusy(true);
    try {
      await downloadReportPdf(report.id, `MediVision-report-${String(report.id).padStart(6, "0")}.pdf`);
    } catch (error) {
      setPdfError(getErrorMessage(error, "Unable to download the report."));
    } finally {
      setPdfBusy(false);
    }
  }

  return (
    <div className={`ai-result-panel ${panelTone}`}>
      <div className="ai-result-header">
        <div className="ai-result-title">
          <span className="ai-result-icon">
            <Icon name={toneIcon} size={18} />
          </span>
          <strong>AI Screening Result</strong>
        </div>
        <span className="ai-result-badge">
          {isUnreliable
            ? isOutsideAges
              ? "Not reliable for this age"
              : "Not reliable for this image"
            : `${report.prediction || "Pending"}${isBorderline ? " · borderline" : ""}`}
        </span>
      </div>

      {assessment && (
        <div className="ai-assessment">
          <strong>{assessment.label}</strong>
          <p>{assessment.advice}</p>
          {assessment.historical_pneumonia_share != null && (
            <small>
              Measured on the model's test set: {Math.round(assessment.historical_pneumonia_share * 100)}% of
              images in this score range were truly pneumonia ({assessment.historical_images} images).
            </small>
          )}
        </div>
      )}

      <ProbabilityMeter
        probability={report.pneumonia_probability}
        thresholdPercent={report.threshold_used != null ? report.threshold_used * 100 : undefined}
      />

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
          {isUnreliable && (
            <p>
              <strong>
                Because the score is not reliable here, the text below only describes what the model
                did; it is not a usable result.
              </strong>
            </p>
          )}
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
            <div className="skeleton skeleton-image" aria-label="Loading heatmap" />
          )}

          <small>
            Warmer colors (red/yellow) show where the model's attention was
            concentrated. This is a visual explainability aid, not a
            confirmed or precise anatomical finding.
          </small>
        </div>
      )}

      <div className="ai-result-actions">
        <button type="button" className="primary-button" onClick={handleDownloadPdf} disabled={pdfBusy}>
          <Icon name="download" size={17} />
          {pdfBusy ? "Preparing report..." : "Download report (PDF)"}
        </button>
        {pdfError && <span className="ai-result-pdf-error">{pdfError}</span>}
      </div>

      <div className="ai-result-disclaimer">
        This is an AI-assisted screening result, not a confirmed medical
        diagnosis. Results should be reviewed by a qualified healthcare
        professional before any clinical decision is made.
      </div>
    </div>
  );
}
