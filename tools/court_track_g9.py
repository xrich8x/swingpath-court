"""court_track_g9.py - G9: the FIXED tracker, scored for the first time.

G3 was a KILL and stands. Everything done to `camtrack` since (an independent
paint check every frame, a looser Kalman, detector-free recovery, restarts) has
only DEVELOPMENT numbers, measured on a renderer that could not draw sub-pixel
paint. This scores it under CP1's render order (`--subpixel`), on seeds never
used, against bars pre-registered in docs/evidence/court-camera3d.md, G9, and
committed before the first scored run.

Measured against the EXACT synthetic camera that rendered each frame
(`court_track_sim.line_errors`: C1's 14 line halves, worst perpendicular ground
error of 11 points). The renderer has NO CODEC and NO LENS - an encoder profile
has no bearing on anything here.

The tracker runs at `camtrack.TrackConfig()` as shipped at the scoring commit;
its far-line setting is `camera3d.FAR_LINES_DEFAULT`, stamped RESOLVED.

    cd backend && .venv/Scripts/python.exe ../tools/court_track_g9.py
    ... --arms main --seeds 100 --n 12 --out <scratch>   # smoke, on a SPENT seed
"""
from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))
sys.path.insert(0, str(REPO / "tools"))

import court_track_sim as S                                        # noqa: E402
from swingvision import camera3d, camtrack                         # noqa: E402

OUT = REPO / "data" / "output" / "court_track_g9"

# ---- G9, pre-registered: do not edit after the first scored run -------------
# Seeds 100-102, 200-202, 300-305 and 400-402 are spent (dev, qa, G8). The two
# large-knock arms reuse the main arm's first three seeds ON PURPOSE: the sway
# path is drawn before the knock is added, so each pair differs in the knock
# magnitude and nothing else.
ARMS = {
    "main":   {"seeds": (500, 501, 502, 503, 504, 505), "knock_scale": 1.0},
    "knock3": {"seeds": (500, 501, 502), "knock_scale": 3.0},
    "knock4": {"seeds": (500, 501, 502), "knock_scale": 4.0},
}
N_FRAMES = 120
SS = 2
SUBPIXEL = True
BAR_M = 0.05             # every line p90, pooled over every frame
KILL_M = 0.10            # C1's KILL_M; also the "wrong" line for a claimed lock
STEADY_JUMP_PX = 2.0     # outside S.KNOCK_WINDOW frames from the knock
RECOVER_FRAMES = 15      # every line back within BAR_M


def score(runs):
    """G9's four bars on a list of `court_track_sim.run` outputs (one arm)."""
    ct = [g["runs"]["camtrack"] for g in runs]
    summ = S.summarise(ct)
    names = list(summ["lines"])
    far = [n for n in names if n.startswith("far")]
    rec = summ["knock_recovery_frames"]
    lw, lw_far_only, scopes = [], 0, {}
    for g in runs:
        fr = g["runs"]["camtrack"]["frames"]
        for i, (lk, f) in enumerate(zip(g["locked"], fr)):
            if lk:
                sc = (g.get("lock_scope") or [None] * len(fr))[i]
                scopes[str(sc)] = scopes.get(str(sc), 0) + 1
            if lk and max(f.values()) > KILL_M:
                bad = sorted(n for n in names if f[n] > KILL_M)
                lw.append({"seed": g["stamp"]["seed"], "frame": i,
                           "worst_m": max(f.values()), "lines_over_10cm": bad,
                           "scope": (g.get("lock_scope") or [None] * len(fr))[i]})
                lw_far_only += all(n in far for n in bad)
    bars = {
        "B1_every_line_p90_le_5cm": summ["worst_p90_m"] <= BAR_M,
        "B2_steady_jump_le_2px": summ["max_steady_jump_px"] <= STEADY_JUMP_PX,
        "B3_every_knock_recovered_le_15": all(r is not None and r <= RECOVER_FRAMES
                                              for r in rec),
        "B4_zero_locked_but_wrong": len(lw) == 0,
    }
    kill = (summ["worst_p90_m"] > KILL_M or any(r is None for r in rec) or len(lw) > 0)
    verdict = "PASS" if all(bars.values()) else "KILL" if kill else "INDETERMINATE"
    return {"verdict": verdict, "bars": bars,
            "kill_reasons": {"p90_over_10cm": summ["worst_p90_m"] > KILL_M,
                             "unrecovered_knock": any(r is None for r in rec),
                             "locked_but_wrong": len(lw) > 0},
            "worst_p90_m": summ["worst_p90_m"],
            "worst_line": max(summ["lines"], key=lambda n: summ["lines"][n]["p90"]),
            "max_steady_jump_px": summ["max_steady_jump_px"],
            "knock_recovery_frames": rec,
            "locked_frames": summ.get("locked_frames"),
            "unlocked_frames": summ.get("unlocked_frames"),
            "locked_but_wrong": len(lw), "locked_but_wrong_far_lines_only": lw_far_only,
            "locked_but_wrong_frames": lw, "lock_scope_on_locked_frames": scopes,
            "setup_worst_m": [g["setup_worst_m"] for g in runs],
            "lines": summ["lines"],
            "lock_step_baseline_worst_p90_m": S.summarise(
                [g["runs"]["lock_step"] for g in runs])["worst_p90_m"]}


