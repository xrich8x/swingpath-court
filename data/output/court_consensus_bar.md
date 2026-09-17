# Is the 6-of-8 consensus bar in the right place?

`pipeline.calibrate_video` auto-accepts a court only when `courtfit.fit_video_frames`
finds **≥6 of 8** sampled frames agreeing. The code asserted that ">=6/8 agreeing frames
has always been a correct court on the gold set + cold tests"; that had never been
verified against the court gold labels as a votes-vs-correctness pairing.

**Pre-registered gate: lower the bar to 5 only if ZERO 5-vote consensuses are wrong.**

Measured with `tools/eval_court_consensus.py --all --k 8` over all 20 court gold clips.
`err` is the median distance from the consensus court's four doubles corners to the
human-clicked corners, in the clip's own 640-wide pixels.

| votes | clips | err range | verdict |
|---|---|---|---|
| 8/8 | 6 | 5.7 – 13.9 px | all correct |
| 7/8 | 2 | 11.5 – 12.0 px | all correct |
| 6/8 | 3 | 3.4 – 8.3 px | all correct |
| **5/8** | **1** | **68.7 px** | **WRONG COURT** |
| 4/8 | 2 | 30.1 – 86.4 px | wrong |
| 3/8 | 1 | 111.0 px | wrong |
| 2/8 | 1 | 25.5 px | wrong |

Per clip:

```
8/8   am_college           13.9      6/8   am_classB             8.3
      am_ntrp45_courtlevel 12.4            am_grass1             6.3
      am_fr_sud             9.0            am_usta60             3.4
      am_ntrp40             7.9
      am_ntrp30             6.2      5/8   am_ntrp50            68.7  <- the one that decides it
      am_usta40             5.7
                                     4/8   am_indoor_hard2      86.4
7/8   am_rec30             12.0            am_beginner          30.1
      am_usta45            11.5      3/8   am_ntrp45w          111.0
                                     2/8   am_indoor_hard1      25.5
stk   am_lk35              15.6      1/8   am_wingfield_clay   refused
                                     0/8   am_rally32short     refused
```

## Verdict: GATE FAILS. The bar stays at 6.

There is exactly one 5-vote clip and it is wrong by **68.7 px** — five times the worst
error of any accepted court. Lowering the bar by a single vote would admit it.

**The separation is not close, and that is the finding.** Every clip at ≥6 votes lands
between 3.4 and 13.9 px. Every clip at ≤5 votes lands between 25.5 and 111.0 px. There is
nothing in the gap. The bar is empirically in exactly the right place, and the code
comment that asserted it is now verified rather than believed.

## What this also says

**Auto-calibration already works on 11 of 20 clips (55%), with a perfect precision
record** — no wrong court has ever been auto-accepted on this gold set. The failure mode
is refusal, not error, and refusal costs a user ~30 seconds in
`tools/court_setup_server.py`.

`am_lk35` reached a court only through the stacked clay rescue (`stk`), at 15.6 px — the
worst of the accepted set and worth watching, since the stack path has no vote count to
gate on.
