---
name: court-gold-keypoints-are-derived
description: data/gold/*.court.labels.json "keypoints" are homography-derived from the 4 clicked corners, not human clicks — any "corners -> other landmarks" test on that pool is self-grading (P8 C2, 2026-09-16)
metadata:
  type: project
---

`tools/gold_label_server.py::cornersToLabel()` writes every non-corner `keypoint` as
applyH(H from the 4 clicked corners) rounded to 0.1 px. Invoked check: 3,300 pairs, median
0.048 px@640, p90 0.090, max 0.59 = rounding. P8 C2 ("does the four-tap model agree with human
clicks on other landmarks") was therefore NOT RUNNABLE on this pool; reported void, not PASS.

**Why:** a pre-registered test was specified against a truth set whose schema looked like
independent landmarks. Reading the WRITER of the labels, not just the reader (`eval_court.py`),
is what caught it. Tell-tale in git: frames with unchanged corners had keypoints move +-0.1 px.

**How to apply:** before scoring anything against a label file, open the tool that wrote it
and find which fields a human actually set. For this pool only `corners` (and court/unusable)
are human. Also found: agent commit `2e49f38` (2026-09-06) re-saved am_beginner (corners moved
up to 27 px) and added 15 frames to am_usta45final — provenance unrecorded.

Side check same day: demo30 (1.38 m) vs yt_match40 (1.64 m) is a QUAD disagreement (217 px@640
at near corners), not hfov — common-hfov gap stays 0.20-0.50 m. On the shared frame the current
yt_match40 file (09-05 re-click) sits on paint; demo30's near baseline is ~60 px off. T23 is
about the .bak file only. See [[synth-truth-harness-reproducibility]] for a related lesson.
Evidence: docs/evidence/court-map-gold.md.
