# What is actually going wrong — measured at the known-true court

Follow-up to [court_breadth_54.md](court_breadth_54.md). Two questions from the user:
*take only the top-down angle for the professional clips*, and *why do the framings
that show more of the court do worse?*

## 1. Top-down-only selection: done, and it does not help

`eval/pick_view.py` proposes N numbered candidate frames per recording and a human
keeps the ones that are the elevated top-down TV camera; the choice is written to
`eval/clip_classes.json`. Applied to six broadcast recordings, excluding serve cams,
half-court cameras, close-ups and score cards.

```
clip            frames locked votes    result
45VdNMtbulA          8      0     0   refused
9gUvgm23qMU          8      0     0   refused
DY6WVsuHqFs          8      1     1   refused
eala_segment         8      0     0   refused
J8__TwOgTY0          8      2     1   refused
U5Af1jGgYqA          8      1     1   refused
```

**0 of 6.** The instruction was right — the frames genuinely were mixed, and
`45VdNMtbulA`'s automatic selection had included a low tight camera showing only the
near half. Fixing that changed nothing, so camera-angle selection is not the cause.
`eala_segment` is the cleanest evidence: **23 of its 24 candidates were already the
same top-down camera**, and it locks zero frames.

## 2. Three hypotheses tested and killed

| hypothesis | test | result |
|---|---|---|
| the broadcast pose is not seeded | added 27 synthetic 6–18 m / long-lens poses, mirroring `_lowcam_seeds` | **no change** on any clip |
| the court is too small in the frame | cropped toward the court and upscaled, x1.18 → x2.50, nothing else changed | **no change**; `BwLUgip8OSI` got *worse* (2/4 → 0/4) as its corners cropped out |
| the wrong camera angle was selected | human top-down-only selection, above | **no change**, 0/6 |

A fourth reading was **retracted mid-run**: a wide parameter sweep found courts scoring
g = 0.41–0.52 on broadcast frames, above the 0.33 gate, which read as "the answer exists
but the search misses it". Drawn on the frames, **all four are junk** — three imply a
0.6–0.9 m camera at Wimbledon with 21–37 px `cam_fit` residuals. The agreement score's
global maximum sits on a wrong court, so that number meant the opposite of what it looked
like. Second time this session a figure pointed one way and the picture corrected it.

## 3. The real diagnosis: score the gates AT the true court

Ten clips carry a human-placed calibration (`"_exact": true`). Running the detector's own
accept criteria on the human's court removes all guesswork — no search, no ranking, just
"can these criteria recognise the correct answer when handed it".

```
clip                   verdict   g@truth  gate | struct match acr len  suff | what fails
A7vXlWIlyrI             vote<6     0.303  FAIL |   0.88     7   3   4   yes | g<0.33
am_hard_utr           ACCEPTED     0.314  FAIL |   1.00     8   4   4   yes | g<0.33
CYqapSq5llo             vote<6     0.490    OK |   0.88     7   3   4   yes | nothing
e8T34KoJzOw_s2          vote<6     0.486    OK |   0.88     7   4   4   yes | nothing
HoHxFSX_gLk_s1         refused     0.203  FAIL |   0.50     4   2   3   yes | g<0.33, struct<0.55
HoHxFSX_gLk_s2          vote<6     0.608    OK |   0.88     7   3   4   yes | nothing
sAjkpeRq4P4             vote<6     0.181  FAIL |   0.43     3   3   1    NO | g, sufficiency, struct
tc8CGFxyRE8             vote<6     0.440    OK |   0.88     7   3   4   yes | nothing
UHf0LeMU2pg             vote<6     0.220  FAIL |   0.50     4   2   2   yes | g<0.33, struct<0.55
uR5q2cSM6AY             vote<6     0.648    OK |   0.88     7   3   4   yes | nothing
```

