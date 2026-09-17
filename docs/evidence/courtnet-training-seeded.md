# CourtNet training seeded

> Evidence for the `courtnet-training-seeded` row in [docs/STATE.md](../STATE.md) (What has worked).
> Text preserved verbatim from SCOREBOARD.md at the 2026-08-26 split.

closes an undocumented asymmetry flagged by the 2026-08-16 review (P2-1): `train_courtnet.py` had zero seeding while `train_ballnet.py` fully seeds random/np.random/torch/cuda plus the DataLoader shuffle generator. Now matches that exact discipline (same caveat as ballnet: pairs init/shuffle/augmentation draws, not full multi-worker bit-determinism) via a new `--seed` flag, so a future CourtNet A/B won't repeat the "arms differ by more than the flag under test" problem Trap T10 already fixed once for BallNet. No CourtNet number moved — this only removes a confound from the *next* comparison. | 2026-08-16
