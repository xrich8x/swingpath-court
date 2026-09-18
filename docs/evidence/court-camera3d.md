# The 3D court camera: keypoint PnP seed → paint fit → tracked pose

**2026-09-17, one session (task brief: "upgrade court spatial modeling from 2D homography to an
adaptive 3D PnP & keypoint calibration").** Branch `camera3d-pnp-paintfit`.

Code:
- `backend/swingvision/camera3d.py`: `CourtCamera`, `solve_pnp_seed`, `fit_camera_on_paint`;
- `backend/swingvision/paintfit.py`: the R1 fit, lifted from CP1;
- `backend/swingvision/camtrack.py`: `CameraTracker`;
- `courtfit.KeypointSet` / `KeypointDetector` / `CourtNetKeypoints` / `ClassicalKeypoints` /
  `cross_ratio_check`;
- `court.LANDMARKS_3D` / `KEYPOINTS_3D` / `COLLINEAR_SETS`;
- `setup_state` `camera` block.

Tools: `tools/court_camera3d_seed.py` (arms K, K0) and `tools/court_track_sim.py` (tracking).

**WHAT EVERY SCORED NUMBER HERE IS MEASURED AGAINST:** the exact synthetic camera that rendered the
image. That means true ground coordinates of 11 points on each of C1's 14 line halves, projected
through that camera, with the error taken perpendicular to each line (as in C1 and CP1). No labels,
no model output, no footage.

**Rule 5.** Every camera states what pinned it (`CourtCamera.pinned_by`). The keypoint PnP camera is
pinned by detected points, the regulation court and a centred principal point. The paint-fit camera
is pinned by what CP1 lists. A reprojection residual is reported as a diagnostic and never used as
evidence.

**Scope decisions (user, this session):**
- **court only**: the brief's ball-trajectory solver was dropped, since ball work is archived;
- **keypoints only seed**: C1 measured that point-pinned cameras misplace far lines by metres; the
  paint fit decides the camera;
- **detector = interface + adapters**: no model trained here.

---

## PRE-REGISTRATION — written and committed before any scored run

### G1. Arm K — the paint fit seeded by keypoints through PnP

**Scene:** CP1 arm P, unchanged:
- Brown lens, fence and truss clutter, sensor noise;
- 30-frame mean through real libx265;
- 1920×1080, 3 m mount, 100° horizontal FOV.

**Seed:**
- every `court.LANDMARKS_3D` keypoint that projects into the frame;
- per-axis Gaussian noise σ = 14.78 px (CP1's seed noise);
- TWO gross outliers per trial, 100–300 px in a random direction;
- through `camera3d.solve_pnp_seed`, with no focal length given. The cross-ratio gate is on.

**Fit:** `paintfit.r1_fit` from that seed.
- The principal point is the image centre. This fixes the latent leak qa found in CP1, which passed
  the true `cx`.
- n = 400, `--seed 0`, CP1's readouts M and L.
- A trial that throws (PnP refused, fit failed) is a failure scored as infinite error.

**BAR (the SPEC §3 working target, not a founder bar):**
- **PASS** if every line's p90 of max(M, L) ≤ **5 cm**;
- **KILL** if any line > **10 cm**;
- otherwise INDETERMINATE.

**Prediction:** PASS, with the far baseline near CP1 arm P's 3.58 cm (L), because the seed is no
worse than CP1's. Risks:
- the PnP focal error (a smoke run on another seed showed 7% p90) is larger than CP1's
  four-corner seed;
- outliers that RANSAC keeps.

### G2. Arm K0 — the keypoint camera alone (no paint fit)

The same seeds, scored with readout M only. **Reported, no gate.**

**Prediction, from C1:** KILL on the far lines, by tens of centimetres to metres. This arm exists to
show why the paint fit decides.

### G3. Tracking — `camtrack.CameraTracker` under fence sway and a knock

**Setup, `tools/court_track_sim.py`:**
- **Render:** 1920×1080, 30 fps, 120 frames per seed, **seeds 0, 1, 2 pooled** (360 frames).
- **Sway:** fence sway of ~0.3° (yaw, pitch) and 0.15° roll, as sinusoids plus a random walk, with
  ~1 cm translation.
- **Knock:** at 2.0 s, +1.5° pitch and +1° yaw, held.
- **Setup on frame 0 as the product would do it:** noisy keypoints (σ 14.78 px) → PnP seed → paint
  fit.
- **Renderer:** simpler than CP1's. Flat court, 5 cm paint, 2×2 supersampling, 0.9 px blur, sensor
  noise, and a far fence with posts. No lens and no codec.
- **Tracker settings:** `TrackConfig()` defaults, all unmeasured, as SPEC §1 says.

**BAR, camtrack:**
- **PASS** if every line's p90 over all 360 frames ≤ **5 cm**, AND
  - the largest frame-to-frame far-baseline jump beyond the true motion is ≤ **2 px**, outside the
    6 frames starting at each knock, AND
  - after each knock every line is back within 5 cm within **15 frames** (0.5 s).
- **KILL** if any line's p90 > **10 cm**, or any knock never recovers.
- Otherwise INDETERMINATE.

**Baseline, `calibration.court_lock_step`** (the shipped per-frame snap, same frames and the same
starting court): **reported, no gate.**

**Prediction:** its own docstring says it "does NOT track a sustained pan", and its bounds are 14 px
and 1.2°. It should hold during sway, lose the court at the knock, and never come back, so KILL.

### G4. Already fixed BEFORE this pre-registration (development numbers, not scored results)

- **The cross-ratio gate tolerance** was set on a NOISE-ONLY simulation: CP1's σ 14.78 px on
  exact keypoints, three camera poses, 300 draws each. The results, as the rate of any false flag,
  then the rate of catching a near point moved 1.5 m:

  | Tolerance (px @720) | False flags | Moved point caught |
  |---|---|---|
  | 20 | 18–38% | — |
  | 40 | 6–12% | — |
  | 60 | 0.3% | 87–90% |

  **Chosen: 60 px @720**, scaled by frame height. Predicting a point from other noisy points
  amplifies their noise, so this gate only ever catches gross errors, and RANSAC does the real
  outlier work. With the 10% relative cross-ratio tolerance first written, a 1 m move changed the
  ratio by only 5–8% and passed; that version was discarded.
- **Two tracker faults found on the unit tests (`test_camtrack.py`), not on the scored sim:**
  - LK flow from frame to frame DRIFTED, about 0.7 px per frame on a slow pan. The optimiser
    converged below the true pose's cost, so the drift was the measurement having no anchor. Flow now
    only predicts, and each point is snapped onto the paint ridge along its line's normal.
  - Samples placed on ITF line EDGES instead of paint centres, and samples at line crossings, biased
    the snap by about 4 px. They now sample paint centrelines, at least 0.3 m from any other line.

  After both fixes a 30-frame pan tracks to within 0.1–0.2 px after a 5-frame filter catch-up.

---

## Rule 7 — lifting the R1 fit into `swingvision.paintfit` changed nothing

- **Method:** a pristine checkout of `b3af0ca` (a git worktree) against the lifted code. Same arms,
  same seeds, rows compared value by value with timings excluded (`cp1_repro.py`, session
  scratchpad).
- **ctl1** (n = 3, seed 7), **A3** (n = 4, seed 1; lens + clutter + noise, the whole fitter),
  **ctl2** (n = 4) and **ctl3a** (n = 1): **0 differing values.**
- **Fresh renders with the cache OFF** (no-lens/no-clutter and lens+clutter) are **bit-identical**
  to the cached ones.
  - This check matters because the render cache is keyed on scene settings, not code. The lifted
    `PHI` helper, used only by the renderer, was missing after the first rewire, and a cached run
    would not have noticed.
- **Arm P differs (445 values), and so does the PRISTINE code against itself.** Two pristine runs of
  the same P trials gave:
  - bitrates 18935.8 / 20483.3 kbps and then 18916.5 / 20145.2 kbps;
  - far-baseline L of 1.32 / 2.42 cm and then 0.58 / 2.97 cm.
- **FINDING: libx265 as CP1 drives it is not deterministic run to run on this machine**, most likely
  from encoder threading.
  - qa's "bit-identical reproduction" covered the codec-free controls only.
  - A single trial's far-baseline number carries up to ~0.7 cm of encoder noise.
  - CP1's p90 over 400 trials is a population figure and is not overturned by this, but stage 2
    should pin encoder threads (e.g. `pools=1:frame-threads=1`) before any arm-vs-arm comparison of
    codec arms.
- **Pinned by `tests/test_paintfit_lift.py`:** A3 trial 0 reproduces the pre-lift f, λ, height,
  κ, σ, per-line point counts and three line errors.
- **The CourtNet decode moved into `calibration.courtnet_decode`:** `detect_court_learned` returned
  identical keypoints, homography and confidence to the pristine code on two rendered courts, with
  `courtnet_split.pt`.

---

## Results (scored after `617cd96`; bars above not moved)

Raw output:
- `data/output/court_camera3d_seed/K_seed0_n400.json`;
- `data/output/court_track_sim/seeds0-1-2_n120.json`.

### G1 Arm K — **PASS by the letter, with a wrong-camera tail about 9× CP1's**

400 trials, 0 failures to run.

Every line's p90 is ≤ 5 cm. The four far lines:

| Line | M p90 | L p90 |
|---|---|---|
| far baseline | 1.18 cm | **4.43 cm** |
| far service line | 0.74 cm | **4.57 cm** |
| far singles sideline R | — | 1.61 cm |
| far singles sideline L | — | 1.20 cm |

Every other line is ≤ 1 cm. CP1 arm P, from a four-corner seed, was 3.58 cm on the far baseline and
3.42 cm on the far service line. The margin to the bar is now 0.4–0.6 cm.

**THE TAIL, which the p90 bar cannot see:**
- **35 of 400 trials (8.75%) converged to a WRONG camera.** Fitted focal length is 13–130% off, and
  36 trials put some line more than 5 cm out on the model readout.
- CP1 arm P had 4 of 400 trials past 5 cm, all on the far lines.
- **The false solutions are discrete, not noise.** f −13.7% with height 3.39 m recurs 5 times,
  and ±15.4% recurs 4 times. These are neighbouring basins, most likely a paint line assigned to its
  neighbour.
- **The seed predicts the failure.** The PnP seed's median height error is **0.69 m** on
  wrong-camera trials against **0.13 m** on the rest; its focal error is 10.5% against 4.6%.
  RANSAC kept one of the injected outliers on 4 of the 35 wrong-camera trials and on 1 of the 365
  others.
- **So the keypoint seed's tail is worse than CP1's four-corner seed.** The keypoint noise is the
  same, but the seed solves focal length and pose from it jointly.
- A further 11 trials have the right camera but one measured-line (L) readout past 5 cm, mostly on
  the far baseline.
- The cross-ratio gate dropped a point in 94 of 400 trials, nearly all of them points that were only
  noisy, not outliers.

On the correct-camera trials:
- fitted focal error p90 **0.043%**;
- camera height error p90 **0.6 mm**.

**Measured against** exact projected court geometry from CP1's synthetic camera.

### G2 Arm K0 — **KILL, as predicted**

The keypoint PnP camera alone, with no paint fit. Worst-of-11-points p90:

| Line | p90 |
|---|---|
| far baseline | **6.65 m** |
| far service line | **3.86 m** |
| near sidelines | 0.63–0.95 m |

Every line fails the bar. With the same seeds, the paint fit takes the far baseline to 1.2 cm (M).
C1's conclusion holds for 21 keypoints as well as for 4.

### G3 Tracking — **KILL, and it is the more important result**

Pooled over 360 frames:

| Measure | camtrack | court_lock_step (baseline) |
|---|---|---|
| Worst line p90 | **11.0 m** (far baseline) | 13.4 m |
| Largest steady-state jump (bar ≤ 2 px) | **10.1 px** | 5.3 px |
| Knock recovery (frames, per seed) | **32 / never / never** | never on all three |

Three separate failures, each named:

1. **Setup failed on seed 2.** The paint fit on frame 0 converged to f = 694 px against a true
   806 px, with the worst line 1.64 m out. This is G1's wrong-camera tail again (1 of 3), and
   everything after it inherits the error.
2. **Steady sway, on seeds 0 and 1 (good setup, first 60 frames):**
   - camtrack's worst line has a median of **5.0–5.2 cm**, a p90 of **9.2–10.9 cm** and a max of
     15 cm;
   - court_lock_step's worst line has a median of **61–154 cm**, a p90 of 133–273 cm and a max of
     338 cm.

   camtrack is 10–30× better than the shipped snap, but not inside 5 cm. The shipped snap does not
   follow sway at all, as its docstring says.
3. **The knock (1.5° pitch + 1° yaw in one frame, about 14 px):**
   - Flow and the ±9 px paint snap lose the court. The simulation passes **no detector**, so the
     tracker HOLDS (6–11 frames on seeds 0–1).
   - When holding ended it resumed "tracking" from the stale pose. Seed 0 found its way back after
     32 frames. **Seed 1 LOCKED ONTO THE WRONG PAINT and tracked 7–10 m out for the remaining
     50 frames, with status `tracking`.**
   - **No paint re-fit ever fired**, for two reasons:
     - the drift test compares the pose with its own flowed-and-snapped points, which agree with
       each other even when they are all on the wrong line;
     - the 10 s backstop is longer than the 4 s clip.

**What this means for the design, recorded as observations, not fixed here (a fix needs its own
pre-registered run):**
- **A confident wrong lock is the worst outcome.** The tracker needs an INDEPENDENT check that the
  court is on the paint. Self-consistency of its own points is not one.
- **Recovery must not depend on a detector existing.** A pose-only paint re-fit from the last good
  pose, whose first pass searches 40 px, is a recovery path that is not the closed search.
- **Steady precision:** single-frame snaps give about 5 cm median. Getting under 5 cm at p90 likely
  needs temporal averaging of the paint measurements, or scheduled paint re-fits.
- **The setup tail (G1 and G3 seed 2)** needs multi-start or seed-quality screening before the paint
  fit is trusted.

---

## What was NOT done, and why

- **No real footage was run.** This repository holds no video; the footage lives in the main
  repository's `data/incoming`, which this project's settings forbid reading (`Read(../**)`).
  `run.py`, `pipeline.py` and `schema.py` are not in the court-only repository, so there is no
  `analyze` to integrate the tracker into. The tracker is standalone.
- **`live.py` is not in this repository**, and the plan left it out anyway (queue item 4).
- **No detector was trained.** `CourtNetKeypoints` wraps the existing CourtNet, which on amateur
  footage fires on 2–3 of 14 keypoints (cnn-global-classical-local). A model trained on amateur or
  synthetic courts plugs in behind `KeypointDetector`; that is a separate, pre-registered ML task.
- **No ball code.** `CourtCamera.ray()` is the single-camera inverse projection a future solver
  would use; a ray pins nothing until something else does (rule 5).
- **Cost:** one paint fit is ~11 s on this CPU at 1080p, and the tracker re-fits at most every 10 s
  or on drift. Nothing here is measured on a phone.

---

## G7: does a photometric cost separate right from wrong cameras?

**PRE-REGISTRATION — written and committed BEFORE any scored run (hard rule 2).**
backend-dev, 2026-09-18, branch `camera3d-pnp-paintfit`. Chosen by pm as the first build off the
founder's per-frame roadmap (`docs/DECISIONS_PENDING.md`, "PM feasibility check: the founder's
per-frame roadmap (2026-09-18)").

### Why this is the first thing to measure

Three roadmap items are written as if a photometric cost already told a right camera from a wrong
one, and nobody has checked:

- **item 3**, the multi-anchor selector, picks the fit with "the lowest photometric residual";
- **item 1 Tier 2**, the fast paint fit, needs an acceptance rule;
- **item 4**, global re-localisation, triggers on "not locked".

G1 supplies the population: arm K converged to a WRONG camera on **35 of 400** trials (8.75%), in
discrete false basins, while the other 365 were right. If no photometric quantity separates those
two groups, all three items are unimplementable as written.

### Population, and how it is produced

**Arm K re-run at `--seed 0`, n = 400** — the same scene, the same seeded keypoint noise and the
same fitter as G1: CP1 arm P (Brown lens, fence and truss clutter, sensor noise, 30-frame mean,
real libx265, 1920x1080, 3 m mount, 100 deg HFOV), 21 in-frame `court.LANDMARKS_3D` keypoints with
sigma 14.78 px per axis plus two 100-300 px outliers, `camera3d.solve_pnp_seed` with no focal
given, then `paintfit.r1_fit` from that seed with the principal point at the image centre.

`paintfit.r1_fit`, **not** `camera3d.fit_camera_checked`: arm K used the plain fit (its rows carry
no `check`/`starts`), and `fit_camera_checked` already uses `paint_check` as its acceptance rule,
so scoring it here would beg the question this section asks.

**Why a re-run and not the recorded rows:** `K_seed0_n400.json` predates the `params` field, so the
fitted camera is not in the file and cannot be re-projected. **And the codec is not deterministic
run to run** (Rule 7 section above), so a re-run gives different images and can land in different
basins. **Therefore the wrong/right label is RECOMPUTED from the fit actually scored, in the run
actually done:** a trial is WRONG if `|f_fit - 805.35| / 805.35 > 0.01`, the same rule G1 used.
The 35/400 count is not assumed; whatever this run produces is the population, and its size is
reported.

### The three instruments, stated exactly

All three read **one image**: the same 30-frame-mean, codec'd, 8-bit grey image the fit saw.

**(1) `camera3d.paint_check(grey, cam)` at its shipped defaults** (`tol_px_720 = 1.5`,
`min_dn = 6.0`, `min_line_frac = 0.5`, `min_width_px_720 = 0.67`, `min_samples = 6`,
`step_m = 0.4`). Recorded per trial: the court-wide `support`, the per-line fractions, the
`worst` line and its fraction, the `ok` flag, and the list of `unchecked` lines. What `support`
reads: of every sample on a painted-line centreline that this camera projects into the frame and
whose projected paint is at least 0.67 px @720 wide, the fraction that has a bright ridge within
1.5 px @720 of where this camera puts it.

**(2) The RIDGE RESIDUAL — this section's own photometric residual, defined here.** Same sample
set and same ridge finder as (1) (`camera3d._samples(0.4)`, `camera3d.ridge_offsets`), but
**censored at a wider reach instead of thresholded**: for each usable sample, search along the
line's image normal within +-12 px @720 for the nearest local grey maximum standing >= 6 DN above
that profile's median; the sample's residual is `|offset|` in px @720 if one is found and the full
12 px @720 if none is. Reported per trial: the **median** and the **mean** of that censored
residual over all usable samples, the fraction of samples with any ridge found, and the sample
count. It is a distance-to-nearest-ridge along the projected lines, in pixels, and nothing else.

Why a wider reach than `paint_check`: at 4.5 px @720 a grossly wrong camera saturates and the
instrument degenerates into `support`. At 12 px @720 it grades. The cost of the wider reach is
that a wrong camera may capture a NEIGHBOURING line's ridge and score well — which is exactly the
failure mode G1 named (dolly-zoom basins), so the instrument is honest about it rather than blind
to it.

**BLIND SPOT, declared in advance:** instrument (2) inherits `paint_check`'s
`min_width_px_720 = 0.67` filter, so **it cannot see the far lines either** — they project too thin
for the ridge finder. Both instruments therefore judge a camera mostly on the near half of the
court. The `unchecked` list is recorded per trial so the blind spot is measurable, not assumed.

**(3) The fit's OWN final robust cost** — the median `|perpendicular residual|`, in undistorted
pixels, of every paint point the fit measured (`meas`) against the line the fitted camera puts
there, plus the point count. **This is a self-consistency number, not independent evidence**
(rule 1): the fit chose both the points and the camera. It is measured precisely because G3 found
a tracker that was self-consistent on the WRONG paint, and the prediction below says it fails.

### The ceiling: the same quantities for the TRUE camera on the same image

Instruments (1) and (2) are also computed for `tools/court_fit_cp1.py::truth_camera` — the exact
camera that rendered the image, independent of the fit (rule 1) — on that same image. Without it,
"support 0.9" is a number with no scale. (3) has no ceiling: it is a property of a fit, and the
true camera did not do one.

**Rule 5 — what pins each camera reported here:** the true camera is pinned by the renderer (it IS
the rendering camera); the fitted camera is pinned by measured paint + regulation dimensions + flat
court + a centred principal point (`camera3d.PINNED_PAINT`); the wrong/right LABEL is pinned by the
true camera's focal length alone.

### THE BAR

A threshold is chosen on a **seeded 50/50 split** of the 400 trials (`--split-seed 0`, stratified
so both halves hold about the same share of wrong cameras). On the TRAIN half the threshold is set
at the tightest value that catches >= 90% of that half's wrong cameras; it is then applied unchanged
to the HELD-OUT half, and the held-out numbers are the verdict.

For **each** of the three instruments, and for the best single threshold on any of them:

- **SEPARATES** if, on the held-out half, one threshold catches **>= 90%** of the wrong cameras
  while falsely rejecting **<= 2%** of the right ones.
- **FAILS** if catching 90% of the wrong cameras costs **> 10%** false rejection of right ones.
- **PARTIAL** in between (2-10% false rejection at 90% catch): usable as a trigger for a re-fit,
  which costs only compute, but not as a silent accept/reject.

Reported either way, since the pm's question is a separation, not a claim: both distributions as
percentiles, their overlap, the full catch-vs-false-flag trade-off curve, and the ceiling.

**NULL CONTROL, mandatory.** The wrong/right labels are permuted 1,000 times under a fixed seed and
the whole split-and-threshold procedure re-run on each permutation. The permuted held-out catch rate
must sit at chance (i.e. at the false-flag rate the threshold costs). If a permuted null also
"separates", the instrument or the split is broken and no verdict is reported.

### Predictions, recorded before the run

- **(1) `paint_check`'s WORST-LINE fraction separates better than its court-wide `support`** — its
  own docstring argues a court slid in depth keeps its long sidelines and loses one baseline, which
  an average hides. Expect PARTIAL to SEPARATES on the worst line.
- **(2) The ridge residual lands between them** — better than `support` because it is graded, worse
  than the worst-line rule because it is also an average.
- **(3) The fit's own cost DOES NOT separate.** G3 already found a pose that was self-consistent on
  the wrong paint. If this prediction is wrong, item 3's selector is cheap; if it is right, item 3's
  "lowest photometric residual" must mean an independent residual, not the optimiser's own.
- **The residual failure mode is the one-alley shift and the dolly-zoom**, not gross nonsense: a
  camera one alley over still sits on real paint. Expect the surviving false negatives to be those.

**A failed bar stays failed.** Nothing below this line is edited after the run except by adding
results.