> ### ⚠ FINDING A BELOW IS WITHDRAWN — corrected 2026-08-24
>
> **It measured our labelling, not the criteria.** Every number in it scores the
> scorer at the human's four clicked corners, *exactly*. But the gate does not define
> "correct" as those exact corners — it defines correct as **within 20 px at 640
> wide**, the empty band between accepted courts (3.4–13.9 px) and refused ones
> (25.5–111 px). The clicks are one sample from that neighbourhood and, measured, not
> the best-registered one.
>
> `eval/truth_neighbourhood.py` swept the courts still inside the gate's own 20 px
> definition. At a median **5.8 px** from the human clicks:
>
> | | at the clicks | best court the gate still calls correct |
> |---|---|---|
> | clears the 0.33 accept gate | 5/10 | **9/10** |
> | margin over the best wrong court positive | 8/10 | **9/10** |
> | median margin | +0.126 | **+0.210** |
>
> So "the criteria refuse the right answer" is **false on 9 of 10 clips**. The
> criteria recognise the correct court; they were being handed a slightly
> mis-registered version of it. `am_hard_utr` is the sharpest case *in reverse*: its
> three per-frame locks all land within 20 px of the human court **and outrank it**,
> so the detector's snap is better registered to the paint than the clicks are.
>
> One clip survives the correction: **`UHf0LeMU2pg`** (best 0.279, margin −0.014).
>
> Read finding B, and the search, as the live problem. Evidence:
> `data/output/truth_neighbourhood.{log,json}`, `candidate_audit.log`.

**There are two different failures, five clips each.**

**A. The accept gate rejects the correct court (5 of 10).** ~~g at the human's own court is
**0.18–0.31 against a 0.33 bar**. No amount of better searching fixes this — the criteria
refuse the right answer.~~ **WITHDRAWN — see the box above.** `am_hard_utr` is the sharpest
case: the true court scores 0.314 and *fails*, yet the clip is ACCEPTED, so what shipped is
a court scoring higher than the truth. ~~That is the accept rule preferring a near-miss to
the correct answer~~ — corrected: the "near-miss" is inside the gate's own tolerance and is
*better* registered than the clicks, which is why its measured error is 14.3 px rather
than ~0.

**B. The correct court passes every gate and still is not found (5 of 10).** g = 0.44–0.65,
structure 0.88, sufficiency satisfied — and the clip reaches only 2–4 of 8 votes. Here the
scoring is fine and the search or its ranking is the problem.

So "what is going wrong" has no single answer: **half the failures are scoring, half are
search.** Any fix aimed at only one of them addresses at most half the gap, which is worth
knowing before Stage 2 is scoped.

## 4. On "more of the court shown does worse"

The court gold set **cannot test this** — all 20 clips show 94–100% of the court, so there
is no variation on that axis. What does vary is how much of the *frame* the court fills,
and on the gold set that is predictive: accepted clips occupy **0.21–0.40** of frame area,
and **every clip below 0.21 is refused (4 of 4)**, as is the one at 0.57.

Among the ten reference clips the split leans the same way — the five scoring-failures sit
at a median near-baseline width of 0.54 of frame width against 0.61 for the five
search-failures, i.e. the further-back framings are the ones whose true court fails the
agreement gate. **With five clips per group that is a lean, not a result**, and the zoom
experiment above shows apparent size is not itself causal. Treat the observation as
directionally supported and not yet explained.

## 5. A separate defect found on the way

`autodetect`'s coarse grid searches far-half-width over **0.20–0.42 of frame width**.
Measured from human corners across 30 courts (20 gold clips + 10 reference calibrations),
real courts sit at **0.09–0.22** — **30 of 30 fall outside the grid's range**. The grid is
largely searching poses that do not occur; the learned prior is doing the seeding work,
which is consistent with it failing wherever the prior has no coverage. Not fixed here —
recorded as the concrete thing to change first if search is the half being attacked.

---

## 6. The seed-grid fix was BUILT, MEASURED and REJECTED — and it reprioritises the work

Section 5 said the coarse grid searches far-half-width 0.20–0.42 and near-half-width
0.40–0.72 while all 30 human-measured courts sit at wf 0.09–0.22, wn 0.40–0.85. That is a
defect, not a preference, so it was fixed and measured. The grid was hoisted to
`courtfit.COARSE_GRID` (pure refactor: the baseline arm below reproduces the committed
scorecard exactly) and three arms were run, one variable at a time.

