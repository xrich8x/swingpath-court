"""Pins tools/court_map_ceiling.py (P8 C1) - the court-model geometry it scores."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

M = pytest.importorskip("court_map_ceiling")


def test_perfect_taps_and_exact_hfov_reproduce_the_court_exactly():
    """The internal control: with nothing perturbed, both maps must place every
    line on itself and recover the true camera height. If this fails, every
    other number from the tool is junk."""
    r = M.run(3.0, 0.0, 0.0, n=3, seed=0)
    # 0.1 mm, not zero: camera_from_court_corners solves PnP in float32, which
    # leaves ~5 um on the 3d map. That is 10,000x below the 5 cm bar.
    for m in ("2d", "3d"):
        assert r["maps"][m]["worst_p90"] < 1e-4, m
    assert r["cam_height_p50"] == pytest.approx(3.0, abs=1e-4)
    assert r["pose_failures"] == 0


def test_every_painted_line_is_scored_once():
    names = [n for n, *_ in M.lines()]
    assert len(names) == len(set(names)) == 14
    assert {"far_baseline", "near_baseline", "far_centre_service"} <= set(names)


def test_hfov_error_moves_only_the_3d_map():
    """The homography never sees hfov; the PnP camera does."""
    r = M.run(3.0, 0.0, 10.0, n=3, seed=0)
    assert r["maps"]["2d"]["worst_p90"] < 1e-4
    assert r["maps"]["3d"]["worst_p90"] > 0.1
    assert r["cam_height_p50"] != pytest.approx(3.0, abs=0.05)


def test_error_is_linear_in_tap_noise_in_the_small_noise_regime():
    """The published 'tap precision needed' column divides the bar by the
    1 px error, which is only valid if the error scales linearly."""
    a = M.run(3.0, 1.0, 0.0, n=200, seed=0)["maps"]["2d"]["lines"]["far_baseline"]["p90"]
    b = M.run(3.0, 2.0, 0.0, n=200, seed=0)["maps"]["2d"]["lines"]["far_baseline"]["p90"]
    assert b / a == pytest.approx(2.0, rel=0.1)
