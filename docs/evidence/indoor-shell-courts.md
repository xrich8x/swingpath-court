# Indoor shell courts — GROUND TRUTH EXISTS as of 2026-08-24, and it says the failure is the SEARCH

> Evidence for the `indoor-shell-courts` row in [docs/STATE.md](../STATE.md) (Open).
> Text preserved verbatim from SCOREBOARD.md at the 2026-08-26 split.

**Nothing. Unblocked.** 10 human calibrations (2 per venue) arrived and are good: repeatability **1.2–7.0 px@640** on 4 of 5 venues, camera audit **2 PASS / 3 LOW-CAMERA / 0 fail** at **0.0–2.5 px** fit residual, implied camera height reproducing to 0.02 m across independent labels. (`mpc_tuesday` repeats at **25.4 px**, above the wrong-court line — reported, not used as truth.) The result: **the human court would be ACCEPTED on 7 of 10 shell clips if the search produced it**, but truth is inside the candidate set on only **3 of 10** — and on all 4 clips where locks exist but none is true, **the human court OUTRANKS every lock**. Three no-lock, four never-reached, three reached-but-vote-fails. Tuning stays on the 10 original calibrated clips; **shell is verification only**. `data/output/court_scoring_diagnosis.md` §10.
