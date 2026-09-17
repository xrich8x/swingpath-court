# Swing Vision — automatic, live 3D court mapping (iPhone, on-device)

**This repository is currently working on ONE feature: the court.** From a single fixed iPhone camera,
the app finds a tennis court automatically, places every line (doubles alley included) as a 3D court
with a solved camera, infers lines that are out of view from the regulation dimensions, and keeps
tracking the court when the phone moves. Everything runs on the phone.

Everything else this repo once did — ball tracking, line calls, physics, players, scoring, highlights —
is archived in `swingpath:docs/archive/2026-09-17-pre-court-only/` (the old README is there too).

**This is `swingpath-court`, the court-only repository.** `swingpath:` in a path means the MAIN repository, `xrich8x/swingpath`, which holds everything archived and the full pipeline.

## Where to start

- `CLAUDE.md` — orientation and rules.
- `docs/SPEC.md` — what the court feature must do.
- `docs/STATE.md` — what has been measured so far.

## Tests

`python -m pytest tests/` from `backend/`. Five tests (`test_refs_pool_strict16.py` x3, `test_recording_identity.py` x2)
need the source FOOTAGE on disk under `data/incoming/`: `eval/run_refs.references()` searches for the `.mp4` files.
Videos are git-ignored in both repositories, so a fresh clone of the main repository fails them the same way. Copy
the footage in to run them; do not edit the tests.

## Court tools

```bash
# Windows: backend\.venv\Scripts\python.exe
python tools/court_setup_server.py --video clip.mp4            # court overlay setup tool
python ../tools/court_map_ceiling.py --n 400 --seed 0          # C1 court-model test (from backend/)
python -m pytest tests/                                        # from backend/
```
