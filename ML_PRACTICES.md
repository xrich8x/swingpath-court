# ML_PRACTICES.md — how to build and tune models on this project

> **Two ML docs, two jobs.** This file (PRACTICES) is the *discipline*: how to
> conduct model work honestly and reproducibly. **[ML_PLAYBOOK.md](ML_PLAYBOOK.md)** is
> the *technique*: how to diagnose a weak model and what to steal from the field. Read
> **both** before any model work — CLAUDE.md requires it.

Read this before creating, training, tuning, or evaluating ANY model in this
project. It sits alongside CLAUDE.md (architecture + hard rules), ML_PLAYBOOK.md
(ML technique), and docs/archive/HANDOFF.md (historical evidence log). CLAUDE.md governs how we
work; this file governs how we do machine learning specifically.

The rules below are not generic ML advice. Every one of them is here because
this project already got burned by breaking it — see the pointers to docs/archive/HANDOFF.md.

The person running this project is not a developer (SQL only) and cannot read
code or audit a training run. That means a number they can't verify is worse
than no number at all. Honesty about what a metric actually means is the single
most important thing in this file.

## The one rule that matters most: never let a model grade its own homework

A model's score is only meaningful if it's measured against labels the model had
NO hand in creating. This project's biggest recurring mistake is self-grading:
reporting a number that looks like accuracy but is really the model agreeing with
itself or its own teacher.

Examples from this project's history:

- BallNet's "84.7% within-10px" is agreement with the fusion tracker's own locks,
  not accuracy against a human. (HANDOFF §4, §7.1)
- The classical court fallback reports "4.48px reprojection" by measuring against
  its own fitted points — and was visually wrong anyway. (HANDOFF §4,
  TilAFMPc0yg false-fit)
- "87.4% ball coverage" counts tracker locks (including bg-bridge guesses) as the
  denominator — it measures how often the tracker fired, not how often it was
  right. (HANDOFF §7.4)

Rules:

1. Before improving any model, ask: what independent ground truth am I scoring
   against? If the answer is "the model's own outputs" or "its teacher's
   outputs," you are not measuring accuracy — say so in plain words.
2. When reporting any number, state in one sentence what it was measured against.
   "84.7% agreement with pseudo-labels on held-out frames" is honest. "84.7%
   accuracy" is a lie. Never drop the qualifier.
3. The first real benchmark on this project is the human-clicked gold-label set.
   Until a model is scored against that, its numbers are provisional — label them
   provisional.

## Honesty rules for reporting results

The person cannot check your work, so these are load-bearing:

- Tag every claim MEASURED / VISUAL / INFERRED / UNKNOWN, exactly like docs/archive/HANDOFF.md
  does. A number with no evidence tag is not trustworthy.
- "It should work" is not a result. Run it, show the actual output. (This is also
  CLAUDE.md's verify-don't-claim rule — it applies doubly to training, where
  things silently half-work.)
- Never quote a training-log number from memory or from a previous session's
  summary. Session summaries drift under compaction (HANDOFF §7.8). Re-run or
  re-read the artifact before repeating a number.
- Report the denominator. "990 locks" means nothing without "out of 1108 frames,
  of which N were checked against truth."
- If a result is surprising or too good, treat it as a bug until proven
  otherwise. The 990-lock BallNet run looked like a win and was actually the
  model locking onto the adjacent court. (HANDOFF §6)
- Retract cleanly. When an earlier claim turns out false, say so plainly and
  point to the measurement that disproved it — the way HANDOFF §7.2 retracts
  "rescue caused the regression." A retracted wrong claim is good practice, not
  an embarrassment.

## Ground truth before metrics

You cannot improve what you cannot honestly measure. Order of operations is
always: build the exam first, then train.

- Build the human-labeled benchmark before retraining, not after. Retraining
  first means you can't tell whether the new model is better.
- Stratify the benchmark — don't sample frames randomly. Cover the cases that
  break: near court, far court, serves, blur, occlusion, and crucially frames
  where the answer is "nothing" (no ball in play, HUD graphics, adjacent court).
  Random sampling under-represents exactly the hard cases.
- "Negative" frames are the most valuable labels you'll collect. A model that's
  95% right when the ball is present but confidently hallucinates a ball during
  changeovers is a bad model, and only no-ball labels expose that.
- A small honest benchmark (200–300 human labels) beats a large self-graded one
  (23,000 pseudo-labels) for judging a model. Use the big set to train, the small
  honest set to grade.

### Ground truth describes the GAME, never the VIDEO

