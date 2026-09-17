# `verify_court`'s coverage gate does not separate correct courts from wrong ones

> Evidence for the `verify-court-false-rejects` row in [../STATE.md](../STATE.md) (Open).
> Measured 2026-09-04 (lead).

## Why this was run

STATE's joint-line-to-model row names `verify_court` as the **largest single kill
category** in that solver — 9 of 30 tuning clips — and describes them as *"shipped
criteria rejecting a correctly-labelled court"*. That names the function but not which of
its three gates fires, so nothing actionable followed. This measures that.

**Different population, deliberately, and it is not a reproduction of the 9-of-30.** That
figure came from the solver's own 30-clip tuning set. This runs over **every committed
human calibration that has a video** — 25 clips — and asks a narrower question the shipped
pipeline cares about directly.

## Method

For each clip: build `H` from the **four human-clicked corners** (never a detector), take
one real frame, and run the shipped `calibration.verify_court` and its three components.
A refusal here is the shipped gate rejecting a court a human labelled — a false reject by
construction. Nothing trained, tuned, or written back. `H` comes from human clicks, so the
gate is the only thing under test.

The three gates (`calibration.py:1087`): `coverage >= 0.40`, `visible >= 0.30`,
`centrality >= 0.70`.

## Result: 3 of 25 human-clicked courts are REFUSED

| clip | coverage | visible | centrality | which gate fires |
|---|---|---|---|---|
| `CYqapSq5llo` | **0.328** | 0.955 | 0.946 | coverage |
| `HoHxFSX_gLk_s3` | **0.245** | 0.991 | 0.819 | coverage |
| `UHf0LeMU2pg` | 0.517 | 0.968 | **0.661** | centrality (a near miss on 0.70) |

`visible` never fires on any clip — its 0.30 bar is far below the observed range
(0.927–1.000), so on this evidence **it is inert**.

## The finding is not the 3 rejects — it is that the bar sits inside the correct-court distribution

Coverage on courts a human clicked spans **0.245 to 1.000**, and the 0.40 bar cuts through
the middle of it. Correct courts sitting just above the line:

| clip | coverage | |
|---|---|---|
| `HoHxFSX_gLk_s1` | 0.426 | correct, passes by 0.026 |
| `yt_match40` | 0.436 | **grossly wrong (T23), passes by 0.036** |
| `sAjkpeRq4P4` | 0.464 | passes |

> **`yt_match40` PASSES `verify_court`.** Its four corner clicks sit on run-off asphalt, a
> hedge and a fence — STATE calls it *"visibly, grossly wrong"* and it is the clip that
> defines trap T23. The gate designed to catch *"a self-consistent but WRONG court that
> doesn't lie on any white lines"* scores it 0.436 and accepts it, **above two courts that
> are correct**.

So the coverage statistic is not ordering correct courts above wrong ones. It is largely
ordering clips by **how visible their white lines are** — line contrast, surface, exposure —
which is a property of the footage, not of whether the court is right. `courtfit.py:171`
already says as much for one surface (*"verify_court is white-mask-blind"* on clay), and
one of the two coverage rejects here is the clay clip.

## What this does NOT establish

- **A false-accept RATE.** There is exactly **one** court here known to be grossly wrong
  (`yt_match40`). One example proves the gate *can* accept a wrong court; it cannot give a
  rate, and none is quoted.
- **That the 9-of-30 has been explained.** Different clip set, different pipeline stage. It
  is consistent with this, not established by it.
- **Anything about other frames.** One frame per clip (frame 30). Coverage varies with what
  is on the court at that instant — players, shadows, ball marks.
- **A replacement threshold.** None is proposed. Lowering 0.40 would admit `yt_match40`
  further, and the sweep discipline this project just applied to `seen_frac` says a
  threshold must be chosen on held-out clips against a pre-registered bar with a coverage
  floor — not read off the table that revealed the problem.

## What follows

