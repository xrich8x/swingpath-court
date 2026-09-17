# The gravity-arc calibration pilot — pre-registered design, before any run

> Ranked #2 in `docs/evidence/independent-calibration-references.md`, behind the net-post
> detector. This file designs the pilot that ranking called for and prices it against the
> one instrument in this project that has actually worked (the net tape,
> `docs/evidence/net-tape-camera-height-consistency.md`, AGREE 13/15,
> **3.2%/px at 720p**). Nothing here is run. **This document is a research design, not
> code** — backend-dev or qa would build/run it if the RUN recommendation is taken.

## The one number that decides it, stated first

**A single amateur-mount arc's apparent-`g` fit has an estimated random precision of
roughly ±15–25% of `g` from pixel noise alone** (derived below, not measured — see the
caveat in §2), before drag/spin bias is added on top. **The net tape's bar is 10%, and it
is met.** A candidate that cannot beat an already-working instrument's bar, on its own
best-case arithmetic, before its known systematic confounds are even added, does not
justify a build. **Recommendation: DO NOT fund a build. A narrow, cheap, fully-simulated
pilot (§5, no real footage, no new labels) is worth running ONLY to settle the open
science question — not as a step toward shipping this as a calibration check.**

---

## 1. What exactly is measured, and from what

**The claim being tested:** fit a ballistic trajectory to an observed 2-D pixel arc,
holding `g = 9.81 m/s²` fixed as a known constant and real elapsed time (from the video's
own fps) fixed as a known axis, and treat the camera's assumed metric **scale** as the
unknown being solved for. If the reprojection is best at a scale `k ≠ 1` relative to the
existing calibration, that calibration's implied camera height (or hfov) is wrong by
(something related to) `k`.

**This is not what exists in the repo today, and that gap is itself a finding.** The
actual arc-fitting code, read for this brief:

- `ball_physics/tennis_tracker/estimation/trajectory_fit.py::fit_arc` — least-squares
  (`scipy.optimize.least_squares`, Levenberg-ish `trf`) over a **forward physics
  simulation** (`ball_physics/tennis_tracker/physics/simulate`, drag + Magnus lift
  included, RK4 integration) that solves for **launch state** `(p0, v0, omega)` given a
  **fixed camera** (`Camera.project`) and **fixed `g = 9.81`**
  (`ball_physics/tennis_tracker/physics/constants.py:24`, hardcoded, not a parameter
  anywhere in the call chain). `rmse` is reprojection error in **pixels** when fit to a 2-D
  track — this is the `reproj_px` quantity already cited in this project's own history
  (`docs/evidence/60-fps-shipped-as-full-rate.md`: "arc reproj 148 → 91 px").
- `ball_physics/tennis_tracker/bridge.py` supplies the calibrated `Camera` from the same
  4 doubles-corner clicks the court calibration already uses
  (`camera_from_court_corners`), plus Kalman smoothing, bounce detection and arc
  segmentation on the raw ball track before the fit runs.
- `tools/synth_truth.py` is the compliant **absolute** reference (rule 11-clean: no HUD,
  no scoreboard, a physics simulator + the real per-clip calibration + real detector
  noise/dropout). It already reports a three-term error budget — `drag_pct` (launch →
  true average 3-D speed, median **−21.7%**), `ground_proj_pct` (3-D → ground, geometry),
  `our_pct` (ground → estimate, the only term that is genuinely "our error") — but for
  **average speed**, not for fitted vertical acceleration. It is the right harness to
  extend for this pilot (§5), not a source of a ready-made `g` number: **no run of
  `synth_truth.py` or any other tool has ever fitted for `g` or for scale here.** That is
  the first thing any pilot would produce, not something already sitting in this repo.

**To build the check as described, the fit direction has to invert**: fix `g = 9.81`,
add a scale unknown `k` (equivalently, perturb the assumed camera height / hfov), and
solve for `(k, p0, v0, omega)` jointly against the 2-D pixel track. **This is new code,
not a config flag on `fit_arc`** — worth stating plainly since the brief's framing ("the
chain already exists") is only half true: the physics engine, the smoother, the bounce
detector and the compliant truth generator exist; the inverted fit itself does not.

## 2. The error budget, in the units that matter — and why it likely loses to the tape

