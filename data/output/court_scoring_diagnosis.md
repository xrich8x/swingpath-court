# Court detection — what is actually wrong, measured 2026-08-24

Session O's diagnostic pass. **Five hypotheses tested, five negatives, and one published
claim withdrawn.** No shipped code changed. Pre-registered brief:
[docs/archive/sessions/SESSION_O_shell_courts.md](../../docs/archive/sessions/SESSION_O_shell_courts.md).

Every number here is search-free unless stated: the scorer is handed a court and asked
what it thinks, so "can the criteria recognise the right answer" is separated from "can
the search find it". Ground truth is human only — the 10 `"_exact": true` calibrations.
Distractors are the shipped coarse grid, so a negative margin is a live failure.

    margin = score(true court) − max score(court >20 px from truth, at 640 wide)

The margin, not the level, decides everything below. A higher score at the truth with a
lower margin is a recall lever that ships a confident wrong court — which is how the
seed-grid widening failed earlier this month.

---

## 1. The evidence band is inert — REFUTED

`_ori_detail` calls a model line "measurable" when paint sits within `EVID_BAND (5.0) ×
tol` but only counts support within `1 × tol`. The hypothesis was that clutter 3–4 tol
away from a projected line promotes it into the denominator while contributing nothing to
the numerator, dragging down the true court on cluttered frames.

**It does not happen.** `n_included = n_geometrically_in_frame = 10 of 10` court lines on
**every clip at every band** from 5.0 down to 1.0. The gate never excludes a line at the
true court, so it cannot be what depresses the score.

## 2. Narrowing the band is a wrong-court lever — as pre-registered

It leaves the truth untouched (`g@true` identical to three decimals) and lifts the wrong
courts, whose `n_included` falls as their poorly-supported lines drop out of the
denominator:

| band | 5.0 (shipped) | 3.0 | 2.0 | 1.5 | 1.0 |
|---|---|---|---|---|---|
| median margin | **+0.123** | +0.123 | +0.116 | +0.111 | +0.102 |
| median `n@wrong` | 10.0 | 10.0 | 9.5 | 9.0 | 8.5 |

`band1.0` lifts 2 of the 5 low clips over the 0.33 gate *while cutting the pooled margin*.
Caught by the pre-registered `n_included` guard rather than shipped.

## 3. Geometric observability is a no-op — so the expensive half is closed

Deciding observability from geometry rather than nearby paint (`ev = seen`, dropping the
`EVID_MIN` test) is one line, so it was measured rather than costed. **+0.000 margin on all
10 clips, byte-identical to shipped.** The free half buys nothing, so there is no evidence
to justify the un-occluded half that needs real machinery. Closed.

## 4. Two follow-up suspicions, both refuted

**Behind-camera projection.** `calibration._apply` divides by the homogeneous coordinate
with no sign check, so a court point beyond the horizon could mirror back into frame and
inflate the denominator with samples that can never carry paint. Measured: **0.0% of
samples behind the camera on every clip.** The reason for suspecting it was also wrong —
`reliable_court_span`'s "7.5 m of 23.77" on `am_hard_utr` describes metres-per-pixel
precision near the horizon, not lines being off-frame. All ten lines really are in frame.

**Ground-truth registration error.** If the human's clicks were a few pixels off, the
projected line would miss the paint by more than `tol` and score near zero. Swept `tol`
×0.5 → ×4: no clip shows the steep-then-plateau signature that would produce, and the
median margin degrades monotonically (+0.147 → +0.123 → +0.049). Not a labelling artefact.

*(Aside worth recording: the shipped `tol` is mildly conservative-optimal — ×0.5 scores
+0.147 against the shipped +0.123 on the same 8/10 clips. Tightening it would trade
against what the refine stage has to grab, so it is not a free win and was not taken.)*

---

## 5. THE METHOD CORRECTION — a published claim is withdrawn

`eval/candidate_audit.py` found `am_hard_utr`'s per-frame locks landing **within 20 px of
the human court and outranking it by 0.296**. The human's clicks are not the
best-registered court inside their own tolerance band — and every search-free number this
project has published scores those clicks exactly.

