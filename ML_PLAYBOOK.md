# ML_PLAYBOOK.md — tennis computer-vision ML, for whoever works this repo

> **Two ML docs, two jobs.** This file (PLAYBOOK) is the *technique*: how to
> diagnose a weak model and what to steal from the field. **[ML_PRACTICES.md](ML_PRACTICES.md)**
> is the *discipline*: how to conduct the work honestly (never grade a model on its
> own outputs, tag every number, the session-end checklist). Read **both** before any
> model work — CLAUDE.md requires it. Current state lives in CLAUDE.md's Status +
> [docs/STATE.md](docs/STATE.md); [docs/archive/HANDOFF.md](docs/archive/HANDOFF.md) is the historical evidence log this
> file cites, and [docs/archive/sessions/](docs/archive/sessions/) holds the pre-registered briefs, all of which have run.

Operate as a machine-learning engineer who specializes in tennis computer
vision: small-object tracking, keypoint/geometry estimation, motion-blur and
occlusion, physics-based prediction, and pose-driven shot understanding. This
file is the standing reference for *how to think* when a model here is weak —
diagnose the real cause before touching a knob, and measure honestly.

The project's own architecture rule still governs (CLAUDE.md): **learn what you
can't compute, compute what you can.** ML is only for perception (court
keypoints, ball, pose, shot type). Geometry (homography, speed, line calls) and
logic (scoring, rallies) are exact — never ML-ify them. Most "model" problems
here are actually data, domain, or evaluation problems.

---


> **Scoped to the court feature 2026-09-17.** Sections on ball tracking, prediction, pose, the
> failure cheat-sheet and the ball state of the art are archived in `swingpath:docs/archive/2026-09-17-pre-court-only/ML_PLAYBOOK.md`.

## 1. Diagnose before you adjust — the five buckets

When a model is weak, attribute the weakness to ONE of these before changing
anything. Guessing wastes training runs.

1. **Evaluation / leakage** — is the number even real? A train/test leak, a
   metric that rewards the wrong thing, or scoring against pseudo-labels all
   produce fake confidence. *Always fix this first.* (We caught `indoor_elev =
   yt_rally2` in both ball and court training; the gold sets are held out.)
2. **Data** — too little, imbalanced, noisy labels, or the labels came from a
   weaker model (pseudo-label ceiling: a student can't beat its teacher). Most
   gains in this repo are here.
3. **Domain shift** — train and deploy distributions differ (broadcast → phone;
   hard court → clay; bright → dim indoor). The model is fine; it's just never
   seen the target. Fix with target data + augmentation, not more epochs.
4. **Architecture / representation** — the model *cannot express* the answer.
   Example: CourtNet is a heatmap model, so it can only place a keypoint peak
   *inside* the image; it structurally cannot predict an off-frame corner that
   an amateur wide angle needs. No amount of data fixes a representation limit.
5. **Optimization** — LR too high/low, loss collapsed to background, catastrophic
   forgetting, under/over-fitting. Read the train-vs-val curve before blaming it.

Quick triage: **train acc low → underfitting (capacity/optimization/labels).
Train high, val low → overfitting or domain shift. Val high, real-world low →
leak or eval-set unrepresentative.**

---

## 3. Court / keypoint detection + homography

- **Heatmap keypoint model** (CourtNet): 14 named landmarks → homography. Fast,
  but the off-frame limitation above is real — amateur frames with cut-off
  corners need either coordinate regression, a homography/parametric output, or
  a classical intersection step that recovers corners outside the frame.
- **The homography is the whole game downstream.** Speed, line calls, and shot
  placement are exact functions of it. A court that's slightly wrong silently
  corrupts every number — so a *confidently-wrong* court is worse than no court.
  Prefer refusing (→ manual corner-drag) over drawing a bad court.
- **Self-check with geometry priors** (calibration.verify_court): project the
  rigid court template and measure how much lands on real white-line pixels
  (coverage) + whether it sits centrally (rejects background/adjacent courts).
  The template is also the line-continuation prior: you always know where a line
  *should* be even where the paint is faded/occluded/cut.
- **Line detection must be lighting-invariant.** Global thresholds (tophat+Otsu)
  collapse on dim indoor / bright-ceiling amateur footage. A bright-*ridge* test
  (brighter than a few px to the sides) + low-saturation (white, not coloured)
  is robust (line_ridge_mask lifted amateur coverage ~9-31% → 55-62%).
- **Domain adaptation for the learned path:** fine-tune the broadcast model on
  target angles with **random-perspective augmentation** (re-warp each labeled
  frame as a new camera). Guard **catastrophic forgetting** by balancing/
  oversampling domains so the target's few frames don't drown, and the source
  isn't forgotten. Fixed camera → detect once and *lock/smooth* the homography;
  don't re-detect a jittery court every frame.

## 6. Data auditing (the QA lens that catches most "model" problems)

Before training, audit: **leakage** (same clip/footage in train and test),
**label provenance** (human vs pseudo-label vs projected), **balance** (surfaces,
angles, near/far, ball present/absent), **noise** (static-lock junk, drifted
clicks), **coverage gaps** (which real cases have *no* labels — usually the fast
/ far / occluded ones). A held-out, human-labeled gold set is the only honest
scoreboard; never train on it, and re-score the same set before/after every
change so "better" is a number, not a vibe.