**No version of this has been built, so every number below is a first-principles
estimate, explicitly flagged as such, not a measurement.** It is offered because the
brief asks whether the candidate can beat a stated bar, and refusing to estimate at all
would forfeit the one question this document exists to answer.

**Mechanism, derived from the actual acceleration model in `aerodynamics.py` and
`constants.py`:** for a *pure, isotropic scale error* (the whole reconstructed 3-D
scene, camera height included, wrong by a constant factor `k` about the camera centre —
the classical single-camera scale ambiguity), reconstructed positions are `k×` the true
ones at every instant, so reconstructed vertical acceleration is exactly `k×` the true
one: **`g_apparent = k · g_true`**, confirming the brief's premise for that specific
error class. **This project's own measured calibration failures are not that class.**
The `yt_match40` compression (`docs/STATE.md`, T23) squeezed the court onto its near
half — an anisotropic depth-vs-height distortion coming from a jointly-fit,
under-constrained `hfov` (`backend/swingvision/calibration.py`, `hfov_deg` is an assumed
input to the 4-corner pose recovery, default 70°, not measured), not a single scalar `k`.
**So even a perfectly clean apparent-`g` measurement resolves only one degree of freedom
of a calibration error that, on this project's own evidence, is not one-dimensional** —
the same limitation the net-tape write-up already stated about its own instrument
("cannot arbitrate a calibration on its own — two unknowns, one observation").

**Precision, from curvature estimation on a short window (the honest limiting factor).**
A quadratic fit `z(t) = z0 + v0 t − ½g t²` to `N` noisy points spanning duration `T` has
standard error on the fitted `g` growing as `~1/T²`, not `~1/√N` — the **time window
matters far more than frame count**, which matters because a **low mount caps the window
directly**: `docs/STATE.md`'s own measured mounts (1.38 m, 1.74 m) limit *measurable
depth* to 22–32% of the court (5.2 m / 7.5 m of 23.77 m). At a typical rally-shot
horizontal speed of 15–20 m/s, that band is crossed in **~0.26–0.5 s**, i.e. 8–15 frames
at 30 fps, **before the ball leaves the region this project can even trust geometrically
at all** (the same T22 low-`z` regime `synth_truth.py` already restricts its "low-ball"
comparison to). Plugging in a per-point vertical pixel-noise estimate of **4–8 cm** at
15–20 m depth on a 720p wide-FOV amateur phone lens (2 px centroid noise —
`synth_truth.py`'s own default — converted through a rough px→m scale at that depth and
that `hfov`), a standard quadratic-regression variance formula for `N≈12` points over
`T≈0.4 s` gives **SE(g) of order 2 m/s², i.e. ~20% of g, from pixel noise alone, on a
single arc, before any systematic term.**

**That number, ~20%, already exceeds the net tape's ~10% bar** (net tape sensitivity:
**3.2%/px at 720p**, i.e. the tape's whole bar is ~3 px of measured row —
`net-tape-camera-height-consistency.md`). It would need averaging over roughly `(20/10)²
≈ 4` **independent, well-conditioned** arcs just to match the tape's random-noise floor,
before the systematic terms in §3 are considered at all — and those terms, unlike the
tape's, are shot-dependent and do not obviously average toward zero across arcs of a
similar type (a match's groundstrokes share similar pace and spin, the way the tape's
courts share a similar net rather than each being an independent random draw).

**This derivation is a hand estimate, not a run — flagged as the single cheapest thing
that would move this number**: a real Monte Carlo through `synth_truth.py`'s own
simulator (§5) replaces the ~20% guess with a measured one in under an hour of compute
and no new code beyond a scale-unknown flag.

## 3. The three warning signs, each answered

