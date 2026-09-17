---
description: On-demand deep PM review of recent SwingVision work for a non-technical PM — plain English, grounded in this project's real ML/CV technique and physical tennis facts, cross-checked against docs/STATE.md's measured history. Invoke with /pm-review.
disable-model-invocation: true
---

# /pm-review

**The review prompt lives in one place: [`PM_REVIEW_PROMPT.md`](../../../PM_REVIEW_PROMPT.md)
in the repo root. Read it now and follow the prompt block inside it verbatim.**

That file is the single source. This skill is the `/pm-review` entry point to it;
pasting the same file by hand is the other. Both run the same text.

## Why this file is a pointer and not a copy

It used to be a copy, and the copy went stale in exactly the way
[T21](../../../docs/TRAPS.md) predicts — *re-deriving a rule instead of sharing it,
then trusting the copy over the pixels.*

On 2026-08-15 the racket clause was corrected: it had claimed confuser filtering
tops out at ~55% because a ball and a racket "are genuinely close in apparent
size". **Both halves were wrong** — a racket is 10× a ball, and the measured reason
negation failed is that COCO found the *near* player's racket while the detector
fired on the *far* player's. The correction was applied to `PM_REVIEW_PROMPT.md`
and **not** to this file, so for eleven days `/pm-review` was handing every review
a cause the project had already measured and disproved. By 2026-08-26 the two texts
shared **one** substantive line out of ~160.

A prompt that encodes a wrong cause hands it to every future review. One text, two
entry points, is the only arrangement where correcting it once is enough.

**Do not restate the prompt here.** If the review itself needs changing, change
`PM_REVIEW_PROMPT.md`. The previous 113-line copy is in git history
(`git show 4bb5baa:.claude/skills/pm-review/SKILL.md`) if any of its framing is
wanted back — but merge it into the canonical file, do not fork it again.
