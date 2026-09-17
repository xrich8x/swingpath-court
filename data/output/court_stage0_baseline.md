# Court detection Stage 0 — the harness, the baseline, and what the failures actually are

`eval/run_eval.py` runs the shipped court path (`courtfit.auto_fit_frame` per frame →
`consensus` → `stacked_clay_fit` rescue — exactly `pipeline.calibrate_video` Tier 1) over
the 20 hand-labelled court gold clips, and writes a three-panel diagnostic overlay per
frame to `eval/out/`. Built before any change to the detector, so every later stage has a
before.

```
backend/.venv/Scripts/python.exe eval/run_eval.py --gold --k 8
```

## The baseline reproduces the shipped scorecard

Measured against the human clicks in `data/gold/*.court.labels.json`, k=8 frames per clip.

```
clip                     frames locked  votes    result consensus_px
am_beginner                   8      8      4    vote<6         30.1
am_classB                     8      7      6  ACCEPTED          8.3
am_college                    8      8      8  ACCEPTED         13.9
am_fr_sud                     8      8      8  ACCEPTED         10.9
am_grass1                     8      7      6  ACCEPTED          6.3
am_indoor_hard1               8      3      2    vote<6         24.9
am_indoor_hard2               8      8      4    vote<6         86.0
am_lk35                       8      2      1       stk         15.6
am_ntrp30                     8      8      8  ACCEPTED          6.2
am_ntrp40                     8      8      8  ACCEPTED          7.9
am_ntrp45_courtlevel          8      8      8  ACCEPTED         12.4
am_ntrp45w                    8      8      3    vote<6        111.0
am_ntrp50                     8      8      5    vote<6         69.1
am_rally32short               8      0      0   refused            -
am_rec30                      8      8      7  ACCEPTED         12.0
am_usta40                     8      8      8  ACCEPTED          5.7
am_usta45                     8      8      7  ACCEPTED          9.1
am_usta45final                2      1      1   refused            -
am_usta60                     8      8      6  ACCEPTED          3.4
am_wingfield_clay             8      3      1   refused            -
--------------------------------------------------------------------
ACCEPTED 11/20   median 8.3 px (range 3.4-13.9)   WRONG (>20px) 0
```

**11 of 20 accepted, 3.4–13.9 px, zero wrong** — clip-for-clip agreement with
[court_consensus_bar.md](court_consensus_bar.md), which was produced by a different tool
(`tools/eval_court_consensus.py`). Two clips differ by 1–2 px because that tool medians
error over *all* labelled frames while this one uses the 8 it sampled. **The agreement is
the point**: this is a second scorer that does not disagree with the first, which is the
failure this project has hit before (trap T15).

`WRONG_PX = 20.0` is not a taste call — accepted courts occupy 3.4–13.9 px and refused
ones 24.9–111.0 px, with nothing between. The line sits in the empty gap. **Zero accepted
courts above it is the precision record every later stage must not spend.**

## The premise this work started from is wrong

The brief assumed the detector depends on all four court corners being visible. It does
not: corners are a *parameterisation* (`courtfit._corners`, then a 6-DOF physical camera
re-fit), projected rather than found, and free to land off-frame.

Counted over the gold labels — how many labelled frames have at least one doubles corner
outside the image:

| | clips | with off-frame corners |
|---|---|---|
| ACCEPTED (11) | 11 | **9** (up to 224 px outside) |
| refused / wrong (9) | 9 | 6 |

**9 of the 11 clips that auto-calibrate today have off-frame corners**, and the clip the
split file calls "the hardest mount" (`am_ntrp45_courtlevel`, court-level camera) locks
**8/8 at 12.4 px**. Meanwhile **both hard refusals have all four corners in frame**. Corner
visibility does not predict failure and neither does low mount on its own. Corner-dependent
code does exist — `calibration.detect_court` — but it is Tier 3 and effectively dead.

## What the failures actually are — three families, from the overlays

The overlay is three panels: frame + fit + GT | `line_ridge_mask` (the default white
channel) | `_clay_mask` (the hue-agnostic retry). The middle/right pair is the diagnosis.

**1. Clay — the mask fires almost entirely OFF the court.** `am_wingfield_clay` f00552:
white-ridge mask has 3,092 px and 5 lines, and essentially all of it is foliage and fence
at the top of the frame; the court region is empty, though the lines are plainly visible to
a human. `am_rally32short` f00585 is the same, 3,185 px, all background. Both hard refusals
are clay, and `am_lk35` reaches a court only through the clay stack rescue.

This is not "the mask sees nothing", it is "the mask sees the wrong things". The court-line
signal on clay is *chroma* (whitish paint on orange), and `line_ridge_mask` discards it at
`sat < 90` while its luminance-ridge test fires happily on tree and fence edges. **CLAHE
alone would not fix this** — more contrast on a channel that has already thrown the paint
away buys nothing. Chroma has to enter the mask.

**2. Low indoor — architecture outcompetes the paint.** `am_ntrp45w` f01890 (111.0 px, the
worst wrong court on the set): the white mask holds 16,502 px / 29 lines dominated by
**rafters, ceiling strip-lights and the top edge of the green curtain** — long, strong,
near-horizontal, far better contrast than the court. The fit collapses the whole 23.77 m
court onto the curtain band near the horizon. It locks on 8 of 8 frames, so it is confident
and wrong; only the 6/8 *agreement* rule saves it, and it survives the existing degeneracy
floor (`p5[3]*2 < 0.15w or |p5[1]-p5[2]| < 0.06h`) by being just wide and tall enough.

**3. Marginal agreement.** `am_beginner` (4 votes, 30.1 px), `am_ntrp50` (5 votes, 69.1 px),
`am_indoor_hard1` (2 votes, 24.9 px) lock on most frames but do not agree. Not yet
characterised from the overlays.

## What this says about the plan

The bottleneck is **refusal on faded and cluttered surfaces**, and it is a *mask and
acceptance* problem, not a corner-geometry problem and not (per Session H part 2) a model
problem. Stage 2 targets family 1 (chroma fusion, local contrast, large-gap merging);
family 2 says a distractor-rejection stage has to survive strong non-court horizontals,
which is the same requirement multi-sport overlay lines impose.

## Not measured here

No clay or shell frames beyond `am_wingfield_clay` and `am_rally32short` carry court
labels; `data/gold_clay.mp4` and `data/gold_shell.mp4` are **ball**-labelled only. Frames
dropped into `eval/frames/` have no ground truth at all — lock/refuse and the overlay are
the only honest signals there, and `run_eval.py` prints `-` rather than a number.