The gate does not define correct as the clicks. It defines correct as **within 20 px at
640 wide** — the empty band between accepted courts (3.4–13.9 px) and refused ones
(25.5–111 px). Sweeping that neighbourhood (`eval/truth_neighbourhood.py`), at a median
**5.8 px** from the clicks:

| | at the clicks | best court the gate still calls correct |
|---|---|---|
| clears the 0.33 accept gate | 5/10 | **9/10** |
| margin over best wrong court positive | 8/10 | **9/10** |
| median margin | +0.126 | **+0.210** |

> **"The criteria reject the correct answer even when handed it" is false on 9 of 10
> clips.** The criteria recognise the correct court; they were being handed a
> mis-registered version of it.

Corrected in place in [court_why_it_fails.md](court_why_it_fails.md) (finding A),
[the research brief](../../docs/archive/RESEARCH_BRIEF_indoor_shell_courts.md) §4, and
`eval/score_truth.py`'s docstring. That paragraph is what drove the external research to
rank "the scoring function is mis-specified" second of five, so those rankings re-weight.

**One clip survives as a genuine scoring failure: `UHf0LeMU2pg`** (best 0.279, margin
−0.014).

---

## 6. Where the failure actually is — the candidate audit

`eval/candidate_audit.py`, 10 references × 8 frames. It reproduces the shipped 2/10 accept
rate exactly (`am_hard_utr` 7 votes, `sAjkpeRq4P4` 6 votes), which is the validity check.

| | clips |
|---|---|
| truth is inside the candidate set (≥1 lock within 20 px) | **7 / 10** |
| ≥2 good locks that also agree with each other | 4 / 10 |
| truth never reached — gating cannot help | 3 / 10 |

The within-frame margin splits those 3 into two different problems, which is exactly what
the vote count cannot do:

| clip | within-frame margin | reading |
|---|---|---|
| `HoHxFSX_gLk_s1` | −0.112 | the locks **outrank** truth → scoring |
| `tc8CGFxyRE8` | +0.161 | truth **outranks** the locks → search/gate lost it |
| `UHf0LeMU2pg` | +0.038 | truth outranks → search/gate |

### The consequence for the gate plan

A refuse-only gate plus a survivor-based vote rule (`≥6 of surviving frames`) converts
**zero** additional reference clips. The good locks do not agree tightly enough with each
other:

| clip | good locks | largest agreeing subset | best possible survivor rate |
|---|---|---|---|
| `CYqapSq5llo` | 4 | 2 | 50% |
| `e8T34KoJzOw_s2` | 3 | 2 | 67% |
| `am_hard_utr` | 8 | 7 | 88% — already accepts |
| `sAjkpeRq4P4` | 6 | 6 | 100% — already accepts |

Even a *perfect* gate that deleted every wrong lock leaves the two convertible clips at 50%
and 67% against a 75% bar. **The player-foot gate's value is precision only.**

*Caveat on the accept-term breakdown in that run: `truth_fails` is a union across the 8
frames, so a term failing on one frame of eight marks the whole clip. It is a "failed at
least once" reading, not a rate, and should not be quoted as one.*

---

## 7. The horizon crop (B2) — safe, and nearly inert

The one recall-positive lever in the plan, run against the required safety check: on all 20
gold clips, does the crop ever delete a court line a human clicked?

**With the pre-registered `k = 1.0` and the four required mitigations, a crop is proposed on
1 of 20 clips** — and that one (`am_ntrp45w`) crops the top 20 rows of a 360-row frame,
removing almost nothing, with +172 px of clearance to the nearest clicked keypoint.

