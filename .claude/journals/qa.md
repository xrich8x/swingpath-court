# qa — working journal

**READ THIS FIRST IF YOU ARE RESTARTING.** A usage limit kills an agent outright and nothing restarts it
automatically. Whatever is below is what survived.

**SCOPE: the court feature only (founder, 2026-09-17).**

---

## TASK — 2026-09-18: audit the 3D court camera (G7, tracker fixes, rule-7 lift, libx265 nondet)
Branch camera3d-pnp-paintfit. Python: "E:\Claude Outputs\Cowork Tasks\Swing Vision\backend\.venv\Scripts\python.exe".
1. G7 photometric separation: paint_check 33/33 @1 false flag/365; fit's own cost inverted AUC 0.216; ridge AUC 0.997;
   trial 32 "mislabel" claim; prereg-before-run; label circularity; split leak; null control; dev-data grading.
2. Post-G3 tracker fixes UNSCORED (camtrack.py, paint_check/fit_camera_checked) - what is established vs not; tuned-on-quoted-seeds?
3. Rule-7 lift no-op claim; re-run backend/tests/test_paintfit_lift.py + one other arm.
4. libx265 nondeterminism - confirm/refute independently.
Deliverable: append "QA AUDIT 2026-09-18: the 3D court camera, G7 and the unscored tracker fixes" to
docs/evidence/court-camera3d.md + 1 STATE row if material. Commit locally, DO NOT PUSH.

## STATE
- Started. Prior task (CP1 audit) DONE, archived below.