**Gate, pre-registered before the first run:** accepted must stay ≥ 11 of 20 **and** zero
accepted court may exceed 20 px. Buying recall with a wrong court fails.

```
arm       accepted  median   range      wrong (>20px)                         verdict
baseline    11/20    8.3 px  3.4-13.9   none                                  PASS
A_wf        13/20   10.0 px  3.4-77.7   am_beginner 26.1, am_indoor_hard2 77.7  FAILS
B_wn        12/20    8.3 px  2.9-25.3   am_beginner 25.3                      FAILS
C_both      12/20    8.4 px  2.9-25.5   am_beginner 25.5                      FAILS
```

**All three fail. Nothing ships; `COARSE_GRID` keeps its shipped values.**

The mechanism worked exactly as predicted — no arm loses a single existing clip, and the
widened grid does reach clips the old one could not. **Every clip it newly reaches, it gets
wrong.** `am_indoor_hard2` at 77.7 px is not a near miss; it is a different rectangle.

This would have been **the first wrong court ever auto-accepted on this gold set**
([court_consensus_bar.md](court_consensus_bar.md)), which is precisely what the gate was
written to prevent.

### What it means — the scoring is the binding constraint, not the search

Section 3 split the failures five/five between "the gate rejects the true court" and "the
true court passes but is not found", and called the second half a search problem. **This
result corrects that reading.** When the search is extended to reach those courts, what it
finds and accepts is wrong — so on those clips the scoring cannot separate the true court
from a wrong one either. The search was not the thing holding them back; it was hiding a
scoring failure behind a reachability failure.

So the useful ordering is now: **fix the agreement score first.** Widening the search
before that actively costs precision, and precision is the one thing this detector has
never spent.

---

## 7. The mask fix: built, measured, REJECTED. And the proxy did not predict the product.

Section 6 concluded the agreement score is the binding constraint. So a candidate mask was
built (`eval/masks_candidate.py`, never in `backend/`) and measured two ways.

### The proxy said it worked

`eval/score_truth.py` scores the criteria at 30 HUMAN-placed courts, search-free, and
reports the margin over the best wrong candidate from the shipped grid.

| mask | truth outscores every distractor | median margin | g@truth below the 0.33 gate |
|---|---|---|---|
| white (shipped) | 25/30 | +0.214 | **11/30** |
| `_clay_mask` | 26/30 | +0.201 | 11/30 |
| CLAHE only | 28/30 | +0.239 | 4/30 |
| chroma only | 28/30 | +0.213 | **3/30** |
| both | 28/30 | +0.197 | 4/30 |
| **neither** | 25/30 | +0.214 | **11/30** |

Clay clips scoring literally **0.000** at the human's own court (`am_lk35`,
`am_rally32short`) reach 0.20-0.32. **CHROMA AND CLAHE ARE REDUNDANT SUBSTITUTES** - either
alone gives the whole gain, both gives nothing more, neither gives exactly the baseline.
Reading the single ablations alone said "neither matters", which was an artefact of
removing one while the other still covered for it. Only the joint removal separates them.

### The product gate said it did not

Same pre-registered gate as the grid sweep: accepted >= 11 of 20 **and** zero accepted court
over 20 px. Here the candidate replaces `calibration.line_ridge_mask` outright, so
`_precompute`, `_clay_mask`, `snap_to_lines`, `verify_court` and `line_distance_map` all see
it - which is what shipping would mean.

```
arm          accepted  median   range      wrong (>20px)                    verdict
baseline       11/20    8.3 px  3.4-13.9   none                             PASS
chroma_only     9/20    9.1 px  2.0-15.1   none                             FAILS (recall)
clahe_only     13/20    8.2 px  1.7-22.4   am_beginner 22.4, am_classB 22.4 FAILS (precision)
both            6/20   10.7 px  2.5-17.7   none                             FAILS (recall)
```

**All fail. Nothing ships.**

