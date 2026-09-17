# Court auto-detection after the line ceiling — is there a next build, or not

> Assessment, not a plan to execute. Written by researcher, 2026-09-05, on top of
> [least-squares-court-fit.md](least-squares-court-fit.md) (2026-09-04) and
> [verify-court-false-rejects.md](verify-court-false-rejects.md) (2026-09-04). Nothing here
> re-runs or re-derives either result; both are cited as given.

## Finding, stated first

**No line-based auto-detection branch — classical or learned, better fitter or better
search — can be shown to reach the shipped 8.1 px bar, and there is no untried candidate
left in this family that the project's own evidence supports funding.** The bottleneck
is the line detector's ~6.4 px rms disagreement with the true court, and roughly the same
order of magnitude (~5.8 px) is already accounted for by the human corner-click
neighbourhood itself — so a large share of the "ceiling" may not even be a detector
defect to fix. **My recommendation is to stop building auto-detection branches for v1 and
treat manual calibration as the product answer** — not as a fallback, as the answer. This
is not a new position invented for this run: STATE already ships manual calibration as
the working path and has closed five auto-detection branches, most recently this week.
This assessment closes the sixth candidate list rather than opening a seventh.

---

## 1. Is the 6.4 px gap a detector problem, a labelling problem, or a definitional one?

**Evidence available:** two numbers, both already on record, not re-measured here.

| Quantity | Value | Source |
|---|---|---|
| Line detector's rms disagreement with the human-derived true court | **6.44 px@640** | `least-squares-court-fit.md` §3 |
| Median distance a human's own 4 corner clicks vary within (the "click neighbourhood") | **~5.8 px** | STATE withdrawn-figures row `0.18–0.31`, `eval/truth_neighbourhood.py` |

**These are the same order of magnitude.** 5.8 px of the 6.44 px gap is consistent with
being nothing more than the noise already present in the *definition* of "true court" —
before the line detector is asked to agree with anything. That does not prove the
detector is unbiased; it proves the experiment as run cannot currently tell detector
bias apart from label noise, because the two are close enough that either could be doing
most of the work.

**What each candidate cause would look like, and which this evidence supports:**

- **A detector problem** (the classical Hough/ridge line-finder is systematically off the
  true painted line — e.g., biased toward one edge of the line's width, or drawn toward a
  nearby shadow/mesh) would show up as a *fixed offset* independent of who labels the
  court. Nothing here isolates that from the labelling noise.
