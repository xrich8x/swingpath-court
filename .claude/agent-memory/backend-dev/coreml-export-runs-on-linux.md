---
name: coreml-export-runs-on-linux
description: The Core ML export runs on Linux at 1x CI billing, not just macOS at 10x; the manylinux1 tag trap that hides it, and ultralytics' silent .mlmodel fallback
metadata:
  type: project
---

`coremltools` produces `.mlpackage` files on **Linux**. macOS is not required to export
— only to *run/inspect* a model. Both `tools/export_coreml_p0.py` halves (ball via
`ct.convert`, pose via ultralytics `format="coreml"`) work on `ubuntu-latest`.

**Why:** GitHub-hosted macOS runners bill **10x** on a private repo — the free
2,000 min/month is ~200 macOS-minutes, and the founder does not want to pay for CI.
Linux is 1x. The original macOS choice was reasoning from a **Windows** failure
(`RuntimeError: BlobWriter not loaded`) that said nothing about Linux.

**How to apply:** prefer `.github/workflows/coreml-export-linux.yml`; the `macos-14`
`coreml-export.yml` is the known-good fallback, not the default. Full evidence in
`docs/evidence/coreml-export-on-linux.md`.

Durable facts worth not re-deriving:

- **Tag trap.** `pip download coremltools --platform manylinux_2_17_x86_64` silently
  resolves to **4.0b3** (a 2020 pure-Python wheel) and looks like "no Linux wheel".
  coremltools uses the ancient **`manylinux1`** tag. Use `--platform manylinux1_x86_64`.
  **x86_64 only — there is no aarch64 Linux wheel**, so no ARM runner.
- The Linux wheel ships `libmilstoragepython.so` (BlobWriter — *the* Windows blocker)
  and `libmodelpackage.so` (the `.mlpackage` writer). Only `libcoremlpython.so` is
  macOS-only, and it is used solely for predict/compute-plan/compute-device.
- `MLModel.save()` on a package is `shutil.copytree` — pure Python. Conversion and
  serialization do not fail independently.
- **The Linux artifact is less validated.** With `skip_model_load=False` (our ball path)
  macOS actually loads the model into the Core ML runtime at convert time — a free smoke
  test. Linux skips it. Pose gets no such check on *either* platform because ultralytics
  hard-codes `skip_model_load=True`.
- **`nms=True` is a silent no-op for a POSE model** (ultralytics warns and ignores it for
  any non-detect task). The exported pose `.mlpackage` has **no built-in NMS** — that is
  mine to implement on-device. See [[ane-cost-and-far-player-crop]].
- **Silent-corruption trap:** ultralytics catches a failed `.mlpackage` save and
  re-saves a legacy `.mlmodel`; `export_coreml_p0.py` then renames it onto a
  `.mlpackage` name. Always verify the output is a **directory containing
  `Manifest.json`**, never trust the exit code.
- numpy 2.4+ breaks coremltools export (apple/coremltools#2633) and ultralytics wants
  `<=2.3.5`. Pin at install time — its `check_requirements` downgrade lands too late to
  affect the already-imported numpy. **This hazard applies to the macOS job too.**
