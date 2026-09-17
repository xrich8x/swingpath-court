# What else can validate a court calibration, given that coverage, camera-height, and the net-anchor bars have all failed as GATES

> Context this assumes read: `docs/evidence/verify-court-false-rejects.md`,
> `docs/evidence/net-tape-camera-height-consistency.md`,
> `docs/evidence/net-anchor-calibration-check.md`, trap **T23**, and the "Court
> auto-detection is CLOSED for v1" row in `docs/STATE.md`. Not reproduced here.

## The one finding that organises everything below

**Every check that has failed so far uses only the GROUND PLANE** (`z = 0`): the four
corners, the projected lines, the coverage/centrality statistics, the camera-height
fit computed from those same corners. **The one check that worked — the net tape —
is the only one that uses a point OFF the ground plane** (`z = 0.914` m).

That is not a coincidence, and it is checkable from the geometry already in this repo.
A regulation tennis court's line pattern is symmetric under two operations that respect
`z = 0`: reflection left-right, and (ignoring the net) a depth rescaling that keeps the
same aspect. **The failure that fooled every ground-plane check in this project's own
corpus — the `yt_match40` re-click that compressed the whole court onto its near
half — is exactly this class of error**: residual 0.0 px, camera height a plausible
1.64 m, `verify_court` coverage 0.944 (higher than most correct courts), horizon row
sane. Every one of those statistics is a function of the four ground-plane corners, and
the compressed quad is *also* four corners forming a plausible trapezoid — so nothing
that only reads the ground plane can distinguish them BY CONSTRUCTION, not by tuning.
**Only the net tape caught it**, because a point at real height `h` above the ground
images at a row that depends on `(H − h)/H`, and no relabelling of the four ground
corners can spoof that ratio for a feature it never touched.

**This is the filter I ranked every candidate through**: does it carry information
off the `z = 0` plane (or otherwise outside the symmetry the court's own paint
possesses), or does it just re-read the same four corners in different clothing?

---

## Ranked candidates

### 1. Net posts at 1.07 m — BUILD THIS NEXT. Off-plane, rigid, cheap, framing-limited.

**What it measures.** The same off-plane geometry as the net tape (`row = horizon +
(ground_row − horizon)·(H−h)/H`, `h = 1.07` at the post) but at a **rigid** structure —
a post does not sag, is not affected by stringing tension, and gives **two**
measurements per post (base on the ground plane, top at 1.07 m), so post-vs-tape
agreement separates the tape's own confound (net sag / non-regulation height) from a
calibration error, which the tape alone cannot do.

**What detecting it requires.** A vertical, high-contrast, roughly-column-fixed segment
at the predicted x (`X_LEFT_POST = −0.914`, `X_RIGHT_POST = 11.884` in `court.py`,
already defined and already projected by `net_anchor_check.net_post_segments_3d()`).
Mechanically the same kind of 1-D matched-filter sweep already built for the tape
(`tools/net_tape_height.py`), rotated 90°: search a small column band around the
predicted post x for a bright-or-dark vertical edge pair (post against sky/fence vs.
post against court), refuse on low contrast or an ambiguous rival peak exactly as the
tape does. No new ML model — classical signal processing, same family as the shipped
tool.

**Error budget.** `dH/drow` at `h = 1.07` is smaller by the ratio `0.914/1.07 = 0.85×`
than the tape's own sensitivity, so a bit MORE precise per pixel of row error, same
order: **roughly 2–5 px of measured row = 10% of camera height**, matching the tape's
measured 1.8–14 px range depending on resolution (`net-tape-camera-height-consistency.md`
§"What the 10% bar is worth in pixels"). Two independent rows (base, top) per post,
two posts per frame where visible — up to 4 measurements, which is exactly the kind of
redundancy that would let a founder rule out both drow-outliers seen in the tape run
(`demo30`, `L73ep7JHiJ4`) with a same-frame cross-check instead of a second clip.

