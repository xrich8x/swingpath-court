---
name: g8-far-line-audit
description: G8 far-line instrument audit 2026-09-19 — numbers reproduce, but the committed tool cannot rerun its own sweep and an undeclared 3.56x search-reach widening is what makes BAR 4 fail
metadata:
  type: project
---

Audit of backend-dev's G8 (`docs/evidence/court-camera3d.md`, commits `46e5fe7` prereg,
`f3bddd6` results). Nine claims; every published number reproduced from the raw rows or from my own
re-implementation. **Two process faults found, neither fixed by me.**

**Fault (a) — the committed tool does not run the instrument it scored.**
`tools/court_far_line_gate.py` calls `paint_check(img, cam, far_kw={...})` with no `far_lines=True`,
and `camera3d.FAR_LINES_DEFAULT` is `False`. Re-running it at HEAD gives the pre-G8 baseline in all
40 cells (catch 0.8333 flat). The artifacts were produced with the default set True in the working
tree, then the default flipped before the results commit. Numbers fine, provenance broken.

**Fault (b) — an undeclared prereg deviation is what makes BAR 4 fail.** Prereg: `reach = 3 *
far_tol` = 2.25 px@720. Code: `reach_px_720 = 8.0`, **3.56x wider**, undeclared (only the peak rule
was declared). The net tape sits 4.8-5.6 px from the far service line: inside the shipped window,
outside the registered one. On CP1 arm-P trials 0/1/2 the exact rendering camera FAILS at reach 8.0
and **PASSES at reach 2.25** (far lines go `unchecked`). Held-out catch 0.9167 (reach 8.0, reproduces
exactly) vs **0.9028** (reach 2.25) at 0 false flags both. So BAR 1/2 survive the registered reach;
BAR 4's "369 of 369" does not. The 400-trial re-run at reach 2.25 is the open experiment.

**Held-out means noise, not scene.** `cases()` renders ONE frame per seed and perturbs only the
camera; the 57-case ladder geometry is byte-equal between dev (300-305) and score (400-402).
**Effective n = 24 distinct cases, not 72**; the 6 misses are 2 geometries (pitch +/-0.05 deg), the
same 2 that miss on all 6 dev seeds. The whole gain over the pre-G8 check is **pure pitch ~0.1 deg**
(2 distinct cases). One more distinct miss and BAR 1 fails.

**Renderer fault blast radius — my ruling: QUALIFIED, nothing overturned.** Paired one-variable
control, seeds 101+201, only the render order: worst-line p90 **2.595 -> 1.479 cm** (1.76x), knock
frames **70.39/56.82 -> 62.27/49.11 cm**. G3's KILL UNAFFECTED (11-13 m). The 3.5 cm / 2.41 cm
figures are renderer-conditional and **pessimistic by ~1.8x**. Wider than backend-dev stated: the
WIDE `near_service` line's offset also moves -0.19 -> -0.09 px, so it is not a far-line-only fault.
Defaults left faulty on purpose = a live trap.

Also verified: BAR 3's A/B is genuinely one-variable (12 differing leaves in the whole file pair);
"ships OFF" is a proven no-op (worktree diff, byte-identical render, one changed field); the encoder
pin holds (cp1 4 distinct hashes / deterministic 1, and the deterministic profile runs **14.5x the
bitrate** — a number missing from the writeup); a hand-edited `lock_scope: "whole_court"` DOES
out-claim (nothing cross-checks scope against `lock_unverified`).

Related: [[tracker-fixes-hold-on-held-out-seeds]], [[g7-separation-audit]].