A source being *independent of us* does not make it *true*. A tennis video often
carries annotations **about** the game — a burned-in scoreboard, a SwingVision
HUD reporting shot speed and stroke type, a rendered graphic. Those are somebody
else's **data entry**, and they are barred as a training target, as a
ground-truth reference and as a tuning signal.

- **Self-consistency is not correctness.** A tool read the point-by-point boards
  on two clips and every one of 79 score transitions was legal tennis — which
  proves the scoreline is internally coherent, not that it matches the court. A
  diligently-kept *wrong* board passes that check perfectly. Built, rejected on
  its premise, reverted (`afffb5a`).
- **You inherit the other system's errors and lag.** Tuning a rally threshold
  against point-boundary timestamps calibrates against *when somebody pressed a
  button*. Fitting to a HUD's shot speed teaches you to reproduce that
  estimator's mistakes — it makes the other product a ceiling, not a target.
- **It does not generalise.** The footage this project targets — an amateur
  phone on a fence — has no scoreboard and no HUD. Anything leaning on one works
  only where the answer is already printed on the frame.
- **It leaks.** Five training clips carried a SwingVision overlay whose
  watermark is a literal yellow tennis ball; 83 pseudo-labels landed inside those
  graphics, teaching the detector that a logo is a ball. Now scrubbed and
  refused by `assert_no_swingvision_leak`.

**Compliant sources, all of which describe the court:** human clicks on the
ball/court, `tools/synth_truth.py` (simulated flights with known physics — the
only absolute accuracy figures this project has), and geometry derived from the
homography.

**Live exception to declare, not hide:** `tools/hud_ocr.py` reads SwingVision's
burned-in MPH panel, and several shipped speed numbers are measured against it.
Report those as **agreement with another estimator, not accuracy** — the other
system's error is inside every one of them. Prefer `synth_truth`.

## Data quality beats model cleverness

Most failures on this project were data failures wearing a model costume.

- Clean the training labels before touching the model architecture. BallNet v1's
  HUD-logo problem is a data problem: it was trained only on positive locks with
  no "this is not a ball" examples. No amount of tuning fixes a poisoned or
  one-sided dataset.
- Physics/geometry sanity filters are cheap ground truth. A real tennis ball is
  never stationary for 10 frames; a HUD logo always is. A ball follows a
  locally-parabolic path; a false lock jumps around. Use these to auto-discard
  bad labels before training. This costs a script, not human labeling time.
- Beware label poisoning. This project trained CourtNet v2 on 222/332 labels
  generated from a wrong calibration (the service line mistaken for the
  baseline). It never beat baseline and the root cause took real work to find.
  (HANDOFF §4.) Before mass-generating labels, verify the label generator on a
  few examples a human eyeballs.
- Never modify the original dataset in place. Cleaned or augmented data goes in a
  NEW directory. You must always be able to get back to the raw source.
- Report what you removed and why. "Filtered 23,558 → 19,800 labels; dropped
  3,758 static/isolated locks" — with a few example discarded frames as images so
  a human can confirm you didn't throw away real data.

## Hard negatives: teach the model what the answer is NOT

A detector trained only on positive examples learns "find the most X-like thing
in the frame" — even when there is no X. That's how BallNet ends up locking onto
a logo.

- Every detector needs negative examples with a "nothing here" target: frames
  with no ball, distractor graphics, the adjacent court, net posts.
- Mine negatives from known failure frames — the exact frames where the model
  already went wrong (this project has them saved in track_compare.jpg). Those
  are worth more than random negatives.
- Show a human ~10 example negatives before training on them, to confirm they're
  actually negatives and not mislabeled positives.

## Fine-tuning without destroying what worked

- Catastrophic forgetting is real and has already bitten this project. CourtNet
  v0 fine-tuned so hard it forgot everything and had to be withdrawn. (HANDOFF
  §4.) When fine-tuning, keep the learning rate low, and after training, re-check
  performance on the ORIGINAL data the base model was good at — not just the new
  data. A model that improved on the new angle but broke the old one is a
  regression, not a win.
- Always save a new weights file. `ballnet_v2.pt`, never overwrite `ballnet.pt`.
  Keep the "not ready" experiments too, clearly named
  (`courtnet_ft_v0_notready.pt` is the right pattern). Weights are cheap; a lost
  working model is expensive.
- Keep a one-line note per weights file: what data it was trained on, what it
  scored against the gold benchmark, and whether it's adopted or shelved.

## Generalization vs memorizing the training set

