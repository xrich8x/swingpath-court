// Court constants — MUST stay in sync with backend/swingvision/court.py.
// All dimensions in metres. Coordinate system: x 0..DOUBLES_WIDTH left->right,
// y 0..LENGTH near baseline -> far baseline, net at y = LENGTH/2.

export const LENGTH = 23.77;
export const DOUBLES_WIDTH = 10.97;
export const SINGLES_WIDTH = 8.23;
export const ALLEY = (DOUBLES_WIDTH - SINGLES_WIDTH) / 2; // 1.37
export const SERVICE_LINE_FROM_NET = 6.4;
export const NET_Y = LENGTH / 2; // 11.885

export const X_LEFT_DOUBLES = 0;
export const X_LEFT_SINGLES = ALLEY; // 1.37
export const X_CENTER = DOUBLES_WIDTH / 2; // 5.485
export const X_RIGHT_SINGLES = DOUBLES_WIDTH - ALLEY; // 9.60
export const X_RIGHT_DOUBLES = DOUBLES_WIDTH; // 10.97

export const Y_NEAR_BASELINE = 0;
export const Y_NEAR_SERVICE = NET_Y - SERVICE_LINE_FROM_NET; // 5.485
export const Y_FAR_SERVICE = NET_Y + SERVICE_LINE_FROM_NET; // 18.285
export const Y_FAR_BASELINE = LENGTH; // 23.77

// Net structure. Posts sit 0.914 m (3 ft) outside the DOUBLES sideline; singles
// sticks use the same offset from the SINGLES sideline. Mirrors court.py.
export const NET_POST_OFFSET = 0.914;
export const NET_HEIGHT_POST = 1.07;
export const NET_HEIGHT_CENTER = 0.914;
export const X_LEFT_POST = X_LEFT_DOUBLES - NET_POST_OFFSET; // -0.914
export const X_RIGHT_POST = X_RIGHT_DOUBLES + NET_POST_OFFSET; // 11.884
export const X_LEFT_STICK = X_LEFT_SINGLES - NET_POST_OFFSET; // 0.456
export const X_RIGHT_STICK = X_RIGHT_SINGLES + NET_POST_OFFSET; // 10.514

// Line segments [[x1,y1],[x2,y2]] in court metres — mirrors court.LINES.
export const LINES = [
  // Baselines
  [[X_LEFT_DOUBLES, Y_NEAR_BASELINE], [X_RIGHT_DOUBLES, Y_NEAR_BASELINE]],
  [[X_LEFT_DOUBLES, Y_FAR_BASELINE], [X_RIGHT_DOUBLES, Y_FAR_BASELINE]],
  // Doubles sidelines
  [[X_LEFT_DOUBLES, Y_NEAR_BASELINE], [X_LEFT_DOUBLES, Y_FAR_BASELINE]],
  [[X_RIGHT_DOUBLES, Y_NEAR_BASELINE], [X_RIGHT_DOUBLES, Y_FAR_BASELINE]],
  // Singles sidelines
  [[X_LEFT_SINGLES, Y_NEAR_BASELINE], [X_LEFT_SINGLES, Y_FAR_BASELINE]],
  [[X_RIGHT_SINGLES, Y_NEAR_BASELINE], [X_RIGHT_SINGLES, Y_FAR_BASELINE]],
  // Service lines
  [[X_LEFT_SINGLES, Y_NEAR_SERVICE], [X_RIGHT_SINGLES, Y_NEAR_SERVICE]],
  [[X_LEFT_SINGLES, Y_FAR_SERVICE], [X_RIGHT_SINGLES, Y_FAR_SERVICE]],
  // Center service line
  [[X_CENTER, Y_NEAR_SERVICE], [X_CENTER, Y_FAR_SERVICE]],
];

// Net is drawn separately so it can be styled differently.
export const NET_LINE = [[X_LEFT_DOUBLES, NET_Y], [X_RIGHT_DOUBLES, NET_Y]];

// Build a projector from court metres to SVG pixels for a top-down view with
// the near baseline (player A) at the bottom. Returns helpers + canvas size.
export function makeCourtLayout(scale = 20, pad = 28) {
  const width = DOUBLES_WIDTH * scale + 2 * pad;
  const height = LENGTH * scale + 2 * pad;
  const sx = (x) => pad + x * scale;
  const sy = (y) => pad + (LENGTH - y) * scale; // flip: y=0 at bottom
  return { width, height, scale, pad, sx, sy };
}