**Does drag bias the fit in a way that masquerades as a scale error? Yes, mechanistically,
not just by analogy.** From `aerodynamics.py`'s own model, the vertical acceleration is
`a_z = −g − (drag term)·v_z·|v| + (lift term)`. Drag opposes the *total* velocity vector,
so while the ball **rises** (`v_z > 0`) drag adds an extra downward deceleration
(apparent `g` reads **high**), and while it **falls** (`v_z < 0`) drag's vertical
component points upward, partially arresting the fall (apparent `g` reads **low**). A
fit over an asymmetric window (most amateur clips see more of the descending half of a
groundstroke than the rising half, because contact height sits well above the far
baseline's visible horizon on a low mount) will read a **shot- and window-dependent
biased `g`**, not the physical constant — and that bias is **the same sign and rough
magnitude class as a scale error**, so a least-squares fit with both `k` and the launch
state free has every incentive to trade one against the other rather than report either
honestly. This is a stronger, mechanistic version of the same warning the tape's own
write-up flagged for net sag (a real, physical, non-calibration nuisance parameter that
looks exactly like the thing being measured) — except the tape's nuisance term is a
fixed few percent per court, and this one is a live free parameter inside the same
optimisation the calibration check is supposed to be reading.

**Can a `z = 0` assumption on an airborne ball corrupt it? Only if the pilot uses the
wrong existing code path — and this is fixable by construction, not a new risk.** T22
measured that flat-plane back-projection of an airborne ball is wrong by **+72% median,
p90 +25,000%** near a grazing ray. `fit_arc`/`bridge.py`'s physics-fit path **already**
carries the ball in full 3-D (`Camera.project` of a simulated 3-D trajectory, never a
`z=0` homography lookup) — it is the `approx`/flat-projection speed path in the *live*
pipeline that has the T22 problem, not this one. **The one discipline this pilot must
hold itself to: build on `bridge.py`'s physics-fit path, never on the flat `image_to_court`
path**, and say so explicitly in any implementation brief so a builder does not reach for
the faster, wrong tool.

**Given `reproj_px` cannot certify an arc (a 23.8× span of candidate arcs all pass the
same reprojection screen — `arc-fit-observability` finding, cited via
`.claude/agent-memory/researcher/open-questions.md`; the primary evidence file could not
be re-located this session under the same T25 search failure noted last session, so this
is carried at the memory-index level of detail, not re-verified against its own numbers),
what *would* certify one?** Not a tighter residual bar — that is the same instrument
that already failed. Two things structurally different from `reproj_px`, both already
proven to work in this project's OTHER off-plane check:
1. **Repeatability across many arcs on the same camera**, the way the tape's four
   same-camera pairs (`net-tape-camera-height-consistency.md`) separated real signal
   from noise — not one arc's residual, but the *spread* of apparent-`g` across a
   whole match's worth of groundstrokes on one fixed calibration. A wrong calibration
   should read a consistent, repeatable bias across many shots; noise should not.
2. **Validation against known-truth simulated arcs first** (§5) — the same discipline
   `synth_truth.py` already applies to speed, extended to `g`/scale, so the pilot's own
   recoverability is established before any real clip's answer is trusted. This is the
   only way to avoid the model grading its own homework here: the fit's "goodness" cannot
   be judged by its own residual, per the reproj_px finding, so it must be judged against
   an independent, exactly-known input instead.

## 4. Confounds

- **Spin (Magnus).** Topspin curves the ball down faster (mimics a *larger* apparent
  `g`); backspin/slice curves it up (mimics *smaller*). `aerodynamics.py`'s `LiftModel`
  already models this in the forward simulation, but the **inverse** fit has to solve
  for `omega` simultaneously with `k` — and `trajectory_fit.py`'s own docstring already
  flags spin as **"the softest parameter in the model"**, prone to pinning at its bound
  on a short arc for a cheap residual gain. A free spin term gives the optimiser a THIRD
  way (alongside `k` and the drag-window asymmetry above) to trade away the very signal
  the pilot wants to read.
- **Wind, outdoors.** Not modelled at all — `constants.py` has no wind term. Every
  outdoor clip (all but the indoor Shell subset) carries an unbounded, uncharacterised
  extra force on the vertical (and horizontal) acceleration that this pilot has no way
  to separate from a scale error. This is a confound with no existing mitigation in the
  repo, unlike drag and spin, which at least have a forward model to be inverted.
- **fps timing error.** The one axis that is genuinely NOT the bottleneck: video frame
  timestamps are precise to a small fraction of a frame interval on modern phone
  encoders, several orders of magnitude tighter than the pixel-noise term in §2. Not
  worth budgeting further here.
- **The degenerate pair, stated precisely.** A single monocular camera plus 4
  known-real-world-size coplanar corners does **not**, in general, leave scale free —
  the corners' real coordinates (23.77 × 8.23 m, hardcoded) already pin the metric scale
  *if the clicks are at the true corners*. The actual failure mode this project has
  measured (`yt_match40`) is a **general homography/hfov misfit**, not a missing-scale
  problem, so "wrong court scale, wrong apparent `g`" is the right intuition only for the
  narrow sub-class of errors that behave like a pure isotropic rescaling. For the
  anisotropic class this project's own gold set actually contains, an apparent-`g`
  reading off by `x%` constrains one scalar and **cannot say which corner, or which
  axis, is wrong** — precisely the "two unknowns, one observation" ceiling the tape
  write-up already stated honestly about itself, inherited here in a harder form because
  the ball arc has *more* free parameters (`v0`, `p0`, `omega`) than the tape's single
  assumed height.
- **On-device only, a genuinely different risk profile.** `hfov_deg` is a *guessed*
  input in the desktop calibration path used to produce this project's gold clips
  (`calibration.py`, default 70°). On an iPhone, per CLAUDE.md, the true horizontal FOV
  is a **known camera intrinsic from `AVCaptureDevice`**, not fit. If the shipped
  product uses the real intrinsic rather than guessing it, the specific hfov/scale
  ambiguity this pilot is aimed at is **smaller in the shipped product than in this
  project's own historical gold set** — worth stating so a pilot run on old desktop gold
  clips is not over-read as representative of the phone product's actual exposure.

## 5. The pre-registered bar for the pilot

**Scope: simulation only. No real footage, no new human labels, no code beyond a scale
unknown added to the existing simulate/fit machinery.** This is deliberately narrower
than "build the detector" — it answers the recoverability question this whole file
turns on, at near-zero cost, before any real-clip claim is made.

- **Tool:** extend `tools/synth_truth.py` (or a sibling script reusing its `simulate`/
  `measure` machinery) to (a) draw launches exactly as it does now, (b) apply a KNOWN,
  injected scale error `k ∈ {0.85, 0.90, 0.95, 1.00, 1.05, 1.10, 1.15}` to the camera used
  for projection only (truth stays at the real scale), (c) fit `(k̂, p0, v0, omega)`
  jointly against the resulting noisy 2-D pixel track using drag+lift physics held fixed
  at their forward-model defaults, `g` fixed at 9.81.
- **Clips:** the 2 clips with real per-clip calibrations and known camera height already
  used throughout this project's own gold work — one low mount (`am_hard_utr`, 1.74 m)
  and one lower (`demo30`, 1.38 m) — plus one better-mounted comparison clip if any 4K
  clip (`hillsborough_p02`/`p08`, ~1.6 m but reaches further depth) is available, to see
  whether mount height changes the answer in the direction §2 predicts.
- **n:** at least 200 simulated arcs per `(clip, k)` cell — matching `synth_truth.py`'s
  own existing default `n=400` order of magnitude, cheap because it is pure simulation.
- **PASS bar (recoverability, not accuracy):** median `|k̂ − k|/k ≤ 10%` (the tape's own
  bar, so the two are compared on the same footing) **on the low-mount clips**, at both
  30 and 60 fps, under the SAME pixel-noise/dropout defaults `synth_truth.py` already
  uses (2 px, 30% dropout) — no loosening of the noise model to make the pilot pass.
- **KILL CONDITION, stated before any run:** **if the median recovered `|k̂ − k|/k` on
  the low-mount clips exceeds 20% at k=1.00 (i.e. even the null/no-error case reads a
  false scale error bigger than the net tape's whole bar), or if `k̂` is not monotonic in
  the injected `k` across the swept range (evidence of the drag/spin/scale degeneracy in
  §3 actively absorbing the signal rather than merely adding noise to it) — the idea is
  dead, not just underpowered, and no real-footage follow-up is warranted.** A
  non-monotonic response is the sharper kill: it means the fit cannot even rank two
  different real scale errors correctly, which no amount of additional real data fixes.
- **What would make this worth funding further:** median recovery error **at or below
  the tape's 10%** on the low-mount clips, monotonic in `k`, AND separated by a
  shuffled/permutation null exactly as this project's other gates now require (rule:
  never report a gate without its null control) — a null built by fitting the SAME
  machinery to arcs with `k` shuffled across clips, to rule out any accidental
  correlation between clip identity and recovered scale.
- **Cost:** simulation-only, no GPU beyond what `synth_truth.py` already uses (CPU-viable,
  a few hundred short optimisations), no new human labelling, no real video required at
  all beyond the 2–3 existing calibrated gold clips already committed. Estimated at
  under an hour of compute and a half-day of implementation for whoever builds it — cheap
  enough that its only real cost is the half-day, not GPU time or ground truth.

## 6. On-device

**No new ANE inference of any kind.** The entire mechanism — forward RK4 physics
simulation and the inverse least-squares fit — is closed-form numerical optimisation on
an already-existing 2-D pixel track (itself produced by the ball detector, which already
runs on-device per the shipped stack). `scipy.optimize.least_squares` itself is a desktop
dependency and would need a from-scratch port (Gauss-Newton/Levenberg-Marquardt is
straightforward hand-rolled numerics, not a model), but the **cost class is
Accelerate/vDSP arithmetic, the same class as the net tape's 1-D matched filter and the
homography fit itself** — not a Core ML graph, not a quantisation question, not subject
to the ANE thermal-sustain concerns that bind pose/ball detector inference. If this were
ever built into the shipped product (not recommended by this pilot design), its
feasibility on an A13 is not in question; its **accuracy** is the entire open question,
and that is what §2–5 are about.

---

## RUN / DO-NOT-RUN

**DO NOT fund a build of this as a shipping calibration check.** Its theoretical appeal
(a physical constant plus fps-timed real seconds, immune to the ground-plane symmetry
that killed four other gates) is real, but this project's own physics model, read
directly for this brief, shows the practical case losing to the already-working net tape
on the one number that matters: **an estimated single-arc precision of ~20% against the
tape's proven 10%, with drag and spin able to actively cancel the signal being measured,
and the anisotropic nature of this project's own measured calibration failures meaning
even a perfect apparent-`g` reading resolves only one of the several degrees of freedom
actually wrong.**

**RUN the narrow simulation-only pilot in §5** if the founder wants the underlying
science question settled rather than assumed — it is cheap (half a day, no GPU, no new
labels, no real footage) and its kill condition is sharp: a non-monotonic or >20%-at-k=1
response ends the idea outright, and a clean pass would be the first real evidence, not
another hand estimate, that the candidate belongs above people-as-scale in the earlier
ranking rather than below it.

**The one number that decides it:** **the tape's 10% bar vs. this pilot's estimated ~20%
single-arc precision.** If the §5 simulation instead measures the recoverable precision
at ≤10% and monotonic, this recommendation reverses; nothing else in this document would
need to change to accommodate that.

---

## For the PM: the tradeoff, stated plainly

Building the gravity-arc check now costs a half-day of new code (the inverted fit does
not exist) plus the risk that its own three known failure modes (drag/spin degeneracy,
multi-DOF calibration errors reduced to one scalar, and reprojection's proven inability
to certify an arc) make it a second, more expensive way to arrive at the same "one more
number for a human to look at" role the net-post detector already fills more cheaply and
with a cleaner error model (no drag, no spin, a rigid known height). The founder gets to
decide whether the underlying physics question — can a phone recover its own calibration
scale from a ball's flight — is worth a half-day simulation-only answer even though the
product case for it is currently weak. Decision left open.

## NOT ESTABLISHED THIS RUN

- **The ~20% single-arc precision figure is a hand derivation, not a measurement.** §5's
  pilot is the cheapest way to replace it with a real number; it was not run here.
- **The exact evidence file behind "reproj_px cannot certify an arc, 23.8× span" could
  not be re-located this session** (same T25 search-tool failure flagged in the prior
  session's journal) — carried at the agent-memory index's level of detail, not
  re-verified against its own primary numbers. If this matters to the founder's decision,
  it is a `qa` task to locate and re-confirm the file, not a re-derivation.
- **Whether wind is a material confound outdoors, quantitatively.** Flagged as
  unmodelled and uncharacterised in §4; no attempt was made to bound its size here.
- **Whether the on-device hfov advantage (§4, known intrinsic vs guessed) meaningfully
  changes the error budget for the SHIPPED product** relative to this project's desktop
  gold clips — noted as a real asymmetry, not sized.