**The proxy did not predict the product, and that is the lesson.** All three candidates are
indistinguishable on `score_truth` (28/30, 3-4/30) and span **6/20 to 13/20** on the gate.
`score_truth` asks whether the criteria RECOGNISE a court handed to them; it says nothing
about what the search finds once the mask changes underneath it, nor about the four
downstream stages the mask also feeds. It is a screening tool, not a gate, and a variant
must clear the full eval regardless of how good its margin looks.

### What 22.4 px actually is - and why the gate still stands

Rendered (`eval/verdicts/gate_22px.jpg`), both 22.4 px courts are **the same court as the
human's**, slightly narrow at the near baseline, with service lines and centre line tracking
correctly. That is a loose fit, not the different-rectangle failure the 77.7 px grid-sweep
case was. The 20 px line was drawn across a gap the gold set had no data in (accepted
3.4-13.9, refused 25.5+), and this probes inside it.

**The gate was pre-registered and it fails; the line does not move after the fact.** A
principled replacement was tested rather than assumed - court-outline IoU:

```
am_beginner  clahe_only  IoU 0.842      am_ntrp50       baseline  IoU 0.714  (wrong, 66 px)
am_classB    clahe_only  IoU 0.782      am_indoor_hard2 baseline  IoU 0.641  (wrong, 86 px)
am_usta40    baseline    IoU 0.945      am_ntrp45w      baseline  IoU 0.221  (wrong, 111 px)
```

**IoU does not separate them** - 0.782 for the near-miss against 0.714 for a genuinely wrong
court, seven hundredths apart, against the 11.6 px gap the pixel metric had. So there is no
better-founded discriminator available and the pixel gate stays exactly as it is.

### The one genuine positive

**`am_rally32short` - clay - auto-calibrates in ALL THREE arms.** No clay clip has ever
auto-calibrated on this gold set before. `am_indoor_hard2` also gains in all three. The mask
work is reaching the right surfaces; it is the collateral on hard courts that fails it -
`clahe_only` loses `am_usta60`, `chroma_only` loses four, `both` loses seven.

The next candidate should therefore be **additive, not a replacement**: keep the shipped mask
where it already works and fuse the new channel only where the shipped one has no evidence.
Every arm here swapped the mask globally, which is why each bought clay and paid in hard courts.

---

## 8. SHIPPED: surface routing. 11/20 to 12/20, nothing lost, zero wrong.

The user's proposal, and the first change in this line of work to clear the gate:
**judge the surface, then use the mask built for it**, instead of finding one mask that
serves every surface. Sections 6 and 7 each failed by trading gains on one surface for
losses on another; routing removes that mechanism, because a non-clay frame takes a
bit-identical path.

### The surface is separable from colour alone

Measured over 31 recordings against the eyeball labels in `eval/clip_classes.json`, in
OpenCV Lab where 128 is neutral:

```
clay    a* 148.0-163.5      everything else tops out at 132.0   -> 16 units clear
shell   L* 170.0-176.5      hard courts top out at 163.0        ->  7 units clear
hard    a* 112.5-131.5
```

`CLAY_A_STAR = 140.0` sits in the middle of the clay gap: **3 of 3 clay gold clips
called correctly, zero false positives on the other 17**, and 9 of 9 on the wider set.

**Shell is deliberately NOT special-cased.** It was measured to work already —
`gold_shell` auto-calibrates at 8/8 votes — because a pale surface still yields a
luminance ridge. Only clay lacks one. That is one fewer detector than the proposal
called for, on evidence.

### Routing to the EXISTING clay mask does nothing

Measured first, because it was the cheapest thing to try: identical to baseline,
gained none, lost none. `autodetect` already falls back to `_clay_mask` when the
white path fails, so promoting that fallback to a route changes no outcome. What was
needed was a better clay mask, not a better time to reach for the old one.

### The gate

```
                       accepted  median   range      wrong (>20px)  verdict
baseline                 11/20    8.3 px  3.4-13.9   none           PASS
routed, clay=chroma      12/20    8.1 px  2.0-13.9   none           PASS
routed, clay=CLAHE       12/20    8.1 px  1.7-13.9   none           PASS
```

