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

### G7 RESULTS — **SEPARATES, and the separator is already shipped; the fit's OWN cost FAILS and is INVERTED**

Run: `tools/court_cost_separation.py --n 400 --seed 0 --workers 10`, 1,059 s,
`data/output/court_cost_separation/G7_seed0_n400.json` (stamp: commit, n, seed, arm, fitter config,
codec, the ridge-residual parameters, the wrong rule). Tests: `backend/tests/test_cost_separation.py`
(8). Instruments and bar pre-registered above and committed at `adafc41` before this ran; the tool
at `026c55b`, also before.

**The population this run produced.** 400 trials, **2 threw** in the paint fit (trial 20
`pass 5: no measurements`, trial 398 `pass 4: no measurements`) and are excluded from the scoring;
**398 scored, of which 33 (8.3%) are WRONG cameras** by the pre-registered rule
(|f_fit − 805.54| / 805.54 > 1%) and 365 right. G1's run of the same arm gave 35/400 (8.75%) and
0 failures — the difference is the non-deterministic codec, as the pre-registration expected, which
is why the label was recomputed here rather than carried over. The wrong cameras' focal error runs
**−34.4% to +132.4%**, with the discrete basins G1 named recurring: −13.6 to −13.7% eight times, +15.3 to
+15.6% four times.

#### The ceiling: the TRUE rendering camera, on these same 398 images

| Quantity | p50 | min | max |
|---|---|---|---|
| `paint_check` support | 0.968 | 0.929 | 0.993 |
| `paint_check` worst-line fraction | 0.943 | 0.895 | 0.981 |
| ridge residual, median (px @720) | 0.054 | 0.032 | 0.109 |
| ridge residual, mean (px @720) | 0.151 | 0.084 | **0.252** |
| ridge residual, fraction of samples with a ridge | **1.000** | **1.000** | 1.000 |

`paint_check.ok` is True on **398 of 398**. `unchecked` is `[far_baseline, far_service]` on every
single trial — the declared blind spot, confirmed, not assumed: **neither instrument ever judged a
camera on a far cross-court line.** So the true camera does not score perfectly (support 0.968, not
1.0), and a right fitted camera is indistinguishable from it: fitted-right support p50 0.964 against
the truth's 0.968, ridge mean 0.150 against 0.151.

#### The two distributions

Fitted cameras, 33 wrong against 365 right:

| Quantity | wrong p10 / p50 / p90 | right p10 / p50 / p90 | right inside the wrong range |
|---|---|---|---|
| support (low = wrong) | 0.330 / 0.498 / 0.719 | 0.947 / 0.964 / 0.993 | 100% |
| worst-line fraction (low = wrong) | 0.000 / 0.000 / 0.000 | 0.925 / 0.943 / 0.981 | 100% |
| ridge median px @720 (high = wrong) | 0.108 / 1.170 / 4.520 | 0.036 / 0.052 / 0.076 | 98.6% |
| ridge mean px @720 (high = wrong) | 2.421 / 4.023 / 5.688 | 0.102 / 0.150 / 0.195 | **1.6%** |
| ridge fraction found (low = wrong) | 0.687 / 0.780 / 0.876 | 1.000 / 1.000 / 1.000 | **0.3%** |
| fit's own cost, px (high = wrong) | 0.0138 / 0.0184 / 0.0853 | 0.0140 / 0.0163 / 0.0197 | 100% |
| fit's own cost, weighted (high = wrong) | 0.437 / 1.219 / 1.716 | 1.304 / 1.500 / 1.710 | 100% |

"Inside the wrong range" is the share of RIGHT cameras whose score falls between the wrong group's
minimum and maximum — a raw overlap, before any threshold. Rank separation (AUC, 33 x 365 pairs):

| Instrument | AUC |
|---|---|
| ridge fraction found | **0.9973** |
| ridge mean | **0.9972** |
| worst-line fraction | 0.9683 |
| support | 0.9679 |
| ridge median | 0.9617 |
| fit's own cost, px | 0.6930 |
| **fit's own cost, weighted** | **0.2157 — inverted** |

