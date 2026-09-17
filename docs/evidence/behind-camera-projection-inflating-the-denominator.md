# Behind-camera projection inflating the denominator (_apply divides by w with no sign check)

> Evidence for the `behind-camera-projection-inflating-the-denominator` row in [docs/STATE.md](../STATE.md) (What has not worked).
> Text preserved verbatim from SCOREBOARD.md at the 2026-08-26 split.

**0.0% of court samples project from behind the camera** on every clip. Also killed the reasoning behind it: `reliable_court_span`'s "7.5 m of 23.77" is metres-per-pixel precision near the horizon, not lines being off-frame.
