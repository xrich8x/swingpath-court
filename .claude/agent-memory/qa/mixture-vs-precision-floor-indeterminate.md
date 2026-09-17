---
name: mixture-vs-precision-floor-indeterminate
description: The §4.1 modality falsifier ran 2026-09-09 and returned INDETERMINATE (strict-16 4 MIX / 1 PF / 6 IND vs a >=6 bar); all mixture support is 1920-wide, zero on 4K shell, and the bar has an all-singleton specification gap
metadata:
  type: project
---

Ran researcher's pre-registered §4.1 modality test (single-linkage on per-frame court
quads at 12 px@640) on 2026-09-09. Evidence:
`docs/evidence/mixture-vs-precision-floor.md`.

**Result: INDETERMINATE.** strict-16 measurable n=11 -> MIXTURE 4 / PRECISION FLOOR 1 /
INDETERMINATE 6, against a bar of >=6 of ~12 for either reading. Pooled 20 (n=15
measurable): 5 / 1 / 9. **The kill condition did not fire** — this neither closes nor
confirms the classical-court-path ceiling.

**Why:** the pre-registered gate was mis-specified for wide scatter, and the population
cannot support the question where it matters.

- **All 5 MIXTURE verdicts are 1920-wide clips; 0 of 5 measurable 3840 shell clips.** The
  observation the mixture reading was invented to explain (29.9/31.9/36.3/37.5 px@640) is
  3840-wide. Do not carry a mixture conclusion onto shell.
- **The 4 motivating static tripods barely exist as data.** `flexi_joy_p01` locks 2 of 8
  frames, so its 29.9 px figure is **a single pair**; `hillsborough_p02` and `_p08` rest on
  3 pairs each. Any future claim resting on those four needs the pair count stated.
- **ALL-SINGLETON is the gap:** 4 clips have no two frames within 12 px, so within-cluster
  median is undefined and they satisfy neither branch. A sigma~30 scatter produces exactly
  this under a 12 px linkage — the PF branch ("exactly 1 cluster") assumed a scatter would
  link into one cluster. Unresolved; flagged, not patched.

**Why:** a pre-registered bar written from a summary artefact can be unrunnable as written.
**How to apply:** before honouring an inherited bar, check the artefact it names actually
holds the quantity it assumes — `interframe.json` was cited as storing "all pairwise
distances per clip" and stores only per-clip medians/maxima, so every quad had to be
recomputed (which reproduced run 4's `D_raw` to 2 dp — see
[synth-truth-harness-reproducibility]]).

Related: [[camera-motion-vs-court-agreement]], [[court-proposal-recall-search-binds]],
[[clip-shot-map-single-setup]].
