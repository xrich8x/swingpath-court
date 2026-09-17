# qa — working journal

**READ THIS FIRST IF YOU ARE RESTARTING.** A usage limit kills an agent outright and nothing restarts it
automatically. Whatever is below is what survived.

**SCOPE: the court feature only (founder, 2026-09-17).**

---

## TASK — DONE 2026-09-17: verify CP1 stage 1 (commits 4ac52fc code freeze, 99e1812 results)
Checks: 1 freeze integrity, 2 truth leakage (fn near line 274 "f and pp held at truth"), 3 shared
assumptions, 4 recompute tables from data/output/court_fit_cp1/, 5 rerun control1+3a, arm P n=50 seed 1
(>10 cm any line = reproduction concern; descriptive only), 6 encode realism from existing A3 vs P.
Output: docs/evidence/court-fit-cp1-qa.md, commit (no push). Verdict: PASS STANDS / QUALIFIED / DOES NOT STAND.

## STATE
- COMPLETE: docs/evidence/court-fit-cp1-qa.md written, verdict PASS QUALIFIED; committed, not pushed. Resumed once after a usage-limit kill.

## LOG
- 2026-09-17: journal reset to court scope.
- check1: tool unchanged 4ac52fc..HEAD and in worktree (git diff empty); tool has ONE commit (4ac52fc). JSON stamps next.
- check2 (code read): fitter r1_fit(img, seed_corners, FitConfig, rcam.cx, H/2). lam_star/truth_camera/ref_cam/HFOV only in run_trial setup, readouts, summarise, stamp = scoring. f free (bounds 200-4000) all passes. LEAKS/near-leaks: cx passed from TRUTH object (=W/2 in stage 1, latent leak for A9); fitter sig_grid 0.5..2.5 step .05 contains exactly the render PSF_GRID values (on-grid sigma, undeclared); profile model = exact render kernel form (pixel box x Gaussian); paint_lines()/centre_marks()/TapeLine/POST_X shared objects; surface/run-off boundary coincides with outer paint edge in both; ONE camera geometry for dev tuning AND scoring. stamp render_order string stale ("1/4 px grid").
- check1: all 7 JSONs stamp commit 4ac52fc8, dirty False, render cp1-render-5-smooth-kernel-sub2, 0 failures; every run STARTED after the freeze commit (ctl1 +20 s). BUT git_sha()/git_dirty() run at END (stamp()), and stamp dict has duplicate key "seed" -> numeric seed overwritten by description string (metadata bug). Coverage CACHE predates freeze: ctl1/ctl2 key 86a05df4 built ~4 h pre-freeze, P/A3 efa87348 ~4 min pre, ctl3a ff11a531 ~10 min pre. Cache key = RENDER_VERSION+geometry, not code hash -> re-rendering fresh (cache=False) to compare, scratch scripts in scratchpad.
- check4 DONE: every per-line p90 (P, A3, ctl1/2/2s0/3a/3b) recomputed from rows = evidence/STATE to rounding; 0 failures, 0 inf, trial ids complete 0..n-1; rows regenerate from SeedSequence([0,trial]); P/A3 paired identical draws. ctl3b paired L 0.0993 sd .0023. P-A3 median fbL +1.21 cm, fsL +1.36. TAIL: P far_baseline L >5 cm in 4/400 (max 5.69, trial 268), far_service L >5 cm in 4/400 (max 6.75); none >10 cm; M max 1.38 cm. fbL p90 by contrast 60-85 DN = 4.31 cm; psf 1.15/1.20 = 4.51/4.69 cm (subgroups n~30). sig_est == true psf in 100% of trials in ALL arms incl P (fitter grid contains render grid).
- rerender ctl1 running in bg -> scratchpad/rr_ctl1.txt
- check5: ctl1 + ctl3a rerun (seed 0, n 20, out to scratchpad) BIT-IDENTICAL to scored JSON (max diff 0). ctl1 cache (4 h pre-freeze) == fresh render from frozen code, max diff 0.0. P-geometry fresh render running -> scratchpad/rr_P.txt. Next: P n=50 seed 1 -> scratchpad/P_seed1_n50.json (log P1.txt).
- check3 notes (spec §7 read): f free in fit_camera every pass (CONFIRMED). Undeclared shared assumptions found: sigma on-grid (fitter grid contains render grid); linear sensor (no gamma/tone map/sharpening) - profile model is linear; chroma flat U=V=128 (all bits to luma) not in flattering list; step boundary exactly at outer paint edge; single camera pose for dev AND score; all 4 corners + 14 halves in view; cx passed from truth object (latent A9 leak); tape_top() sag function shared; square pixels. Controls ctl1/ctl3a n=20 (deterministic apart from contrast/psf) - minor vs addendum "400 every arm".
- check6 framing: P-A3 p90 fbL 3.58 vs 0.93 (+2.65 cm); margin 1.42 -> codec cost can grow ~1.5x before fbL p90 > 5 cm. Apple 1080p60 HEVC bitrate ~12 Mbps is my UNVERIFIED recollection.
- check5 DONE: P n=50 seed 1 (frozen code, run at HEAD a00dbf4 with tool clean): 0 failures, every line p90 <=5 cm; worst far_baseline L p90 3.87 cm (seed0 first-50: 3.89), far_service 3.03; 1/50 far_baseline trial 5.36 cm; none >10 cm -> no reproduction concern. P-geometry fresh render == cache (max diff 0.0), so pre-freeze caches are clean.
- PROBE (QA, pre-registered now, DESCRIPTIVE ONLY, cannot change verdict): fitter sigma grid shifted +0.025 px (true sigma falls midway between grid values), everything else identical, P n=50 seed 1 paired with the run above. Reading: report per-line p90 and paired far-baseline change; flag if any line p90 >5 cm. Script scratchpad/probe_sig.py -> probe_sig.json
- PROBE result: 0 fails; off-grid sigma (est always true +-0.025): far_baseline L p90 3.87->3.98 (paired median +0.11 cm, 2/50 >5 cm), far_service 3.03->3.86 (1/50 >5), every line still p90<=5; kappa bias +2.2%. Mild, margin thinner.
