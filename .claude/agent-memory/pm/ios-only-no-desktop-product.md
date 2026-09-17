---
name: ios-only-no-desktop-product
description: Two rulings of 2026-08-27 — the Python backend is a lab not a product, and the target is iOS/iPadOS A13+ only with Android as companion-only
metadata:
  type: project
---

Two user rulings, 2026-08-27, that reshape every mobile decision.

**1. There is no desktop product.** Verbatim: *"There should be no more desktop product,
at most the desktop is only here to help the ML training of the feature."* The Python
backend + React frontend are a **training and evaluation lab**. The phone is the product.

Consequences worked through:
- **"Parity" is the wrong word** and should be retired. There is no shipping thing to
  match. The goal is *the iOS app becomes the product, using the Python lab as reference
  implementation and as the source of trained weights and tuned constants.*
- **The differential-testing burden drops.** I had scoped proving a court port reproduces
  Python within tolerance on every gold clip. Not needed: **the gold set is the arbiter,
  not the Python code.** The iOS implementation must pass the gate, not match the
  reference. Differential testing demotes from contractual gate to optional debugging
  tool. (And it becomes meaningless if court is rebuilt sensor-first — you are
  deliberately computing something different.)
- The lab must gain a **Core ML export path as a first-class output**, not a side script.

**2. iOS / iPadOS only, A13 or newer.** iPhone 11, iPhone SE 2nd gen, 2020 iPad Pro and
newer; iOS/iPadOS 18+. Follows SwingVision's own supported-device policy. Android is
excluded as a *recording* device for the two reasons SwingVision cites — **60 fps
third-party camera access, and thermal overheating during long tracking sessions**.
Android's only role is **companion**: remote control, and challenging line calls, while a
supported iPhone/iPad records and tracks.

What this deletes: the TFLite/NNAPI export path, operator-coverage intersection, "budget
to a mid-range Android", the NNAPI-silently-falls-back-to-CPU risk, dual-device
benchmarking, the Android app shell and Play Store, and the cross-platform abstraction
inside the shared core. **~13-17 sessions.**

What it enables: **Core ML / ANE is the only inference target and may be designed to
specifically.** It also makes a **native Swift app** the right stack rather than React
Native — every capability this plan now leans on (ARKit, `AVCaptureDevice` intrinsics,
IMU, 60 fps capture control, Core ML, `BGProcessingTask`, `AVAssetReader`) is a native
iOS API, and wrapping all of them in RN bridges buys nothing once there is no second
platform.

**The floor device is an A13, not a recent Pro** — that is what P0 measures against.
A13's Neural Engine is roughly an order of magnitude behind current silicon, and the
iPhone 11 has no LiDAR (LiDAR is Pro/iPad Pro only, so treat it as progressive
enhancement; ARKit plane detection works on all A13 devices).

**Read SwingVision's Android thermal exclusion as third-party corroboration**, in both
directions: a competitor with a shipped product concluded the hardware could not sustain
long tracking — but they *do* sustain it on iPhone, which means the envelope exists and
the question is whether this stack fits inside it, not whether it is possible at all.

Related: [[mobile-parity-first]], [[sensor-assisted-court]], [[parity-before-features]]
