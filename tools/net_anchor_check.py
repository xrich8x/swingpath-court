"""The NET-ANCHOR check: verify a 4-corner calibration against something the four
corners did NOT determine.

Why this exists
---------------
On 2026-09-05 `yt_match40` was re-clicked and came back STILL WRONG while
IMPROVING on every screen this project owns: fit residual 0.9 -> 0.2 px, camera
height 11.3 m (impossible) -> 1.61 m (plausible), `verify_court` line coverage
0.436 -> 0.944, higher than almost every CORRECT calibration in the repo. The far
corners had been placed on the NET rather than the far baseline, mapping the whole
court onto the near half.

Coverage rewards that. A court squashed into the near half still projects its
lines onto real paint - the near baseline, both service lines, the centre line,
the sidelines - just the wrong paint. **Coverage measures whether lines land on
paint, not whether they land on the paint they are named for.**

What caught it was projecting the NET (court-y = 11.885 m), a distinct physical
object with tape and posts, and seeing it land ~36 px below the real net. This
module makes that a first-class check.

Why it is not circular
----------------------
Four clicked doubles corners determine H exactly (4 points, 8 DOF). Anything
projected through H is a CONSEQUENCE of the clicks, so scoring the projected
court lines against paint is close to grading the clicks with themselves. The
escape has two parts, and BOTH are needed:

  1. the projected feature is not one of the four fitted points - the net line,
     the net band and the two net posts are never clicked;
  2. it is checked against DIFFERENT image evidence than white court paint - net
     mesh texture, and small vertical high-contrast posts standing outside the
     doubles sideline.

That second part is what coverage lacks. A wrong-but-plausible quad can keep
landing on paint; it cannot conjure a net where there is none.

Net posts are the founder's suggestion and they are the right anchor here for
exactly the reason the failure happened: a foreshortened far baseline at the top
of frame is ambiguous (net tape, fence, a line 12 m further away all look
similar at that scale), while a post is small, vertical, high-contrast and
unambiguous. Post bases lie on the ground plane so the homography places them;
post tops are 1.07 m up and need the camera pose.

Measurements, and the bars, PRE-REGISTERED
------------------------------------------
Written down before any clip was measured. n=1 clip cannot validate a threshold,
so these are a TRIAGE ORDER, not a verdict - this project's own rule is that a
residual is not a verdict and the frame is.

  band_ratio  median edge energy in the projected NET BAND (net line up to the
              net's own height) over the same statistic in the court-surface
              strip 0.2-1.2 m in front of it. A net is a mesh: high edge density.
              Court surface is smooth. A net line projected onto bare court
              scores ~1.
              BAR: band_ratio < 1.5 -> FLAG.

  dy_best     the vertical pixel shift, applied RIGIDLY to both strips together,
              that maximises band_ratio. This is the automated form of "the
              projected net is 36 px below the real net". 0 is agreement.
              BAR: |dy_best| > 0.5 * projected net pixel height -> FLAG.

Post evidence is rendered but deliberately NOT gated: posts are off-frame on
most low wide mounts in this repo, so a post-based bar would be a bar on framing.

GROUND vs TAPE - the mistake this tool must not let anyone repeat
----------------------------------------------------------------
There are TWO net rows in every frame and they are not the same row:

  * the net GROUND line, court-y 11.885 at z = 0, which is what a homography
    gives you and what `court.LINES` draws;
  * the net TOP TAPE, the white strip a human actually looks at, at z = 0.914 m
    at the centre strap rising to z = 1.07 m at the posts. It needs the camera
    POSE (`calibration.project_court_3d` with an hfov from
    `courtfit.cam_fit_quad`), not the homography.

Comparing the projected ground line against the observed tape is apples to
oranges and fails on every CORRECT calibration. That is exactly how the
2026-09-05 `yt_match40` re-click was mistakenly called wrong: the ground line
projected at row 325 was compared to tape observed at ~295 and the 30 px gap
read as an error. For a pinhole at height H, (row - horizon) is proportional to
H / depth, so a point h above the ground at the same depth scales the offset by
(H - h) / H. At H = 1.64 m with the horizon at row 264.6, the tape MUST image at
264.6 + (325 - 264.6) * (1.64 - 0.914) / 1.64 = 291.3. Observed ~295, so the
real disagreement was 3.7 px and the calibration is correct.

So this module reports `horizon_row`, `net_ground_row` and `net_tape_row`
explicitly, and the render labels the two lines differently. Anyone eyeballing
the PNG can redo that arithmetic instead of repeating the error.

Limits
------
* THE TWO BARS FAILED on first contact with the corpus and are retained ONLY as
  reported numbers - see docs/evidence/net-anchor-calibration-check.md. They
  flagged 14 of 27 calibrations including `yt_match40`, which is now known
  CORRECT (0.0 px residual, 1.64 m camera, coverage 0.948). A failed bar stays
  failed; it is not being moved to fit the result. Read `flags` as "look at this
  PNG first", never as a verdict.
* Both bars are one-clip-motivated and unvalidated. Treat FLAG as "open the PNG".
* `band_ratio` needs a camera pose (hfov) to place the net's height. Where the
  pose is unrecoverable the check degrades to the rendered picture only.
* A player, a shadow, a fence or a crowd inside either strip inflates the edge
  energy. Medians across 41 columns blunt that; they do not remove it.
* The control strip is on the NEAR side of the net, which on a badly squashed
  calibration may fall outside the court entirely. That makes the ratio harder
  to interpret, not wrong - the picture settles it.
"""