**Confounds.** Structurally cleaner than the tape (no sag), but the post itself can be
thin (a few px wide at typical amateur framing), can be occluded by a player or the net
itself, and its base can sit in shadow or against a fence of similar tone — the same
"is this a bright band against both neighbours" problem the tape already solves, just
oriented differently.

**Low amateur mount?** This is the open risk, and it is not measured, only observed
qualitatively: `net-anchor-calibration-check.md` §6 already states **"posts are
frequently off-frame on the low wide mounts this project targets."** A camera set back
to capture the full 10.97 m doubles width from a low, close mount has to use enough
horizontal FOV that the posts — 0.914 m *outside* the doubles sideline, i.e. 12.8 m of
total width — are the first thing cropped. **No fraction is quoted here because none
has been measured**; the 27 already-rendered `*_netanchor.png` files could answer this
for the cost of a look, not a build (see the falsifier below).

**On-device, iPhone A13, Core ML?** Yes, trivially — it is a 1-D brightness sweep over
a few dozen columns and rows, the same cost class as the tape check, no network
inference at all. This is Accelerate/vDSP work, not ANE work.

**Rule 11.** Compliant — the post is a physical fixture of the court (part of the game),
never a HUD element, and it is never one of the four clicked points.

---

### 2. Ball physics / gravity arc — theoretically the SHARPEST reference, practically the riskiest.

