"""The derived live-setup criterion: is the far baseline clear of the net tape?

Pins the geometry in docs/evidence/setup-envelope-net-occludes-far-baseline.md and
the implementation in docs/evidence/live-setup-criterion.md. The criterion is
GUIDANCE, not a gate, so several tests here assert that it does NOT refuse.
"""
import json
import math
import os

import numpy as np
import pytest

from swingvision import calibration as C
from swingvision import court

DBL = ("near_bl_doubles", "near_br_doubles", "far_bl_doubles", "far_br_doubles")
DATA = os.path.join(os.path.dirname(__file__), "..", "..", "data")


def synth_H(cam_h, standoff=3.0, hfov=80.0, w=1280, h=720):
    """Court-plane homography for a camera `cam_h` up, `standoff` m behind the
    near baseline, centred on x and aimed at the net. The same construction the
    source finding used, so the numbers below are comparable to its table."""
    f = (w / 2.0) / math.tan(math.radians(hfov) / 2.0)
    K = np.array([[f, 0, w / 2.0], [0, f, h / 2.0], [0, 0, 1.0]])
    Cpos = np.array([court.X_CENTER, -standoff, cam_h])
    fwd = np.array([court.X_CENTER, court.NET_Y, 0.0]) - Cpos
    fwd /= np.linalg.norm(fwd)
    right = np.cross(fwd, np.array([0, 0, 1.0]))
    right /= np.linalg.norm(right)
    R = np.vstack([right, np.cross(fwd, right), fwd])
    P = K @ np.hstack([R, (-R @ Cpos).reshape(3, 1)])
    H = P[:, [0, 1, 3]]
    return H / H[2, 2]


def margin(cam_h, **kw):
    r = C.net_tape_clearance(synth_H(cam_h, **kw), (kw.get("w", 1280), kw.get("h", 720)),
                             hfov_deg=kw.get("hfov", 80.0))
    assert r is not None
    return r.margin_px_720


# --- the geometry itself -----------------------------------------------------

@pytest.mark.parametrize("cam_h,expected", [
    (1.40, -15.0), (1.64, -9.5), (2.00, -1.4),
    (2.50, +10.1), (3.00, +21.4), (4.00, +44.1),
])
def test_reproduces_the_source_findings_table(cam_h, expected):
    """3 m back, 80 deg, 720p - the table in
    docs/evidence/setup-envelope-net-occludes-far-baseline.md. Tolerance 1.5 px
    because the source quotes rows relative to the horizon and rounds to 0.1."""
    assert margin(cam_h) == pytest.approx(expected, abs=1.5)


def test_margin_increases_monotonically_with_camera_height():
    ms = [margin(h) for h in (1.2, 1.6, 2.0, 2.5, 3.0, 4.0, 6.0)]
    assert all(b > a for a, b in zip(ms, ms[1:]))


@pytest.mark.parametrize("standoff", [2.0, 3.0, 5.0])
@pytest.mark.parametrize("hfov", [65.0, 80.0, 100.0])
def test_crossover_sits_between_1_9_and_2_3_m_whatever_the_camera(standoff, hfov):
    """The whole point of the finding: the crossover is set by the COURT's
    geometry, not the camera's, so it barely moves with standoff or lens."""
    lo, hi = 0.5, 12.0
    for _ in range(50):
        mid = (lo + hi) / 2.0
        if margin(mid, standoff=standoff, hfov=hfov) < 0.0:
            lo = mid
        else:
            hi = mid
    assert 1.9 <= (lo + hi) / 2.0 <= 2.3


def test_normalising_to_720p_makes_the_margin_resolution_independent():
    """Same physical setup at 1080p: the RAW pixel margin grows 1.5x, the
    720p-normalised one does not move. Unscaled constants have silently deleted
    real balls at 1080p before - this criterion must not repeat it."""
    a = C.net_tape_clearance(synth_H(3.0, w=1280, h=720), (1280, 720), hfov_deg=80.0)
    b = C.net_tape_clearance(synth_H(3.0, w=1920, h=1080), (1920, 1080), hfov_deg=80.0)
    assert b.margin_px == pytest.approx(a.margin_px * 1.5, rel=0.02)
    assert b.margin_px_720 == pytest.approx(a.margin_px_720, rel=0.02)


def test_the_sidelines_are_worse_than_the_centre():
    """The net rises from 0.914 m at the strap to 1.07 m at the posts, so the
    occlusion is worse toward the sides than the centre-line figure shows."""
    r = C.net_tape_clearance(synth_H(3.0), (1280, 720), hfov_deg=80.0)
    assert r.worst_margin_px_720 < r.margin_px_720


def test_net_height_model_hits_both_physical_endpoints():
    assert C._net_height_at_x(court.X_CENTER) == pytest.approx(court.NET_HEIGHT_CENTER)
    assert C._net_height_at_x(court.X_RIGHT_POST) == pytest.approx(court.NET_HEIGHT_POST)
    assert C._net_height_at_x(court.X_LEFT_POST) == pytest.approx(court.NET_HEIGHT_POST)
    mid = C._net_height_at_x(court.X_RIGHT_DOUBLES)
    assert court.NET_HEIGHT_CENTER < mid < court.NET_HEIGHT_POST


