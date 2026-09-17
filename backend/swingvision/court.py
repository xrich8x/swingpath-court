"""Court constants and landmark geometry (the geometry layer).

A regulation tennis court, all dimensions in metres. The coordinate system is a
top-down, right-handed plane:

    x: 0 .. WIDTH   left doubles sideline -> right doubles sideline
    y: 0 .. LENGTH  near baseline -> far baseline
    net at y = LENGTH / 2

These are *real-world* coordinates. The homography maps between this plane and
image pixels. Court constants here are mirrored in frontend/src/lib/court.js;
keep the two in sync (see CLAUDE.md).
"""

from __future__ import annotations

# --- Regulation dimensions (metres) -----------------------------------------
LENGTH = 23.77          # baseline to baseline
DOUBLES_WIDTH = 10.97   # doubles sideline to doubles sideline
SINGLES_WIDTH = 8.23    # singles sideline to singles sideline
ALLEY = (DOUBLES_WIDTH - SINGLES_WIDTH) / 2.0   # 1.37, each doubles alley
SERVICE_LINE_FROM_NET = 6.40                    # net to service line
NET_Y = LENGTH / 2.0                            # 11.885

# Derived x positions of the four vertical lines (left -> right).
X_LEFT_DOUBLES = 0.0
X_LEFT_SINGLES = ALLEY                          # 1.37
X_CENTER = DOUBLES_WIDTH / 2.0                  # 5.485
X_RIGHT_SINGLES = DOUBLES_WIDTH - ALLEY         # 9.60
X_RIGHT_DOUBLES = DOUBLES_WIDTH                 # 10.97

# Derived y positions of the horizontal lines (near -> far).
Y_NEAR_BASELINE = 0.0
Y_NEAR_SERVICE = NET_Y - SERVICE_LINE_FROM_NET  # 5.485
Y_FAR_SERVICE = NET_Y + SERVICE_LINE_FROM_NET   # 18.285
Y_FAR_BASELINE = LENGTH                         # 23.77

# --- Net structure ----------------------------------------------------------
# The net is a distinct PHYSICAL object, not paint, and none of it is one of the
# four corners a manual calibration is fitted to. That makes it the natural
# independent anchor: a homography fitted to four clicked corners predicts where
# the net must appear, and the frame either agrees or it does not. See
# docs/evidence/net-anchor-calibration-check.md.
NET_POST_OFFSET = 0.914     # doubles post centre, outside the doubles sideline (3 ft)
NET_HEIGHT_POST = 1.07      # net height at the posts
NET_HEIGHT_CENTER = 0.914   # net height at the centre strap

# Doubles posts. On a court marked for doubles these are the posts actually in
# the ground, and are what a phone clip of a singles match still shows.
X_LEFT_POST = X_LEFT_DOUBLES - NET_POST_OFFSET      # -0.914
X_RIGHT_POST = X_RIGHT_DOUBLES + NET_POST_OFFSET    # 11.884

# Singles STICKS, when a singles match is played on a doubles-posted court: the
# same 0.914 m offset, but measured from the SINGLES sideline, and they stand
# INSIDE the doubles alley rather than outside the court. Code that cares which
# it is looking at must choose; the check in tools/render_corner_audit.py draws
# the doubles posts because they are the ones bolted to the ground.
X_LEFT_STICK = X_LEFT_SINGLES - NET_POST_OFFSET     # 0.456
X_RIGHT_STICK = X_RIGHT_SINGLES + NET_POST_OFFSET   # 10.514


