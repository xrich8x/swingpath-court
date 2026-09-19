# pm memory

> **SCOPE: court feature only (founder, 2026-09-17).** Non-court memories were moved to `archive-pre-court-only/` in this folder — history, not work. The full previous index is at `swingpath:docs/archive/2026-09-17-pre-court-only/.claude/agent-memory/<agent>/MEMORY.md`.


Index. Detail in the topic files. Inherited 2026-08-28 from the prior planning work.

- [iOS-only, no desktop product](ios-only-no-desktop-product.md) — the Python backend is a training lab, not a product; target is iOS/iPadOS A13+
- [Sensor-assisted court](sensor-assisted-court.md) — IMU/intrinsics/ARKit collapse the search; REBUILD not port; blocked on a sensor gold set that does not exist
- [Human asks are a scarce batched resource](human-asks-are-a-scarce-batched-resource.md) — one batched update, ranked by leverage, artefact built first, dispatched before machine work
- [Cheap tests that close a line](cheap-tests-that-close-a-line.md) — price a cheap experiment by what its FAILURE closes; riders get no gate; pre-write the row both ways
- [No confirmed metric footage exists](project-owns-no-confirmed-metric-footage.md) — all four named mounts are 1.36-1.74 m; per-clip status, and the 15-min recording ask that is now top of the queue
- [Two court pools, only one compromised](two-court-pools-only-one-compromised.md) — the 12/20 gate scores against GOLD, not the `_exact` REFERENCES that T26 broke; only 2 of 20 confirmed misplaced
- [Setup-time camera motion is an ordering problem](setup-time-camera-motion-is-an-ordering-problem.md) — calibrate LAST + IMU stillness; never detect movement from the court fit (it self-disagrees by 29.9-37.5 px)
- [Seed vs answer is the court cut line](seed-vs-answer-is-the-court-cut-line.md) — points/PnP/pose-regression are SEEDS (K0: 6.65 m); only the paint fit places lines; seed floor height 0.15 m / focal 5%
- [Latency vs 5 cm is the recurring trade](latency-vs-5cm-is-the-recurring-trade.md) — warm 0.020 s vs cold 9.6 s; stateless is measured at p90 9-11 cm, so "make it fast" is a precision proposal
- [No researcher agent](no-researcher-agent.md) — deleted by the founder 2026-09-18; the lead does that work, do not ask for it

**Settled, do not reopen:** iOS only, A13+, Core ML only. 100% on-device, no server ever.