**What it measures.** `g = 9.81 m/s²` is not a game-object assumption, a labelling
convention, or a manufacturing tolerance the way "the net is at regulation height" is —
it is a physical constant, and real time (from the video's own fps) is an independent,
non-rescalable axis alongside it. That combination is a genuinely different kind of
anchor: a pure scale ambiguity in a single perspective camera is otherwise invisible
(scaling the whole 3D scene — camera height and all real distances — by a constant
leaves every image unchanged), but a ballistic drop under gravity, timed in real
seconds, is NOT rescalable that way. In principle, fitting the camera's metric scale
so that a ball's fitted vertical acceleration reads `9.81 m/s²` is a legitimate,
non-circular calibration constraint — the same family of technique the literature uses
for recovering metric scale from human motion under gravity (e.g. "Humans as
Checkerboards," arXiv:2407.00574, which calibrates *camera motion scale* from body
height + gravity in mocap — different domain, same principle) and from single-camera
ballistic-trajectory reconstruction in volleyball/basketball (Springer
978-3-319-24560-7_5; ResearchGate 251310870) — **all of which are broadcast or
lab multi-frame-rate setups, not a single fixed amateur phone, and none of them is a
tennis-specific or amateur-footage number — do not import a figure from them.**

**Why this project should treat it with real suspicion before funding it.** Three
things already measured here point the same direction:
- **Trap T22**: naively projecting an airborne ball onto the court's `z=0` plane is
  already known to be badly wrong (+72% median bias, near-infinite near a grazing ray).
  Any gravity check has to solve the SAME 3-D reconstruction problem it would be
  validating, not sidestep it.
- **This project's own arc-fit work already found a residual-based certification of an
  arc fit to be uninformative** — `arc-fit-observability.md` (agent-memory pointer):
  `reproj_px` cannot certify an arc; a 23.8× span of candidate arcs all pass the
  reprojection-residual screen. That is the T23 lesson (a residual is not a verdict)
  recurring in the ball-physics domain, and it is the single cheapest reason to expect
  a naive "does the fitted g match 9.81" check to be similarly non-discriminative
  unless built far more carefully than a residual bar.
- **Drag is already measured to bias average-vs-launch speed by −21.7%** (`synth_truth.py`,
  cited throughout `docs/STATE.md`). A real tennis ball's flight is NOT a pure ballistic
  parabola — drag flattens the apparent vertical acceleration in a shot-dependent way
  (spin, pace, air density), so "apparent g ≠ 9.81" would fire on **every correctly
  calibrated shot**, for a reason that has nothing to do with the calibration. This is a
  worse version of the net tape's sag confound: the tape's confound is a few percent and
  roughly rigid per court; drag's effect on apparent vertical acceleration is shot- and
  spin-dependent and has not been characterised at the per-flight level here at all.

**Error budget.** Cannot be stated — no version of this has been built or measured in
this repo, and the honest answer is that pinning one down is itself the first
experiment, not a number I can quote.

**Feasibility on-device.** The math is closed-form least-squares (fit unknowns: scale
factor, launch position, launch velocity, against known g and known real Δt per frame)
— cheap, no ML, no network. The **bottleneck is data, not compute**: it needs several
frames of a clean, unoccluded, low-motion-blur ball mid-flight, and `docs/STATE.md`
already documents that this project's chain has "9 solid ghost balls" and detector
dropout in exactly the frames (fast motion, far court) most useful for a clean parabola.

**Rule 11.** Compliant in principle (physics derived, no HUD).

**Verdict:** worth a narrow, pre-registered pilot (see below) — NOT worth building
into the pipeline yet. The theoretical case is the strongest of any candidate here; the
practical case is the weakest, for reasons this project has already paid for once
(T22, the arc-observability finding) and would very plausibly pay for again (drag).

---

### 3. People as a scale reference — works, but its error budget is wider than the tape's, and it stacks a NEW unknown on top of the same old one.

**What it measures.** A standing player's image height, at a court position whose
depth is known (e.g. feet on a line), constrains camera height the same way the net
tape does — but the object's real height is now a **population** quantity, not a
regulation constant.

**Error budget, computed against what this project actually has:**
- **Population variance in adult standing height is real and not small**: ~7 cm SD
  within one sex, more once sex is unknown, i.e. a **4–5%** nuisance term on `h` before
  any pixel error is even considered — an order of magnitude worse than the tape's
  regulation-exact `h = 0.914` m.
- **Pose keypoints do not reach the true extremes.** YOLO-pose's nose/eye keypoints sit
  well below the true crown of the head (commonly cited ~10–14 cm gap in pose literature
  for "head-top" proxies), and ankle keypoints sit above the sole/shoe by a few cm. Both
  biases point the same way — pixel height reads too SHORT — and neither is
  characterised on this project's own model.
- **Posture confounds the "known real position" premise.** A split-step, a bent-knee
  return stance, or a mid-swing lean all shorten the apparent standing height at exactly
  the moments the player is easiest to see clearly (in the middle of a point, not idly
  standing). A frame where the player is genuinely upright and their feet are at a
  known court position (e.g. about to serve, both feet behind the baseline) has to be
  selected, and nothing here selects it.
- **Net effect:** stacking a ~4–5% population term with keypoint bias and posture noise
  plausibly lands in the **10–20% single-frame** range — worse than the tape's own
  ~3–10% (`net-tape-camera-height-consistency.md`), and unlike the tape's four
  same-camera pairs, there is no cheap repeatability check (every player is a different
  height).

**Confounds.** Same off-plane logic as the net (a person's head is off `z=0`, so this
DOES break the ground-plane symmetry problem described above) — but it trades the
tape's single, exactly-known nuisance parameter (net height, ± sag) for a much
noisier and less characterised one (human height, ± posture, ± keypoint bias).

**Low amateur mount?** Works better here than most candidates precisely because players
are close to camera on a low mount and their whole body is usually in frame — the
opposite framing problem to the posts.

**On-device?** Pose already runs on-device (YOLO-pose via Core ML per `docs/STATE.md`
"The stack"); the extra cost is arithmetic on keypoints already computed, near-zero
marginal cost.

**Rule 11.** Compliant — a player's body is the game, not a HUD.

**Verdict:** a real, buildable, on-device candidate, and worth having as a
**corroborating** signal averaged over many frames/players across a match (which would
average out the population term across different players, though not the pose-model
bias, which is systematic). Not worth building as a PRIMARY check ahead of the post
detector: it is strictly noisier per-observation and has no repeatability structure
analogous to the tape's same-camera pairs.

---

### 4. Other court markings (service lines, centre T, singles sidelines) — REJECTED as a new idea; it already exists and already failed under a different name.

`court.py`'s `LANDMARKS` dict already contains all 14 of these intersections (service
line × singles sideline, the two centre "T" points, both singles-baseline corners), and
`court.LINES` already draws all of them. **This is exactly what `verify_court`'s
coverage/centrality statistic already scores** — the fraction of *all* projected lines,
service lines included, that land on real white pixels. The finding in
`verify-court-false-rejects.md` (coverage orders clips by line VISIBILITY, not
correctness, and the grossly-wrong `yt_match40` passed at 0.436, above two correct
courts) is not a finding about the four corners specifically; it is a finding about
scoring *any* set of projected court lines against a white-pixel mask, and every
service line, sideline and T-mark is already inside that scored set.