# --- Named landmarks --------------------------------------------------------
# 14 intersections a homography solve / keypoint model can anchor on. Names are
# the contract: calibration JSON and detect_court_keypoints() use these keys.
LANDMARKS: dict[str, tuple[float, float]] = {
    # Doubles corners
    "near_bl_doubles": (X_LEFT_DOUBLES, Y_NEAR_BASELINE),
    "near_br_doubles": (X_RIGHT_DOUBLES, Y_NEAR_BASELINE),
    "far_bl_doubles": (X_LEFT_DOUBLES, Y_FAR_BASELINE),
    "far_br_doubles": (X_RIGHT_DOUBLES, Y_FAR_BASELINE),
    # Singles sideline meets baseline
    "near_bl_singles": (X_LEFT_SINGLES, Y_NEAR_BASELINE),
    "near_br_singles": (X_RIGHT_SINGLES, Y_NEAR_BASELINE),
    "far_bl_singles": (X_LEFT_SINGLES, Y_FAR_BASELINE),
    "far_br_singles": (X_RIGHT_SINGLES, Y_FAR_BASELINE),
    # Service line meets singles sideline
    "near_sl_left": (X_LEFT_SINGLES, Y_NEAR_SERVICE),
    "near_sl_right": (X_RIGHT_SINGLES, Y_NEAR_SERVICE),
    "far_sl_left": (X_LEFT_SINGLES, Y_FAR_SERVICE),
    "far_sl_right": (X_RIGHT_SINGLES, Y_FAR_SERVICE),
    # Center service line meets service line (the "T")
    "near_t": (X_CENTER, Y_NEAR_SERVICE),
    "far_t": (X_CENTER, Y_FAR_SERVICE),
}

# --- Line segments for drawing the full court -------------------------------
# Each segment is (start_xy, end_xy) in court metres. overlay.py / the frontend
# project these to pixels with court_to_image to draw the line set.
LINES: list[tuple[tuple[float, float], tuple[float, float]]] = [
    # Baselines
    ((X_LEFT_DOUBLES, Y_NEAR_BASELINE), (X_RIGHT_DOUBLES, Y_NEAR_BASELINE)),
    ((X_LEFT_DOUBLES, Y_FAR_BASELINE), (X_RIGHT_DOUBLES, Y_FAR_BASELINE)),
    # Doubles sidelines
    ((X_LEFT_DOUBLES, Y_NEAR_BASELINE), (X_LEFT_DOUBLES, Y_FAR_BASELINE)),
    ((X_RIGHT_DOUBLES, Y_NEAR_BASELINE), (X_RIGHT_DOUBLES, Y_FAR_BASELINE)),
    # Singles sidelines
    ((X_LEFT_SINGLES, Y_NEAR_BASELINE), (X_LEFT_SINGLES, Y_FAR_BASELINE)),
    ((X_RIGHT_SINGLES, Y_NEAR_BASELINE), (X_RIGHT_SINGLES, Y_FAR_BASELINE)),
    # Service lines
    ((X_LEFT_SINGLES, Y_NEAR_SERVICE), (X_RIGHT_SINGLES, Y_NEAR_SERVICE)),
    ((X_LEFT_SINGLES, Y_FAR_SERVICE), (X_RIGHT_SINGLES, Y_FAR_SERVICE)),
    # Center service line
    ((X_CENTER, Y_NEAR_SERVICE), (X_CENTER, Y_FAR_SERVICE)),
    # Net
    ((X_LEFT_DOUBLES, NET_Y), (X_RIGHT_DOUBLES, NET_Y)),
]


def landmark_names() -> list[str]:
    """Stable ordering of landmark names (dict order is insertion order)."""
    return list(LANDMARKS.keys())


def is_in_singles(x: float, y: float, margin: float = 0.0) -> bool:
    """True if (x, y) lies within the singles court, with an optional margin
    (metres) added to every boundary. Used by the line-call geometry."""
    return (
        X_LEFT_SINGLES - margin <= x <= X_RIGHT_SINGLES + margin
        and Y_NEAR_BASELINE - margin <= y <= Y_FAR_BASELINE + margin
    )


