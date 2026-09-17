---
name: post-loses-on-precision-not-sensitivity
description: The net-post height reference FAILED (3/11 vs a 2/3 bar) despite being 15% MORE sensitive per pixel than the tape - sensitivity and precision are different axes, and a two-object cross-check fails when the confuser spans both objects
metadata:
  type: project
---

**The net POST as a camera-height reference FAILED its pre-registered bar on
2026-09-05: 3 of 11 confident clips within 10% of fitted, bar was 2/3, n >= 6.**
The tape scores 13/15 on the same corpus with the same constants.
Evidence: `docs/evidence/net-post-detector.md`. Tool: `tools/net_post_height.py`.

**Why:** the post was ranked #1 next off-plane reference because it is rigid (no sag,
the tape's one unresolved confound). It really is 15% more sensitive per pixel —
`%/px = 100·H/(h·(ground−horizon))`, and `h` is 1.07 vs the tape's 0.914, so
`0.914/1.07 = 0.854×`. Median 1.26 %/px post vs 1.48 %/px tape, measured. **It still
lost, because sensitivity and row precision are different axes and precision
dominated**: the tape averages a long bright band over ~120 columns and lands within
2–6 px; the post is a step at the end of one short bar and landed a median **22.3 px**
from the calibration's own predicted top (n = 54 posts). ~7× worse. Confident rows were
off by +261.7%, +94.0%, −69.1%, −45.8%.

**How to apply:**
- **Price an instrument on BOTH axes before ranking it.** "More sensitive per pixel" is
  not "more precise". Ask separately: how many pixels of error does the measurement
  actually make? This is the mistake that made the post look like the best candidate.
- **A two-object cross-check is only independent if the confuser cannot span both
  objects.** P5 (the two posts must agree) was the post's headline advantage over the
  tape. It failed: a horizontal fence rail runs behind BOTH posts at one height, so both
  lock the same wrong `h'` and *agree*. 2 of the 3 clips passing P5 were grossly wrong.
  Inferred from numbers, not eyeballed — flagged in `docs/DECISIONS_PENDING.md`.
- **Framing/resolution were never the limit.** P6 (post >= 10 px tall) and P0/P1
  (pose/framing) fired **zero** times across 27 clips; posts image 18–179 px. Do not
  re-litigate post visibility — see [[net-ground-vs-net-tape]].
- **Do not "fix" it by narrowing the search range to near `h' = 1.07`.** It is choosing
  after the result AND circular: the range would be centred on the fitted height, so the
  independent check would be steered by the number it is checking.
- The tape's 10% / ~3 %-per-px bar is now the **benchmark for off-plane references**, and
  two challengers have failed it: the post (this) and gravity/arc (researcher, same day,
  ~±20% from pixel noise at these low mounts). See
  [[net-tape-height-is-precision-limited]].
