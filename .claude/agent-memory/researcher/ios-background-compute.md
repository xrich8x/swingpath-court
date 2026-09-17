---
name: ios-background-compute
description: iOS 18/26 background compute limits for on-device match analysis — BGProcessingTask is minutes not hours, GPU work from background is blocked, ANE is the only legal accelerator
metadata:
  type: project
---

Researched 2026-08-27 for R1 of the approved iOS plan. All published/secondary sources;
nothing measured on a device here.

**The rule: there is no supported way to run multi-hour compute in the iOS background.**
Quinn's canonical "iOS Background Execution Limits" thread (developer.apple.com/forums/thread/685525)
lists every mechanism and none permits continuous execution. `BGProcessingTask` is
**opportunistic, overnight-biased, and measured in minutes** (reports range "several
minutes" to ~10-30 min); Apple DTS states the schedule is an implementation detail.

**Why:** it changes "analyse my match" from one background feature into two products —
a foreground job the user watches, and an opportunistic overnight top-up.
**How to apply:** never plan a phase that assumes an uninterrupted background job.
Resumable checkpointing is core architecture, not a nice-to-have.

## Kill conditions worth not re-deriving

- **CPU Monitor: 80% average CPU over 60 s → SIGKILL.** `BGProcessingTask` is documented
  to disable it while on charger, but a developer measured it firing anyway at 97%
  average (thread/675166). DTS's suspected cause: **declaring another background mode,
  notably `audio`, re-enables the limit.** A tennis recorder is likely to want the audio
  mode. Do not declare it casually.
- **The system terminates background processing tasks when the user picks up the phone.**
- **Force-quit from the app switcher permanently blocks background launches** until the
  user manually reopens the app. No documented override.
- **LLDB disables the watchdogs**, so attached debugging never reproduces any of this.

## The GPU rule, and it binds Core ML

**Submitting Metal work from the background is refused** —
`IOGPUCommandQueueErrorDomain`, "Insufficient Permission (to submit GPU work from
background)". On iOS 26.2 this became a hard **Metal abort / process crash** rather than
a silently revoked job.

Consequence: **Core ML must be pinned to `.cpuAndNeuralEngine`, never `.all`**, anywhere
that can run backgrounded. `.all` lets Core ML place ops on the GPU at its own
discretion, and one GPU-placed layer turns a background job into a crash. This joins R2
at the hip: an op that falls back off the ANE is not just slow, in the background it is
fatal.

**iOS 26 `BGContinuedProcessingTask`** is the purpose-built API for this pattern
(user-initiated, system progress UI, cancellable) and iPhone 11 / A13 does receive iOS 26.
But: GPU use needs the `com.apple.developer.background-tasks.continued-processing.gpu`
entitlement, is **not supported on all devices** (developers report iPhone 16 Pro Max and
M1 iPad Pro returning false), must be probed at runtime via
`BGTaskScheduler.supportedResources`, and a developer testing 30-60 min workloads
reported the expiration handler firing "irregularly" with no discoverable pattern and no
way to learn why.

## What actually ships today

- **Foreground with the screen on** is the only place sustained compute is reliable.
  `isIdleTimerDisabled`. Thermal state, not the OS, is the limit.
- **Apple Photos' background ML is a system-app privilege**, gated on charging + locked +
  Wi-Fi + not Low Power. It is an aspirational UX pattern, not an available API.
- **SwingVision — the direct competitor — runs real-time on-device tracking in the
  foreground on iPhone 11 / SE 2020 and up, iOS 18+.** That is third-party proof the
  thermal envelope exists for a full match. Their model complement is unknown.

Related: [[coreml-ane-budget]]
