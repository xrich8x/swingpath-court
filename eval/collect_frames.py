"""eval/collect_frames.py - fill eval/frames/ from every video in the repo.

Sweeps the source-footage pools, groups files by the RECORDING they came from,
and drops N frames per recording into eval/frames/<group>/ for eval/run_eval.py.

Why grouping matters. `data/train_clips/*.mp4` were cut from `data/incoming/*.mp4`
(recorded in data/train_clips/lineage.json, written because a trim renames the
footage and defeated the gold guard once - trap T17). A trimmed clip and the
recording it came from are the SAME COURT. Counting both would inflate any
pass-rate by duplicating the easy cases, so one recording contributes one entry
and its frames are spread across whichever files it has.

  backend/.venv/Scripts/python.exe eval/collect_frames.py --list
  backend/.venv/Scripts/python.exe eval/collect_frames.py --n 8
  backend/.venv/Scripts/python.exe eval/collect_frames.py --n 8 --sheets

SELECTION IS DELIBERATELY NOT THE DETECTOR. Choosing "frames with a court" by
asking `courtfit` whether it found a court would select the test set with the
thing under test, and every survivor would pass by construction. So the only
automatic filter here is TECHNICAL - black frames, fades, flat cards, frozen
duplicates - and the court-in-view judgement is made by a human looking at the
contact sheets (--sheets). What gets rejected is printed, never silent.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DROP = REPO / "eval" / "frames"
SHEETS = REPO / "eval" / "sheets"

# Source videos live under data/incoming/<surface>/ (Clay, Hardcourt, Shell,
# Grass). "Raw - Do Not Process" is EXCLUDED on purpose and not merely by name:
# it holds the full-length downloads whose trims are already in the surface
# folders, so sweeping both would count the same court twice - the double-count
# that eval/recordings.py exists to stop.
INCOMING = "data/incoming"
SKIP_DIRS = {"raw - do not process"}


def _pools():
    root = REPO / INCOMING
    if not root.exists():
        return []
    return [d for d in sorted(root.iterdir())
            if d.is_dir() and d.name.lower() not in SKIP_DIRS]


# A YouTube id in square brackets, or as a yt_/e2e_ prefix, or a bare 11-char stem.
_YTID = re.compile(r"\[([A-Za-z0-9_-]{11})\]")


def _ascii(s: str) -> str:
    """The data/incoming filenames are YouTube titles and carry full-width glyphs
    that a cp1252 console cannot encode. Printing must never be the thing that
    crashes a sweep."""
    return s.encode("ascii", "replace").decode("ascii")


_CUT_SUFFIX = re.compile(r"_p\d+$")             # split_by_serve output: name_p07
_HC_CUT = re.compile(r"^(hc\d+)_.*$")           # hand cuts: hc1_2-1 -> hc1


def _group_key(path: Path, lineage: dict[str, str]) -> str:
    """The recording a file belongs to. Same key = same court = one entry.

    N cuts of one recording are ONE court. Counting them separately inflates any
    pass-rate, which is the bug eval/recordings.py exists to stop - and with 88
    hand cuts of three hard-court videos now on disk it would swamp every number.

    Order matters: lineage is authoritative where it exists, and the filename
    patterns are the fallback for cuts made outside these tools."""
    name = path.name
    src = lineage.get(name)                     # a trim -> its source recording
    if src:
        name = src
    m = _YTID.search(name)
    if m:
        return m.group(1)
    stem = Path(name).stem
    for pre in ("yt_", "e2e_"):
        if stem.startswith(pre):
            stem = stem[len(pre):]
    # a trimmed segment (X_s1, X_s2) is the same recording as X
    stem = re.sub(r"_s\d+$", "", stem)
    stem = _CUT_SUFFIX.sub("", stem)            # split_by_serve cuts
    m2 = _HC_CUT.match(stem)                    # hand cuts hc1_2-1 -> hc1
    if m2:
        stem = m2.group(1)
    return stem


def discover() -> dict[str, list[Path]]:
    lineage = {}
    for lp in (REPO / "data" / "train_clips" / "lineage.json",
               REPO / "data" / "incoming" / "lineage.json"):
        if lp.exists():
            lineage.update(json.loads(lp.read_text(encoding="utf-8")).get("clips", {}))
    files = []
    for pool in _pools():
        # RECURSIVE: cuts of a long recording are filed in per-clip subfolders
        # (hc1_2/hc1_2-1.mp4). A non-recursive glob made 88 of them invisible.
        files += sorted(pool.rglob("*.mp4"))
    groups: dict[str, list[Path]] = {}
    for f in files:
        groups.setdefault(_group_key(f, lineage), []).append(f)
    # smallest file first: same court, cheapest decode
    for v in groups.values():
        v.sort(key=lambda p: p.stat().st_size)
    return dict(sorted(groups.items()))


# --- technical rejects (NOT court-likeness) ---------------------------------

def _dhash(img) -> int:
    import cv2

    g = cv2.cvtColor(cv2.resize(img, (9, 8)), cv2.COLOR_BGR2GRAY)
    bits = 0
    for r in range(8):
        for c in range(8):
            bits = (bits << 1) | int(g[r, c + 1] > g[r, c])
    return bits


def _usable(img, seen: list[int]) -> str | None:
    """None = keep. Otherwise the reason it was rejected."""
    import numpy as np

    g = img.mean()
    if g < 12:
        return "black"
    if g > 243:
        return "blown"
    if float(np.asarray(img).std()) < 12:
        return "flat"                      # fade, title card, blank
    h = _dhash(img)
    if any(bin(h ^ s).count("1") <= 4 for s in seen):
        return "duplicate"                 # frozen frame / repeated still
    seen.append(h)
    return None


def _sig(img):
    """A coarse appearance signature: 4x4x(H,S,V) means. Cheap, and it separates
    'the fixed play camera' from 'a close-up', 'the crowd' and 'a title card'
    without knowing anything about tennis."""
    import cv2
    import numpy as np

    hsv = cv2.cvtColor(cv2.resize(img, (64, 64)), cv2.COLOR_BGR2HSV).astype(np.float32)
    return hsv.reshape(4, 16, 4, 16, 3).mean(axis=(1, 3)).ravel()


def dominant_view(cands, keep: int, tol: float = 26.0):
    """Keep the frames that look like each other: the DOMINANT CAMERA VIEW.

    A match recording is one fixed camera, so nearly every frame is in one cluster
    and this is a no-op. A vlog or a broadcast highlight reel is cut - talking
    heads, crowd, replays, graphics - and uniform sampling returns mostly those.
    The play camera is still the view with the most airtime, so the largest
    appearance cluster recovers it.

    THIS IS NOT A COURT DETECTOR and must never become one. It asks "what does
    this video mostly look like", never "is there a court here" - selecting frames
    by asking `courtfit` would hand the test set to the thing under test and make
    every survivor pass by construction. The court-in-view judgement stays with a
    human reading eval/sheets/.

    cands: [(pos, img, sig)]. Returns (kept, cluster_size, n_candidates)."""
    import numpy as np

    if len(cands) <= keep:
        return cands, len(cands), len(cands)
    sigs = np.asarray([c[2] for c in cands])
    d = np.linalg.norm(sigs[:, None, :] - sigs[None, :, :], axis=2) / np.sqrt(sigs.shape[1])
    members = d <= tol
    best = int(members.sum(axis=1).argmax())
    grp = [c for c, m in zip(cands, members[best]) if m]
    n_grp = len(grp)
    if n_grp < keep:                          # cluster too small to fill the quota
        grp = cands
    idx = np.linspace(0, len(grp) - 1, keep).round().astype(int)
    return [grp[i] for i in sorted(set(idx.tolist()))], n_grp, len(cands)


def collect(group: str, files: list[Path], n: int, oversample: int = 3):
    """Seek n usable frames spread across the recording.

    SEEKING (not the sequential decode data/gold uses) is correct here precisely
    because eval/frames has no labels: nothing is keyed to a frame number, so
    keyframe drift costs nothing, and a 944 MB source would otherwise take
    minutes to walk. The gold path must stay sequential - its labels ARE frame
    numbers."""
    import cv2

    out = DROP / group
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)

    want = n * oversample
    per = max(1, want // len(files))
    cands, seen, rejects = [], [], {}
    for f in files:
        cap = cv2.VideoCapture(str(f))
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total <= 0:
            cap.release()
            continue
        lo, hi = int(0.05 * total), int(0.95 * total)
        step = max(1, (hi - lo) // max(1, per))
        for pos in range(lo, hi, step):
            cap.set(cv2.CAP_PROP_POS_FRAMES, pos)
            ok, img = cap.read()
            if not ok:
                continue
            why = _usable(img, seen)
            if why:
                rejects[why] = rejects.get(why, 0) + 1
                continue
            real = int(cap.get(cv2.CAP_PROP_POS_FRAMES)) - 1
            cands.append((max(real, 0), img, _sig(img)))
        cap.release()

    picked, grp_n, cand_n = dominant_view(cands, n)
    for pos, img, _s in picked:
        cv2.imwrite(str(out / f"f{pos:06d}.jpg"), img, [cv2.IMWRITE_JPEG_QUALITY, 92])
    kept = len(picked)
    if kept == 0:
        shutil.rmtree(out, ignore_errors=True)
    return kept, rejects, grp_n, cand_n


def contact_sheet(groups: list[str], path: Path, cols: int = 4, tile: int = 320):
    """One row per clip, `cols` frames wide - so a human can rule on court-in-view."""
    import cv2
    import numpy as np

    rows = []
    for g in groups:
        fs = sorted((DROP / g).glob("*.jpg"))[:cols]
        if not fs:
            continue
        cells = []
        for f in fs:
            im = cv2.imread(str(f))
            h = int(tile * im.shape[0] / im.shape[1])
            cells.append(cv2.resize(im, (tile, h)))
        hh = min(c.shape[0] for c in cells)
        row = np.hstack([c[:hh] for c in cells])
        if row.shape[1] < cols * tile:
            row = np.hstack([row, np.zeros((hh, cols * tile - row.shape[1], 3), np.uint8)])
        cv2.putText(row, g, (8, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.85, (0, 0, 0), 4, cv2.LINE_AA)
        cv2.putText(row, g, (8, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.85, (80, 255, 120), 2, cv2.LINE_AA)
        rows.append(row)
    if not rows:
        return 0
    hh = min(r.shape[0] for r in rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(path), np.vstack([r[:hh] for r in rows]))
    return len(rows)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--n", type=int, default=8, help="frames per recording (8 = the pipeline's own sample)")
    ap.add_argument("--oversample", type=int, default=6,
                    help="candidate positions per kept frame, before the dominant-view "
                         "cluster picks. Higher finds the play camera in a heavily cut video.")
    ap.add_argument("--list", action="store_true", help="show the grouping and exit")
    ap.add_argument("--sheets", action="store_true", help="also write eval/sheets/ contact sheets")
    ap.add_argument("--only", nargs="*", help="restrict to these group keys")
    a = ap.parse_args()

    groups = discover()
    if a.only:
        groups = {k: v for k, v in groups.items() if k in a.only}

    if a.list:
        print(f"{len(groups)} distinct recordings from "
              f"{sum(len(v) for v in groups.values())} files\n")
        for g, fs in groups.items():
            names = ", ".join(f.parent.name + "/" + f.name for f in fs)
            print(f"{g:26s} {len(fs)} file(s)  {_ascii(names)[:110]}")
        return

    done = []
    for g, fs in groups.items():
        kept, rej, grp_n, cand_n = collect(g, fs, a.n, a.oversample)
        tag = "" if kept >= a.n else "  <- SHORT"
        share = (100.0 * grp_n / cand_n) if cand_n else 0.0
        cut = "  <- CUT VIDEO" if share < 60 else ""
        rj = "  rej: " + ", ".join(f"{k}x{v}" for k, v in sorted(rej.items())) if rej else ""
        print(f"{g:26s} {kept:2d} frames  dominant view {grp_n:3d}/{cand_n:3d} "
              f"({share:5.1f}%){tag}{cut}{rj}")
        if kept:
            done.append(g)
    print(f"\n{len(done)} recordings -> {DROP}")

    if a.sheets:
        for i in range(0, len(done), 8):
            batch = done[i:i + 8]
            p = SHEETS / f"sheet_{i // 8:02d}.jpg"
            contact_sheet(batch, p)
            print(f"  {p}  ({', '.join(batch)})")


if __name__ == "__main__":
    main()
