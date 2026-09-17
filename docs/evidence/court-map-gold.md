# P8 C2 — four-tap court model vs human clicks on real footage: NOT RUNNABLE on this pool

**Run 2026-09-16 by qa.** Pre-registered in `.claude/journals/lead.md` ("P8", C2). Nothing was tuned,
fixed or edited; no gold file was touched.

**WHAT THE NUMBERS BELOW WERE MEASURED AGAINST:** the `keypoints` stored in
`data/gold/*.court.labels.json`. **Those keypoints turned out NOT to be independent human clicks** —
the labelling tool computes them from the human's four corner clicks with a homography — so the
registered measurement grades the four-tap model against its own output (rule 1), and its number is
reported below only as a proof of that, **never as a verdict**.

## 0. The direction of the test, as briefed

C2 cannot overturn C1 (`court-map-ceiling.md`): both ends are human clicks at ~5.8 px@640 spread,
about 200x coarser than the ~0.1 px@1920 that C1 says the far baseline needs. C2 exists only to catch
problems on real footage that the pinhole/flat/regulation synthetic rig cannot see — lens distortion,
non-flat or non-regulation courts, roll, a wrong landmark convention — i.e. whether real footage is
materially WORSE than simulation. **This run cannot answer that question** (§2).

## 1. Definitions written down before running

- **Pool:** all 20 `data/gold/*.court.labels.json` (640 wide). Not `data/<clip>_pts.json` (T26).
- **Model:** the flat homography — `calibration.homography_from_landmarks` on the four `corners`
  (`near_bl/near_br/far_br/far_bl_doubles`), then `calibration.court_to_image`. No 3D camera (no
  known hfov on these clips).
- **Landmark set:** the 10 `court.LANDMARKS` that are not doubles corners — 4 singles/baseline
  junctions, 4 service-line/singles-sideline junctions, 2 T's. Error = Euclidean px (files are
  already 640 wide, so px = px@640).
- **Absent landmarks / frames:** a frame with `court: false` contributes nothing; a landmark missing
  from `keypoints` is skipped, never imputed. Off-frame landmarks (the tool stores extrapolated
  positions) are reported both included and excluded.
- **Secondary, per landmark:** median and p90; near (`near_*`) vs far (`far_*`).
- **Bar (lead.md, fixed):** PASS iff pooled median <= 5.8 px@640. Headline with and without the 8
  known-mislabelled frames.

## 2. The finding: the "other landmarks" are computed from the corners, not clicked

`tools/gold_label_server.py`, `cornersToLabel()` — identical at all three label commits
(`82fb523` 2026-07-10, `537ed12` / `6843ee7` 2026-07-12):

```js
function cornersToLabel() {
  const H = solveH(CORNERS.map(c => c.m), corners);
  ...
  if (H) for (const k in KP) { const p = applyH(H, KP[k][0], KP[k][1]);
    kobj[k] = [Math.round(p[0]*10)/10, Math.round(p[1]*10)/10]; }
  return { court: true, corners: cobj, keypoints: kobj, estimated_corners: est };
}
```

The labeller clicks four doubles corners (dragging them until the drawn overlay sits on the visible
paint); every other `keypoint` is that overlay's homography evaluated at the regulation coordinate
and rounded to 0.1 px. **There is no independently clicked non-corner landmark anywhere in this pool.**

**Confirmed by running the check, not only by reading the code** (script in §6, backend venv):

| | pairs | median px@640 | p90 | max |
|---|---|---|---|---|
| all | 3,300 (330 court frames x 10, 20 clips) | **0.048** | **0.090** | 0.589 |
| near landmarks | 1,650 | 0.050 | 0.104 | 0.589 |
| far landmarks | 1,650 | 0.046 | 0.083 | 0.125 |
| in-frame landmarks only | 3,099 | 0.048 | — | 0.518 |

Per landmark the median runs 0.038-0.050 and p90 0.066-0.116 px. That is 0.1 px rounding — of the
stored keypoints and of the corners the homography was rebuilt from — and nothing else. The maximum
(0.59 px, `am_ntrp45w` near singles junctions) is corner rounding amplified by off-frame near corners.

**Verdict: the registered bar reads "PASS, median 0.048 px" and that reading is VOID.** It is the
four-tap model scored against the four-tap model. **C2 is NOT RUNNABLE on `data/gold` as registered;
it is not a pass and not a fail.** Near vs far: no difference (0.050 vs 0.046), for the same reason.
Nothing here says anything about lens distortion, court flatness, roll or landmark convention.

**With/without the 8 mislabelled frames:** identical by construction. The 8 (`am_indoor_hard1`
9204…15427) are all `court: false`, so they never enter. Recorded, not corrected (rule 10). All 30
`court: false` frames in the pool carry `unusable: true`; `am_usta60` also has 8 of them — whether
those are also mislabelled is not established.

**The one qualitative thing the pool does carry:** each of the 330 court labels is a human's
judgement that a flat regulation homography overlay could be dragged onto the visible paint at 640
wide. That is weak evidence that real footage is not grossly non-pinhole at this resolution. It is
not a number and does not stand in for C2.

## 3. A provenance defect found on the way (rule 10)

Commit `2e49f38` (2026-09-06, "composite calibration score FAILS its bar") — an agent commit whose
message never mentions gold — **re-saved two human gold files**:

