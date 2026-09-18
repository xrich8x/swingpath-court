---
name: g7-separation-audit
description: G7 photometric-separation audit 2026-09-18 — confirmed and strengthened by an independent geometric label, but the held-out verdict is split-seed brittle and every check is blind to the far baseline
metadata:
  type: project
---

**G7 audited 2026-09-18 (commit `1f377af`, section appended to `docs/evidence/court-camera3d.md`).**
Verdict: **CONFIRMED and strengthened**, with three qualifications.

**Why:** one session wrote the 3D camera code and the tests that scored it, so hard rule 1 required
an independent re-derivation. Everything below came from raw rows or my own re-runs.

**How to apply:**

- **Re-derive, don't trust the table — but here the table held.** Population (33 wrong / 365 right of
  398), all seven AUCs, the whole held-out table, the ceiling and the four rules reproduced exactly.
  Note `AUC is NOT computed by tools/court_cost_separation.py` — it was worked out by hand after the
  run, so it is not reproducible from the committed instrument.
- **The strongest move available against a proxy label is to build the label it stands in for.** The
  published label is fitted focal. I built a geometric one (worst line > 0.10 m from the exact
  rendering camera). It adds exactly one trial (32, a 1.37 m lateral shift with the focal right to
  0.01%) and turns 33/33-at-1/365 into **34/34 at 0/364**. A cleaner result than the published one.
- **A held-out verdict set at EXACTLY the pre-registered catch rate is brittle.** `SEPARATES` holds
  on only **3 of 10 split seeds** (seed 0 was pre-registered, so not p-hacking). Two held-out misses
  of 17 flip it to PARTIAL. Quote the whole-population number, which involves no split.
- **The permanent gap: nothing in the repo can see the far baseline.** `paint_check` marks
  `far_baseline` and `far_service` `unchecked` on 398 of 398 trials; the ridge residual inherits the
  same width filter. Inside the accepted set `ridge_found` is constant 1.000 — zero 5 cm resolving
  power. See [[tracker-fixes-hold-on-held-out-seeds]] for the consequence in the tracker.
- **`paint_check`'s thresholds cite a `G5` section that does not exist** anywhere in `docs/` (also
  cited by `camtrack.TrackConfig`). The only record is a bullet list in `.claude/journals/lead.md`.
  The result survives because the untuned ridge residual matches the tuned instrument exactly.
- **libx265 non-determinism is real and isolated to the encoder**: 4 encodes of a byte-identical
  30-frame array give 4 bitrates (18919.7-18945.2 kbps) and differ on ~1.8 M of 2.07 M px. Per-trial
  far-baseline spread 0.24-0.66 cm. Any per-trial codec number in CP1/G1/G7 carries that.
