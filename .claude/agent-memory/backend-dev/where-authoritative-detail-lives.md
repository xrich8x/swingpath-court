---
name: where-authoritative-detail-lives
description: Which repo docs are authoritative for mobile scope, measured verdicts, and each past result — read these before scoping or proposing anything
metadata:
  type: reference
---

- `docs/evidence/mobile-viability-audit.md` — what ports, what is a rebuild, what is
  blocked on-device. Read it before scoping anything.
- `docs/STATE.md` — the only live record of state. "What has not worked" is ~50 measured
  negatives; check it before proposing. "Withdrawn figures" is machine-read by a commit
  hook — never re-publish a string listed there.
- `docs/evidence/p0-0-coreml-export.md` — why Core ML export needs macOS.
- `docs/evidence/p0-3-crop-around-contact.md` — the P0-3 result and how it was measured.
- `docs/evidence/yt-match40-calibration-is-wrong.md` — the calibration defect that
  invalidated P0-2 on that clip.
- `docs/evidence/audio-impact-feasibility-screen.md` — the audio lane; see
  [[audio-lane-screened-not-measured]].

Related: [[mobile-port-split]], [[ios-architecture-rules]].
