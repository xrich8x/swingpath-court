# Court precision routes — what could pin the court to the precision P8 C1 demands, and how to prove it

**researcher, 2026-09-17. Assessment and test design. Nothing was run; no code was written.**
It answers `court-map-ceiling.md` (P8 C1). Court only, per the founder's ruling of 2026-09-17.

**Labels used throughout.** **PUBLISHED** = an external source, linked. **MEASURED** = a number this
project produced, with its evidence file. **ARITHMETIC** = my own calculation, which nobody has measured.
**JUDGEMENT** = my opinion, with a confidence.

**WHAT THE ARITHMETIC IS MEASURED AGAINST:** nothing. It is pinhole geometry at C1's camera:
1920×1080, hfov 100° so f = 805.5 px, mount 3.0 m, 6.0 m setback, on the centreline. So the far
baseline is D = 29.77 m from the camera and the net is 17.885 m away.

---

## 0. The answer to question 2, first

**Yes, in image space, for a line the camera can see. The part that survives is BIAS, not noise, and
it is multiplied by the same D/h and D²/(f·h) factors that sank the four-tap.**

1. **A visible line decides its own call. The court model is not needed for that.** A projective map
   keeps points on the same side of a line, for ground points in front of the camera. So "is the
   bounce beyond the far baseline?" can be answered from where the far baseline sits in the image.
   The model's prediction of that line is not required. The court contributes only the error in the
   **measured** line position, converted to metres at the local scale. (ARITHMETIC. This holds
   exactly for a planar court.) **The regulation court model is needed for two things only:** lines
   the camera cannot see, and a metric landing position. Neither needs the model's guess where the
   paint itself can be measured.
2. **What the far baseline needs is a line-position precision, not a tap precision.** At D = 29.77 m,
   1 px of row error is 0.30-0.37 m down-court (the sec² term depends on where the pitch puts the
   line). So **5 cm needs about 0.14-0.17 px of line offset.** C1's "0.07-0.11 px" is a per-corner
   tap figure: a four-point fit amplifies it. The two are not the same number, and the line figure is
   the one a line measurement has to hit. (ARITHMETIC, consistent with C1's 0.69 m worst-point p90
   per px of tap noise.)
3. **Noise can be averaged below that. Bias cannot.** §1 shows that about 45 independent profile
   samples along the line reach the bar under white noise. A static camera gives hundreds of columns
   times many frames, so **noise is not the binding term** (JUDGEMENT, 0.7). What survives however
   precisely the line is located:

| Surviving error | How it reaches the far baseline | Size (ARITHMETIC unless marked) |
|---|---|---|
| **Court surface not planar** at the far baseline | A painted line dz above or below the fitted plane is displaced along the ray by **dz·D/h ≈ 10·dz** | ASBA allows **3 mm under a 3 m straightedge** (PUBLISHED, [ASBA §2.I](https://www.novasports.com/asba-guidelines-for-tennis-court-construction/section-2i/)). 3 mm gives **3 cm**. 5 mm uses the whole 5 cm budget. **This affects the MODEL's prediction of the far baseline, not a direct measurement of it** (point 1). |
| **Which edge is "the line"** | Dimensions are measured to the **outside** of the lines. The baseline may be **up to 10 cm** wide, other lines 2.5-5 cm (PUBLISHED, ITF Rules via [Wikipedia](https://en.wikipedia.org/wiki/Tennis_court)) | A profile fit finds the paint's **centre**, which is w/2 = 2.5-5 cm inside the outer edge. At the far baseline that is **0.07-0.14 px, as large as the whole budget**. Width must be measured, on near lines where it can be resolved, or assumed. It must be modelled, not ignored. |
| **Lens distortion residual** at the top of the frame, where the far baseline sits | Pixel error × 0.36 m/px | Ultra-wide barrel distortion is tens of px at the frame edge. A 1% model error there is more than 0.3 px, over twice the budget. |
| **Intrinsics wrong** (f, principal point) | Enters the model directly. C1: **5° of hfov error ≈ 40 cm** with perfect taps (MEASURED, `court-map-ceiling.md`) | 1% of focal ≈ 0.56° ≈ 4.5 cm on C1's slope. Factory iPad focal lengths are off by 6-7% on two devices, which is ~30 cm (PUBLISHED, below). |
| **Thermal drift of intrinsics** | Principal-point shift looks like camera rotation | Android phones with autofocus fixed: **focal moved 1.0-5.6 px, principal point up to 29 px** at full resolution, with CPU temperature up 10-26 °C (PUBLISHED, [Elias et al., Sensors 2020](https://pmc.ncbi.nlm.nih.gov/articles/PMC7038322/)). **Not iPhone.** Even 1% of that is over the budget, so the fit must be repeated, not done once (§6). |
| **Net tape next to the far baseline in the image** | A strong white bar a few px away biases a profile fit, or captures it outright | The tape top covers ground out to **D·h/(h−0.914)**. At **h = 3.0 it sits ~13 px below the far baseline. At h = 2.5 (the protocol's A-low cell) it sits ~0-4 px below it**, inside the blur scale, and at the far doubles corners it nearly touches. At h = 3.5 the gap is ~21 px. |
| **Compression erasing the line** | The far baseline is **0.14 px tall** (0.27 px if 10 cm). Its integrated contrast is about C·0.14 DN·px, **a ~1-px bar of roughly 8 DN** | HEVC at phone bitrates may quantise that away. **Unknown. This is the cheapest thing to falsify (§7).** |

**So the whole-court fit fixes the far baseline in pixel terms only if the model is exact. The direct
measurement fixes it only if the line survives compression and its bias terms stay under ~0.05 px.**
Both are testable. Neither is established.

**Where it cannot be done at 1080p / 3 m, what it would take** (per the founder's directive to find
the way rather than shrink the product). Every lever multiplies the allowed pixel error: **mount
height ×h, resolution ×f, a telephoto far-half framing ×f.** A 4K calibration still or frame doubles
f; a 3.5 m mount is ×1.17. These scale the bar. They do not remove the bias terms.

**Confidence in §0 as a whole: 0.65.** It would move up if the §7 test's clean arm passes and the
compression arm keeps the far baseline visible. It would move down if HEVC erases the line or the
distortion arm cannot close to 0.05 px.

---

## 1. Achievable sub-pixel line precision (question 1)

**PUBLISHED**
- Steger, "An unbiased detector of curvilinear structures", **IEEE TPAMI 20(2), 1998**
  ([ACM DL](https://dl.acm.org/doi/10.1109/34.659930)). It returns sub-pixel line position **and
  width**, and removes analytically the bias that asymmetric contrast on the two sides would otherwise
  cause. That matters here because a baseline has court on one side and run-off on the other.
- Steger, "Evaluation of subpixel line and edge detection precision and accuracy", ISPRS Comm. III,
  1998 ([PDF](https://mv.in.tum.de/_media/members/steger/publications/1998/isprs-comm-iii-98-steger.pdf)).
  The abstract says analytical noise formulas were confirmed on synthetic images, and **"subpixel
  accuracy better than one tenth of a pixel is possible in typical industrial inspection tasks"** on
  real images. **Transfer caveat:** industrial inspection means controlled light, high contrast and
  uncompressed images. Only the abstract was readable; the full PDF does not extract here.
- Trujillo-Pino et al., "Accurate subpixel edge location based on partial area effect", **Image and
  Vision Computing 31(1):72-90, 2013**
  ([ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S0262885612001850)). It models
  area sampling explicitly, which is the right model for a line narrower than a pixel. Claims hold
  under noise and blur. Numbers were not read.
- Datta, Kim & Kanade, ICCV Workshops 2009 ([CMU PDF](https://www.ri.cmu.edu/pub_files/2009/10/Calib.pdf)).
  Undistorting and unprojecting to a fronto-parallel plane, then re-localising the features, cut
  reprojection error by about 50% against OpenCV. **The same idea applies here:** measure the lines
  in an undistorted, rectified frame and iterate with the fit.
- **Not found:** any published sub-pixel line-localisation number on compressed phone video of sports
  lines, or any paper on what HEVC does to features narrower than a pixel. Treat that as a gap in the
  literature.

**ARITHMETIC for our geometry** (f = 805.5, h = 3, setback 6):

| Line | Range D | Paint tall in image | Length in image | 5 cm down-court equals |
|---|---|---|---|---|
| near baseline | 6.0 m | **~2.8 px** | about the frame width | ~3.4 px |
| far service line (**seen through the net mesh** at h = 3) | 24.3 m | ~0.20 px | ~275 px (singles/service) | ~0.20 px |
| **far baseline** | 29.8 m | **~0.14 px** (0.27 px if 10 cm) | **~295 px** doubles, 222 singles | **~0.14 px** |

- **Precision from averaging along the line.** Take a Gaussian profile of amplitude a, blur σ_s, and
  white noise σ_n. The Cramér-Rao bound on its position per column is
  **σ_pos = σ_n·√(2σ_s/√π) / a**. For the far baseline: contrast C ≈ 150 DN × 0.136 px of width
  gives about 20 DN·px, so a ≈ 8 DN at σ_s = 1 px. With σ_n = 2 DN, **σ_pos ≈ 0.27 px per column.**
- **What the bar needs.** A fitted line's error at its ends is about twice its error at the centre,
  and p90 is 1.645σ, so reaching 0.14 px at p90 at the worst point needs the centre σ at about
  **0.04 px**. That takes **about 45 independent samples.** The ~295 columns of one frame are not
  independent: PSF and compression blocks correlate them, leaving perhaps 20-75 effective samples.
  **One frame is marginal. Thirty or more frames of a static court are not.** Frame noise is
  independent between frames, but compression artefacts may not be.
- **What degrades it,** most dangerous first, for our regime (JUDGEMENT):
  1. **compression**, which can erase the feature, not merely blur it;
  2. **the net tape and mesh** in the same image band, which can capture the fit;
  3. **distortion** near the top of the frame;
  4. **paint-width convention**;
  5. **worn paint, and shadows crossing the line.** A shadow edge running along a line biases it; one
     crossing it only removes samples;
  6. **players standing on lines.** This mostly removes samples, and a pre-play clean window avoids it;
  7. **motion blur.** None for a static camera and static paint, except mount vibration.

---

## 2. Field of view and the lens on iPhone (question 3)

**PUBLISHED / platform facts:**
- **Per-frame intrinsics.** `AVCaptureConnection.isCameraIntrinsicMatrixDeliveryEnabled` attaches
  `kCMSampleBufferAttachmentKey_CameraIntrinsicMatrix` to video buffers
  ([Apple docs](https://developer.apple.com/documentation/avfoundation/avcaptureconnection/2875903-cameraintrinsicmatrixdeliveryena)).
  **For `builtInUltraWideCamera`, `isCameraIntrinsicMatrixDeliverySupported` was reported `false`**
  ([Apple forum 666517](https://developer.apple.com/forums/thread/666517), a developer in Nov 2020,
  unanswered, so it may be out of date). A 2020 thread reports iPad fx/fy **varying with focus
  locked** ([forum 654288](https://developer.apple.com/forums/thread/654288), unanswered).
- **Distortion table.** `AVCameraCalibrationData` carries `lensDistortionLookupTable`, a 1-D radial
  table ([SDK header](https://github.com/xybp888/iOS-SDKs/blob/master/iPhoneOS13.0.sdk/System/Library/Frameworks/AVFoundation.framework/Headers/AVCameraCalibrationData.h)).
  **An Apple Media Engineer confirmed (Dec 2023) that it is delivered only on the PHOTO output, and
  only with `virtualDeviceConstituentPhotoDeliveryEnabled = YES`, content-aware distortion correction
  OFF, and the device's `geometricDistortionCorrectionEnabled = NO`**
  ([forum 741815](https://developer.apple.com/forums/thread/741815), verbatim header text).
  **The video path has no documented distortion table.**
- **Geometric distortion correction (GDC) is on by default for the ultra-wide**
  (`AVCaptureDevice.isGeometricDistortionCorrectionSupported/Enabled`; search synthesis plus forum
  741815. The iOS version it arrived in was not verified.) Urban et al. found AVCaptureSession frames
  "already rectified and undistorted", **but on the front TrueDepth camera, not the rear ultra-wide**.
  The same paper found factory focal lengths **within ~1% on most iPads and 6-7% off on two**, and
  saw them change between iOS 14 and iOS 15 ([arXiv 2201.10865](https://ar5iv.labs.arxiv.org/html/2201.10865)).
- **Net effect.** With GDC on, video arrives nearly rectilinear, but nothing publishes how good
  Apple's correction is at the 0.1-px level, or what effective focal it leaves. With GDC off, the
  distortion table is available only from a photo, in photo pixel coordinates
  (`intrinsicMatrixReferenceDimensions`). **The mapping from photo pixels to 1080p video pixels
  (crop, binning, scaling) is undocumented, and it is a bias source in its own right.**

**Can the whole-court fit solve focal length itself?** (ARITHMETIC)
- **Yes, in principle.** For a single view of a plane with the principal point known and square
  pixels, H = K[r1 r2 t]. For our camera (centred, pure pitch) the orthogonality constraint
  h1ᵀωh2 = 0 is satisfied for any f and says nothing. The equal-norm constraint reduces to
  **cos²φ·(f²/f′² − 1) = 0**, which is uniquely f′ = f for any pitch short of looking straight down.
  **So f is identifiable.**
- **It is weakly conditioned.** To first order, a narrow view trades focal length against distance
  (the dolly-zoom ambiguity). Only second-order perspective breaks the trade, and that is stronger at
  a 100° field of view than at broadcast. **How well it is conditioned is not known; the test in §7
  measures it.**
- **Distortion.** Court lines are straight, so they constrain it (plumb-line). The shipped
  `calibration.estimate_k1` already estimates a division-model k1 by straightening pixel chains
  (`backend/swingvision/calibration.py:375-473`). f and k1 are correlated, so they must be fitted
  together.

**Routes for intrinsics, ranked** (JUDGEMENT):
- **(a) Fit f and k1 jointly inside the whole-court fit, with priors from (b).** Most general, no lab
  step.
- **(b) A per-iPhone-model lens table** that we measure once with a checkerboard (Zhang). It is a
  prior, not truth, because units vary by about 1% (Urban, on different cameras).
- **(c) A calibration photo at setup through the photo output with GDC off,** with video also
  recorded with GDC off. That gives Apple's own table, but it depends on the undocumented
  photo-to-video mapping, and it must be checked on a device before anyone relies on it.
- **Not recommended:** the 70° default, or trusting GDC to be exact.

---

## 3. How SwingVision and comparable products set up the court (question 4)

- **SwingVision: not publicly disclosed.** Their setup guide covers placement only: behind the
  baseline, a mount-height ladder that gates line-call coverage, and the net tape inside a pink
  rectangle for ground mode (PUBLISHED, [set-up guide](https://swing.vision/guides/set-up-your-recording),
  read via r.jina.ai). No text on corner taps, refinement or re-checking was found.
  - Their patent (US11893808B2) describes a network that maps object pixels plus **court-line pixels
    as reference features** straight to 3D, which reads like automatic, line-based referencing.
  - Their ML job ad asks for "intrinsic and extrinsic calibrations, projection matrices, ray casting"
    (see `swingvision-teardown.md`).
  - **JUDGEMENT (0.6):** the calibration is automatic and line-based, with no user taps. No source
    establishes any drift re-check. A marketing summary claiming the court is detected from "four
    sidelines and two baselines" came from a search engine mixing sources and **is not attributable**.
- **PB Vision (pickleball):** "CourtFocus … built-in lock-on indicator", and "the camera must be
  stable and not move during filming" (PUBLISHED, [help page](https://help.pb.vision/articles/1108176-framing-and-court-alignment-guidelines)).
  The method is not disclosed.
- **Wingfield:** its configuration page covers camera positioning only
  ([help](https://help.wingfield.io/en/baseline-camera-configuration)). It is a fixed installation.
- **In/Out:** a court model from a homography, in its patent (see the teardown).
- **Marketing only:** a review says Baseline Vision's "trajectory calculations compensate" for
  imperfect line calibration ([tennisleo](https://www.tennisleo.com/baseline-vision-review/)).
- **Finding:** no product publishes its court-calibration precision, method or drift policy.
  **Nothing here can be benchmarked against.**

---

## 4. Rule 3: the closed record, read row by row (question 5)

| Closed row | What it measured, against what | Does it speak to sub-pixel precision? | This proposal vs it |
|---|---|---|---|
| **Building the court quad from DETECTED LINES** | Unseeded angular clustering of Hough lines into two families, then intersection. Best quad **68-256 px@640** from **human corner clicks**. Killed because converging sidelines do not cluster. | **No.** It is a grouping / search failure, measured roughly 500-2000× coarser than 0.14 px@1920. | **Different.** No clustering: the taps give the correspondence. |
| **Snapping a near-correct court onto detected lines** | Each model line snapped independently to its nearest Hough line, then intersected. Median **70.5 px@640** vs clicks. | **No.** It is an assignment-robustness failure. | **Partly overlaps, and this is a warning.** Measuring each line inside a narrow band around the seeded model IS a snap-like step. **The net tape 0-13 px from the far baseline is exactly the parallel confuser that kills independent snapping.** The test must include it (§7, clutter arm), and the fit must be joint and robust. |
| **Least-squares over ALL matched line correspondences** | **Given the TRUE correspondence**, nonlinear LS over the shipped detector's **HoughLinesP segments from a binary mask**, at 640-3840 px. Scored against **the human's 4 corner clicks (~5.8 px@640 neighbourhood)**. LS-geom 19.80 vs 4-point 17.10 px@640, p = 0.97. It fitted the lines at **3.01 px, tighter than the human homography's 6.44**. | **No. Both its input and its ruler are too coarse.** Hough segments are quantised to a pixel or worse, and the truth is ±~17 px@1920, about **100× the 0.14 px in question**. Its §3 result (the fit agrees with the lines better than the clicks do) is **equally consistent with "the lines are more accurate than the clicks"**. That decomposition was never run. My own 2026-09-05 assessment gave "mostly irreducible" only **0.45**. | **Same fitting principle, and that principle was shown not to be the limiter.** Different evidence (sub-pixel profile fits on raw luminance, not Hough on a mask) and a different ruler (exact synthetic truth, then F-marks). **The claim being tested is not that LS beats 4 points. It is that sub-pixel measured lines beat clicks.** |
| **Court AUTO-detection generally** | Every classical and learned branch, graded on **search and acceptance** against an 8.1 px@640 bar on click gold. "~6.4 px ceiling" = the line detector's **disagreement with click-derived truth**. | **No.** 6.4 px is agreement with a ~5.8 px ruler. The closure is about finding the court without a human. | **Not auto-detection.** A human still taps. The fit refines; it does not search. It does not reopen v1's product decision (manual setup). |
| *Lookalike:* **Clean plate / MTI** (retired) | Temporal median as input to the **auto-detector search**, 11.5 px bar. | No. | Temporal averaging here is **noise reduction for a profile fit**, graded per line in cm. Different metric, different stage. |
| *Lookalike:* **fitted-hfov as a calibration reference** (FAILS) | A **60-90° window gate** on the focal length that `cam_fit_quad` fits from **4 clicked corners**. On correct clips the fitted hfov spanned **23-104°** (MEASURED, `fitted-hfov-reporting-gap.md`). | No. It is a gate, with no known-truth focal. | **A warning that 4-point focal is poorly determined.** The §7 f-free arm measures whether a many-line fit with distortion does better, against exact truth. It is not a gate. |

**Verdict: none of the four named rows speaks to sub-pixel precision.** All were scored in px@640
against human clicks, and three are about search or robustness. **The line-level question has never
been asked here.** C2 found that the court gold holds no independently clicked non-corner points, so
there has never been an instrument that could ask it. **The proposal survives rule 3, but only as a
new INSTRUMENT with the snap failure mode built in as a test arm.**

---

## 5. Ranked routes

| # | Route | What pins the court (rule 7) | Plausible precision, our geometry (ARITHMETIC/JUDGEMENT) | Closed-row check | Cost |
|---|---|---|---|---|---|
| **R1** | **Seeded whole-court fit to sub-pixel line measurements.** Taps seed it. Steger-style profile fits in narrow bands around the seeded projection, averaged over a pre-play static window (e.g. 5 s = 300 frames). A joint robust fit of pose + f + k1 (± principal point) to all lines under regulation dimensions. **For a VISIBLE line, its measured image position is the call authority; the fitted model covers unseen lines and metric position.** | Measured paint positions + the regulation court + planarity. For visible-line calls, the paint alone. | **Near lines: comfortably under 5 cm.** Far service line (through the mesh) and far baseline: **noise ~0.02-0.05 px after averaging, so 1-2 cm; the bias terms in §0 decide it.** Confidence 0.5 that the far baseline meets 5 cm p90 at 3 m in the clean synthetic arm with distortion. 0.3 that it survives compression plus the net tape at 2.5 m. | Survives (§4), with the snap confuser as a mandatory arm. | Classical and CPU-only: ~10⁵ 1-D profile fits at setup, well under a second with Accelerate/Metal (JUDGEMENT, **not measured on an A13**). **No ANE, no model, no training data.** |
| **R2** | **Intrinsics priors:** a per-model lens table (checkerboard) and/or the setup photo's `AVCameraCalibrationData` with GDC off, feeding R1's f/k1 as priors. | Lab or Apple calibration of the lens. | Takes f from "unknown, 5° = 40 cm" to about ±1% (≈ 4.5 cm by C1's slope) **before** R1 refines it. | New. Not the fitted-hfov gate. | One lab session per iPhone model, or a device spike to verify the photo-to-video mapping. |
| **R3** | **High-resolution calibration frames.** Capture the setup window at 4K (or a 12 MP ultra-wide still), fit there, and map to 1080p60. | As R1. | f doubles, so every pixel bar doubles. The noise term improves about 2√2×. Angular bias terms do not improve. | New. | The format switch may change crop and GDC, **a mapping bias to verify on a device**. |
| **R4** | **Continuous image re-fit as the drift detector,** with the IMU as a bump trigger (§6). | As R1, repeated. | Detects rotation at the ~0.01° level and **absorbs thermal intrinsics drift, which no IMU can see.** | New. It differs from the P4(ii) observation (§6). | A few lines per N frames, in milliseconds (JUDGEMENT). |
| **R5** | **Geometry multipliers:** mount height, 4K throughout, telephoto far-half framing (B), or a second phone (v2). | Each scales f·h. | Required px bar ×h/3 or ×f/805. | Already on record (monocular-3d routes, the teardown). | Product and founder decisions. Listed so they are not forgotten, **not as a narrowing**. |
| **R6** | **Learned sub-pixel line heatmaps** (M-LSD-class, on the ANE). | Learned line positions. | **Attacks robustness (finding the line), not the bias floor.** Training targets at sub-pixel accuracy would have to come from synthesis. | Near the closed CourtNet / segmentation reasoning. | Training + export + ANE budget. **Fund only if R1 fails on robustness, not on precision.** |
| — | **User-placed markers on the court** | Physical tape | High | — | **Violates "ships on a bare court"** (CAPTURE_PROTOCOL §0). **Truth only (§8).** |

---

## 6. Drift (question 6)

- **What precision drift detection needs.** Far-baseline 0.14 px ≈ **0.01° ≈ 0.17 mrad** of camera
  rotation (ARITHMETIC).
- **The IMU cannot certify that.** Static phone tilt accuracy is **0.05-0.2° at best, up to ~2° across
  devices** (PUBLISHED, Behavior Research Methods 2020; see `sensor-court-priors`). Gyro bias
  integrates over minutes.
  - **The IMU is still the right bump detector:** instant, free, and it catches any knock larger than
    ~0.05°.
  - **It cannot see thermal intrinsics drift at all.** In Elias et al. the principal point moved up to
    29 px while the phone sat still (PUBLISHED, Android).
- **The image can see it.** A seeded sub-pixel re-measurement of a few long lines, every N frames,
  sees rotation and intrinsics drift alike (they look the same in the image, and the re-fit absorbs
  both). This is R4.
- **The P4(ii) record does not contradict this.** "Motionless tripods disagree with themselves" was
  measured on the **unseeded auto-detector's re-detections** (~24-30 px@640, `camera-motion-vs-court-agreement.md`),
  which is a mixture over hypotheses. It says nothing about a seeded sub-pixel tracker. **The
  conclusion that drift can only be seen by the IMU is premature for that reason.**
- **Recommendation (JUDGEMENT, 0.7): use both.** IMU bump → immediate re-fit, with calls held. The
  periodic image re-fit is the precision drift signal. Calibrate after thermal warm-up, or keep
  re-fitting.
- **SPEC §1's trigger is inconsistent with SPEC §3, reported and not edited.** "15 px sustained for
  3 frames" is **~5.4 m at the far baseline**, about 100× coarser than a 5 cm court needs. It catches
  gross moves only. **Proposed text for the lead / pm:** *"SPEC §1's 15 px drift trigger is ~5 m at
  the far baseline at 1080p/3 m; a sub-5 cm court needs a per-line re-fit tolerance of ~0.1 px on far
  lines (researcher, court-precision-routes.md §6)."* That is a SPEC question for the founder; this
  file does not change it.

---

## 7. THE PRE-REGISTERABLE SYNTHETIC TEST — "CP1", for backend-dev to build

**Why this is a new instrument, not a re-run of a closed row.** Every closed line-fit row used Hough
segments and a ~17 px@1920 human ruler. CP1 has exact truth, resolving well under 0.01 px and 1 mm,
a sub-pixel luminance measurement, and a seeded fit. **It asks a question no closed row could
resolve: can measured paint beat clicks by ~100×?** It keeps the one closed failure mode that does
apply (parallel-confuser snapping) as an arm that must pass.

**What it measures against:** exact projected court geometry from a known synthetic camera. No
labels, no model output.

### Configuration (primary arm "P")
- **Camera:** C1's `height_curve.frame_the_court` at 1920×1080, setback 6.0 m, centreline, **h = 3.0 m**,
  true hfov 100°, roll 0.
- **Lens:** **distortion ON.** Render with a **polynomial (Brown k1, k2) model** equivalent to about
  30 px of edge displacement. The fitter uses the division model. **The two models are deliberately
  different** so the fitter is not grading its own lens model.
- **Scene:** regulation doubles court, flat. Paint 5 cm everywhere (baseline 5 cm). Positions are
  measured to the OUTSIDE of lines, per ITF.
  - Surface and run-off in different colours. Line contrast drawn per trial from 60-160 DN.
  - **Area-sampled at 16×16 supersampling**, then Gaussian PSF σ drawn from 0.7-1.2 px.
  - **Net:** tape 0.914 m at centre, sagging to 1.07 m at the posts, 5 cm white tape, dark mesh.
    **Clutter ON:** fence and a roof-truss line above the court.
- **Sensor and codec:** Poisson-Gaussian noise (σ ≈ 2 DN at mid-grey). **30 frames** of independent
  noise, **encoded by a real encoder** (ffmpeg libx265, 1080p60, ~16 Mbps, main profile), then decoded.
  **Not a filter meant to imitate compression.**
- **Seed:** the four doubles corners perturbed at C1's rungs: 1, 4 and **14.78 px** per-axis σ.
  14.78 is primary.
- **Method under test:** R1 as specified in §5. Its internals are backend-dev's to design, **and are
  frozen before the scored run.**
- **Trials:** ≥ 400 per configuration, seeded (`--seed` on every arm), `recipe_stamp` recorded.

### Scoring, identical to C1
- For each of the 14 line halves, take 11 points and the **worst perpendicular ground error** per
  trial, then **p90** over trials.
- Two readouts:
  - **(M)** the fitted model's projection of each line;
  - **(L)** the measured line itself, for lines visible in that trial. L is the call authority.
- Also reported:
  - f error, k1 error and fitted height;
  - the far-baseline **image-space** offset error in px;
  - the per-line fraction of trials where measurement locked onto the net tape instead of the
    baseline: **perpendicular image error > 2 px = captured.**

### Bars (pre-registered here, before anything is built)
- **PASS:** arm P, **every line p90 ≤ 5 cm on readout L where visible, and on readout M for all
  lines.**
- **KILL, per line:** p90 > **10 cm** on arm P. That line is dead for R1 at 1080p/3 m. The verdict is
  **per line**: the far baseline and far service line may die while the others pass, and that is a
  result, not an INDETERMINATE.
- **INDETERMINATE:** 5-10 cm.
- **Instrument controls, which must pass before any bar is read:**
  1. **zero noise, zero distortion, zero seed noise:** every line < 5 mm;
  2. **noise only** (no codec, no distortion, no clutter): every line p90 ≤ 2 cm, else the
     implementation is suspect;
  3. **injected known shift:** translate the rendered court 0.10 px vertically and recover
     0.10 ± 0.02 px on the far baseline.

### Arms (each changes ONE variable from P)

| Arm | Variable | Why |
|---|---|---|
| A1 | distortion OFF | isolates the lens term |
| A2 | distortion model **matched** (render with division) | shows how much the model mismatch costs |
| A3 | codec OFF | **the cheapest falsifier:** does HEVC erase a 0.14 px line? |
| A4 | frames 1 / 300 | the noise-averaging curve |
| A5 | baseline paint **10 cm** | an ITF-legal wider baseline |
| A6 | **h = 2.5** / 3.5 | net-tape proximity: **~0-4 px at 2.5 m**, 21 px at 3.5 m |
| A7 | clutter OFF (no net tape or mesh) | the snap-confuser cost |
| A8 | f **known** (vs free in P) | conditioning of self-calibration |
| A9 | principal point shifted ±10 px, f free | thermal drift, scaled from Elias et al. |
| A10 | court **non-planar:** far baseline 3 mm low (the ASBA limit), plus a 1% single-plane slope | the dz·D/h amplifier. Readout L should be immune, M should not |
| A11 | a shadow edge crossing two lines at 30° | a real outdoor degradation |
| A12 | seed rungs 1 / 4 px | shows whether the seed matters once the fit converges |

**Known ways CP1 flatters R1, stated now:**
- the PSF is Gaussian and known in form;
- the court is exactly regulation and, except in A10, flat;
- paint is uniform, not worn;
- no players, no rolling shutter, no OIS, no temporal noise reduction;
- libx265 is not Apple's hardware encoder;
- the distortion is radially symmetric;
- the principal point is centred, except in A9;
- the camera sits on the centreline with roll 0. Off-centre mounts are not tested;
- fence and trusses are simple geometric stand-ins.

A pass says the mechanism **can** work. It does not say it **does** work on a phone. §8 is what says
that.

**Cost (JUDGEMENT):** renderer plus encode harness plus R1, about 1-2 build days. Runtime is
dominated by encoding, about 400 × 30 frames per arm. Use fewer trials for the encoded arms and say
so, rather than skipping them.

**Kill condition for the ROUTE, not only the test:** if **A3 (codec off) passes but P fails on the
far lines** because the far-baseline profile amplitude after encoding is below noise, R1 is
compression-bound at 1080p. The next step is then R3 (a 4K / still calibration window), **not
tuning.**

---

## 8. What truth could validate it on REAL footage

1. **The F-marks at the court visit** (`CAPTURE_PROTOCOL.md` §3.3). They are independent of the four
   taps, **and F8 sits on the far baseline**.
   - **Score in IMAGE space:** project each F-mark's taped ground position through the fitted model
     and compare it with the F-mark's measured pixel. The ±10 mm placement is only ~0.03 px at the
     far baseline, so the placement is fine.
   - **What limits it is locating the mark in the image.** A 10 cm square at 30 m is **2.7 px wide
     and 0.27 px tall**, so its corner cannot be located vertically to 0.1 px. **Proposed protocol
     addition, for pm/lead and not applied here:** at the far end, lay **down-court-elongated
     marks**, e.g. a 1.0 m × 5 cm strip along y whose two ends are taped (~2.7 px tall), plus one
     strip lying on the far baseline's outer edge.
2. **Measure the court itself at the visit** (a lab instrument, not the product):
   - the actual baseline and sideline lengths and paint widths, by tape;
   - **surface height at the far baseline relative to the near court** with a laser level or water
     level, to ±2 mm. **That sets A10's real value;**
   - whether the court is regulation.
3. **A second lab camera** (allowed, CAPTURE_PROTOCOL §0) placed high or to the side. It sees the far
   baseline with good down-court conditioning and gives an independent line position.
4. **Direct blind clicks along lines** (C2's §5 design) **cannot validate sub-pixel precision**, since
   a human ruler is ~15 px. They can only catch gross real-footage failures. Keep them for that.
5. **Temporal self-consistency is NOT truth.** Repeat fits agreeing with each other measure precision
   only (rule 1). Report them as precision and never as accuracy.

---

## 9. For the PM — the tradeoff, decision left open

- **The four-tap cannot deliver SPEC §3. A seeded line fit might, and it costs no ANE budget and no
  training data.** The price is a pre-play static window (seconds, empty court) and a setup that
  captures a clean calibration.
- **The far lines are uncertain at 1080p / 3 m.** If CP1 kills them, the levers are:
  - a calibration window at 4K or from a still;
  - a higher mount;
  - a far-half telephoto;
  - a second phone.

  Each is a product decision. None is decided here.
- **SPEC §1's 15 px drift trigger** cannot protect a 5 cm court (§6). Changing it is the founder's
  call.
- **The A-low (2.5 m) protocol cell puts the net tape on top of the far baseline in the image.** That
  cell is still valuable as a failure-mode capture, but it will not test R1's far lines fairly.

## 10. Open questions

- Does Apple's HEVC encoder at 1080p60 keep a 0.14-px, ~8 DN line? **This is the cheapest thing to
  falsify:** A3 on synthetic data, then one real 1080p frame from the visit.
- Is ultra-wide intrinsic delivery still unsupported on iOS 18? Does GDC leave a residual at the
  0.1 px level? What is the exact photo-to-video pixel mapping? These need a device, and the
  sideload line is founder-paused.
- How well conditioned is f in a many-line fit at 100° hfov? CP1's A8 answers this.
- What is real hard-court non-planarity at the far baseline? The visit (§8.2) answers this.
- Is the thermal drift of iPhone intrinsics comparable to Elias et al.'s Android numbers? No iPhone
  source was found.

---

## LEAD ADDENDUM 2026-09-17 — verification and two pre-run fixes to CP1

**Verified by the lead.**
- **Arithmetic** at C1's camera (f = 805.5 px, h = 3 m, far baseline 29.77 m out): 1 px ~ 0.37 m
  down-court, so 5 cm ~ 0.14 px; far baseline ~295 px long; net tape ~12.6 px below the far baseline
  at 3 m and ~3.8 px at 2.5 m; surface height error amplified by D/h ~ 10.
- **Apple forum 741815:** an Apple Media Engineer confirms camera calibration data (intrinsics,
  lens distortion) is delivered only when geometric distortion correction is OFF; the header adds
  `virtualDeviceConstituentPhotoDeliveryEnabled` YES and `contentAwareDistortionCorrectionEnabled`
  NO. A video-output workaround is mentioned by the poster but not confirmed by Apple.

**Two fixes, made BEFORE anything is built, so nothing is chosen after seeing results:**
1. **Trial count.** §7 says ">= 400 per configuration" and also "use fewer trials for the encoded
   arms". Resolved: **400 trials on every arm.** An arm may drop to **200** only if its measured
   runtime at 400 would exceed 60 minutes, and that decision is recorded before its scored run.
2. **Build order (not a change to any bar).** Stage 1: renderer, encoder harness, the R1 fit, the
   three instrument controls, **arm P and arm A3 (codec off)** — the route-level kill condition lives
   in that pair. Stage 2: the other arms. Stage 1 is reported on its own so a route kill is not
   discovered two days in.