def is_in_doubles(x: float, y: float, margin: float = 0.0) -> bool:
    """True if (x, y) lies within the doubles court, with an optional margin."""
    return (
        X_LEFT_DOUBLES - margin <= x <= X_RIGHT_DOUBLES + margin
        and Y_NEAR_BASELINE - margin <= y <= Y_FAR_BASELINE + margin
    )


def near_half(y: float) -> bool:
    """True if y is on the near side of the net."""
    return y < NET_Y


# --- Independent (non-fitted) anchors ---------------------------------------
# Deliberately NOT added to LINES: LINES is what overlay.py draws and what
# validate_new_clip.py counts horizon crossings over, and changing it would
# change behaviour that has nothing to do with this check.
NET_LINE_SEGMENT: tuple[tuple[float, float], tuple[float, float]] = (
    (X_LEFT_DOUBLES, NET_Y), (X_RIGHT_DOUBLES, NET_Y)
)

# Post bases lie ON the ground plane, so a homography alone projects them.
NET_POST_BASES: dict[str, tuple[float, float]] = {
    "net_post_left": (X_LEFT_POST, NET_Y),
    "net_post_right": (X_RIGHT_POST, NET_Y),
}


def net_post_segments_3d() -> dict[str, tuple[tuple[float, float, float],
                                              tuple[float, float, float]]]:
    """Each net post as a (base_xyz, top_xyz) pair in court metres.

    The top is off the ground plane, so it needs the full camera pose
    (calibration.project_court_3d), not the homography. A post is the anchor a
    foreshortened far baseline is not: small, vertical, high-contrast and
    unambiguous.
    """
    return {
        name: ((x, y, 0.0), (x, y, NET_HEIGHT_POST))
        for name, (x, y) in NET_POST_BASES.items()
    }


# --- 3D keypoints (camera solve) ---------------------------------------------
# World frame for the 3D camera: the court frame above plus z UP, metres. The
# 14 ground intersections, the two centre marks where they meet the baselines,
# and four points OFF the ground plane (the doubles post tops and the net's
# centre strap), which a single camera can use to pin its height. These are the
# names a keypoint detector returns (courtfit.KeypointSet) and camera3d solves on.
LANDMARKS_3D: dict[str, tuple[float, float, float]] = {
    **{name: (x, y, 0.0) for name, (x, y) in LANDMARKS.items()},
    "near_center_mark": (X_CENTER, Y_NEAR_BASELINE, 0.0),
    "far_center_mark": (X_CENTER, Y_FAR_BASELINE, 0.0),
    "net_post_left_base": (X_LEFT_POST, NET_Y, 0.0),
    "net_post_right_base": (X_RIGHT_POST, NET_Y, 0.0),
    "net_post_left_top": (X_LEFT_POST, NET_Y, NET_HEIGHT_POST),
    "net_post_right_top": (X_RIGHT_POST, NET_Y, NET_HEIGHT_POST),
    "net_center_top": (X_CENTER, NET_Y, NET_HEIGHT_CENTER),
}

KEYPOINTS_3D: tuple[str, ...] = tuple(LANDMARKS_3D)

# Named points that lie on ONE straight painted line, in order along it. Any
# four of them have a cross-ratio that perspective cannot change, so a detector
# output that breaks it has a misplaced point (courtfit.cross_ratio_ok).
COLLINEAR_SETS: dict[str, tuple[str, ...]] = {
    "near_baseline": ("near_bl_doubles", "near_bl_singles", "near_center_mark",
                      "near_br_singles", "near_br_doubles"),
    "far_baseline": ("far_bl_doubles", "far_bl_singles", "far_center_mark",
                     "far_br_singles", "far_br_doubles"),
    "left_singles_sideline": ("near_bl_singles", "near_sl_left", "far_sl_left",
                              "far_bl_singles"),
    "right_singles_sideline": ("near_br_singles", "near_sl_right", "far_sl_right",
                               "far_br_singles"),
    "centre_line": ("near_center_mark", "near_t", "far_t", "far_center_mark"),
}