#### The pre-registered verdict: threshold set on the train half, applied to the held-out half

17 wrong and 183 right cameras in the held-out half.

| Instrument | held-out catch | false flag | cost of 90% catch in held-out | **verdict** |
|---|---|---|---|---|
| `paint_check` support | **17/17 = 1.000** | 1/183 = 0.55% | 0.55% | **SEPARATES** |
| ridge residual, mean | **17/17 = 1.000** | 1/183 = 0.55% | 0.55% | **SEPARATES** |
| ridge residual, fraction found | **17/17 = 1.000** | 1/183 = 0.55% | 0.55% | **SEPARATES** |
| `paint_check` worst line | 15/17 = 0.882 | 1/183 = 0.55% | 0.55% | PARTIAL |
| ridge residual, median | 15/17 = 0.882 | 1/183 = 0.55% | 3.28% | PARTIAL |
| fit's own cost, px | 14/17 = 0.824 | **170/183 = 92.9%** | 96.7% | **FAILS** |
| fit's own cost, weighted | 16/17 = 0.941 | **183/183 = 100%** | 100% | **FAILS** |

**NULL CONTROL PASSES.** 1,000 seeded label permutations per instrument, the whole split-and-
threshold procedure re-run on each: held-out catch equals held-out false-flag rate to within 0.01 on
every instrument (0.877-1.000 against 0.877-1.000) — chance, exactly as required — and **not one
permutation of any instrument met the bar (`separates_rate` 0.000, 7/7).** The pass above is not
something this procedure hands out for free.

#### The three rules that hold over all 398, not just the held-out half

| Rule | catches | false-flags |
|---|---|---|
| **`camera3d.paint_check(...).ok` — the SHIPPED flag, no new threshold** | **33 of 33** | **1 of 365 (0.27%)** |
| ridge fraction found < 1.000 | **33 of 33** | 1 of 365 (0.27%) |
| ridge mean >= 0.235 px @720 | **33 of 33** | 6 of 365 (1.64%) |
| support < 0.90 | 32 of 33 (97.0%) | 1 of 365 (0.27%) |

Every one of those meets the pre-registered bar. **The strongest result is that nothing new is
needed:** the flag that `fit_camera_checked` already computes catches every wrong camera here.

**The single "false flag" is a MISLABEL, recorded and NOT fixed (hard rule 8).** All four rules
false-flag the same trial, **trial 32**, and its focal length is right to 0.01% — so the
pre-registered label calls it a right camera. But its worst line is **infinite metres out**, its
`centre_service` line has **0.0** of its samples on paint, and 36% of its samples have no ridge
within 12 px @720. The instruments are right about trial 32 and the focal-length label is wrong
about it. **The label is left alone**, so every false-flag rate above is if anything overstated;
excluding trial 32 the three top rules cost **0 of 364**.

**The one wrong camera that support cannot see, and why the structure rule matters.** Trial 69 is
**+132.4% in focal** and scores **support 1.000** and ridge mean 0.235 — inside the right cameras'
range. It is invisible to a court-wide average because it puts almost the whole court out of frame:
only **5 lines** remain checkable and **all four cross-court lines** (`near_baseline`,
`far_baseline`, `near_service`, `far_service`) are unchecked. `paint_check` catches it on
`too_few_lines`, its `min_across`/`min_along` guard, not on any fraction. **So a bare threshold on a
photometric average is not enough; the acceptance rule must also require that enough of the court
was checkable.** That is a design requirement this run produced, not a tuning detail.

#### The fit's own cost is worse than useless — it is INVERTED

