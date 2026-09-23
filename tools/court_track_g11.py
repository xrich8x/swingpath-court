"""court_track_g11.py - G11: does a shock hold-off stop a knock claiming a lock?

G9 (docs/evidence/court-camera3d.md) KILLed on its silent-failure bar: on 5 of 6
knock frames the tracker reported `locked` while the court was 41-65 cm out. qa
traced it to 27-34 coherent flow outliers that bend the pose on the knock frame
only, and showed the tracker's own flow signals jump on exactly that frame.
`camtrack.TrackConfig.shock_*` reports such a frame NOT locked, and touches
nothing else. This tool:

  run     renders a VARIED-KNOCK population (size 0.5-2x G9's, any direction,
          any time in 1.5-2.2 s) or G9's own protocol, and tracks it, logging
          every frame's shock signals;
  choose  replays the logged signals offline over a threshold grid (the hold-off
          changes only the reported flag, so replay == running it) and applies
          the pre-registered rule;
  score   applies G11's bars to the scored runs.

Measured against the exact synthetic camera that rendered each frame
(`court_track_sim.line_errors`: C1's 14 line halves).
"""
from __future__ import annotations

import argparse
import itertools
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

WRONG_M = 0.10                 # a lock claimed while any line is past this is WRONG
KNOCK_WINDOW = S.KNOCK_WINDOW  # frames from the knock that are not "steady"
BASE_KNOCK_DEG = math.hypot(1.0, 1.5)       # G9's knock, 1.80 deg
SS, SUBPIXEL = 2, True

# the threshold grid (None = that signal off); fixed with the pre-registration
GRID = {"shock_n_ratio": (None, 0.95, 0.90, 0.85, 0.80),
        "shock_resid_ratio": (None, 2.0, 3.0, 4.0, 6.0),
        "shock_outlier_frac": (None, 0.02, 0.04, 0.06, 0.08)}
MAX_STEADY_FIRE = 0.01         # dev rule: the hold-off may fire on <= 1% of steady frames


def knock_for(seed):
    """G11's varied knock for one seed, drawn from its own stream so the sway
    (court_track_sim's streams) is untouched."""
    r = np.random.default_rng(np.random.SeedSequence([seed, 11]))
    scale = float(r.uniform(0.5, 2.0))
    th = float(r.uniform(0.0, 2.0 * math.pi))
    knock_s = float(np.round(r.uniform(1.5, 2.2) * S.FPS) / S.FPS)
    return {"knock_deg": (BASE_KNOCK_DEG * scale * math.cos(th),
                          BASE_KNOCK_DEG * scale * math.sin(th)),
            "knock_s": knock_s, "scale": scale, "theta_deg": math.degrees(th)}


def _job(j):
    cfg = dict(j.get("track_cfg") or {})
    far_lines = cfg.pop("far_lines", camtrack.TrackConfig.far_lines)
    far_mode = cfg.pop("far_mode", camtrack.TrackConfig.far_mode)
    kw = {}
    if j["protocol"] == "varied":
        k = knock_for(j["seed"])
        kw = {"knock_deg": k["knock_deg"], "knock_s": k["knock_s"]}
    g = S.run(j["seed"], j["n"], verbose=False, ss=SS, subpixel=SUBPIXEL,
              far_lines=far_lines, far_mode=far_mode, track_cfg=cfg,
              runoff_dn=j.get("runoff_dn"), **kw)
    g["g11"] = {"protocol": j["protocol"], **({"knock": knock_for(j["seed"])}
                                              if j["protocol"] == "varied" else {})}
    return g


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


# ---------------------------------------------------------------- replay ----
def frames(runs):
    """One record per frame: (steady?, knock-window?, locked-as-run, worst error,
    shock signals)."""
    out = []
    for g in runs:
        r = g["runs"]["camtrack"]
        k = r["knock"]
        for i, (f, lk, sh, st) in enumerate(zip(r["frames"], g["locked"], g["shock"],
                                                g["status"])):
            out.append({"seed": g["stamp"]["seed"], "i": i, "knock": k,
                        "steady": not (k <= i < k + KNOCK_WINDOW),
                        "locked": bool(lk), "status": st, "worst": max(f.values()),
                        "sh": sh})
    return out


