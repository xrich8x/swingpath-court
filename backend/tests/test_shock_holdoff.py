"""camtrack's shock hold-off (job 3, 2026-09-23): a frame whose own flow shows a
shock is reported NOT locked - and NOTHING ELSE changes. Truth is the camera that
rendered each frame (tools/court_track_sim.py)."""
import math
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
S = pytest.importorskip("court_track_sim")

from swingvision import camtrack  # noqa: E402

WH = (1280, 720)


def no_fit(frames, seed, pose_only=False):
    raise RuntimeError("no paint fit in this test")


@pytest.fixture(scope="module")
def clip():
    p0 = S.base_pitch(WH)
    cams = [S.camera(math.radians(0.05 * i) + (math.radians(1.0) if i >= 6 else 0.0),
                     p0 + (math.radians(1.5) if i >= 6 else 0.0), 0.0, wh=WH) for i in range(9)]
    imgs = [np.clip(S.render(c, np.random.default_rng(i)), 0, 255).astype(np.uint8)
            for i, c in enumerate(cams)]
    return cams, imgs


def track(clip, **cfg):
    cams, imgs = clip
    tr = camtrack.CameraTracker(cams[0], paint_fit=no_fit, cfg=camtrack.TrackConfig(**cfg))
    return [tr.step(im, i / 30.0) for i, im in enumerate(imgs)]


def test_the_default_is_off():
    c = camtrack.TrackConfig()
    assert c.shock_n_ratio is None and c.shock_resid_ratio is None and c.shock_outlier_frac is None


def test_signals_are_recorded_even_when_off(clip):
    st = track(clip)
    assert all(s.shock["fired"] == [] for s in st)
    steady = [s.shock for s in st[4:6]]            # history exists, before the knock
    assert all(np.isfinite(s["n_ratio"]) and np.isfinite(s["outlier_frac"]) for s in steady)


def test_the_holdoff_changes_the_REPORT_and_nothing_else(clip):
    off = track(clip)
    on = track(clip, shock_n_ratio=10.0)          # fires on every frame with history
    for a, b in zip(off, on):
        assert np.array_equal(a.camera.rvec, b.camera.rvec)
        assert np.array_equal(a.camera.tvec, b.camera.tvec)
        assert a.status == b.status and a.n_tracked == b.n_tracked
        if b.shock["fired"] and a.status == "tracking" and a.locked:
            assert not b.locked and b.lock_worst == "shock_holdoff" and b.lock_scope == "none"
            assert "shock" in b.claim()
        else:
            assert (a.locked, a.lock_worst, a.lock_scope) == (b.locked, b.lock_worst, b.lock_scope)
    assert any(b.lock_worst == "shock_holdoff" for b in on)
