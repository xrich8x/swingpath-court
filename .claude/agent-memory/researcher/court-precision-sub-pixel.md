---
name: court-precision-sub-pixel
description: Why a seeded sub-pixel line fit is the route to C1's court precision, the far-baseline bias budget, iOS intrinsics/GDC facts, and why the closed line-fit rows cannot speak to sub-pixel (2026-09-17)
metadata:
  type: project
---

Full writeup: `docs/evidence/court-precision-routes.md` (2026-09-17, answers P8 C1). Founder
ruling that day: court-only work. Do not re-derive any of the following.

**Why:** C1 showed a four-tap court is off by metres at the far baseline. This is the reasoning for
what could fix that, and the traps in it.
**How to apply:** start any court-precision question from here. The test to build is CP1 (§7 of the
writeup).

## Arithmetic (C1 camera: f = 805.5, h = 3, setback 6, far baseline D = 29.77)
- The far baseline's 5 cm paint is **0.14 px tall** (0.27 px if 10 cm), ~295 px long. The near
  baseline is ~2.8 px tall.
- **5 cm at the far baseline = ~0.14 px of LINE offset.** C1's 0.07-0.11 px is a per-TAP figure,
  amplified by the 4-point fit. Do not confuse the two.
- The Cramér-Rao bound per column is ~0.27 px (σ_n = 2 DN, a = 8 DN). The bar needs ~45 independent
  samples, so **noise can be averaged away over a static window. BIAS binds.**
- **Bias amplifiers:**
  - non-planar surface **dz·D/h ≈ 10·dz** (ASBA allows 3 mm per 3 m);
  - paint-centre vs outer-edge convention, 2.5-5 cm (0.07-0.14 px);
  - distortion residual at the top of the frame;
  - thermal intrinsics drift;
  - net tape;
  - HEVC erasing a ~8 DN, 1-px bar.
- **Net-tape top covers ground to D·h/(h−0.914).** At h = 3 it sits ~13 px below the far baseline;
  **at h = 2.5 (protocol A-low) ~0-4 px, effectively on it;** at 3.5, ~21 px.
- **Projection preserves sidedness.** A VISIBLE line's measured image position decides its own call.
  The regulation model is needed only for unseen lines and metric landing.
- For a centred pure-pitch view, **f is identifiable from one plane** (the equal-norm constraint;
  orthogonality is vacuous). It is weakly conditioned by the dolly-zoom trade.
- Far baseline 0.14 px = 0.01° of rotation. **The IMU cannot certify that; the image re-fit can.
  SPEC §1's 15 px trigger is ~5.4 m at the far baseline** (reported to the lead, not edited).

## Rule-3 reading (settled)
- The closed rows (quad-from-lines, snap, LS-all-lines, auto-detection generally) were all px@640
  against ~5.8 px clicks, using Hough segments. **None speaks to sub-pixel.**
- **The snap row IS relevant as a failure mode:** a parallel confuser (the net tape) captures an
  independent narrow-band line match. It must be a test arm.
- Lookalikes: clean-plate (search input, retired) and fitted-hfov (a 60-90° gate on 4-click focal,
  spread 23-104°).

## Published facts, verified 2026-09-17 (do not re-fetch)
- **The Apple Media Engineer (forum 741815, Dec 2023):** AVCameraCalibrationData
  (lensDistortionLookupTable) comes **only on the photo output**, with constituent delivery ON, CADC
  OFF and **GDC OFF**. Forum 666517 (2020, a user): ultra-wide intrinsic-matrix delivery unsupported.
  GDC on the ultra-wide is on by default (iOS version unverified).
- Urban et al., arXiv 2201.10865: AVCaptureSession frames arrive undistorted. **FRONT TrueDepth
  cameras**, factory focal within ~1%, 6-7% off on 2 iPads.
- **Elias et al., Sensors 20(3):643, 2020 (PMC7038322), ANDROID:** principal point moved up to 29 px
  and focal 1-5.6 px with warm-up, autofocus fixed.
- Steger TPAMI 1998 (unbiased, returns width too) and ISPRS 1998 ("better than 1/10 px" in industrial
  inspection, abstract only; the PDF does not extract). Trujillo-Pino IVC 2013. Datta/Kim/Kanade ICCVW 2009.
- ITF: baseline up to 10 cm, others 2.5-5 cm, measured to the outside. ASBA §2.I: 1/8" in 10'; slope
  0.83-1% in one plane.
- **SwingVision, PB Vision and Wingfield do not disclose their court-calibration method.** Searched;
  don't repeat.

Related: [[monocular-3d-geometry]], [[court-detection-negatives]], [[sensor-court-priors]],
[[swingvision-public-method]], [[amateur-court-literature]]
