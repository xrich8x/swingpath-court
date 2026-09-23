"""Height-prior seeding (G12, job 4 2026-09-23): the seed is dolly-zoomed to each
prior height and the independent paint_check picks the winner."""
import math
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
S = pytest.importorskip("court_track_sim")

from swingvision import camera3d, court  # noqa: E402


@pytest.fixture(scope="module")
def cam():
    return S.camera(0.0, S.base_pitch(), 0.0)          # 3.0 m mount


@pytest.mark.parametrize("h", [1.5, 2.5, 3.5])
def test_at_height_reaches_the_prior_and_keeps_the_court_centre(cam, h):
    c = camera3d.at_height(cam, h)
    assert c is not None
    assert abs(c.position_m()[2] - h) < 1e-6
    ctr = [[court.X_CENTER, court.NET_Y, 0.0]]
    assert np.allclose(c.project(ctr), cam.project(ctr), atol=1e-6)


def test_an_unreachable_prior_is_refused(cam):
    assert camera3d.at_height(cam, 40.0) is None


def test_the_winner_is_chosen_by_the_paint_check_not_the_fit(cam, monkeypatch):
    img = np.clip(S.render(cam, np.random.default_rng(5), subpixel=True), 0, 255).astype(np.uint8)
    calls = []

    def fake_fit(frames, start, pose_only=False, cfg=None):
        calls.append(float(start.position_m()[2]))
        # the 2.5 m anchor "converges" to the truth; the others stay where they started
        out = cam if abs(start.position_m()[2] - 2.5) < 1e-6 else start
        return camera3d.PaintFitResult(out, 1.0, None, {})
    monkeypatch.setattr(camera3d, "fit_camera_on_paint", fake_fit)
    res = camera3d.fit_camera_anchored(img, cam)
    assert np.allclose(sorted(calls), [1.5, 2.5, 3.5])
    assert res.camera.extra["height_prior_m"] == 2.5
    assert res.camera.extra["paint_check"] == "pass"
    assert len(res.camera.extra["anchors"]) == 3