- Test on angles/conditions the model has never seen. CourtNet v3 scores well and
  is genuinely verified — but ONLY on its 3 training angles, and fails on unseen
  ones. (HANDOFF §4.) A model that only works on its training data is a lookup
  table, not a learned model. State clearly which case you're in.
- If a model can't generalize from N examples, more fine-tuning on those same N
  examples won't fix it. The honest options are: get more varied data (e.g.
  synthetic data for a known geometric object like a court), or accept the narrow
  scope and add an independent guardrail that catches the failures.
- An independent self-check gate is worth more than a better model. The
  "white-paint check" idea — sample actual pixel brightness along where you think
  the court lines are, and reject the fit if the paint isn't there — is the first
  grader in this whole project that doesn't trust the model's own math. Build
  guardrails like that; they catch confident-but-wrong outputs.

## Reproducibility: a result you can't reproduce isn't a result

The project's single most expensive open problem is a ball-track cache that
current code cannot reproduce because nobody recorded how it was built. (HANDOFF
§6.) Don't create more of these.

- Stamp every artifact with how it was made: model name(s) + weight hashes,
  device (cpu/cuda), key parameters (hfov, gate thresholds), a hash of any
  calibration it depended on, and the git commit. A cache/output that outlives
  the settings it was built under will silently poison later work.
- Cache keys must include everything that changes the output. If a cache is keyed
  only on the video but the result also depends on the model, device, and
  calibration, the cache will hand back stale results after any of those change.
- CPU vs GPU can give different numbers. Argmax over a probability map can flip
  near-threshold decisions between devices. If a result must be reproducible, pin
  the device and note it.
- Version-control the code, and track which dataset + weights produced which
  result. Without git, "what changed?" is unanswerable — which is exactly the
  situation §6 describes.

## Tuning discipline: change one thing, measure, stop

- Establish a baseline number first. You can't tell if a change helped without
  the before number, measured against the honest benchmark.
- Change one thing at a time. New data AND new architecture AND new learning rate
  in one run means you learn nothing about which one mattered.
- Do NOT tune in a loop chasing a number. If a model isn't clearly better after a
  reasonable attempt, STOP and report plainly what you tried and what to try next
  — do not silently thrash through hyperparameters. (This is CLAUDE.md's
  3-attempts rule applied to training.) Chasing a metric with endless tweaks is
  how you overfit to the benchmark and fool yourself.
- A model that's not clearly better is a "no." Say so. "v2 did not beat v1 on the
  gold benchmark; here's what I'd change next" is a valid, honest session
  outcome. Shipping a marginal model because effort was spent is not.
- Commit working state before risky training. If a training run corrupts
  something, you roll back to the last commit — not to nothing.

## Keep the architecture boundaries intact

CLAUDE.md's contract: perception = ML; geometry = closed-form math; logic =
deterministic rules. ML best practice here includes not reaching for ML where
math or rules belong.

- Don't "ML-ify" geometry (court projection, homography) or logic (scoring, rally
  segmentation). Those have exact answers; a learned approximation is strictly
  worse and un-auditable.
- Ball detection and pose are perception — ML is right there. Serve height,
  bounce location, line calls are geometry/logic — solve them from first
  principles (e.g. gravity + a known frame rate), not by copying another
  product's output numbers. (HANDOFF §5, §8-R2.)

## The working summary — 11 rules, moved here from SCOREBOARD 2026-08-26

This is how work gets decided here, and it is the reason the numbers in
[docs/STATE.md](docs/STATE.md) can be trusted. It lived in SCOREBOARD.md until the
2026-08-26 split, which separated *state* (what is true now) from *discipline*
(how we decide). The sections above expand these; this is the checklist form.

1. **Score only against independent human labels.** 1851 human ball clicks and 308
   no-ball frames across 10 clips (the legacy six, 1201/204, is kept as a named subset
   so historical figures stay reproducible). Test-only, never trained on. A model never
   grades its own homework.
2. **Pre-register the gate before running the experiment.** Write the threshold down
   first, then measure. Do not move the gate to fit the result — Session G part 4 fails
   at 54.5% against a 60% gate and stays failed.
3. **Order the gates so the expensive one is checked first.** Recall before ghost-ball.
   In Session F the ghost-ball gate would have *passed* at threshold 0.6; only the
   recall gate, deliberately ordered first, caught it.
4. **Diagnose before adjusting.** Per-gate miss counters, not just success counts. That
   is what showed far-court was detector-shaped rather than gate-shaped.