def fires(sh, cfg, scale):
    """The rule `camtrack.CameraTracker._shock` applies, on logged signals."""
    if not sh or not np.isfinite(sh.get("n_ratio", math.nan)):
        return False
    if cfg["shock_n_ratio"] is not None and sh["n_ratio"] < cfg["shock_n_ratio"]:
        return True
    if (cfg["shock_resid_ratio"] is not None and sh["resid_ratio"] > cfg["shock_resid_ratio"]
            and sh["resid_px"] > camtrack.TrackConfig.shock_resid_floor_px_720 * scale):
        return True
    if cfg["shock_outlier_frac"] is not None and sh["outlier_frac"] > cfg["shock_outlier_frac"]:
        return True
    return False


def replay(fr, cfg, scale=S.H / 720.0):
    wrong = steady_fire = steady = knock_held = 0
    for f in fr:
        fire = fires(f["sh"], cfg, scale) and f["status"] == "tracking"
        held = f["locked"] and not fire
        wrong += held and f["worst"] > WRONG_M
        if f["steady"]:
            steady += 1
            steady_fire += fire
        else:
            knock_held += fire
    return {"locked_wrong": wrong, "steady_fire_rate": steady_fire / max(steady, 1),
            "knock_window_fires": knock_held}


def choose(dev_runs):
    fr = frames(dev_runs)
    base = replay(fr, {k: None for k in GRID})
    table = []
    for vals in itertools.product(*GRID.values()):
        cfg = dict(zip(GRID, vals))
        table.append({**cfg, **replay(fr, cfg)})
    ok = [r for r in table if r["locked_wrong"] == 0 and r["steady_fire_rate"] <= MAX_STEADY_FIRE]
    ch = None
    if ok:
        # lowest steady fire rate; ties to MORE knock-window fires; then grid order
        ch = min(ok, key=lambda r: (r["steady_fire_rate"], -r["knock_window_fires"]))
    return {"rule": "zero locked-but-wrong on dev AND steady fire rate <= 1%; the lowest "
                    "steady fire rate; ties to more knock-window fires, then grid order",
            "no_holdoff": base, "n_frames": len(fr), "table": table,
            "choice": None if ch is None else {k: ch[k] for k in GRID}, "choice_row": ch,
            "kill": ch is None}