The actionable statement is **not** "retune 0.40". It is that **coverage and centrality are
being asked to do a job neither can do**: separate a correct court from a wrong one using a
white-mask statistic that is dominated by line visibility. The T23 audit already showed the
same thing from the other direction — a 0.9 px reprojection residual also accepted
`yt_match40`, and the **camera-height fit** was the one screen that isolated it. That
suggests the discriminative signal here is **geometric plausibility of the implied camera**,
which `verify_court` does not look at, rather than a better white-mask threshold.

Reproduce: the script is in the lead's scratchpad (`verify_court_rejects.py`) and writes
`verify_court_rejects.json`; it imports the shipped `calibration` module and reads only
committed `data/*_pts*.json` plus their videos.

---

## The camera-height screen, quantified. 2026-09-04

The section above ends by pointing at *geometric plausibility of the implied camera* as the
signal `verify_court` does not look at. STATE asserts that qualitatively ("the one screen
that isolates it"). Here is the actual distribution, read from the `_audit` stamps every
committed calibration already carries — so the screen costs nothing to compute.

**Non-degenerate calibrations fitting a camera above 4 m — the entire set:**

| clip | camera h | stamped | correctness |
|---|---|---|---|
| `court_pts_refined` | 12.28 m | PASS 2.3 px | **unverified** |
| `yt_match40` | 11.30 m | PASS 0.9 px | **KNOWN WRONG (T23)** |
| `eala_pts_auto` | 8.89 m | PASS 3.7 px | **unverified** |

**Every other non-degenerate calibration — all 25 of them — sits between 1.36 m and
3.35 m.** The gap between the plausible band and the next file up is **3.35 → 8.89 m**, a
factor of 2.7 with nothing in it.

That gap is not merely empirical. The shipped framing advice in `calibration.py` states the
physical prior independently of this table: *"a fence clamp (~2.5 m) is the practical
ceiling, a standing tripod is ~1.5 m"*. A court-side amateur mount cannot be 9–12 m; that
is a broadcast gantry.

### What this is, and what it is not

**It is a screen candidate with a physically-motivated bound — not a validated gate.**

- **Only ONE of the three flagged files is verified wrong.** `yt_match40` is confirmed by
  rendered corners. `court_pts_refined` and `eala_pts_auto` are **unverified in either
  direction** — nobody has looked at their corner sheets. They may be correct calibrations
  of genuinely elevated cameras.
- **So the false-accept side is 1-for-1 and the false-reject side is 0 of 25 — on n = 1
  known positive.** No rate is claimed from that, and none should be.
- **The 4 m figure is post-hoc.** It was read off this table. What is *not* post-hoc is the
  physical prior above, which motivates a bound somewhere in the 3.5–5 m region without
  reference to these numbers. A real threshold still has to be chosen on held-out
  calibrations against a pre-registered bar — the discipline applied to `seen_frac` this
  week, and the reason no number is proposed here.

### One decision this already justified

Section 7 of the `seen_frac` evidence nominated `court_pts_refined` and `eala_pts_auto` as
the held-out clips for the replacement-bar sweep. They were rejected on exactly this ground
before any sweep ran, and this table is the quantified version of that call: they are two of
the only three files in the repo that fit an implausible camera, and the third is the clip
that defines T23.


---

## CORRECTION, same day: the camera-height screen is a MOUNT-TYPE test, not a correctness test

The section above called the camera-height fit a screen candidate on the strength of three
flagged files, only one of which was verified. I rendered the corner sheet for one of the two
unverified ones. **It is correct, and that changes what the screen means.**

`eala_pts_auto` had no corner sheet because `render_corner_audit.py` derives the video from
the tag and there is no `eala.mp4` — the footage is `data/incoming/Grass/eala_segment.mp4`.
Rendered directly (clicked corners and their quad only, never a projected court, which would
be circular): **the four corners track the doubles court properly on real match footage.**

So its **8.89 m is a real camera** — this is Wimbledon broadcast footage and that is a
broadcast gantry, not a bad fit.

> **The camera-height screen would FALSE-REJECT a correct calibration.** It does not separate
> *correct* from *wrong*; it separates **amateur mounts from elevated cameras**. On broadcast
> footage a high camera is the right answer.

**What survives.** For this product the screen may still be useful, because the target footage
is amateur phone video on a fence or tripod, where `calibration.py`'s own prior (fence clamp
~2.5 m, tripod ~1.5 m) holds and a 9–12 m fit really does indicate a bad solve. But it must be
described as a **mount-type prior conditional on target footage**, never as a correctness
screen — and on the two clips it would flag, one is correct.

