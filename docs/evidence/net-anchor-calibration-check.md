# The net-anchor calibration check

**DELIVERABLE:** a first-class, reusable check that projects court features the
four-corner fit did *not* use — the net line, the net **tape**, and both **net
posts** — renders them over a real frame, reports the rows a human needs, and
runs over every calibration in `data/`.

Built 2026-09-05 by backend-dev. Code:

| Piece | Path |
| --- | --- |
| Constants (posts, tape heights, sticks) | `backend/swingvision/court.py` (+ mirror in `frontend/src/lib/court.js`) |
| The check itself | `tools/net_anchor_check.py` |
| Render entry point | `tools/render_corner_audit.py --net-anchors` |
| Numeric entry point | `tools/validate_new_clip.py --audit … --net-anchors` |
| Tests | `backend/tests/test_net_anchor_geometry.py` (7, all pass) |
| Sweep output | `data/output/corner_audit/*_netanchor.png` + `net_index.json` |

```
./backend/.venv/Scripts/python.exe tools/render_corner_audit.py --net-anchors
./backend/.venv/Scripts/python.exe tools/validate_new_clip.py --audit data/x_pts.json --net-anchors
```

---

## 1. Why it exists, and the correction that reshaped it

The brief for this work said `yt_match40`'s 2026-09-05 re-click was *still wrong*
— far corners on the net — because the projected net landed ~36 px below the real
net, while improving on every screen the project owns (residual 0.9 → 0.2 px,
camera 11.3 m → 1.61 m, `verify_court` coverage 0.436 → 0.944).

**Mid-run the lead withdrew that premise, and the withdrawal is the most useful
thing in this document.** The comparison had been the projected net **GROUND**
line (court-y 11.885 at z = 0, which is all a homography can give) against the
net's white **TOP TAPE** in the image, which is 0.914 m above the ground and
therefore *must* image higher. That test fails on every correct calibration.

The arithmetic, reproduced independently by this tool (see §4): for a pinhole at
height `H`, `(row − horizon) ∝ H / depth`, so a point `h` above the ground at the
same depth scales that offset by `(H − h) / H`.

> `yt_match40`: horizon row 264.8, net ground row 325.4, camera 1.64 m
> ⇒ tape must image at `264.8 + (325.4 − 264.8) × (1.64 − 0.914) / 1.64 = 291.6`.
> The tool's 3-D projection puts it at **291.9**. Observed tape ≈ 295.
> **Disagreement ≈ 3 px. The calibration is CORRECT.**

So this tool has two jobs, not one:

1. project the right thing (**tape and posts**, not just the ground line), and
2. **make the two impossible to confuse** — different colours, different labels,
   both rows printed, on every image and in every numeric report.

The claim "a wrong court scored 0.944 coverage" is **withdrawn** and is not
evidence. What survives untouched is the mechanism it was invented to describe:
coverage asks whether projected lines land on paint, not whether they land on the
paint they are *named* for.

## 2. What is drawn and measured

Ground plane (homography alone):

* the **net ground line**, court-y 11.885, z = 0 — drawn **green**, labelled
  `net GROUND z=0 (homography)`;
* both **net post bases**, at `x = −0.914` and `x = 11.884` (0.914 m / 3 ft
  outside the doubles sideline), z = 0.

Needs the camera **pose** (`calibration.project_court_3d`, with the hfov read off
`courtfit.cam_fit_quad` — never the 70° default; mounts here run 60–91°):

* the **net tape**, z = 0.914 m at the centre strap rising to 1.07 m at the posts
  — drawn **yellow**, labelled `net TAPE z=0.914m (pose) <- compare THIS to the
  white tape`;
* both **post tops**, z = 1.07 m, drawn as red vertical sticks from base to top.

Printed on the image and by `--net-anchors`: `horizon_row`, `net_ground_row`,
`net_tape_row`, post base/top pixels, and the band measurements of §3. Every
image carries the line *"Do NOT read the GREEN ground line against the tape —
that is the apples-to-oranges error"*.