The sharper version of this idea — match specific JUNCTIONS (corner detector at each
predicted intersection) rather than an aggregate coverage fraction — is not new either:
it is **joint line-to-model correspondence**, built 2026-08-29 and killed
2026-09-04 (`docs/STATE.md`, "Least-squares over ALL matched line correspondences").
That work handed the solver the *correct* correspondence between every detected line
and its court-model counterpart and still reconstructed WORSE than the shipped 4-point
fit (19.8 vs 8.1 px), because the ~6.4 px line-detector-to-truth disagreement is
upstream of any fitting strategy.

**And there is a structural reason it cannot be otherwise, independent of both prior
findings**: every one of these markings sits on the `z = 0` plane, and a regulation
court's marking pattern is symmetric near/far and left/right (the net excepted). The
`yt_match40` near-half compression that fooled coverage would fool a junction-matching
check for the identical reason — the compressed near half genuinely contains a real
baseline-and-service-line pair of real paint, just the WRONG pair, and a junction
detector matching "is there a line crossing near this predicted pixel" cannot tell
which crossing it found. **Rejected — not because it is untested, but because it is
tested twice already, under the names `verify_court` and joint correspondence, and it
inherits the ground-plane symmetry problem that both those failures actually trace to.**

### 5. Vanishing points / horizon geometry — REJECTED, same reason, already closed by name.

