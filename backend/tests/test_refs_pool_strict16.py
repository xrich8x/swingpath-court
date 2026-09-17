"""Pin the court references pool at STRICT-16 (founder ruling, 2026-09-09).

WHY THIS TEST EXISTS. `eval/run_refs.references()` is the denominator of every
"N/20" court figure this project has published, and it is imported by eleven
other eval scripts. It builds itself by globbing `data/*_pts*.json`, so the pool
can change size because somebody added a file, moved a file, or renamed one -
with no diff anywhere that says "the pool changed". That has already happened
once: `bump_ntrp30` and `bump_ntrp30b` sat in `data/amateur_clips/` for weeks,
invisible to a NON-RECURSIVE glob, absent from every measurement, unnoticed.

Silent pool drift is the failure mode. This test makes it loud.

WHAT THE RULING WAS. `docs/evidence/clip-shot-map.md` (qa, 2026-09-09) grouped
each clip's 8 scored frames into camera setups and every clip cleared the
pre-registered ">= 6 of 8 in one setup" bar - but qa flagged a defect in its own
instrument: an ORB/RANSAC *similarity* edge only proves a REGISTRABLE background,
which a hard pan-and-zoom still satisfies. Backgrounds move up to 188.3 px@640
with a 40% zoom INSIDE a winning 8/8 group. The founder therefore took the strict
reading, adding the project's existing `WRONG_PX_640 = 20.0` line to the bar, and
dropped four clips. Pool 20 -> 16. The reasons live next to the code, in
`run_refs.EXCLUDED_CLIPS`; the invalidation list is
`docs/evidence/pool-strict-16.md`.

`uR5q2cSM6AY` is the marginal fifth case (S20 = 5, one frame short) and was
RETAINED and flagged. Widening the rule to catch it needs a new founder ruling,
and this file will fail if anyone does it quietly.

Nothing here decodes a video or scores a court; it is set arithmetic over the
pool definition.
"""

from __future__ import annotations

import json
import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
if str(REPO / "eval") not in sys.path:
    sys.path.insert(0, str(REPO / "eval"))

import run_refs  # noqa: E402

# Restated here deliberately rather than imported, so that editing the pool
# definition cannot also edit the expectation it is checked against.
DROPPED = {"A7vXlWIlyrI", "HoHxFSX_gLk_s1", "HoHxFSX_gLk_s2", "UHf0LeMU2pg"}
RETAINED_MARGINAL = "uR5q2cSM6AY"
POOL_SIZE = 16
POOL_SIZE_BEFORE_RULING = 20

needs_videos = pytest.mark.skipif(
    not (REPO / run_refs.SEARCH_ROOT).exists(),
    reason=f"{run_refs.SEARCH_ROOT} absent - source videos are not in the repo")


# --------------------------------------------------------------------------
# 1. The exclusion is declared in code, with a reason, and names exactly four.
# --------------------------------------------------------------------------

def test_excluded_clips_is_exactly_the_four_named_in_the_ruling():
    assert set(run_refs.EXCLUDED_CLIPS) == DROPPED, (
        "The founder's 2026-09-09 ruling named these four and only these four. "
        "Adding or removing one needs a new ruling, not an edit here.")


def test_every_exclusion_carries_a_reason():
    for clip, reason in run_refs.EXCLUDED_CLIPS.items():
        assert isinstance(reason, str) and len(reason) > 40, (
            f"{clip} is excluded with no usable reason. A bare list of clip "
            f"names is the thing this ruling was explicitly told not to ship.")
        assert "S20" in reason, (
            f"{clip}'s reason must quote the measured S20 from "
            f"docs/evidence/clip-shot-map.md, so a reader can check it.")


def test_the_marginal_clip_is_retained_and_flagged():
    assert RETAINED_MARGINAL not in run_refs.EXCLUDED_CLIPS, (
        "uR5q2cSM6AY was RETAINED by the ruling. It is one frame short of the "
        "vote (S20 = 5) and the rule was explicitly forbidden from widening to "
        "catch it.")
    assert RETAINED_MARGINAL in run_refs.FLAGGED_MARGINAL


