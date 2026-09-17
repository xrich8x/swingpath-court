---
name: court-fit-ceiling-is-the-lines
description: Least squares over ALL matched court lines FAILS the 17.1px ceiling (19.80 px); the ceiling is the line evidence, not the fit — and the naive point-on-line objective is broken by low mounts
metadata:
  type: project
---

**Least squares over all matched line correspondences does NOT beat the exact 4-point
fit, and the joint line-to-model correspondence branch dies on a fit ceiling.** Measured
2026-09-04, `docs/evidence/least-squares-court-fit.md`, harness `eval/corr_ls_fit.py`.

Given the TRUE line-to-model assignment, on the same 13 clips: exact 4-point **17.10**
px@640 (control, reproduces the 2026-08-29 row to 0.00 px per clip), LS-geom **19.80**,
LS-DLT **73.50**. Pre-registered FAIL band was >13.0. Better on 7 clips, worse on 5,
tied 1, paired Wilcoxon **p = 0.97** — no direction at all.

**Why: the ceiling is one stage upstream of the fit.** LS-geom lowers the line residual
below the exact fit on **13 of 13** clips and below the **HUMAN homography** on 13 of 13
(3.01 px vs 6.44 px rms). The detected lines do not agree with the true court to better
than ~6.4 px, so the homography that best explains them is not the true court. A better
fitter converges harder onto a biased target.

**Why:** an all-lines fit was the named continuation for the 17.1 px ceiling, and it was
the one test that isolates FIT from SEARCH — run given the true correspondence.

**How to apply:** do not propose another fitting strategy for the court (weighted LS,
robust LS, bundle adjustment, more intersections) as a route to accuracy; the evidence
floor bars it. Any continuation is about the LINE DETECTOR. And because the search was
handed the right answer here, the solver's other two failures — C6's 12.6x cost and the
22-of-30 that die before scoring, both SEARCH problems — cannot reach the accuracy bar
and are not worth paying for. See [[mobile-port-split]] for why the classical court path
is a v1 skip anyway.

**A geometry trap worth not repeating.** The obvious point-on-line residual — project a
court line's WORLD ENDPOINTS and measure their distance to the detected image line — is
unusable on this project's footage. A low mount puts the far baseline at or beyond the
vanishing line, so an endpoint projects with near-zero or sign-flipped depth and the
distance explodes: **204 px@640 under the HUMAN homography** on `hillsborough_p02`. An
objective the true answer does not minimise cannot test anything. Pose it the other way —
project the MODEL line into the image (`l_i = H^-T l_w`, linear, no depth division) and
measure from sample points on the frame-clipped DETECTED line. Acceptance test for any
such objective: **its value under the truth must be a few px, not 200.** Related:
[[calibration-trap-check-corners-first]].