- `am_beginner` frame 1021: `near_bl_doubles` moved (-195.1, 273.7) -> (-209.5, 282.0), ~16 px.
  Frame 3904: **all four corners moved**, up to 27 px (`near_bl` -176.1 -> -203.5). Eight more frames
  re-saved with only 0.1 px keypoint re-rounding and new timestamps (`t` 2026-09-06 01:08).
- `am_usta45final`: **15 new labelled frames added** (5074 … 35251).

Whether a human made those edits in the label tool during that session is not recorded. The rest of
the pool is unchanged since July. This matters to the 12/20 gate and to anything else scored on these
two clips; it is reported, not reverted.

## 4. Side check — `demo30` vs `yt_match40`, one static camera, 1.38 m vs 1.64 m

Both files are in the compromised references pool and were **not scored against gold**. Shipped
`tools/height_curve.camera_height_of` (PnP via `bridge.camera_from_court_corners`), 1280x720:

| hfov assumed (deg) | demo30 height (m) | yt_match40 height (m) | gap (m) |
|---|---|---|---|
| **104.16** — demo30's own FITTED hfov (`height_curve.hfov_of` -> `courtfit.cam_fit_quad`) | **1.376** | 1.581 | 0.205 |
| **91.04** — yt_match40's own FITTED hfov | 1.421 | **1.642** | 0.221 |
| 90 | 1.424 | 1.647 | 0.223 |
| 70 (bridge default) | 1.507 | 1.784 | 0.277 |
| 60 | 1.567 | 1.889 | 0.322 |
| 40 | 1.781 | 2.282 | 0.501 |

Both stamped heights reproduce at their own fitted (not known) focal lengths. **An hfov difference
does NOT explain the 0.26 m gap:** at any COMMON hfov the gap stays 0.20-0.50 m. A 5 deg hfov change
moves one quad's height 1.6-2.3% (70 -> 75 deg), consistent with C1's 2-3%; even the full 13 deg
between the two fitted hfovs moves one quad only 0.045-0.061 m.

**The two QUADS disagree.** Projected through each map, the same landmark lands 217 px@640 apart at
`near_bl_doubles`, 145 at `near_br_doubles`, 27-31 at the near service line/T, and 6-12 at the far
landmarks. Rendered both courts on yt_match40 frames 0 and 3002 and demo30 frame 450 (the same image,
per the P2 finding): **the current `yt_match40_pts.json` (2026-09-05 re-click) lies on the painted
near baseline (row ~452) and near service line (row ~362); `demo30_pts.json` (2026-08-03) puts its near
baseline ~60 px below any painted line**, on empty asphalt, and its near service line above the paint.
This is qa's visual reading of a 1280x720 render; the founder's eye is authoritative.

**T23 is not the answer for the current file.** T23 describes the superseded `.bak-2026-09-05` quad
(11.33 m at a fitted 20.7 deg — reproduced here); the 2026-09-05 re-click was already exonerated in
`net-anchor-calibration-check.md` §1. On this frame **the wrong calibration is demo30's**, and both
files pass the residual screen (0.5 / 0.0 px) — the T23 blindness again. Note for the record: the
2026-09-05 file replacement is also why qa saw `yt_match40` "resolve to a different court" between
2026-09-02 and 2026-09-10 (`gate-noise-diag` verification) — a file change, not silent drift.

## 5. What would actually run C2

An independent click set: a human clicks the non-corner landmarks (T's, service-line junctions,
singles junctions) directly on a sample of gold frames, **with no overlay drawn**, blind to the
corner fit. Roughly 20 frames x 6 visible points is enough to resolve a 5.8 px median. Until then
the only real-footage check of the four-tap model off its own corners is the net-anchor render
(`tools/net_anchor_check.py`), which is an eye check, not a number. C3 (the court visit) remains the
only metric truth. **This is a new measurement design and needs a fresh pre-registration by the
lead; qa has not run or proposed a substitute bar.**

## 6. Reproduce

Scripts were kept in qa's scratchpad (qa may not write `tools/`); the scoring script, verbatim:

```python
import json, sys, glob, os
import numpy as np
sys.path.insert(0, os.path.join(os.getcwd(), "backend"))
from swingvision import calibration, court
CORN = ["near_bl_doubles", "near_br_doubles", "far_br_doubles", "far_bl_doubles"]
OTHER = [k for k in court.LANDMARKS if k not in CORN]
rows = []
for p in sorted(glob.glob("data/gold/*.court.labels.json")):
    for fr, L in json.load(open(p))["labels"].items():
        if not L.get("court") or not L.get("corners"): continue
        H = calibration.homography_from_landmarks({k: L["corners"][k] for k in CORN})
        for k in OTHER:
            if k in L.get("keypoints", {}):
                pr = calibration.court_to_image(H, [court.LANDMARKS[k]])[0]
                rows.append(float(np.hypot(*(pr - np.array(L["keypoints"][k])))))
print(np.median(rows), np.percentile(rows, 90), max(rows))   # run from repo root
```

Side check: `camera_height_of(kp, hfov, 1280, 720)` and `hfov_of(kp, H, 1280, 720)` imported from
`tools/height_curve.py`, for `data/demo30_pts.json`, `data/yt_match40_pts.json` and
`data/yt_match40_pts.json.bak-2026-09-05`, with both maps' `court.LINES` drawn on the frames above.
