# researcher memory

> **SCOPE: court feature only (founder, 2026-09-17).** Non-court memories were moved to `archive-pre-court-only/` in this folder — history, not work. The full previous index is at `swingpath:docs/archive/2026-09-17-pre-court-only/.claude/agent-memory/<agent>/MEMORY.md`.


Index. Detail in the topic files. Inherited 2026-08-28.

**Before proposing any investigation, read `docs/STATE.md` "What has not worked"** — ~50
rows, each measured here under a pre-registered gate. Nine were re-proposed at least once.

## The existing pipeline

- [Court detection negatives](court-detection-negatives.md) — ~20 rejected approaches; CLOSED 2026-09-05: line detector's ~6.4px vs truth is the ceiling, near-order-of-magnitude with click noise (~5.8px) — manual calibration is the product answer for v1
- [Amateur court literature](amateur-court-literature.md) — the 6 published court/field-registration methods ranked against OUR regime, each with its rule-3 verdict, plus the unreachable-source list (2026-09-09)
- [External research reconciled](external-research-reconciliation.md) — HF/GitHub claims verified first-hand 2026-09-09; upstream's 0.963 is in-distribution broadcast, the 15th keypoint is upstream's own, CourtSide cannot calibrate, Gholamreza = upstream's own training set
- [Court precision, sub-pixel](court-precision-sub-pixel.md) — far BL = 0.14 px line; bias not noise binds; closed line-fit rows can't see sub-px; CP1 test; iOS GDC/intrinsics facts (2026-09-17)
- [SwingVision public method](swingvision-public-method.md) — mount ladder gates line calls by height; 97% self-reported; 2 phones >99%; no public hidden-bounce method; fetch tips (2026-09-16)
- [Project method rules](project-method-rules.md) — gold discipline, threshold scaling, the screening proxy that does not predict the gate

## iOS / on-device

- [iOS background compute](ios-background-compute.md) — no multi-hour background job exists; ANE-only is mandatory
- [Core ML / A13 ANE budget](coreml-ane-budget.md) — the desktop ball-vs-pose cost ratio INVERTS on ANE; int8 buys no speed on A13
- [Sensor court priors](sensor-court-priors.md) — gravity usable, yaw useless, LiDAR does not reach the far baseline; 1 deg pitch = 6 px
- [macOS + A13 device access](macos-and-device-access-options.md) — GH Actions CI for Core ML export; Xcode Performance Report needs a local USB device

**Settled:** iOS only, A13+, Core ML/ANE only. No Android, no TFLite, no NNAPI.