Both gain `am_rally32short` and lose nothing. **Re-run against the shipped code path —
named call sites, not the monkeypatch the sweep used — reproduces exactly: 12/20,
median 8.1, range 1.7-13.9, zero wrong.**

### CLAHE beats chroma on the clay footage outside the gold set

Seven fixed-camera clay recordings in `eval/frames`, no ground truth, so lock/votes only:

```
                 baseline          chroma            CLAHE
gold_clay        1/8 lock  1v      8/8  8v ACCEPT    8/8  6v ACCEPT
tnxkujogch4      0/8 lock  0v      8/8  8v ACCEPT    8/8  7v ACCEPT
sAjkpeRq4P4      8/8  6v ACCEPT    8/8  5v  LOST     8/8  8v ACCEPT
                 1/7 accepted      2/7               3/7
```

`tnxkujogch4` goes from **0 of 8 frames locking to 8 of 8**. Chroma *loses*
`sAjkpeRq4P4` (6 votes to 5), so CLAHE ships.

All three accepted courts were rendered and checked by eye
(`eval/verdicts/clay_accepted.jpg`): the overlay sits on the real clay lines,
service boxes and centre line included. They are correct courts, not consensus
on a wrong one.

### Two honest limits on the size of this

**The three accepted clay clips look like one club** — the same house, windbreak and
treeline appear in all three. So "3 of 7" overstates the independence; read it as one
venue family now working where none did. The gold-set gain (`am_rally32short`) is a
genuinely separate venue.

**It is one clip on a 20-clip gate.** Real, reproduced, verified — and small. The
broader clay evidence (total votes across the 7 drop clips 15 -> 27, 5 of 7 improving)
is what suggests it is an effect rather than a lucky clip, and two of those seven got
slightly worse.

---

## 9. Surface routing across ALL 54 recordings, and against the human references

The gate is a 20-clip set. This is what routing does everywhere else.

### The 54 recordings (votes only - no ground truth here)

```
                                     baseline    routed
ALL 54 recordings                    17/54  ->  19/54    gained gold_clay, tnxkujogch4   lost none
  fixed camera (the product's input) 17/43  ->  19/43    39.5% -> 44.2%
  broadcast                           0/10  ->   0/10    unchanged
  surface: clay                        1/7  ->    3/7
  surface: shell / pale                2/4  ->    2/4    unchanged
  surface: indoor                      2/6  ->    2/6    unchanged
  surface: night floodlit              2/3  ->    2/3    unchanged
  surface: very low mount              2/4  ->    2/4    unchanged
```

**Not one clip anywhere lost acceptance.** Every non-clay surface is bit-identical,
which is the routing design working exactly as intended and not a happy accident.

**Broadcast stays at 0 of 10, as predicted.** It fails for a different reason - three
hypotheses were tested there (seeding, apparent court size, camera-angle selection) and
none implicated the mask, so a mask fix was never going to move it.

### Measured against the ten human-placed calibrations

The stronger evidence, because these are real pixel errors rather than vote counts, and
because these clips have hand calibrations *precisely because auto-detection failed on them*.

| clip | baseline | routed |
|---|---|---|
| **sAjkpeRq4P4** (clay) | 4 votes, refused, 11.4 px | **ACCEPTED, 6 votes, 2.3 px** |
| CYqapSq5llo (clay) | 51.6 px | **16.9 px** — 3x better fit, still refused |
| am_hard_utr | ACCEPTED 14.3 px | unchanged |
| the other seven | — | unchanged |

Accepted 1/10 -> **2/10**, and **2.3 px@640 is tighter than any court in the gold set's
accepted band**, which starts at 3.4. Nothing regressed.

### What it costs, stated plainly

Two clay clips lose votes without losing acceptance: `CYqapSq5llo` 3 -> 2 and
`SgZpQtiTG1A` 3 -> 1 (the latter now reaches a court only through the stacked-clay
rescue). Against that, `tnxkujogch4` gains 7 votes from zero, `gold_clay` 5, and
`sAjkpeRq4P4` 2. Five of eight clay recordings improve, two get worse, one is flat.

