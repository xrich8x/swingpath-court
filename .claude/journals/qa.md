# qa — working journal

**READ THIS FIRST IF YOU ARE RESTARTING.** A usage limit kills an agent outright and nothing restarts it
automatically. Whatever is below is what survived.

**SCOPE: the court feature only (founder, 2026-09-17).**

---

## TASK — 2026-09-22: audit G8 remediation + G9 (commits 0783ff0, c2d4537, a3f6a2a)
Branch camera3d-pnp-paintfit. Python: "E:\Claude Outputs\Cowork Tasks\Swing Vision\backend\.venv\Scripts\python.exe".
12 claims: G8 (1) --reach-mode fixed8 reproduces 13,680 cells; (2) 2.25px BAR1 .9028, BAR3 fails via unseen
dropped from denominator — verify mechanism; (3) BAR4 at 2.25 == far-lines-OFF on CP1 scene; (4) pyramid fails
BAR4 263/368, true 126/400, settings from sweep?; (5) FAR_LINES_DEFAULT False only defensible?; (6) forge
whole-court claim again; (7) stamp fix — name any prior result with wrong stamp. G9: (8) prereg before runs,
seeds 500-505 unused; (9) KILL applied correctly; (10) 5/6 stable?; (11) MECHANISM: why knock frame passes paint
check 41-65cm out (MOST IMPORTANT); (12) knock3/4 lost+0 false locks.
Deliverable: append "QA AUDIT 2026-09-22: G8 remediation and G9" to docs/evidence/court-camera3d.md, STATE row
as text, commit locally, NO PUSH. Lead already recomputed G9 headlines — go deeper.

## STATE
- COMPLETE 2026-09-22. Evidence section appended; memory g9-and-g8-remediation-audit.md written; committing locally (no push).
- Verdicts: 1 CONFIRMED / 2 CONFIRMED+correction / 3 CONFIRMED(outcome) / 4 numbers CONFIRMED, cause REFUTED (run-off step) / 5 CONFIRMED / 6 QUALIFIED / 7 QUALIFIED (reverse stamp) / 8 CONFIRMED+UNVERIFIABLE / 9 CONFIRMED / 10 QUALIFIED / 11 confined CONFIRMED, lag REFUTED / 12 CONFIRMED.

