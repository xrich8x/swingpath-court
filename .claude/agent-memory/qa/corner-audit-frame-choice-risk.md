---
name: corner-audit-frame-choice-risk
description: Measured 2026-09-09 — 7 of the 10 founder "wrong court" verdicts were made on a frame the evaluation never scores; the corner audit sheets are frame 0 and 15 of 28 clips are not static
metadata:
  type: project
---

The founder's 2026-09-09 review of 28 `data/output/corner_audit/*_corners.png` sheets
marked 10 calibrations wrongly placed. Those sheets were all rendered on **frame 0**
(confirmed from the sheets' own caption text, not assumed), while corners placed in the
court-setup tool's **gallery** mode came from arbitrary mid-clip frames and the scoring
looks only at `run_refs.frame_positions(total, 8)` = the middle 5%–95%.

**Measured: 7 of the 10 wrong verdicts are AT RISK** (background displacement of the
clicked corners between frame 0 and the scored frames >= `WRONG_PX_640` = 20 px@640):
`HoHxFSX_gLk_s3` 212.9, `A7vXlWIlyrI` 162.6, `HoHxFSX_gLk_s1` 119.4, `sAjkpeRq4P4` 80.4,
`bump_ntrp30` 60.5, `CYqapSq5llo` 38.8, `UHf0LeMU2pg` 29.2. `uR5q2cSM6AY` 13.2 is WATCH.
Only `L73ep7JHiJ4` (5.95) and `demo30` (0.04) are clean. **The risk runs both ways** —
`HoHxFSX_gLk_s2` (110.5) and `bump_ntrp30b` (40.2) were marked CORRECT on an equally
unrepresentative frame.

**Why:** cuts and zooms, not drift. `A7vXlWIlyrI` frame 0 is a **monochrome intro frame**;
`sAjkpeRq4P4` frame 0 is a zoomed-in title shot matching **0 of 8** scored frames;
`HoHxFSX_gLk_s3` contains **more than one venue**. All 10 shell clips plus `tc8CGFxyRE8`,
`yt_match40`, `yt_rally2` are perfectly static (<0.5 px) — so motion is confounded with
clip type and does NOT explain the wrong/correct split on its own.

**How to apply:** never treat a single-frame render as evidence about a whole clip; the
frame index is part of the claim. A one-clip spot-check is not a control — the lead's
`sAjkpeRq4P4` check (frame 0 vs frame 500) landed inside the opening shot and missed a
zoom change that the eval's own sampling starts after. Resolve with
`tools/render_corner_audit.py --eval-frames`, which renders all 8.

Full numbers, controls and per-frame rows: `docs/evidence/camera-motion-verdict-risk.md`.
Related: [[court-proposal-recall-search-binds]] — every court figure scored against this
pool is provisional while T26 provenance is unresolved.