Two things already exist for this: (1) `court-detection-negatives.md` records
"Vanishing-point filtering as a court/not-court classifier" **closed by argument** — a
shared vanishing point proves 3-D parallelism, not coplanarity, so it cannot even
distinguish a court from an aligned building. (2) The horizon row implied by a fit is
already reported (`net-anchor-calibration-check.md` §5, "the one number that did
separate the known pair") and is explicitly flagged there as **NOT independent
evidence** — it is a function of the same four corners and the fitted hfov, reported
because it is free and reads concretely, with **no bar proposed on it for that reason**.
Detecting the ACTUAL image vanishing points from real line segments and comparing them
to the ones implied by the fit is the same problem as candidate 4 above, wearing a
different name — it needs the same line detector whose ~6.4 px disagreement with truth
already set the ceiling for every classical/joint-correspondence branch this project
has killed. Rejected as a duplicate, not reassessed from scratch.

### 6. Shadows — a genuinely independent idea, not rejected, but not worth building now.

**What it measures.** Shadow tip position (ground plane) plus a known caster height
(net post 1.07 m, or an assumed player height) constrains sun elevation via
`tan(elevation) = height / shadow_length`. Internal CONSISTENCY — do the post's shadow
and a player's shadow, both converted through the same fitted homography, imply the
SAME sun azimuth and elevation — is a real, non-circular check, because it does not
need to know the true sun position, only that two independently-cast shadows in one
frame must agree if the calibration converting their image positions to metres is
correct. This is a known technique in image-forensics literature for detecting
composited/manipulated photos (shadow-consistency analysis), applied here to a
different purpose.

**Why it ranks last anyway.** (a) **It needs no shadow at all on an overcast day or an
indoor shell court** — and this project's own footage census records Shell as 64 of
116 clips, the single largest surface bucket, entirely indoors, entirely without this
signal. (b) **This project has already found the net's OWN shadow to be a measured
confound** for an unrelated check (`net-anchor-calibration-check.md` §4: the failed
`band_ratio` bar's likely-wrong control strip "picks up the net's own shadow" among
other clutter) — so shadow segmentation is demonstrably messy on exactly this footage
before any new work is attempted. (c) **No shadow detector exists here in any form** —
this is not an increment on shipped infrastructure the way the post detector is; it is
a new CV problem (segment a specific person's or post's cast shadow, separate from the
net's own shadow, other players' shadows, and line paint) with no existing on-device
component to build from. **Not rejected as wrong — ranked last because it is the only
candidate here that is simultaneously footage-inapplicable on the majority surface,
confound-prone on the footage where it does apply, and requires a wholly new detector.**

---

## What I would build first, and what would falsify it

**Build: the net-post detector**, as the next line item in the existing
`net_anchor_check.py` / `net_tape_height.py` family — a vertical matched-filter sweep
at the predicted post columns, refusal rules mirroring the tape's (R1–R5), reporting
base row and top row exactly as the tape reports its one row.

**Function: a NUMBER shown to the human doing the one-time calibration confirmation,
never an autonomous accept/reject gate.** This is not a new principle — it is the
pattern already shipped (`render_corner_audit.py`, `net_anchor_check.py`) and the
pattern every attempted GATE in this family has failed at: `verify_court`'s
coverage/centrality bars, the camera-height "screen" (which would false-reject a
correct Wimbledon broadcast calibration), and `net_anchor_check`'s own `band_ratio`/`dy`
bars (which INVERT on the one pair with known truth). Four gates tried, four gates
retired as reported numbers only. A fifth gate is not proposed here.

**Pre-registered falsifier, cheap and not yet run**: before writing any detector code,
**count post visibility across the 27 already-rendered `*_netanchor.png` files** — a
human look, zero build cost. If posts are visible (both, or even one) on fewer than
roughly a third of amateur-mount clips, the candidate is framing-limited to the point
of not being worth the detector, regardless of its per-pixel precision, and the tape
(already built, already working within its stated limits) remains the only working
off-plane check. If posts are visible on a majority, the detector is justified purely
by that count.

**Second falsifier, for the detector once built**: reuse the tape's own pre-registered
bar — AGREE if `|Δheight| ≤ 10%` on ≥ 2/3 of confident measurements, minimum n ≥ 6 —
and additionally require that where BOTH tape and post agree with each other to within
their combined precision, they also agree with the fitted corner height; where they
disagree WITH EACH OTHER, that specific disagreement is the sag signal the tape run
already inferred but could not isolate.

---

## The honest framing this brief asked for

**A human confirming the calibration once, at setup, is already the shipped product**
(`run.py check`, the Court Setup tool, manual four-tap calibration) and nothing in
today's or this run's work argues for replacing it with an autonomous verifier. Every
attempt at an automated ACCEPT/REJECT gate in this project — four of them now, across
two research sessions — has failed on the same shape of evidence: a statistic that
correlates with correctness in the middle of its range but is fooled at the edges by
exactly the wrong-court class most worth catching (a self-consistent, plausible, WRONG
court). **That pattern is now established enough to generalise from, not just to
observe again**: no ground-plane-only statistic can, in principle, distinguish the
`yt_match40`-class error, because that error preserves every ground-plane invariant a
homography has to preserve.

**What IS worth building is not a gate — it is a second independent NUMBER for the
human to look at**, exactly the role the net tape already fills successfully (AGREE,
13 of 15 clips, closed 2026-09-05) and exactly the role the post detector would add
(closing the tape's one remaining ambiguity, sag vs. calibration error, at close to
zero marginal engineering cost). That is a genuinely small, bounded, high-confidence
increment — not a new verification system, and not a claim that automated verification
of ANY kind should be trusted to run without a person reading the result.

**For the PM, the tradeoff stated plainly:** the post detector is cheap (reuses shipped
code, no new model, no network, on-device trivially) and directly closes a named,
measured ambiguity in a check that already works — build it. The gravity-arc idea is
the theoretically strongest independent reference in this whole list (an actual
physical constant, not another court-object assumption) but has three separate reasons
in this project's own history to expect it to fail cheaply if funded now (T22, the
arc-observability residual finding, and unmeasured drag bias) — worth a narrow,
explicitly-scoped pilot if the founder wants the underlying science question answered,
not worth funding as a shipping feature. Shadows and the two duplicate candidates
(internal markings, vanishing points) are not worth funding at all on current evidence.
Decision left open.

