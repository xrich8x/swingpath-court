---
name: ios-latency-harness-built
description: ios/ now holds a full unbuilt Swift latency-measurement app (XcodeGen + CI workflow); design decisions and unverified points, for anyone continuing this before/after the first real build
metadata:
  type: project
---

**2026-09-10.** Before this, `ios/` did not exist at all — no `.xcodeproj`,
`Package.swift`, or `Info.plist` anywhere in the repo (confirmed by grep). It now
holds a complete, XcodeGen-based SwiftUI app (`ios/project.yml`, `ios/App/*.swift`,
`ios/App/Info.plist`) plus `.github/workflows/ios-latency-harness.yml`
(`workflow_dispatch` only) and `ios/README.md`. **None of it has been built, run,
or even `xcodegen generate`-d anywhere — there is no Mac in this project, so the
first real compile happens on the GitHub `macos-14` runner, whenever that workflow
is triggered (not yet, deliberately).** Treat that first CI run as the actual test
of every claim below, not a formality.

**Why:** `docs/DECISIONS_PENDING.md` item −1 found that the P0-0/P0-2 hardware
blocker (sustained throughput, int8-vs-fp32 ship call, pose affordability) wasn't
actually a hardware problem once the founder got an iPhone 17 — it was that no
installable app existed to load `tools/export_coreml_p0.py`'s `.mlpackage` outputs
and time them. This closes that gap. **How to apply:** any future latency number
for this project should come from this harness (or its descendant), on a real
device, not from a synthetic/simulator estimate — and per this project's own
"never quote an unmeasured phone fps" rule, an iPhone 17 number is not an A13 floor
number just because it's the first one measured.

## Design decisions made, and why (don't re-derive, but DO re-verify against
whatever the first CI build actually says)

- **Models load from the app's Documents directory at runtime, NOT bundled into
  the app at build time.** Bundling would tie every model swap (8 variants exist:
  `ballnet_v21.{fp16,int8}`, `yolo11m-pose.{1280,640,384}.{fp16,int8}`) to a fresh
  macOS CI build, and this private repo's macOS runners bill at 10x (~200
  macOS-minutes/month from the free 2,000). Documents-loading costs zero CI
  minutes per swap.
- **Core ML compile happens ON-DEVICE at runtime**, via `MLModel.compileModel(at:)`
  (public API, documented since iOS 11, extended to accept `.mlpackage`
  directories — this is Apple's own mechanism for downloadable/post-install
  models). This is DIFFERENT from Xcode's build-time compile (which only fires
  when a `.mlpackage` is a project resource, i.e. only under the bundling option
  that was rejected). **Not verified by an actual compile — flagged as the
  highest-confidence-but-still-unverified claim in the whole harness.**
- **The pose model's exact Core ML input feature name/type was never determined**
  (ultralytics' native `format="coreml", nms=True` export — would need a Mac to
  inspect the actual `.mlpackage`). Solved by NOT hardcoding it: `ModelRunner.
  dummyInput(for:)` reads `model.modelDescription.inputDescriptionsByName` and
  builds a zero-filled value generically (multiArray or image constraint) for
  whatever is actually declared. Same code path handles BallNet's known `frames`
  (1,9,288,512) input with no special case. If a future session needs the pose
  model's real input name (e.g. to feed it a real frame instead of zeros), the
  first CI build's harness run against a real device will reveal it via the
  app's own error/log output — check there before guessing again.
- **Compute units pinned `.cpuAndNeuralEngine`**, matching both
  `tools/export_coreml_p0.py`'s `ct.ComputeUnit.CPU_AND_NE` and this project's
  standing GPU-background-refusal finding (see MEMORY.md's iOS execution model
  section) — deliberately never `.all`.
- **A real correctness bug caught and fixed before shipping this run**: the
  sustained-measurement loop originally rebuilt the dummy input (a
  1,327,104-element MLMultiArray for BallNet) on every single timed sample
  instead of once per sweep. That would have burned CPU/heat on throwaway array
  construction, confounding the exact thermal-steady-state measurement the
  harness exists to make. Fixed in `ModelRunner.swift` — `dummyInput` is now
  built once per `runSweep` call and threaded through `measure`/`measureOnce`.
  **Lesson for any future on-device timing harness in this project: always check
  whether per-sample setup cost is inside or outside the sustained loop — it is
  very easy to accidentally add heat/CPU load that has nothing to do with the
  thing being measured.**
- **Model transfer path (Windows, no Mac, no cloud): zip the `.mlpackage` on
  Windows → "Apple Devices" (Microsoft Store) File Sharing tab, drag the single
  `.zip` in → iOS Files app → native "Extract".** Chosen specifically to avoid an
  unverified claim (whether Apple Devices' File Sharing preserves a *dragged-in
  folder's* nested structure) by sidestepping it — a zip is one file, and iOS's
  Files app has a native unzip action, so no third-party dependency was needed.
- **Sideloading**: Sideloadly or AltStore, free Apple ID, CI produces an unsigned
  `.ipa` (`CODE_SIGNING_ALLOWED=NO` etc. in `project.yml` and the workflow).
  7-day free-ID re-sign expiry documented in `ios/README.md` — re-run the
  sideload tool against the SAME `.ipa`, no new CI build needed.

## What's still genuinely open (do not treat these as settled)

- Whether the whole thing actually compiles on `macos-14` — first CI run is the
  real test, and per the project's money-cost rule that run should not be
  triggered speculatively.
- Whether `MLModel.compileModel(at:)` really accepts a `.mlpackage` directly
  (very likely, per Apple's own documented use case, but unverified here).
- Whether the generic `dummyInput(for:)` correctly covers whatever feature type
  the ultralytics pose export actually uses — if it doesn't, the app should
  surface a specific "unsupported model feature" error rather than crash (that
  error message includes the feature type's raw enum value, which is itself a
  useful clue for whoever reads it next).
- No latency number of any kind exists yet — this memory describes the
  *instrument*, not a result.