from __future__ import annotations

import pathlib
import sys

import cv2
import numpy as np

REPO = pathlib.Path(__file__).resolve().parents[1]
if str(REPO / "backend") not in sys.path:
    sys.path.insert(0, str(REPO / "backend"))

from swingvision import calibration, court as _court   # noqa: E402

CORNERS = ["near_bl_doubles", "near_br_doubles", "far_br_doubles", "far_bl_doubles"]

NET_SAMPLES = 41          # columns across the doubles width
NET_DEPTH_SAMPLES = 10    # points sampled up each column
BAR_BAND_RATIO = 1.5      # pre-registered
BAR_DY_FRAC = 0.5         # pre-registered, as a fraction of net pixel height


def net_height_at(x: float) -> float:
    """Net height in metres at court-x: centre strap 0.914 m rising to 1.07 m at
    the post. Linear, which is not the true catenary but is well under a pixel
    of difference at any mount this project sees."""
    span = _court.X_RIGHT_POST - _court.X_CENTER
    frac = min(1.0, abs(x - _court.X_CENTER) / span)
    return (_court.NET_HEIGHT_CENTER
            + frac * (_court.NET_HEIGHT_POST - _court.NET_HEIGHT_CENTER))


def hfov_for(kp, w, h):
    """Horizontal FOV from the FITTED camera, never the 70 deg default.

    Mounts in this repo run 60-90 deg and the wrong focal moves a projected post
    top by more than a post is wide, which would make the render lie."""
    try:
        from swingvision import courtfit
        fit = courtfit.cam_fit_quad({n: kp[n] for n in CORNERS}, calibration,
                                    _court, w, h, allow_roll=True)
        if fit is not None:
            return float(calibration.hfov_from_focal(fit[3][5], w))
    except Exception:                                   # noqa: BLE001
        pass
    return None


def net_anchor_geometry(kp, img_wh, hfov_deg=None):
    """Project the net-anchor features. Ground-plane parts (net line, post BASES)
    go through the homography; anything with height (the net band top, post TOPS)
    needs the camera pose and is None when that is unrecoverable or the point is
    behind the camera."""
    H = calibration.compute_homography([_court.LANDMARKS[n] for n in CORNERS],
                                       [kp[n] for n in CORNERS])
    xs = np.linspace(_court.X_LEFT_DOUBLES, _court.X_RIGHT_DOUBLES, NET_SAMPLES)
    net_ground = calibration.court_to_image(H, [(x, _court.NET_Y) for x in xs])
    posts = {n: calibration.court_to_image(H, [b])[0]
             for n, b in _court.NET_POST_BASES.items()}
    tops, band_top = {}, None
    if hfov_deg is not None:
        for n, (_b, t) in _court.net_post_segments_3d().items():
            pt = calibration.project_court_3d(H, img_wh, [t], hfov_deg)
            tops[n] = None if pt is None else pt[0]
        band_top = calibration.project_court_3d(
            H, img_wh, [(float(x), _court.NET_Y, net_height_at(float(x))) for x in xs],
            hfov_deg)
    band_top = None if band_top is None else np.asarray(band_top, float)
    mid = NET_SAMPLES // 2
    return {"H": H, "xs": xs, "net_ground": np.asarray(net_ground, float),
            "post_bases": posts, "post_tops": tops, "band_top": band_top,
            "horizon_row": horizon_row(H, img_wh),
            "net_ground_row": round(float(net_ground[mid][1]), 1),
            "net_tape_row": None if band_top is None
            else round(float(band_top[mid][1]), 1)}


