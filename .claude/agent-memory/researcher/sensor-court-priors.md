---
name: sensor-court-priors
description: What phone sensors can and cannot contribute to court registration — gravity is good, yaw is useless, ARKit/LiDAR do not reach the far baseline; the error budget in pixels
metadata:
  type: project
---

Researched 2026-08-27 for R3, against `[[../pm-agent/sensor-assisted-court]]`.
No published work was found applying phone IMU priors to *sports court* registration.
The gravity-prior literature is robotics/SfM; the sports-field literature is broadcast.
Neither transfers cleanly, and saying so is the finding.

## The DOF arithmetic, which does hold

A ground-plane homography is 8 DOF. Known intrinsics from `AVCaptureDevice` removes the
intrinsic unknowns, leaving R (3) + t (3) = 6. **Gravity fixes roll and pitch, leaving
yaw + 3 translations = 4.** Add camera height (ARKit, close range) and it is 3: yaw and
two ground translations. Published gravity-prior solvers (Ding et al., ACCV 2020;
Fraundorfer et al.) all rest on the same reduction, tested on iPhone 6s image+IMU
sequences — but for egomotion, not court fitting, and they report solver accuracy, not
registration error in metres.

**The current 5-parameter grid `(cx, y_near, y_far, hw_near, hw_far)` is parameterised in
IMAGE space and does not enforce a physically consistent court.** The sensor rebuild
replaces 5 unconstrained image parameters with 3-4 physically meaningful ones. That is
the real argument, and it is stronger than "fewer parameters".

## The error budget — my arithmetic, and it is the decision-relevant part

640-wide frame, ~86 deg horizontal FOV, so f ~= 343 px.

- **1 deg of pitch error = ~6 px of vertical image shift** (f * tan 1 deg). The 20 px
  `WRONG_PX_640` gate is ~3.3 deg of pitch. So gravity may narrow the search; it may not
  fix it. A +/-2-3 deg window is the honest setting.
- **1 deg of roll error = up to ~5.6 px at the image edge** (320 * sin 1 deg).
- **On the GROUND the same 1 deg is catastrophic and must never be trusted directly.**
  At a 1.74 m mount the far baseline at 23 m sits at a 4.33 deg depression;
  dd/dtheta = h/sin^2(theta) = ~305 m/rad = **~5.3 m of ground error per degree of pitch.**
  Sensors constrain the image-space horizon, never the far-baseline distance.

## What each sensor is actually worth

- **Gravity (roll + pitch): usable.** Published static smartphone tilt accuracy spans
  **0.05-0.20 deg best case to ~2.1 deg mean per-device worst case** (Springer, Behavior
  Research Methods 2020, multi-device). At 2.1 deg the pitch prior alone eats ~13 px of a
  20 px budget — so the device spread, not the sensor noise, is what sets the window.
- **Yaw: useless.** Magnetometer-referenced yaw showed **15-45 deg discrepancy between
  two iPhones held at the same true orientation**. Leave yaw to the image or the user.
- **ARKit plane detection: only good near the camera.** Use it for *camera height above
  the local ground plane at 1-3 m*, which is exactly the parameter that sets apparent
  court width. Do not use it to find the court plane at range.
- **LiDAR: out of range.** Apple LiDAR measures to **~5 m** (occasionally 7 m). The near
  baseline may be inside that; the far baseline never is. And there is no LiDAR on the
  A13 floor device anyway.
- **Vibration on a fence mount: no published number exists.** Core Motion fuses gyro and
  accelerometer, so high-frequency shake mostly averages out; the real risk is a *bump*
  that changes the true pose. The IMU is then the **detector** for a stale homography,
  which is a benefit, not a cost. Framing it as noise misses the point.

## Transfer warning

TVCalib (WACV 2023), PnLCalib and the SoccerNet-Calibration numbers are all **broadcast
long-lens soccer**. Farin et al. 2003 (>91% feature detection on badminton/tennis/
volleyball) is also broadcast. None of these tells you anything about a phone on a fence
in a Manila shell court. Do not import a figure from them.
