"""court_g10.py - G10: score the step-aware far-line check against its pre-registration.

docs/evidence/court-camera3d.md, "G10: a far-line check that models the step".
Pure arithmetic on the artifacts the gate tools wrote; it runs nothing itself.

    python tools/court_g10.py choose DEV_NO_RUNOFF.json DEV_RUNOFF.json --out choice.json
    python tools/court_g10.py score --choice choice.json \
        --heldout H_NO.json H_RO.json --track T_NO.json T_RO.json --cp1 CP1.json --out G10.json

Every number is measured against the exact synthetic camera that rendered the
frame (sim) or CP1's exact rendering camera; the wrong/right label on CP1 is the
fitted focal length, recomputed from that run.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))
sys.path.insert(0, str(REPO / "tools"))

import court_far_line_gate as G                                    # noqa: E402

S1_CATCH = 0.90
S2_FALSE = 0.02
S3_CHECKED = 0.90
S5_FALSE = 0.02
S5_CHECKED = 0.90
KILL_CATCH, KILL_FALSE = 0.50, 0.10
KNOCK_FRAME = 60
WRONG_LOCK_M = 0.10


def _load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def choose(dev_files):
    rows = [r for f in dev_files for r in _load(f)["rows"]]
    table = G.sweep_table(rows, "stepfit", G.STEP_TOL_GRID, G.STEP_SECOND)
    ch = G.choose(table)
    kill = not any(r["catch"] >= KILL_CATCH and r["false"] <= KILL_FALSE for r in table)
    return {"rule": "highest catch at > 20 cm among tolerances with incremental false <= 1%; "
                    "ties to the larger tolerance (G8's rule, verbatim)",
            "pooled_from": [str(f) for f in dev_files], "n_rows": len(rows),
            "table": table, "choice": ch,
            "far_tol_px_720": None if ch is None else ch["tol_px_720"], "kill": kill}


def score(choice, heldout, track, cp1):
    tol = choice["far_tol_px_720"]
    key = f"{tol}|{G.STEP_SECOND[0]}"
    out = {"far_tol_px_720": tol, "bars": {}, "detail": {}}
    for f in heldout:
        d = _load(f)
        scene = f"runoff {d['stamp'].get('runoff_dn')}"
        r = G.rates(d["rows"], "stepfit", key)
        checked = 1.0 - r["far_unchecked_on_good"]
        out["detail"][f"heldout {scene}"] = {**r, "far_both_checked_on_good": checked}
        out["bars"][f"S1 catch >= {S1_CATCH} ({scene})"] = r["catch"] >= S1_CATCH
        out["bars"][f"S2 incremental false <= {S2_FALSE} ({scene})"] = r["false"] <= S2_FALSE
        out["bars"][f"S3 both far lines checked on good >= {S3_CHECKED} ({scene})"] = (
            checked >= S3_CHECKED)
    for f in track:
        d = _load(f)
        for run in d["runs"]:
            st = run["stamp"]
            scene = f"runoff {st.get('runoff_dn')}"
            fr = run["runs"]["camtrack"]["frames"][KNOCK_FRAME]
            worst = max(fr.values())
            locked = run["locked"][KNOCK_FRAME]
            name = f"S4 seed {st['seed']} frame {KNOCK_FRAME} ({scene})"
            out["detail"][name] = {"worst_m": worst, "locked": locked,
                                   "scope": run["lock_scope"][KNOCK_FRAME],
                                   "status": run["status"][KNOCK_FRAME],
                                   "tracker_cfg": st.get("tracker_cfg")}
            out["bars"][name + " NOT locked (it is > 10 cm out)"] = (
                (not locked) if worst > WRONG_LOCK_M else True)
    a = _load(cp1)["analysis"]["stepfit_arm"][f"{tol}"]
    out["detail"]["S5 CP1 seed 1000"] = a
    out["bars"]["S5 every wrong fit caught"] = a["n_caught"] == a["n_wrong"]
    out["bars"][f"S5 right fits flagged <= {S5_FALSE}"] = a["false_flag_right"] <= S5_FALSE
    out["bars"][f"S5 both far lines checked, right fits >= {S5_CHECKED}"] = (
        a["far_both_checked_rate_right_fit"] >= S5_CHECKED)
    out["bars"][f"S5 both far lines checked, true cameras >= {S5_CHECKED}"] = (
        a["far_both_checked_rate_true"] >= S5_CHECKED)
    out["verdict"] = "PASS" if all(out["bars"].values()) else "FAIL"
    out["failed"] = [k for k, v in out["bars"].items() if not v]
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("choose")
    c.add_argument("dev", nargs="+")
    c.add_argument("--out", required=True)
    s = sub.add_parser("score")
    s.add_argument("--choice", required=True)
    s.add_argument("--heldout", nargs="+", required=True)
    s.add_argument("--track", nargs="+", required=True)
    s.add_argument("--cp1", required=True)
    s.add_argument("--out", required=True)
    a = ap.parse_args()
    if a.cmd == "choose":
        res = choose(a.dev)
        for r in res["table"]:
            print(f"tol {r['tol_px_720']:.2f} catch {r['catch']:.3f} false {r['false']:.3f} "
                  f"false_total {r['false_total']:.3f} unchecked_good {r['far_unchecked_on_good']:.3f}")
        print("chosen:", res["far_tol_px_720"], "kill:", res["kill"])
    else:
        res = score(_load(a.choice), a.heldout, a.track, a.cp1)
        for k, v in res["bars"].items():
            print(f"{'PASS' if v else 'FAIL'}  {k}")
        print("VERDICT", res["verdict"])
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(res, indent=1), encoding="utf-8")
    print("wrote", a.out)


if __name__ == "__main__":
    main()