**Singles sticks** (`X_LEFT_STICK` 0.456, `X_RIGHT_STICK` 10.514) are added to
`court.py` because singles-post geometry genuinely differs — the same 0.914 m
offset, but from the *singles* sideline, so the sticks stand **inside** the
doubles alley rather than outside the court. The check draws the **doubles**
posts: those are the ones bolted into the ground and visible in every clip here.
`court.LINES` is deliberately **unchanged** — it is what `overlay.py` draws and
what `validate_new_clip.py` counts horizon crossings over, and adding posts to it
would change behaviour unrelated to this check.

## 3. Why it is not circular

Four clicked doubles corners determine `H` exactly (4 points, 8 DOF). *Anything*
projected through `H` is a consequence of the clicks, which is why scoring the
projected court lines against white paint is close to grading the clicks with
themselves. The escape needs **both** of:

1. the projected feature is **not one of the four fitted points** — the net line,
   the tape and the posts are never clicked, and
   `test_net_posts_are_not_fitted_points` pins that they are not even in
   `court.LANDMARKS`;
2. it is checked against **different image evidence than white court paint** —
   the net's mesh and tape, and small vertical high-contrast posts standing
   *outside* the doubles sideline.

Part 2 is what coverage lacks. A wrong-but-plausible quad keeps landing on paint;
it cannot conjure a net or a post where there is none. Posts are the founder's
suggestion and are the strongest anchor available for exactly the reason the
original failure happened: a foreshortened far baseline at the top of frame is
ambiguous, while a post is small, vertical, high-contrast and unambiguous — and,
being a segment from a known ground point to a known height, it constrains the
ground position **and** the camera height at once.

Honest caveat on the *numeric* half: `horizon_row` and the fitted hfov are
derived from the same four corners, so they are **not** independent evidence.
They are the existing camera-height screen in different clothing (see §5). The
independent part is the **picture** — tape against tape, post against post.

## 4. The pre-registered bars, and their FAILURE

Written down before any clip was measured (`tools/net_anchor_check.py`
docstring, `BAR_BAND_RATIO`, `BAR_DY_FRAC`):

* **`band_ratio`** — median edge energy in the projected net band (ground line up
  to the tape) over the same statistic in the court-surface strip 0.2–1.2 m in
  front of it. A net is a mesh; court surface is smooth.
  **BAR: `band_ratio < 1.5` → FLAG.**
* **`dy_best`** — the rigid vertical shift of *both* strips together that
  maximises `band_ratio`; the automated form of "the projected net is N px away".
  **BAR: `|dy_best| > 0.5 × net pixel height` → FLAG.**

### Verdict: both bars FAIL. They are not moved; they are retained as reported numbers only.

Two-sided, on the one clip whose truth is now settled, using the current file and
its `.bak-2026-09-05` predecessor (the genuinely wrong one — **not restored, not
edited**):

| `yt_match40` | residual | camera | hfov | horizon row | ground row | tape row | `band_ratio` | `dy_best` | bar says |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| current — **CORRECT** | 0.0 px | 1.64 m | 91° | 264.8 | 325.4 | 291.9 | **0.78** | +49 | **FLAG** |
| `.bak-2026-09-05` — **WRONG** | 0.9 px | 11.3 m | 20.7° | **−382.2** | 384.8 | 325.3 | **7.84** | −15 | **ok** |

The texture bars are **inverted** on the only pair where truth is known: they
flag the right calibration and pass the wrong one. A single pair cannot establish
a general inversion, but it is decisively enough to disqualify the bars as a
gate. The corpus agrees they are unusable regardless of direction: **14 of 27
flagged**, including four `PASS`-stamped calibrations and clips whose corner
sheets were accepted.

Likely mechanism, stated as a hypothesis and not measured: at a low mount the
"court surface 0.2–1.2 m in front of the net" control strip is neither small nor
featureless — it spans a large pixel range, and picks up the net's own shadow,
the bottom of the netting and the near service area — so the ratio is not
measuring what its name says.

