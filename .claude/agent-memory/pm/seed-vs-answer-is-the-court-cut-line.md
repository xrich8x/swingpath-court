---
name: seed-vs-answer-is-the-court-cut-line
description: Any point-like court estimate (keypoints, PnP, a pose-regressing network) can only ever be a SEED; only a whole-court paint fit places lines to 5 cm — and the seed floor is a measured number
metadata:
  type: project
---

**Every point-like court estimate is a SEED, never the shipped camera. The whole-court paint fit is the
only thing measured to place lines to 5 cm. Price and gate the two differently.**

**Why:** three independent measurements say the same thing.
- C1 (`docs/evidence/court-map-ceiling.md`): a court pinned by POINTS misplaces far lines by metres
  unless the points are right to ~0.1 px at 1080p / 3 m — **whoever or whatever finds them, an ML model
  included**.
- Arm K0 (`docs/evidence/court-camera3d.md` §G2): a PnP camera from 21 noisy keypoints, no paint fit,
  gives far baseline **p90 6.65 m**. Same seeds through the paint fit: **1.18 cm (M) / 4.43 cm (L)**.
- Hard rule 5: a single camera does not observe depth, it imposes it — so whatever fixes the depth
  parameter sets the far-line error, and a reprojection residual certifies nothing.

**How to apply:**
- A proposal that a network predict camera extrinsics/intrinsics *directly* as the answer is
  contradicted by a measurement. Say so plainly; do not soften it. Its viable role is a seed.
- **The seed floor is measurable and much easier than the answer floor.** Arm K's wrong-camera trials
  are predicted by seed **height error 0.69 m vs 0.13 m** and focal **10.5% vs 4.6%**. So the floor I set
  for any seed producer is **height p90 ≤ 0.15 m, focal p90 ≤ 5%, wrong-camera rate after the fit ≤ 2%**
  (arm K's tail is 8.75%/400).
- On correct-camera trials the paint fit holds focal to **p90 0.043%** and height to **p90 0.6 mm**. Quote
  those two numbers whenever someone proposes replacing the fit — they are what a replacement must match.
- Corollary for scoping: a keypoint or detector model does **not** need sub-pixel labels, so it can be
  trained on synthetic renders and validated on real footage by **availability** (how many keypoints
  fire, does the seeded fit lock), never by precision against computed labels.

Related: [[two-court-pools-only-one-compromised]], [[cheap-tests-that-close-a-line]].