def horizon_row(H, img_wh):
    """Image row of the ground plane's VANISHING LINE at the frame centre column.

    l = H^-T [0,0,1]^T is the image of the plane's line at infinity. This is the
    reference the (row - horizon) proportional-to-H/depth relation is measured
    from, so reporting it lets a reader re-derive the expected tape row by hand.
    Returns None when the horizon is parallel to the column (a nadir view).
    """
    try:
        line = np.linalg.inv(np.asarray(H, float)).T @ np.array([0.0, 0.0, 1.0])
        a, b, c = line
        x = float(img_wh[0]) / 2.0
        if abs(b) < 1e-12:
            return None
        return round(float(-(a * x + c) / b), 1)
    except Exception:                                   # noqa: BLE001
        return None


def _sample(edge, pts):
    """Mean edge energy at integer-rounded pixel locations; nan if all off-frame."""
    h, w = edge.shape
    p = np.rint(np.asarray(pts, float))
    p = p[np.isfinite(p).all(axis=1)].astype(int)
    if len(p) == 0:
        return float("nan")
    ok = (p[:, 0] >= 0) & (p[:, 0] < w) & (p[:, 1] >= 0) & (p[:, 1] < h)
    if not ok.any():
        return float("nan")
    return float(edge[p[ok, 1], p[ok, 0]].mean())


def _band_ratio(edge, geo, dy):
    """Median NET-BAND edge energy over median COURT-SURFACE edge energy, with the
    whole construct shifted dy pixels. Both strips shift TOGETHER, so dy is a
    rigid translation of a paired measurement, not a free parameter that can go
    hunting for texture on its own."""
    H = geo["H"]
    ctrl_y = np.linspace(_court.NET_Y - 1.2, _court.NET_Y - 0.2, NET_DEPTH_SAMPLES)
    a, b = [], []
    for i, x in enumerate(geo["xs"]):
        g, t = geo["net_ground"][i], geo["band_top"][i]
        if not (np.isfinite(g).all() and np.isfinite(t).all()):
            continue
        col = np.linspace(t, g, NET_DEPTH_SAMPLES) + np.array([0.0, dy])
        ctrl = np.asarray(calibration.court_to_image(
            H, [(float(x), float(y)) for y in ctrl_y]), float) + np.array([0.0, dy])
        a.append(_sample(edge, col))
        b.append(_sample(edge, ctrl))
    a, b = np.asarray(a, float), np.asarray(b, float)
    m = np.isfinite(a) & np.isfinite(b)
    if int(m.sum()) < 8:
        return None, int(m.sum())
    na, nb = float(np.median(a[m])), float(np.median(b[m]))
    return (na / nb if nb > 1e-6 else None), int(m.sum())