## 5. The sweep over the existing calibrations

All `data/**/*_pts.json`, frame 0, run 2026-09-05.
**27 rendered of 29**; `court` and `yt_court` have no matching `.mp4`.
Full table in `data/output/corner_audit/net_index.json`; PNGs alongside.

| tag | horizon | ground | tape | net px | `band_ratio` | best | `dy_best` | bar |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A7vXlWIlyrI | 575.0 | 681.5 | 623.8 | 62.1 | 2.33 | 7.40 | −168 | FLAG |
| am_hard_utr | 480.4 | 585.0 | 530.5 | 58.6 | 4.36 | 39.44 | −136 | FLAG |
| bump_ntrp30 | 75.0 | 155.3 | 135.9 | 20.8 | 5.46 | 77.90 | +46 | FLAG |
| bump_ntrp30b | 93.5 | 150.8 | 135.1 | 16.8 | 2.14 | 32.00 | +50 | FLAG |
| CYqapSq5llo | 413.7 | 572.1 | 500.0 | 77.6 | 1.64 | 14.01 | −80 | FLAG |
| demo30 | 263.9 | 311.8 | 280.1 | 34.1 | 3.34 | 14.00 | +6 | ok |
| e8T34KoJzOw_s2 | 517.1 | 624.8 | 568.8 | 60.2 | 3.06 | 174.12 | +32 | FLAG |
| flexi_franz_p01 | 514.8 | 930.7 | 780.9 | 161.3 | 1.03 | 17.36 | +28 | FLAG |
| flexi_franz_p07 | 519.6 | 936.8 | 786.1 | 162.0 | 3.57 | 14.97 | +18 | ok |
| flexi_joy_p01 | 831.5 | 1031.9 | 897.8 | 144.0 | 16.86 | 24.78 | +23 | ok |
| flexi_joy_p07 | 833.3 | 1024.3 | 896.2 | 137.5 | 12.23 | 22.73 | +37 | ok |
| hillsborough_p02 | 1043.4 | 1255.6 | 1137.5 | 127.0 | 18.51 | 19.92 | +9 | ok |
| hillsborough_p08 | 1053.3 | 1245.1 | 1137.8 | 115.3 | 10.43 | 20.46 | +9 | ok |
| HoHxFSX_gLk_s1 | 504.7 | 631.2 | 563.5 | 72.7 | 3.41 | 62.62 | −35 | ok |
| HoHxFSX_gLk_s2 | 493.9 | 578.1 | 529.9 | 51.7 | 2.60 | 32.69 | −111 | FLAG |
| HoHxFSX_gLk_s3 | 580.5 | 675.4 | 620.6 | 58.8 | 3.25 | 21.87 | +152 | FLAG |
| L73ep7JHiJ4 | 109.3 | 313.2 | 251.1 | 66.8 | 19.95 | 39.45 | +99 | FLAG |
| mpc_mixed_p02 | 974.2 | 1163.1 | 1057.8 | 113.0 | 2.32 | 12.83 | +11 | ok |
| mpc_mixed_p08 | 975.2 | 1161.4 | 1057.2 | 112.0 | 1.28 | 16.58 | +14 | FLAG |
| mpc_tuesday_p01 | 642.9 | 1040.1 | 912.1 | 137.2 | 21.26 | 28.00 | +9 | ok |
| mpc_tuesday_p07 | 644.1 | 1050.8 | 921.3 | 138.4 | 22.71 | 25.97 | +5 | ok |
| sAjkpeRq4P4 | 289.4 | 490.1 | 437.5 | 56.5 | 5.64 | 9.85 | −2 | ok |
| tc8CGFxyRE8 | 426.8 | 603.8 | 523.4 | 86.3 | 21.74 | 93.27 | +37 | ok |
| UHf0LeMU2pg | 5.4 | 281.3 | 210.4 | 76.3 | 3.34 | 8.26 | −43 | FLAG |
| uR5q2cSM6AY | 325.5 | 513.1 | 463.0 | 54.1 | 1.78 | 17.40 | −36 | FLAG |
| yt_match40 | 264.8 | 325.4 | 291.9 | 36.0 | 0.78 | 16.67 | +49 | FLAG |
| yt_rally2 | 146.7 | 275.0 | 241.1 | 36.5 | 1.79 | 5.59 | −17 | ok |

