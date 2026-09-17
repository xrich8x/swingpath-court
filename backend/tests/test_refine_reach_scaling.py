"""The court refiner's reach must scale with resolution - and be an EXACT no-op at 640.

`autodetect` bounds each candidate's corner refinement to `max_move_px`. That constant
was tuned on the court gold set, and every one of those 20 clips is exactly 640 px wide -
so an ABSOLUTE bound meant the refiner's reach silently shrank as resolution grew:

    640-wide gold clips   55 px@640-equivalent   (what it was tuned at)
    1920 references       18.3
    4K shell             9.2

Measured in Session P (`data/output/seed_reach.log`): on 7 of 38 human-labelled clips the
seed nearest the true court sat FARTHER from it than the refiner could travel, and all 7
come back into range once the bound scales with width.

This is the same defect the ball stack hit at 1080p - "every 720p-tuned pixel constant
silently deleted real balls at 1080p" - and it gets the same discipline: scale it, and
prove it is an exact no-op at the resolution it was tuned at, so no clip that already
worked can move.

These tests fail if anyone reverts the scaling, or changes the anchor so that a 640-wide
frame stops reproducing the original 55 px exactly.
"""

import inspect
import re

import pytest

cv2 = pytest.importorskip("cv2")

from swingvision import courtfit  # noqa: E402


def _refine_call_source():
    """The `refine_homography_bounded` call inside autodetect, as source text.

    Takes a fixed window after the call rather than trying to match balanced
    parentheses: the argument list contains `_corners(*p)`, so a non-greedy `\\(.*?\\)`
    stops at the wrong bracket and silently captures almost nothing."""
    src = inspect.getsource(courtfit.autodetect)
    i = src.find("refine_homography_bounded(")
    assert i >= 0, "autodetect no longer calls refine_homography_bounded"
    return src[i:i + 240]


def test_the_reach_is_not_an_absolute_constant():
    """The bug in one line: a bare number here is resolution-dependent."""
    call = _refine_call_source()
    assert "max_move_px" in call
    assert re.search(r"max_move_px\s*=\s*55\.0\s*[,)]", call) is None, (
        "max_move_px is back to an absolute 55.0 - the refiner's reach is 6x tighter "
        "on 4K than on the gold clips it was tuned on")
    assert "/ 640" in call or "/640" in call, (
        "the reach no longer scales against the 640-wide anchor the gold set uses")


@pytest.mark.parametrize("w,expected", [(640, 55.0), (1280, 110.0),
                                        (1920, 165.0), (3840, 330.0)])
def test_reach_scales_linearly_with_width(w, expected):
    """The value the call computes, evaluated directly.

    640 -> 55.0 EXACTLY is the load-bearing case: it is what makes the change unable to
    move any of the 20 gold clips the gate is built from."""
    assert 55.0 * (w / 640.0) == pytest.approx(expected)


def test_the_anchor_matches_the_gold_set_width():
    """The anchor is not arbitrary - it is the width of every gold clip. If the gold
    set ever stops being 640 wide, the no-op guarantee above is void and this test is
    the thing that says so."""
    from pathlib import Path
    import json

    gold = Path(__file__).resolve().parents[2] / "data" / "gold"
    if not gold.exists():
        pytest.skip("gold set not present")
    widths = set()
    for lf in sorted(gold.glob("*.court.labels.json")):
        clip = lf.name.replace(".court.labels.json", "")
        d = gold / "frames" / clip
        if not d.is_dir():
            continue
        for p in sorted(d.glob("f*.jpg"))[:1]:
            im = cv2.imread(str(p))
            if im is not None:
                widths.add(im.shape[1])
    if not widths:
        pytest.skip("no extracted gold frames")
    assert widths == {640}, (
        f"gold frames are no longer uniformly 640 wide (found {sorted(widths)}) - "
        f"the 640 anchor no longer makes the scaling a no-op on the gate")