The clay gain is real but concentrated: `gold_clay`, `tnxkujogch4` and `sAjkpeRq4P4`
share a house, a windbreak and a treeline and are very likely **one club**. Read the
clay result as one venue family plus `am_rally32short` on the gold set, not as five
independent venues.

---

## 10. CORRECTION: the gold set and the drop set are NOT independent populations

Found while rendering the before/after pictures - the `am_rally32short` panel showed the
same venue as the drop-set clay clips, which contradicted what section 9 claimed.

**`data/gold/am_rally32short.court.manifest.json` records its source video as
`data/amateur_clips/yt_tnxkujogch4.mp4`.** It is not a similar court, it is the SAME
RECORDING as drop group `tnxkujogch4` - dHash 3 bits apart, where identical scenes are 0-4.

Checking every gold manifest: **9 of the 20 court gold clips share a source video with the
54-recording drop set.**

```
am_beginner          == drop 'QsO90orMfWM'      am_ntrp45_courtlevel == drop '0genZFgM61E'
am_classB            == drop 'esnrHQhCIxQ'      am_rally32short      == drop 'tnxkujogch4'
am_college           == drop '5VUiurUhSRY'      am_rec30             == drop 'rNMc9tpWWZ0'
am_ntrp30            == drop 'deNCnfQjfoU'      am_usta45            == drop 'ihXS4IDvF0A'
am_ntrp40            == drop '4apx6gd5Uxs'
```

**This is trap T17 recurring** - a clip renamed on the way into the gold set, and identity
matched on filename. `eval/collect_frames.py` deduped by filename and YouTube id, which
correctly merged trims within the drop set but could not see that a gold clip called
`am_rally32short` is a file called `yt_tnxkujogch4.mp4`. The gold manifests record the
source and were never consulted.

### What this corrects

**Section 9's claim that "the gold-set gain (`am_rally32short`) is a genuinely separate
venue" is WRONG.** It is the same recording as the drop-set gain `tnxkujogch4`. The gate
gain and one of the two breadth gains are the same footage counted twice.

Restated honestly, surface routing newly accepts **two distinct recordings**:

* `tnxkujogch4` / `am_rally32short` - one recording, appearing in both sets
* `gold_clay` - a different recording, but by eye the same club (shared house, windbreak,
  treeline; sig distance 5.9 to `tnxkujogch4`)

plus `sAjkpeRq4P4` improving on the same club (6 -> 8 votes on the drop frames; on the
human reference, refused at 11.4 px -> **accepted at 2.3 px**).

**So the clay evidence is essentially one club, not five venues.** That is a materially
smaller claim than section 9 made.

### What it does NOT change

The gate result stands on its own terms: **12/20 accepted, nothing lost, zero wrong
courts**, reproduced against the shipped call sites. Non-clay surfaces remain
bit-identical by construction and no clip anywhere lost acceptance. The 2.3 px fit on
`sAjkpeRq4P4` is measured against a human placement and is real.

What is weakened is the *breadth* of the evidence, not its correctness. Two distinct
recordings at one club is thin support for a general clay fix, and the honest next step
is clay footage from venues this club has nothing to do with.

### The fix to the harness

Any future population split must key on the gold manifest's `video` field, not on clip
names. Until that lands, treat "gold" and "drop" as overlapping by 9 recordings and do
not quote them as independent confirmation of each other.

---

## 11. FIXED: recording identity now comes from the source video, not the clip name

Section 10's correction, made structural.

`eval/recordings.py` resolves every gold clip and every drop group to a canonical
**recording key** derived from the source video the gold manifest records, and exposes
`overlap()` and `independent_drop_groups()`. `eval/run_eval.py --drop` now prints the
independent subset alongside the full one and names what it excluded;
`eval/collect_frames.py` prints the same warning at collection time, so the overlap is
visible without reading a document. Four tests in
`backend/tests/test_recording_identity.py` fail if identity regresses to clip names, if
the overlap stops being reported, or if a streamed clip is given a local key it cannot have.