5. **State what every number was measured against, in one sentence.** Every eval tool
   emits a `measured_against` field.
6. **A refactor must prove it changed nothing.** Re-run and diff, or pin with a test.
7. **Record negatives with their reason.** A dead end nobody wrote down gets
   re-proposed.
8. **Look at the errors, at the right zoom, before theorising about them.**
   `tools/false_fire_viewer.py` renders every false lock as a clickable context tile
   with a matching zoom, because the two questions need opposite crops: *what object is
   this attached to* needs 140 px of context, *is this literally a tennis ball* needs
   44 px blown up. Judging either from the wrong one produces confident nonsense — see
   Trap T18.
9. **And look at them MOVING.** `tools/false_fire_reel.py` renders ±0.5 s around each
   false fire with the detector run continuously and its lock drawn every frame. A still
   cannot separate a racquet head from a ball — both are ball-sized, ball-coloured blobs
   — and the thing that separates them is that one is on a short arc pinned to a person.
   Two sessions were spent proving the pipeline cannot make that call from geometry while
   the discriminator was motion, which no contact sheet shows. Annotation colour is
   **magenta on purpose**: the subject and every confuser are yellow-green, so a yellow
   marker hides inside the object it points at.
10. **A test set that PICKS a hyperparameter is a validation set wearing a test set's
    reputation, even if pre-registered.** External review (2026-08-16, P0-1): rule 1 says
    the gold set is never trained on, but `tools/tune_smoother.py` and
    `tools/tune_suppress.py` had both been sweeping `max_gap_s`, suppression segment
    thresholds, `score_thresh` and more directly against the same 1851 clicks that also
    produce every headline recall/false-fire number — over a dozen sweeps across six
    weeks. Pre-registering each individual gate (rule 2) limits cherry-picking within one
    sweep; it does not stop the cumulative drift of many sweeps against one fixed set.
    Two clips are now a permanent, ONE-WAY blind holdout (`tools/_goldset.py`'s
    `HOLDOUT`), structurally withdrawn from both tools' `--clip` choices — see the
    matching row below. They stay fully visible to `eval_gold.py` / `eval_detector_gold.py`
    / `eval_model_filters.py` for reporting; the rule is about what CHOSE a value, not
    about what gets measured.
11. **Truth comes from the GAME, not from the VIDEO.** The court, the ball, the
    players, the bounces, the physics — never a scoreboard, HUD or graphic somebody
    burned into the frame. Those are *data entry about* the game, and they are out of
    bounds as a training target, a ground-truth reference AND a tuning signal. This is
    the generalisation of three separate incidents here: the burned-in scoreboard built
    and rejected on its premise (`afffb5a`), the `~1.6x`/`1.47x` over-split figures
    withdrawn with it, and 83 pseudo-labels landing inside a SwingVision overlay whose
    watermark is a literal yellow tennis ball. Independence is not truth — a
    diligently-kept WRONG board is perfectly self-consistent; and nothing that leans on
    an overlay generalises to the user's own phone clip, which has neither. **Compliant
    references: human clicks, `tools/synth_truth.py`, and geometry we derive ourselves.**
    **THE ONE LIVE EXCEPTION, stated rather than buried:** `tools/hud_ocr.py` reads
    SwingVision's burned-in MPH panel, and the speed figures in this file that cite a
    "HUD MAE" or "HUD speed error" (the `--full-rate` row, the frame-rate row,
    `speed_err_pct`) are measured against it. Those are **agreement with another
    estimator, not accuracy** — SwingVision's own error is inside every one of them, so
    they bound how well we MATCH SwingVision, not how right we are. `synth_truth` is the
    compliant speed reference and is the one that produced this project's only absolute
    accuracy figures. Do not add new HUD-referenced numbers; re-reference the existing
    ones to `synth_truth` when they next matter.

---

## Session-end checklist for any ML work

Before ending a session that trained, tuned, or evaluated a model:

- [ ] Every reported number states what it was measured against, tagged
      MEASURED/VISUAL/INFERRED/UNKNOWN.
- [ ] New model scored against the human/gold benchmark, not pseudo-labels.
- [ ] New weights saved to a new filename; original weights untouched.
- [ ] Cleaned/augmented data in a new directory; raw data untouched.
- [ ] New artifacts carry provenance stamps (model, device, params, commit).
- [ ] A plain-English verdict: did it get better, yes/no, on what evidence.
- [ ] Any earlier claim proven false this session is explicitly retracted.
- [ ] CLAUDE.md current-state and docs/archive/HANDOFF.md updated; committed to git.
