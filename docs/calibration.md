# Calibration files — auditing, and the known-good / known-bad list

> Moved out of CLAUDE.md on 2026-08-26. CLAUDE.md keeps the one-line rule
> (*audit before trusting; good is < 2.5 px fit residual*); the per-file
> residuals and the reasoning live here.

Text preserved verbatim from CLAUDE.md.

- CALIBRATION FILES: some committed `data/*_pts.json` are DEGENERATE (corners
  swapped / near-baseline at top of frame / a shape no real camera produces) and
  silently break the court overlay + ball gating. ALWAYS audit before use:
  `tools/validate_new_clip.py --audit data/*_pts*.json` — it reads each clip's own
  resolution and fits the actual camera (`courtfit.cam_fit_quad`, roll allowed)
  rather than assuming a 70 deg lens.
  The decisive number is the FIT RESIDUAL — how far the corners sit from the
  nearest legal camera view. It separates the set cleanly:
  KNOWN GOOD (<2.5 px): yt_match40_pts 0.9, yt_rally2_pts 1.4, yt_court_pts 2.1,
  court_pts_refined 2.3, eala_pts_auto 3.7, am_hard_utr_pts 0.7.
  KNOWN BAD (>10 px): court_pts 38, yt_court_pts_refined 48,
  yt_court_pts_doubles 54, yt_court_pts_singles 91.
  demo30_pts was the worst at 565 px and is now RE-CALIBRATED to **0.5 px** — the
  lowest residual in the repo (Session G part 2). It is LOW-CAMERA, not degenerate.
  EVERY committed calibration now carries its verdict in an `_audit` key
  (`tools/validate_new_clip.py --audit <files> --stamp`), and
  `pipeline.calibrate_video` WARNS loudly when it loads one stamped DEGENERATE —
  the point being that these files used to fail silently. The stamp is inert:
  calibrate_video already strips `_`-prefixed keys, pinned by
  tests/test_calib_audit_stamp.py (which also fails if the degenerate set drifts).
  A LOW camera is not degenerate — it is the amateur case this project targets;
  what it costs is measurable DEPTH, so the audit reports that in metres via
  `calibration.reliable_court_span`. Note the primary 1080p gold clip
  `am_hard_utr` fits a **1.74 m** camera (hfov 86 deg, 0.7 px — good corners,
  low mount) and is measurable only to **court-y 7.5 m of 23.77 (32% of depth)**:
  it does not reach the net at 11.885 m. Treat any far-court number on that clip
  as detection recall, NOT as a measurement.
