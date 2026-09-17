---
name: committed-calibration-files-can-be-degenerate
description: Committed *_pts.json calibration files are not all valid — check the _audit stamp (validate_new_clip.py --stamp) before using one as a reference, especially in a name that looks like a sibling of a good one.
metadata:
  type: feedback
---

Five of the eleven committed `data/*_pts.json` files are `_audit`-stamped `DEGENERATE`
(fit residual 38–565 px, vs under 2.5 px for every good one) by `validate_new_clip.py
--stamp`. The naming actively traps you: `court_pts.json` is the bad one (38.1 px,
"corners are not a physical camera view"), `court_pts_refined.json` is the good version
of the *same clip* (2.3 px) — one word apart, easy to grab the wrong one by habit or
tab-completion. Commit `20a672e` did the stamping specifically because of this trap.

**Why this matters for parity/verification work:** `mobile/verify_live.js` was silently
reading `court_pts.json` and producing a wrong-but-plausible-looking number (6 in / 1
out). Nothing about that number looked broken — it just wasn't a real disagreement, it
was the wrong input. See [[video-free-parity-checks]] for the fix and how it was
resolved without needing to re-run anything against the video.

**How to apply:** before trusting ANY committed `*_pts.json` as a calibration input
(reference test, demo, new harness), read its `_audit` block first. `verdict:
"DEGENERATE"` or `"LOW-CAMERA"` are both real signals, not noise to strip — `LOW-CAMERA`
(e.g. `am_hard_utr`, an honest 1.74 m mount) is usable but caps what's measurable; only
`PASS` is a clean reference. If a file has no `_audit` block at all, it predates the
stamping and its quality is unknown — don't assume PASS.
