---
name: cleanplate-mti-near-baseline-measured
description: Clean-plate/MTI temporal integration measured against the founder's near-baseline+net-line-only court solve; weak/mixed result, protocol mismatch with backend-dev found mid-run
metadata:
  type: project
---

Measured 2026-09-06 whether `tools/eval_court_cleanplate.py`'s clean plate (per-pixel
median over a short video window) sharpens the near-baseline row/width enough to make
the founder's near-baseline+net-line-only court solve
([net-baseline-solve-without-far-line.md](../../../docs/evidence/net-baseline-solve-without-far-line.md))
clear its ≤2 px input-precision requirement. Full writeup:
[../../../docs/evidence/cleanplate-mti-measured.md](../../../docs/evidence/cleanplate-mti-measured.md).

**Headline:** only 1 of 8 double-locked clips (`am_rally32short`) got both the near-baseline
row AND width under 2 px with the plate. Row sharpening is NOT a majority win (3/7 better,
4/7 worse); width IS a majority win (5/7) but with two regressions. Net-line side is
unmeasured (see below — not actually impossible, just not done).

**T24 check (docstring self-claims):** `eval_court_cleanplate.py`'s "measured: it made
detection worse" claim traces to one real commit (`dd2369f`, 2026-07-15) with real numbers
in the commit message, not a bare fabrication — but it is STALE (predates the 2026-08-21
surface-router ship that already beats the old clean-plate number) and was never re-tracked
in STATE.md. Re-ran fresh 2026-09-06: 13/20 locked, median 8.6 px on `data/gold/*.court
.labels.json` (a DIFFERENT 20-clip pool from the precision-gate gold — same `am_*` naming
convention as both, easy to confuse, watch for this in future tasks).

**Real-recipe caveat:** only 10 of 20 clips in that pool have local video; the other 10
silently fall back to medianing a handful of JPG stills (not the n=150/span=90 recipe) when
`plate_from_video` gets a YouTube URL with no local file. Any clean-plate claim on this pool
must be scoped to the 10 local clips: am_beginner, am_classB, am_college, am_lk35,
am_ntrp30, am_ntrp40, am_ntrp45_courtlevel, am_rally32short, am_rec30, am_usta45.

**Decode cost finding:** `plate_from_video`'s n=150/span=90 recipe costs 0.16-1.87s/clip
(mean 1.36s), NOT the ~60s the "decoding a minute of video" framing implies — `cv2
.VideoCapture.set(CAP_PROP_POS_FRAMES)` seeks rather than sequentially decoding, so cost
tracks sampled-frame count, not span length.

**n-sweep finding (pre-registered "as well" bar: same lock set + within 1.0px on every
double-locked clip):** the value ACTUALLY SHIPPED in `court_setup_server.clean_plate_and_
motion` (n=80, span_s=60) FAILS this bar against the eval script's own tested n=150/span=90
— width error exceeds 1.0px tolerance on 7 of 8 double-locked clips, some by 10-30px. What
ships was not the setting that was measured. Decode saving from n=150→n=80 is only ~0.6s/
clip, trivial against the precision lost.

**Protocol-mismatch correction (important, found mid-run):** backend-dev's
`docs/evidence/near-line-detection-precision.md` appeared DURING this task with a properly
pre-registered shared protocol (units px@640, truth from `data/*_pts.json`, detection via
raw `line_ridge_mask`→`_detect_lines` matched truth-seeded) that diverges from what I'd
already measured (native-res `auto_fit`-pipeline output on a different gold pool). My
numbers answer a real but DIFFERENT question ("does the plate change the shipped court-fit
tool's output") than backend-dev's ("does the plate sharpen raw line detection"). Also
corrected my own over-claim that net-line ground truth is unmeasurable — it isn't: net
position in court metres is fixed regulation geometry and can be projected through the
human-fitted homography (same as the eval script already does for rendering); I just didn't
have that insight until reading backend-dev's file. Did not redo the measurement on the
corrected protocol this run (budget) — see [[dispatch-collision-cleanplate-task]].

See also [[no-sendmessage-tool-in-toolset]] and [[dispatch-collision-cleanplate-task]].