The check ran the real operating condition where it could: 9 of the 20 gold clips have a
local source video and were measured over **120 frames spanning the whole recording** (the
required mitigation #1), yielding 343–480 foot points each. The other 11 are YouTube-stream
clips with no local file and could only be checked on their ~18 extracted gold frames.
Neither population produced a crop.

The mechanism is diagnosed, not guessed. The margin is `k · spread` where `spread` is the
5th-to-95th percentile of foot Y — the near-player-to-far-player range, which is
approximately the whole court's image depth. Subtracting that from the deepest foot puts
the crop row above the top of the frame on 19 of 20 clips, so `crop_row` correctly returns
"no crop":

| | median across the 20 gold clips |
|---|---|
| deepest foot (5th pct of Y) | ~85 px of 360 |
| spread (5th→95th pct) | ~250 px |
| resulting row, `lo − 1.0·spread − 0.05·h` | ~−180 px → no crop |

Capping detections at `MAX_PLAYERS = 4` (the rules of the game, not a tuned threshold)
roughly halved the blob count — from a median ~9 per frame to ~4 — and **did not change the
outcome**, which is what identifies the margin rather than the mover detection as the cause.

**`k` was not re-tuned.** It is pre-registered, and the brief says explicitly not to fit it
against the gold set — that is the cumulative-drift problem the blind holdout exists to
stop. The honest result is: *B2 as specified is safe and inert.*

If it is re-registered, the margin needs a principled derivation rather than a fitted one.
The quantity being protected against is a player standing *inside* the court rather than on
the baseline, and the deepest that can be is the service line — 5.485 m of 23.77. Near the
horizon that compresses to far less image distance than the near-to-far foot spread. But
converting metres to pixels needs a homography, and the crop runs before one exists, so
that ordering problem has to be solved first.

---

## 8. The frame disagreement — the resolution artefact is REAL, and fixing it fails the gate

`eval/agree_sweep.py`. `courtfit.AGREE_PX = 30` is absolute and does not scale with frame
size, which is this codebase's own recorded trap (every 720p-tuned pixel constant silently
broke at 1080p). `_corner_dist` measures in native pixels, so on a 1920-wide clip 30 px is
10 px at 640 — while accepted courts are allowed to sit 3.4–13.9 px from truth at 640.

**The mechanism checks out, and it is confined exactly where the theory predicts.** Among
locks that are each within 20 px of truth, 4 of 18 clips have them a median of more than
30 native px apart — and three of those four are the high-resolution clips, where the same
distance is small at 640:

| clip | median apart, native px | the same distance @640 |
|---|---|---|
| `e8T34KoJzOw_s2` | 45.8 | **15.3** |
| `A7vXlWIlyrI` | 39.4 | **13.1** |
| `CYqapSq5llo` | 38.3 | **12.8** |
| `am_wingfield_clay` | 56.4 | 56.4 — genuinely far apart |

**But scaling it does not pass.** At the shipped vote bar, height-scaling *loses* a gold
clip:

| `AGREE_PX` | bar | gold | worst | verdict | refs | worst |
|---|---|---|---|---|---|---|
| 30 abs (**shipped**) | 6 | 12 | 13.9 | PASS | 2 | 14.3 |
| 30·h/720 | 6 | **11** | 13.9 | fail | 3 | 14.2 |
| 45·h/720 | 6 | 12 | 13.9 | PASS | **5** | **58.7** |
| 60 abs | 6 | 17 | **116.1** | fail | 4 | 58.7 |

`45·h/720` passes the letter of the gate — 12/20 gold, worst 13.9 — and takes the
references from 2 to 5. **It gets there by accepting a 58.7 px court on the reference set.**
The formal gate is defined on the 20 gold clips, so that court is outside it; the precision
record is not. Treat that cell as a failure.

The one clean cell is `30·h/720` at bar ≥5 — 12/20 gold at 15.2 px, 3/10 refs at 14.2 px,
nothing wrong anywhere — but it bundles the scaling with a lowered vote bar, which is two
changes and must be pre-registered separately.

### The actionable part: they disagree about WIDTH, not position

| dominant disagreeing parameter | clips |
|---|---|
| `w_far` (far half-width) | 7 |
| `w_near` (near half-width) | 6 |
| `y_far` | 4 |
| `cx` | 1 |

**13 of 18 clips' good locks disagree principally about how wide the court is, not where it
is.** Corner distance treats a width error and a position error identically, so the
agreement test spends its whole budget on the least-determined parameter. That points at a
reweighted or court-normalised agreement metric rather than a wider radius — a different
fix, and one this session did not test.

## 9. The player-foot gate is DEAD — it has no discriminative power

`eval/foot_gate_power.py`. Every per-frame lock across all 30 clips, labelled from the human
court: **216 locks, 118 GOOD (within 20 px), 98 BAD.**

