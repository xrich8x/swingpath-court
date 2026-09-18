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
    raise RuntimeError("no paint fit in this test")


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
    # the paint fit from the last good camera is tried first (and fails the check)
    assert st.status == "recovered" and det.calls == 1 and seen == [True, True]
    assert st.camera.f_px == before.f_px
    assert worst_px(st.camera, after) < 0.5


def test_without_a_detector_a_lost_court_holds_the_last_good_camera(p0):
    before, after = cam_at(p0), cam_at(p0, yaw=math.radians(12), dpitch=math.radians(6))
    tr = camtrack.CameraTracker(before, paint_fit=no_fit)
    tr.step(frame(before), 0.0)
    st = tr.step(frame(after, 1), 1 / 30.0)
    assert st.status == "lost" and st.locked is False
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


def test_a_knock_recovers_by_paint_fit_without_a_detector(p0):
    """The pose-only paint fit from the last good camera comes before any
    detector; stubbed here to return the true camera."""
    before, after = cam_at(p0), cam_at(p0, yaw=math.radians(1.0), dpitch=math.radians(1.5))
    seeds = []

    def fit(frames, seed, pose_only=False):
        seeds.append(seed)
        return camera3d.PaintFitResult(after, 1.0, None, {})
    tr = camtrack.CameraTracker(before, paint_fit=fit)
    tr.step(frame(before), 0.0)
    got = [tr.step(frame(after, i), i / 30.0) for i in range(1, 4)]
    assert any(s.status == "recovered" for s in got)
    assert seeds and np.allclose(seeds[0].rvec, before.rvec)
    assert got[-1].locked and worst_px(got[-1].camera, after) < 0.5


def test_a_wrong_lock_is_never_reported_as_locked(p0):
    """G3's worst outcome: following paint onto the WRONG lines. The paint check
    sees it whatever the tracked points say."""
    truth = cam_at(p0)
    wrong = S.camera(0.0, p0, 0.0, dx=court.ALLEY, wh=WH)
    tr = camtrack.CameraTracker(wrong, paint_fit=no_fit)
    got = [tr.step(frame(truth, i), i / 30.0) for i in range(4)]
    assert not any(s.locked for s in got)


# ------------------------------------------------ camera3d.paint_check -----
@pytest.fixture(scope="module")
def truth_and_frame(p0):
    truth = cam_at(p0)
    return truth, frame(truth, 7)


def test_paint_check_passes_the_true_camera(truth_and_frame):
    truth, img = truth_and_frame
    chk = camera3d.paint_check(img, truth)
    assert chk.ok and chk.support > 0.8
    assert {"near_baseline", "doubles_L", "doubles_R"} <= set(chk.lines)


@pytest.mark.parametrize("wrong", [
    dict(dx=court.ALLEY),                       # one alley over
    dict(yaw=math.radians(0.5)),                # a small pan
    dict(dolly=1.3),                            # slid in depth
])
def test_paint_check_fails_wrong_cameras(p0, truth_and_frame, wrong):
    truth, img = truth_and_frame
    if "dolly" in wrong:
        cam = camera3d.dolly_zoom(truth, wrong["dolly"])
    elif "dx" in wrong:
        cam = S.camera(0.0, p0, 0.0, dx=wrong["dx"], wh=WH)
    else:
        cam = cam_at(p0, yaw=wrong["yaw"])
    assert not camera3d.paint_check(img, cam).ok


def test_paint_check_needs_enough_lines_to_judge(truth_and_frame):
    truth, img = truth_and_frame
    away = camera3d.CourtCamera(truth.f_px, truth.rvec + [0.0, 1.5, 0.0], truth.tvec, WH)
    chk = camera3d.paint_check(img, away)
    assert not chk.ok


def test_dolly_zoom_keeps_the_court_centre_scale(truth_and_frame):
    truth, _ = truth_and_frame
    c = np.array([court.X_CENTER, court.NET_Y, 0.0])
    pts = [c + [-1, 0, 0], c + [1, 0, 0]]

    def span(cam):
        a, b = cam.project(pts)
        return np.linalg.norm(a - b)
    for s in (0.75, 0.87, 1.15, 1.33):
        d = camera3d.dolly_zoom(truth, s)
        assert d.f_px == pytest.approx(truth.f_px * s)
        assert span(d) == pytest.approx(span(truth), rel=0.02)
        assert np.allclose(d.project([c]), truth.project([c]), atol=1e-6)


def test_checked_fit_restarts_until_the_paint_agrees(truth_and_frame, monkeypatch):
    truth, img = truth_and_frame
    starts = []

    def fake_fit(frames, seed, pose_only=False, cfg=None):
        starts.append(seed)
        # only the one-alley shift start "converges" to the truth
        cam = truth if len(starts) == 6 else seed
        return camera3d.PaintFitResult(cam, 1.0, None, {})
    monkeypatch.setattr(camera3d, "fit_camera_on_paint", fake_fit)
    wrong = camera3d.shifted(truth, -court.ALLEY)
    res = camera3d.fit_camera_checked(img, wrong)
    assert res.camera is truth and res.camera.extra["paint_check"] == "pass"
    assert res.camera.extra["starts"] == 6


def test_checked_fit_reports_a_failure_instead_of_hiding_it(truth_and_frame, monkeypatch):
    truth, img = truth_and_frame
    monkeypatch.setattr(camera3d, "fit_camera_on_paint",
                        lambda frames, seed, pose_only=False, cfg=None:
                        camera3d.PaintFitResult(seed, 1.0, None, {}))
    res = camera3d.fit_camera_checked(img, camera3d.shifted(truth, 3.0))
    assert res.camera.extra["paint_check"].startswith("FAIL")
    assert res.camera.extra["starts"] == 1 + len(camera3d.RESTARTS)
