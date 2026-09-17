---
name: ground-plane-blindness-narrows
description: synthetic-corruption test of researcher's ground-plane-blindness claim — the claim NARROWS, its anchoring anecdote does not survive
metadata:
  type: project
---

Full writeup: `docs/evidence/ground-plane-blindness-test.md` (2026-09-05).

**The claim under test** (`docs/evidence/independent-calibration-references.md`): every
calibration check that has failed on this project reads only the ground plane (z=0), and
this is structural — "invisible by construction" — because a near-half-compressed court
preserves the ground-plane symmetry a homography must respect.

**What broke on inspection.** The anecdote offered as evidence (`yt_match40`, residual
0.0 px, height 1.64 m, coverage 0.944, all simultaneously on a WRONG court) turns out to
be a citation of a calibration that `docs/evidence/verify-court-false-rejects.md` itself
withdrew as CORRECT within the same hour it was first written ("I mis-read the net").
There is no confirmed instance anywhere in this repo of an actually-wrong court scoring
well on ground-plane stats. Worse for the claim: the one calibration that IS confirmed
wrong (the `.bak` file, 11.3 m) WAS caught, by the exact camera-height screen the claim
calls a failure.

**What I built to test the abstract claim anyway** (since the anecdote gave nothing to
reproduce): corrupted real clicked corners in memory (never touched `data/*_pts*.json`)
across 5 families — depth-anisotropic compression (the claim's own mechanism), isotropic
scale (researcher's requested control), sideways shift, rotation, asymmetric scale — on
2 clips (`yt_match40`, `flexi_franz_p01`), scored against the SHIPPED gates
(`verify_court`, `camera_height_m` via `cam_fit_quad`) and the one off-plane statistic
(`tools/net_tape_height.py`).

**Result: NARROWS, does not FAIL cleanly, does not SURVIVE as stated.**
- Depth-anisotropic compression really is invisible to every shipped gate across the
  whole tested range (far corners moved up to 90% of the way to the near corners) on
  both clips — the real, reproducible core of the claim.
- But it is not invisible to every ground-plane QUANTITY — `cam_fit_quad` already solves
  for focal length as part of the same fit that gives camera height, and the implied hfov
  collapses monotonically with compression severity (91°→2° on one clip) well outside the
  repo's own stated 60–90° amateur-lens prior by ~15% compression. Nobody reads it;
  `camera_height_m()`'s production call even hardcodes a default 70° hfov instead of the
  fitted one. This is a REPORTING gap, not a geometric law — "hard to see" not
  "impossible to see."
- Isotropic scale (not depth-specific) IS caught by `court_line_coverage`/`verify_court`
  on `yt_match40` (coverage 0.94→0.31, correctly FAILS) — confirming the researcher's
  cross-feed prediction that the honest boundary is anisotropic-depth-specific, not
  ground-plane-general. (Masked on the other clip only because its baseline coverage
  margin, 0.996, is so far above the lax 0.40 bar that nothing tested crosses it — a
  restatement of the already-known "coverage tracks line visibility" finding, not new.)
- Mechanistic read: what actually separates "caught" from "not caught" is (a) whether the
  corrupted homography still points at REAL PAINT nearby (depth compression does; isotropic
  shrink/shift/rotation don't), and (b) whether the corruption is achievable by SOME legal
  pinhole pose under this project's own model constraints (±3° roll cap, fixed principal
  point) — depth compression is (residual stays ~0), rotation/shift/asym-scale are not
  (residual explodes at small magnitudes). Sharper than "z=0 symmetry."

**Standing lesson: an anecdote used to anchor a structural claim needs to be re-verified
against its own later corrections before being cited** — this project already withdrew the
specific number being leaned on, in the same file, the same day. [[qa_does_not_write_to_codebase]]
