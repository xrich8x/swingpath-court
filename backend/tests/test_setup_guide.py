"""Setup guidance: the framing check the Court Setup tool shows live.

Two questions, graded from measurements (never guessed): can the camera SEE the
court, and is its ANGLE good enough to actually measure the court. Synthetic
cameras only - no footage or weights - so the thresholds are deterministic.
"""

import math

import numpy as np
import pytest

pytest.importorskip("cv2")
pytest.importorskip("scipy")

import cv2  # noqa: E402

from swingvision import calibration as C  # noqa: E402
from swingvision import court, courtfit  # noqa: E402

DBL = ["near_bl_doubles", "near_br_doubles", "far_br_doubles", "far_bl_doubles"]
W, H = 1280, 720


def _cam(Cz, f_px, back=8.0):
    """Homography for a centre-line camera `back` m behind the baseline at height Cz."""
    Cx, Cy = court.DOUBLES_WIDTH / 2.0, -back
    pitch = math.atan2(Cz, back + court.LENGTH * 0.5)
    st, ct = math.sin(pitch), math.cos(pitch)
    fwd = np.array([0.0, ct, -st]); right = np.array([1.0, 0.0, 0.0])
    up = np.array([0.0, st, ct])
    img, wld = [], []
    for n in DBL:
        X, Y = court.LANDMARKS[n]
        d = np.array([X - Cx, Y - Cy, -Cz]); z = d @ fwd
        img.append([W / 2 + f_px * (d @ right) / z, H / 2 - f_px * (d @ up) / z])
        wld.append([X, Y])
    return C.compute_homography(wld, img), {n: img[i] for i, n in enumerate(DBL)}


def _draw(Hm):
    frame = np.full((H, W, 3), (60, 120, 70), np.uint8)
    for a, b in court.LINES:
        p = C.court_to_image(Hm, [a])[0]; q = C.court_to_image(Hm, [b])[0]
        cv2.line(frame, tuple(np.round(p).astype(int)), tuple(np.round(q).astype(int)),
                 (245, 245, 245), 3, cv2.LINE_AA)
    return frame


def _f(hfov_deg):
    return W / (2.0 * math.tan(math.radians(hfov_deg) / 2.0))


def test_reliable_span_grows_with_camera_height():
    """The measured reliable span is what makes 'mount it higher' a fact, not an
    opinion: a higher camera resolves more court depth."""
    spans = []
    for cz in (1.5, 3.0, 6.0):
        Hm, _ = _cam(cz, _f(74))
        frac, until = C.reliable_court_span(Hm)
        spans.append(until)
    assert spans[0] < spans[1] < spans[2], spans


def test_reliable_span_shrinks_on_a_wider_lens():
    """At a fixed height, 'seeing more court' by going wider costs resolution."""
    _, until_tight = C.reliable_court_span(_cam(2.5, _f(60))[0])
    _, until_wide = C.reliable_court_span(_cam(2.5, _f(110))[0])
    assert until_wide < until_tight


def test_low_camera_is_graded_poor_and_says_why():
    Hm, corners = _cam(1.4, _f(90))
    v = courtfit.setup_verdict(_draw(Hm), corners, C, court)
    assert v["angle"]["level"] == "poor"
    assert v["angle"]["height_m"] < 2.0
    assert "%" in v["angle"]["msg"]          # quantified, not vague


def test_good_camera_is_graded_good():
    Hm, corners = _cam(7.0, _f(60))
    v = courtfit.setup_verdict(_draw(Hm), corners, C, court)
    assert v["angle"]["level"] == "good"
    assert v["angle"]["reliable_frac"] > 0.5


def test_never_claims_far_half_when_span_stops_short_of_the_net():
    """The honesty guard: only claim the far half when the span really passes the
    net. (An earlier draft said 'including the far half' at an 8.8 m reach.)"""
    for cz in (1.2, 1.6, 2.0, 2.6, 3.4, 5.0, 8.0):
        Hm, corners = _cam(cz, _f(80))
        v = courtfit.setup_verdict(_draw(Hm), corners, C, court)
        _frac, until = C.reliable_court_span(Hm)
        msg = v["angle"]["msg"]
        if until < court.NET_Y:
            # states the shortfall as fact, never claims coverage it doesn't have,
            # and is never graded "good" (advice like "...extends it past the net"
            # is fine - that's a fix, not a claim)
            assert "short of the net" in msg
            assert "Both service boxes are covered" not in msg
            assert v["angle"]["level"] != "good"
        else:
            assert "past the net" in msg


def test_advice_stays_within_a_reachable_mount():
    """Realism guard: a phone tripod is ~1.5 m and a fence clamp ~2.5-3 m, so the
    guide must never tell someone to MOUNT at a height they cannot reach. Only the
    advice is checked - factual text ("1.4 m up", "24 m") legitimately has numbers."""
    import re
    mount_tips = [t for t in courtfit._setup_tips(Cz=1.4, back_m=6.0, frame_w=1920)
                  if "fence" in t or "tripod" in t or "clamp" in t]
    assert mount_tips, "a low camera should get a mount tip"
    for t in mount_tips:
        for h in re.findall(r"([\d.]+)\s*m\b", t):
            assert float(h) <= 3.0, f"advises an unreachable mount height: {t}"
    assert any("fence" in t for t in mount_tips)     # the realistic lever


