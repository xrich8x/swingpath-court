# backend-dev — working journal

**READ THIS FIRST IF YOU ARE RESTARTING.**

**SCOPE: the court feature only (founder, 2026-09-17).** Earlier non-court history lives in the main repository (`xrich8x/swingpath`).

---

## TASK

**G8: make the FAR LINES CHECKABLE, and make LOCK HONEST.** (lead, 2026-09-18, branch
`camera3d-pnp-paintfit`, commit locally, DO NOT PUSH.)

The gap qa named: `paint_check` marks `far_baseline`/`far_service` `unchecked` on 398/398 G7
trials (`min_width_px_720 = 0.67` drops them). Consequence measured: dev seed 101 and fresh seed
201 knock frames report `locked=True, status="tracking"` while 70.4 / 56.8 cm out, ALL of it on
those two lines.

Build (1) a far-line-observable acceptance test (multi-scale pyramid / along-line integration /
matched filter — my call, must be cheap, must not read far-line position from the model it checks);
(2) HONEST LOCK SEMANTICS — paint_check + camtrack.TrackStep.locked say WHAT was verified;
setup_state carries it to match.json.

Deliverables: G8 pre-registration committed BEFORE the run; implementation; tests; results in G8;
STATE row; local commits.

## STATE

RESTART #2 (session limit killed run 1 before any commit). G8 PRE-REGISTRATION WRITTEN AND
COMMITTED at 46e5fe7 (docs/evidence/court-camera3d.md, +~160 lines). Baseline suite:
**2 failed / 394 passed / 10 skipped** (both failures test_recording_identity.py, pre-existing).
NOW: implement Part A (camera3d.far_line_profile, along-line segmented stacked normal profile),
Part B (X265_DETERMINISTIC in tools/court_fit_cp1.py behind --codec-profile), Part C (PaintCheck
.scope/.checked, TrackStep.lock_scope, setup_state camera lock block). Then dev sweep on sim seeds
300-305, score on 400-402 + knock frames of 101/201, non-degradation on G7 arm K n=400 seed 0.

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
- G7 ANSWER (done, committed): paint_check.ok catches 33/33 wrong cameras at 1/365; fit's own cost
  INVERTED (AUC 0.216). Blind spot far_baseline+far_service on 398/398.
- G8 IMPLEMENTED camera3d.far_line_profile + paint_check(far_lines=True) -> far_baseline and
  far_service move from `unchecked` to `checked` at 1080p. 12-26 ms per call.
- **G8 BLOCKER FOUND AND SOLVED: tools/court_track_sim.py's renderer ALIASES sub-pixel paint.**
  ss=2 (shipped) point-samples 2x2 per pixel and blurs AFTER binning, so a 0.19 px far baseline is
  hit by almost no sub-sample. Stacked normal profile of the TRUE camera, noiseless:
  far_baseline dn 0.488 offset +3.96 px (garbage) at ss=2; dn 10.6 off -0.135 at ss=4;
  dn 5.1 off -0.130 at ss=8; dn 7.9 off -0.133 at ss=16. far_service is aliased the OTHER way,
  dn 21.5 at ss=2 vs 7.9 at ss=16. **Amplitude never converges (phase is constant along a
  horizontal line, so stacking cannot average it) but the OFFSET converges from ss=4.**
  Render cost 0.73 / 2.70 / 10.62 s per frame at ss 2 / 4 / 8.
  => add --ss to court_track_sim (default 2, every prior number untouched), score G8 at ss=4,
  declare NOT comparable with G3 / the 100-102 / 200-202 tracking numbers.
- Systematic bias seen on the TRUE camera at ss>=4: far_service +0.17 px, far_baseline -0.13 px.
  Real (photometric centroid of foreshortened paint != geometric centre); ~4 cm. Eats the budget.
- RENDERER: ss alone does NOT fix it. Two independent faults, both measured:
  (a) fixed-grid sub-samples hit/miss a 0.13-0.19 px band by PHASE; (b) PSF applied
  AFTER binning quantises the line onto a pixel centre (0.5 px error at 720p, any ss).
  FIX = CP1's order: JITTERED stratified sub-samples + PSF at sub-sample resolution.
  `court_track_sim.render(..., subpixel=True)`, default False so no prior number moves.
  At 1080p ss=2 subpixel: far_baseline z 6.8-9.5, offset -0.04..+0.05 px (vs -0.13), 0.97 s/frame.
  At 720p it still cannot be seen at all (0.13 px paint, 0.9 px blur) -> correctly UNCHECKED.
