---
name: swingvision-public-method
description: What SwingVision publicly discloses (setup ladder, patent, self-reported 97%, 2-phone >99%, no hidden-bounce method) and which sources fetch — verified 2026-09-16, do not re-search
metadata:
  type: reference
---

Full write-up: `docs/evidence/swingvision-teardown.md` (2026-09-16). Founder directive that day:
**the app must call hidden bounces too — do not propose narrowing or more refusals.**

## Facts verified first-hand (do not re-fetch)
- **Mount ladder = their answer to D²/(f·h):** ground mode NO line calls; fence mount "half court line
  calls"; Swing Stick on top of fence "full court line calls". All mounts behind baseline, centre.
  Swing Stick "60 cm above fence" is UNVERIFIED (search summary only).
- **Device floor iPhone 11 / SE 2020 = A13**, iOS 18, 60 fps + 1080p (Apple Dev 2023-06-05),
  ANE "basically not possible without". A user says video capped at HD, not 4K.
- **Live calls are DISABLED on overheating** (App Store release note) — thermal binds them too.
- **97% within 10 cm is SELF-REPORTED** — founder, Second Serve ep 292 (2025-10-16): "hasn't been
  verified by others". **Two phones "one on each side" → "above 99%".** Seeking ITF Silver (95%).
- "Instances when it can't make the call" — Tennis.com 2024-12-08 (verifies SPEC §3). No rate, no cause.
- **No public source describes hidden-bounce handling.** v11.9.65 "volleys incorrectly called out"
  is ambiguous (extrapolation vs volley-as-bounce).
- Patent **US11893808B2** (filed 2020-11-30, granted 2024-02-06; Sahai, Hsu, Balamurugan,
  Ramachandran; Mangolytics → SwingVision Inc): NN maps object pixels + court-line pixels → 3D
  property; trained on radar/lidar/multi-camera 3D at a training event. No physics, occlusion,
  bounce method disclosed.
- ITF PAT-25-037 (2025-10-31) is PAT, not ELC. Report PDF unread. Only independent studies: MDPI
  Appl Sci 2023 (N=5, ICC placement 0.83-0.87) and IJPAS 2024 — neither tests line calls.
- Competitors: In/Out US10143907B2 single net-post cam, bounce = direction change, NO call if unseen,
  Line Devices override; Zenniz 4 cams + 30 mics audio triangulation; Hawk-Eye ~10 cams.

## Fetch tips (this machine)
- swing.vision is client-side: fetch via `https://r.jina.ai/<url>` (FAQ answers still don't render).
- patents.google.com works WITHOUT the `/en` suffix; `/en` and justia DNS-fail.
- ITF / arXiv PDFs do not text-extract; saved copies land outside the project — do not read them.
- **The USPTO-PDF fetch hallucinated "Hawk-Eye" as assignee — never trust a summariser on a
  rasterised PDF.**

Related: [[monocular-3d-geometry]], [[point-boundary-ground-truth]], [[coreml-ane-budget]]
