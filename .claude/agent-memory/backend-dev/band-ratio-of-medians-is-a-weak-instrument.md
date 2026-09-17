---
name: band-ratio-of-medians-is-a-weak-instrument
description: Measured 2026-09-03 — a ratio of two band medians is so seed-unstable it flipped a verdict-relevant sign; use accept-precision-vs-base-rate instead, and seed-sweep before quoting any ratio
metadata:
  type: feedback
---

**Never pre-register, and never quote, a bar expressed as "median of band A >= k x median of
band B" without first sweeping seeds.** On n ~ 40-160 per band with a heavy-tailed,
ceiling-saturating error distribution, that estimator has sd 0.17-0.45 across seeds 0-9, a
range as wide as 0.62-1.89 on one clip, and bootstrap 95% CIs 0.69-2.47 wide that **all
contain 1.0**.

**Why:** two honest implementations of the identical described procedure — mine and qa's
independent rebuild — produced 1.02 and 1.89 for the same clip and landed on opposite sides
of 1.0. Four real implementation differences were ablated one at a time and **none moved the
number by more than 0.06**; the gap was pure sampling noise. Worse: under the more faithful
configuration the pre-registered "gate predicts error" bar **passes on 4 of 10 reseeds** of
the same experiment, so a single-seed refusal of it was luck, not a result. Full write-up:
`docs/evidence/does-seen-frac-predict-speed-error.md` §8.

**The metric that DID work, on the same rows:** the gate as a binary classifier —
accept-precision against the base rate. It reproduced to within 0.001-0.004 across two
independently written harnesses with different N, different RNG and different chain
assembly, and in the positive control it moved +3.8 -> +14.8 points under an injected effect
that barely shifted the band ratio at all. Same data, same injected effect: one estimator
sees it, the other does not.

**How to apply:**
- Prefer accept-precision vs base rate (or any whole-sample paired statistic) over a ratio
  of subgroup medians when designing a gate test.
- If a ratio is unavoidable, pre-register **seed-averaging over >= 20 seeds plus its
  spread**, or a paired design (same flight at two treatment levels) that removes the
  between-unit variance.
- When two implementations of one procedure disagree, ablate each difference as ONE
  VARIABLE before assuming a bug. If no single difference explains the gap, the estimator
  is the problem — and that instability is a better finding than a reconciled digit.
- Corollary for band edges: `seen_frac` is a ratio of small integers, so **2.9% of rows sat
  exactly on 0.50**, the threshold itself. A `<` / `<=` slip moves a real slice of the
  sample in the direction that flatters the gate. Pin the convention with a test.

Related: [[speed-error-is-geometry-not-detection]],
[[synth-truth-as-a-paired-error-rig]], [[null-controls-and-pre-registered-populations]].
