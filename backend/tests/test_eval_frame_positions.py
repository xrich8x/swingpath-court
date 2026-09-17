"""Pin `eval/run_refs.frame_positions` against the inline expression it was
extracted from, and pin the tool that renders audit sheets to the same numbers.

Why this test exists (repo rule 8: a refactor must prove it changed nothing).
`frames_from` used to compute its sample positions inline. `tools/
render_corner_audit.py` rendered frame 0 instead, so the sheet a human audited
could show a frame the scoring never looks at - harmless on a locked-off tripod,
misleading the moment the camera moves, and nothing in a `*_pts.json` records
which of the two it is. The fix makes the tool import the eval's own function.
That is only worth anything if the function still returns what the eval returned
before, and if the tool keeps agreeing with it - hence both halves below.

No video is decoded here: `frame_positions` is pure arithmetic on a frame count.
"""

from __future__ import annotations

import pathlib
import sys

import numpy as np
import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
for p in (REPO / "eval", REPO / "tools"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))


def _legacy(total: int, k: int) -> list[int]:
    """Verbatim copy of the pre-2026-09-09 body of `frames_from`'s position
    loop, from git 5e322e2:eval/run_refs.py lines 163-165."""
    out = []
    if total > 0:
        lo, hi = int(0.05 * total), int(0.95 * total)
        for pos in np.linspace(lo, hi, k).round().astype(int):
            out.append(int(pos))
    return out


TOTALS = [0, 1, 2, 7, 8, 9, 100, 101, 899, 900, 1801, 5000, 27_000, 108_000]
KS = [1, 2, 3, 5, 8, 16]


@pytest.mark.parametrize("total", TOTALS)
@pytest.mark.parametrize("k", KS)
def test_frame_positions_matches_the_expression_it_replaced(total, k):
    import run_refs

    assert run_refs.frame_positions(total, k) == _legacy(total, k)


def test_positions_are_inside_the_sampled_band():
    import run_refs

    total, k = 10_000, 8
    pos = run_refs.frame_positions(total, k)
    assert len(pos) == k
    assert pos == sorted(pos)
    assert pos[0] >= int(0.05 * total)
    assert pos[-1] <= int(0.95 * total)
    # Frame 0 - the tool's old default - is NOT one of them. That is the whole
    # point of the defect being fixed.
    assert 0 not in pos


def test_zero_length_video_yields_no_positions():
    import run_refs

    assert run_refs.frame_positions(0, 8) == []
    assert run_refs.frame_positions(-1, 8) == []


def test_render_corner_audit_default_frame_is_an_eval_sample():
    """The audit sheet's default frame must be one of the frames the eval scores,
    and must be reported as such. If these two ever drift apart again, the sheet
    silently goes back to auditing a frame nobody scores."""
    import render_corner_audit as rca
    import run_refs

    total, k = 10_000, rca.EVAL_K
    pos = run_refs.frame_positions(total, k)
    idx, how = rca.default_frame(total)
    assert idx in pos
    assert idx == pos[(len(pos) - 1) // 2]
    # The caption line must name the frame and how it was chosen - a human
    # reading the PNG could previously not tell either.
    assert str(idx) in how and "8" in how and "5%-95%" in how


def test_render_corner_audit_falls_back_when_frame_count_is_unknown():
    import render_corner_audit as rca

    idx, how = rca.default_frame(0)
    assert idx == 0
    assert "UNKNOWN" in how.upper()