---

## What was considered and rejected, and why (summary table)

| Candidate | Rejected because |
|---|---|
| Other court markings (service lines, T, singles sidelines) | Already scored by `verify_court` coverage (failed, `verify-court-false-rejects.md`) and by joint line-to-model correspondence (failed, `least-squares-court-fit.md`) — same statistic and same detector-ceiling under a different name, not new work |
| Vanishing points | Already closed as a court/not-court classifier (`court-detection-negatives.md`); the numeric form is not independent of the four corners (`net-anchor-calibration-check.md` §5) and would need the same ~6.4 px line detector every classical branch already failed on |
| Shadows | Genuinely independent in principle, but inapplicable on Shell (64 of 116 clips, indoors), already shown to confound an unrelated check via the net's own shadow, and needs a wholly new detector with no existing component to build from |

---

## NOT ESTABLISHED THIS RUN

- **Post visibility fraction across the corpus.** The single cheapest fact that would
  settle whether to build the post detector at all — a look at 27 existing PNGs, not
  performed here (out of scope for a research assessment; flagged as the pre-registered
  first step above).
- **Any error budget for the gravity-arc idea.** Explicitly not estimable without a
  built pilot; stated as such rather than guessed.
- **Whether pose keypoint head/foot bias has ever been measured on this project's own
  YOLO-pose model.** The 10–14 cm head-crown gap quoted for candidate 3 is a general
  pose-literature figure, not one measured on this repo's model or footage — flagged
  per the rule that a benchmark number is only as good as the footage it came from.
- **A shadow-consistency implementation of any kind.** Assessed on argument only, per
  the brief's own instruction that a negative assessment is a fine outcome — nothing
  here was built or run to confirm or refute it beyond the reasoning given.

---

## The candidate-1 falsifier, RUN. Post visibility is not the limit. 2026-09-05 (lead)

The assessment above ranks net posts first but flags a blocker: `net-anchor-calibration-check.md`
states qualitatively that "posts are frequently off-frame", with **no fraction ever measured**.
The proposed falsifier was to count post visibility *before* writing any detector. Counted:

| | clips |
|---|---|
| **both** posts project inside the frame | **27 of 28** |
| exactly one | 1 (`court_pts_refined`, which has no video and is unverifiable anyway) |
| neither | **0** |
| **at least one** | **28 of 28 = 100%** |

**The qualitative claim was wrong, and it was blocking the best candidate.** Framing is not the
limit. Every calibrated clip in the corpus puts at least one post in frame and all but one puts
both.

**Two limits on this number, stated rather than buried.** It projects the post position *under
each clip's own calibration*, so for a wrong calibration the projected post could be anywhere —
it is a framing-feasibility estimate, not a guarantee about a bad calibration. And "inside the
frame" is not "visible": a post can be in frame yet occluded by a player, or lost against a dark
fence. What the count rules out is the specific objection raised — that posts are too often
outside the image to be useful — and it rules it out decisively.

**So candidate 1 is unblocked.** It remains what the assessment says it is: one more cheap
diagnostic number for the human who confirms the calibration at setup, not an autonomous gate.
Four autonomous gates have now failed, and this does not make a fifth.