# --- the pre-registered bands ------------------------------------------------

def test_bands_are_the_pre_registered_ones():
    """good >= +10 px @720p, marginal 0 < m < +10, poor <= 0. Registered in the
    journal before the clip sweep and unchanged after it."""
    assert C.CLEARANCE_GOOD_PX == 10.0
    assert C.net_tape_clearance(synth_H(1.5), (1280, 720), hfov_deg=80.0).level == "poor"
    assert C.net_tape_clearance(synth_H(2.2), (1280, 720), hfov_deg=80.0).level == "marginal"
    assert C.net_tape_clearance(synth_H(3.0), (1280, 720), hfov_deg=80.0).level == "good"


def test_clear_property_tracks_the_sign_not_the_band():
    assert C.net_tape_clearance(synth_H(2.2), (1280, 720), hfov_deg=80.0).clear
    assert not C.net_tape_clearance(synth_H(1.5), (1280, 720), hfov_deg=80.0).clear


def test_every_level_carries_an_actionable_message():
    for h in (1.5, 2.2, 3.0):
        msg = C.net_tape_clearance(synth_H(h), (1280, 720), hfov_deg=80.0).message
        assert msg and msg[0].isupper() and msg.rstrip().endswith(".")


def test_hfov_defaults_to_self_calibration_not_an_assumed_lens():
    """The criterion has no free parameter: with hfov_deg omitted it recovers the
    focal from H itself, and must land on the same answer as passing the truth."""
    for hfov in (65.0, 80.0, 100.0):
        H = synth_H(3.0, hfov=hfov)
        auto = C.net_tape_clearance(H, (1280, 720))
        told = C.net_tape_clearance(H, (1280, 720), hfov_deg=hfov)
        assert auto.hfov_deg == pytest.approx(hfov, abs=1.0)
        assert auto.margin_px == pytest.approx(told.margin_px, abs=1.0)


# A quad whose left/right corners cross over: no physical camera produces it, so
# the pose solve has nothing to return. data/yt_court_pts_doubles.json is a real
# instance of this in the shipped set.
_UNFITTABLE = {"near_bl_doubles": [500, 300], "near_br_doubles": [100, 300],
               "far_bl_doubles": [100, 100], "far_br_doubles": [500, 100]}


def test_unfittable_quad_degrades_to_None_rather_than_guessing():
    H = C.homography_from_landmarks(_UNFITTABLE)
    assert C.net_tape_clearance(H, (1280, 720)) is None


# --- it is guidance, not a gate ----------------------------------------------

def test_framing_report_reports_the_clearance_but_never_calls_it_poor():
    """A low mount must degrade to `warn` with an explanation, never to `poor`.
    `poor` stays reserved for a court that isn't even in frame."""
    frame = np.zeros((720, 1280, 3), np.uint8)
    # 1.4 m up, 5 m back, 100 deg lens: all four corners ARE in frame, so nothing
    # but the clearance is wrong with this setup.
    r = C.framing_report(frame, synth_H(1.4, standoff=5.0, hfov=100.0))
    assert r.corners_visible == 4
    assert r.clearance_level == "poor"
    assert r.clearance_px_720 < 0
    assert r.level != "poor"
    assert any("net tape" in m for m in r.messages)


def test_framing_report_survives_an_unfittable_quad():
    """clearance_* go None and nothing raises - the report is still usable."""
    frame = np.zeros((720, 1280, 3), np.uint8)
    r = C.framing_report(frame, C.homography_from_landmarks(_UNFITTABLE))
    assert r.clearance_px_720 is None and r.clearance_level is None


# --- regression against the shipped calibrations -----------------------------

@pytest.mark.parametrize("clip,level", [
    ("yt_match40_pts", "poor"),        # 1.64 m - the twice-misclicked clip
    ("am_hard_utr_pts", "poor"),       # 1.74 m - one of the two unsettled sheets
    ("demo30_pts", "poor"),            # 1.38 m
    ("flexi_franz_p01_pts", "marginal"),   # 2.50 m - just over the crossover
    ("sAjkpeRq4P4_pts", "good"),       # 3.33 m
    ("UHf0LeMU2pg_pts", "good"),       # 3.35 m
])
def test_shipped_calibrations_land_where_the_sweep_put_them(clip, level):
    path = os.path.join(DATA, clip + ".json")
    if not os.path.exists(path):
        pytest.skip(f"{clip} not present")
    d = json.load(open(path))
    wh = d.get("_audit", {}).get("img_wh")
    if not wh or not all(k in d for k in DBL):
        pytest.skip(f"{clip} has no stamped img_wh")
    H = C.homography_from_landmarks({k: [float(d[k][0]), float(d[k][1])] for k in DBL})
    r = C.net_tape_clearance(H, (float(wh[0]), float(wh[1])))
    assert r is not None and r.level == level
