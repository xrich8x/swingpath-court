"""camtrack: the court is tracked as a moving camera. Frames are rendered from
known synthetic cameras (tools/court_track_sim.py); truth is that camera."""
import math
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
S = pytest.importorskip("court_track_sim")

from swingvision import camera3d, camtrack, court, courtfit  # noqa: E402

WH = (1280, 720)


@pytest.fixture(scope="module")
def p0():
    return S.base_pitch(WH)


def cam_at(p0, yaw=0.0, dpitch=0.0):
    return S.camera(yaw, p0 + dpitch, 0.0, wh=WH)


def frame(cam, seed=0):
    return np.clip(S.render(cam, np.random.default_rng(seed)), 0, 255).astype(np.uint8)


def no_fit(frames, seed, pose_only=False):
    raise AssertionError("paint fit must not run here")


def worst_px(est, truth):
    names = [n for n, p in court.LANDMARKS_3D.items() if p[2] == 0.0]
    pts = [court.LANDMARKS_3D[n] for n in names]
    a, b = est.project(pts), truth.project(pts)
    ok = np.isfinite(b).all(1) & (b[:, 0] >= 0) & (b[:, 0] < WH[0]) & (b[:, 1] >= 0) & (b[:, 1] < WH[1])
    return float(np.max(np.linalg.norm(a[ok] - b[ok], axis=1)))


def test_a_static_camera_stays_put(p0):
    truth = cam_at(p0)
    tr = camtrack.CameraTracker(truth, paint_fit=no_fit)
    for i in range(5):
        st = tr.step(frame(truth, i), i / 30.0)
        assert st.status == "tracking"
    assert worst_px(st.camera, truth) < 0.5
    assert st.n_tracked > 50


def test_a_slow_pan_is_followed(p0):
    truths = [cam_at(p0, yaw=math.radians(0.15 * i), dpitch=math.radians(0.05 * i))
              for i in range(12)]
    tr = camtrack.CameraTracker(truths[0], paint_fit=no_fit)
    errs = []
    for i, tc in enumerate(truths):
        st = tr.step(frame(tc, i), i / 30.0)
        errs.append(worst_px(st.camera, tc))
    assert {s for s in [st.status]} == {"tracking"}
    # the court moved ~1.8 deg of yaw (~30 px); tracked to within a few px
    assert worst_px(truths[0], truths[-1]) > 20
    assert max(errs) < 3.0


class ExactDetector:
    """Keypoints straight from the true camera: isolates the tracker's logic."""

    def __init__(self, truth):
        self.truth = truth
        self.calls = 0

    def detect(self, img):
        self.calls += 1
        names = list(court.LANDMARKS_3D)
        uv = self.truth.project(list(court.LANDMARKS_3D.values()))
        px = {n: tuple(p) for n, p in zip(names, uv)
              if np.isfinite(p).all() and 0 <= p[0] < WH[0] and 0 <= p[1] < WH[1]}
        return courtfit.KeypointSet(px, source="exact", image_wh=WH)


def test_a_knock_recovers_through_the_detector_never_the_closed_search(p0, monkeypatch):
    def closed(*a, **k):
        raise AssertionError("courtfit.autodetect is CLOSED and must not be called")
    monkeypatch.setattr(courtfit, "autodetect", closed)
    before, after = cam_at(p0), cam_at(p0, yaw=math.radians(12), dpitch=math.radians(6))
    det = ExactDetector(after)
    seen = []

    def seed_as_fit(frames, seed, pose_only=False):
        seen.append(pose_only)
        return camera3d.PaintFitResult(seed, 1.0, None, {})
    tr = camtrack.CameraTracker(before, detector=det, paint_fit=seed_as_fit)
    tr.step(frame(before), 0.0)
    st = tr.step(frame(after, 1), 1 / 30.0)
    assert st.status == "recovered" and det.calls == 1 and seen == [True]
    assert st.camera.f_px == before.f_px
    assert worst_px(st.camera, after) < 0.5


def test_without_a_detector_a_lost_court_holds_the_last_good_camera(p0):
    before, after = cam_at(p0), cam_at(p0, yaw=math.radians(12), dpitch=math.radians(6))
    tr = camtrack.CameraTracker(before, paint_fit=no_fit)
    tr.step(frame(before), 0.0)
    st = tr.step(frame(after, 1), 1 / 30.0)
    assert st.status == "holding"
    assert np.allclose(st.camera.rvec, before.rvec) and np.allclose(st.camera.tvec, before.tvec)


def test_the_backstop_refits_on_schedule(p0):
    truth = cam_at(p0)
    calls = []

    def fit(frames, seed, pose_only=False):
        calls.append(pose_only)
        return camera3d.PaintFitResult(truth, 1.0, None, {})
    cfg = camtrack.TrackConfig(refit_s=0.1)
    tr = camtrack.CameraTracker(truth, paint_fit=fit, cfg=cfg)
    statuses = [tr.step(frame(truth, i), i / 30.0).status for i in range(6)]
    assert statuses.count("refit") >= 1 and calls and all(calls)


def test_the_closed_search_is_refused_as_a_recovery_detector():
    cam = camera3d.CourtCamera(800.0, [0.0, 0.0, 0.0], [0.0, 0.0, 10.0], WH)
    with pytest.raises(ValueError):
        camtrack.CameraTracker(cam, detector=courtfit.ClassicalKeypoints())


def test_players_are_masked_out_of_the_flow(p0):
    truth = cam_at(p0)
    tr = camtrack.CameraTracker(truth, paint_fit=no_fit)
    tr.step(frame(truth), 0.0)
    full = tr.step(frame(truth, 1), 1 / 30.0).n_tracked
    boxes = [(0, WH[1] // 2, WH[0], WH[1])]           # the whole near half
    part = tr.step(frame(truth, 2), 2 / 30.0, boxes=boxes).n_tracked
    assert 0 < part < full


def test_court_lines_project_as_polylines(p0):
    lines = camtrack.ground_lines_px(cam_at(p0), n=10)
    assert len(lines) == len(court.LINES) and all(p.shape == (10, 2) for p in lines)