- DESIGN FIX that made test_camtrack pass again (49/49): _seg_hit returns DETECTED separately
  from HIT. No peak anywhere in the window = cannot tell a wrong camera from invisible paint
  => the line goes back to `unchecked`, NOT to failed. frac = hits / segments-that-saw-it.
- PART B done: X265_DETERMINISTIC + _encode_argv + --codec-profile in tools/court_fit_cp1.py.
- PART C done: PaintCheck.scope/checked/far/detail/claim(), TrackStep.lock_scope/lock_unverified/
  lock_worst/claim(), fit_camera_checked writes lock_scope+lock_claim into camera.extra.
- PART B SMOKE PASSES (n=2, arm P, seed 900): deterministic profile -> 0 differing fields,
  far_baseline L identical (0.9225 / 0.5066 cm both runs). NULL CONTROL cp1 profile -> 14
  differing fields, far baseline 1.3955->1.1608 and 1.6865->1.9679 cm. n=4 running.
- GATE TOOL tools/court_far_line_gate.py written. reach_px_720 raised 3.0 -> 8.0 (dev choice):
  at 3.0 a >1.6 m far error falls OUTSIDE the search window and reads `unseen`, not flagged.
  Verdict scored is the WHOLE paint_check.ok. false-flag rate is INCREMENTAL over cases the
  pre-G8 check already passed (bar 2's wording).
  1-seed smoke: catch 1.000 at tol<=0.35, 0.962 at tol 0.50; pre-G8 baseline floor 8.7% false.
- far error = max(far_baseline, far_service_line) per C1 names (G8's registered wording);
  far_half_err_m (all `far_*` C1 halves) recorded beside it.
- DEV SWEEP DONE (seeds 300-305, 1728 cases, 8x5 grid). far_min_z INERT across 3-8.
  STACK registered choice tol 0.75@720 z 5.0(tie): catch 0.917, incremental false 0.000.
  (tol 0.50 -> catch 0.979 at 1.6% false, just over my 1% rule; do NOT re-pick post hoc.)
  PYRAMID (founder's arm) tol 0.50 dn 3.0: catch 1.000 at 0.000 -> **MY PREDICTION A3 IS WRONG**.
  pre-G8 baseline catch 0.833 / false 0.087.
  The 24 wrong cases pre-G8 MISSES are ALL PITCH: stack catches 12/24, pyramid 24/24.
  The 12 pre-G8 false flags on good cases are ALL DEPTH at 5.0 cm - the shipped near-line
  check already refuses a camera 5 cm out in depth.
  Stack wins at (0.1,0.2] m (0.667 vs 0.417); pyramid wins at (0.2,0.5] (1.000 vs 0.667).
- PART B PASSES at n=4: deterministic 0 differing fields, bitrates identical to 0.1 kbps.
  NULL CONTROL cp1: 28 differing fields, far baseline L 1.2024->1.7625 / 2.0506->1.1809 /
  1.1255->0.5047 cm (spread to 0.87 cm, bigger than qa's 0.66).
- SHIPPED DEFAULTS now camera3d.FAR_TOL_PX_720 = 0.75, FAR_MIN_Z = 5.0.
- Tests: test_far_line_check.py (13) + test_codec_profile.py (6) pass; updated
  test_cost_separation.py::test_ridge_residual_STILL_has_the_far_line_blind_spot_paint_check_lost.
- RUNNING: G7 non-degradation (cost_separation n=400 seed 0) + held-out gate (seeds 400-402).
- HELD-OUT (seeds 400-402) REPRODUCES DEV EXACTLY: stack catch 0.9167 false_inc 0.000
  (BAR 1 >=0.90 PASS, BAR 2 <=0.02 PASS); pyramid 1.000 / 0.000; pre-G8 0.833 / 0.087.
  CAVEAT TO STATE: the ladder geometry is identical across seeds - only the sensor-noise
  realisation changes - so 400-402 test NOISE robustness, not scene generalisation.
  The 12 pre-G8 misses are again all PITCH; stack catches 6/12, pyramid 12/12.
- RUNNING: G7 non-degradation; tracker seeds 101+201 with --subpixel.
- TODO: tracker fresh seeds 400-402; obs_cost.py (4K + timing); G8 results; STATE row; commit.
