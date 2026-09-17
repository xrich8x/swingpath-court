# data/incoming — source videos, by court surface

Every source video in the repo lives here. Filenames are **never** changed:
the ball gold-leak guard (`train_ballnet.gold_source_videos`) and
`data/train_clips/lineage.json` both key on **basename**, so a rename silently
defeats both. That is trap T17. Moving a file between these folders is safe;
renaming it is not.

The surface folder is organisational only — the detector calls
`calibration.court_surface()` on the actual frame at runtime, so a misfiled
video costs nothing functionally.

| folder | videos | processed by the eval? |
|---|---|---|
| `Clay` | 9 | yes |
| `Grass` | 4 | yes |
| `Hardcourt` | 38 | yes |
| `Raw - Do Not Process` | 9 | **no** — full-length downloads whose trims are already in the surface folders; sweeping both would count the same court twice |
| `Shell` | 6 | yes |

## GOLD test footage in these folders — never train on these

`data/gold_clips/` used to keep gold videos out of the training pool by
*location*. That cue is gone now they are filed by surface, so it is recorded
here instead. The leak guard still catches it (it derives from
`data/gold/*.manifest.json`, not from a folder), but a human building a
training set from a surface folder has nothing visual to warn them.

| file | gold set |
|---|---|
| `Clay/gold_clay.mp4` | BALL gold (`gold_clay`) |
| `Clay/sAjkpeRq4P4.mp4` | BALL gold (`gold_sAjkpeRq4P4`) |
| `Clay/yt_tnxkujogch4.mp4` | COURT gold (`am_rally32short`) |
| `Hardcourt/am_hard_utr.mp4` | BALL gold (`am_hard_utr`) |
| `Hardcourt/gold_am.mp4` | BALL gold (`gold_am`) |
| `Hardcourt/L73ep7JHiJ4.mp4` | BALL gold (`gold_L73ep7JHiJ4`) |
| `Hardcourt/UHf0LeMU2pg.mp4` | BALL gold (`gold_UHf0LeMU2pg`) |
| `Hardcourt/uR5q2cSM6AY.mp4` | BALL gold (`gold_uR5q2cSM6AY`) |
| `Hardcourt/yt_0genZFgM61E.mp4` | COURT gold (`am_ntrp45_courtlevel`) |
| `Hardcourt/yt_4apx6gd5Uxs.mp4` | COURT gold (`am_ntrp40`) |
| `Hardcourt/yt_5VUiurUhSRY.mp4` | COURT gold (`am_college`) |
| `Hardcourt/yt_deNCnfQjfoU.mp4` | COURT gold (`am_ntrp30`) |
| `Hardcourt/yt_ihXS4IDvF0A.mp4` | COURT gold (`am_usta45`) |
| `Hardcourt/yt_match40.mp4` | BALL gold (`yt_match40`) |
| `Hardcourt/yt_QsO90orMfWM.mp4` | COURT gold (`am_beginner`) |
| `Shell/gold_shell.mp4` | BALL gold (`gold_shell`) |
| `Shell/yt_esnrHQhCIxQ.mp4` | COURT gold (`am_classB`) |
| `Shell/yt_rally2.mp4` | BALL gold (`yt_rally2`) |
| `Shell/yt_rNMc9tpWWZ0.mp4` | COURT gold (`am_rec30`) |

Anything not listed above is free to train on.
