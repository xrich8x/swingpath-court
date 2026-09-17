"""eval/movers.py - where the PLAYERS are, with no model and no torch.

UNRUN. Written 2026-08-24 as preparation for Session O; no number in this repo has
been measured with it yet. See docs/archive/sessions/SESSION_O_shell_courts.md.

WHY THIS EXISTS
---------------
Two of Session O's branches need the same thing: the image positions where a human
being's feet touched the floor.

  B1 (refuse-only)      project those feet through a candidate homography. Real
                        players stand on the real court, so a court hypothesis that
                        collapses 23.77 m onto a curtain band near the horizon sends
                        them to absurd court coordinates. That refutes the
                        `am_ntrp45w`-family failure with closed-form geometry and no
                        vanishing point, no horizon fit and no cross-ratio.
  B2 (recall-positive)  roof trusses, strip lights and the upper fence lattice are
                        ABOVE every point a player can stand on, so the highest foot
                        seen bounds the court region from above. Zeroing the mask
                        above it removes architecture from the Hough pool BEFORE the
                        lines are detected.

WHY NOT THE POSE MODEL WE ALREADY SHIP
--------------------------------------
`pose.PoseEstimator` would give better feet, but court detection runs BEFORE any
perception and is classical + CPU with no torch dependency. Inverting that order to
gate calibration on a neural net is a large architectural change to buy a foot point.
A temporal-median clean plate gives one for free, and if it turns out not to be good
enough THAT is the finding that justifies the bigger change.

WHY THE HORIZON IS NOT FITTED FROM THESE POINTS
-----------------------------------------------
The research reply proposed fitting the ground-plane horizon from foot spread. Our
8 frames come from ONE short clip cut at a serve boundary, so the players barely
move and that fit is ill-conditioned exactly where it is needed. Projecting feet
through a candidate H asks less of the same evidence.

NOTHING HERE DECIDES ANYTHING. The helpers report fractions and rows; every accept /
refuse threshold stays in the caller, so it can be pre-registered next to the run
that measures it rather than buried in a library as an unmeasured constant.
"""

from __future__ import annotations

import numpy as np

# A standing person, as a fraction of frame area. The lower bound is what a far
# player costs at 640 wide; the upper bound rejects a lighting change or a camera
# nudge repainting half the frame.
AREA_MIN_FRAC = 2.0e-4
AREA_MAX_FRAC = 6.0e-2
# A person is taller than wide, but a lunging or running player is not, so this is
# deliberately loose - it exists to drop long thin horizontal artefacts (a banner
# flapping, a rolling-shutter band), not to insist on a posture.
MIN_H_OVER_W = 0.8
# A tennis court holds at most four people. Measured on the 20 gold clips, the
# size/aspect filters alone let through a MEDIAN OF ~9 blobs PER FRAME (up to 18) -
# crowd, scoreboard flicker, trees, and high-contrast edges shivering under camera
# shake. That wrecks the statistic the crop depends on: the 5th percentile of foot Y
# landed at 55-132 px in a 360 px frame, i.e. the top third, which is nowhere a
# player can stand. Keeping only the largest few is not a tuned threshold, it is the
# rules of the game - and unlike a threshold it cannot drift.
MAX_PLAYERS = 4


# Movers are blobs, not detail. The shell footage is 4K, and a temporal median over
# eight 4K colour frames is a ~1.6 GB float64 intermediate for a result measured in
# whole limbs - so the whole stage runs downscaled and the foot points are scaled
# back to the caller's pixels at the end.
WORK_W = 960


def _prep(images):
    """([gray_small], scale) where scale multiplies a small-image x/y back to full."""
    import cv2

    ims = list(images)
    if not ims:
        return [], 1.0
    h, w = ims[0].shape[:2]
    f = min(1.0, WORK_W / float(w))
    out = []
    for im in ims:
        g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
        if f < 1.0:
            g = cv2.resize(g, (int(round(w * f)), int(round(h * f))),
                           interpolation=cv2.INTER_AREA)
        out.append(g)
    return out, 1.0 / f


# The crop wants foot points from the WHOLE recording (see crop_row), which can be
# hundreds of frames - but a median needs only enough frames to outvote the players,
# and a 120-frame float64 median is half a gigabyte for no extra accuracy.
PLATE_MAX = 31


