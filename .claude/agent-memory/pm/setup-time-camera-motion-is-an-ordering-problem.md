---
name: setup-time-camera-motion-is-an-ordering-problem
description: The user propping a phone and walking to the court is a real v1 regime; the answer is calibrate LAST plus an IMU stillness gate, never a court-based motion check
metadata:
  type: project
---

The founder raised "the user moving around to set up the view" on 2026-09-09. It is a real
regime, nothing in the court work addresses it, and **the answer is sequencing, not
perception.**

**Three sub-regimes, three answers:**
- **(a) movement while propping, before recording** — reorder the setup screen so the 4-tap
  calibration happens on a frame captured AFTER the phone is in final position and the user
  has stopped touching it. Deletes the regime by ordering. Zero perception work.
- **(b) is the phone settled** — `CMMotionManager` (accelerometer/gyro), on-device, zero
  inference. "Phone not settled — wait" is a refusal, and the refusal surface is already the
  largest un-owned area in v1. Needs a pre-registered stillness threshold (rule 2).
- **(c) drift during the match** — **CUT from v1.** No threshold can be set.

**Why (b) and (c) must not use the court fit — this is the load-bearing measured fact:**
four *motionless* 4K tripods disagree with **themselves** about the court by
**29.9-37.5 px@640**, and motion compensation is a **0.01 px no-op** on static clips
(`docs/evidence/camera-motion-vs-court-agreement.md`, via its STATE row). The fit's own noise
exceeds the project's 20 px wrong-court line. **You cannot tell whether the camera moved by
watching the court fit wobble** — any court-based drift detector would fire on tripods.

**How to apply:** if anyone proposes detecting camera movement from the court, quote the
29.9-37.5 px self-disagreement and redirect to the IMU. If anyone proposes multi-homography
support for clips with cuts or zooms, note that the product records ONE continuous take from
a propped phone — cuts and zooms are an artefact of our YouTube-sourced eval pool, not of
footage the app will ever see.

**Rule-3 check:** nothing about setup-time motion is in "What has not worked". Mid-match
motion compensation IS measured and dead; these are not that.

Detail: `docs/evidence/court-triage-2026-09-09.md` §D.3, §D.4. Related:
[[live-path-has-no-refusal-surface]], [[two-court-pools-only-one-compromised]].
