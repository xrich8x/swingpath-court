# Making the calibration auditor find videos recursively

> Evidence for the `making-the-calibration-auditor-find-videos-recursively` row in [docs/STATE.md](../STATE.md) (What has worked).
> Text preserved verbatim from SCOREBOARD.md at the 2026-08-26 split.

**0 pass / 5 fail → 4 pass / 6 LOW-CAMERA / 0 fail** on the ten new shell calibrations. `validate_new_clip.py` resolves a clip's resolution from its video and falls back to assuming 720p when it cannot find one — so ten 4K calibrations were audited as if 720p and every one reported DEGENERATE at 41–117 px fit residual. Read at the correct resolution they are **0.0–2.5 px**, the best band in the repo. **The cause is that the previous fix for this exact bug was a hard-coded list of directories** (its own docstring records it stamping nine correct calibrations DEGENERATE), and reorganising `data/incoming/` into per-surface subfolders put the videos one level deeper than the list looked. Replaced with a recursive search, which cannot be broken by moving a file. | Session O