def test_wrong_px_640_is_the_projects_existing_constant_not_a_new_one():
    assert run_refs.WRONG_PX_640 == 20.0
    sys.path.insert(0, str(REPO / "eval"))
    import candidate_audit  # noqa: E402
    assert run_refs.WRONG_PX_640 == candidate_audit.WRONG_PX_640, (
        "The strict rule was allowed to re-use the shipped wrong-court line and "
        "nothing else. If these two ever diverge, one of them is a new threshold.")


def test_exclusion_note_names_each_clip_and_cites_the_evidence():
    note = run_refs.exclusion_note()
    for clip in DROPPED:
        assert clip in note
    assert "clip-shot-map.md" in run_refs.__doc__ or "clip-shot-map.md" in note
    assert "pool-strict-16.md" in note
    assert RETAINED_MARGINAL in note


# --------------------------------------------------------------------------
# 2. The exclusion is by RULE, not by hiding files from the glob.
# --------------------------------------------------------------------------

@pytest.mark.parametrize("clip", sorted(DROPPED))
def test_dropped_calibrations_are_still_on_disk_and_still_exact(clip):
    """The four files must remain exactly where they were, still `_exact`, still
    found by the glob. If a future change implements the drop by moving or
    deleting them, this fails - that is the `bump_ntrp30` failure mode, where
    two calibrations vanished from every measurement because a non-recursive
    glob stopped seeing them and nobody noticed."""
    p = REPO / "data" / f"{clip}_pts.json"
    assert p.exists(), (
        f"{p} is gone. The pool exclusion must be visible in code, not "
        f"implemented by moving files out of the glob's reach.")
    d = json.loads(p.read_text(encoding="utf-8"))
    assert d.get("_exact") is True, (
        f"{clip} lost its `_exact` marker. The ruling excluded the clip from the "
        f"pool; it did not authorise editing the file (repo rule 9).")
    globbed = {q.stem[:-4] for q in (REPO / "data").glob("*_pts*.json")
               if q.stem.endswith("_pts")}
    assert clip in globbed


# --------------------------------------------------------------------------
# 3. The pool itself.
# --------------------------------------------------------------------------

@needs_videos
def test_pool_is_sixteen():
    clips = [c for c, _p, _v in run_refs.references()]
    assert len(clips) == POOL_SIZE, (
        f"references() returned {len(clips)}, expected {POOL_SIZE}: "
        f"{sorted(clips)}. The pool changed size. If that was deliberate, every "
        f"published /{POOL_SIZE} figure is now stale and needs adding to "
        f"docs/evidence/pool-strict-16.md before this number is edited.")
    assert len(set(clips)) == len(clips), "a clip appears twice in the pool"


@needs_videos
def test_dropped_clips_are_absent_from_the_pool():
    clips = {c for c, _p, _v in run_refs.references()}
    assert clips.isdisjoint(DROPPED), sorted(clips & DROPPED)


@needs_videos
def test_marginal_clip_is_present_in_the_pool():
    clips = {c for c, _p, _v in run_refs.references()}
    assert RETAINED_MARGINAL in clips


@needs_videos
def test_the_ruling_arithmetic_20_minus_4_is_16():
    """Pin the before/after, not just the after. Reconstructs the pre-ruling pool
    by applying `references()`'s own criteria with the exclusion lifted, so the
    published "20" stays checkable after the code that produced it has changed."""
    before = []
    for p in sorted((REPO / "data").glob("*_pts*.json")):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not d.get("_exact"):
            continue
        stem = p.stem[:-4] if p.stem.endswith("_pts") else p.stem
        if any((REPO / run_refs.SEARCH_ROOT).rglob(f"{stem}.mp4")):
            before.append(stem)
    assert len(before) == POOL_SIZE_BEFORE_RULING, (
        f"the pre-ruling pool reconstructs to {len(before)}, not "
        f"{POOL_SIZE_BEFORE_RULING}: {sorted(before)}")
    assert DROPPED.issubset(set(before)), "a dropped clip was never in the pool"
    assert len(before) - len(DROPPED) == POOL_SIZE