def clean_plate(grays) -> np.ndarray:
    """Per-pixel temporal median of GRAYSCALE frames. The camera is static, so this
    is the court with the people taken out. Median, not mean: a mean leaves a ghost
    of every player it averaged over."""
    g = list(grays)
    if len(g) > PLATE_MAX:
        g = [g[i] for i in np.linspace(0, len(g) - 1, PLATE_MAX).round().astype(int)]
    return np.median(np.stack(g, axis=0), axis=0).astype(np.uint8)


def _diff_threshold(d: np.ndarray) -> float:
    """Noise-relative, not absolute. An indoor hall under strip lights and a bright
    outdoor court sit at completely different absolute difference levels; a constant
    works on one and not the other (the same lesson split_by_serve.py records for
    its motion trace). MAD is the noise, so 3 sigma above it is a mover."""
    mad = float(np.median(np.abs(d - np.median(d))))
    return float(np.clip(3.0 * 1.4826 * max(mad, 1e-3), 15.0, 60.0))


def foot_points(images):
    """[(frame_idx, x, y, area_frac)] - the bottom-centre of every player-sized blob,
    in the CALLER's pixel coordinates.

    Bottom-centre, not centroid: the contact point with the floor is what carries
    the ground-plane information. A centroid sits at chest height and would imply a
    plane a metre above the court."""
    import cv2

    grays, s = _prep(images)
    if len(grays) < 3:
        return []
    gp = clean_plate(grays)
    h, w = gp.shape[:2]
    area = float(h * w)
    k = max(3, int(round(w / 213.0)) | 1)          # ~3 px at 640 wide, odd

    out = []
    for i, g in enumerate(grays):
        frame_blobs = []
        d = cv2.absdiff(g, gp)
        d = cv2.GaussianBlur(d, (k, k), 0)
        m = (d >= _diff_threshold(d)).astype(np.uint8) * 255
        m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((k, k), np.uint8))
        m = cv2.morphologyEx(m, cv2.MORPH_CLOSE,
                             np.ones((k * 3, k * 3), np.uint8))
        n, _lab, stats, _cent = cv2.connectedComponentsWithStats(m, 8)
        for j in range(1, n):
            x, y, bw, bh, a = stats[j]
            af = a / area
            if not (AREA_MIN_FRAC <= af <= AREA_MAX_FRAC):
                continue
            if bh < MIN_H_OVER_W * bw:
                continue
            if y + bh < 0.15 * h:                  # entirely in the roof band
                continue
            frame_blobs.append((i, (x + bw / 2.0) * s, (y + bh) * s, float(af)))
        frame_blobs.sort(key=lambda b: -b[3])      # largest first
        out.extend(frame_blobs[:MAX_PLAYERS])
    return out


def foot_band(feet):
    """(y_min, y_max) over every foot point, or None. y_min is the FURTHEST a player
    was seen standing - the top of the region the court can occupy."""
    if not feet:
        return None
    ys = np.asarray([f[2] for f in feet], float)
    return float(ys.min()), float(ys.max())


DEEP_PCT = 5.0          # 5th percentile of foot Y == 95th percentile of DEPTH
CROP_K = 1.0            # pre-registered margin, in units of the foot-Y spread
CROP_FLOOR_FRAC = 0.05  # absolute margin floor, as a fraction of frame height
CROP_MIN_SPREAD = 0.02  # below this much foot-Y spread, nothing is bounded


