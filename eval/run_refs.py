"""eval/run_refs.py - MEASURED court error on clips with a human-placed calibration.

eval/frames has no ground truth, so eval/run_eval.py --drop can only say "it
locked", never "it locked to the right place". This closes that gap on the subset
where a human already placed the corners by hand.

WHAT COUNTS AS A REFERENCE HERE. Only `data/<clip>_pts.json` carrying
`"_exact": true`, MINUS the four clips in `EXCLUDED_CLIPS` below.

POOL SIZE IS 16, AND WAS 20 UNTIL 2026-09-09. The founder took the strict
reading of "one camera setup" and dropped `A7vXlWIlyrI`, `HoHxFSX_gLk_s1`,
`HoHxFSX_gLk_s2` and `UHf0LeMU2pg`. The rule, the per-clip reason and the
measurement each one failed are in `EXCLUDED_CLIPS`; the evidence is
`docs/evidence/clip-shot-map.md`. **Every figure published as an `/20` against
this pool is now STALE** - it was correct when measured and is not re-measurable
by simply re-running this script. The list of them is
`docs/evidence/pool-strict-16.md`. Shell-clip figures are untouched: all 10
shell references come from commit 7c8b8af and none was dropped.

WHAT `_exact` ACTUALLY MEANS - corrected 2026-09-09, it is NOT what this file
used to claim. Read tools/court_setup_server.py's /api/save: the flag is written
whenever the browser's "Shape lock" checkbox happened to be UNCHECKED at the
moment Save was pressed. That is all it records. It says the saved corners were
NOT run through lock_shape; it says NOTHING about who or what placed them. The
tool serves a localhost page and cannot tell a person's mouse from an agent's
HTTP POST, so an agent driving it with the box unticked produced a file
indistinguishable from a human's - and did, in the 2026-08-11/12 batch (see
docs/evidence/calibration-provenance.md and the warning printed below).

This docstring previously asserted `_exact` meant "the user DELIBERATELY placed
these corners ... a human placement, not a detector output". That was false, and
it is how agent-placed corners entered this scoring pool wearing a human
ground-truth label. Saves made from 2026-09-09 carry a `_provenance` block
instead; its `placed_by` defaults to "unattributed" and must never be read as
"human" either. Existing files were NOT backfilled (repo rule 9).

`data/eala_pts_auto.json` is excluded by name and by rule: scoring the detector
against a court the detector produced is self-grading, which ML_PRACTICES
forbids. Files with neither marker are excluded as provenance-unclear rather
than assumed human.

WHY IT RE-EXTRACTS. eval/collect_frames.py groups a recording's files together
(a trim and its source are the same court), but a calibration belongs to ONE FILE
at ONE resolution. Comparing a fit made on the 1080p source against corners
clicked on a 720p trim would be measuring the resize. So each reference is paired
with the single file whose stem matches its own name, and frames come from there.

The error is the mean distance between the four doubles corners as projected by
the human's homography and by the consensus fit, in that file's own pixels. Two
corners are usually OFF-FRAME on a low mount - that is fine and is the point:
they are projected, not detected.

    backend/.venv/Scripts/python.exe eval/run_refs.py
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

from swingvision.courtfit import DBL  # noqa: E402

# Source videos now live under data/incoming/<surface>/, so resolve a reference to
# its file by searching that tree rather than a fixed list of legacy folders.
SEARCH_ROOT = "data/incoming"

ACCEPT_VOTES, ACCEPT_K = 6, 8

# WHICH COMMIT LAST WROTE EACH REFERENCE'S FOUR CORNER NUMBERS.
# Measured 2026-09-09 by diffing the non-underscore keys of every version of
# every data/*_pts*.json against its parent, so a commit that only stamped
# `_audit` (20a672e, 1b3f623 for most files) is NOT credited with the placement.
# Frozen here rather than shelled out to git on every run: `git show` per commit
# per file takes ~30 s, and this pool changes about twice a month. Regenerate
# with the recipe in docs/evidence/calibration-provenance.md if a file is
# re-placed. A clip missing from this map prints as "unknown", never as "clean".
CORNER_SOURCE_COMMIT = {
    "A7vXlWIlyrI": "3399d58", "CYqapSq5llo": "6a3e10f",
    "HoHxFSX_gLk_s1": "3399d58", "HoHxFSX_gLk_s2": "1b3f623",
    "e8T34KoJzOw_s2": "3399d58", "tc8CGFxyRE8": "3399d58",
    "UHf0LeMU2pg": "3399d58", "uR5q2cSM6AY": "3399d58",
    "sAjkpeRq4P4": "209b6b5", "am_hard_utr": "d3f84af",
    "flexi_franz_p01": "7c8b8af", "flexi_franz_p07": "7c8b8af",
    "flexi_joy_p01": "7c8b8af", "flexi_joy_p07": "7c8b8af",
    "hillsborough_p02": "7c8b8af", "hillsborough_p08": "7c8b8af",
    "mpc_mixed_p02": "7c8b8af", "mpc_mixed_p08": "7c8b8af",
    "mpc_tuesday_p01": "7c8b8af", "mpc_tuesday_p07": "7c8b8af",
}
# The two commits the founder's 2026-09-09 corner-audit review implicated by name.
FLAGGED_COMMITS = ("3399d58", "ac94aab")
# ...but those are two commits of ONE agent calibration session. 3399d58 is its
# closing commit, not its only one, and ac94aab wrote corner values for exactly
# one file (L73ep7JHiJ4) which is not in this pool at all. Counting the session
# is what reproduces the founder's "9 of 20".
FLAGGED_SESSION = ("6a3e10f", "63f304e", "8c29896", "209b6b5", "1b3f623",
                   "3399d58", "ac94aab")
_WARNED = False


def provenance_warning(refs) -> str:
    """The caveat printed above every score. See this module's docstring for why
    `_exact` is not the human-placement marker it was documented to be."""
    src = {clip: CORNER_SOURCE_COMMIT.get(clip, "unknown") for clip, _p, _v in refs}
    named = sorted(c for c, s in src.items() if s in FLAGGED_COMMITS)
    session = sorted(c for c, s in src.items() if s in FLAGGED_SESSION)
    unknown = sorted(c for c, s in src.items() if s == "unknown")
    lines = [
        "!! PROVENANCE WARNING - these references are NOT verified human placements.",
        f"   `_exact` only means the Shape-lock box was unticked at Save; it records",
        f"   nothing about who placed the corners (docs/evidence/calibration-provenance.md).",
        f"   {len(named)}/{len(refs)} clips had their corner values written by "
        f"{' or '.join(FLAGGED_COMMITS)}:",
        f"     {', '.join(named) if named else '(none)'}",
        f"   {len(session)}/{len(refs)} come from the wider 2026-08-11/12 agent",
        f"   calibration session ({', '.join(FLAGGED_SESSION)}), of which 3399d58's own",
        f"   message both claims 'all 10 were verified by eye' and retracts two of its",
        f"   own verdicts. The founder marked 10 of 28 rendered corner sheets WRONG on",
        f"   2026-09-09; that review is open and no clip here has been re-placed.",
    ]
    if unknown:
        lines.append(f"   {len(unknown)} clip(s) with no recorded corner-source commit: "
                     f"{', '.join(unknown)}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# THE STRICT "ONE CAMERA SETUP" EXCLUSION - founder ruling 2026-09-09.
# Pool 20 -> 16. Evidence: docs/evidence/clip-shot-map.md (qa, 2026-09-09) and
# docs/evidence/pool-strict-16.md (the invalidation list for every /20 number
# published before this ruling).
#
# WHY THESE FOUR AND NOT A GLOB. qa's shot map grouped each clip's 8 sampled
# frames (frame_positions(total, 8), the frames this eval actually scores) into
# camera setups with an ORB/RANSAC similarity edge, and every clip cleared the
# pre-registered ">= 6 of 8 in one setup" bar. qa then raised a defect in its own
# instrument: a similarity edge only proves two frames share a REGISTRABLE
# background, which a hard pan-and-zoom still satisfies. Measured INSIDE each
# winning group, backgrounds move up to 188.3 px@640 with a 40% zoom while
# scoring 8/8. One homography cannot hold across that; nine wrong-court distances
# fit inside it.
#
# The strict reading therefore adds this project's EXISTING wrong-court line -
# `WRONG_PX_640 = 20.0`, no new constant - to the bar: a clip qualifies only if
# its scored frames are pairwise LINKED *and* pairwise WITHIN 20 px@640. qa calls
# that quantity `S20`. A clip needs S20 >= ACCEPT_VOTES (6) to be re-placeable at
# all, because a calibration is only accepted when >= 6 of the 8 frames agree.
#
# Second, independent reason (docs/evidence/court-triage-2026-09-09.md): all four
# are edited YouTube with cuts and zooms, while the product's own footage is one
# continuous take. They are unrepresentative of anything this app will ever see.
#
# NOT IMPLEMENTED BY MOVING FILES. `references()` globs `data/*_pts*.json`
# NON-RECURSIVELY; two calibrations parked in `data/amateur_clips/` (bump_ntrp30,
# bump_ntrp30b) were thereby absent from every measurement for weeks with nobody
# aware. An exclusion has to be readable at the point the pool is built.
WRONG_PX_640 = 20.0     # the project's existing wrong-court line; NOT a new number

# clip -> why it is out. Every entry quotes qa's measured S20, the max intra-group
# background displacement and the max zoom, all from docs/evidence/clip-shot-map.md.
EXCLUDED_CLIPS: dict[str, str] = {
    "A7vXlWIlyrI": (
        "S20=3 of 8. Background moves 188.3 px@640 with a 40.0% zoom inside the "
        "winning 8/8 group - the worst zoom in the population. Confirmed by eye: "
        "eval samples 1 and 8 are visibly different zooms. Edited broadcast."),
    "HoHxFSX_gLk_s1": (
        "S20=1 of 8 - the worst in the population; no two scored frames are "
        "within 20 px@640 of each other. 189.5 px / 42.2% zoom, and it also "
        "fails the ORIGINAL bar at G=5. Edited YouTube."),
    "HoHxFSX_gLk_s2": (
        "S20=3 of 8. 105.9 px / 28.5% zoom; passed the original bar only at "
        "exactly G=6, on the line. Edited YouTube; shares a source recording "
        "with _s1, so dropping both removes one recording, not two."),
    "UHf0LeMU2pg": (
        "S20=4 of 8. 28.2 px / 1.1% zoom - a clean cut at frame 4198 rather "
        "than a zoom, but still two setups inside the scored window. Edited "
        "YouTube."),
}

# RETAINED AND FLAGGED, NOT DROPPED - founder ruling, explicit. `uR5q2cSM6AY` is
# the marginal fifth case: S20 = 5, one frame short of ACCEPT_VOTES, 20.5 px@640
# at 0.6% zoom (i.e. it misses by half a pixel, not by a re-frame). The ruling
# keeps it and forbids widening the rule to catch it. Do not add it below without
# a new founder ruling; `backend/tests/test_refs_pool_strict16.py` fails if you do.
FLAGGED_MARGINAL = ("uR5q2cSM6AY",)


def exclusion_note() -> str:
    """Printed with the pool so no consumer scores against 16 clips believing
    they have 20. See EXCLUDED_CLIPS above."""
    lines = [
        f"!! POOL IS STRICT-16 - {len(EXCLUDED_CLIPS)} clips excluded by founder "
        f"ruling 2026-09-09 (docs/evidence/pool-strict-16.md).",
        f"   Rule: pairwise-linked AND pairwise within WRONG_PX_640="
        f"{WRONG_PX_640:.0f} px@640 on the scored frames.",
    ]
    for clip in sorted(EXCLUDED_CLIPS):
        lines.append(f"     - {clip}: {EXCLUDED_CLIPS[clip].split('.')[0]}.")
    lines.append(f"   Retained but FLAGGED marginal: {', '.join(FLAGGED_MARGINAL)}.")
    lines.append("   Any /20 figure published before this ruling is STALE, not wrong - "
                 "see the invalidation list.")
    return "\n".join(lines)


def references() -> list[tuple[str, Path, Path]]:
    """[(clip, pts_path, video_path)] for every `_exact` calibration whose video
    can be identified unambiguously by stem, MINUS the clips in EXCLUDED_CLIPS.

    Returns 16 clips as of the founder's 2026-09-09 strict "one camera setup"
    ruling; it returned 20 before. The four exclusions and the reason for each
    are named in EXCLUDED_CLIPS directly above - read them there, not here.

    `_exact` is a shape-lock-OFF marker, NOT a human-placement marker - see the
    module docstring. The set this returns is unchanged by that correction; only
    what may be claimed about it has changed."""
    out = []
    for p in sorted((REPO / "data").glob("*_pts*.json")):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not d.get("_exact"):
            continue                      # not a deliberate human placement
        stem = p.stem[:-4] if p.stem.endswith("_pts") else p.stem
        if stem in EXCLUDED_CLIPS:
            continue                      # strict one-setup ruling, see above
        vid = None
        for c in (REPO / SEARCH_ROOT).rglob(f"{stem}.mp4"):
            vid = c
            break
        if vid is not None:
            out.append((stem, p, vid))
    # Warn HERE, not in main(): eight other eval scripts import references()
    # directly, and the point is that nobody scores against this pool without
    # seeing the caveat. stderr, so it cannot corrupt a parsed stdout table.
    # Once per process - repeated calls would drown the table they precede.
    global _WARNED
    if not _WARNED:
        _WARNED = True
        print(exclusion_note(), file=sys.stderr)
        print(provenance_warning(out), file=sys.stderr)
    return out


SAMPLE_LO, SAMPLE_HI = 0.05, 0.95


def frame_positions(total: int, k: int) -> list[int]:
    """The frame indices this eval actually scores: `k` evenly spaced over the
    middle 5%-95% of the clip. Head and tail are skipped because clips are
    trimmed by hand and often open on a scoreboard or a walk-on.

    Extracted from `frames_from` unchanged (2026-09-09) so that a tool which
    RENDERS a frame for a human to audit can ask for the same frames the scoring
    sees, structurally rather than by copying the formula. Pinned by
    backend/tests/test_eval_frame_positions.py - the old inline expression is
    reproduced there and asserted equal.

    Consumer: tools/render_corner_audit.py. Before this existed that tool
    rendered frame 0, which on a clip whose camera moves is a frame the scoring
    never looks at."""
    if total <= 0 or k <= 0:
        return []
    lo, hi = int(SAMPLE_LO * total), int(SAMPLE_HI * total)
    return [int(p) for p in np.linspace(lo, hi, k).round().astype(int)]


def frames_from(video: Path, k: int):
    import cv2

    cap = cv2.VideoCapture(str(video))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frames = []
    for pos in frame_positions(total, k):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(pos))
        ok, img = cap.read()
        if ok:
            frames.append((int(pos), img))
    cap.release()
    return frames


def score(clip, pts_path, video, k):
    import cv2  # noqa: F401
    from swingvision import calibration, court, courtfit

    ref = json.loads(pts_path.read_text(encoding="utf-8"))
    named = {kk: v for kk, v in ref.items() if not kk.startswith("_")}
    if not all(n in named for n in DBL):
        return None
    frames = frames_from(video, k)
    if not frames:
        return None
    h, w = frames[0][1].shape[:2]

    fits = [courtfit.auto_fit_frame(im, calibration, court) for _p, im in frames]
    pts, votes = courtfit.consensus(fits)
    tag = "vote" if pts is not None else None
    if pts is None and len(frames) >= 6:
        pts = courtfit.stacked_clay_fit(frames, calibration, court)
        tag = "stack" if pts is not None else None
    accepted = pts is not None and tag == "vote" and votes >= ACCEPT_VOTES

    err = None
    if pts is not None:
        Href = calibration.compute_homography(
            [court.LANDMARKS[n] for n in DBL], [named[n] for n in DBL])
        Hfit = calibration.compute_homography(
            [court.LANDMARKS[n] for n in DBL], [pts[n] for n in DBL])
        err = float(np.mean([
            np.hypot(*(calibration.court_to_image(Href, [court.LANDMARKS[n]])[0]
                       - calibration.court_to_image(Hfit, [court.LANDMARKS[n]])[0]))
            for n in DBL]))
    return {"clip": clip, "w": w, "h": h, "votes": votes, "tag": tag,
            "accepted": accepted, "err": err, "locked": sum(1 for f in fits if f),
            "frames": len(frames), "audit": ref.get("_audit", {}).get("verdict", "?")}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--k", type=int, default=ACCEPT_K)
    ap.add_argument("--json", default=None)
    a = ap.parse_args()

    refs = references()
    print(f"{len(refs)} human-placed calibrations with an identifiable video\n")
    print(f"{'clip':22s} {'res':>10s} {'audit':>11s} {'lock':>5s} {'votes':>5s} "
          f"{'result':>9s} {'err_px':>7s} {'err@640':>8s}")
    print("-" * 84)
    rows = []
    for clip, pts_path, vid in refs:
        r = score(clip, pts_path, vid, a.k)
        if r is None:
            print(f"{clip:22s}  (skipped: no frames or incomplete corners)")
            continue
        rows.append(r)
        # normalise to the gold set's 640-wide frames so the number is comparable
        # to the 3.4-13.9 px accepted band in data/output/court_consensus_bar.md
        e640 = None if r["err"] is None else r["err"] * 640.0 / r["w"]
        res = ("ACCEPTED" if r["accepted"] else "stk" if r["tag"] == "stack"
               else f"vote<{ACCEPT_VOTES}" if r["tag"] == "vote" else "refused")
        err_s = "-" if r["err"] is None else f"{r['err']:.1f}"
        e640_s = "-" if e640 is None else f"{e640:.1f}"
        print(f"{r['clip']:22s} {r['w']}x{r['h']:<5d} {r['audit']:>11s} "
              f"{r['locked']:>2d}/{r['frames']:<2d} {r['votes']:5d} {res:>9s} "
              f"{err_s:>7s} {e640_s:>8s}")
    acc = [r for r in rows if r["accepted"] and r["err"] is not None]
    if acc:
        e = [r["err"] * 640.0 / r["w"] for r in acc]
        print("-" * 84)
        print(f"ACCEPTED {len(acc)}/{len(rows)} with a reference.  "
              f"err@640 median {np.median(e):.1f} px, range {min(e):.1f}-{max(e):.1f}")
        print("The gold set's accepted band is 3.4-13.9 px at 640 wide "
              "(data/output/court_consensus_bar.md); >20 px there has always been a wrong court.")
    if a.json:
        Path(a.json).write_text(json.dumps(rows, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
