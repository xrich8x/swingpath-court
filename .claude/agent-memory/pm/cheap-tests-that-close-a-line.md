---
name: cheap-tests-that-close-a-line
description: Price a cheap experiment by what it CLOSES, not by its odds of passing — a founder idea killed by inference comes back, one killed by a number does not
metadata:
  type: feedback
---

**Rule: when an experiment is cheap, rank it on the value of the NEGATIVE outcome, not on
its probability of success.**

**Why:** `docs/STATE.md` rule 3 exists because nine distinct ideas here were re-proposed at
least once, and ~50 measured negatives is the asset that stops a tenth. An idea rejected by
argument comes back — especially the founder's own ideas, which is exactly when re-litigating
is most expensive. A measured negative retires a whole *family*, not one proposal. So a
minutes-of-compute test at 0.5 confidence is a good buy even if it fails, because failure is
the product.

**How to apply:**
- Ask "what does the FAIL close?" before "what does the PASS buy?" If the fail closes a
  family, run it; if the fail closes only this exact variant, it is probably not worth a
  session.
- **The real cost is a session, not the compute.** Minutes of CPU is free; the agent run is
  not. So bundle every cheap measurement that shares the same population and the same load
  into ONE brief — two runs for one data load is pure waste.
- **A rider measurement gets no gate.** If a second statistic rides along that was never
  pre-registered, it is DESCRIPTIVE only and must be labelled so. Inventing a bar for it
  after seeing the result violates rule 2, and rule 2's whole point is that a failed gate
  stays failed.
- **Pre-write the STATE row in BOTH directions** and hand it over before the run. Once a
  number is known, a kill condition gets softened by degrees; written in advance it cannot.
- **Watch for the asymmetric outcome.** A pass and a fail often need different levels of
  scrutiny — typically a fail is final and unattended, while a pass needs a human eye
  because a numeric near-match can be satisfied by the wrong object (a shadow, the near
  player, a shivering fence panel). Say which is which in the brief, or the builder will
  declare victory on the unverified half. Trap T23 is the same lesson for residuals.