The optimiser's own weighted residual has **AUC 0.216**: in a head-to-head between a wrong camera
and a right one, **the WRONG camera has the lower weighted cost 78.4% of the time**. Unweighted, in
undistorted pixels, it is weakly informative (AUC 0.693) but still loses **30.7%** of head-to-heads,
and catching 90% of wrong cameras costs 93-100% false rejection. A wrong camera measures its own
paint points on whatever lines it landed near and then fits them beautifully: median 0.018 px on
about 950 points, against 0.016 px for a right camera. This is G3's "self-consistent on the wrong
paint" finding again, now measured on the fit rather than the tracker.

#### Predictions, scored

- **Prediction 1 WRONG.** The worst-line fraction did NOT beat the court-wide support: support
  SEPARATES (17/17) and the worst line is PARTIAL (15/17). The cause is threshold selection, not
  signal — the wrong group's worst-line fraction is **exactly 0.000 at every percentile up to p90**,
  so the "tightest threshold catching 90% of the train half" lands on the degenerate value 0.0. Its
  AUC (0.9683) is a hair above support's (0.9679). **The bar was pre-registered and it stays where
  it fell: PARTIAL.**
- **Prediction 2 WRONG in a useful direction.** The ridge mean did not land between them, it beat
  both (AUC 0.9972 against 0.968), because it is an average over samples rather than over lines and
  a wrong camera is far off nearly everywhere. The ridge MEDIAN, which discards exactly that, is the
  weakest of the three (0.9617).
- **Prediction 3 RIGHT, and stronger than predicted.** The fit's own cost does not separate; it is
  inverted.
- **Prediction 4 PARTLY RIGHT.** The surviving hard case is a zoom basin (trial 69, +132%), as
  predicted, but it survives by pushing the court out of frame rather than by sitting on real paint
  one alley over.

#### What this means for the three roadmap items

- **Item 3, the multi-anchor selector that picks "the lowest photometric residual": VIABLE, but only
  if the residual is an INDEPENDENT one.** Read as the fit's own cost it picks the wrong camera 78%
  of the time in a head-to-head. Read as `paint_check` support or the ridge mean it ranks right
  above wrong on 96.8-99.7% of pairs. **Specify which residual; the two answers are opposite.**
- **Item 1 Tier 2's acceptance rule: EXISTS ALREADY.** `camera3d.paint_check(...).ok` at its shipped
  defaults caught 33 of 33 wrong cameras at 1 flag in 365 right ones, and that one flag is a
  mislabel. No new threshold is needed on this scene.
- **Item 4's "not locked" trigger: SUPPORTED on this evidence, with the structure guard kept.** A
  trigger on `paint_check` failing would have fired on every wrong camera here and idled on
  365 of 365 right ones. It must keep the `min_across`/`min_along` requirement: trial 69 passes every
  fraction and fails only that.

#### Caveats, stated rather than buried

- **Synthetic, one camera pose, one scene.** CP1 arm P: rendered paint, uniform surface, a Gaussian
  PSF, libx265, no players, no shadows, no worn paint, no occlusion. `ridge fraction found = 1.000`
  on 364 of 365 right cameras is a property of a clean synthetic court; on real footage some samples
  will miss for reasons that have nothing to do with the camera, and that rule is the one most likely
  to fall apart first. Support and the ridge mean degrade more gracefully.
- **Neither instrument can see the far baseline or the far service line** (too thin for the ridge
  finder at this mount and resolution), on every one of the 398 trials. A camera that is right on
  the near half and wrong on the far half is exactly what C1 says to fear, and **this experiment
  cannot detect it.** Everything above separates GROSSLY wrong cameras from right ones; it says
  nothing about the 5 cm question.
- **`paint_check`'s thresholds were set on development seeds of this same scene** (G4/G5), so its
  33/33 is not a fully independent number in the way the ridge residual's is — the ridge residual was
  defined in the pre-registration above, before this run, and never tuned.
- **The wrong/right label is the focal length alone.** Trial 32 shows it is not a perfect label. The
  right way to read this section is as separating *cameras that are grossly wrong somewhere* from
  *cameras that are right*, with focal error as a proxy that misses at least one case.
- **2 of 400 trials threw** in the paint fit and are outside every number here. In a product they are
  trivially "not locked".
