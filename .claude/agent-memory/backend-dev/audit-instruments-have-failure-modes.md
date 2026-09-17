---
name: audit-instruments-have-failure-modes
description: The corner-audit renderer showed frame 0 while the eval scores 5%-95%, and silently overwrote sheets - an audit tool's defects are findings, and both directions of error matter
metadata:
  type: project
---

Three defects found 2026-09-09 in the tools that render court calibrations for a
human to judge. Fixed the same day. The lesson outlives the fixes.

**The renderer showed a frame the scoring never looks at.**
`tools/render_corner_audit.py` defaulted to `--frame 0`; `eval/run_refs.py` scores
k=8 frames over 5%-95%. Both directions of error are live:
- false ACQUITTAL - corners fit at frame 0, miss across the whole scored band;
- false ACCUSATION - and this is the one that bit. `tools/court_setup_server.py`
  places against frame 0 **only in `--video` mode**; in GALLERY mode the image comes
  from `eval/collect_frames.py`, which SEEKS arbitrary mid-clip positions. So for
  every gallery-placed calibration the audit sheet showed a frame that is not the
  placement frame. On any clip with camera motion a CORRECT placement renders as
  wrong. The founder marked 10 of 28 sheets wrong-placed from frame-0 renders.

**Nothing in a `*_pts.json` records whether the camera moves.** One rendered frame
cannot establish it. `--eval-frames` (renders all 8) is the only instrument, and it
is a human eye, not a number.

**A tool that writes one filename per clip destroys evidence silently.** Rendering
one clip at five frames left one PNG and no error. Outputs now carry the frame
index. Any artifact a human will JUDGE must name in itself what it depicts - which
file, which frame - or the judgement cannot be re-checked later.

**Frame index is an A/B variable.** Every published `--net-anchors` number
(band_ratio, dy, tape 13/15, post 3/11) was measured at frame 0. Pass `--frame 0`
to reproduce them; a different value at the new default is a different frame, not
a changed result.

**Why:** these tools render what the founder re-reviews court ground truth with,
after trap T26 (an agent placed corners and was the sole judge of its own
placement). A defect in the instrument corrupts the re-review exactly the way
self-verification corrupted the placement, and invisibly - a broken renderer's
output looks like a working one's.

**How to apply:** before trusting any rendered audit sheet, ask which frame it
shows and whether the scoring sees that frame. Before running any eval script
here, grep `docs/evidence/` and `data/output/` for its numbers rather than
believing its docstring ([[traps-this-project-paid-for]], T24 - `candidate_audit.py`
said UNRUN while `424ecdc` had committed its own output in the same commit).
Related: [[calibration-trap-check-corners-first]],
[[court-gold-provenance-is-unattributed]].
