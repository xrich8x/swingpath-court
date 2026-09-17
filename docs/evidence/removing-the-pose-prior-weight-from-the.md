# Removing the pose-prior weight from the seed RANKING

> Evidence for the `removing-the-pose-prior-weight-from-the` row in [docs/STATE.md](../STATE.md) (What has not worked).
> Text preserved verbatim from SCOREBOARD.md at the 2026-08-26 split.

Looked like the classic patched-one-caller defect — `autodetect` gives low mounts an escape hatch in the accept gate (`pose_ok`) and never gave the ranking one. **Refuted:** measured maha of the truth-nearest seed is **1.3–19.8** against `PRIOR_MAHA_MAX = 55`, so the penalty is mild; re-ranking by `g` alone promotes the true court into the top-12 on **2 of 38** clips, and on many it is actively **worse** (`hillsborough_p02` rank 193 → 761). The prior is helping.
