---
name: coreml-ane-budget
description: Core ML / A13 ANE budget for the perception stack — the desktop CPU cost ratio INVERTS on ANE; pose@1280 is the whole budget and int8 buys no speed on A13
metadata:
  type: project
---

Researched 2026-08-27 for R2. **No A13 measurement exists anywhere, public or in this
repo.** Everything below is either a published number on other silicon or my arithmetic,
labelled as such.

## The one number that is published and close to relevant

Ultralytics' own iOS docs: **YOLO26n-pose, 640x640, int8, iPhone 17 Pro (A19 Pro,
16-core ANE), iOS 26.5.2 — 3.9 ms on `.cpuAndNeuralEngine`, 11.9 ms CPU-only.**
That is the *nano* model, at 640, on the newest silicon. Our default is
`yolo11m-pose @ 1280` on an A13.

## The cost ratio INVERTS versus desktop CPU

FLOPs at the operating resolution, not parameter count, is the right proxy on ANE.

| Stage | GFLOPs | Desktop CPU | My A13 ANE estimate |
|---|---|---|---|
| BallNet, 512x288, 9ch U-Net, 1.3M params | ~8-12 (my estimate) | ~0.7 s/frame | ~30-50 ms/frame |
| `yolo11m-pose` @ 640 | ~72 (published) | — | ~250 ms/frame |
| `yolo11m-pose` @ 1280 | ~287 (4x the 640 figure) | ~0.4 s/frame | **~1,000 ms/frame** |

Method for the estimate: scale the 3.9 ms figure by FLOPs ratio (x38 for m@1280 vs
n@640) and by nominal ANE TOPS (A13 ~5-6 vs A19 Pro ~35-40, so ~7x). Optimistic — it
ignores memory bandwidth at 1280 and thermal throttling.

**So on desktop CPU pose was CHEAPER than ball (0.4 vs 0.7). On ANE pose@1280 is roughly
25x the ball.** Any compute arithmetic inherited from the desktop numbers is wrong in
direction, not just magnitude. `mobile-parity-first`'s "ball 0.7 + pose 0.4 = ~1.1
s/frame" does not survive the platform change.

**The largest lever is not quantisation, it is frame rate.** The ball needs every frame;
pose does not. `events.classify_shot` / `classify_spin` need pose at the contact frame;
movement stats need a few Hz. Ball-first, then pose only on contact frames plus a low-rate
sample, is a 5-10x cut at no measured accuracy cost. Nothing about quantisation
approaches that.

## int8 is not a speed lever on an A13

- **int8-int8 compute on the ANE arrived with A17 Pro / M4.** Through earlier silicon
  Core ML stores int8 weights and **dequantises to fp16** (`constexpr_affine_dequantize`).
  On an A13, int8 buys download size and memory bandwidth. It does not buy throughput.
- Ultralytics' `int8=True` CoreML export is **weight-only palettization (W8A16)**, so its
  accuracy cost is small — and so is its A13 speed benefit. The literature on int8 harming
  pose is about **full W8A8 activation quantization**, whose reported cause is YOLO's
  unified `[batch, nKeypoints+5, nFeatures]` head mixing keypoints (regional, high
  precision needed), boxes (uniform) and confidences (bimodal) in one tensor
  (ultralytics#21625). No published OKS/mAP delta was found for it.
- Apple's own published example (ResNet50, W8A8): **1.52 -> 0.94 ms on A16, 0.77 ms on
  A17 Pro**, accuracy 76.14 -> 76.80%. Classification, not pose.

## Silent-fallback triggers to design around

- `computeUnits = .all` lets Core ML place unsupported ops on GPU/CPU **silently**. Pin
  `.cpuAndNeuralEngine`. In the background this is not a perf question — see
  [[ios-background-compute]], GPU submission from background is refused/aborts.
- Flexible/ranged input shapes push work off the ANE. Use fixed or enumerated shapes.
- Ultralytics' `nms=True` embeds NMS as a Core ML pipeline stage; the NMS ML Program is
  **fp16 and required for segment and pose**. Treat the decode/NMS tail as CPU work and
  budget it separately from the backbone.
- Ultralytics' own iOS profiling found **preprocessing (~8 ms) exceeded inference (~7 ms)**
  in a live camera app on an A19 Pro. Preprocessing does not shrink with the model.

## Sustained vs peak — there is no public ANE curve

Every sustained-load figure found was GPU or CPU, not ANE. The best available
(arXiv 2603.23640, LLM decode via MLX on iPhone 16 Pro **GPU**): **-40% of peak within 3
iterations**, settling -41.5%. The paper states plainly that MLX does not target the ANE.
Argmax's iPhone 17 work reports ANE reaching ~15 of 17.5 theoretical TFLOP/s on an
iPhone 16 Pro, but burst.

**Treat "no published sustained ANE throughput figure for any A13-generation device"
as the finding.** Budget a derate and measure.
