// What a mount height costs in line-call accuracy.
//
// MIRROR of backend/swingvision/calibration.py — `_CALL_ACCURACY_BY_HEIGHT`,
// `CALL_MAJORITY_FLOOR_PCT` and `expected_call_accuracy`. Same rule as
// court.js: the Python file is the source of truth, this is the copy the
// browser reads, and the two must be kept in sync. tests/test_setup_guide.py
// pins the Python side; `npm test` has no equivalent, so if you change the
// table there, change it here in the same commit.
//
// Source: tools/height_curve.py, evidence data/output/height_curve.md.
// Synthetic flights with a KNOWN bounce, projected through cameras that differ
// only in height, measured by the shipped analytics.line_call. Restricted to
// bounces whose true position is within 0.5 m of a line, because that is the
// only population where a call is a call: pooled over ALL bounces the figure
// saturates at 87-99% and cannot tell a 1 m mount from a 12 m one.
//
// THE FLOOR IS NOT 50%. Always answering "in" scores CALL_MAJORITY_FLOOR_PCT
// on that population, so a setup at or below it is worth nothing — which is
// exactly what a 1.0 m camera measures.
//
// Guidance, not a promise: measured at 6 m setback, 100 deg lens, 720p, 30 fps
// with 30% detector dropout. Real clips at matching heights land within ~3
// points. Flat within noise above ~6 m; the small 8 -> 12 m dip is sampling.

const CALL_ACCURACY_BY_HEIGHT = [
  [1.0, 54.0], [1.25, 56.5], [1.5, 60.1], [1.75, 61.7], [2.0, 62.8],
  [2.5, 67.5], [3.0, 69.1], [4.0, 72.7], [5.0, 77.1], [6.0, 79.9],
  [8.0, 81.0], [12.0, 79.4],
];

export const CALL_MAJORITY_FLOOR_PCT = 56.2;

// Measured share of NEAR-THE-LINE calls this mount height gets right (%).
// Linear interpolation, clamped at both ends. Compare against
// CALL_MAJORITY_FLOOR_PCT before quoting it: below that, guessing wins.
export function expectedCallAccuracy(cameraHeightM) {
  const t = CALL_ACCURACY_BY_HEIGHT;
  const z = Number(cameraHeightM);
  if (!Number.isFinite(z)) return null;
  if (z <= t[0][0]) return t[0][1];
  if (z >= t[t.length - 1][0]) return t[t.length - 1][1];
  for (let i = 0; i < t.length - 1; i++) {
    const [z0, a0] = t[i];
    const [z1, a1] = t[i + 1];
    if (z >= z0 && z <= z1) return a0 + ((a1 - a0) * (z - z0)) / (z1 - z0);
  }
  return t[t.length - 1][1];
}

// Grade a mount for the UI. `good` once it clears the floor by a clear margin,
// `warn` when it is barely above it, `poor` at or below — the level a constant
// "in" already achieves.
export function callVerdict(cameraHeightM) {
  const pct = expectedCallAccuracy(cameraHeightM);
  if (pct === null) return null;
  const floor = CALL_MAJORITY_FLOOR_PCT;
  const gain = pct - floor;
  const level = gain <= 1.0 ? "poor" : gain < 6.0 ? "warn" : "good";
  return { pct, floor, gain, level };
}
