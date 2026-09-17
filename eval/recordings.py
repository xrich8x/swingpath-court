"""eval/recordings.py - one canonical identity per RECORDING, across gold and drop.

Why this exists. The 20 court gold clips and the 54-recording drop set were reported
all session as independent populations. They are not: **9 of the 20 gold clips share a
source video with the drop set**, and `am_rally32short` IS `yt_tnxkujogch4.mp4` under
another name - the same file, dHash 3 bits apart. A gate gain and a breadth gain were
counted as separate evidence when they were one recording.

The root cause is identity by FILENAME. `collect_frames.py` grouped by filename and
YouTube id, which correctly merges a trim with its source inside the drop set, but
cannot see that a gold clip called `am_rally32short` is a file called
`yt_tnxkujogch4.mp4`. **The gold manifests record the source video in their `video`
field and nothing read it.** This is trap T17 again - "trimming a clip renames it, and
the guard matches on the NAME" - now hit on the evaluation side rather than the
training side.

So: resolve everything to a recording key derived from the SOURCE, and let callers ask
which drop groups are independent of the gold set.

    backend/.venv/Scripts/python.exe eval/recordings.py          # the overlap report
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "eval"))

GOLD = REPO / "data" / "gold"
_YTID = re.compile(r"([A-Za-z0-9_-]{11})")


def _key_for_file(path: Path) -> str:
    """Canonical recording key for a source video path.

    Mirrors collect_frames._group_key so a gold clip and its drop twin land on the
    same string: strip the yt_/e2e_ prefix and any _sN trim suffix, and prefer a
    YouTube id in brackets when the filename carries one."""
    from collect_frames import discover, _group_key

    lineage = {}
    lp = REPO / "data" / "train_clips" / "lineage.json"
    if lp.exists():
        lineage = json.loads(lp.read_text(encoding="utf-8")).get("clips", {})
    return _group_key(path, lineage)


def gold_sources() -> dict[str, dict]:
    """{gold_clip: {'video': str, 'source': str, 'key': str|None}}.

    `key` is None for a clip streamed from YouTube with no local file - those cannot
    overlap the drop set, which is built from local files only."""
    out = {}
    for mf in sorted(GOLD.glob("*.court.manifest.json")):
        clip = mf.name.replace(".court.manifest.json", "")
        m = json.loads(mf.read_text(encoding="utf-8"))
        vid = str(m.get("video", "") or "")
        key = None
        if vid and not vid.startswith("http"):
            key = _key_for_file(Path(vid))
        out[clip] = {"video": vid, "source": str(m.get("source", "") or "local"),
                     "key": key, "sha1": m.get("video_sha1")}
    return out


def drop_keys() -> dict[str, str]:
    """{drop_group: recording_key}. The group name already IS the key, by
    construction in collect_frames - kept explicit so callers never assume it."""
    from collect_frames import discover
    return {g: g for g in discover()}


def overlap() -> dict[str, str]:
    """{gold_clip: drop_group} for every gold clip that is the same recording as a
    drop group. These must never be counted as independent confirmation."""
    dk = set(drop_keys())
    return {c: g["key"] for c, g in gold_sources().items()
            if g["key"] and g["key"] in dk}


def independent_drop_groups() -> list[str]:
    """Drop groups that are NOT also a court gold clip. The honest denominator when
    a drop-set result is offered as evidence beyond the gate."""
    shared = set(overlap().values())
    return sorted(g for g in drop_keys() if g not in shared)


def report() -> None:
    gs, ov = gold_sources(), overlap()
    ind = independent_drop_groups()
    all_drop = drop_keys()
    print(f"court gold clips        : {len(gs)}")
    print(f"drop recordings         : {len(all_drop)}")
    print(f"SHARED recordings       : {len(ov)}   <- not independent evidence")
    print(f"independent drop groups : {len(ind)}\n")
    if ov:
        print("gold clip            is the same recording as")
        print("-" * 52)
        for c, g in sorted(ov.items()):
            print(f"{c:22s} {g}")
    n_stream = sum(1 for v in gs.values() if v["source"] == "youtube-stream")
    print(f"\n{n_stream} gold clips are youtube-stream with no local file - "
          f"genuinely independent of the drop set.")


if __name__ == "__main__":
    report()