## LOG
- PROVENANCE: g8r far_line_gate artifacts (heldout_fixed8 19:59, dev_registered 20:02, heldout_registered 20:03, bar3 20:06:36) all PREDATE 0783ff0 (20:06:31) and stamp commit 501e793 with NO dirty flag => produced from an uncommitted tree; "instrument committed before any scored run" is FALSE for them. Only G8R_bar4 (0783ff0 clean, 20:33) and G9.json (c2d4537 clean, 20:53 > commit 20:40) are clean. bar3 sim json has no top-level stamp.
- Running in bg: my own --reach-mode fixed8 + registered heldout reruns -> scratchpad qa_fixed8.json/qa_reg.json; knock_diag.py (monkeypatched tracker, no source edit) seeds 500-505 frames 57-63 -> scratchpad diag_main.json.
- Mechanism hypothesis (to test): paint_check sidelines are WHOLE-LENGTH lines (doubles_L etc. 0->23.77 m), min_line_frac 0.5, so far-half sideline off + near-half on = pass; far_baseline/far_service unchecked (far lines OFF). Kalman gain ~1 (q=100) so lag unlikely - check raw pose vs KF.
- CLAIM 12 CONFIRMED from G9.json: knock3/4 seeds 500-502 frames 0-59 BIT-IDENTICAL to main (paired design real); post-knock 0/180 locked each arm, status all 'lost', scope 'none'; worst 105-131 m (x3), inf (x4).
- CLAIM 11 partial from G9.json: main arm non-knock worst max 2.59 cm; ZERO locked frames in 5-10 cm band; knock+1 frames 0.46-1.40 cm; all 720 statuses 'tracking' (501's knock frame = 'tracking' + locked False: fail_run<2 branch).
- CLAIM 7 FINDING: committed seeds101-201_n120_sub.json (G8 bar3 OFF arm, f3bddd6, mtime 09-19 12:58) stamps tracker_cfg.far_lines=TRUE but ran OFF (paint_check_far_lines False) - REVERSE of backend-dev's description; corroborates FAR_LINES_DEFAULT was True in tree then. _sub_far.json (ON arm, 12:47) has NO far_lines key in tracker_cfg. g8r reach2.25 file correct. seeds0-1-2 predates field.
- Seeds 500-505: no trace in repo/data/journals before c2d4537 (git grep at 0783ff0 empty; only G9.json in court_track_g9). Cannot inspect backend-dev's out-of-repo scratchpad (boundary).
- CLAIM 1 CONFIRMED (my run at HEAD, scratchpad qa_fixed8.json): 0 of 33,207 non-stamp leaves differ vs published heldout_seeds400-401-402.json AND vs g8r/heldout_fixed8.json. Registered rerun: 0 of 51,641 differ vs g8r/heldout_registered.json => the uncommitted-tree provenance of g8r files is HARMLESS (HEAD reproduces bit-exact). 13,680 = 171 rows x 40 cells x 2 arms.
- CLAIM 11 DIAG DONE (scratchpad diag_main.json; my replication reproduces G9 knock-frame worst 40.99/72.97/61.29/63.87/61.09/64.92 and locked flags EXACTLY).
  * NOT Kalman lag: KF prior (const-vel) is 1.8 deg / ~10 m off; KF output rotation == raw _pose_from rotation (drot 0.258-0.290 deg both); raw pose alone is 35-62 cm out. The RAW measurement under-corrects the ~1.8 deg step by ~15% (+4.6-6.3 cm position). backend-dev's "lags the step by one frame" inference is WRONG as stated.
  * Why check passes: far_baseline/far_service unchecked (far OFF); near cross lines all 1.0; SIDELINES POOLED whole-length at min_line_frac 0.5: seeds 502-505 doubles_L far-half hit 0.52/0.48/0.55/0.21 but near-half 1.0 -> pooled 0.754/0.737/0.772/0.596 PASS. Seed 501 caught only because doubles_L near-half fell to 0.536 -> pooled 0.263.
  * SEED 500 IS DIFFERENT: every line 1.0 incl. sidelines far half; with far lines ON it passes at BOTH windows (far_baseline frac 0.8 reg / 0.67 at 8.0) -> LOCKED whole_court at 41 cm. Error is sub-tolerance in pixels everywhere (pixel->metre amplification at far baseline).
  * far ON (reg or 8.0) would catch 502-505 and 501, not 500.
  * knock frame: resid 0.40-0.64 px vs 0.06-0.10 neighbours; flow_n 219-244 vs 302-311 (only frames 57-63 looked at; do NOT score a remedy on 500-505).
- CLAIM 2 BAR1 CONFIRMED: heldout_registered .75|5 = 65/72 catch, 0/63 false; 3 distinct miss geometries (pitch +/-0.05 all seeds, pitch -0.1 on 1 seed) of 24. Rule on dev picks .75|z3 (0.9167; z3/z4 tie). 
- CLAIM 4 provenance CONFIRMED: dev_registered pyramid_choice = tol .5 / min_dn 2.0 (0.9444), TIED with .5/3.0 (0.9444) -> tie broken by list order. Dev seeds 300-305.
- CLAIM 3 CONFIRMED by outcome: G8R_bar4 ok==ok_pre_g8 400/400 on fit, true AND seed cams; support identical 400/400; far lines checked on 0/400 true, 1/400 fits (a wrong one), 8/400 seed cams - never changes a verdict. Not literally inert but outcome-identical.
- CLAIM 4 numbers CONFIRMED: pyr right flagged 263/368, true ok 126/400, 262 flags = far_BASELINE (not far_service), median frac 0.0, 229<0.1, all level 0. BUT ATTRIBUTION SUSPECT: my geometry (3 m mount, 6 m setback, 0.914 net) puts the net tape ~5.6 px from far SERVICE and ~12 px from far BASELINE at 1080p; level-0 window is +/-2.25 px. "net tape lies over far baseline" looks wrong -> checking.
- SOLVER EXPT (scratchpad solve.json): knock-frame raw pose error is NOT the solver: least_squares from the TRUE pose converges to the SAME wrong pose (34.8/62.3/51.4/54.9/51.5/54.7 cm), nfev 16-17 << 60 (status 2). Cauchy cost at truth > at wrong pose (993 vs 980 etc) => DATA prefers the wrong pose. Snapped points: median |resid vs truth| 0.06-0.10 px, but 11-14% gross outliers (p90 ~20 px), concentrated FAR half (19-23% vs 5% near). Cauchy f_scale 4.5 px keeps ~43% influence at 20 px. linear loss -> 5-6 m, soft_l1 -> 2.8-5 m.
- PYRAMID ATTRIBUTION: CP1 true cam material scan: net TAPE is +12..+14 px BELOW far baseline (outside +/-2.25 px window), and -3.5..-7.5 px from far service; far service seen THROUGH net MESH. "net tape lies over the far baseline" is geometrically wrong. Running pyr_ctl.py (arm P vs clutter off vs codec off, trials 0-3).
- CLAIM 6 QUALIFIED: my 09-19 attack + bare string/{}/0/forged claim text all REFUSED now; double-normalise stable; 19/19 test_far_line_check pass. STILL FORGEABLE: whole_court with lock_unverified [] / absent / None / "" / "   " -> "Every court line was checked"; also paint_check="FAIL:near_baseline" + whole_court + [] -> same sentence (claim never carries pass/fail). Block has no re-verifiable evidence; only inconsistent pairs are caught. metrics_eligible False for forged block (not a gate).
- **PYRAMID ATTRIBUTION REFUTED (scratchpad pyr_ctl.json):** on CP1 TRUE camera, trials 1-3, far_baseline pyramid frac with clutter OFF = 0.009/0.000/0.020 (arm P 0.000/0.008/0.048; codec OFF 0.007/0.000/0.027). Trial 0 passes in all 3 (0.85/0.93/1.0). Per-point median offset +0.69..+1.0 px vs tol 0.75 px@1080; wide stacked profile peak at +0.75 px (+1.5 trial 2). => a SYSTEMATIC ~0.7-1.0 px far-baseline offset vs the true camera's projection, present with no net/tape/fence and no codec. Not clutter. Source unidentified -> testing distortion off.
- **CAUSE of pyramid bar-4 failure FOUND (scratchpad cp1_off.json, noiseless, no clutter, no codec, dist on AND off, trials 1-2):** far_baseline stacked peak +0.9/+1.0 px (centroid +1.22/+1.59) vs true projection; far_service/near_service/centre/singles 0.00; doubles_L/R +/-0.2 inward; near_baseline -0.07 inward. ALL 4 OUTER boundary lines biased INWARD = the court SURFACE(95 DN)/RUN-OFF(80 DN) brightness STEP at the boundary pulls the peak. Far baseline worst because its paint is 0.14 px (ridge ~ step). NOT the net tape (tape is 12-14 px away). The tracking sim has NO run-off step (flat SURFACE_DN) -> G9/bars1-3 scene lacks this bias.
- OUTLIER CONTROL (scratchpad outl.json): outliers ONLY on knock frame (0 on 58/59/61, 1 on 502/61). ALL on LEFT sidelines (22-29 far + 5-6 near), 100% negative sign, median -22.7..-26.4 px => coherent mis-flow (alley aliasing?) not noise. Trim (oracle AND 2-pass) fixes 501/503/504 (1.3-1.9 cm) but 500/502/505 -> 2.0-2.2 m. Naive trim is NOT a fix.
- ALL 6 knock frames >10 cm (41-73 cm): wrong-pose rate 6/6; caught 1/6. Half-split sidelines would catch 2/5 (503 far .483, 505 .207; 502 .517, 504 .552 pass). Far ON catches 4/5, turns 500 into whole_court.
- Claim 10: "1 in 3" was OLD renderer (100-102, 200-202 non-subpixel). On subpixel renderer my 09-19 paired control already had 2/2 (101, 201) locked-wrong. Pooled subpixel 7/8.
- CLAIM 2 MECHANISM CONFIRMED by invocation (scratchpad diag_bar3.json): seed 201 fr60 far_baseline at 8.0: offs -1.137,-0.844,-1.368,-1.375,-1.209,-1.070 (z 6-37, all seen), 2 hits/6=.333 FAIL. At 2.25 (tol 1.125, wing |s|>1.125): the two -1.37 ridges -> z 0 -> undetected; 2 hits/4 det = 0.50 >= min_line_frac -> PASS, scope whole_court. far_service 2/4=0.50 exactly. CORRECTION: dropped segments were the FURTHEST off (-1.37), not "just past tolerance"; range is -0.84..-1.375 not -0.84..-1.21. Seed 101 reg: far_service drops its worst seg (-1.388) too. => SYSTEMATIC: the further a ridge sits into the wing, the likelier it is dropped (anti-monotone in 1.125-3.375 px). Pass is on the >= boundary.
- CLAIM 9 CONFIRMED: no tools/backend change c2d4537->a3f6a2a; evidence diff additions-only (0 removed lines); KILL rule applied as registered; lbw = exactly the 5 knock frames.
- ALL MEASUREMENTS DONE. Next: write evidence section "QA AUDIT 2026-09-22: G8 remediation and G9", memory, commit.
