# The fitted hfov: is it computed and thrown away?

**DELIVERABLE (backend-dev, 2026-09-05):** whether the reporting gap is real and what
caused it; the full per-clip fitted-hfov table; the corruption sweep against the
**pre-registered** window; the verdict; and what (if anything) was changed to surface
the number.

**Scope note.** Pre-registration is in `.claude/journals/lead.md`, section
"PRE-REGISTRATION — the fitted hfov, which the code computes and throws away", dated
2026-09-05. It is quoted verbatim below and was **not** retuned. Source of the
corruption: qa's `docs/evidence/ground-plane-blindness-test.md`. **No gate is proposed
here** — four accept/reject gates have already failed on this evidence.

---

## 1. Is the gap real? — **NO. The premise is wrong.**

I was asked to confirm by reading the code rather than trusting the brief. Reading it,
the briefed claim — *"`camera_height_m()` hardcodes a default 70° hfov instead of using
the value the fit produced a few lines earlier"* — does not describe what the shipped
code does. Three separate checks:

**(a) The `70.0` is a Python default argument, not a hardcode over a live value.**

```python
# backend/swingvision/calibration.py:192
def camera_height_m(H, img_wh, hfov_deg: float = 70.0) -> Optional[float]:
```

`hfov_deg` is a *parameter*. Nothing inside the function overrides a caller-supplied
value. The docstring is explicit that the height comes "from the calibration homography
+ an **assumed** horizontal field of view" — the assumption is declared, not hidden.

**(b) `camera_height_m()` has no production call site at all.**
`grep` for `camera_height_m(`, `camera_position_m(`, `camera_pose_m(` across
`backend/swingvision/`, `tools/` and `backend/tests/` returns:

- `camera_height_m` — **zero callers** outside its own definition.
- `camera_position_m` — one production caller, `pipeline.py:1026`, and it passes
  `camera_hfov_deg`, the *resolved* field of view (see (c)). The remaining callers are
  `tools/` probes; four of those (`ball_perception.py`, `coast_fill_probe.py`,
  `demo_false_alarm.py`) do pass a literal `70.0`, and four pass a real `hfov`.

So the function the brief names is not on the path that produces any shipped number.
The camera height that the audit and the setup grader report does **not** come from it —
it comes from `cam_fit_quad`'s own `cam[2]`, which is fitted jointly with the focal.

**(c) The pipeline already prefers the fitted lens, in an explicitly ordered chain.**

```python
# backend/swingvision/pipeline.py:1244-1260  (comment verbatim)
# Field of view priority: explicit --camera-hfov (a phone whose fov the user
# knows) > the PHYSICAL CAMERA LOCK's focal (works on every view, including
# the telephoto broadcasts where focal_from_homography is degenerate) >
# focal self-calibration from H > the old fixed 70° guess.
```

`cam_hfov_deg` arrives from `courtfit.shape_lock(...)["hfov_deg"]`
(`pipeline.py:535`), which is `hfov_from_focal(fit[3][5], w)` — i.e. **the fitted
focal from `cam_fit_quad`**. The literal `70.0` at `pipeline.py:1259` is reached only
when the shape lock did not apply *and* `focal_from_homography` was degenerate, and it
prints a line saying so. `pipeline.py:1017` even carries a comment recording that a
downstream threshold was *re-tuned* when heights stopped coming from the 70° assumption
— evidence that the migration off 70° already happened and was accounted for.

**Verdict on ask 1: the hardcode is a deliberate, declared, last-resort fallback for
the case where no fit is available, and it is not load-bearing on any shipped number.**
The fitted hfov is not thrown away by the pipeline.

## 2. Does `--audit` print the fitted value or the 70° default? — **the FITTED value.**

This was flagged in the brief as the bigger finding if the audit had been printing 70°
all along. It has not been.

```python
# tools/validate_new_clip.py:141-171  (camera_fit)
fit = courtfit.cam_fit_quad({n: kp[n] for n in CORN}, calibration, court,
                            img_wh[0], img_wh[1], allow_roll=True)
cam = fit[3]
hfov = calibration.hfov_from_focal(cam[5], img_wh[0])
...
return (abs(float(cam[2])), float(fit[2]),
        f"hfov {hfov:.0f}deg roll {roll:+.1f}deg fit {fit[2]:.1f}px")
```

`cam[5]` is `cam_fit_quad`'s fitted focal. So the `hfov ...deg` in every `--audit` line
is **per-clip fitted**, and the height printed alongside it is `cam[2]` from the same
fit — also not the 70° path. The function's own docstring already contrasts the two
("on `am_hard_utr` the assumption reads 2.1 m, the fit reads 1.74 m at hfov 86 deg").

**So the number is computed AND printed.** What is genuinely missing is narrower and
worth stating precisely:

