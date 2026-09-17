# Raising topk so more seeds get refined

> Evidence for the `raising-topk-so-more-seeds-get-refined` row in [docs/STATE.md](../STATE.md) (What has not worked).
> Text preserved verbatim from SCOREBOARD.md at the 2026-08-26 split.

**Measured dead end, 2026-08-25.** The seed nearest the true court dies at `in top-k` on **35 of 38** clips (ranks 13–993 against `topk=12`), which looked like a depth problem. It is not: at topk 12 → 40 → 150, `flexi_franz_p01` stays at 2/4 true frames and `hillsborough_p02` goes **1/4 → 0/4**, for **7× the compute** (32 s → 229 s per 4 frames). `data/output/seed_reach.log`.
