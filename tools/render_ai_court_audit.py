"""Render the AI's OWN court-detection guess onto real frames - no human click
shown - so a person can judge the detector's determination directly, separate
from any question about whether the human-clicked ground truth is right.

Companion to tools/render_corner_audit.py (which renders a human's clicks and
nothing else, for exactly the opposite reason - see that file's docstring for
T23). This tool renders the other half: `courtfit.auto_fit_frame`'s own output,
the exact function the shipped pipeline calls to find a court on one frame. No
human corner is drawn anywhere in this image - there is nothing here to anchor
on but the real lines in the photo.

Samples the SAME k=8 frames eval/run_refs.py uses (5%-95% of the clip, evenly
spaced) so a clip's "locked N/8" here means the same thing it means in that
harness and in last night's candidate-proposal-recall audit. For each clip:
  * if at least one of the 8 sampled frames locks, the frame with the smallest
    reprojection spread among locked frames is shown (a stand-in for "the AI's
    best shot"; there is no ground truth in this tool to rank against)
  * if none locks, ONE sampled frame is shown with a plain "NO DETECTION"
    caption - that absence is itself the finding for these clips

Run from the repo root:
  ./backend/.venv/Scripts/python.exe tools/render_ai_court_audit.py
  ./backend/.venv/Scripts/python.exe tools/render_ai_court_audit.py --clips sAjkpeRq4P4 mpc_mixed_p02
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

import cv2
import numpy as np

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))
sys.path.insert(0, str(REPO / "tools"))

from swingvision import calibration, court  # noqa: E402
from swingvision import courtfit as ad  # noqa: E402
from swingvision.courtfit import DBL  # noqa: E402

SEARCH_ROOT = REPO / "data" / "incoming"
K = 8
WHITE = (255, 255, 255)
GREY = (140, 140, 140)
AMBER = (0, 190, 255)
AI_COL = {
    "near_bl_doubles": (60, 220, 255),   # amber-cyan family, distinct from the
    "near_br_doubles": (60, 160, 255),   # human-click tool's green/yellow/blue/
    "far_br_doubles": (255, 100, 60),    # magenta palette, so a viewer who has
    "far_bl_doubles": (200, 60, 255),    # seen both never confuses which is which
}


def find_video(tag: str):
    cands = [REPO / "data" / f"{tag}.mp4"]
    if SEARCH_ROOT.is_dir():
        cands += sorted(SEARCH_ROOT.rglob(f"{tag}.mp4"))
    for sub in ("train_clips", "gold_clips", "amateur_clips", "gold"):
        d = REPO / "data" / sub
        if d.is_dir():
            cands += sorted(d.rglob(f"{tag}.mp4"))
    for v in cands:
        if v.exists():
            return v
    return None


def frames_from(video: pathlib.Path, k: int = K):
    """Identical sampling to eval/run_refs.py: k frames evenly spaced 5%-95%."""
    cap = cv2.VideoCapture(str(video))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frames = []
    if total > 0:
        lo, hi = int(0.05 * total), int(0.95 * total)
        for pos in np.linspace(lo, hi, k).round().astype(int):
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(pos))
            ok, img = cap.read()
            if ok:
                frames.append((int(pos), img))
    cap.release()
    return frames


def quad_spread(quad):
    """A ground-truth-free stand-in for 'how confident is this lock': the
    quad's own edge-length regularity. Not a correctness measure - there is no
    truth in this tool to measure correctness against - only used to pick
    which locked frame to display when more than one locks."""
    pts = np.array([quad[k] for k in DBL], dtype=np.float64)
    edges = np.linalg.norm(np.roll(pts, -1, axis=0) - pts, axis=1)
    return float(np.std(edges))


def run_clip(tag: str, video: pathlib.Path):
    frames = frames_from(video)
    results = []
    for idx, frame in frames:
        try:
            quad = ad.auto_fit_frame(frame, calibration, court)
        except Exception as e:  # noqa: BLE001
            quad = None
            print(f"    [warn] {tag} frame {idx}: auto_fit_frame raised {e!r}")
        results.append({"idx": idx, "frame": frame, "quad": quad})
    return results


def draw(frame, quad, tag, video_name, idx, n_locked, k):
    h, w = frame.shape[:2]
    img = frame.copy()
    off = []
    if quad is not None:
        P = {name: (float(quad[name][0]), float(quad[name][1])) for name in DBL}
        for name in DBL:
            x, y = P[name]
            if not (0 <= x < w and 0 <= y < h):
                off.append(name)
        for a, b in zip(DBL, DBL[1:] + DBL[:1]):
            xa, ya = P[a]
            xb, yb = P[b]
            cv2.line(img, (int(round(xa)), int(round(ya))),
                      (int(round(xb)), int(round(yb))), WHITE, 2, cv2.LINE_AA)
        for name in DBL:
            x, y = P[name]
            xi, yi = int(round(x)), int(round(y))
            if 0 <= xi < w and 0 <= yi < h:
                cv2.drawMarker(img, (xi, yi), AI_COL[name], cv2.MARKER_CROSS, 34, 3)
                cv2.circle(img, (xi, yi), 15, AI_COL[name], 2, cv2.LINE_AA)
                cv2.putText(img, name.replace("_doubles", ""), (xi + 19, yi - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.62, AI_COL[name], 2, cv2.LINE_AA)

    scale = 1280.0 / w
    if abs(scale - 1.0) > 0.01:
        img = cv2.resize(img, (1280, int(h * scale)), interpolation=cv2.INTER_AREA)

    cap_h = 118
    cap = np.zeros((cap_h, img.shape[1], 3), np.uint8)
    if quad is None:
        rows = [
            (f"{tag}   {video_name}   frame {idx}   {w}x{h}", WHITE),
            (f"NO DETECTION on this frame - the shipped court search produced no lock at all.", AMBER),
            (f"Locked on {n_locked} of {k} sampled frames across this clip (0.05-0.95 of its length).", GREY),
            ("This is the AI's own attempt. No human click is shown or used here.", GREY),
        ]
    else:
        rows = [
            (f"{tag}   {video_name}   frame {idx}   {w}x{h}   [AI GUESS]", WHITE),
            (f"Locked on {n_locked} of {k} sampled frames across this clip; this is the steadiest one shown.", GREY),
            ("Ask only: does each cross sit on the real court line it is labeled for?", GREY),
            (("off-frame, not drawn: " + ", ".join(n.replace("_doubles", "") for n in off)
              + "  (normal on a low wide mount)") if off else
             "all four corners are inside the frame", AMBER if off else GREY),
        ]
    for i, (t, c) in enumerate(rows):
        cv2.putText(cap, t, (8, 22 + i * 25), cv2.FONT_HERSHEY_SIMPLEX, 0.52, c, 1, cv2.LINE_AA)
    return np.vstack([cap, img])


def render_clip(tag: str, out_dir: pathlib.Path):
    video = find_video(tag)
    if video is None:
        return {"tag": tag, "status": "NO VIDEO"}
    results = run_clip(tag, video)
    if not results:
        return {"tag": tag, "status": "NO FRAMES"}
    locked = [r for r in results if r["quad"] is not None]
    n_locked = len(locked)
    if locked:
        chosen = min(locked, key=lambda r: quad_spread(r["quad"]))
    else:
        chosen = results[0]
    img = draw(chosen["frame"], chosen["quad"], tag, video.name, chosen["idx"], n_locked, len(results))
    out = out_dir / f"{tag}_ai.png"
    cv2.imwrite(str(out), img)
    return {"tag": tag, "status": "rendered", "out": out.name,
            "locked": n_locked, "of": len(results),
            "shown_frame": chosen["idx"]}


def default_clip_list():
    """Every clip run_refs.py itself scores, so this tool's population matches
    whatever the eval's population currently is.

    That pool is 16 since the founder's 2026-09-09 strict one-setup ruling and
    was 20 before it (eval/run_refs.EXCLUDED_CLIPS). So this default NO LONGER
    reproduces the population behind the pre-ruling proposal-recall numbers -
    see docs/evidence/pool-strict-16.md. To render one of the four dropped
    clips, pass it explicitly with --clips; the exclusion is a scoring-pool
    decision, not a ban on looking at the frames."""
    sys.path.insert(0, str(REPO / "eval"))
    import run_refs  # noqa: E402
    return [stem for stem, _pts, _vid in run_refs.references()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--clips", nargs="*", default=None,
                    help="clip tags to render (default: the run_refs references "
                         "pool, 16 clips since 2026-09-09; dropped clips can "
                         "still be named explicitly)")
    ap.add_argument("--out-dir", default="data/output/ai_court_audit")
    args = ap.parse_args()

    clips = args.clips if args.clips else default_clip_list()
    out_dir = REPO / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    for tag in clips:
        r = render_clip(tag, out_dir)
        rows.append(r)
        print(f"  {r['tag']:28s} {r['status']:10s} "
              + (f"locked {r.get('locked')}/{r.get('of')} shown-frame {r.get('shown_frame')}"
                 if r["status"] == "rendered" else ""))

    (out_dir / "index.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    done = [r for r in rows if r["status"] == "rendered"]
    print(f"\n[ai-corners] {len(done)} rendered of {len(clips)} -> {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
