---
name: a-second-profile-never-an-edit
description: Determinism fixes and fidelity fixes change the SCENE; ship them as a named second profile whose default reproduces every stamped number
metadata:
  type: feedback
---

**When a fix changes what is being measured, add a NAMED SECOND PROFILE behind a flag whose
default reproduces every stamped number — never edit the existing one.** Used three times in
one task (G8, 2026-09-19) and it worked every time: `X265_DETERMINISTIC` beside `X265`,
`court_track_sim --subpixel` beside the shipped render order, `paint_check(far_lines=...)`
beside the pre-G8 check.

**Why:** the lead's instruction was explicit — "changing CRF/preset/keyint changes the SCENE,
not just its determinism" — and the numbers proved it: under the pinned encoder the
far-baseline error is 0.42-0.92 cm against the CP1 profile's 0.50-2.05 cm, because all-intra
CRF 18 is a materially easier compression. Re-basing G1/G7/CP1 onto it would have silently
improved every number. The same holds for renderer fidelity: fixing the sub-pixel render order
moved the tracker's worst-line p90 from 2.41 to 1.48 cm, which is a different scene, not an
improvement.

**How to apply:** the flag's default must be the OLD behaviour; write "NOT comparable with
<the runs>" into the profile dict itself so it travels into every stamp; pin the old argv or
old code path character-for-character with a test, so a later edit that moves a stamped number
fails loudly; and make the stamp read the RESOLVED profile, not a static preset table. Pair
this with a NULL CONTROL that must FAIL — two runs under the old profile must differ, or the
determinism test cannot see non-determinism and proves nothing. See
[[renderers-cannot-place-subpixel-paint]] and [[traps-this-project-paid-for]].