def crop_row(feet, frame_h: int, k: float = CROP_K,
             never_below_y: float | None = None) -> int | None:
    """The row above which the mask is architecture, not court. None = do not crop.

        y_deep = 5th percentile of foot Y      (the 95th percentile of DEPTH)
        row    = y_deep - k * spread - floor
        row    = min(row, never_below_y)       (hard rule)

    THE RISK IS ASYMMETRIC AND THIS IS BUILT AROUND THAT. Too permissive costs
    nothing - a spectator on a balcony or a shadow on the fence pushes the row UP,
    the crop removes less clutter, and the fit is exactly what it is today. Too
    aggressive is the dangerous direction: a recording where no player ever goes
    deep puts the row BELOW the far baseline, the crop deletes true court lines, and
    the detector returns a WRONG COURT rather than a refusal. Wrong courts are the
    one thing the gate does not tolerate.

    So each ingredient is doing a specific job, and they are not interchangeable:

      DEEP_PCT is for USEFULNESS, not safety. A raw min over a 25-minute recording
        picks up every spectator and bird and puts the row near the top of the
        frame, where the crop removes nothing. The percentile buys a crop that
        actually does something; it does NOT buy safety, and reading it that way
        gets the sign backwards.
      k AND CROP_FLOOR_FRAC are the safety. The floor matters because the spread
        term vanishes exactly when the evidence is thin.
      never_below_y is the backstop, and it is the only ingredient that cannot be
        fooled by the foot statistics at all.

    FEED THIS THE WHOLE RECORDING, not the 8 frames used for fitting. `y_deep` is
    essentially a max-statistic over depth, and a max-statistic on 8 samples is
    exactly where this fails: more frames make it converge on the deepest position
    a player really reached. `run_refs.frames_from(video, 120)` is the intended
    source, and the plate is subsampled internally so the cost stays flat.

    never_below_y: the topmost candidate court line, in this frame's pixels. The
    crop is generated before any fit, so the caller has to source it - either from
    the per-frame locks of the uncropped pass (the min over their topmost projected
    line), or, when verifying, from the human court. Policy stays with the caller;
    this function only enforces it."""
    if not feet:
        return None
    ys = np.asarray([f[2] for f in feet], float)
    lo, hi = float(np.percentile(ys, DEEP_PCT)), float(np.percentile(ys, 95.0))
    if hi - lo < frame_h * CROP_MIN_SPREAD:
        return None                   # players never separated - nothing is bounded
    row = lo - k * (hi - lo) - CROP_FLOOR_FRAC * frame_h
    if never_below_y is not None:
        row = min(row, never_below_y - CROP_FLOOR_FRAC * frame_h)
    row = int(round(row))
    return None if row <= 0 else min(row, frame_h - 1)


def cropped_mask_fn(base_fn, row: int | None):
    """Wrap a mask function so everything above `row` is zeroed.

    Zeroes the MASK rather than the frame: blanking pixels would create a hard
    synthetic edge at the crop row that the ridge filter would then detect as a
    line, handing the fitter a perfectly straight horizontal confuser."""
    if row is None or row <= 0:
        return base_fn

    def _fn(frame):
        m = base_fn(frame)
        m = m.copy()
        m[:row] = 0
        return m
    return _fn


GATE_MARGIN_M = 10.0


def feet_in_court(H, feet, calibration, court, margin_m: float = GATE_MARGIN_M):
    """(fraction_inside, median_court_xy) for the feet under this homography.

    A correct court puts players on it, or just off it. The collapsed-onto-the-
    horizon failure puts them hundreds of metres away or behind the camera, so the
    fraction falls off a cliff rather than degrading.

    THE MARGIN IS COARSE ON PURPOSE AND MUST STAY COARSE. Two independent reasons,
    and both of them are about what this measurement can actually resolve:

      * the foot points come back from a downscaled pass, so they carry +/- one
        scale factor of pixel error - and near the far baseline, where the ground
        plane is nearly edge-on, a few pixels is several METRES on the court. The
        resolution simply is not there for a tight test.
      * players legitimately stand well behind a baseline, and a gate that fires on
        a deep return is a gate that spends the precision record.

    So this separates "on the court" from "hundreds of metres away", which is the
    only distinction the evidence supports and the only one the failure needs. It is
    fine for the crop, which is a bound; it is not fine to read this as a position.

    Returns (0.0, None) when there are no feet - the caller must read that as NO
    EVIDENCE and skip the gate, not as a refusal."""
    if not feet:
        return 0.0, None
    pts = [[f[1], f[2]] for f in feet]
    try:
        xy = np.asarray(calibration.image_to_court(H, pts), float)
    except Exception:
        # a collapsed court can be singular, and image_to_court inverts H. That is
        # a refutation, not an error - but report it as no-evidence and let the
        # caller decide, so this helper still owns no policy.
        return 0.0, None
    ok = np.isfinite(xy).all(axis=1)
    if not ok.any():
        return 0.0, None
    xy = xy[ok]
    inside = ((xy[:, 0] >= -margin_m) & (xy[:, 0] <= court.DOUBLES_WIDTH + margin_m) &
              (xy[:, 1] >= -margin_m) & (xy[:, 1] <= court.LENGTH + margin_m))
    med = [float(np.median(xy[:, 0])), float(np.median(xy[:, 1]))]
    return float(inside.mean()), med
