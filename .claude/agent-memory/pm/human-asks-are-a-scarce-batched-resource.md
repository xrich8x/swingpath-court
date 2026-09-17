---
name: human-asks-are-a-scarce-batched-resource
description: Founder minutes are the scarcest resource — batch every human ask into one update, rank by leverage, build the artefact first so he only looks, and dispatch human-latency items before machine work
metadata:
  type: feedback
---

**Rule: every task needing a human goes out in ONE batched update, ranked by leverage, and
the artefact he looks at is built before the ask is made.**

**Why:** founder minutes are the binding constraint on this project, not compute and not
sessions — see [[v1-critical-path-is-founder-blocked]], where roughly five minutes of
re-clicking gates the single largest v1 runtime risk. Human asks also carry latency the
team cannot compress, so an ask sent late idles the whole queue behind it. And an ask that
arrives without the artefact ("please audit the calibrations") converts a 10-minute look
into an hour of hunting, which is how a cheap ask silently becomes an expensive one.

**How to apply:**
- **Dispatch the human-latency item first**, before machine work, so his clock and the
  team's run in parallel. This inverts the usual "do the cheap thing first" instinct.
- **Rank the asks and say what each unblocks**, so he can spend five minutes rather than
  three hours if that is all he has. Do not present them as an undifferentiated list.
- **Build first, ask second.** Lead renders the sheets; founder only looks. Never hand him
  a task where the first step is locating the thing.
- **Never queue a human-blocked item as team work.** It is not work, it is a dependency,
  and listing it as work makes the queue look fuller than it is.
- **Sequence labelling protocols BEFORE labelling.** If he is about to spend 3-6 hours
  clicking, the schema for what he clicks is a prerequisite line item — otherwise the
  hours produce a gold set that does not support the gate it was meant to support, and
  they get spent twice. Same logic as
  [[score-layer-reopened-no-ground-truth]].
- **Rule 9 makes some things permanently his.** Human ground truth is recorded when
  wrong, never quietly fixed, so a mislabel is always an ask and never a task.
