"""Extract uniform frames from a clip for COURT gold-labeling.

A tennis court barely moves within a clip, so a handful of frames spread across
the clip is enough to catch any camera drift/zoom. This is the court analogue of
select_gold_frames.py (which stratifies by BALL motion — irrelevant here).

Writes, under --out (default data/gold/):
  <clip>.court.manifest.json          frame list + video metadata (committed)
  frames/<clip>/f<NNNNN>.jpg          extracted frames, original resolution
                                      (gitignored; regenerable with --extract-only)

Then open the labeler and pick the Court page:
  py tools/gold_label_server.py   ->  click "Court quality" in the header

Usage (repo root; backend venv has cv2, but any python with opencv works):
  backend/.venv/Scripts/python.exe tools/court_gold_frames.py data/myclip.mp4
  backend/.venv/Scripts/python.exe tools/court_gold_frames.py data/myclip.mp4 --clip lowangle1 --n 18
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def extract(video_path: Path, frames_dir: Path, frame_numbers: list[int]) -> None:
    """Single sequential decode pass — exact frames, no codec seek drift."""
    import cv2

    wanted = set(frame_numbers)
    frames_dir.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(str(video_path))
    i, done = 0, 0
    while done < len(wanted):
        ok, frame = cap.read()
        if not ok:
            break
        if i in wanted:
            cv2.imwrite(str(frames_dir / f"f{i:05d}.jpg"), frame,
                        [cv2.IMWRITE_JPEG_QUALITY, 92])
            done += 1
        i += 1
    cap.release()
    if done < len(wanted):
        raise SystemExit(f"video ended early: got {done}/{len(wanted)} frames")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("video", help="path to the clip (e.g. data/myclip.mp4)")
    ap.add_argument("--clip", default=None, help="short id (default: the filename)")
    ap.add_argument("--n", type=int, default=18, help="frames to sample (default 18)")
    ap.add_argument("--out", default="data/gold")
    ap.add_argument("--extract-only", action="store_true",
                    help="re-extract JPEGs for an existing manifest (after re-clone)")
    ap.add_argument("--to-eval", action="store_true",
                    help="dump the frames into eval/frames/<clip>/ for eval/run_eval.py "
                         "instead of data/gold/. NO manifest and NO gold declaration: this "
                         "is the look-at-it drop-zone, not the labelled TEST set, so it "
                         "commits you to nothing and yields no ground truth.")
    args = ap.parse_args()

    import cv2
    import numpy as np

    video_path = Path(args.video)
    if not video_path.is_absolute():
        video_path = REPO / args.video
    if not video_path.exists():
        raise SystemExit(f"cannot find video: {video_path}")
    clip = args.clip or video_path.stem
    out_dir = REPO / args.out
    frames_dir = ((REPO / "eval" / "frames" / clip) if args.to_eval
                  else out_dir / "frames" / clip)
    manifest_path = out_dir / f"{clip}.court.manifest.json"

    if args.extract_only:
        man = json.loads(manifest_path.read_text(encoding="utf-8"))
        extract(video_path, frames_dir, [f["frame"] for f in man["frames"]])
        print(f"re-extracted {len(man['frames'])} frames -> {frames_dir}")
        return

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise SystemExit(f"cannot open {video_path}")
    n_video = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()

    # uniform over the middle 96% (skip intro/outro title cards)
    lo, hi = int(0.02 * n_video), max(int(0.98 * n_video) - 1, 1)
    frame_nums = sorted(set(
        int(x) for x in np.linspace(lo, max(lo, hi), args.n).round().astype(int)))

    extract(video_path, frames_dir, frame_nums)

    if args.to_eval:
        # Deliberately no manifest: eval/frames is unlabelled by design. Declaring a
        # clip gold is ONE-WAY (data/gold/court_split.json), so it must be a separate,
        # deliberate act - not a side effect of wanting to look at a surface.
        print(f"{len(frame_nums)} frames -> {frames_dir}")
        print("now: backend/.venv/Scripts/python.exe eval/run_eval.py --drop")
        return

    sha1 = hashlib.sha1()
    with open(video_path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            sha1.update(chunk)

    manifest = {
        "clip": clip,
        "kind": "court",
        "video": args.video,
        "video_sha1": sha1.hexdigest(),
        "width": width, "height": height, "fps": fps,
        "video_frames": n_video,
        "created": time.strftime("%Y-%m-%d %H:%M:%S"),
        "params": {"n": args.n, "sampling": "uniform"},
        "frames": [{"frame": n, "bucket": "court"} for n in frame_nums],
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=1), encoding="utf-8")

    print(f"wrote {manifest_path}")
    print(f"extracted {len(frame_nums)} frames -> {frames_dir}")
    print(f"video: {width}x{height}, {n_video} frames @ {fps:.1f} fps")
    print("\nNext: py tools/gold_label_server.py  ->  click \"Court quality\"")


if __name__ == "__main__":
    main()