| court margin | good mean | bad mean | gap |
|---|---|---|---|
| ±5 m | 0.522 | 0.555 | **−0.033** |
| ±10 m | 0.595 | 0.649 | **−0.054** |
| ±20 m | 0.751 | 0.822 | **−0.071** |

**The gap is negative at every margin — wrong courts contain the players BETTER than right
ones.** The mechanism is obvious in hindsight and fatal: "fraction of feet inside the court"
rewards a court for being *large*, and wrong courts are frequently too large. The statistic
measures size, not correctness.

Every threshold kills at least as many good locks as bad. At the project's standing ≤5%
collateral ceiling for a negation criterion the best cell catches **2.0%** of bad locks —
against pose proximity's 11.4% and racquet-box negation's 54.5%/4.5%, **both of which were
rejected on that bar.** The foot gate is five times worse than the worst idea already
thrown out.

B1 is closed. Nothing in it should be built, and `eval/movers.py` survives only as the
mover-detection primitive the crop used.

## 10. SHELL, with ground truth at last — it is the SEARCH, decisively

Ten human calibrations arrived 2026-08-24 (two per venue, `"_exact": true`). They are
good ground truth and that is measured, not assumed:

- **repeatability** between the two independent labels of each venue: **1.2–7.0 px@640**
  on four of five — tighter than the band accepted courts land in (3.4–13.9 px). The
  exception is **`mpc_tuesday` at 25.4 px**, above the wrong-court line; its two labels
  disagree by more than the amount separating a right court from a wrong one, so it is
  reported but not treated as truth.
- **camera audit**: 2 PASS, 3 LOW-CAMERA, **0 fail**, at fit residuals of **0.0–2.5 px** —
  the best band in the repo. Cameras 1.36–2.81 m, measurable to 45–48% of court depth.
  Independent labels reproduce the implied camera height to **0.02 m**.

*(A prediction of mine died here: I expected the far corners to be unclickable because the
far court looked like a sliver behind the net in a downscaled contact sheet. It is not. That
is the second time this session a visual call was overturned by a measurement — see also the
`am_hard_utr` overlay retraction. Overlays and thumbnails do not settle geometry.)*

### The result

| | shell clips |
|---|---|
| the human court would be **ACCEPTED** if the search produced it | **7 / 10** |
| truth is inside the candidate set (≥1 lock within 20 px) | **3 / 10** |
| locks exist but none is true | 4 / 10 |
| no lock produced at all | 3 / 10 |

**On all 4 clips where locks exist but none is true, the human court OUTRANKS every lock
the detector produced** (within-frame margin +0.041, +0.051, +0.163, +0.355). The scorer
would prefer the right answer. It is never offered one.

Corroborated independently by the neighbourhood sweep over all 20 references (10 original +
10 shell): at a median 4.9 px from the clicks, the true court clears the 0.33 accept gate on
**19 of 20** clips and has a positive margin on **19 of 20**. Only `UHf0LeMU2pg` fails.

> **The scoring criteria are not the bottleneck on shell, or anywhere else. The search is.**
> This is the direct opposite of the premise this session's research brief was written on —
> §4 of that brief has already been withdrawn (see §5), and the external recommendations
> that ranked "the scoring function is mis-specified" second of five were ranked on it.

### The shell failure splits three ways, and they need different fixes

| failure | clips | what it needs |
|---|---|---|
| truth reached, but the vote fails | 3 | the agreement radius — see §11 |
| locks produced, truth never among them, truth outranks them | 4 | seeding / candidate generation |
| no lock at all | 3 | mask or seeding; nothing downstream can help |

## 11. The agreement radius is 6× tighter on shell than on the gate, from resolution alone

Measured: **all 20 gold clips are exactly 640×360**, the original references are 1920, and
every shell recording is 3840. `courtfit.AGREE_PX = 30` is absolute, and `_corner_dist`
works in native pixels, so the radius that decides whether two frames "agree" is really:

| population | native width | AGREE_PX in px@640 |
|---|---|---|
| gold (the gate) | 640 | **30.0** |
| original references | 1920 | 10.0 |
| **shell** | 3840 | **5.0** |

