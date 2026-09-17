# Narrowing EVID_BAND so clutter near a model line cannot inflate the denominator

> Evidence for the `narrowing-evid-band-so-clutter-near-a` row in [docs/STATE.md](../STATE.md) (What has not worked).
> Text preserved verbatim from SCOREBOARD.md at the 2026-08-26 split.

**The band is INERT.** `n_included` = geometrically-in-frame = **10 of 10** court lines on every calibrated clip at every band 5.0 → 1.0, so it never excludes anything at the true court. Narrowing it is a *wrong-court lever*: truth does not move, wrong courts' `n_included` falls 10 → 8.5, and the median margin drops **+0.123 → +0.102**. Caught by a pre-registered `n_included` guard. `data/output/court_scoring_diagnosis.md` §1–2.