def _job(j):
    return S.run(j["seed"], j["n"], verbose=False, knock_scale=j["knock_scale"], ss=SS,
                 subpixel=SUBPIXEL, far_lines=camtrack.TrackConfig.far_lines)


def _sha():
    try:
        sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True,
                             text=True, timeout=15).stdout.strip()
        dirty = bool(subprocess.run(["git", "status", "--porcelain", "--", "backend", "tools"],
                                    cwd=REPO, capture_output=True, text=True,
                                    timeout=15).stdout.strip())
        return sha or "unknown", dirty
    except Exception:
        return "unknown", None


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--arms", nargs="+", default=list(ARMS))
    ap.add_argument("--seeds", type=int, nargs="+", default=None,
                    help="override (SMOKE ONLY - the scored seeds are in ARMS)")
    ap.add_argument("--n", type=int, default=N_FRAMES)
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    jobs = [{"arm": arm, "seed": s, "n": a.n, "knock_scale": ARMS[arm]["knock_scale"]}
            for arm in a.arms for s in (a.seeds or ARMS[arm]["seeds"])]
    t0 = time.time()
    with ProcessPoolExecutor(min(a.workers, len(jobs))) as ex:
        got = list(ex.map(_job, jobs))
    sha, dirty = _sha()
    res = {"stamp": {"tool": "tools/court_track_g9.py", "gate": "G9", "commit": sha,
                     "dirty": dirty, "n_frames": a.n, "ss": SS, "subpixel": SUBPIXEL,
                     "codec": None, "lens": None,
                     "tracker_cfg_resolved": got[0]["stamp"]["tracker_cfg"],
                     "far_lines_default": camera3d.FAR_LINES_DEFAULT,
                     "far_reach_px_720": camera3d.FAR_REACH_PX_720,
                     "arms": {k: ARMS[k] for k in a.arms},
                     "seeds_override": a.seeds,
                     "measured_against": "the exact synthetic camera that rendered each frame",
                     "wall_s": round(time.time() - t0, 1)},
           "arms": {}, "runs": []}
    for arm in a.arms:
        runs = [g for j, g in zip(jobs, got) if j["arm"] == arm]
        res["arms"][arm] = score(runs)
    res["runs"] = [{"arm": j["arm"], **g} for j, g in zip(jobs, got)]
    out = Path(a.out or OUT / "G9.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    for arm, s in res["arms"].items():
        print(f"{arm:7s} {s['verdict']:13s} worst p90 {s['worst_p90_m'] * 100:8.2f} cm "
              f"({s['worst_line']})  steady jump {s['max_steady_jump_px']:.2f} px  "
              f"recovery {s['knock_recovery_frames']}  locked-but-wrong "
              f"{s['locked_but_wrong']} (far-only {s['locked_but_wrong_far_lines_only']})  "
              f"unlocked {s['unlocked_frames']}  scopes {s['lock_scope_on_locked_frames']}")
        print(f"        bars {s['bars']}")
    print("wrote", out)


if __name__ == "__main__":
    main()
