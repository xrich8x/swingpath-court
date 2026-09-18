# backend-dev — working journal

**READ THIS FIRST IF YOU ARE RESTARTING.**

**SCOPE: the court feature only (founder, 2026-09-17).** Earlier non-court history lives in the main repository (`xrich8x/swingpath`).

---

## TASK

**G7: does a photometric cost separate a RIGHT camera from a WRONG one?** (pm, 2026-09-18,
branch `camera3d-pnp-paintfit`, commit locally, DO NOT PUSH.)
Three roadmap items assume it does: item 3's multi-anchor selector, item 1 Tier 2's acceptance
rule, item 4's "not locked" re-localisation trigger.

Deliverables: (1) G7 pre-registration committed BEFORE the run; (2) `tools/court_cost_separation.py`
seeded + re-runnable, rows to `data/output/`; (3) results in the same G7 section; (4) a STATE row;
(5) local commit.

## STATE

**TASK COMPLETE** apart from the final report to the lead. All five deliverables done.
- adafc41 G7 pre-registration (BEFORE the run). 026c55b the tool (BEFORE the run).
- Scored run: `--n 400 --seed 0 --workers 10`, 1,059 s ->
  `data/output/court_cost_separation/G7_seed0_n400.json` (force-added; data/output/*.json is
  ignored in subdirectories but the arm-K artifact is tracked by the same precedent).
- Results + STATE row + `backend/tests/test_cost_separation.py` (8 pass) committed.

## THE ANSWER (do not re-derive)

**SEPARATES.** 398 scored, 33 wrong (8.3%) vs 365 right; 2 trials threw (`pass N: no measurements`).
- **`camera3d.paint_check(...).ok`, the SHIPPED flag, catches 33/33 at 1 false flag in 365** — and
  that flag, trial 32, is a MISLABEL (focal right to 0.01%, worst line INFINITE). Recorded, not fixed.
- Held-out (pre-registered split): support / ridge-mean / ridge-frac-found all 17/17 at 0.55%
  = SEPARATES; worst-line and ridge-median 15/17 = PARTIAL (degenerate threshold at exactly 0.0).
- **The fit's OWN robust cost is INVERTED: AUC 0.216, wrong beats right in 78.4% of head-to-heads.**
  Unweighted px cost AUC 0.693, still loses 30.7%.
- Trial 69 (+132% focal) scores support 1.000 by pushing the court OUT OF FRAME; only the
  `min_across`/`min_along` structure guard catches it.
- Null control PASSES: 1,000 permutations, catch == false-flag rate, `separates_rate` 0.000 on 7/7.
- **Blind spot on every one of 398 trials:** `unchecked` = [far_baseline, far_service]. This
  separates GROSSLY wrong cameras only; it says NOTHING about the 5 cm question.

## SMOKE RESULT (n=3, seed 99, all three RIGHT cameras) — keep, it sets scale
- true camera:  support 0.940-0.993, worst-line frac 0.912-0.981, ridge_med 0.033-0.087 px@720
- fitted (right): essentially identical to the true camera (support to 4 dp, ridge_med within 0.003)
- PnP SEED camera: support 0.12-0.34, worst-line frac 0.00-0.03, ridge_med 2.6-3.8 px@720
  -> the instruments have a big dynamic range on a KNOWN-bad camera. Encouraging, not the answer.
- `unchecked` is ALWAYS ['far_baseline','far_service'] — the declared far-line blind spot, confirmed.
- fit's own cost px_med 0.014-0.021 px on ~950 points; w_med 1.2-1.8.
- 14.7 s per trial at 3 workers.

## KEY FACTS ESTABLISHED (do not re-derive)

- `data/output/court_camera3d_seed/K_seed0_n400.json` rows have NO `params`/`seed_params`
  (verified: row keys are trial, contrast, psf, kbps, n_kps, outliers, dropped_cross_ratio,
  outliers_kept, seed_f, seed_h, K0, ok, lines, far_bl, sig_est, kappa, f_fit, lam_fit, cam_h,
  t_total_s). So the FITTED CAMERA IS NOT RECOVERABLE from that file -> must re-run.
- Arm K used plain `paintfit.r1_fit` (NOT `fit_camera_checked` — no `check`/`starts` keys in the
  rows). Score the raw fit; compute paint_check post hoc. That is the right experiment anyway:
  `fit_camera_checked` already uses paint_check as an acceptance rule, which would beg the question.
- Reproducing arm K exactly: `np.random.SeedSequence([seed, trial]).spawn(3)` ->
  r_scene, r_seed, r_noise; contrast ~ U(60,160); psf from PSF_GRID; keypoints =
  court.LANDMARKS_3D projected through `T.truth_camera(True, 0.0)` and kept in frame,
  + N(0, 14.78) per axis, + 2 outliers 100-300 px.
- Render coverage IS disk-cached (`data/output/court_fit_cp1/cache/cov_*.npz`, 3 present).
- f_true = (1920/2)/tan(50 deg) = 805.35 px. Wrong camera := |f_fit - f_true|/f_true > 0.01.
- `T.truth_camera(True,0)` has cy = H/2 exactly, so `CourtCamera.from_paintfit` accepts it
  (it refuses an off-centre principal point). Lens comes out "brown".
- `camera3d._samples(step_m)` gives (world, wdir, ids, names, widths) — paint centrelines at
  step_m, >=0.3 m clear of other lines. `camera3d.ridge_offsets(grey, pts, nrm, reach, min_dn)`
  is the sub-pixel ridge finder.

## LOG
- CARRIED FORWARD: `python` broken Store shim -> use the CPU venv at
  "E:\Claude Outputs\Cowork Tasks\Swing Vision\backend\.venv\Scripts\python.exe" (this repo has none).
- CARRIED FORWARD: grep -rn at repo ROOT times out (walks .venv) - grep explicit dirs.
- CARRIED FORWARD: Grep/Glob TOOLS false "no matches" (T25); use bash grep.
- CARRIED FORWARD: long markdown via heredoc FAILS -> use Write tool for long docs.
- CARRIED FORWARD: bash /tmp not visible to Windows python.exe - use scratchpad abs path.
- CARRIED FORWARD: tools/ and ball_physics/ are at the REPO ROOT, not under backend/.
- CARRIED FORWARD: smoke-test at small n before any long run (float32 JSON crash, 25 min).
- CARRIED FORWARD: the `researcher` agent was DELETED by the founder 2026-09-18. Do not reference it.