That leaves the positive class at **n = 1** (`yt_match40`) and now a known **false reject at
n = 1** (`eala_pts_auto`). `court_pts_refined` remains unverifiable: there is no `court*.mp4`
anywhere in the repo, so its sheet can never be rendered.

### Two things noticed while looking, both rule-11 relevant

`eala_segment.mp4` carries a **burned-in scoreboard** (EALA/SWIATEK, games and points) **and a
"111 mph" speed readout**. Rule 11 bars both as training target, ground-truth reference and
tuning signal. Recorded here so nobody reaches for that clip as a convenient speed reference —
it is exactly the trap the rule exists for, and it is the only absolute-looking speed number
sitting in the footage tree.

Sheet written to `data/output/corner_audit/eala_segment_corners.png`. A sheet rendered from
`eala_swiatek.mp4` frame 30 was **deleted rather than kept**: that frame is a "MATCH
HIGHLIGHTS" title card, so the corners sat over a blurred graphic and the image would have
read as a gross miscalibration to anyone reviewing the folder.

### The correction is corroborated by a measure, not just by my eye

I corrected the camera-height claim off **one rendered frame**, having already had to walk
back a claim once that day. So it was checked against an independent quantity before being
allowed to stand: `eala_pts_auto`'s own **white-line coverage**, sampled across the segment.

| frame | coverage | visible | centrality | `verify_court` |
|---|---|---|---|---|
| 30 | 0.921 | 1.000 | 0.944 | True |
| 200 | 0.918 | 1.000 | 0.944 | True |
| 400 | 0.908 | 1.000 | 0.944 | True |
| 600 | 0.910 | 1.000 | 0.944 | True |
| 800 | 0.912 | 1.000 | 0.944 | True |

**0.908–0.921 across the whole 900-frame segment** — among the highest coverage in the repo,
beside `flexi_franz_p01` (0.996) and `mpc_tuesday_p01` (0.987), and stable rather than a lucky
frame. Its projected court lands on real white pixels nine times in ten. That is independent
of the corner rendering and of my judgement of it, and it says the calibration is right.

**A nuance this forces, in fairness to the coverage statistic.** Coverage is not blind: it
scores the correct `eala` at 0.91 and the wrong `yt_match40` at 0.436 — it *does* order those
two correctly. The failure is that the **0.40 bar is far too low to act on that ordering**.
But raising it does not rescue the gate either: at 0.60 it would reject `yt_match40` (0.436)
and also `HoHxFSX_gLk_s1` (0.426), `sAjkpeRq4P4` (0.464), `CYqapSq5llo` (0.328) and
`HoHxFSX_gLk_s3` (0.245) — **four correct courts for one wrong one.** So the conclusion above
stands unchanged: correct and incorrect courts overlap in coverage, and no single threshold
separates them. What is corrected is only the sharper claim that coverage carries *no* signal.


---

## WITHDRAWN: "a wrong court scoring 0.944". The calibration was CORRECT; I mis-read the net

Written 2026-09-05, withdrawn the same hour. The section that stood here claimed the founder's
re-click of `yt_match40` was still wrong — far corners on the net — and presented it as this
file's strongest evidence, a wrong court scoring 0.944 line coverage. **It was my error, not a
bad calibration.**

**What I did wrong.** I compared the projected net **GROUND line** — court-y 11.885 m, where
the net meets the court, which is what a homography gives you — against the net's **TOP TAPE**
in the image. The tape sits **0.914 m above the ground**, so it necessarily images higher.
Comparing the two is apples to oranges and will "fail" every correct calibration ever tested.