## LOG
- 2026-09-18 start. git: prereg adafc41 (21:04) -> tool 026c55b (21:08) -> results db33a45 (21:51). Results commit does NOT touch tools/court_cost_separation.py => tool unchanged after commit. Need: camera3d.py threshold history.
- PRIOR TASK (CP1 stage 1 audit) COMPLETE: docs/evidence/court-fit-cp1-qa.md, verdict PASS QUALIFIED, committed.
- G7 pop CONFIRMED from rows: stamp commit 026c55b dirty=false (run AT the instrument commit, after prereg adafc41); 400 rows, 2 threw (20,398), 398 ok, 33 wrong / 365 right; f_true 805.5356 (prereg text says 805.35 = typo, tool computes it); basins -13.6/-13.7 x8, +15.3-15.6 x4, +132.4 x1 - all match evidence.
- ALL 7 AUCs reproduce EXACTLY (support .9679, worst_frac .9683, ridge_med .9617, ridge_mean .9972, ridge_found .9973, self_px .6930, self_w .2157). NB AUC is NOT computed by the tool - backend-dev computed it ad hoc; my recompute is independent.
- TRIAL 32 CONFIRMED MISLABEL: focal rel -0.000103 (0.01%), but camera X 4.1124 vs ~5.485 = 1.37 m lateral shift; every sideline/centre-service 1.36-1.37 m out (M readout), L readout inf. Genuinely wrong camera the focal label calls right. Label untouched in code => hard rule 8 honoured.
- INDEPENDENT GEOMETRIC LABEL (worst-line M err > 0.10 m vs the exact rendering camera, no focal): 34 wrong; agrees with focal label on 33, adds only trial 32. paint_check.ok catch 34/34, FALSE FLAG 0/364. ridge_found AUC 1.0000, ridge_mean 0.9996. Headline STRENGTHENED, not weakened. Right-group worst line max finite 0.061 m => no hidden grossly-wrong camera among the 365.
- G7 held-out split REPRODUCES EXACTLY at split-seed 0 (all 7 instruments, catch+false to 4dp, verdicts). Ceiling table reproduces. Null control stored: catch_mean==false_mean, separates_rate 0.000 on 7/7.
- G7 FINDING (new, mine): the held-out verdict is SPLIT-SEED BRITTLE. Over split seeds 0-9: support SEPARATES on 3/10 (catch 0.765-1.000), ridge_mean 3/10, ridge_found 3/10 (catch as low as 0.471), ridge_median 0/10. Cause: threshold set at exactly 90% catch on train (17 wrong) leaves zero margin; 2 held-out misses of 17 flips SEPARATES->PARTIAL. Seed 0 was pre-registered so this is not p-hacking, but the label "SEPARATES" is an n=17 coin flip. The WHOLE-POPULATION rules (33/33 @1/365) are not split-dependent and are the durable result.
- Rules over all 398 reproduce: paint_check.ok 33/33 @1/365 (trial 32); ridge_found<1 33/33 @1/365; support<0.90 32/33 @1/365; ridge_mean>=0.2348377 33/33 @6/365 BUT literal ">=0.235" as written in the table gives 32/33 (rounding).
- Trial 69 CONFIRMED: +132.4% focal, support 1.000, 5 lines all frac 1.0, unchecked = all 4 cross-court lines, ok False via worst="too_few_lines".
- Tracker-fix dev numbers exist ONLY in .claude/journals/lead.md (seeds 100-102 p90 3.5 cm, 1-frame recovery, KC 101/102 0 silently wrong). NOT in docs/evidence/ and NOT in STATE; STATE's G3 row still says KILL. So the record does not overclaim.
- LIBX265 NONDETERMINISM CONFIRMED INDEPENDENTLY: 4 encodes of a byte-identical 30-frame array -> kbps 18919.7/18933.3/18945.2/18937.2, decoded mean differs on ~1.8M of 2.07M px, max |dDN| 1.47. Downstream: arm P seed 1 trials 0/1/2 x3 repeats -> far_baseline L spread 0.302/0.236/0.657 cm. "up to ~0.7 cm" CONFIRMED.
- test_paintfit_lift + test_cost_separation: 12 passed (A3 trial 0 matches pre-lift pins at rel 1e-9).
- RULE 7 CONFIRMED INDEPENDENTLY: fresh git worktree at b3af0ca (pre-lift) vs HEAD, ctl1 (3 trials seed 7) + ctl2 (4, seed 0) + ctl3a (1): 768 values compared, 0 differing. Plus test_paintfit_lift A3 trial 0 passes at rel 1e-9.
- TRACKER SIM RE-RUN BY ME. Dev seeds 100-102 REPRODUCE the lead's journal numbers exactly: worst p90 3.52 cm (claimed 3.5), steady jump 0.18 px, knock recovery [1,1,1], 1 locked-but-wrong frame, 358 locked / 2 unlocked. FRESH seeds 200-202 (never used in dev): worst p90 2.41 cm, jump 0.18 px, recovery [1,1,1], 1 locked-but-wrong, 358/2. => the fixes are NOT tuned to the quoted seeds; they generalise (and improve) on held-out seeds.
- BUT the silent wrong lock persists on BOTH sets: seed 101 frame 60 (knock) locked=True status=tracking at far_baseline 70.4 cm / far_service 44.2 cm; seed 201 frame 60 56.8 / 35.8 cm. Near lines <=10 cm. Those are exactly the 2 lines paint_check lists UNCHECKED => G7's declared blind spot is demonstrated, not hypothetical.
- G7 within-accepted power (mine, n=364 excl trial 32): worst line <=1.48 cm; rho(support, worst-line) -0.682 but rho(support, far_baseline L) only -0.265; ridge_found is CONSTANT 1.000 across all 364 => zero resolving power inside the accepted set. Quantifies "says nothing about 5 cm".
- paint_check docstring + camtrack q comment both cite "docs/evidence/court-camera3d.md, G5" - THERE IS NO G5 SECTION in that file. Dangling provenance for the tuned thresholds.
- camtrack.TrackConfig comment states q 1e-2 -> 100 was changed on "dev seed 100", one of the seeds the 3.5 cm is quoted against => tuned on a quoted seed (but held-out seeds confirm it anyway).
- PENDING: knock x4 on fresh seeds running -> scratchpad/sim_fresh_k4.json. Then write the evidence section + commit.
- knock x4 FRESH seeds 200-202: lost at frame 60 on 3/3, never recovered, 0/180 locked-but-wrong, worst p90 while locked 2.34 cm => dev claim reproduces held-out.
- Evidence section appended to docs/evidence/court-camera3d.md (12-claim verdict table + 7 subsections + STATE row as TEXT ONLY; did not touch docs/STATE.md). Committing next.