# ----------------------------------------------------------------- score ----
def score(varied, g9):
    out = {"bars": {}, "detail": {}}
    allr = varied + g9
    lw = []
    for g in allr:
        r = g["runs"]["camtrack"]
        for i, (lk, f) in enumerate(zip(g["locked"], r["frames"])):
            if lk and max(f.values()) > WRONG_M:
                lw.append({"seed": g["stamp"]["seed"], "frame": i, "knock": r["knock"],
                           "worst_m": max(f.values()), "protocol": g["g11"]["protocol"],
                           "shock": g["shock"][i]})
    out["detail"]["locked_but_wrong"] = lw
    out["bars"]["H1 zero locked frames with any line > 10 cm (all 30 knocks)"] = not lw
    fr = frames(allr)
    st = [f for f in fr if f["steady"]]
    held = sum(1 for f in st if f["sh"].get("fired"))
    out["detail"]["steady_frames"] = len(st)
    out["detail"]["steady_holdoffs"] = held
    out["bars"]["H3 hold-off fires on <= 2% of steady frames"] = held / max(len(st), 1) <= 0.02
    import court_track_g9 as G9
    s9 = G9.score(g9)
    out["detail"]["g9_protocol"] = {k: s9[k] for k in
                                    ("worst_p90_m", "worst_line", "max_steady_jump_px",
                                     "knock_recovery_frames", "locked_but_wrong",
                                     "locked_frames", "unlocked_frames", "setup_worst_m")}
    out["bars"]["H2 G9 B1: every line p90 <= 5 cm (G9 protocol)"] = s9["bars"]["B1_every_line_p90_le_5cm"]
    out["bars"]["H2 G9 B2: steady jump <= 2 px (G9 protocol)"] = s9["bars"]["B2_steady_jump_le_2px"]
    out["bars"]["H2 G9 B3: every knock back within 15 frames (G9 protocol)"] = (
        s9["bars"]["B3_every_knock_recovered_le_15"])
    sv = S.summarise([g["runs"]["camtrack"] for g in varied])
    out["detail"]["varied"] = {"worst_p90_m": sv["worst_p90_m"],
                               "knock_recovery_frames": sv["knock_recovery_frames"],
                               "knocks": [g["g11"]["knock"] for g in varied]}
    out["verdict"] = "PASS" if all(out["bars"].values()) else "FAIL"
    out["failed"] = [k for k, v in out["bars"].items() if not v]
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--protocol", choices=("varied", "g9"), required=True)
    r.add_argument("--seeds", type=int, nargs="+", required=True)
    r.add_argument("--n", type=int, default=90)
    r.add_argument("--choice", default=None, help="choose-output: switch the hold-off ON")
    r.add_argument("--far-shipped", action="store_true",
                   help="far lines as camera3d ships them at this commit (the default "
                        "TrackConfig); without it, far lines OFF")
    r.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    r.add_argument("--out", required=True)
    c = sub.add_parser("choose")
    c.add_argument("runs", nargs="+")
    c.add_argument("--out", required=True)
    s = sub.add_parser("score")
    s.add_argument("--varied", nargs="+", required=True)
    s.add_argument("--g9", nargs="+", required=True)
    s.add_argument("--out", required=True)
    a = ap.parse_args()
    if a.cmd == "run":
        cfg = {} if a.far_shipped else {"far_lines": False}
        if a.choice:
            cfg.update({k: v for k, v in json.loads(Path(a.choice).read_text())["choice"].items()})
        jobs = [{"seed": sd, "n": a.n, "protocol": a.protocol, "track_cfg": cfg}
                for sd in a.seeds]
        t0 = time.time()
        with ProcessPoolExecutor(min(a.workers, len(jobs))) as ex:
            got = list(ex.map(_job, jobs))
        sha, dirty = _sha()
        res = {"stamp": {"tool": "tools/court_track_g11.py", "commit": sha, "dirty": dirty,
                         "protocol": a.protocol, "seeds": a.seeds, "n": a.n, "ss": SS,
                         "subpixel": SUBPIXEL, "track_cfg_requested": cfg,
                         "tracker_cfg_resolved": got[0]["stamp"]["tracker_cfg"],
                         "far_lines_default": camera3d.FAR_LINES_DEFAULT,
                         "far_mode_default": camera3d.FAR_MODE_DEFAULT,
                         "measured_against": "the exact synthetic camera that rendered each frame",
                         "wall_s": round(time.time() - t0, 1)},
               "runs": got}
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(json.dumps(res, default=float), encoding="utf-8")
        print("wrote", a.out)
        return
    if a.cmd == "choose":
        runs = [g for f in a.runs for g in json.loads(Path(f).read_text())["runs"]]
        res = choose(runs)
        print("no hold-off:", res["no_holdoff"])
        print("choice:", res["choice"], res["choice_row"], "kill:", res["kill"])
    else:
        load = lambda fs: [g for f in fs for g in json.loads(Path(f).read_text())["runs"]]  # noqa
        res = score(load(a.varied), load(a.g9))
        for k, v in res["bars"].items():
            print(f"{'PASS' if v else 'FAIL'}  {k}")
        print("VERDICT", res["verdict"])
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    print("wrote", a.out)


if __name__ == "__main__":
    main()