Against an accepted-court band of **3.4–13.9 px@640**. On shell the radius is *tighter than
the distance two correct locks routinely differ by*, so correct frames cannot group.
`flexi_franz_p01` shows it exactly: **6 of 8 locks correct, consensus 9.8 px from the human
court — and 3 votes against a 6 bar.** Right court, refused.

This also explains why the earlier `h/720` scaling failed its gate (§8): every gold clip is
360 tall, so `h/720` only ever *shrinks* the radius there. **The gate population is
structurally incapable of testing a resolution-scaled threshold in the widening direction.**

### MEASURED: it works exactly where predicted, and it cannot ship alone

`AGREE_PX = 30 · (w/640)` holds the radius at a constant 30 px@640-equivalent.

**The no-op property holds exactly.** On gold it gives 12/20 at worst 13.9 px — identical
to the shipped row, as designed. The gate is structurally safe from this change, which also
means the gate cannot *validate* it.

**On shell it does what the diagnosis predicted.** 0 → 2 accepted, both correct:

| clip | shipped | `30·(w/640)` |
|---|---|---|
| `flexi_franz_p01` | 3 votes, 9.8 px, refused | **7 votes, 9.1 px, ACCEPTED** |
| `flexi_franz_p07` | 2 votes, **39.1 px** | **7 votes, 10.5 px, ACCEPTED** |

`flexi_franz_p07` is the sharpest case: the tight radius had picked a *wrong* group of 2 as
its largest agreeing set, giving a 39.1 px consensus. Widening let the 5 correct locks find
each other and the consensus falls to 10.5 px.

**But on the 1920 references it admits two wrong courts, and that is disqualifying.**

| clip | shipped | `30·(w/640)` |
|---|---|---|
| `tc8CGFxyRE8` | 3 votes, 59.6 px, refused | 6 votes, **58.7 px, ACCEPTED** |
| `e8T34KoJzOw_s2` | 2 votes, 17.9 px, refused | 8 votes, **28.7 px, ACCEPTED** |

`tc8CGFxyRE8` is a **reproducible wrong court** — the detector finds the same wrong answer
on most frames, and the candidate audit already flagged it as "truth never reached, truth
outranks the locks". It is exactly the failure `run_eval.py`'s own comment names: *"a wrong
court that reproduces across 8 frames votes itself in."* The too-tight radius was
**accidentally protecting against it**, and widening removes that protection.
`e8T34KoJzOw_s2` fails more subtly: widening pulls wrong locks into the agreeing group and
drags the *median* across the 20 px line, from 17.9 to 28.7.

> **Conclusion: the normalisation is right in principle and demonstrably fixes the 4K case,
> but it cannot ship on its own.** The tight radius is doing two jobs — grouping correct
> frames, and suppressing reproducible wrong courts — and fixing the first exposes the
> second. The wrong-court problem is the *search* failure of §10, and it has to be solved
> independently before this can land.

The only cell clean on all three populations is `30·h/720` at bar ≥5 (gold 12/15.2, refs
3/14.2, shell 1/8.4) — but that bundles the scaling with a lowered vote bar, which is a
second change requiring its own pre-registration, and it converts one shell clip rather
than two.

## What this leaves

The scoring branch shrank and the search branch grew:

- the criteria **do** recognise the correct court on 9 of 10 clips (§5);
- the search **does** produce it on 7 of 10 (§6);
- but the frames that produce it **do not agree with each other**, so the vote fails (§6);
- and the two levers aimed at fixing this — the refuse-only gate and the horizon crop —
  are measured at zero and near-zero respectively (§6, §7).

**The live question is the disagreement between frames that have each found the right
court** (§8) — and it is now characterised rather than merely named. It is partly a
resolution artefact in the agreement radius, confirmed and confined to the high-resolution
clips; but widening the radius admits wrong courts, and the disagreement is dominated by
the court's **width**, which corner-distance agreement has no way to treat differently
from its position.

The untested idea that follows from that, stated so it is not mistaken for a result: **an
agreement metric normalised in court terms rather than image pixels**, which would make the
radius resolution-independent by construction and could weight width and position
separately. Nothing has measured it.

**Still untested on the target surface.** All of the above is the 10 hard/clay reference
clips. The five indoor shell recordings remain 0/5 and have no ground truth, so no number
here has been checked against the footage the session exists for.
