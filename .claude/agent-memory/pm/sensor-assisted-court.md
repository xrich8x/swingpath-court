---
name: sensor-assisted-court
description: Phone sensors (IMU, AVCaptureDevice intrinsics, ARKit) collapse the court search space — argues for a sensor-first REBUILD, not a C++ port; blocked on a new gold set that does not exist
metadata:
  type: project
---

**Verdict reversal, 2026-08-27: do not port `courtfit.py`. Rebuild court detection
sensor-first.** I had scoped a faithful C++ port and sequenced it last as the worst
ratio in the stack. Phone sensors change the problem.

**The mechanism, and it is specific — not hand-waving.** Desktop court failure is a
**search** problem. `autodetect` searches a 5-parameter grid `(cx, y_near, y_far,
half_width_near, half_width_far)`. Verified in `courtfit.py` (`COARSE_GRID`, ~line 758):
the far-half-width axis is **`[0.20, 0.27, 0.35, 0.42]`**, while all 30 human-measured
courts sit at **0.09-0.22**. The grid is searching almost entirely *outside* the true
distribution — they overlap only in the 0.20-0.22 sliver. And the frames that do find a
court disagree principally about **how WIDE it is**.

A phone supplies for free the priors that search has to guess:
- **Gravity / IMU -> camera roll and pitch directly.** Roll is already measured to matter
  here: roll-aware snap moved a -2.4 deg clip **6.9 px -> 1.8 px**, no-op when level.
- **`AVCaptureDevice` -> camera intrinsics** (focal length, sensor size, distortion),
  where the desktop path currently *fits* the camera — the two amateur clips self-calibrate
  to 86 and 104 deg FOV, a huge spread for a free parameter absorbing error.
- **ARKit plane detection (+ LiDAR on Pro / iPad Pro) -> ground plane and camera height.**

Roll, pitch, FOV and approximate height are exactly the parameters that set apparent
court **width**. So the sensors attack precisely the failure mode. What remains is yaw
plus two ground-plane translations — *where is the phone and which way is it pointing* —
which a user can trivially disambiguate.

**Two caveats that bind:**
1. **Candidate priors, not ground truth** — same status this project gives any geometric
   input not measured by hand. IMU drift, ARKit plane error, nominal-not-per-unit
   intrinsics, a vibrating fence mount. Architecture must be: sensors *narrow* the search,
   image evidence still *decides*, disagreement -> refuse -> manual tap.
2. **The existing gate cannot measure this, in either direction.** All 20 court gold clips
   and all 54 recordings are video files with **no sensor metadata**, so a sensor-assisted
   detector cannot be shown to help *or* to have regressed against the >=12/20 gate. It
   needs a **new gold set: in-app footage with synchronised sensor data plus human corner
   clicks**, under the same one-way TEST/TRAIN discipline. This is a real line item and it
   is the biggest non-code cost in the plan.

**Consequence for phasing:** the in-app capture tool moves *very early* — it is on the
critical path for both the on-device benchmark and the sensor gold set, and the
real-world shooting is human weeks, not sessions. Court *algorithm* work stays late;
court *data collection* starts almost first.

**The trade, stated plainly:** a port is guaranteed to reproduce a 12/20 detector at high
cost; a rebuild might do much better at similar cost, plus data-collection time, plus
real risk of failure. **Manual tap bounds the downside**, which is what makes the rebuild
the right bet.

Related: [[ios-only-no-desktop-product]], [[mobile-parity-first]]
