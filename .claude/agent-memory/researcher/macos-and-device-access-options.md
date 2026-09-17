---
name: macos-and-device-access-options
description: Options and costs for macOS coremltools access and A13 physical-device access, researched for P0-0 — will recur every device-dependent iOS phase
metadata:
  type: project
---

Researched 2026-08-27 to unblock P0-0 (`[[coreml-ane-budget]]`, `docs/evidence/p0-0-coreml-export.md`).
User has no Mac and no A13 device on hand. **Two independent problems — do not
solve with one rental.**

## Problem A — running `coremltools.convert(...)` (no physical device needed)

**Best answer: GitHub Actions macOS CI job.** Confirmed pricing (Jan 2026 cut):
standard macOS runner $0.062/min, large M1/M2 Pro $0.16/min; macOS draws minutes
at a **10x multiplier** against the included allowance, not a separate quota.
GitHub Free private-repo tier (2,000 Linux-equiv min/mo) → **~200 macOS-equivalent
min/mo free.** A convert job is plausibly 5-15 min, so ~15-20 free runs/month.
`coremltools` installs as a prebuilt wheel on GH runners (not built-from-source),
so the M-series build issues that dominate its GitHub issues don't apply.
**Untested caveat:** M1/M2 Pro large runners report **14 GB total storage** —
verify torch+ultralytics+export intermediates fit before relying on this.

Rejected for this step: AWS EC2 Mac / Scaleway Mac-as-a-service both carry a
**24-hour minimum dedicated-host lease — this is Apple's EULA, not a vendor
policy, applies to both** — so even a 10-min job costs ~$15.60 (AWS mac2.metal
$0.65/hr floor) or ~€2.64-5.76 (Scaleway €0.11-0.24/hr). MacinCloud PAYG ($1/hr)
is a reasonable interactive fallback for debugging the export script live, but
strictly worse than free CI for a scripted repeated job.

## Problem B — measuring per-layer compute-unit dispatch + latency on a physical A13

**Confirmed (Apple dev forum thread 767412):** Xcode's Core ML Performance
Report requires the device to show **"Connected"** — a physical USB-pairing
transport to that specific Mac. No remote-network-only mode exists. Renting a
Mac does not solve this alone.

**New risk found, not previously known:** the same thread reports Performance
Reports **crash on iPhone when compute unit = `.all` / `.cpuAndGPU` /
`.cpuAndNeuralEngine`** — only CPU-only-on-iPhone or any-unit-on-Mac reportedly
works. If still current in the iOS 18 toolchain, this blocks the exact
measurement P0-0's gate needs, independent of access method. 55% confidence —
untested by me, cheap to check: this should be the FIRST thing done with any
physical iPhone, before spending money on remote access.

**The workaround (recommended over the Xcode GUI regardless of the bug):**
`MLComputePlan` (Swift, on-device since iOS 17.4) queries per-op compute-device
assignment + estimated cost from your own app code — sidesteps the GUI crash
risk and is the only version of this measurement that's portable to a device
farm's custom-test-execution model. **Nuance: `MLComputePlan` reports the plan
for whatever hardware is EXECUTING it** — calling it via `coremltools` in
Python on a Mac tells you the Mac's own Apple Silicon dispatch, NOT an iPhone
A13's. It only answers the real question if compiled into an app and run on
the iPhone itself.

**Device access options for that harness / the GUI:**
- **AWS Device Farm, custom XCTest**: writes to `$DEVICEFARM_LOG_DIR`, returned
  as a downloadable zip artifact after the run — real mechanism, confirmed
  from AWS docs, not UI-testing-only. $0.17/device-min PAYG; unmetered plans
  $200-250/device/mo (breakeven ~24 hrs/mo device time — overkill here).
  **Not confirmed:** whether iPhone 11 / SE2020 (6-7 yr old hardware) are still
  in the LIVE device pool in 2026 — farms retire old stock, check the console
  before committing, don't trust a stale search result.
- **BrowserStack App Automate**: instrumentation + device logs real-device
  confirmed, but **no confirmed file upload/download from iOS real devices**
  (Android has it, iOS docs don't) — may block retrieving a custom JSON
  artifact. Weaker than AWS Device Farm for this need.
- **Corellium** (virtualized ARM iOS device): judgement call, 60% confidence
  dead end — no confirmation ANE silicon is passed through / faithfully
  emulated by the hypervisor. Exactly the silent-fallback-to-CPU/GPU risk the
  project is trying to catch, from the tool least likely to represent it
  correctly. Don't pursue without explicit vendor confirmation.
- **MacinCloud + FlexiHub**: MacinCloud's own support docs describe plugging a
  **physically-owned** iPhone into any local machine and tunneling it via
  FlexiHub (3rd-party USB-over-IP) to a MacinCloud **Dedicated** server ($59/mo
  Intel 4-core/8GB/120GB, confirmed root access), then using Xcode normally.
  Doesn't remove the need to own the phone — only removes needing to own the
  Mac. **Not confirmed** whether Xcode's Performance Report transport
  (stricter than ordinary run/debug) tolerates the FlexiHub tunnel's latency.

## Buy vs. rent the physical A13 device

Confirmed prices (Aug 2026, Swappa/BackMarket): **iPhone SE 2nd gen $64-98**
(best listing $68), iPhone 11 $121-176. SE2 is cheaper and still the project's
named floor device.

**Breakeven against AWS Device Farm (~$2.50-3.50/session at 15-20 min) is
~20-28 sessions** — lines up almost exactly with the user's own "20-30 future
sessions" framing, meaning owning wins under nearly any real usage projection.
Rentals also structurally cannot give you unhurried sustained-load/thermal
testing (metered billing discourages the long unhurried runs that a real
throttling measurement needs) — and `[[coreml-ane-budget]]` already flags "no
published sustained ANE throughput figure for any A13-generation device" as an
open gap this project needs to close itself.

## Apple Developer Program ($99/yr) — confirmed, does not help

App Store distribution, TestFlight (testers must own their own device —
already known), beta OS, 2 DTS support incidents/yr. **No device-lab or
remote-device-loan benefit found anywhere in Apple's own program page or
general search.** Absence-of-evidence, ~80% confidence there's no such
benefit; a DTS incident is the one authoritative channel to confirm further.

## Recommendation given to PM (2026-08-27)

Right now: stand up GH Actions CI for exports (near-free, permanent) + buy a
used SE2 (~$70-100, breaks even fast, removes hardware-availability risk
permanently) + test the Xcode-crash risk on any borrowed iPhone before
building further tooling around the GUI report. Long-term: owned device + CI
export is very likely cheaper AND higher quality than any recurring rental for
the rest of the iOS build; device farms are a supplementary breadth check
later (other iOS versions/A13-class devices), not the primary path.
