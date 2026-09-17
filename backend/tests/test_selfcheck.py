"""White-line court self-check (calibration.verify_court and friends).

Uses a synthetic frame with the court lines drawn through a known homography, so
the accept/refuse behaviour is deterministic (no real footage or weights).
"""

import cv2
import numpy as np

from swingvision import calibration as C, court

CORNERS = ["near_bl_doubles", "near_br_doubles", "far_br_doubles", "far_bl_doubles"]


def _H(image_pts):
    return C.compute_homography([court.LANDMARKS[n] for n in CORNERS], image_pts)


def _draw_court(H, w=640, h=360, thickness=2):
    """Dark bluish surface with white court lines projected through H."""
    frame = np.full((h, w, 3), (60, 40, 25), np.uint8)  # BGR: dim blue-ish court
    for a, b in court.LINES:
        p = C.court_to_image(H, [a])[0]
        q = C.court_to_image(H, [b])[0]
        cv2.line(frame, (int(round(p[0])), int(round(p[1]))),
                 (int(round(q[0])), int(round(q[1]))), (255, 255, 255), thickness)
    return frame


# A central, perspective-correct court (near baseline wide, far baseline narrow).
TRUE_PTS = [(150, 320), (490, 320), (400, 95), (240, 95)]


def test_ridge_mask_finds_drawn_lines():
    frame = _draw_court(_H(TRUE_PTS))
    mask = C.line_ridge_mask(frame)
    # The old tophat/Otsu mask can collapse; the ridge mask must find real lines.
    assert mask.mean() > 0
    assert (mask > 0).sum() > 200


def test_verify_accepts_the_true_court():
    H = _H(TRUE_PTS)
    frame = _draw_court(H)
    chk = C.verify_court(frame, H)
    assert chk.ok
    assert chk.coverage > 0.6      # lines land on the drawn white
    assert chk.centrality > 0.7    # court sits centrally
    assert chk.visible_frac > 0.9


def test_verify_refuses_an_offcentre_court():
    """A court squeezed into a corner (like a background/adjacent court) must be
    refused even though the frame contains a real central court."""
    frame = _draw_court(_H(TRUE_PTS))
    H_corner = _H([(20, 120), (180, 120), (155, 30), (45, 30)])
    chk = C.verify_court(frame, H_corner)
    assert not chk.ok
    assert chk.centrality < 0.7


def test_verify_refuses_a_misaligned_court():
    """A court shifted off the real lines scores lower coverage and is refused."""
    frame = _draw_court(_H(TRUE_PTS))
    good = C.verify_court(frame, _H(TRUE_PTS))
    shifted = C.verify_court(frame, _H([(230, 330), (560, 320), (470, 110), (315, 105)]))
    assert shifted.coverage < good.coverage
    assert not shifted.ok


def test_framing_report_good_when_whole_court_in_frame():
    H = _H(TRUE_PTS)                       # all 4 corners well inside 640x360
    frame = _draw_court(H)
    r = C.framing_report(frame, H)
    assert r.corners_visible == 4
    assert r.level == "good"
    assert r.ok


def test_framing_report_flags_offscreen_corners():
    # push the near baseline below the frame -> near corners off-screen
    H = _H([(120, 470), (520, 470), (400, 95), (240, 95)])
    frame = _draw_court(H)
    r = C.framing_report(frame, H)
    assert r.corners_visible < 4
    assert r.level == "poor"
    assert any("off-screen" in m for m in r.messages)