**The arithmetic that settles it.** For a pinhole at height `H`, `(row − horizon)` is
proportional to `H / depth`; a point `h` above the ground at the same depth scales by
`(H − h) / H`. With the fitted camera at **1.64 m** and a horizon row of **264.6** derived from
the three court rows:

    net ground line (court-y 11.885)  projected at row 325.0
    => top tape (0.914 m up) must image at row 291.3
    observed white tape in the frame:              row ~295
    mismatch                                        3.7 px

**Two independent confirmations.** The far player's feet sit at row ~301, which this
calibration places at **24.0 m** — the far baseline, exactly where a player standing at their
baseline belongs. And the fit residual is **0.0 px** with coverage 0.948 and a plausible
1.64 m mount.

**So the re-click is good, and I sent the founder back to redo work that was already correct.**

### What survives, and it is not nothing

The original `yt_match40` calibration — preserved at `data/yt_match40_pts.json.bak-2026-09-05`
— really did score **0.436** coverage while being grossly wrong, and really did pass the audit
at 0.9 px. That is still a genuine example of coverage failing to separate, and the rest of
this file stands on the 25-clip measurement, not on this clip.

What does **not** survive is the claim that a wrong court scored 0.944. Nothing in this repo
has been shown to do that.

### The lesson, which is worth more than the claim was

A check against a physical object in the frame is only valid if it is projected **at that
object's real height**. The net tape is at 0.914 m, the posts reach 1.07 m; only the net's
*base* is on the ground plane a homography describes. This makes the height check a *better*
anchor rather than a discarded one — the tape row is tied to the fitted camera height, so
agreement directly tests the quantity that exposed this clip's original error (an implausible
11.3 m). That correction has been sent to the agent building the net-anchor check.

---

## [SUPERSEDED — see the withdrawal above] The original claim, kept for the record

The founder re-clicked `yt_match40`'s corners on 2026-09-05. The result is the sharpest
demonstration of this file's thesis so far, and it is a **live** one, not a retrospective.

| | old (wrong: corners on asphalt/hedge) | re-clicked (wrong: corners on the NET) |
|---|---|---|
| fit residual | 0.9 px | **0.2 px** |
| camera height | 11.3 m (implausible) | **1.61 m (plausible)** |
| `verify_court` line coverage | 0.436 | **0.944** |
| verdict | PASS | LOW-CAMERA |

**Every screen this project has improved passed it, and it is still wrong.** The residual
improved. The camera-height screen — the one that isolated the original error — now reads a
perfectly plausible 1.61 m. And line coverage reads **0.944**, which is higher than almost
every *correct* calibration in the repo (`eala` 0.91, `L73ep7JHiJ4` 0.75) and beaten only by
the very best (`flexi_franz_p01` 0.996).

**What actually caught it:** projecting the **net** — a distinct physical object at a known
`court-y = 11.885 m`, plainly visible in the frame with its posts and tape — and comparing it
to where the net really is. The projected net landed **~36 px below** the real net tape, and
the projected *far baseline* landed on the real net. The four far corners had been placed on
the net rather than the far baseline: the whole court mapped onto the near half.

**Why coverage rewards that.** Mapping a full court onto the near half puts the projected
lines on top of *real paint* — just the wrong paint. The near half carries the near baseline,
both service lines, the centre line and the sidelines, so a court compressed into it scores
extremely well on "do my lines lie on white pixels?" **Coverage measures whether lines land on
paint, not whether they land on the paint they are named for.**

> **The lead nearly accepted this calibration on the strength of the 0.944.** It is recorded
> because that is the failure this file exists to document, and the number very nearly worked
> a second time on the same clip.

**The generalisable check, and it is cheap:** project a court feature that was **not clicked**
and that is **physically identifiable in the frame** — the net is ideal — and require it to
land on the real thing. That is not circular (the net is not one of the four fitted points)
and it does not care about line contrast, surface or exposure, which is exactly where coverage
fails. Recommended as the standard follow-up to any re-click, alongside the rendered corners.
