# Court detection across ALL 54 recordings in the repo

Stage 0 measured the detector on the 20 hand-labelled court gold clips (11/20 accepted,
[court_stage0_baseline.md](court_stage0_baseline.md)). This widens it to **every video in
the repo** — 66 files, deduped to **54 distinct recordings** — to see whether the picture
holds outside the set every threshold was tuned against.

```
backend/.venv/Scripts/python.exe eval/collect_frames.py --n 8 --sheets
backend/.venv/Scripts/python.exe eval/run_eval.py --drop --k 8 --verdict-sheets
backend/.venv/Scripts/python.exe eval/run_refs.py
```

## How the set was built, and what it is not

`data/train_clips/*.mp4` were cut from `data/incoming/*.mp4` (`lineage.json`), so files
were grouped by **recording** — a trim and its source are the same court, and counting
both would inflate any rate by duplicating easy cases. 66 files → 54 recordings.

**Court-in-view was decided by a human reading contact sheets**, never by the detector.
Selecting the test set with the thing under test would make every survivor pass by
construction. The first uniform-sampling pass returned tweet screenshots, talking heads
and crowd shots from vlogs and highlight reels, so frames are now chosen by **dominant
camera view** — cluster candidates by coarse appearance, keep the largest cluster. That
asks "what does this video mostly look like", never "is there a court here". It is a
no-op on fixed-camera footage; on `BwLUgip8OSI` it went from 2 court frames in 4 to 8 in 8.
Verdicts are recorded in `eval/clip_classes.json`.

**A failed attempt worth recording:** a frame-appearance-spread metric was tried as an
automatic way to flag multi-venue files. It ranked `uOy8ow5yoQ4` — visibly five different
venues — *below* `bump_ntrp30`, a single static court. It was measuring lighting drift,
not venue change, and was dropped rather than reported.

## The denominator has to be split, because the vote's premise is not universal

The shipped accept rule is a **≥6-of-8 frame consensus**, which assumes one fixed camera
on one static court. Broadcast footage violates that by construction (baseline cam, serve
cam, close-ups) and a compilation violates it absolutely.

| class | n | accepted | locked ZERO frames |
|---|---|---|---|
| **fixed camera** — the product's actual input | 43 | **17 (39.5%)** | 2 |
| broadcast — one venue, several cameras | 10 | **0** | 9 |
| multi-venue compilation | 1 | 0 | 1 |
| all | 54 | 17 (31.5%) | 12 |

**Broadcast is a total failure and a clean one: 0 of 10, with 9 locking not one frame.**
That is not the vote failing to agree — the detector never fires. Tier 1 is tuned for
amateur uploads; the learned Tier 2 path exists for broadcast framings. Worth stating
plainly because "0/10" looks alarming until you notice it is out-of-scope footage.

On the product's own footage: **39.5% vs 55% on the gold set** — the gold set is easier
than the repo at large, which is what a set every threshold was tuned against would look like.

## By surface (fixed-camera clips only)

| surface | accepted | note |
|---|---|---|
| clay | **1/7 (14%)** | the worst surface, and 2 of 7 lock zero frames |
| shell / pale | **2/4 (50%)** | *better than clay* — see below |
| indoor | 2/6 (33%) | |
| night floodlit | 2/3 (67%) | |
| very low mount | 2/4 (50%) | including `am_hard_utr` at 1.74 m |

**Clay is confirmed as the binding surface problem; shell is not.** That reverses the
prior expectation. `gold_shell` accepts at 8/8 votes and `rNMc9tpWWZ0` at 7/8, so
white-on-light is *not* where this breaks — the pale surface still gives a luminance ridge.
Clay does not, because its line signal is chroma and `line_ridge_mask` discards it at
`sat < 90`. Stage 2 should target clay and stop assuming shell needs the same fix.

## Precision: measured, not assumed — on 10 clips with a human reference

The 54 have no ground truth, so a pass rate can only say "it locked". Ten clips carry a
`data/<clip>_pts.json` with `"_exact": true` — `pipeline.calibrate_video`'s own marker for
"the user deliberately placed these corners" in the Court Setup tool. That is a human
placement. `data/eala_pts_auto.json` is excluded by name and by rule: scoring the detector
against a court the detector produced is self-grading.

Errors normalised to 640-wide so they compare to the gold set's accepted band of 3.4–13.9 px.

```
clip                   lock votes    result  err@640
A7vXlWIlyrI            6/8      2    vote<6     21.5
am_hard_utr            8/8      7  ACCEPTED     14.3
CYqapSq5llo            8/8      2    vote<6     51.6
e8T34KoJzOw_s2         8/8      2    vote<6     17.9
HoHxFSX_gLk_s1         4/8      1   refused        -
HoHxFSX_gLk_s2         8/8      3    vote<6     32.8
sAjkpeRq4P4            8/8      4    vote<6     11.4
tc8CGFxyRE8            7/8      3    vote<6     59.6
UHf0LeMU2pg            7/8      3    vote<6     55.0
uR5q2cSM6AY            8/8      3    vote<6     20.8
```

**The one acceptance is correct** — 14.3 px, against a wrong-court band that starts at
25.5 px. **And the nine refusals are right to refuse**: five would have been wrong by
20.8–59.6 px had the bar been lower. The ≥6-vote rule earns its keep here on footage it
was never tuned on. `sAjkpeRq4P4` (4 votes, 11.4 px) is refused conservatively — a correct
court thrown away, which is the cost side of the same rule.

**Do NOT read 1/10 as a recall rate.** These ten clips have a hand-placed calibration
*because auto-detection failed on them* — the `_exact` flag specifically marks the
shape-lock-OFF save used when no pinhole view fits. The set is selected for difficulty.
The honest recall figure is the 17/43 above.

## One retraction

An earlier read of this run called `am_hard_utr`'s accepted court a wrong "half-court"
lock, from the overlay picture. **Measured against the human placement it is 42.9 px on a
1920-wide frame — the same court**, with near-baseline width matching to 0.7% (2132 vs
2147 px) and far-baseline y to 5 px. The overlay looked wrong because a 1.74 m mount
foreshortens the far baseline to near the net's apparent height, exactly as CLAUDE.md
documents. **An overlay eyeball could not separate a correct low-mount fit from a
half-court error; the reference could.** The other 16 acceptances remain unverified —
they have no reference, and after this, eyeballing them is not evidence.

## Not measured

No pickleball or multi-sport-overlay footage exists in the repo, so that requirement is
still unverifiable. Grass appears only in broadcast clips, so it has no fixed-camera
number. `tennis_sample_short` yielded 3 frames after de-duplication and cannot reach a
6-of-8 vote at all.