def measure(frame, kp, img_wh, hfov_deg):
    """Quantitative half of the check. See the module docstring for the bars."""
    gray = cv2.GaussianBlur(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), (3, 3), 0)
    edge = cv2.magnitude(cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3),
                         cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3))
    geo = net_anchor_geometry(kp, img_wh, hfov_deg)
    out = {"net_px_height": None, "band_ratio": None, "ratio_best": None,
           "dy_best": None, "columns": 0, "flags": [],
           "horizon_row": geo["horizon_row"],
           "net_ground_row": geo["net_ground_row"],
           "net_tape_row": geo["net_tape_row"]}
    if geo["band_top"] is None:
        out["flags"].append("no camera pose - net height not projectable")
        return out, geo
    nh = float(np.median(np.abs(geo["net_ground"][:, 1] - geo["band_top"][:, 1])))
    out["net_px_height"] = round(nh, 1)
    r0, n = _band_ratio(edge, geo, 0.0)
    out["columns"] = n
    if r0 is None:
        out["flags"].append("net band falls outside the frame")
        return out, geo
    out["band_ratio"] = round(r0, 2)
    span = int(max(12, round(3.0 * nh)))
    step = max(1, span // 60)
    best = (r0, 0.0)
    for dy in range(-span, span + 1, step):
        r, k = _band_ratio(edge, geo, float(dy))
        if r is not None and k >= 8 and r > best[0]:
            best = (r, float(dy))
    out["ratio_best"], out["dy_best"] = round(best[0], 2), best[1]
    if r0 < BAR_BAND_RATIO:
        out["flags"].append(
            f"band_ratio {r0:.2f} < {BAR_BAND_RATIO} - no net texture where this "
            f"calibration puts the net")
    if abs(best[1]) > BAR_DY_FRAC * nh:
        out["flags"].append(
            f"most net-like band is dy={best[1]:+.0f} px away "
            f"(> {BAR_DY_FRAC} x net height {nh:.0f} px)")
    return out, geo


def draw(frame, geo, meas, caption_rows):
    """Overlay the net line, the net band and both posts, plus a caption block."""
    img = frame.copy()
    h, w = img.shape[:2]
    # TWO lines, drawn and named differently on purpose. Reading the white tape
    # against the GROUND line is the apples-to-oranges error this tool exists to
    # stop; see the module docstring.
    pts = np.int32(geo["net_ground"])
    cv2.polylines(img, [pts], False, (0, 160, 0), 2, cv2.LINE_AA)
    mid = pts[len(pts) // 2]
    cv2.putText(img, "net GROUND z=0 (homography)", (int(mid[0]) - 130, int(mid[1]) + 26),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 200, 0), 2, cv2.LINE_AA)
    if geo["band_top"] is not None:
        tp = np.int32(geo["band_top"])
        cv2.polylines(img, [tp], False, (0, 255, 255), 2, cv2.LINE_AA)
        m2 = tp[len(tp) // 2]
        cv2.putText(img, "net TAPE z=0.914m (pose)  <- compare THIS to the white tape",
                    (int(m2[0]) - 130, int(m2[1]) - 12),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 2, cv2.LINE_AA)
    off = []
    for name, base in geo["post_bases"].items():
        bx, by = int(round(base[0])), int(round(base[1]))
        if not (0 <= bx < w and 0 <= by < h):
            off.append(name.replace("net_", ""))
            continue
        top = geo["post_tops"].get(name)
        if top is not None and np.isfinite(top).all():
            cv2.line(img, (bx, by), (int(round(top[0])), int(round(top[1]))),
                     (80, 80, 255), 3, cv2.LINE_AA)
        cv2.drawMarker(img, (bx, by), (80, 80, 255), cv2.MARKER_TILTED_CROSS, 26, 2)
        cv2.putText(img, name.replace("net_", ""), (bx + 12, by + 22),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (80, 80, 255), 2, cv2.LINE_AA)

    scale = 1280.0 / w
    if abs(scale - 1.0) > 0.01:
        img = cv2.resize(img, (1280, int(h * scale)), interpolation=cv2.INTER_AREA)
    rows = list(caption_rows)
    if off:
        rows.append(("off-frame, not drawn: " + ", ".join(off)
                     + "  (normal on a low wide mount)", (0, 190, 255)))
    rows.append((("FLAG: " + "; ".join(meas["flags"]))[:150] if meas["flags"] else
                 "no automatic flag - the picture is still the verdict",
                 (0, 0, 255) if meas["flags"] else (140, 140, 140)))
    cap = np.zeros((26 + 25 * len(rows), img.shape[1], 3), np.uint8)
    for i, (t, c) in enumerate(rows):
        cv2.putText(cap, t, (8, 22 + i * 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, c, 1,
                    cv2.LINE_AA)
    return np.vstack([cap, img])
