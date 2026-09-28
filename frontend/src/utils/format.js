/**
 * Formats a percentage value (already on a 0-100 scale, e.g. from
 * report.pneumonia_probability) for display.
 *
 * Uses 2 decimal places normally. If the model's real probability is
 * extremely close to (but not exactly at) 0 or 100 - e.g. 99.9998 - a
 * plain 2dp rounding would show "100.00%", implying absolute certainty
 * the model never actually reported. In that case, this falls back to
 * up to 4 decimal places, just enough to show a value that isn't a bare
 * 0 or 100, so the display never claims more certainty than the
 * underlying number supports.
 *
 * Examples (input already *100, matching the API's pneumonia_probability
 * and confidence fields):
 *   99.9354   -> "99.94"
 *   99.9935   -> "99.99"
 *   99.9998   -> "99.9998"  (2dp would round to "100.00" - misleading)
 *   6.2209    -> "6.22"
 */
export function formatPercent(value) {
  if (value == null || Number.isNaN(value)) return null;

  const twoDecimals = Math.round(value * 100) / 100;

  const wouldFalselyHitBoundary =
    (twoDecimals >= 100 && value < 100) || (twoDecimals <= 0 && value > 0);

  if (!wouldFalselyHitBoundary) {
    return twoDecimals.toFixed(2);
  }

  for (let decimals = 3; decimals <= 4; decimals += 1) {
    const factor = 10 ** decimals;
    const rounded = Math.round(value * factor) / factor;
    if (rounded < 100 && rounded > 0) {
      return rounded.toFixed(decimals);
    }
  }

  return value.toFixed(4);
}