> The fitted hfov is printed as decoration inside a free-text lens string. **Nothing
> compares it against the 60–90° lens prior, nothing stamps it into the `_audit` blob
> written by `--stamp`, and no verdict line mentions it.** A human reading
> `hfov 34deg` on an amateur phone clip gets no signal that 34° is impossible.

That — a *plausibility read and a persisted field*, not a rescued discarded number — is
the real remainder, and it is what section 4 addresses.

---

## 3. Per-clip fitted hfov, all calibrations

> Sections 3-6 were completed by the **lead** from `data/output/hfov_sweep.json`, which
> backend-dev had already produced before a session limit ended its run mid-write. Sections 1-2
> and the sweep itself are backend-dev's.

28 non-degenerate calibrations. Sorted, the fitted hfov spans **23.4 deg to 104.2 deg**.

**Seven sit OUTSIDE the pre-registered 60-90 deg window**, and this is the whole result:

| clip | hfov | stamp | believed correct? |
|---|---|---|---|
| `demo30` | **104.2** | LOW-CAMERA | yes |
| `HoHxFSX_gLk_s2` | **94.3** | LOW-CAMERA | yes |
| `yt_rally2` | **93.7** | PASS | **yes - a gold clip** |
| `yt_match40` | **91.0** | LOW-CAMERA | **yes - the one just re-clicked and confirmed** |
| `flexi_franz_p07` | **59.6** | PASS | yes |
| `eala_pts_auto` | **23.4** | PASS | yes - Wimbledon broadcast |
| `court_pts_refined` | **12.3** | PASS | unverifiable, no video |

## 4. The corruption sweep against the pre-registered window

The sensitivity half of the claim is **confirmed exactly**. Compressing `yt_match40`'s far
corners toward the near ones collapses the fitted hfov monotonically while the fitted height
barely moves and the residual stays near zero:

| compression | hfov | fitted height | residual px |
|---|---|---|---|
| 0.00 (correct) | 91.0 | 1.641 | 0.000 |
| 0.15 | **55.3** | 1.661 | 0.080 |
| 0.30 | **34.4** | 1.661 | 0.088 |
| 0.50 | **18.3** | 1.665 | 0.071 |
| 0.70 | **8.7** | 1.667 | 0.045 |
| 0.90 | **2.4** | 1.198 | 2.989 |

So hfov **does** see the one corruption every shipped gate misses, and it sees it at 15%
compression - while height and residual stay healthy throughout, which is precisely why those
two gates missed it.

## 5. Verdict — **FAILS the pre-registered bar, on its second half**

The bar was two-sided by design: flag **>=4 of 5** compressions **AND** flag **0** of the
calibrations believed correct.

- **First half PASSES.** A 60-90 window flags every compression from 0.15 down.
- **Second half FAILS, and badly.** The same window flags **6 clips believed correct**,
  including **`yt_match40`, the calibration just re-clicked and confirmed by three independent
  checks**, and **`yt_rally2`, a gold clip**. It also flags `eala_pts_auto` - reproducing
  exactly the broadcast false-reject that the camera-height screen already commits, which the
  bar named in advance as the failure mode to avoid.

**A window that catches the corruption by also rejecting the clip we just fixed has reproduced
the previous failure, not fixed it.** The bar said so before the numbers existed. It stays
failed; the window is not widened to fit.

**This is the fifth autonomous calibration gate to fail.** Coverage/centrality, the
camera-height screen, the net-anchor `band_ratio`/`dy` bars, the net-post detector (a
concurrent run, 3/11 against a 67% bar), and now hfov.

## 6. What I changed

**Nothing in the shipped code, and section 1 is why.** The premise this run was dispatched on -
that `camera_height_m()` hardcodes 70 deg over a live fitted value - is **wrong**: the 70.0 is a
Python default argument, the function has **zero production callers**, and `--audit` already
prints the **fitted** hfov. There was no reporting gap to close.

**The chain that produced the false premise is worth recording:** researcher asserted
ground-plane blindness -> qa tested it and reported the hfov hardcode as an aside -> the lead
believed it and pre-registered a bar against it -> backend-dev read the code and found it did
not exist. **Four steps, and only the last one opened the file.** The correction cost one agent
run; believing it would have cost a shipped change to a function nothing calls.

## NOT ESTABLISHED THIS RUN

- Whether any hfov window narrower or wider than 60-90 could separate. Not swept, deliberately:
  choosing a window from this table after seeing which clips it excludes is the post-hoc error
  this project has now been caught in twice.
- Whether the wide-hfov clips (`demo30` 104.2, `yt_rally2` 93.7) are genuinely ultra-wide phone
  lenses or a mild version of the same compression bias. That is a real open question and the
  natural next measurement.
