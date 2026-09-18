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

- Step 1 DONE: read CLAUDE.md, STATE.md, court-camera3d.md, ML_PRACTICES.md, camera3d.py,
  paintfit.py, court_camera3d_seed.py, court_fit_cp1.py.
- Step 2: write + commit the G7 pre-registration.  <- IN PROGRESS
- Step 3: write the tool, smoke at n=2, then run n=400 seed 0.
- Step 4: analyse, write results, STATE row, commit.

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
