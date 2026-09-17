"""eval/candidate_audit.py - is the RIGHT ANSWER even in the candidate set?

RUN HISTORY - corrected 2026-09-09. This header used to say "UNRUN. No number in
this repo has been produced by it yet." That was false for at least a fortnight,
and it is trap T24 for the second time (`eval/movers.py` carried the identical
false claim while two docs/STATE.md rows already quoted its results). It is
restated below from git and from what CONSUMED this script's output, because a
file's own prose about its past is not a fact about the present.

  Written 2026-08-24 as step O1 of docs/archive/sessions/SESSION_O_shell_courts.md.
  RUN at least twice:

  * 2026-08-26, commit `424ecdc` ("The court diagnosis harness, and the twelve
    negatives it produced"). The SAME COMMIT that introduced this file also
    committed `data/output/candidate_audit.json` - 10 clips x 8 frames, its own
    output. The docstring shipped saying UNRUN with the run's artifact beside it.
    Consumed by `data/output/court_scoring_diagnosis.md` §10,
    `docs/evidence/indoor-shell-courts.md` (shell: 3/10 reached), and
    `eval/truth_neighbourhood.py`'s header. `--movers` ran the same day; its
    numbers are in docs/evidence/far-player-motion-gate-result.md.
  * 2026-09-09, over the full 20-clip reference pool (`--k 8 --json`), published
    in commit `5e322e2` as docs/evidence/candidate-proposal-recall.md: proposal
    recall 40%, the SEARCH binds rather than the vote, shell worst (2/10).

  `git log` ON THIS FILE PROVES NONE OF THAT - it has been edited once since
  creation. Runs are recorded by their outputs, never by the script.

DO NOT QUOTE `truth_would_pass` (it prints 9/20). It scores the exact human
clicks and fails a clip if any one of 8 frames fails any term - the same all-or-
nothing artifact that got the 0.18-0.31 band numbers withdrawn, and it
self-contradicts: 5 of the 8 clips where a good lock WAS produced come out as
"truth would not pass". The accept-side instrument that works is the
neighbourhood sweep, `data/output/court_scoring_diagnosis.md` §10 (19/20).

STANDING WARNING FOR EVERY NUMBER BELOW - the human courts this scores against
are under review. 9 of the 20 pool clips were placed by an agent that then judged
its own placement (trap T26, docs/evidence/calibration-provenance.md), and the
founder marked 10 of 28 rendered sheets wrong-placed on 2026-09-09. Recall
measured against a wrong court is not recall.

THE QUESTION IT SETTLES
-----------------------
`run_refs.py` reports one number per clip: the consensus court's error, or a
refusal. A refusal tells you nothing about WHY. Two completely different failures
hide behind the same word:

  the search never produced the true court  -> a refuse-only gate CANNOT help,
                                               because there is nothing to save
  it produced it and then lost the vote     -> a refuse-only gate CAN help, by
                                               removing the wrong locks it is
                                               competing against

`flexi_franz` locks 7 of 8 frames and scores 1 vote - it fires every time and finds
a different court each time. Whether that is the first failure or the second decides
the whole session's build order, and nobody has looked.

So: keep every per-frame lock, measure each one against the human court, and say
which of the two it is.

--movers additionally previews the two things Session O would build, BEFORE building
either of them:

  B1  does the foot-projection gate actually separate the good locks from the bad
      on this footage? Reported as feet-in-court fraction per lock. If the good and
      bad locks score the same, the gate is worthless here and should not be built.
  B2  would the horizon crop eat the far baseline? The human court says exactly
      where the far baseline is, so this is checkable now rather than after a
      failed gate run. If the crop row sits BELOW the human far baseline on any
      clip, B2 is dead on that clip.

GROUND TRUTH IS HUMAN ONLY - the `"_exact": true` calibrations that run_refs.py
accepts. `data/eala_pts_auto.json` is excluded there by name and by rule: scoring
the detector against a court the detector produced is self-grading.

    backend/.venv/Scripts/python.exe eval/candidate_audit.py
    backend/.venv/Scripts/python.exe eval/candidate_audit.py --movers --k 8
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "eval"))

from swingvision.courtfit import DBL  # noqa: E402

WRONG_PX_640 = 20.0     # the same empty band the gate uses; NOT a new number


def _err_640(named_a, named_b, calibration, court, scale):
    """Mean landmark distance between two courts, at 640 wide.

    Compares the four doubles landmarks as PROJECTED by each homography, exactly as
    run_refs.score does, so the numbers here and there mean the same thing. Two
    corners are usually off-frame on a low mount; projecting rather than detecting
    them is the point."""
    try:
        Ha = calibration.compute_homography(
            [court.LANDMARKS[n] for n in DBL], [named_a[n] for n in DBL])
        Hb = calibration.compute_homography(
            [court.LANDMARKS[n] for n in DBL], [named_b[n] for n in DBL])
    except Exception:
        return None
    d = [np.hypot(*(calibration.court_to_image(Ha, [court.LANDMARKS[n]])[0]
                    - calibration.court_to_image(Hb, [court.LANDMARKS[n]])[0]))
         for n in DBL]
    return float(np.mean(d)) * scale


def explain(H, frame, fs, calibration, court, cf):
    """Every term of `autodetect`'s white-path accept conjunction, evaluated for one
    homography. Returns (rankv, {condition: bool}, detail).

    WHY THIS AND NOT JUST A SCORE. "Refused" is one word covering several different
    failures, and they have opposite fixes. Handing this the HUMAN court answers the
    question that decides the session: if the search had produced the right answer,
    would the accept rule have taken it? A truth that fails `verify_court` needs a
    different fix from a truth that fails `g >= 0.33`, and both need a different fix
    from a truth the search never generated at all.

    Mirrors the conjunction at courtfit.py:696-712. It is a copy, and copies drift -
    but the terms are not reachable from outside `autodetect`, which returns only a
    winner. tests/test_court_surface_routing.py's approach (pin the property, not the
    implementation) does not apply to a diagnostic that has to see inside."""
    dt, w, h, tol = fs["dt"], fs["w"], fs["h"], fs["tol"]
    g, nl, _n_ev = cf._ori_detail(H, calibration, court, dt, fs["cos2"], fs["sin2"],
                                  w, h, tol, 0.80)
    st, st_m, st_ev, n_across, n_len = cf._structure(H, fs["lines"], calibration,
                                                     dt, w, h, tol)
    corners = {n: calibration.court_to_image(H, [court.LANDMARKS[n]])[0]
               for n in DBL}
    p5 = cf._params_from_corners(corners)
    maha = cf._maha(p5, w, h, fs["prior"])

    sufficient = (st_m >= 4 and n_across >= 2 and n_len >= 2) or nl >= 5
    pose_ok = (maha <= cf.PRIOR_MAHA_MAX
               or (st >= 0.70 and st_m >= 5 and n_across >= 2 and n_len >= 2))
    cond = {
        "scale": not (p5[3] * 2.0 < 0.15 * w or abs(p5[1] - p5[2]) < 0.06 * h),
        "g>=.33": g >= 0.33,
        "suffic": sufficient,
        "pose": pose_ok,
        "struct": st >= cf.STRUCT_MIN or st_ev < 3,
        "verify": bool(calibration.verify_court(frame, H).ok),
    }
    return (g * (0.5 + 0.5 * st), cond,
            {"g": g, "st": st, "st_m": st_m, "n_lines": nl, "maha": maha})


def _largest_agreeing(fits, calibration, court, idxs):
    """How many of the listed locks agree with each other under the shipped rule.

    A pair of correct locks only becomes an acceptance if they also AGREE within
    courtfit.AGREE_PX - two right answers that disagree still lose the vote."""
    from swingvision import courtfit as cf
    best = 0
    for i in idxs:
        n = sum(1 for j in idxs
                if cf._corner_dist(fits[i], fits[j]) <= cf.AGREE_PX)
        best = max(best, n)
    return best


def audit(clip, pts_path, video, k, want_movers):
    from swingvision import calibration, court
    from swingvision import courtfit as cf
    from run_refs import frames_from

    ref = json.loads(pts_path.read_text(encoding="utf-8"))
    truth = {n: v for n, v in ref.items() if not n.startswith("_")}
    if not all(n in truth for n in DBL):
        return None
    frames = frames_from(Path(video), k)
    if not frames:
        return None
    h, w = frames[0][1].shape[:2]
    scale = 640.0 / w

    fits = [cf.auto_fit_frame(im, calibration, court) for _p, im in frames]
    locked = [i for i, f in enumerate(fits) if f]
    errs = {i: _err_640(truth, fits[i], calibration, court, scale) for i in locked}
    good = [i for i in locked if errs[i] is not None and errs[i] <= WRONG_PX_640]

    # WITHIN-FRAME MARGIN. The vote count says how the frames ended up disagreeing;
    # it does not say whether the truth was a close second or never in the running,
    # and those point at opposite fixes. Seven locks each with the true court just
    # behind them is a SCORING problem no matter what the votes say; seven locks
    # with the truth nowhere is a SEARCH problem.
    prior = cf._load_prior()
    wm, tcond, lcond = [], [], []
    for i, (_p, im) in enumerate(frames):
        dt, cos2, sin2, w_, h_, lines = cf._precompute(im, calibration, None)
        fs = {"dt": dt, "cos2": cos2, "sin2": sin2, "w": w_, "h": h_,
              "tol": max(2.0, w_ * 0.006), "lines": lines, "prior": prior}
        Ht = calibration.compute_homography(
            [court.LANDMARKS[n] for n in DBL], [truth[n] for n in DBL])
        rt, ct, _dt_ = explain(Ht, im, fs, calibration, court, cf)
        tcond.append(ct)
        if fits[i]:
            Hl = calibration.compute_homography(
                [court.LANDMARKS[n] for n in DBL], [fits[i][n] for n in DBL])
            rl, cl, _dl = explain(Hl, im, fs, calibration, court, cf)
            lcond.append(cl)
            wm.append(rt - rl)

    pts, votes = cf.consensus(fits)
    cons_err = (_err_640(truth, pts, calibration, court, scale)
                if pts is not None else None)

    # Which accept terms the HUMAN court fails, across the frames - and which of
    # those same terms the detector's own locks passed. A term the truth fails while
    # the locks pass it is a term that is actively selecting AGAINST the right answer,
    # which is a much stronger statement than "the truth scored low".
    fails = sorted({k for c in tcond for k, v in c.items() if not v})
    lock_ok = sorted({k for c in lcond for k, v in c.items() if v})
    against = [k for k in fails if k in lock_ok]

    row = {"clip": clip, "w": w, "h": h, "frames": len(frames),
           "locked": len(locked), "n_good": len(good),
           "best_err": min((errs[i] for i in locked if errs[i] is not None),
                           default=None),
           "errs": sorted(e for e in errs.values() if e is not None),
           "agree_good": _largest_agreeing(fits, calibration, court, good) if good else 0,
           "votes": votes, "cons_err": cons_err,
           "within_margin": float(np.median(wm)) if wm else None,
           "truth_fails": fails,
           "selects_against_truth": against,
           "truth_would_pass": not fails}

    if not locked:
        row["verdict"] = "NO LOCK - the search produces nothing"
    elif not good:
        row["verdict"] = "TRUTH NEVER REACHED - a refuse-only gate cannot help"
    elif len(good) == 1:
        row["verdict"] = "TRUTH REACHED ONCE - needs a second good frame"
    elif row["agree_good"] >= 2:
        row["verdict"] = f"TRUTH REACHED x{len(good)}, AGREEING - gating can convert"
    else:
        row["verdict"] = f"TRUTH REACHED x{len(good)} but they disagree"

    # the within-frame reading overrides the vote reading when they disagree, because
    # it names the stage at fault rather than the symptom
    if row["within_margin"] is not None and not good:
        row["verdict"] += ("; truth OUTRANKS the locks (search/gate lost it)"
                           if row["within_margin"] > 0
                           else "; the locks OUTRANK truth (scoring)")

    if want_movers:
        import movers
        ims = [im for _p, im in frames]
        feet = movers.foot_points(ims)
        row["n_feet"] = len(feet)
        band = movers.foot_band(feet)
        row["foot_band"] = band
        crow = movers.crop_row(feet, h)
        row["crop_row"] = crow

        # B2's known failure mode, checked against the human court rather than
        # discovered later by a failed gate run: where IS the far baseline?
        Ht = calibration.compute_homography(
            [court.LANDMARKS[n] for n in DBL], [truth[n] for n in DBL])
        fb = calibration.court_to_image(
            Ht, [court.LANDMARKS["far_bl_doubles"],
                 court.LANDMARKS["far_br_doubles"]])
        row["far_baseline_y"] = float(np.mean(fb[:, 1]))
        row["crop_safe"] = (crow is None or crow < row["far_baseline_y"])

        # B1's discriminative power, measured before it is built
        def _frac(named):
            try:
                H = calibration.compute_homography(
                    [court.LANDMARKS[n] for n in DBL], [named[n] for n in DBL])
            except Exception:
                return None
            return movers.feet_in_court(H, feet, calibration, court)[0]

        row["feet_truth"] = _frac(truth)
        row["feet_good"] = [_frac(fits[i]) for i in good]
        row["feet_bad"] = [_frac(fits[i]) for i in locked if i not in good]
    return row


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--k", type=int, default=8, help="frames per clip")
    ap.add_argument("--clips", nargs="*")
    ap.add_argument("--movers", action="store_true",
                    help="also preview the B1 foot gate and the B2 crop")
    ap.add_argument("--json", default=None)
    a = ap.parse_args()

    from run_refs import references
    refs = references()
    if a.clips:
        refs = [r for r in refs if r[0] in set(a.clips)]
    print(f"{len(refs)} human-placed calibrations; {a.k} frames each; "
          f"a lock counts as TRUE within {WRONG_PX_640:.0f} px @640\n")

    print(f"{'clip':18s} {'lock':>4s} {'true':>4s} {'agr':>3s} {'best':>6s} "
          f"{'vote':>4s} {'cons':>6s} {'w-marg':>7s}  verdict")
    print("-" * 110)
    rows = []
    for clip, pts_path, vid in refs:
        r = audit(clip, pts_path, vid, a.k, a.movers)
        if r is None:
            print(f"{clip:18s}  (skipped: no frames or incomplete corners)")
            continue
        rows.append(r)
        be = "-" if r["best_err"] is None else f"{r['best_err']:.1f}"
        ce = "-" if r["cons_err"] is None else f"{r['cons_err']:.1f}"
        wm = "-" if r["within_margin"] is None else f"{r['within_margin']:+.3f}"
        print(f"{clip:18s} {r['locked']:4d} {r['n_good']:4d} {r['agree_good']:3d} "
              f"{be:>6s} {r['votes']:4d} {ce:>6s} {wm:>7s}  {r['verdict']}", flush=True)

    # --- would the accept rule take the TRUTH if the search handed it over?
    print(f"\n{'clip':18s} {'truth passes?':>14s}  fails                selects AGAINST truth")
    print("-" * 92)
    for r in rows:
        print(f"{r['clip']:18s} {str(r['truth_would_pass']):>14s}  "
              f"{','.join(r['truth_fails']) or '-':20s} "
              f"{','.join(r['selects_against_truth']) or '-'}")
    npass = sum(1 for r in rows if r["truth_would_pass"])
    print(f"\nthe human court would be ACCEPTED on {npass}/{len(rows)} clips if the "
          f"search produced it.")
    blocked = {}
    for r in rows:
        for k in r["truth_fails"]:
            blocked[k] = blocked.get(k, 0) + 1
    if blocked:
        print("blocking terms: " + ", ".join(
            f"{k} x{v}" for k, v in sorted(blocked.items(), key=lambda kv: -kv[1])))

    print("-" * 110)
    reach = [r for r in rows if r["n_good"] > 0]
    conv = [r for r in rows if r["agree_good"] >= 2]
    print(f"truth is inside the candidate set on {len(reach)}/{len(rows)} clips; "
          f"{len(conv)} have two agreeing good locks a gate could convert.")
    dead = [r["clip"] for r in rows if r["locked"] and not r["n_good"]]
    if dead:
        print(f"gating CANNOT help (locks, none true): {', '.join(dead)}")

    if a.movers:
        print(f"\n{'clip':24s} {'feet':>5s} {'crop':>6s} {'far_bl':>7s} {'safe':>5s} "
              f"{'f@true':>7s} {'f@good':>7s} {'f@bad':>7s}")
        print("-" * 84)
        for r in rows:
            def _m(v):
                v = [x for x in (v or []) if x is not None]
                return f"{np.mean(v):.2f}" if v else "-"
            cr = "-" if r.get("crop_row") is None else str(r["crop_row"])
            ft = "-" if r.get("feet_truth") is None else f"{r['feet_truth']:.2f}"
            print(f"{r['clip']:24s} {r.get('n_feet', 0):5d} {cr:>6s} "
                  f"{r.get('far_baseline_y', float('nan')):7.0f} "
                  f"{str(r.get('crop_safe')):>5s} {ft:>7s} "
                  f"{_m(r.get('feet_good')):>7s} {_m(r.get('feet_bad')):>7s}")
        unsafe = [r["clip"] for r in rows if r.get("crop_safe") is False]
        if unsafe:
            print(f"\nB2 IS DEAD on: {', '.join(unsafe)} - the crop row sits below "
                  f"the human far baseline, so the crop would delete it.")

    if a.json:
        Path(a.json).write_text(json.dumps(rows, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