- **A labelling problem** (the four-corner click is itself imprecise, and errors amplify
  through the homography at the foreshortened far court — exactly the "few px error
  amplified" mechanism STATE already names for the *4-point fit's* 17.1 px) would show up
  as detector-to-truth error tracking corner-click spread. The 5.8-vs-6.44 order-of-magnitude
  match is consistent with this, not proof of it.
- **A definitional problem** (a painted line has ~5 cm of width, the camera has motion
  blur and JPEG/H.264 block noise, and "the line" is genuinely a band, not a curve of zero
  width) sets a floor under *both* of the above regardless of who or what measures it. At
  amateur phone distance (15-24 m to the far baseline, per this project's own measured
  mounts) a 5 cm line width subtends roughly 2-4 px at 640-wide — not the whole 6.4 px, but
  a non-trivial fraction of it, and it does not go away with a better detector or a
  steadier hand.

**What is and is not established:** it is established that the 6.4 px gap is *not* a pure
fitting artefact (§3 of the cited evidence proves this directly — the best possible fit to
the detected lines is 3.01 px, tighter than the human homography's own 6.44 px, so the
optimiser is not the problem). It is **not established** how the remaining budget splits
between detector bias, click noise, and line-width/blur. My judgement, not a measured
fact: **most of it is irreducible or close to it**, because 5.8 px of click-neighbourhood
noise plus 2-4 px of physical line width already covers most of 6.4 px without invoking
any detector defect at all. Confidence in that judgement: **45%** — better than a guess
because the orders of magnitude line up, worse than a finding because nobody has run the
decomposition.

**What would falsify this (the cheapest test in this whole assessment):** click a
*sample of points directly along* each of the four outer court lines — not just the four
corners — on a handful of frames already in the gold set, and measure the classical line
detector's rms distance to those direct line-clicks. This is a genuinely different
ground truth from the corner-derived homography (it needs no fit, no projective geometry,
just point-to-line distance) and it decomposes the question directly:
- If the detector-to-direct-line-click residual is **well under 6.4 px** (say, 2-3 px),
  the corner-click-derived "truth" is the noisier element, not the detector — the
  detector may already be closer to the true line than this whole analysis credits it,
  and the real problem is that a 4-point-derived homography is a bad way to *score* a
  line detector, not that line detection is bad. This would not, on its own, unlock a
  route to 8.1 px, because the shipped fit is presumably scored the same corner-click
  way — but it would matter for whether any future line-based effort is worth funding.
- If the residual is **still ~5-7 px**, the detector genuinely disagrees with the paint
  by roughly what was measured here, corroborating that the gap is close to irreducible
  for a classical line-finder on this footage.
- If the residual is **>10 px**, the detector itself is a real, fixable target — which
  would reopen (not re-propose unchanged) a "better classical line detection" branch,
  but on a different, narrower objective than anything already closed.

This is a small, cheap, one-afternoon labelling task on existing gold clips, not a model
change — squarely a `researcher`/founder labelling item, not backend-dev work, and it is
the single most informative next measurement in this whole area if anyone wants to keep
this line of investigation open at all.

---

## 2. The alternatives, each judged against the same 8.1 px / ≤10 px bar

| Candidate | Verdict | Why |
|---|---|---|
| **Better classical line detection** (sub-pixel Hough refine, local ridge fit — the ML6 "crop + local Hough refine" trick cited in `ML_PLAYBOOK.md`) | **Not funded on current evidence.** Untested here specifically, but §1 above shows the ceiling may not even be a detector-accuracy problem — it may be dominated by label/definitional noise of the same order. Funding a refinement pass before the falsifying test in §1 runs would be guessing at a target that might not exist. Not the same experiment as any of the five closed branches (`building the court quad from detected lines`, `snapping onto detected lines`, `global mask replacement`, `topk`/seed-ranking/`EVID_BAND` changes) — those attacked correspondence or search, not sub-pixel line localisation — but it inherits the same risk profile: five branches in this family, all measured, all dead. |
| **Learned keypoints (CourtNet)** | **Already closed, and today's finding does not reopen it.** STATE: *"Improving CourtNet for auto-calibration — wrong target: CourtNet is Tier 2, `courtfit` consensus is Tier 1 and beats it."* CourtNet fires on only **21.6%** of amateur frames at baseline. Today's finding is that Tier 1's *ceiling* is ~6.4 px of line-truth disagreement — but Tier 1 still beats Tier 2 in absolute terms (8.1 px on the frames it accepts vs. a keypoint net that fires on barely a fifth of frames). A capped classical detector still outperforms a lower-coverage learned one; nothing here changes that ordering. Re-proposing CourtNet improvement now would be proposing the same closed idea under new cover — barred by rule 3. |
| **Learned dense segmentation of court paint** (a U-Net-style per-pixel line-probability mask, replacing the classical colour/contrast mask) | **Genuinely untested, and I recommend against funding it — reasoning, not a measurement.** This is architecturally distinct from CourtNet (dense pixel labels, not 14 sparse keypoints) and from the closed "global mask replacement" branch (that was classical contrast/chroma engineering on the *existing* mask, not a trained network). But §1's core question applies here just as much as to classical detection: a learned segmentation net still has to localise a painted line's *centre* through the same physical floor — line width, motion blur, compression — that may already explain most of the 6.4 px gap. A learned net could plausibly **improve robustness/fire-rate** (more frames where lines are found at all, the CourtNet-style failure mode) without improving **localisation precision** past that same physical floor. Since the finding this run is built on is precision-limited, not coverage-limited, a segmentation net attacks the wrong axis unless the §1 decomposition comes back showing real detector-bias headroom. Also costs real ANE budget (§3) for a payoff that is speculative twice over. |
| **Accepting manual calibration as the product answer** | **This is the recommendation.** It already ships (`run.py check`, the Court Setup tool, `framing_report`-style guidance), it already works (the human-clicked calibrations are the "truth" this entire evidence chain is measured against — they are not a fallback, they are the reference standard the auto-detector has been trying and failing to reproduce for five-then-six branches), and every number in this project's court-accuracy story (close-call accuracy 54-81% by mount height, the 8.1 px shipped fit) is downstream of a human-clicked or human-verified court. The project has a standing preference, stated explicitly in this brief, for controlling the input over solving the general vision problem — this is exactly that preference, applied to the one subsystem where it has now been tested six times over. |

---

## 3. Hard constraints check — does any candidate above get disqualified by them?

**None of the candidates above are disqualified by the iOS/A13/Core ML/on-device
constraints per se** — that is not why I am recommending against them. A classical
line-detector refinement, a CourtNet-style keypoint net, and a dense-segmentation U-Net
are all expressible as Core ML graphs (conv/pool/upsample ops, all ANE-eligible); none
requires a network call, a datacentre GPU, or anything outside this project's boundary.

What the constraints *do* affect is the cost side of the tradeoff, which matters because
the accuracy case for funding any of them is already weak (§1, §2):

- Per `coreml-ane-budget.md` (my own prior research, not re-derived here), **pose at
  1280 already consumes on the order of ~1,000 ms/frame on an A13's ANE** — the single
  largest item in the whole perception budget. Any additional court network competes with
  that for the same fixed frame budget, and the offline analyzer is not real-time, so this
  is a throughput/thermal cost, not a hard blocker — but it is not free.
- Per `mobile-port-split.md`, the **existing classical court pipeline (`courtfit.py` +
  `calibration.py`, ~2,900 lines) has no conversion toolchain to iOS at all** — it would
  need to become a shared C++ core over OpenCV's mobile build, which is a genuine
  engineering project, not a port. A learned replacement (CourtNet or a new segmentation
  net) *would* have a real Core ML export path where the classical pipeline does not —
  that is the one respect in which a learned approach is mechanically easier to ship, not
  more accurate.
- None of this changes the verdict in §2: readiness-to-export is not the same question as
  whether the resulting network would clear the 8.1 px bar, and nothing in this section
  argues that it would.

---

## 4. Is court auto-detection on the v1 critical path at all?

**No, plainly.** Manual calibration ships and works today; `run.py check` plus the Court
Setup tool already guide the user to a mount and framing that produces good calibrations,
and the accuracy numbers this whole project reports (close-call accuracy by camera height,
the 8.1 px reference fit) all come from that human-clicked path, not from auto-detection.
Auto-detection has never shipped as the default; it has been a research target pursued
and closed across (with today) six measured attempts since 2026-08-13ish.

**What saying this plainly frees:**

- **The mobile-port question closes for v1.** `mobile-port-split.md` already lists court
  auto-detection under "needs a rebuild, not a port" with the explicit note *"a v1 can
  skip it: manual 4-corner tap is already pure JS."* This assessment corroborates that
  call rather than just repeating it — the accuracy ceiling found this week means even a
  *successful* port of the classical pipeline would not have shipped something better
  than manual entry, so there is no accuracy case for prioritising that rebuild even after
  v1.
- **backend-dev and frontend-dev effort budget is not needed here.** No Core ML export,
  no C++/OpenCV court core, no correspondence-search engineering is required to hit v1.
- **This researcher's remaining court-detection budget should move to the one open,
  cheap, decisive test in §1** (direct line-clicking, not corner-clicking) if the founder
  wants the question answered at all — or to nothing, if the founder is content leaving
  court auto-detection closed and moving research effort to the ball/player/point-boundary
  work that is still genuinely open (see agent-memory `open-questions.md`).
- **The product decision this frees, stated plainly, left open:** does the product ever
  want auto-detection as a convenience feature (skip the 4-tap setup) even at *lower*
  accuracy than manual entry, accepting a worse calibration in exchange for less user
  friction? That is a real tradeoff a PM could take either way — nothing in this evidence
  says users must hand-click forever, only that nothing tested reaches manual's accuracy.
  This assessment does not resolve that tradeoff; it says the "auto-detection that matches
  manual accuracy" version of the feature is not currently buildable.

---

## 5. Rule 11 check

Every candidate discussed above is compliant. Classical line detection operates on raw
pixel colour/contrast; CourtNet and any hypothetical segmentation net would train against
human-clicked corners or `tools/synth_truth.py`-derived geometry; manual calibration is
itself a human click. None touches a scoreboard, HUD, or burned-in graphic, and nothing
in this assessment proposes a new ground-truth source of any kind — the one test
recommended in §1 is more human clicks (on lines instead of corners), which is the same
compliant category the project already uses.

---

## Recommendation

**Stop funding auto-detection branches for court geometry. Ship manual calibration as the
product answer for v1** — not provisionally, as the settled position — and do not
re-open classical line detection, CourtNet improvement, correspondence search, or
alternative fitters without a new argument that specifically survives this file's §1 and
§2. The one measurement worth running, if the founder wants the underlying science
question closed rather than just the product question, is the direct-line-click
decomposition in §1 — it is cheap (an afternoon of labelling on existing gold clips), and
it is the single measurement that would falsify this recommendation's premise that the
gap is substantially irreducible.

**The one measurement that would change this recommendation:** the §1 direct-line-click
test returning a detector-to-truth residual **>10 px** (versus the corner-derived 6.44 px)
— that would mean the classical detector carries real, fixable bias beyond both click
noise and physical line width, and a bounded "better line detection" branch would then be
worth pre-registering on that specific, narrower objective. Short of that result landing,
this recommendation stands.

---

## NOT ESTABLISHED THIS RUN

- **The §1 decomposition itself.** This assessment argues from order-of-magnitude
  agreement (5.8 px click noise vs. 6.44 px total gap), not from a direct measurement of
  detector bias in isolation. That is the load-bearing gap in this whole file, named
  rather than hidden.
- **Whether a learned dense-segmentation network would improve *coverage* (frames where
  lines are found at all) even if it does not improve *precision*.** That is a different
  metric from the one this whole evidence chain is built on, and this assessment does not
  claim to have ruled it out — only that it is not what the current bottleneck is asking
  for.
- **Any A13 throughput number for a hypothetical new court network.** Per
  `coreml-ane-budget.md`, no A13 ANE figure exists for anything in this stack; the cost
  argument in §3 is arithmetic from published figures on other silicon, not a measurement.
- **The product tradeoff in §4** (auto-detect-but-worse vs. manual-only) is stated and
  left open by design — it is a PM decision, not a research finding.
