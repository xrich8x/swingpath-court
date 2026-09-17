---
name: net-tape-height-is-precision-limited
description: The net-tape camera-height estimator AGREES with the fitted heights (13/15 within 10%), and its whole 10% bar is ~3 px of tape row at 720p — eyeball tape reads are not admissible
metadata:
  type: project
---

The white net tape gives a camera height independent of the four corner clicks:
`H = 0.914 / (1 - (tape_row - horizon)/(ground_row - horizon))`. Swept over the corpus
2026-09-05 (`tools/net_tape_height.py`, `docs/evidence/net-tape-camera-height-consistency.md`):
**15 of 27 clips measurable, 13/15 within 10%, directions 8+/7-, median +0.3% — AGREE on the
pre-registered bar.** The briefed -12.8/-33.3/+12.2% disagreements did not survive an
automated measurement.

**Why:** `dH/drow = H^2 / (0.914 * (ground_row - horizon))`. That is **3.2%/px on a 720p clip**,
1.8%/px at 1080p, 0.7%/px at 4K. The entire 10% bar is **~3 px of tape row at 720p**. The
-12.8% on `am_hard_utr` was row 522 (an eyeball profile) against row 528.0 (a matched filter):
**six pixels**. Nothing about a fitted height changed; the instrument got sharper.

**How to apply:**
- Never quote a tape-implied height read by eye, or from a single brightness profile. Below
  ~1080p the read must be sub-pixel-ish or it says nothing. `demo30` (47.9 px net span,
  5.5%/px) is simply below the instrument's resolution — its +75.4% means "unmeasurable".
- Search **height, not rows**: projecting the net at a fake `h' = 0.914*H_fit/H` under the
  fitted pose generates the exact candidate-tape family (right columns, slope, curvature).
  Searching image rows is only valid at one column.
- The residual few-percent spread is **court-specific, not noise** — four courts appear twice
  and each pair agrees in sign to <=2.6 pp. Net sag / non-regulation stringing is the leading
  explanation, and the tape alone can never separate it from camera height (two unknowns,
  one observation). The **net POSTS at 1.07 m don't sag** and are the tiebreaker.
- Refusal is the feature: 12/27 refused, including the known-good `yt_rally2`. A refusal
  carries no verdict on the calibration.
- Open: `sAjkpeRq4P4` — qa's hand profile says tape row 406-409, the matched filter says 437.8
  (= the model). ~30 px apart, -33% vs +5.4%. Needs an eye. See [[net-ground-vs-net-tape]].
