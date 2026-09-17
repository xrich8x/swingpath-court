# CP1 stage 1 — can a whole-court fit to the painted lines place the court? On a rendered court: YES, every line.

**backend-dev, 2026-09-17.** Tool: `tools/court_fit_cp1.py`; tests: `backend/tests/test_court_fit_cp1.py`.
Spec: `court-precision-routes.md` §7 (CP1), route R1 in §5, and the LEAD ADDENDUM at the end of that file.
Scored runs used internals frozen at commit **`4ac52fc`**. Every output JSON stamps that commit and
`tool_dirty_at_run: false`.

**WHAT EVERY NUMBER HERE WAS MEASURED AGAINST:** exact projected court geometry from a known synthetic
camera (C1's camera). That means the true ground coordinates of 11 points on each of C1's 14 line
halves, pushed through the true lens. No labels, no model output, no footage.

**WHAT PINS THE COURT (rule 5 / old rule 7):** four things pin it:
- the measured paint positions;
- the regulation doubles court (ITF: positions to the OUTSIDE of lines, 5 cm paint);
- a flat ground plane and a known, centred principal point;
- one paint-to-surface contrast ratio (kappa) and one blur (sigma), both measured on the two near lines.

Focal length and one division-model distortion coefficient are **fitted**. The four corners only
**seed** the fit.

**THE SEED is a rough first guess of the four doubles corners, as an automatic court detector would
supply it:**
- exact corner pixels plus a per-axis Gaussian error of **σ = 14.78 px @1920** (the primary rung;
  1 and 4 px are stage-2 arm A12);
- an automatic detector's corner error in this repo has been of the same order: ~6.4 px @640, which is
  ~19 px @1920.

## Verdict (bars pre-registered in §7 and the lead addendum; not moved)

| Bar | Result | Verdict |
|---|---|---|
| **PASS:** arm P, every line p90 ≤ 5 cm on readout L (where visible) AND on readout M | worst L: **far baseline 3.58 cm**, far service line 3.42 cm. Worst M: far baseline 0.97 cm. All 14 halves are visible and all 14 were measured in all 400 trials | **PASS — all 14 lines** |
| **KILL per line:** p90 > 10 cm on arm P | no line | not fired |
| **INDETERMINATE:** 5-10 cm | no line | — |
| **Route-level kill:** A3 passes but P fails on the far lines (compression-bound) | P passes | **not fired.** R3 (a 4K / still calibration window) is not required by this result |

**What this says:** on a rendered 1080p court from a 3 m mount, with real libx265 compression, the
lens model deliberately wrong, net-tape and fence clutter, and a first guess ~15 px off per corner,
a seeded whole-court fit places **every line within 3.6 cm at p90**. The C1 four-point model missed
the same far baseline by **14 m** (2D) / **7 m** (3D) at the same corner error. **The mechanism CAN work.
It has not been shown to work on a phone** (§8 of the routes file; flattering assumptions below).

**The margin is thin, and it sits in the far lines under compression.** The far baseline's L p90 is
3.58 cm against a 5 cm bar, which is 72% of the budget.

## Instrument controls — all three passed before any bar was read

The control readings were declared in `.claude/journals/backend-dev.md` before any code was written.

| Control | Setting | Criterion | Result |
|---|---|---|---|
| **1** | zero noise (no 8-bit quantisation either), zero distortion, exact corners, no codec, no clutter; n = 20 | every line, both readouts, max over trials < 5 mm | max **0.12 mm (M)**, **0.57 mm (L)**: **PASS** |
| **2** | noise on (σ ≈ 2 DN), no codec, no distortion, no clutter, first guess σ 14.78 px; n = 400 | every line p90 ≤ 2 cm, both readouts | worst **5.6 mm** (far service line, L), 0 fit failures: **PASS** |
| **3a** | control 1 + rendered court translated **+0.10 px** vertically; scored against the unshifted truth; n = 20 | every trial's far-baseline L offset within 0.10 ± 0.02 px | **0.0997-0.1001 px**: **PASS** |
| **3b** | control 2 + the same shift, paired trial-for-trial with control 2; n = 100 | mean paired difference within 0.10 ± 0.02 px | L **0.0993** (sd 0.0023); M 0.1003: **PASS** |
| 2-seed0 (descriptive only) | control 2 with exact corners; n = 100 | none | worst L p90 5.9 mm (far baseline). The first guess costs nothing once the fit converges |

Per line, in mm:

| Line | ctl1 M max | ctl1 L max | ctl2 M p90 | ctl2 L p90 | ctl2-seed0 L p90 |
|---|---|---|---|---|---|
| near_doubles_sideline_L | 0.01 | 0.02 | 0.04 | 0.06 | 0.05 |
| near_doubles_sideline_R | 0.01 | 0.01 | 0.04 | 0.05 | 0.04 |
| near_singles_sideline_L | 0.00 | 0.00 | 0.03 | 0.05 | 0.05 |
| near_singles_sideline_R | 0.01 | 0.01 | 0.03 | 0.06 | 0.04 |
| far_doubles_sideline_L | 0.02 | 0.18 | 0.09 | 0.95 | 0.97 |
| far_doubles_sideline_R | 0.02 | 0.09 | 0.09 | 0.98 | 0.76 |
| far_singles_sideline_L | 0.01 | 0.16 | 0.07 | 1.43 | 1.37 |
| far_singles_sideline_R | 0.01 | 0.10 | 0.08 | 1.46 | 1.53 |
| near_centre_service | 0.00 | 0.00 | 0.01 | 0.07 | 0.06 |
| far_centre_service | 0.00 | 0.05 | 0.02 | 0.23 | 0.17 |
| near_baseline | 0.00 | 0.00 | 0.02 | 0.02 | 0.02 |
| far_baseline | 0.12 | 0.57 | 0.46 | 5.39 | 5.88 |
| near_service_line | 0.01 | 0.00 | 0.06 | 0.12 | 0.12 |
| far_service_line | 0.07 | 0.37 | 0.28 | 5.59 | 5.32 |

## Arm P and arm A3 — per line, p90 in cm (400 seeded trials each, seed 0)

P is the primary arm. A3 is P with the codec OFF, and nothing else changed; its trials are paired with
P's (same seeds).

| Line | P: M p90 | P: L p90 | P: L p50 | P net-tape capture | **P verdict** | A3: M p90 | A3: L p90 | A3 verdict |
|---|---|---|---|---|---|---|---|---|
| near_doubles_sideline_L | 0.23 | 0.24 | 0.20 | 0.000 | **PASS** | 0.23 | 0.18 | PASS |
| near_doubles_sideline_R | 0.24 | 0.21 | 0.18 | 0.000 | **PASS** | 0.24 | 0.18 | PASS |
| near_singles_sideline_L | 0.13 | 0.03 | 0.02 | 0.000 | **PASS** | 0.08 | 0.03 | PASS |
| near_singles_sideline_R | 0.08 | 0.04 | 0.03 | 0.000 | **PASS** | 0.07 | 0.03 | PASS |
| far_doubles_sideline_L | 0.25 | 0.67 | 0.23 | 0.000 | **PASS** | 0.11 | 0.14 | PASS |
| far_doubles_sideline_R | 0.14 | 0.62 | 0.22 | 0.000 | **PASS** | 0.08 | 0.13 | PASS |
| far_singles_sideline_L | 0.24 | 0.76 | 0.26 | 0.000 | **PASS** | 0.13 | 0.19 | PASS |
| far_singles_sideline_R | 0.13 | 1.04 | 0.36 | 0.000 | **PASS** | 0.09 | 0.20 | PASS |
| near_centre_service | 0.03 | 0.03 | 0.01 | 0.000 | **PASS** | 0.01 | 0.01 | PASS |
| far_centre_service | 0.05 | 0.28 | 0.19 | 0.000 | **PASS** | 0.01 | 0.20 | PASS |
| near_baseline | 0.16 | 0.16 | 0.15 | 0.000 | **PASS** | 0.14 | 0.14 | PASS |
| **far_baseline** | 0.97 | **3.58** | 1.73 | 0.000 | **PASS** | 0.46 | 0.93 | PASS |
| near_service_line | 0.06 | 0.11 | 0.06 | 0.000 | **PASS** | 0.04 | 0.03 | PASS |
| **far_service_line** | 0.64 | **3.42** | 1.84 | 0.000 | **PASS** | 0.33 | 0.74 | PASS |

**Side metrics**

| | P | A3 |
|---|---|---|
| fit failures | 0 / 400 | 0 / 400 |
| f error, fitted − true (true f = 805.54 px) | −0.26 px median; \|p90\| 0.31 px (0.04%) | −0.26 px; \|p90\| 0.27 px (0.03%) |
| k1 (division λ) error vs λ* = −0.0423 | \|p90\| 0.0088 | \|p90\| 0.0088 |
| fitted camera height (true 3.000 m) | p50 3.0004 m; \|err\| p90 0.5 mm | p50 3.0005 m; \|err\| p90 0.5 mm |
| far-baseline image offset, L (measured paint vs truth) | mean **+0.016 px**; \|p90\| 0.042 px | mean +0.0001 px; \|p90\| 0.005 px |
| far-baseline image offset, M (fitted model vs truth) | mean +0.016 px; \|p90\| 0.024 px | mean +0.008 px; \|p90\| 0.010 px |
| net-tape capture (L image error > 2 px), any line | **0 / 400** | 0 / 400 |
| kappa estimate vs truth (relative) | median **+1.4%**, \|p90\| 1.9% | −0.01%, \|p90\| 0.1% |
| PSF σ estimate vs truth | median 0.00 | median 0.00 |
| achieved bitrate (p50) | 19.9 Mbps | — |
| runtime | **1363 s** (6 workers, 20.6 s/trial) | **676 s** (10 workers, 16.7 s/trial) |

- **The lens mismatch is small but visible.** The Brown render and the division fit leave a
  near-doubles-sideline floor of ~2.3 mm in both arms, and a consistent −0.26 px focal bias.
  λ is not λ*: the fit trades λ against f.
- **Compression is the dominant cost on the far lines.** Paired, P minus A3, it adds a median
  **+1.2 cm** to the far baseline's L error and +1.4 cm to the far service line's. It also biases the
  near-line kappa estimate by +1.4% and the far baseline's measured position by +0.016 px.
- **The route kill did not fire, but the codec is what spends the margin.**
- **Net tape.** At h = 3 m the tape sits ~13 px below the far baseline and only **~3-4 px above the far
  service line** (the lead's addendum listed only the former). The fitter measures the tape first and
  models it as a linear nuisance in nearby profiles. No trial snapped to it.

## Deviations from §7 forced by the build — each found on DEV seeds (≥ 1000) before the freeze

1. **Render order: PSF BEFORE pixel integration, not after.**
   - §7 reads "area-sampled at 16×16, then Gaussian PSF". Done literally (bin to pixels, then blur the
     pixel image), a line narrower than a pixel renders **identically wherever it sits inside its pixel
     row**. The per-column paint centroid spread was exactly 0.0 for the far service line and far
     baseline. So the renderer, not physics, erased the very sub-pixel position CP1 exists to measure.
     With the true camera it measured biases of +0.07 to −0.17 px.
   - Real optics blur before the sensor integrates.
   - The renderer takes 16×16 stratified-jittered samples per pixel, with 2×2 jittered points inside
     each 1/16 cell (32×32 effective). It integrates them against one smooth separable kernel,
     **pixel box ⊗ Gaussian**, evaluated at the fine-cell centres.
   - An intermediate version (box on a 1/4 px grid, then a discrete Gaussian) left a phase-dependent
     bias of 0.007-0.016 px, which the smooth kernel removes.
   - Pinned by `test_blurring_after_pixel_binning_erases_subpixel_position`.
2. **Jittered, not fixed, supersample positions.** A fixed 16×16 grid quantises a horizontal edge to
   1/16 px. It read the 0.14 px far-baseline band as 3/16 of a pixel, and it would have returned the
   0.10 px shift of control 3 as 0.0625.
3. **PSF σ drawn from an 11-point grid** (0.70, 0.75, … 1.20) rather than continuously, so that each
   value's render can be cached.
4. **"Zero noise" includes zero quantisation.** Noise-free frames are left as floats. An undithered
   8-bit round is a ~0.3 DN *structured* error: on a dev run it put the noiseless far baseline at
   1.5 cm. Every noisy arm is quantised to 8 bits.
5. **The encoder carries a VBV cap** (`vbv-maxrate = vbv-bufsize = 16000`) on top of `-b:v 16M`.
   - Plain ABR over 30 frames overshot to 25.9 Mbps.
   - With the cap, P achieved **19.9 Mbps p50**: still above the ~16 Mbps target, because of the
     start-up I-frame of a 0.5 s clip. That errs in R1's favour and is listed below.
   - Other settings: libx265, main profile, preset medium, keyint 60, yuv420p with the Y plane passed
     through (U = V = 128, no range conversion).
6. **Paint surrounds.** Surface 95 DN inside the doubles court, run-off 80 DN outside, paint =
   surface + contrast (60-160 DN). Mesh: 4 mm cords at 4.45 cm, 30 DN. Tape: 220 DN. Back fence at
   6.4 m behind the baseline, with rail and posts. Six roof-truss beams at 6.0-6.3 m. Wall above: 150 DN.
7. **Brown lens values:** k1 = −0.030, k2 = +0.0056 (f-normalised). That gives **30.0 px** at the
   horizontal edge and ~40 px at the corners.

## R1 internals (designed on dev seeds, then frozen)

- **Seed:** closed-form focal length from the corner homography (known centred principal point), then
  a 7-parameter pose + f refinement on the four corners.
- **Passes:** six coarse-to-fine passes.
  - Near lines and near sideline halves, W = 40, then 16 px.
  - Then far sideline halves and the far centre line, W = 10.
  - Then everything, W = 5, 3, 1.5 px.
  - Each pass re-predicts the stations from the current camera and refits
    **pose + f + division λ** (λ held at 0 in the first two passes).
- **Assignment rule:**
  - A station's search window is capped at 0.45 × the predicted distance to any near-parallel feature.
  - A station is dropped if a crossing feature comes within its strip plus 3σ of blur. Centre marks are
    handled by distance, because at 30 m a mark is shorter than a pixel.
- **Profile model:**
  - The exact pixel footprint ⊗ Gaussian applied to the paint band, between its two projected edges.
    Those are intersected with each station's normal, because perspective makes them asymmetric about
    the centreline.
  - Boundary lines (baselines, doubles sidelines) add a surface/run-off step at the outer edge.
  - Paint amplitude is **tied to the step through kappa**; see the finding below.
  - The net tape near a line enters as a measured linear nuisance: a box plus a veil step.
  - Coarse passes use a grid search. Fine passes use a grid search at 0.1 px, then variable-projection
    Gauss-Newton on raw pixels.
- **Camera fit:** robust least squares (Cauchy in coarse passes, Huber in fine) on perpendicular
  distances in the fitted lens's undistorted frame, weighted by each station's own σ (floor 0.01 px).
- **Readouts:**
  - **M:** C1's back-projection through the fitted camera, worst of 11 points.
  - **L:** a robust straight line through the measured paint centres of that half (in the fitted-λ
    undistorted frame), moved to the ITF reference edge by the model's projected half-width. The error
    is the ground distance along the line normal at which a ball crosses it, worst of 11 points.
  - **Visibility is taken from TRUTH, not from the measurement.** A visible half with fewer than 4
    measured stations scores **inf**, so a measurement failure cannot hide as "not visible". None did.

## A finding that shapes R1 on real courts: a sub-pixel line on a colour boundary is degenerate

- The far baseline is 0.14 px tall, and it lies ON the boundary between run-off and court surface.
- To first order, a shift of that boundary and a change in the paint's brightness produce the same
  image. The apparent edge shift is about paint area ÷ step height, which is ~1 px here.
- With paint amplitude free, even a correct-shape model returned the noiseless far baseline
  **−0.20 to −0.25 px** off.
- R1 breaks the degeneracy by measuring **kappa = paint contrast ÷ (surface − run-off)** on the wide
  near baseline, and applying it to every boundary line. The ratio is unchanged by a veil such as the
  net mesh.
- **The cost is a new sensitivity:**
  - **kappa +5% moves the far baseline −0.034 px, ≈ 1.3 cm** (dev measurement, true camera).
  - Under compression, kappa is estimated +1.4% high in P.
- On a real court the far baseline is seen at a grazing angle, and its paint may be dirtier, newer or
  wider (ITF allows baselines up to 10 cm). **Near-to-far paint contrast equality is therefore an
  assumption this pass leans on,** and stage 2 should break it deliberately. A court whose surface and
  run-off are the same colour has no step, and so no degeneracy; the fitter then leaves amplitude free.

## Known ways CP1 flatters R1 (copied from §7, plus what the build added)

From §7:
- the PSF is Gaussian and known in form;
- the court is exactly regulation and, except in A10, flat;
- paint is uniform, not worn;
- no players, no rolling shutter, no OIS, no temporal noise reduction;
- libx265 is not Apple's hardware encoder;
- the distortion is radially symmetric;
- the principal point is centred, except in A9;
- the camera sits on the centreline with roll 0; off-centre mounts are not tested;
- fence and trusses are simple geometric stand-ins.

Added by this build:
- **paint contrast is identical on near and far lines**, and surface/run-off colours are uniform. This
  is exactly the kappa that the far baseline depends on;
- **the PSF σ is the same everywhere in the frame** and is estimated from the near lines;
- the regulation paint width (5 cm) is known to the fitter and true in the render;
- the net is exactly regulation height, and its tape is 5 cm;
- the achieved bitrate is ~20 Mbps, not 16;
- each clip is 0.5 s long: one I-frame plus 29 P-frames of a static scene;
- the renderer's own fixed-pattern Monte Carlo noise is identical in every trial: 0.09 DN rms was
  measured near the far baseline BEFORE the 2×2 sub-jitter, and about half that is expected after it
  (not re-measured).

## What stage 2 should run (unchanged bars; one variable per arm, paired seeds)

1. **A5, 10 cm baseline.** Stage 1's fitter assumes 5 cm paint, so this arm tests both the paint-width
   prior and the kappa coupling. **Highest risk.**
2. **A6, h = 2.5 m**, where the tape is ~4 px from the far baseline. Also A7 (clutter off).
3. **A4, frames 1 / 300** — the averaging curve under the codec.
4. A1 and A2 (lens), A8 (f known), A9 (principal point ±10 px), A10 (non-planar; readout L should be
   immune), A11 (shadow), A12 (first-guess σ 1 / 4 px).
5. **Proposed new arm, to pre-register before running: kappa mismatch.** Render the far lines' paint
   contrast ±10% off the near lines'. The kappa sensitivity above predicts ~2.7 cm of bias per 10% on
   the far baseline, which would spend most of the remaining margin.
6. **Runtime planning:** a codec arm costs ~23 min per 400 trials on this machine (6 workers). A
   non-codec arm costs ~11 min. Each new geometry costs a one-time render of ~2 min (no clutter) to
   several minutes (clutter and distortion).

Outputs (gitignored): `data/output/court_fit_cp1/{ctl1_seed0_n20, ctl3a_seed0_n20, ctl2_seed0_n400,
ctl3b_seed0_n100, ctl2s0_seed0_n100, P_seed0_n400, A3_seed0_n400}.json`, each with the full resolved
configuration, the frozen fitter settings, the commit and the per-trial rows.
