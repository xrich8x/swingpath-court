---
name: ios-architecture-rules
description: Non-negotiable on-device architecture rules — ANE pinning, fixed input shapes, sequential decode, compact resumable storage, checkpointing
metadata:
  type: project
---

These are constraints, not preferences.

- Pin `computeUnits = .cpuAndNeuralEngine`, never `.all` — a layer that silently lands on
  GPU is a background crash on iOS 26.2, not a slowdown.
- Fixed or enumerated input shapes only; flexible shapes push work off the ANE. For the
  crop path this means **one fixed-size crop per contact, batched** — a variable-shape
  graph loses the ANE and the saving with it.
- Sequential `AVAssetReader` decode only. No random seeking. (Desktop probes should use
  sequential `grab()`/`retrieve()` too — `cap.set(POS_FRAMES)` is a seek.)
- Compact binary, resumable storage. Not JSON-per-frame.
- Checkpoint and resume — iOS has no multi-hour background compute at any tier, and GPU
  submission from the background is refused.
- No server, no API calls, no network. If something appears to need a backend, it needs
  redesigning or cutting — escalate to pm, do not add one.

**Where a DSP port is involved**, add a parity harness rather than assuming: the scipy /
Accelerate disagreement is at the signal edges, which is where a rally starts. See
[[audio-lane-screened-not-measured]].

Related: [[mobile-port-split]], [[ane-cost-and-far-player-crop]].
