# AGREE_PX is 6× tighter on 4K than on the gate, and the tightness is doing a SECOND job

> Evidence for the `agree-px-is-6-tighter-on-4k` row in [docs/STATE.md](../STATE.md) (Open).
> Text preserved verbatim from SCOREBOARD.md at the 2026-08-26 split.

**Waiting on the wrong-court/search problem in the row above — it cannot ship before that.** All 20 gold clips are exactly 640 wide, the references 1920, shell 3840, so the shipped absolute `AGREE_PX = 30` is **30 / 10.0 / 5.0 px@640** against an accepted band of 3.4–13.9. `30·(w/640)` normalises that, is an **exact no-op on gold** (12/20 at 13.9, identical), and does what the diagnosis predicted on shell: **0 → 2 accepted, both correct**, with `flexi_franz_p07` going from a 39.1 px consensus at 2 votes to **10.5 px at 7**. **But on the 1920 references it admits two wrong courts** — `tc8CGFxyRE8` 58.7 px and `e8T34KoJzOw_s2` 28.7 px. `tc8CGFxyRE8` is a *reproducible* wrong court the tight radius was accidentally suppressing. The radius groups correct frames AND suppresses reproducible wrong ones; fixing the first exposes the second. §11.