def test_low_resolution_is_called_out_first():
    """For someone stuck low, resolution is the cheapest big win (measured: 720p
    17% vs 4K 48% at 1.5 m / 6 m back), so it must lead the advice."""
    tips = courtfit._setup_tips(Cz=1.5, back_m=6.0, frame_w=1280)
    assert tips and "resolution" in tips[0]
    assert not any("resolution" in t for t in
                   courtfit._setup_tips(Cz=1.5, back_m=6.0, frame_w=3840))


def test_step_back_only_suggested_when_actually_close():
    assert any("further back" in t for t in
               courtfit._setup_tips(Cz=2.0, back_m=1.0, frame_w=1920))
    assert not any("further back" in t for t in
                   courtfit._setup_tips(Cz=2.0, back_m=6.0, frame_w=1920))


def test_stepping_back_is_never_presented_as_mandatory():
    """A fence is often right behind the baseline, and a phone user can always
    zoom out. Measured: 4K ultrawide 2 m back (35%, 8.3 m) BEATS 1080p normal 6 m
    back (27%, 6.3 m) - so a wider lens is a legitimate answer, never a mistake,
    and the step-back tip must offer zooming out as the alternative."""
    tips = courtfit._setup_tips(Cz=1.5, back_m=1.5, frame_w=1280)
    back_tip = [t for t in tips if "further back" in t]
    assert back_tip and "zoom out" in back_tip[0]
    # resolution leads, because it is what pays for the wider lens
    assert "resolution" in tips[0]


def test_offscreen_corner_advice_allows_zooming_out():
    """Getting all four corners in frame outranks lens width: an extrapolated
    corner is worse than a wider view."""
    Hm, corners = _cam(1.5, _f(40))          # tight lens: corners fall outside
    frame = _draw(Hm)
    v = courtfit.setup_verdict(frame, corners, C, court)
    if v["view"]["corners_visible"] < 4:
        assert "zoom out" in v["view"]["msg"]


def test_setup_gate_matches_the_analysis_gate():
    """The framing guide and the shot-confidence gate must use ONE definition of
    reliable, or the setup advice would contradict the resulting match.json."""
    assert C.RELIABLE_SCALE_M_PER_PX == 0.09
    Hm, _ = _cam(3.0, _f(70))
    p_near = C.court_to_image(Hm, [(court.DOUBLES_WIDTH / 2, 0.0)])[0]
    assert C.court_scale_m_per_px(Hm, p_near) <= C.RELIABLE_SCALE_M_PER_PX


# --- Measured line-call accuracy vs mount height (tools/height_curve.py) ------
# `reliable_court_span` is a GEOMETRIC BOUND, not an error, so on its own it left
# "mount it higher" half an opinion. These pin the measured half.

def test_call_accuracy_clamps_outside_the_measured_range():
    """Guidance must not extrapolate off the end of a measured table."""
    tbl = C._CALL_ACCURACY_BY_HEIGHT
    assert C.expected_call_accuracy(0.2) == tbl[0][1]
    assert C.expected_call_accuracy(0.2) == C.expected_call_accuracy(tbl[0][0])
    assert C.expected_call_accuracy(50.0) == tbl[-1][1]


def test_call_accuracy_interpolates_between_measured_points():
    lo, hi = C._CALL_ACCURACY_BY_HEIGHT[0], C._CALL_ACCURACY_BY_HEIGHT[1]
    mid = C.expected_call_accuracy((lo[0] + hi[0]) / 2.0)
    assert lo[1] < mid < hi[1]
    assert mid == pytest.approx((lo[1] + hi[1]) / 2.0)


def test_a_one_metre_mount_is_no_better_than_guessing():
    """THE finding this table exists to record: on bounces near a line, a 1 m
    camera scores at or below the majority-class floor, so its close calls carry
    no information. If this ever stops being true, the table was re-measured and
    the setup guidance must be re-read, not silently updated."""
    assert C.expected_call_accuracy(1.0) <= C.CALL_MAJORITY_FLOOR_PCT


def test_call_accuracy_rises_with_height_over_the_amateur_range():
    got = [C.expected_call_accuracy(z) for z in (1.0, 1.5, 2.0, 3.0, 5.0)]
    assert got == sorted(got) and got[-1] > got[0] + 15.0, got


def test_setup_verdict_reports_close_call_accuracy_at_every_height():
    for cz in (1.4, 2.5, 7.0):
        Hm, corners = _cam(cz, _f(80))
        v = courtfit.setup_verdict(_draw(Hm), corners, C, court)
        assert v["angle"]["call_accuracy_pct"] == pytest.approx(
            round(C.expected_call_accuracy(v["angle"]["height_m"]), 0), abs=2)
        assert "Close calls" in v["angle"]["msg"]


def test_setup_verdict_says_plainly_when_calls_are_worthless():
    """A user at 1 m should be told the calls are worthless, not handed a
    percentage that sounds like partial credit."""
    Hm, corners = _cam(1.0, _f(100))
    v = courtfit.setup_verdict(_draw(Hm), corners, C, court)
    assert "no better than guessing" in v["angle"]["msg"], v["angle"]["msg"]
