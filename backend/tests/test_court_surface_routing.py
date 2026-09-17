"""Surface routing for the court line mask (calibration.court_surface / court_line_mask).

Clay's paint is whitish-on-orange, so `line_ridge_mask`'s saturation gate discards
it — measured, that mask scores a HUMAN-placed clay court at g = 0.000 on two gold
clips. Three global mask replacements were built to fix it and all three failed the
gold gate by trading clay gains for hard-court losses. Routing by surface passed
(11/20 -> 12/20, nothing lost, zero wrong courts) precisely because non-clay frames
keep a bit-identical path.

These pin the two properties that makes true:
  * the surface call itself, on synthetic colour (no clip needed);
  * that `line_ridge_mask` is UNTOUCHED on a non-clay frame, so nothing that
    already worked can change.
"""

import numpy as np
import pytest

cv2 = pytest.importorskip("cv2")

from swingvision import calibration


def _surface(bgr, w=640, h=360):
    """A flat court-coloured frame with a few white lines drawn on it."""
    img = np.zeros((h, w, 3), np.uint8)
    img[:, :] = bgr
    for y in (int(h * 0.55), int(h * 0.75), int(h * 0.92)):
        cv2.line(img, (int(w * 0.1), y), (int(w * 0.9), y), (245, 245, 245), 2)
    return img


CLAY = (60, 90, 190)      # BGR: orange-red clay
HARD_BLUE = (150, 90, 45)
HARD_GREEN = (90, 130, 90)


def test_clay_is_called_clay_and_others_are_not():
    assert calibration.court_surface(_surface(CLAY)) == "clay"
    assert calibration.court_surface(_surface(HARD_BLUE)) == "hard"
    assert calibration.court_surface(_surface(HARD_GREEN)) == "hard"


def test_non_clay_routes_to_the_untouched_primitive():
    """The whole reason routing passed its gate: a hard court's mask must be
    EXACTLY what it was before, so no clip that already worked can regress."""
    img = _surface(HARD_BLUE)
    assert np.array_equal(calibration.court_line_mask(img),
                          calibration.line_ridge_mask(img))


def test_clay_does_not_route_to_the_primitive():
    img = _surface(CLAY)
    assert not np.array_equal(calibration.court_line_mask(img),
                              calibration.line_ridge_mask(img))


def test_clay_mask_finds_lines_the_saturation_gate_would_drop():
    """On clay the primitive's `sat < 90` test is what loses the paint. The clay
    mask must recover materially more line pixels on the same frame."""
    img = _surface(CLAY)
    assert (calibration.clay_line_mask(img) > 0).sum() > \
           (calibration.line_ridge_mask(img) > 0).sum()


def test_threshold_sits_in_the_measured_gap():
    """CLAY_A_STAR is not a chosen number: over 31 eyeball-labelled recordings,
    clay measured a* 148.0-163.5 and everything else topped out at 132.0. The
    threshold must stay inside that gap, or the separation it claims is gone."""
    assert 132.0 < calibration.CLAY_A_STAR < 148.0
