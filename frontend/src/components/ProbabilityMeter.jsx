import { formatPercent } from "../utils/format";

// Zone edges match ai_model/probability_bands.json (measured on the model's
// test set) and backend/services/assessment.py. Display only - the labels
// and reliability figures come from the backend's `assessment`.
const ZONES = [
  { id: "very-low", from: 0, to: 20 },
  { id: "low", from: 20, to: 50 },
  { id: "probably-normal", from: 50, to: 67 },
  { id: "inconclusive", from: 67, to: 82 },
  { id: "high", from: 82, to: 95 },
  { id: "very-high", from: 95, to: 100 },
];

function clamp(value) {
  return Math.min(100, Math.max(0, value));
}

/**
 * A color-zoned scale showing where this X-ray's pneumonia probability falls
 * relative to the model's decision cutoff, so the number is never read in
 * isolation.
 */
export default function ProbabilityMeter({ probability, thresholdPercent }) {
  if (probability == null) return null;

  const score = clamp(probability);
  const cutoff = clamp(thresholdPercent ?? 82);
  const text = formatPercent(probability);

  // Near either end the value bubble leans inward so it never pokes out of
  // the card; --s is how far along the bubble the pointer sits.
  const anchor = score > 90 ? 0.85 : score < 10 ? 0.15 : 0.5;

  return (
    <div
      className="meter"
      role="img"
      aria-label={`Score ${text} percent on a scale from 0 to 100. Decision cutoff ${cutoff.toFixed(0)} percent.`}
    >
      <div className="meter-bar">
        <div className="meter-track">
          {ZONES.map((zone) => (
            <span
              key={zone.id}
              className={`meter-zone zone-${zone.id}`}
              style={{ width: `${zone.to - zone.from}%` }}
            />
          ))}
        </div>

        <div className="meter-threshold" style={{ left: `${cutoff}%` }}>
          <span>Cutoff {cutoff.toFixed(0)}%</span>
        </div>

        <div className="meter-marker" style={{ left: `${score}%`, "--s": anchor }}>
          <span>{text}%</span>
        </div>
      </div>

      <div className="meter-scale" aria-hidden="true">
        <span>0%</span>
        <span>Likelihood of pneumonia</span>
        <span>100%</span>
      </div>
    </div>
  );
}
