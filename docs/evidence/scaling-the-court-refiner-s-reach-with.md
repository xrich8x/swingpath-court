# Scaling the court refiner's reach with resolution (max_move_px 55 → 55·w/640)

> Evidence for the `scaling-the-court-refiner-s-reach-with` row in [docs/STATE.md](../STATE.md) (What has worked).
> Text preserved verbatim from SCOREBOARD.md at the 2026-08-26 split.

**MOVES NO NUMBER, and shipped anyway** — gold **12/20 → 12/20**, median 8.1 px, 0 wrong; references 2/20 → 2/20; shell 0/10 → 0/10. It is a correctness fix, not a win: the bound was tuned on the 640-wide gold set and was absolute, so the refiner's reach was **55 / 18.3 / 9.2 px@640** on gold / 1920 / 4K. Shipped because (a) it is an **exact no-op** on the gate — every gold clip is 640 wide and `640/640` is exactly `1.0`, so the argument is bit-identical — and (b) the same defect had already misled this project's own diagnosis, sending Session P chasing a reachability hypothesis that the tiny 4K reach made look plausible. Pinned by `tests/test_refine_reach_scaling.py`, which also fails if the gold frames ever stop being 640 wide, since that is what the no-op guarantee rests on. | Session P
