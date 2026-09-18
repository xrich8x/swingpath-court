---
name: pre-court-verifications
description: qa verification results from before the 2026-09-17 court-only scope cut — ball, pose, gates and platform; history, not work, but the measured negatives must not be re-proposed as untested
metadata:
  type: project
---

**Archived scope (founder cut the project to the court feature on 2026-09-17).** These are results I
verified before that cut. **Do not work on any of them.** They live here only so a measured negative
is not re-proposed as untested, and so a number quoted from that era can be checked.

- **P0-2 pose downscale: FAILED its gate, 2026-08-27.** Far-player detection `yt_match40` 11.0%
  @1280 -> 0.1% @640 -> 0.0% @384; `am_hard_utr` 1.0% -> 0.0% -> 0.0%. Near player barely moves. The
  gate allowed 2 points absolute. A measured negative.
- **P0-3 crop-around-contact: UNMEASURED, not negative.** A first attempt reporting 78.8% was
  invalidated on visual inspection — the 448 px box catches the near player regardless, and the
  contact population was wrong. Any retry needs a correct population.
- **Core ML export needs macOS.** `coremltools`' Windows wheel cannot serialize weights
  (`BlobWriter not loaded`). `.github/workflows/coreml-export.yml` runs it on a GitHub Actions macOS
  runner; untested end to end as of 2026-08-28.
- **Line-call margin curve, 2026-08-28.** Below the majority floor under 10 cm from a line, clear it
  from ~20 cm; recommended band 0.20 m, which refuses 39% of close (0.5 m) calls. Measurement only,
  never built.
- **int8 ball-graph parity verified 2026-09-03.** Headline 5/528 and 3/6 clips CONFIRMED exactly; arm
  B/C mitigation rejections CONFIRMED from hashes, op counts and blob dumps. **But** the "close race"
  0.15 px threshold was picked after seeing the 5 failures — "all 5 are close races" is NOT
  threshold-robust (2/5 at 0.05), while "0 close races in the 2 clean clips" IS robust across
  0.05-0.30.
- **`seen_frac` gate evidence verified 2026-09-03.** The gate doesn't predict error, INDETERMINATE,
  accept-precision about the base rate — all CONFIRMED via independent rebuild. The positive control
  shows the harness responds to an injected true correlation on all 3 clips but weakly/saturates on 2
  of 3 camera geometries. Band-ratio DIGITS diverged from backend-dev's (one clip flips sign):
  classifier-shape numbers reproduce, fine per-clip ratios don't.
- **Innovation-gate diagnostic §5 (K3 + K1) verified 2026-09-10.** CONFIRMED (K3 discarded
  914/492/48 and +6.557/+5.142/+3.534 pts, higher than the reported 902/479/47 and
  +6.492/+4.926/+3.450; K1 pooled median 0.11272 on n=291, 12.30x below chi2_2, sign-test p=1.9e-29).
  **Two defects:** a post-hoc run-reconstruction undercount, and `yt_match40`'s calibration silently
  resolving to a DIFFERENT court (86 vs 186 shots, hfov 91.28 vs 26.43) between 2026-09-02 and
  2026-09-10 — so its "reproduces the published baseline" claim is false and every span-derived
  number on that clip is in question.
- **P2 occlusion census sheet built 2026-09-16, UNLABELLED.** On `yt_match40`.
  `demo30.perception.json` is not demo30's; `yt_match40`'s HUD shows SwingVision bounce dots (mask
  it); audio A/V membership is chance-level, so this is a negative-space audit, not
  capture-recapture.
