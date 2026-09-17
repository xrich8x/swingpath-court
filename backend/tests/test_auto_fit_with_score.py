"""`courtfit.auto_fit_frame(..., with_score=True)` is a diagnostic ADD-ON.

The eval harness needs the detector's ranking score per frame, and the only two ways
to get it were to re-implement `auto_fit_frame`'s three-step chain in the harness
(the duplicate-scorer failure this project has already paid for — trap T15) or to
return it from the real thing. This pins the promise made when it was added:

  * with_score=False (the default, and every shipped caller) returns EXACTLY what it
    returned before — a corners dict or None, never a tuple;
  * with_score=True returns the SAME court, paired with a float, and (None, None)
    on a refusal.

Synthetic court, same construction as test_court_snap.py, so the test needs no clip.
"""

import numpy as np
import pytest

cv2 = pytest.importorskip("cv2")

from swingvision import calibration, court, courtfit

_DBL = ("near_bl_doubles", "near_br_doubles", "far_br_doubles", "far_bl_doubles")
_TRUE_IMG = {
    "near_bl_doubles": [150.0, 330.0], "near_br_doubles": [490.0, 330.0],
    "far_br_doubles": [400.0, 90.0], "far_bl_doubles": [240.0, 90.0],
}


def _court_frame(w=640, h=360):
    H = calibration.compute_homography([court.LANDMARKS[n] for n in _DBL],
                                       [_TRUE_IMG[n] for n in _DBL])
    frame = np.full((h, w, 3), 40, np.uint8)          # a dark surface to ridge against
    for a, b in court.LINES:
        pa = calibration.court_to_image(H, [a])[0]
        pb = calibration.court_to_image(H, [b])[0]
        cv2.line(frame, (int(round(pa[0])), int(round(pa[1]))),
                 (int(round(pb[0])), int(round(pb[1]))), (245, 245, 245), 2)
    return frame


def test_default_return_is_unchanged_and_score_pairs_with_it():
    frame = _court_frame()
    plain = courtfit.auto_fit_frame(frame, calibration, court)
    paired = courtfit.auto_fit_frame(frame, calibration, court, with_score=True)

    assert isinstance(paired, tuple) and len(paired) == 2
    assert not isinstance(plain, tuple), "the shipped return must not become a tuple"

    corners, score = paired
    if plain is None:
        assert corners is None and score is None
    else:
        assert score is not None and np.isfinite(score)
        # same frame, same deterministic chain -> the same court
        for n in _DBL:
            assert plain[n] == pytest.approx(corners[n], abs=1e-6)


def test_refusal_returns_a_none_pair():
    blank = np.full((360, 640, 3), 40, np.uint8)      # no lines at all
    assert courtfit.auto_fit_frame(blank, calibration, court) is None
    assert courtfit.auto_fit_frame(blank, calibration, court, with_score=True) == (None, None)
