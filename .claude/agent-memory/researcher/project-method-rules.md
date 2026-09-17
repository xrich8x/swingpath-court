---
name: project-method-rules
description: Standing technical constraints and the two method rules this project learned the hard way — gold discipline, threshold scaling, the proxy that does not predict the gate
metadata:
  type: project
---

Backfilled 2026-08-27 from `docs/STATE.md`, `docs/TRAPS.md`, git history.

## Constraints, and why they exist

- **Geometry is closed-form and never learned.** Perception (ML) / geometry (math) /
  logic (rules) is the architecture, not a preference. ML-ifying geometry adds error to
  exact answers. *(This is also what made the geometry portable to a phone — a dividend
  the decision was never framed as buying.)*
- **Ball/court gold is TEST-only, one-way, enforced** — `assert_no_gold_leak`,
  `assert_no_court_gold_leak`, `assert_no_swingvision_leak`. This exists because **17 of
  20 court gold clips were also in the training set** (trap T06); every figure in
  `court_scores.md` had been the model scored on its own homework.
- **Truth comes from the GAME, not the VIDEO** — no scoreboard, HUD or burned-in graphic
  as training target, ground truth or tuning signal. Independence is not truth: a
  diligently-kept wrong board is perfectly self-consistent.
- **Pixel thresholds scale by `frame_height/720`**, except `static_radius_px` where
  measurement says otherwise. Unscaled 720p constants silently deleted real balls at
  1080p (trap T03).
- **One variable per A/B, seeded** (trap T10). `train_ballnet.py` had no seed at all, so
  one session's two arms differed by weight init, batch order and augmentation as well as
  by the flag under test.
- **Single GPU, one job at a time**, enforced by `lab_jobs.py`. Don't propose parallel
  training. Don't fan out to parallel agents either (trap T07) — two multi-agent runs
  burned ~971k tokens for zero results.
- **The two venvs are an OpenCV MAJOR version apart.** No experiment here has ever
  separated device from libraries. `tools/freeze_env.py` exposed this.
- **A low camera limits measurable depth to 22-32% of the court.** `am_hard_utr` (the
  primary 1080p gold) fits a 1.74 m camera and is measurable only to court-y 7.5 m of
  23.77 — it does not reach the net. Any far-court number on that clip is detection
  recall, never a measurement. `demo30` is 0.5 px but 1.38 m, measuring 5.2 m of 23.77.
- **The court precision gate: >=12 of 20 gold clips accepted, AND zero accepted court more
  than 20 px from human clicks** (`WRONG_PX_640 = 20.0`). It has not moved. Two changes
  have already died on admitting one wrong court.

## Two method rules learned the hard way

- **The search-free proxy does NOT predict the product gate.** `eval/score_truth.py` is a
  screening tool, **never a gate**: three mask arms were indistinguishable on it (28/30)
  and spanned 6/20 to 13/20 on the real gate, because the proxy asks only whether the
  criteria *recognise* a court handed to them — not what the search finds, nor how four
  downstream stages react.
- **Tuning happens on the 10 original calibrated clips; the shell set is VERIFICATION
  ONLY.** No threshold may be chosen, swept or adjusted against shell. You cannot un-see a
  test set, and pre-registering each individual sweep never stopped the cumulative drift of
  a dozen sweeps against one fixed population.
