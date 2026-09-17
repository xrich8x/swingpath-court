# CP1 stage 1 — independent QA of the "PASS on all 14 lines" claim

**qa, 2026-09-17.** Audits `docs/evidence/court-fit-cp1.md` (backend-dev), code frozen at `4ac52fc`, results
`99e1812`. QA did not touch the tool, the tests or the bars. Reruns wrote only to a scratch directory.

**OVERALL VERDICT: PASS QUALIFIED.** The numbers are real, they reproduce bit-for-bit, and no truth
quantity reaches the fitter in any stage-1 arm. But the pass rests on one camera pose (the same one the
fitter was developed on) and on several renderer/fitter assumptions the evidence file does not declare.
Measured on the far baseline, one of those assumptions — sigma on the grid — is mild. The codec margin is
the one that decides the result: the pass holds only if a phone's encoder costs no more than ~1.5x what
libx265 at ~20 Mbps costs on this static scene with flat chroma.

**What every number here was measured against:** the same exact projected court geometry (C1's camera)
the tool scores against. Tables were recomputed from the per-trial rows in
`data/output/court_fit_cp1/*.json`, not taken from the stored summaries.

---

## 1. Freeze integrity — CONFIRMED (with two metadata defects)

- `git diff 4ac52fc HEAD -- tools/court_fit_cp1.py` is empty, and the working tree is clean. The tool has
  exactly one commit, `4ac52fc`.
- All 7 scored JSONs stamp `commit 4ac52fc8`, `tool_dirty_at_run: false` and render
  `cp1-render-5-smooth-kernel-sub2`.
- Each run's start time (file mtime − `wall_s`) is **after** the freeze commit: ctl1 +20 s, ctl3a +55 s,
  ctl2 +91 s, ctl3b +757 s, ctl2s0 +933 s, P +1135 s, A3 +2499 s. So no scored run started on pre-freeze
  code.
- **Defect A: the stamp is taken at the END of a run.** `git_sha()` and `git_dirty()` are called inside
  `stamp()`, after all trials finish. The recorded commit is HEAD at write time, not the code the process
  loaded. Timing rules out a problem here, but the stamp alone could not prove it.
- **Defect B: duplicate `"seed"` key in `stamp()`.** The dict literal sets `"seed": seed` and then
  `"seed": "a rough first guess…"`. The later key wins, so **no JSON records its numeric seed.**
  - The seed was recovered independently. Every P row's `contrast` and `seed_err_px` regenerate exactly
    from `SeedSequence([0, trial])`, so seed 0 is confirmed.
  - Also stale: `scene.render_order` still says "1/4 px grid", which is not the frozen renderer.
- **The coverage-render cache predates the freeze.** The cache is keyed on `RENDER_VERSION` plus
  geometry, **not on the code**:

  | Cache key | Used by | Built |
  |---|---|---|
  | `86a05df4` | ctl1, ctl2, ctl2s0 | ~4 h before the freeze |
  | `efa87348` | P, A3 | ~4 min before the freeze |
  | `ff11a531` | ctl3a | ~10 min before the freeze |

  QA re-rendered the ctl1 geometry and the P geometry fresh from the frozen code (`cache=False`, nothing
  written). Both are **bit-identical to the cached renders** (max |Δ| = 0.0 in both the base and paint
  arrays; renders took 122 s and 429 s). The scored runs therefore used frozen-code renders.

## 2. Truth leakage — CONFIRMED CLEAN for stage 1, one latent leak

The fitter is called exactly once:

```python
r1_fit(img, seed_corners, FitConfig, rcam.cx, H / 2.0)
```

Its inputs are:
- the rendered image, or the decoded codec mean;
- the four corners (true distorted corners + Gaussian error of σ 14.78 px);
- `cx`;
- `cy`, fixed at the constant `H/2`.

Inside `r1_fit`, the following are all estimated from the image or fitted:
- the seed camera: closed-form f, clipped to a 30–65° half-FOV window;
- pose, **f**, the division λ, the PSF σ, kappa and the tape position.

Truth objects appear only in trial setup, in `readouts()` (scoring), `summarise()` and `stamp()`:
`truth_camera`, `ref_cam`, `lam_star`, `HFOV_DEG`, `BROWN`, `contrast`, `psf`, the noise RNG and
`true_corners` beyond the perturbed seed.

- **`lam_star` (the docstring at line 274, "f and the principal point held at truth")** is called only in
  `summarise()`. It is the reference the reported k1 error is measured against. Nothing it computes
  reaches the fitter.
- **f is free in arm P.** `fit_camera` includes f (bounds 200–4000 px) in every pass. λ is held at 0 only
  in the first two coarse passes, as documented.
- **Latent leak:** `cx` is passed from the TRUTH camera object (`rcam.cx`), while `cy` is a constant.
  In every stage-1 arm `rcam.cx == W/2`, so this is exactly the declared centred-principal-point
  assumption and leaks nothing today. **In arm A9 (principal point shifted ±10 px) it would hand the
  fitter the true shifted cx.** It must be fixed before A9 is run.
- The visibility of a line half is taken from truth, but only to decide what is scored. A missing
  measurement scores inf, which is conservative. None occurred.

## 3. Shared assumptions — the lens models genuinely differ; several shared assumptions are undeclared

**The lens models differ.** The renderer distorts with Brown (k1 −0.030, k2 +0.0056, f-normalised),
giving 43.2 px at the frame corner. The fitter's `Camera.from_params` always sets `brown=None` and uses
the division model. The best single λ* (with f fixed at truth) leaves up to **5.46 px** of radial mismatch
at the corner. The fitter absorbs part of that by trading λ against f, which gives the −0.26 px f bias and
the ~2.3 mm near-doubles-sideline floor.

| Shared assumption (renderer = fitter) | Declared in the evidence's flattering list? |
|---|---|
| Regulation dimensions (the same `CT` constants) | yes |
| Paint 5 cm everywhere, baseline included (the same `paint_lines()` object) | yes |
| Flat court | yes |
| Centred principal point | yes (but see the `rcam.cx` leak in §2) |
| Gaussian PSF, uniform across the frame | yes |
| Kappa equal on near and far lines; uniform surface and run-off | yes |
| Net at regulation height, 5 cm tape | yes |
| Radially symmetric lens | yes |
| **PSF σ on-grid.** The render draws σ from {0.70…1.20 step 0.05}; the fitter's grid {0.5…2.5 step 0.05} contains those values exactly. **`sig_est == psf` in 100% of trials in every arm, P included** | **no** — reported only as "median 0.00" |
| **Profile form = the render kernel.** Pixel box (100% fill factor) ⊗ Gaussian, with the same separable footprint | partly ("Gaussian, known in form") |
| **Linear sensor.** No gamma, tone mapping or sharpening; the fitter's photometric model is linear in DN | **no** |
| **Flat chroma** (U = V = 128), so the encoder spends every bit on luma | **no** (listed as a build detail, not as flattering) |
| **The surface/run-off step sits exactly on the outer paint edge** of the baselines and doubles sidelines, and is an ideal step | **no** |
| **Shared net-sag function** `tape_top()`, plus the post positions and 10 cm post width | tape height yes; the sag shape and posts no |
| Centre marks 10 cm × 5 cm, from the same `centre_marks()` (used only for exclusion) | no (minor) |
| **Square pixels, zero skew** | no (minor) |
| **One camera pose.** Every dev seed and every scored trial render the SAME geometry; seeds vary only contrast, PSF, noise and corner error. The six renderer changes and all R1 tuning (windows, assignment fractions, tape handling) were done on the pose that is scored | **no** — only "centreline, roll 0" is declared |
| All 4 corners and all 14 halves in view (no inferred out-of-view end points) | no |

**QA probe (pre-registered in the journal before running; descriptive only, cannot change the verdict).**
The fitter's σ grid was shifted by +0.025 px, so the truth always falls midway between grid values;
everything else was held equal. Arm P, n = 50, seed 1, paired with the §5 run.

| | σ on-grid | σ off-grid |
|---|---|---|
| failures | 0 | 0 |
| every line p90 ≤ 5 cm | yes | yes |
| far baseline L p90 | 3.87 cm | **3.98 cm** (paired median +0.11 cm; 2/50 trials > 5 cm) |
| far service line L p90 | 3.03 cm | **3.86 cm** (1/50 > 5 cm) |
| kappa bias | +1.4% | +2.2% |

**Reading:** the on-grid coincidence flatters a little, not decisively. A real PSF is not Gaussian at
all, and that case is untested.

## 4. Numbers match — CONFIRMED

Every per-line p90 (M and L) for P, A3, ctl1, ctl2, ctl2s0, ctl3a and ctl3b was recomputed from the rows
and matches both the stored summaries (difference < 1e-12) and the evidence tables to rounding. The
headlines check out:

- **P:** far baseline 3.58 cm (L) / 0.97 cm (M); far service line 3.42 cm (L).
- **A3:** far baseline 0.93 cm (L).
- **Controls:** ctl1 max 0.57 mm (L) / 0.12 mm (M); ctl2 worst p90 5.6 mm; ctl3a 0.0997–0.1001 px;
  ctl3b paired mean 0.0993 px (sd 0.0023).
- **Side metrics:** f error −0.26 px median, |p90| 0.31 px; camera height |err| p90 0.5 mm; kappa +1.4%;
  bitrate 19.9 Mbps p50.
- **P − A3, paired:** far baseline +1.21 cm median, far service line +1.36 cm.

**Nothing was excluded.**
- 0 failures in every arm.
- 0 infinite readouts.
- Trial ids run 0..n−1 with none missing.
- P and A3 use identical draws per trial.
- The smallest station count is 5, on the far singles halves; the bar needs 4.

**The tail, which the evidence does not report.**
- **Far baseline (L):**
  - **4 of 400 trials exceed 5 cm** (max **5.69 cm**, trial 268); 40 of 400 exceed 3.58 cm.
  - p95 4.21 cm, p99 4.95 cm.
- **Far service line (L):** 4 of 400 trials exceed 5 cm (max **6.75 cm**).
- No trial exceeds 10 cm on any line. M never exceeds 1.38 cm.
- **The worst trials share a pattern:**
  - they have low contrast (70–98 DN) and/or wide PSF (1.15–1.20);
  - the seed error does not explain them;
  - A3's error on the same draws is 0.3–0.9 cm, so the tail is the codec.
- **Subgroups (n ≈ 30–100 each, descriptive only):** far-baseline L p90 is 4.31 cm at contrast 60–85 DN,
  and 4.51 / 4.69 cm at PSF 1.15 / 1.20. **The margin is thinnest at low contrast with soft optics**,
  which is what a worn, distant line looks like.

## 5. Reproduction — CONFIRMED

- **ctl1 and ctl3a** (seed 0, n = 20), re-run from the frozen code: **bit-identical** to the scored JSON
  (max difference 0 on every line error and on the far-baseline offset).
- **Arm P, n = 50, seed 1** (tool clean; stamped HEAD `a00dbf4`, tool unchanged since `4ac52fc`):
  - 0 failures; **every line p90 ≤ 5 cm.**
  - Worst: far baseline **3.87 cm (L) / 0.95 cm (M)**, far service line 3.03 cm; far sidelines ≤ 0.95 cm.
    Seed 0's first 50 trials gave 3.89 / 3.12 cm, so the result is consistent.
  - 1 of 50 far-baseline trials reached 5.36 cm. **No line exceeded 10 cm**, so the pre-registered
    reproduction concern did not fire.

## 6. Encode realism — the pass is codec-bound (judgement, from existing numbers)

- **The codec spends most of the far-baseline margin.**
  - P against A3 at p90: 3.58 vs 0.93 cm, so the codec costs **+2.65 cm** of the 5 cm budget.
  - Paired: +1.21 cm median, and P is worse in 93% of trials.
  - The remaining margin is **1.42 cm**. If the codec cost adds roughly linearly, **the far-baseline pass
    survives only if the real encoder's cost is ≤ ~1.5x libx265's here.**
- **Why that cost is likely understated:**
  - The achieved bitrate was 16.6–21.6 Mbps (p50 19.9), +24% over the 16 Mbps target.
  - libx265 preset medium is generally more efficient than a hardware real-time encoder (judgement).
  - Chroma is flat, so every bit goes to luma.
  - The 0.5 s static clip is mostly one I-frame.
  - There is no motion, no spatial denoise and no sharpening.
  - QA's recollection, **UNVERIFIED**: iPhone 1080p60 HEVC records at roughly 12 Mbps, below the 16 Mbps
    target.
- **Consequence:** the codec is the most likely thing to flip the far baseline and far service line to
  INDETERMINATE on a phone. Stage 2 should include an arm at the phone's real bitrate, or a real
  iPhone-encoded render, before anyone relies on the far lines.

## What should change in how the result is reported

- Relay it as **"PASS on a rendered court, qualified":** one camera pose, which was also the development
  pose; σ on-grid; a linear sensor; flat chroma; and a codec margin of ~1.4 cm on the far baseline.
- Quote the tail alongside the p90: **1% of trials put the far baseline or far service line past 5 cm**
  (max 5.69 / 6.75 cm).
- **No STATE number is wrong.** Suggested text for the lead to add to the CP1 row's caveats (QA does not
  edit STATE): "qa 2026-09-17: PASS QUALIFIED — numbers reproduce bit-for-bit, no truth leak; tail 4/400 >
  5 cm on the far baseline and far service line; one camera pose for dev and score; σ on-grid (off-grid
  probe: far baseline 3.87→3.98 cm, n=50); codec margin ~1.4 cm. [evidence/court-fit-cp1-qa.md]"
- **Before stage 2, backend-dev should (QA does not fix these):**
  - pass `cx = W/2`, not `rcam.cx`, before A9;
  - fix the duplicate `"seed"` stamp key;
  - take the commit stamp at run START;
  - key the render cache on the code as well as the version string;
  - add at least one scored pose that was not used for development.