### The corrected numbers

```
population                            baseline  routed   gained
ALL 54 (double-counts 9)                17/54    19/54   gold_clay, tnxkujogch4
INDEPENDENT of the gold set (45)        10/45    11/45   gold_clay
```

**Two figures reported earlier in this session are wrong and are corrected here:**

* the breadth gain is **+1 independent recording, not +2** — `tnxkujogch4` is the gate
  gain `am_rally32short`, so it was counted twice;
* the drop set's baseline acceptance is **10/45 = 22.2%, not 17/54 = 31.5%**. The nine
  duplicates are gold clips and seven of the nine already pass, so removing them lowers
  the rate rather than leaving it flat.

Eleven gold clips are `youtube-stream` with no local file and are genuinely independent
of the drop set; the overlap is confined to the nine built from `data/amateur_clips/`.

### What it does not change

The gate is unaffected — it was always the 20 court gold clips alone, never a mixture,
so **12/20 accepted, nothing lost, zero wrong** stands exactly as measured. So does the
2.3 px fit on `sAjkpeRq4P4`, which is a pixel error against a human placement rather than
a population statistic.

What shrinks is the independent support for the clay work: **one recording beyond the
gate, at the same club as the gate's own gain.** Clay footage from unrelated venues is
now the single thing that would move this from "works on one club" to "works on clay".

---

## 12. WITHDRAWN: "shell already works". On the real target footage it is 0 of 5.

Five new Philippine shell recordings arrived (Manila Polo Club, Flexi League,
Hillsborough) — 4K, 20–39 min, indoor, dim, faded lines. They were cut into 58 clips
by `tools/split_by_serve.py` and grouped back to **5 recordings** via
`data/incoming/lineage.json`.

### The result

```
recording      frames locked votes   result
71sXQ2mCbCo         6      3     1   refused     (flexi_joy)
kYI7HjYBwC0         8      3     1   refused     (mpc_mixed)
l4CAptCem88         8      7     1   refused     (flexi_franz)
NL57h6vMKPQ         8      0     0   refused     (mpc_tuesday)
o5uCLE930FU         6      2     1   refused     (hillsborough)
```

**0 of 5.** `l4CAptCem88` locks 7 of 8 frames and still scores 1 vote — the detector
fires and finds a *different* court every frame. `NL57h6vMKPQ` locks nothing at all.

### What this withdraws

Section 8 shipped surface routing with the claim that **shell needs no special case,
measured at 2 of 4 with `gold_shell` at 8/8 votes**. That was four clips, and they were
all *bright* pale courts. The footage this project actually targets — Philippine indoor
shell — is **0 of 5**. The claim is withdrawn: it was true of the sample and false of
the population.

### And the surface classifier does not generalise either

`court_surface` called **all five "hard"**. `SHELL_L = 166` was fitted to four bright
clips (L\* 170–176); these indoor courts measure **L\* 119–164**, and Manila Polo sits at
**a\* 137 against a clay line of 140**. The rule captures "bright and pale", not "shell".
The 7-unit margin flagged as thin in section 8 is now simply broken.

**It costs nothing today** — shell and hard route to the same mask, so a misclassification
changes no behaviour. But the rule must not be trusted if shell ever gets its own mask.

### The cause is NOT the surface — the mask already has the lines

Rendered (`eval/verdicts/shell_fail.jpg`), the masks contain the court clearly: baselines,
service lines and sidelines are all traced. What drowns them is the **building** — roof
trusses, strip lights, mesh fence lattice, chairs, railings. Mask sizes are 395k–1,257k
pixels and `_detect_lines` returns 16–40 distinct lines, of which the strongest are
architecture, not paint.

**This is failure family 2 from section 3** — "architecture outcompetes the paint", first
seen on `am_ntrp45w` (indoor, 111 px wrong). These five are that case in force.

So a better *shell mask* would not fix them, because the mask is not what is failing.
The next lever is line **selection**: the court is on the ground and the trusses are above
the horizon, so position relative to the ground plane separates them, and nothing in
`_detect_lines` currently uses it.