**Read this table as rows, not as flags.** The `bar` column is a failed
instrument (§4). The three geometry columns are the product: `horizon`, `ground`
and `tape` let anyone redo the lead's arithmetic on any clip without repeating
the mistake, and the PNG shows whether the yellow tape line and the red posts
land on the real ones.

### The two the lead could not settle

Per the correction, the height fix was applied before concluding anything.

* **`am_hard_utr`** — camera 1.74 m, hfov 86°, horizon 480.4, ground 585.0, tape
  530.5. The closed-form relation gives `480.4 + 104.6 × (1.74 − 0.914)/1.74 =
  530.1` against the projected 530.5, so the tape projection is internally
  consistent. `band_ratio` at dy = 0 is a **healthy 4.36**; only the failed
  `dy_best` bar fires. **Not settled here, and not condemned:** its PNG needs an
  eye.
* **`sAjkpeRq4P4`** — horizon 289.4, ground 490.1, tape 437.5, `band_ratio` 5.64,
  `dy_best` −2 px. **Not flagged at all.** On this evidence the "far corners near
  the net" reading is unsupported, but the same correction that rescued
  `yt_match40` may apply, and only the frame settles it.

Neither can be concluded from this run: the instrument that would decide them is
the one that failed. **The PNGs exist and are named**
`data/output/corner_audit/{am_hard_utr,sAjkpeRq4P4}_netanchor.png`.

### The one number that did separate the known pair

`horizon_row` and the fitted `hfov` split the `yt_match40` pair very cleanly:
correct = horizon 264.8 (inside a 720-row frame) at hfov 91°; wrong = horizon
**−382.2**, i.e. 382 px above the top of the frame, at hfov 20.7° and a claimed
11.3 m camera. A hand-held phone clip with a horizon 382 px off-plate and a 20°
lens is not physical. **This is not new information** — it is the existing camera
height screen re-expressed, computed from the same four corners, so it is not
independent evidence and no bar is proposed on it. It is reported because it is
free and reads more concretely than "camera height 11.3 m".

## 6. Limits

* **The bars failed and were not replaced.** No pass/fail threshold is proposed
  from this corpus. `n = 1` settled clip cannot validate one, and the project's
  own rule stands: a residual is not a verdict, the frame is.
* **`band_ratio` needs a camera pose.** Where the pose is unrecoverable the check
  degrades to the rendered picture and the ground-plane parts only.
* **One frame, frame 0.** Players, shadows, fences and crowds inside either strip
  move the texture numbers. Medians over 41 columns blunt that, they do not
  remove it.
* **Posts are frequently off-frame** on the low wide mounts this project targets,
  so no bar is placed on post evidence — that would be a bar on framing. They are
  drawn when visible and reported as `OFF-FRAME` when not, so their absence is
  never read as a missing feature.
* **Net height is modelled linearly** from 0.914 m at the centre strap to 1.07 m
  at the post, not as the true catenary. Under a pixel at any mount here.
* **No calibration file was edited** (rule 9). `yt_match40_pts.json.bak-…` was
  read as a negative example and left where it is.

## 7. Not established this run

* Whether `am_hard_utr` or `sAjkpeRq4P4` are correct. Needs a human eye on two
  PNGs that now exist.
* Any *working* quantitative net detector. `band_ratio` is disqualified; a tape
  detector (bright horizontal strip top-hat) and a post detector (vertical
  high-contrast segment at a predicted x) are the obvious next candidates and
  were not built.
* Whether the flag list would change on a mid-rally frame rather than frame 0.
