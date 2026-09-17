"""Court auto-calibration: line-fit + camera prior + regulation-structure matching.

The perception stage that finds the court in amateur footage WITHOUT a learned
model: detect distinct straight lines, score candidate courts by orientation-aware
line support, rank poses by a camera prior learned from labeled courts, demand the
REGULATION STRUCTURE (each court line claiming its own real line, both directions),
and hard-gate every output through a physical 6-DOF camera re-fit — the module can
never emit a shape that is not a real camera's view of a regulation tennis court.

Developed and measured against the hand-labeled gold set (scorecards in git; the
eval harness lives in tools/eval_court_autodetect.py and tools/
eval_court_consensus.py and imports this module). Multi-frame consensus voting +
the clay/shell evidence-stacking rescue live here too, plus the two pipeline
entry points:

  auto_fit_frame(frame, calibration, court)   -> corners or None (one frame)
  fit_video_frames(frames, calibration, court) -> (corners, votes, tag) (a clip)

Confidence law (held on every clip incl. cold tests): >=6/8 agreeing frames has
always been a correct court; every wrong lock had <=4 votes. Callers auto-accept
only tag=="vote" with votes>=6; anything else goes to the overlay confirm tool.
"""

from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Protocol

import numpy as np

REPO = Path(__file__).resolve().parents[2]
DBL = ["near_bl_doubles", "near_br_doubles", "far_br_doubles", "far_bl_doubles"]

# --- the GLOBAL-PROPOSAL source (flag; shipped default unchanged) -------------
# The three-step recipe is: GLOBAL localisation -> LOCAL refinement -> 6-DOF gate.
# Only step one is switchable here.
#   "classical" - `autodetect`: Hough lines + regulation-structure matching (SHIPPED)
#   "courtnet"  - `calibration.detect_court_learned`: the vendored 15-channel
#                 heatmap CNN, used for GLOBAL localisation only.
# Steps two and three (snap_to_lines, lock_quad) and the consensus vote are the
# same objects either way - that is the point of the experiment. One variable.
COURT_PROPOSERS = ("classical", "courtnet")
COURTNET_BASE_WEIGHTS = str(REPO / "backend" / "weights" / "court_detector.pt")


# Court line samples + endpoints (court metres), cached — H-independent.
_S = _LINE_ID = _EA = _EB = None


def _court_samples(court):
    global _S, _LINE_ID, _EA, _EB
    if _S is None:
        S, lid, EA, EB = [], [], [], []
        for i, (a, b) in enumerate(court.LINES):
            EA.append(a); EB.append(b)
            n = max(2, int(math.hypot(b[0]-a[0], b[1]-a[1]) * 3))
            for t in np.linspace(0, 1, n):
                S.append((a[0]+t*(b[0]-a[0]), a[1]+t*(b[1]-a[1]))); lid.append(i)
        _S, _LINE_ID = np.asarray(S), np.asarray(lid)
        _EA, _EB = np.asarray(EA), np.asarray(EB)
    return _S, _LINE_ID, _EA, _EB


def _detect_lines(mask, w):
    """The REAL straight lines in the frame, as distinct infinite lines.

    Hough gives segments; segments of the same painted line are merged into ONE line
    (normal form rho/theta) so we can ask the structural question: does each court
    line land on its OWN real line? Returns [(theta, rho, weight)]."""
    import cv2
    segs = cv2.HoughLinesP(mask, 1, np.pi/180, threshold=45,
                           minLineLength=max(25, int(w*0.05)), maxLineGap=12)
    if segs is None:
        return []
    raw = []
    for x1, y1, x2, y2 in segs[:, 0]:
        th = np.arctan2(y2-y1, x2-x1)              # direction
        n = th + np.pi/2.0                         # normal
        rho = x1*np.cos(n) + y1*np.sin(n)
        if rho < 0:                                # canonical sign
            n, rho = n + np.pi, -rho
        raw.append((np.mod(n, np.pi), rho, float(np.hypot(x2-x1, y2-y1))))
    merged = []
    for n, rho, wt in sorted(raw, key=lambda r: -r[2]):
        for i, (mn, mr, mw) in enumerate(merged):
            dth = abs(np.mod(n - mn + np.pi/2, np.pi) - np.pi/2)
            if dth < np.deg2rad(4) and abs(rho - mr) < max(6.0, w*0.012):
                tot = mw + wt
                merged[i] = ((mn*mw + n*wt)/tot, (mr*mw + rho*wt)/tot, tot)
                break
        else:
            merged.append((n, rho, wt))
    return merged


def _clay_mask(frame, calibration):
    """Hue-agnostic, structure-cleaned line mask for clay/shell.

    Two problems with clay: (1) the default mask demands sat<90 ("must be WHITE") and
    clay lines are lighter-but-ORANGE, so it sees nothing; (2) the clay surface itself
    is speckly, so a permissive mask returns the lines PLUS a storm of texture noise.
    Fix (1) with sat_max=255. Fix (2) by trusting STRUCTURE: court lines are long and
    continuous, texture noise is short and isolated — so keep only pixels that belong
    to a long straight segment (Hough), which erases the speckle and leaves clean
    lines for the snap to lock onto."""
    import cv2
    raw = calibration.line_ridge_mask(frame, tau=12, sat_max=255)
    segs = cv2.HoughLinesP(raw, 1, np.pi/180, threshold=50,
                           minLineLength=max(40, int(frame.shape[1] * 0.08)), maxLineGap=14)
    clean = np.zeros_like(raw)
    if segs is not None:
        for x1, y1, x2, y2 in segs[:, 0]:
            cv2.line(clean, (int(x1), int(y1)), (int(x2), int(y2)), 255, 2)
    return clean


def _precompute(frame, calibration, mask_fn=None):
    """Per-frame maps: distance-to-line, the local LINE ORIENTATION (double-angle
    cos/sin, so 0 and 180deg are the same line), and the DISTINCT real lines."""
    import cv2
    mask = (mask_fn or calibration.court_line_mask)(frame)
    h, w = mask.shape[:2]
    dt = cv2.distanceTransform(255 - mask, cv2.DIST_L2, 5)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).astype(np.float32)
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    lang = np.arctan2(gy, gx) + np.pi / 2.0        # line dir = perpendicular to gradient
    return dt, np.cos(2*lang), np.sin(2*lang), w, h, _detect_lines(mask, w)


EVID_BAND = 5.0     # "is there ANY paint near this line?" band, in units of tol
EVID_MIN = 0.20     # a line counts as measurable if this much of it has paint nearby


def _ori_detail(H, calibration, court, dt, cos2, sin2, w, h, tol, athr):
    """Returns (agreement, n_lines_supported, n_lines_with_evidence).

    EVIDENCE-BASED, not model-recall. A court is a regulation shape, so a line with
    no paint (worn clay, covered, repainted over) is MISSING EVIDENCE — not proof the
    fit is wrong. Scoring "what fraction of my lines did I find?" punishes a faded
    court for being faded. So:
      * a line with NO paint anywhere near it is UNMEASURABLE -> excluded entirely
      * among lines that DO have paint, we score how well the paint agrees
    A sample agrees if it sits on a line pixel (<=tol) AND the local ridge
    orientation matches the projected line. Absence of evidence is never a penalty;
    disagreeing evidence is."""
    S, lid, EA, EB = _court_samples(court)
    P = calibration.court_to_image(H, S)
    pa = calibration.court_to_image(H, EA)
    pb = calibration.court_to_image(H, EB)
    ang = np.arctan2(pb[:, 1]-pa[:, 1], pb[:, 0]-pa[:, 0])
    c2, s2 = np.cos(2*ang)[lid], np.sin(2*ang)[lid]
    x, y = np.round(P[:, 0]).astype(int), np.round(P[:, 1]).astype(int)
    inb = (x >= 0) & (x < w) & (y >= 0) & (y < h)
    if int(inb.sum()) < len(P) * 0.30:
        return 0.0, 0, 0
    xi, yi = np.clip(x, 0, w-1), np.clip(y, 0, h-1)
    align = cos2[yi, xi]*c2 + sin2[yi, xi]*s2
    d = dt[yi, xi]
    sup = inb & (d <= tol) & (align >= athr)      # paint here, and it agrees
    near = inb & (d <= tol * EVID_BAND)           # paint anywhere near -> measurable
    nL = int(lid.max()) + 1
    inb_cnt = np.bincount(lid, weights=inb.astype(float), minlength=nL)
    sup_cnt = np.bincount(lid, weights=sup.astype(float), minlength=nL)
    near_cnt = np.bincount(lid, weights=near.astype(float), minlength=nL)
    seen = inb_cnt >= 3                                   # line meaningfully in frame
    ev = seen & (near_cnt / np.maximum(inb_cnt, 1) >= EVID_MIN)   # paint exists here
    if not ev.any():
        return 0.0, 0, 0
    agree = float(sup_cnt[ev].sum()) / float(max(1.0, inb_cnt[ev].sum()))
    frac = np.where(seen, sup_cnt / np.maximum(inb_cnt, 1), 0.0)
    return agree, int((frac >= 0.5).sum()), int(ev.sum())


def _corners(cx, yn, yf, wn, wf):
    return {"near_bl_doubles": [cx-wn, yn], "near_br_doubles": [cx+wn, yn],
            "far_br_doubles": [cx+wf, yf], "far_bl_doubles": [cx-wf, yf]}


def court_centrality_ok(frame, H, calibration, min_centrality: float = 0.55):
    """Pose sanity for the clay path (verify_court is white-mask-blind there)."""
    return calibration.court_centrality(frame, H) >= min_centrality


# --- Structure: a court is 4 lines ACROSS and 4 lines LENGTHWISE, in a known order.
# Every one must land on its OWN real line. A shifted/wrong-rung court fails this:
# its baseline lands on the real SERVICE line, so two model lines fight over one
# real line and the outer ones match nothing. Pure line-support can't see that;
# distinct correspondence can.
STRUCT_LINES = [
    ((0, 0), (10.97, 0)),              # near baseline
    ((1.37, 5.485), (9.6, 5.485)),     # near service line
    ((1.37, 18.285), (9.6, 18.285)),   # far service line
    ((0, 23.77), (10.97, 23.77)),      # far baseline
    ((0, 0), (0, 23.77)),              # left doubles sideline
    ((1.37, 0), (1.37, 23.77)),        # left singles sideline
    ((9.6, 0), (9.6, 23.77)),          # right singles sideline
    ((10.97, 0), (10.97, 23.77)),      # right doubles sideline
]


def _norm_form(pa, pb):
    """Image line through 2 points -> canonical (theta_normal, rho)."""
    n = np.arctan2(pb[1]-pa[1], pb[0]-pa[0]) + np.pi/2.0
    rho = pa[0]*np.cos(n) + pa[1]*np.sin(n)
    if rho < 0:
        n, rho = n + np.pi, -rho
    return float(np.mod(n, np.pi)), float(rho)


def _structure(H, lines, calibration, dt, w, h, tol):
    """Do the court's structural lines each claim their OWN distinct real line?

    EVIDENCE-BASED (see _ori_detail): a structural line with no paint anywhere near
    it is UNMEASURABLE and is skipped — a worn clay line is missing evidence, not a
    wrong fit. Only lines that HAVE paint are judged, and each must match a distinct
    real line (greedy) — a shifted court that piles its baseline onto the real
    service line loses, because two of its lines fight over one real line.

    Returns (agreement, n_matched, n_measurable, n_across, n_lengthwise). The last
    two give the SUFFICIENCY test: 4 lines with >=2 in each direction is the
    geometric minimum that determines a homography."""
    if not lines:
        return 0.0, 0, 0, 0, 0
    used, matched, measurable = set(), 0, 0
    n_across = n_len = 0
    ang_tol, rho_tol = np.deg2rad(7), max(8.0, w * 0.018)
    ts = np.linspace(0.0, 1.0, 30)[:, None]
    for i, (a, b) in enumerate(STRUCT_LINES):
        pa = calibration.court_to_image(H, [a])[0]
        pb = calibration.court_to_image(H, [b])[0]
        mid = (pa + pb) / 2.0
        if not (-w*0.1 <= mid[0] <= w*1.1 and -h*0.1 <= mid[1] <= h*1.1):
            continue                      # not really in frame -> can't be judged
        pts = pa + ts * (pb - pa)         # the projected line is straight
        xs = np.round(pts[:, 0]).astype(int)
        ys = np.round(pts[:, 1]).astype(int)
        ok = (xs >= 0) & (xs < w) & (ys >= 0) & (ys < h)
        if ok.sum() < 5:
            continue
        painted = (dt[np.clip(ys, 0, h-1), np.clip(xs, 0, w-1)][ok]
                   <= tol * EVID_BAND).mean()
        if painted < EVID_MIN:
            continue                      # no paint here at all -> unmeasurable
        measurable += 1
        n, rho = _norm_form(pa, pb)
        best, bestd = None, 1e9
        for j, (ln, lr, _lw) in enumerate(lines):
            if j in used:
                continue
            dth = abs(np.mod(n - ln + np.pi/2, np.pi) - np.pi/2)
            drho = abs(rho - lr)
            if dth <= ang_tol and drho <= rho_tol and drho < bestd:
                best, bestd = j, drho
        if best is not None:
            used.add(best)
            matched += 1
            if i < 4:
                n_across += 1
            else:
                n_len += 1
    return ((matched / measurable if measurable else 0.0),
            matched, measurable, n_across, n_len)


# --- Camera-angle prior (tools/build_pose_prior.py) -------------------------
_PRIOR_PATH = REPO / "data" / "court_pose_prior.json"
_PRIOR = None
PRIOR_TEMP = 6.0        # softens the plausibility weight used for ranking
PRIOR_MAHA_MAX = 55.0   # reject camera poses this far outside the learned spread
PRIOR_SAMPLES = 500     # Monte-Carlo court seeds drawn from the learned prior
STRUCT_MIN = 0.55       # min fraction of court lines that must match their OWN real line


def _load_prior():
    global _PRIOR
    if _PRIOR is None:
        if _PRIOR_PATH.exists():
            d = json.loads(_PRIOR_PATH.read_text())
            mu, cov = np.asarray(d["mean"]), np.asarray(d["cov"])
            _PRIOR = (mu, np.linalg.inv(cov), cov)   # mean, inverse-cov, cov
        else:
            _PRIOR = False
    return _PRIOR


def _maha(params, w, h, prior):
    """Mahalanobis distance of a candidate camera pose (params=(cx,yn,yf,wn,wf) in
    PIXELS) from the learned prior. 0 when no prior -> no effect."""
    if not prior:
        return 0.0
    cx, yn, yf, wn, wf = params
    p = np.array([cx/w, yn/h, yf/h, wn/w, wf/w]) - prior[0]
    return float(p @ prior[1] @ p)


def _params_from_corners(c):
    nbl, nbr, fbr, fbl = (np.asarray(c[k], float) for k in DBL)
    return ((nbl[0]+nbr[0]+fbr[0]+fbl[0])/4.0, (nbl[1]+nbr[1])/2.0,
            (fbl[1]+fbr[1])/2.0, (nbr[0]-nbl[0])/2.0, (fbr[0]-fbl[0])/2.0)


def _score_seed(params, calibration, court, court_pts, dt, cos2, sin2,
                w, h, tol, athr, prior):
    """Score one trapezoid seed. Returns (rank, support, nlines, params, maha)
    or None; rank = line-support x plausibility weight (a plausible camera pose
    wins ties over an equally-well-fitting but implausible wrong-rung court)."""
    cx, yn, yf, wn, wf = params
    try:
        H = calibration.compute_homography(
            court_pts, [_corners(cx, yn, yf, wn, wf)[n] for n in DBL])
    except Exception:
        return None
    g, nl, _ = _ori_detail(H, calibration, court, dt, cos2, sin2, w, h, tol, athr)
    if g <= 0:
        return None
    m = _maha(params, w, h, prior)
    return (g * np.exp(-0.5 * m / PRIOR_TEMP), g, nl, params, m)


def _scan(axes, calibration, court, court_pts, dt, cos2, sin2, w, h, tol, athr, prior):
    """Score every trapezoid in the axes grid; ranked best-first."""
    out = []
    for cx in axes[0]:
        for yn in axes[1]:
            for yf in axes[2]:
                if yf >= yn - 20:
                    continue
                for wn in axes[3]:
                    for wf in axes[4]:
                        if wf >= wn:
                            continue
                        s = _score_seed((cx, yn, yf, wn, wf), calibration, court,
                                        court_pts, dt, cos2, sin2, w, h, tol,
                                        athr, prior)
                        if s is not None:
                            out.append(s)
    out.sort(key=lambda t: t[0], reverse=True)
    return out


def _prior_seeds(prior, calibration, court, court_pts, dt, cos2, sin2, w, h, tol, athr):
    """Monte-Carlo court seeds drawn straight from the learned camera-angle prior,
    so most seeds already sit on a plausible court -> far higher lock rate on the
    typical amateur framings than a blind grid, and each is already plausible."""
    rng = np.random.default_rng(0)
    out = []
    for s in rng.multivariate_normal(prior[0], prior[2], PRIOR_SAMPLES):
        cx, yn, yf = s[0]*w, s[1]*h, s[2]*h
        wn, wf = s[3]*w, s[4]*w
        if yf >= yn - 20 or wf >= wn or wn <= 0:
            continue
        sc = _score_seed((cx, yn, yf, wn, wf), calibration, court, court_pts,
                         dt, cos2, sin2, w, h, tol, athr, prior)
        if sc is not None:
            out.append(sc)
    return out


def _lowcam_seeds(calibration, court, court_pts, dt, cos2, sin2, w, h, tol, athr):
    """SYNTHETIC court-level seed mode — computed, not learned.

    The learned prior only knows elevated framings (what people upload), so a
    chest-height camera looks 'implausible' and never gets seeded. But a camera is
    just position+height+lens: project the court through phone-like poses at
    1.0-2.6m height, 1-7m behind the baseline, and we get exactly the trapezoids a
    court-level recording produces. Pure geometry — no training data needed."""
    import itertools
    out = []
    L, Wd = 23.77, 10.97
    for cam_h, back, f_px in itertools.product(
            (1.0, 1.6, 2.6), (1.0, 3.0, 7.0), (w*0.7, w*1.1)):
        # camera on the court's centreline, `back` metres behind the near baseline,
        # looking at the far half. Court frame: X across [0,10.97], Y depth.
        cx3, cy3 = Wd/2.0, -back
        look_y = L*0.45
        fwd = np.array([0.0, look_y-cy3, -cam_h]); fwd /= np.linalg.norm(fwd)
        right = np.array([1.0, 0.0, 0.0])
        up = np.cross(fwd, right); up /= np.linalg.norm(up)
        def proj(X, Y):
            p = np.array([X-cx3, Y-cy3, 0.0-cam_h])
            z = p @ fwd
            if z <= 0.1:
                return None
            return (w/2.0 + f_px*(p@right)/z, h/2.0 - f_px*(p@up)/z)
        cs = [proj(*court.LANDMARKS[n]) for n in DBL]
        if any(c is None for c in cs):
            continue
        corners = dict(zip(DBL, [[c[0], c[1]] for c in cs]))
        # keep only poses where a useful part of the court is actually in frame
        xs = [c[0] for c in cs]; ys = [c[1] for c in cs]
        if max(ys) < h*0.5 or min(ys) > h*1.6 or max(xs)-min(xs) < w*0.5:
            continue
        try:
            H = calibration.compute_homography(court_pts, [corners[n] for n in DBL])
        except Exception:
            continue
        g, nl, _ = _ori_detail(H, calibration, court, dt, cos2, sin2, w, h, tol, athr)
        if g > 0:
            p = _params_from_corners(corners)
            out.append((g, g, nl, p, 0.0))    # rank by support; maha not applicable
    return out


_ROLL_MAX = math.radians(3.0)   # small mounting tilt is physics; more is noise-chasing


def _cam_corners(p, w, h, court):
    """Project the 4 doubles corners through a PHYSICAL camera: position (Cx,Cy,Cz)
    in court metres, yaw, pitch, focal f_px, and an optional 7th param ROLL.

    Roll is bounded to +-3 deg: phones are mounted ROUGHLY level, but not
    exactly - a fence-mounted clip measured -1.1 deg, which the old roll=0
    model could only express as an 8px corner misfit (seen as the near-left
    sideline offset on e2e_l6o8FOoy3MY; adding roll cut the on-paint residual
    there from ~8px to ~2-3px). Beyond a few degrees, roll would hand a
    court-shaped hallucination an extra DOF to chase noise, so it stays out.
    Returns {corner:[u,v]} or None if any corner is behind the camera."""
    Cx, Cy, Cz, yaw, pitch, f = (float(v) for v in p[:6])
    roll = float(p[6]) if len(p) > 6 else 0.0
    if abs(roll) > _ROLL_MAX:
        return None
    sy, cy_ = math.sin(yaw), math.cos(yaw)
    st, ct = math.sin(pitch), math.cos(pitch)
    fwd = np.array([sy*ct, cy_*ct, -st])
    right = np.array([cy_, -sy, 0.0])
    up = np.array([sy*st, cy_*st, ct])
    if roll:
        cr, sr = math.cos(roll), math.sin(roll)
        right, up = cr * right + sr * up, -sr * right + cr * up
    out = {}
    for n in DBL:
        X, Y = court.LANDMARKS[n]
        d = np.array([X-Cx, Y-Cy, -Cz])
        zc = d @ fwd
        if zc < 0.5:
            return None
        out[n] = [w/2.0 + f*(d@right)/zc, h/2.0 - f*(d@up)/zc]
    return out


def _cam_refine(frame, quad, calibration, court, dt, w, h):
    """Re-fit the snapped quad as a PHYSICAL CAMERA VIEW of a regulation court.

    The corner snap moves 4 corners independently (8 DOF) — it keeps the template
    rigid in court space but allows warps no real camera produces (skewed quads,
    tilted baselines), which is exactly the 'shape distortion' seen on weak-evidence
    courts. A real camera has ~6 DOF (position, pan, tilt, zoom; roll frozen at 0
    on this candidate path — see the NOTE below). Stage 1
    fits camera params to the quad; stage 2 polishes them on the line-distance map.
    Every candidate shape is then a legal view of a regulation court by
    construction. Returns (H, corners) or None."""
    from scipy.optimize import minimize
    target = np.array([quad[n] for n in DBL])
    f0 = None
    try:
        Hq = calibration.compute_homography([court.LANDMARKS[n] for n in DBL], target)
        f0 = calibration.focal_from_homography(Hq, (w, h))
    except Exception:
        pass
    # NOTE: roll stays FROZEN at 0 on this (auto-detect) path: measured on the
    # gold set, giving candidate courts the roll DOF makes wrong-rung fits
    # reproduce across frames (am_indoor_hard2's 68px court rose from 4 to 6
    # consensus votes - past the auto-accept bar). Roll is for TRUSTED quads
    # only (shape_lock / the calibrate path).
    x0 = np.array([court.DOUBLES_WIDTH/2.0, -6.0, 4.0, 0.0, 0.25,
                   float(f0) if f0 else w*0.9])

    r1 = minimize(_cam_cost_quad(target, w, h, court), x0, method="Nelder-Mead",
                  options={"maxiter": 1200, "xatol": 1e-3, "fatol": 1e-3})
    if not np.isfinite(r1.fun) or r1.fun > 40.0:
        return None                       # quad too non-physical to be a camera view
    use_x = _tethered_dt_polish(r1.x, dt, w, h, calibration, court)
    return _cam_result(use_x, w, h, calibration, court)


def _cam_cost_quad(target, w, h, court):
    """Cost: mean px distance from camera p's corner projection to `target`."""
    def cost(p):
        c = _cam_corners(p, w, h, court)
        if c is None:
            return 1e6
        return float(np.mean(np.hypot(*(np.array([c[n] for n in DBL]) - target).T)))
    return cost


def _tethered_dt_polish(px, dt, w, h, calibration, court):
    """Stage-2 polish of camera params onto the paint (line-distance map),
    TETHERED: dt sinks far from the court (banner/fence rows) can drag the
    polish into a collapsed sliver, so a 'polish' that moves the corners >30px
    mean is discarded. Returns the polished params, or `px` unchanged."""
    from scipy.optimize import minimize
    S = _court_samples(court)[0]

    def cost_dt(p):
        c = _cam_corners(p, w, h, court)
        if c is None:
            return 1e6
        try:
            H = calibration.compute_homography(
                [court.LANDMARKS[n] for n in DBL], [c[n] for n in DBL])
        except Exception:
            return 1e6
        P = calibration.court_to_image(H, S)
        xs = np.clip(P[:, 0], 0, w-1).astype(int)
        ys = np.clip(P[:, 1], 0, h-1).astype(int)
        inb = (P[:, 0] >= 0) & (P[:, 0] < w) & (P[:, 1] >= 0) & (P[:, 1] < h)
        if inb.sum() < len(P)*0.3:
            return 1e6
        return float(dt[ys[inb], xs[inb]].mean())

    c0 = cost_dt(px)
    r2 = minimize(cost_dt, px, method="Nelder-Mead",
                  options={"maxiter": 600, "xatol": 1e-3, "fatol": 1e-3})
    if np.isfinite(r2.fun) and r2.fun < c0:
        c1 = _cam_corners(px, w, h, court)
        c2 = _cam_corners(r2.x, w, h, court)
        if c1 is not None and c2 is not None and float(np.mean(
                [math.hypot(c2[n][0]-c1[n][0], c2[n][1]-c1[n][1])
                 for n in DBL])) <= 30.0:
            return r2.x
    return px


def _cam_result(px, w, h, calibration, court):
    """(H, corners) for camera params px, or None on a degenerate projection."""
    c = _cam_corners(px, w, h, court)
    if c is None:
        return None
    try:
        H = calibration.compute_homography(
            [court.LANDMARKS[n] for n in DBL], [c[n] for n in DBL])
    except Exception:
        return None
    return H, {n: [float(c[n][0]), float(c[n][1])] for n in DBL}


def _seed_from_quad(target, court):
    """Closed-form camera guess from the quad's own geometry (assumes a roughly
    centre-line camera behind the near baseline). Distance from the near/far
    width ratio, focal from the pinhole relation, height from the vertical
    extent — good enough to seed Nelder-Mead for ANYTHING from a phone at the
    fence to a broadcast telephoto (measured: a ~4400px-focal TV view that all
    fixed seeds missed by 88px fits <2px from this seed)."""
    nbl, nbr, fbr, fbl = target
    wn = float(np.hypot(*(nbr - nbl)))
    wf = float(np.hypot(*(fbr - fbl)))
    if wf <= 1.0 or wn <= wf:
        return None
    Wd = court.DOUBLES_WIDTH
    L = float(court.LANDMARKS["far_bl_doubles"][1])
    r = wf / wn
    Dn = r * L / (1.0 - r)                    # camera -> near baseline (ground)
    if not (1.0 <= Dn <= 200.0):
        return None
    f = wn * Dn / Wd
    dy = max((nbl[1] + nbr[1]) / 2.0 - (fbl[1] + fbr[1]) / 2.0, 1.0)
    Cz = dy / (f * (1.0 / Dn - 1.0 / (Dn + L)))
    Cz = float(np.clip(Cz, 0.5, 60.0))
    pitch = math.atan2(Cz, Dn + L / 2.0)
    return np.array([Wd / 2.0, -Dn, Cz, 0.0, pitch, f])


def cam_fit_quad(quad, calibration, court, w, h, dt=None, allow_roll=False):
    """Lock an ARBITRARY 4-corner court placement onto the closest physical
    camera view of a regulation court (position, pan, tilt, zoom; plus, when
    allow_roll is set, roll within the +-3 deg mounting-tilt bound - see
    _cam_corners). allow_roll is for TRUSTED quads only (a snapped/manual
    court): on candidate quads the extra DOF lets wrong courts look physical
    (measured: a 68px wrong consensus court gained 2 votes), so the
    auto-detect path keeps roll frozen at 0.

    Manual-path counterpart of _cam_refine: the overlay tool lets a human drag
    corners freely (8 DOF), which can produce shapes no real camera ever sees.
    This projects that quad onto the 6-DOF camera manifold, so the result is
    ALWAYS a legal view of a regulation court, as close as possible to where the
    user put it. Unlike _cam_refine it never refuses a fittable quad (a hand
    placement must resolve to the nearest legal shape, not be rejected), and it
    multi-starts because hand placements can be far from the elevated-TV pose
    _cam_refine's single seed assumes. Both share the same cost/polish helpers
    (_cam_cost_quad, _tethered_dt_polish, _cam_result); _cam_refine keeps its
    own >40px REFUSE gate, which is measurement-frozen (scorecards in git).

    dt: optional line-distance map; when given, a second stage polishes the
    camera onto the paint (use for Snap, omit for a pure shape lock on Save).

    Returns (H, corners, fit_px, cam_params) or None. fit_px = mean px between
    the input quad and the nearest physical view: ~0 when the input was already
    a real camera shape, large when it was impossible and got corrected.
    cam_params = (Cx, Cy, Cz, yaw, pitch, focal_px, roll) - the actual camera;
    the focal is the honest lens zoom (feeds speed physics downstream)."""
    from scipy.optimize import minimize
    target = np.array([quad[n] for n in DBL], float)

    f0 = None
    try:
        Hq = calibration.compute_homography([court.LANDMARKS[n] for n in DBL], target)
        f0 = calibration.focal_from_homography(Hq, (w, h))
    except Exception:
        pass
    f_guess = float(f0) if f0 else w * 0.9
    Wd = court.DOUBLES_WIDTH
    starts = [
        np.array([Wd/2.0, -6.0, 4.0, 0.0, 0.25, f_guess]),   # elevated behind baseline
        np.array([Wd/2.0, -3.0, 1.6, 0.0, 0.10, f_guess]),   # court-level phone
        np.array([Wd/2.0, -12.0, 8.0, 0.0, 0.35, f_guess]),  # high stands
        np.array([Wd/2.0, -6.0, 4.0, 0.0, 0.25, w*1.4]),     # long lens
    ]
    seed = _seed_from_quad(target, court)
    if seed is not None:
        starts.insert(0, seed)   # data-driven guess first (covers broadcast poses)
    if allow_roll:
        starts = [np.append(x0, 0.0) for x0 in starts]
    cost_quad = _cam_cost_quad(target, w, h, court)

    best = None
    for x0 in starts:
        r = minimize(cost_quad, x0, method="Nelder-Mead",
                     options={"maxiter": 1400, "xatol": 1e-3, "fatol": 1e-3})
        if np.isfinite(r.fun) and r.fun < 1e5 and (best is None or r.fun < best.fun):
            best = r
    if best is None:
        return None
    # restart from the winner until improvement stalls: Nelder-Mead's simplex
    # collapses prematurely (worse in 7-D with roll); fresh simplexes finish
    # the job cheaply (the 8px->0px refit guarantee in test_cam_lock needs it)
    for _ in range(6):
        r = minimize(cost_quad, best.x, method="Nelder-Mead",
                     options={"maxiter": 1400, "xatol": 1e-3, "fatol": 1e-3})
        if not (np.isfinite(r.fun) and r.fun < best.fun - 1e-3):
            break
        best = r
    fit_px, px = float(best.fun), best.x

    if dt is not None:
        px = _tethered_dt_polish(px, dt, w, h, calibration, court)

    res = _cam_result(px, w, h, calibration, court)
    if res is None:
        return None
    return (*res, fit_px, tuple(float(v) for v in px))


def autodetect(frame, calibration, court, *, topk=12,
               athr=0.80, accept=0.33, use_prior=True, mask_fn=None, _fallback=True):
    """Prior-sampled + grid seeds -> local refine -> snap -> structural+plausibility
    gate. Returns (H, score, corners) or None (falls back to manual).

    If the default "white lines" mask yields nothing acceptable, retries ONCE with a
    hue-agnostic mask (clay/shell). Only safe because the verifier is STRUCTURAL: a
    court must claim 4 distinct real lines at regulation spacing with a plausible
    camera pose, so the extra noise a permissive mask lets in is rejected on
    geometry, not on colour."""
    mf = mask_fn or calibration.court_line_mask
    dt, cos2, sin2, w, h, lines = _precompute(frame, calibration, mf)
    tol = max(2.0, w * 0.006)
    court_pts = [court.LANDMARKS[n] for n in DBL]
    prior = _load_prior() if use_prior else False

    coarse = COARSE_GRID
    ax = tuple(np.asarray(v) * (w if i in (0, 3, 4) else h) for i, v in enumerate(coarse))
    ranked = _scan(ax, calibration, court, court_pts, dt, cos2, sin2, w, h, tol, athr, prior)
    if prior:
        ranked += _prior_seeds(prior, calibration, court, court_pts,
                               dt, cos2, sin2, w, h, tol, athr)
    ranked += _lowcam_seeds(calibration, court, court_pts,
                            dt, cos2, sin2, w, h, tol, athr)
    ranked.sort(key=lambda t: t[0], reverse=True)

    # coarse-to-fine: local grid around the top-3 (plausibility-ranked) coarse seeds
    steps = [(coarse[i][1]-coarse[i][0]) * (w if i in (0, 3, 4) else h) for i in range(5)]
    seeds = []
    for t in ranked[:3]:
        p = t[3]
        local = tuple(np.array([p[i]-steps[i]/2, p[i], p[i]+steps[i]/2]) for i in range(5))
        seeds += _scan(local, calibration, court, court_pts, dt, cos2, sin2, w, h, tol, athr, prior)
    seeds += ranked
    seeds.sort(key=lambda t: t[0], reverse=True)

    best = None
    tried = 0
    for _rank, _g, _nl, p, _m in seeds:
        if tried >= topk:
            break
        tried += 1
        try:
            # 55 px was tuned on the 640-wide gold clips and was ABSOLUTE, so the
            # refiner's reach shrank as resolution grew: 55 px@640-equivalent on the
            # gold set, 18.3 on a 1920 reference, 9.2 on 4K. Measured (Session P,
            # data/output/seed_reach.log): on 7 of 38 human-labelled clips the seed
            # nearest the true court sat FARTHER away than the refiner could travel,
            # and all 7 come back into range once the bound scales. Same defect the
            # ball stack hit at 1080p and the same fix - scale it, and keep it an
            # EXACT no-op at the resolution it was tuned at.
            # (w == 640 -> 55.0 exactly; pinned by tests/test_refine_reach_scaling.py)
            Hs, ref, _ = calibration.refine_homography_bounded(
                frame, _corners(*p), max_move_px=55.0 * (w / 640.0), mask_fn=mf)
        except Exception:
            continue
        # DEGENERACY FLOOR (the "not even remotely a court" rule applied to
        # SCALE): near a frame's horizon, banner/fence edges can satisfy the
        # structural gates because every court line collapses into the same
        # horizontal band (seen live: a 70x3px "court" on the fence banners).
        # A usable recording shows the court at size - floor the apparent
        # near-baseline width and depth.
        p5 = _params_from_corners(ref)
        if p5[3] * 2.0 < 0.15 * w or abs(p5[1] - p5[2]) < 0.06 * h:
            continue
        g, nl, n_ev = _ori_detail(Hs, calibration, court, dt, cos2, sin2, w, h, tol, athr)
        maha = _maha(p5, w, h, prior)
        st, st_m, st_ev, n_across, n_len = _structure(Hs, lines, calibration, dt, w, h, tol)
        # Accept gate, evidence-based. We never punish a line for having no paint —
        # a regulation court's lines exist whether or not the surface still shows
        # them. We require instead:
        #   SUFFICIENCY  enough VISIBLE lines to actually determine the shape:
        #                4 matched with >=2 in each direction (the geometric minimum
        #                for a homography). This replaces "found most of my lines".
        #   AGREEMENT    where paint IS visible, it agrees (g, st)
        #   PLAUSIBILITY a sane camera pose (prior) + coverage/centrality check
        sufficient = (st_m >= 4 and n_across >= 2 and n_len >= 2) or nl >= 5
        if mask_fn is not None:
            # STRUCTURE-PRIMARY clay path (user's principle: once lines are matched
            # as court lines, regulation spacing determines everything). On clay the
            # per-pixel agreement g and the white-mask verify_court are BLIND — but
            # the true court still claims 6+ distinct straight lines at regulation
            # spacing, which speckle can't fake. Judged by structure + pose only, so
            # the bar is HIGHER than the white path (measured: the true clay court
            # matches 6 lines at 0.86 agreement; hallucinations on no-court frames
            # scrape 4 — requiring 5+ at 0.70 separates them).
            rankv = st
            ok = (sufficient and st_m >= 5 and st >= 0.70
                  and n_across >= 2 and n_len >= 2
                  and maha <= PRIOR_MAHA_MAX
                  and court_centrality_ok(frame, Hs, calibration))
        else:
            ok_struct = st >= STRUCT_MIN or st_ev < 3   # can't judge with <3 measurable
            rankv = g * (0.5 + 0.5 * st)
            # The learned prior only knows elevated framings. A COURT-LEVEL camera
            # fails the maha test through no fault of its own, so a pose outside
            # the prior is allowed IF the court structure is unambiguous (5+ lines
            # each on their own real line, both directions) — prior breaks ties,
            # overwhelming structure overrides it.
            pose_ok = (maha <= PRIOR_MAHA_MAX
                       or (st >= 0.70 and st_m >= 5 and n_across >= 2 and n_len >= 2))
            ok = (g >= accept and sufficient and pose_ok and ok_struct
                  and calibration.verify_court(frame, Hs).ok)
        if ok and (best is None or rankv > best[1]):
            best = (Hs, rankv, ref)
    if best is not None:
        # HARD RULE: the output must be a real camera's view of a regulation court.
        # Re-fit the winner as camera pose+zoom (roll~0); if NO physical camera can
        # produce this quad (stage-1 residual > 40px), REFUSE rather than ship a
        # shape that isn't remotely a tennis court. No free-quad fallback.
        cam = _cam_refine(frame, best[2], calibration, court, dt, w, h)
        best = (cam[0], best[1], cam[1]) if cam is not None else None
    if best is None and _fallback and mask_fn is None:
        # nothing with the "white lines" mask -> the surface may be clay/shell.
        # Retry hue-agnostic; the structure verifier keeps this honest.
        return autodetect(frame, calibration, court, topk=topk, athr=athr,
                          accept=accept, use_prior=use_prior,
                          mask_fn=lambda f: _clay_mask(f, calibration), _fallback=False)
    return best


# The coarse seed grid: (cx, y_near, y_far, half_width_near, half_width_far) as
# fractions of frame width (cx/wn/wf) or height (yn/yf). Hoisted out of autodetect
# so a change to it can be measured rather than argued about.
COARSE_GRID = ([0.40, 0.47, 0.53, 0.60], [0.74, 0.85, 0.95, 1.06],
               [0.18, 0.28, 0.38, 0.48], [0.40, 0.51, 0.61, 0.72],
               [0.20, 0.27, 0.35, 0.42])

AGREE_PX = 30.0     # two courts "agree" when their corners sit within this
MIN_VOTES = 2       # need at least this many frames agreeing to trust a court


def _corner_dist(a, b):
    return float(np.mean([np.hypot(a[n][0]-b[n][0], a[n][1]-b[n][1]) for n in DBL]))


def consensus(fits):
    """fits: list of {corner:[x,y]} (or None). Returns (court, votes) or (None, 0)."""
    valid = [f for f in fits if f]
    if not valid:
        return None, 0
    best, best_n = None, 0
    for f in valid:
        group = [g for g in valid if _corner_dist(f, g) <= AGREE_PX]
        if len(group) > best_n:
            best, best_n = group, len(group)
    if best_n < MIN_VOTES:
        return None, best_n
    return {n: [float(np.median([g[n][0] for g in best])),
                float(np.median([g[n][1] for g in best]))] for n in DBL}, best_n


def stacked_clay_fit(imgs, calibration, court):
    """Clay/shell rescue: STACK line evidence across frames, then fit ONCE.

    Per-frame clay fits wobble because each frame's Hough pass recovers a different
    subset of the broken orange lines. But the court is static and its lines are
    straight, so accumulating the cleaned masks across frames makes the true lines
    reinforce while players/shadows/per-frame noise wash out. Fit on a synthetic
    frame whose 'paint' is the pixels seen as line in >=30% of frames."""
    import cv2

    acc = None
    for _k, im in imgs:
        m = (_clay_mask(im, calibration) > 0).astype(np.float32)
        acc = m if acc is None else acc + m
    if acc is None:
        return None
    stable = ((acc / len(imgs)) >= 0.30).astype(np.uint8) * 255
    if int(stable.sum() // 255) < 200:
        return None
    synth = np.zeros((*stable.shape, 3), np.uint8)
    synth[stable > 0] = 255                       # white paint on black
    res = autodetect(synth, calibration, court,
                        mask_fn=lambda f: cv2.cvtColor(f, cv2.COLOR_BGR2GRAY),
                        _fallback=False)
    return None if res is None else res[2]


def line_distance_map(frame, calibration, mask_fn=None):
    """Distance-to-nearest-line-pixel map (the dt the polish stages sample).
    Cheaper than _precompute when the caller needs ONLY the dt — no Sobel,
    orientation maps, or Hough pass."""
    import cv2
    mask = (mask_fn or calibration.court_line_mask)(frame)
    return cv2.distanceTransform(255 - mask, cv2.DIST_L2, 5)


def lock_quad(named, calibration, court, w, h, dt=None, allow_roll=False):
    """cam_fit_quad plus 'how far did it move' — the one place that computes the
    lock displacement (the tool, the pipeline, and auto_fit_frame all report it).
    Returns (locked_corners, moved_max_px, fit) where fit is cam_fit_quad's full
    result; on a total fit failure returns (named, 0.0, None) unchanged."""
    r = cam_fit_quad(named, calibration, court, w, h, dt=dt, allow_roll=allow_roll)
    if r is None:
        return named, 0.0, None
    moved = max(math.hypot(r[1][n][0] - named[n][0],
                           r[1][n][1] - named[n][1]) for n in DBL)
    return r[1], moved, r


def shape_lock(H, calibration, court, w, h, *, gate_px=40.0):
    """The HARD SHAPE RULE, as one operation on a homography: project H's
    doubles corners, fit the closest physical camera, and APPLY it only when a
    real camera reproduces the shape within gate_px (else the caller keeps its
    input and warns — an optimizer miss must never 'correct' a good court).

    Returns a dict: applied, H, corners, moved_max, hfov_deg (the fitted lens
    when applied), gap_px (fit distance when NOT applied, for the warning).

    This is the TRUSTED-quad lock (the calibrate/manual path), so the camera
    fit may use its bounded roll DOF (allow_roll) — a fence-mounted phone is
    only roughly level, and forcing roll=0 here displaced a whole court by
    ~8px on-paint (e2e_l6o8FOoy3MY, roll -1.1 deg)."""
    quad = {n: [float(v) for v in calibration.court_to_image(
        H, [court.LANDMARKS[n]])[0]] for n in DBL}
    corners, moved, fit = lock_quad(quad, calibration, court, w, h,
                                    allow_roll=True)
    if fit is None or fit[2] > gate_px:
        return {"applied": False, "H": H, "corners": quad, "moved_max": 0.0,
                "hfov_deg": None, "gap_px": (fit[2] if fit else None)}
    return {"applied": True, "H": fit[0], "corners": corners, "moved_max": moved,
            "hfov_deg": calibration.hfov_from_focal(fit[3][5], w), "gap_px": None}


class CourtWatchdog:
    """Detects that the CAMERA CHANGED after calibration and drives re-acquisition.

    The per-frame lock step absorbs small drift, but a real change — the phone
    gets bumped, re-mounted, or zoomed — moves the lines out of its tiny search
    basin and the court silently stays wrong. This watchdog measures how much of
    the projected court still lands on real line pixels (coverage) and compares
    it against its OWN rolling baseline, so a worn clay court with low absolute
    coverage still alarms on a RELATIVE collapse. Two consecutive bad checks
    (not one — a player standing on a line dips coverage for a moment) raise
    "changed"; the caller then re-runs full detection and, on a gated lock,
    rebases the motion track. After a rebase (or a failed re-acquisition) call
    rebase() to start a fresh baseline instead of alarming forever.

    States from check(): "warmup" (building the baseline), "ok", "watch"
    (one bad check), "changed" (confirmed - re-acquire now).
    """

    def __init__(self, calibration, court, *, drop=0.45, floor=0.05,
                 confirm=2, warmup=5):
        self._calibration = calibration
        self._court = court
        self.drop, self.floor, self.confirm, self.warmup = drop, floor, confirm, warmup
        self._covs: list[float] = []
        self.baseline: float | None = None
        self._bad = 0

    def rebase(self):
        self._covs, self.baseline, self._bad = [], None, 0

    def check(self, frame, H_t, mask=None) -> str:
        cov = self._calibration.court_line_coverage(frame, H_t, mask=mask)[0]
        if self.baseline is None:
            self._covs.append(cov)
            if len(self._covs) >= self.warmup:
                self.baseline = float(np.median(self._covs))
            return "warmup"
        if cov >= max(self.drop * self.baseline, self.floor):
            self._bad = 0
            # slow tracking of gradual, benign change (light, shadows)
            self.baseline = 0.9 * self.baseline + 0.1 * cov
            return "ok"
        self._bad += 1
        return "changed" if self._bad >= self.confirm else "watch"


def snap_court(frame, named, calibration, court, *,
               min_coverage=0.40, max_move_px=30.0, resolvability_weight=False):
    """Guarded corner snap with a CLAY retry.

    White/ridge lines first (the measured default). When that path REFUSES —
    worn or colour-tinted paint has no white signal, exactly the case where a
    stack-fit court sits ~15px off its faintest sideline — retry with the
    hue-agnostic clay mask, judged under the SAME mask it refined with (the
    guard still demands coverage >= min_coverage and no decrease). The snap
    stays bounded (+-max_move_px), so the worst it can do is tighten onto
    nearby clay texture; callers re-lock the shape afterwards regardless.

    `resolvability_weight` (OFF by default) weights the fit by measurement
    precision so the well-resolved near/mid court drives it — used by the
    interactive Court Setup tool, not the automatic pipeline (see
    calibration.refine_homography_bounded).

    Returns (H, named_out, snapped, tag, coverage) — tag "snap", "snap-clay",
    or None when both paths refused (named_out is then the input)."""
    H, out, snapped, _c0, c1 = calibration.snap_to_lines(
        frame, named, min_coverage=min_coverage, max_move_px=max_move_px,
        resolvability_weight=resolvability_weight)
    if snapped:
        return H, out, True, "snap", c1
    H2, out2, snapped2, _c0, c2 = calibration.snap_to_lines(
        frame, named, min_coverage=min_coverage, max_move_px=max_move_px,
        mask_fn=lambda f: _clay_mask(f, calibration),
        resolvability_weight=resolvability_weight)
    if snapped2:
        return H2, out2, True, "snap-clay", c2
    return H, named, False, None, c1


# --- Setup guidance (the SwingVision-style framing check) -------------------
# Two questions a user can actually act on, kept separate because the fixes are
# different: "can I SEE the court properly?" (framing - move/aim/zoom) and "is my
# ANGLE good enough?" (height - remount higher). Both are measured, never guessed.
CAM_H_LOW, CAM_H_GOOD = 2.0, 2.5      # metres above the court plane
CAM_H_MAX = 15.0                       # above this the fit is not a real amateur mount

# REALISTIC SETUPS ONLY. A phone tripod stands ~1.5 m; a fence clamp reaches
# ~2.5-3 m. Nobody mounts at 5 m, so advice above CAM_H_REACHABLE is useless and
# we never give it. Measured sweep (lens framed to fit the court, reliable span):
#   1.5 m tripod, 6 m back : 720p 17% | 1080p 27% | 1440p 35% | 4K 48%
#   2.5 m fence,  6 m back, 4K : 71%   (10 m back: 80%, reaching 19 m)
#   STUCK 2 m from the fence, 1.5 m high (needs the 0.5x ultrawide to fit):
#     720p 17% | 1080p 22% | 4K 35%   -- and 4K-ultrawide-up-close (35%, 8.3 m)
#     BEATS 1080p-normal-stepped-back (27%, 6.3 m).
# So RESOLUTION is the dominant free lever: it more than pays for a wide lens.
# Zooming out to fit the court is fine - a phone user can always do that, and an
# off-frame corner (extrapolated) is worse than a wider view. Stepping back is a
# bonus when there is room, and has an optimum (~4-6 m at 1.5 m; further is worse).
CAM_H_REACHABLE = 2.6      # a fence clamp; do not advise above this
BACK_ROOMY_M = 3.0         # beyond this, stepping back is no longer the easy win
RES_MIN_W = 1920           # below 1080p, resolution is the cheapest fix there is


def _setup_tips(Cz, back_m, frame_w):
    """Prioritised, ACHIEVABLE fixes for a setup that can't measure enough court.

    Ordered by payoff-per-effort. Resolution leads because it is free, works from
    wherever you are standing, and measurably beats repositioning (see the sweep
    above) - crucially it also buys back what the 0.5x ultrawide costs, so a user
    penned in behind the baseline is never stuck.
    """
    tips = []
    if frame_w < RES_MIN_W:
        tips.append(f"record at a higher resolution (this is {frame_w}px wide - "
                    "1080p or 4K roughly doubles the measurable court, it's free, "
                    "and it more than pays for zooming out to fit the court in)")
    if Cz < CAM_H_REACHABLE:
        tips.append("clamp the phone to the fence (~2.5 m) instead of a standing "
                    "tripod (~1.5 m)")
    if back_m is not None and back_m < BACK_ROOMY_M:
        tips.append(f"if you have room, stand a few metres further back "
                    f"(~4-6 m behind the baseline, currently ~{back_m:.0f} m); if a "
                    "fence is behind you, just zoom out instead")
    return tips


def setup_verdict(frame, named, calibration, court):
    """Grade a court setup for the user: view + angle, each with plain-English fixes.

    `named` is the current {corner: [x, y]} placement. Returns a JSON-ready dict:
      view  = {level good|warn|poor, corners_visible, centrality, coverage, msg}
      angle = {level, height_m, hfov_deg, roll_deg, reliable_frac, reliable_to_m, msg}
    'reliable_frac' is the share of the court this camera can actually MEASURE
    (calibration.reliable_court_span) - the number that turns "mount it higher"
    from an opinion into a measurement.
    """
    h, w = frame.shape[:2]
    quad = {k: [float(named[k][0]), float(named[k][1])] for k in DBL}
    H = calibration.homography_from_landmarks(quad)

    # --- view: is the court properly in frame? (existing measured grader) ---
    fr = calibration.framing_report(frame, H)
    view_msgs = [m for m in fr.messages if not m.startswith("Framing looks good")]
    view = {"level": fr.level, "corners_visible": int(fr.corners_visible),
            "centrality": round(float(fr.centrality), 2),
            "coverage": round(float(fr.coverage), 2),
            "msg": (view_msgs[0] if view_msgs else
                    "Whole court in frame, centred, lines clear.")}

    # --- angle: how much of the court can this camera actually measure? ---
    fit = cam_fit_quad(quad, calibration, court, w, h, allow_roll=True)
    frac, until = calibration.reliable_court_span(H)
    angle = {"reliable_frac": round(float(frac), 3),
             "reliable_to_m": round(float(until), 1)}

    # The DERIVED setup criterion: is the far baseline clear of the net tape, and
    # by how many pixels? GUIDANCE, NOT A GATE - it is reported alongside the
    # angle numbers and never changes `level`, because it answers "where should I
    # put the phone", not "is this footage acceptable".
    # docs/evidence/live-setup-criterion.md
    clr = calibration.net_tape_clearance(H, (w, h))
    angle["net_clearance_px"] = (None if clr is None
                                 else round(clr.margin_px_720, 1))
    angle["net_clearance_level"] = None if clr is None else clr.level
    angle["net_clearance_msg"] = None if clr is None else clr.message
    if fit is None:
        angle.update(level="poor", height_m=None, hfov_deg=None, roll_deg=None,
                     msg="This shape isn't a real camera's view of a court - "
                         "re-place the corners.")
        return {"view": view, "angle": angle}

    cam = fit[3]
    Cz = abs(float(cam[2]))
    angle.update(height_m=round(Cz, 2),
                 hfov_deg=round(calibration.hfov_from_focal(cam[5], w), 0),
                 roll_deg=round(math.degrees(cam[6] if len(cam) > 6 else 0.0), 1))
    pct = int(round(frac * 100))
    net_y = float(court.NET_Y)

    # Grade on the MEASURED reach, not on height alone. Height is only a proxy:
    # the reliable span also depends on how far back the camera sits, the lens,
    # and the RESOLUTION (720p resolves far less court than 1080p). Never claim
    # the far half is covered unless the span actually passes the net - saying
    # "good, includes the far half" at an 8.8 m reach would be a plain lie.
    if Cz > CAM_H_MAX:
        angle.update(level="poor",
                     msg=f"Implied camera height {Cz:.0f} m isn't a real mount - "
                         "check the corner placement.")
        return {"view": view, "angle": angle}

    reach = (f"reliable to ~{until:.0f} m of {court.LENGTH:.0f} m "
             f"({'past' if until >= net_y else 'short of'} the net at {net_y:.0f} m)")
    # The reliable span is a GEOMETRIC BOUND (metres per pixel), not an error, so
    # on its own it still leaves "mount it higher" half an opinion. This is the
    # measured half: what share of close calls a mount at this height actually
    # gets right, against synthetic flights with a known bounce.
    call_pct = calibration.expected_call_accuracy(Cz)
    floor = calibration.CALL_MAJORITY_FLOOR_PCT
    angle["call_accuracy_pct"] = round(call_pct, 0)
    angle["call_floor_pct"] = round(floor, 0)
    call_note = (f" Close calls: ~{call_pct:.0f}% right at this height"
                 + (" - no better than guessing." if call_pct <= floor + 1.0
                    else "."))
    back_m = abs(float(cam[1])) if cam[1] < 0 else None   # metres behind the baseline
    angle["back_m"] = round(back_m, 1) if back_m is not None else None
    tips = _setup_tips(Cz, back_m, w)
    fix = (" Best fixes: " + "; ".join(tips) + ".") if tips else ""

    if until >= court.LENGTH * 0.85:
        angle.update(level="good",
                     msg=f"Strong setup ({Cz:.1f} m): ~{pct}% of the court is "
                         f"measurable - {reach}.{call_note}")
    elif until >= net_y:
        angle.update(level="good",
                     msg=f"Good setup ({Cz:.1f} m): ~{pct}% measurable, {reach}. "
                         f"Both service boxes are covered.{call_note}")
    elif Cz < CAM_H_LOW:
        angle.update(level="poor",
                     msg=f"Only ~{pct}% of the court is measurable from here "
                         f"({Cz:.1f} m up), {reach}; past that, calls and speeds are "
                         f"marked uncertain.{call_note}{fix}")
    else:
        angle.update(level="warn",
                     msg=f"Usable ({Cz:.1f} m) but only ~{pct}% of the court is "
                         f"measurable, {reach}.{call_note}{fix}")
    return {"view": view, "angle": angle}


def resolved_proposer(proposer=None) -> str:
    """The proposal source that will ACTUALLY run.

    Resolution order: explicit argument > COURT_PROPOSER env > "classical".
    Provenance stamps must call this rather than quoting a preset table - a stamp
    that reads the request instead of the resolution is how a cache outlives its
    settings."""
    p = proposer if proposer is not None else os.environ.get("COURT_PROPOSER") or "classical"
    p = str(p).strip().lower()
    if p not in COURT_PROPOSERS:
        raise ValueError(f"unknown court proposer {p!r}; expected one of {COURT_PROPOSERS}")
    return p


def resolved_courtnet_weights(requested: str | None = None) -> str:
    """The checkpoint `detect_court_learned` will actually load, mirroring ITS
    order: COURTNET_WEIGHTS env > courtnet_ft.pt beside the requested file if it
    exists > the requested file. Asking for court_detector.pt and silently getting
    our fine-tune is exactly the contamination the seam's own comment warns about,
    so the eval must read this, not the argument it passed."""
    req = requested or COURTNET_BASE_WEIGHTS
    env = os.environ.get("COURTNET_WEIGHTS")
    if env:
        return env
    ft = os.path.join(os.path.dirname(req), "courtnet_ft.pt")
    return ft if os.path.exists(ft) else req


def _propose_classical(frame, calibration, court):
    """GLOBAL stage, shipped: line-fit autodetect. -> (named DBL corners, score)."""
    res = autodetect(frame, calibration, court)
    if res is None:
        return None, None
    ref = res[2]
    return {k: [float(ref[k][0]), float(ref[k][1])] for k in DBL}, float(res[1])


def _propose_courtnet(frame, calibration, court, weights=None):
    """GLOBAL stage, flipped: CourtNet localises the court, we take only the four
    doubles corners its homography implies and hand them to the SAME local snap.

    `verify=False` on purpose: verify_court is a second ACCEPT test that the
    classical proposer has no counterpart for, and the shipped 6-DOF lock plus the
    consensus vote are what decide acceptance here. Leaving it on would make the
    A/B two variables. Score returned is the model's own keypoint confidence and is
    NOT comparable with the classical ranking score (same caveat as `with_score`)."""
    det = calibration.detect_court_learned(
        frame, weights=weights or COURTNET_BASE_WEIGHTS, verify=False)
    if det is None:
        return None, None
    xy = calibration.court_to_image(det.homography, [court.LANDMARKS[k] for k in DBL])
    named = {k: [float(p[0]), float(p[1])] for k, p in zip(DBL, xy)}
    return named, float(det.confidence)


def auto_fit_frame(frame, calibration, court, *, with_score=False, proposer=None,
                   weights=None):
    """The full single-frame recipe: GLOBAL proposal -> guarded corner snap (LOCAL)
    -> physical shape re-lock. Returns {corner:[x,y]} or None (no lock).

    proposer (default None -> `resolved_proposer()` -> "classical", the shipped
    ordering): which stage-one localiser runs. "courtnet" runs the CNN globally and
    the classical machinery locally - the ordering flip. Stages two and three below
    are untouched by the flag, so the two arms differ in exactly one thing.

    with_score (eval harness only, default off so the shipped return is byte-for-byte
    unchanged): also return `autodetect`'s raw ranking score as (corners, score),
    (None, None) on a refusal. The score EXISTS ONLY AS A DIAGNOSTIC and is not
    comparable across mask paths - the white path ranks by g*(0.5+0.5*st) and the
    clay path by st alone, on different scales. Nothing may gate on it while that
    is true; eval/run_eval.py prints it to make the incomparability visible."""
    which = resolved_proposer(proposer)
    if which == "courtnet":
        named, score = _propose_courtnet(frame, calibration, court, weights=weights)
    else:
        named, score = _propose_classical(frame, calibration, court)
    if named is None:
        return (None, None) if with_score else None
    _, out, _snapped, _c0, _c1 = calibration.snap_to_lines(
        frame, named, min_coverage=0.0, max_move_px=60.0)
    use = out if all(k in out for k in DBL) else named
    # the free corner-snap can undo the physical gate; re-lock to a camera view
    h, w = frame.shape[:2]
    out = lock_quad(use, calibration, court, w, h,
                    dt=line_distance_map(frame, calibration))[0]
    return (out, float(score)) if with_score else out


def fit_video_frames(frames, calibration, court, *, proposer=None, weights=None):
    """Consensus auto-calibration over sampled frames of ONE clip.

    Fits each frame independently, keeps the largest agreeing group (the court is
    static; wrong-rung locks don't reproduce), falls back to the clay/shell
    evidence stack when nothing agrees. Returns (corners, votes, tag):
      tag "vote"  - corners = per-corner median of `votes` agreeing frames
      tag "stack" - clay rescue fit (single fit on stacked line evidence)
      (None, votes, None) - refused; votes = best agreement seen."""
    fits = [auto_fit_frame(f, calibration, court, proposer=proposer, weights=weights)
            for f in frames]
    pts, votes = consensus(fits)
    if pts is not None:
        return pts, votes, "vote"
    if len(frames) >= 6:
        pts = stacked_clay_fit(list(enumerate(frames)), calibration, court)
        if pts is not None:
            return pts, 1, "stack"
    return None, votes, None


# --- keypoint detector interface (the 3D camera's first guess) ---------------
# A detector finds named court keypoints; camera3d.solve_pnp_seed turns them
# into a rough camera and paintfit places the court. Keypoints are only ever a
# SEED: P8 C1 measured that a camera pinned by points misplaces the far lines by
# metres unless each point is right to ~0.1 px (docs/evidence/court-map-ceiling.md).
# A model trained on amateur / synthetic courts plugs in behind this Protocol.
COURTNET_SPLIT_WEIGHTS = str(REPO / "backend" / "weights" / "courtnet_split.pt")


@dataclass
class KeypointSet:
    """Named image points (pixels) with a per-point confidence in [0, 1].
    Names are `court.LANDMARKS_3D` keys; `source` says which detector made them."""
    px: dict
    conf: dict = field(default_factory=dict)
    source: str = "unknown"
    image_wh: tuple = (0, 0)


class KeypointDetector(Protocol):
    def detect(self, frame) -> Optional[KeypointSet]: ...


class CourtNetKeypoints:
    """Every CourtNet heatmap peak with its value as confidence - including the
    weak ones `detect_court_learned` drops below 0.40, since RANSAC in the PnP
    solve decides which to keep. Defaults to the LEAK-CLEAN `courtnet_split.pt`
    (courtnet_ft.pt trained on a pool overlapping the court gold, T06). Loads
    its own model per checkpoint: `detect_court_learned`'s global cache ignores
    a later `weights` argument, which is how the wrong checkpoint gets scored.
    The upstream checkpoint finds 2-3 confident peaks on amateur footage
    (docs/evidence/cnn-global-classical-local.md): an interface, not a remedy."""

    _models: dict = {}

    def __init__(self, weights: str | None = None, device: str = "cpu",
                 min_conf: float = 0.0):
        self.weights = weights or COURTNET_SPLIT_WEIGHTS
        self.device, self.min_conf = device, min_conf

    def _model(self):
        key = (self.weights, self.device)
        if key not in self._models:
            import torch
            from ._courtnet import CourtNet
            m = CourtNet(out_channels=15)
            m.load_state_dict(torch.load(self.weights, map_location=self.device))
            self._models[key] = m.eval().to(self.device)
        return self._models[key]

    def detect(self, frame):
        import cv2
        import torch
        from . import calibration
        img = cv2.resize(frame, (640, 360)).astype(np.float32) / 255.0
        inp = torch.from_numpy(np.rollaxis(img, 2, 0)).unsqueeze(0).float().to(self.device)
        with torch.no_grad():
            pred = torch.sigmoid(self._model()(inp)[0]).cpu().numpy()
        got = calibration.courtnet_decode(pred, frame, self.min_conf)
        if not got:
            return None
        h, w = frame.shape[:2]
        return KeypointSet(px={n: (x, y) for n, (x, y, _c) in got.items()},
                           conf={n: c for n, (_x, _y, c) in got.items()},
                           source=f"courtnet:{os.path.basename(self.weights)}",
                           image_wh=(w, h))


class ClassicalKeypoints:
    """The shipped line-fit path (`auto_fit_frame`) as a keypoint source: its
    four doubles corners, and every OTHER ground keypoint projected from them.
    Those extra points carry no information the four corners do not (the same
    trap as the court gold's computed keypoints), and `autodetect` is the search
    recorded CLOSED - this exists so today's behaviour can seed the 3D camera,
    not as a recovery path. Confidence is 1.0: the fit's score is a diagnostic
    only (see auto_fit_frame)."""

    def __init__(self, proposer: str | None = None):
        self.proposer = proposer

    def detect(self, frame):
        from . import calibration, court
        corners = auto_fit_frame(frame, calibration, court, proposer=self.proposer)
        if corners is None:
            return None
        H = calibration.compute_homography([court.LANDMARKS[k] for k in DBL],
                                           [corners[k] for k in DBL])
        names = [n for n, p in court.LANDMARKS_3D.items() if p[2] == 0.0]
        xy = calibration.court_to_image(H, [court.LANDMARKS_3D[n][:2] for n in names])
        h, w = frame.shape[:2]
        return KeypointSet(px={n: (float(p[0]), float(p[1])) for n, p in zip(names, xy)},
                           conf={n: 1.0 for n in names},
                           source=f"classical:{resolved_proposer(self.proposer)}",
                           image_wh=(w, h))


# --- projective sanity: cross-ratios along painted lines ---------------------
# Points on one straight line keep their cross-ratio under any camera: three of
# them fix a 1-D projective map from court metres to image position along the
# line, and that map predicts where every other point on the line must be. A
# detection far from its prediction (along the line, or off it) is misplaced.
# This is a GROSS-OUTLIER gate before the PnP solve, never an accuracy measure.
# It holds for an undistorted image; pass `undistort` when the lens is known.
# Tolerance, px @720 scaled by frame height (CLAUDE.md), set on a NOISE-ONLY
# simulation (CP1's seed noise, sigma 14.78 px @1080, three camera poses, 300
# draws each; docs/evidence/court-camera3d.md): 20 px falsely flags a good point
# in 18-38% of detections, 60 px in 0.3%, and 60 px still names a near point
# moved 1.5 m in 87-90%. Predicting a point from other noisy points amplifies
# their noise, so the gate only ever catches GROSS errors; RANSAC does the rest.
CROSS_TOL_PX_720 = 60.0


def cross_ratio(a: float, b: float, c: float, d: float) -> float:
    """(AC * BD) / (BC * AD) for four positions along one line."""
    return ((c - a) * (d - b)) / ((c - b) * (d - a))


def _line_coords(pts):
    """Positions along, and residuals across, the best-fit line of `pts`."""
    pts = np.asarray(pts, float)
    ctr = pts.mean(0)
    _, _, vt = np.linalg.svd(pts - ctr)
    return (pts - ctr) @ vt[0], (pts - ctr) @ vt[1]


def _held_out_px(world, img, i):
    """Pixel miss of point i predicted from the others on its line: along the
    line through the 1-D projective map, across it through the fitted line."""
    rest = [k for k in range(len(world)) if k != i]
    P = img[rest]
    ctr = P.mean(0)
    _, _, vt = np.linalg.svd(P - ctr)
    u, n = vt[0], vt[1]
    s = (P - ctr) @ u
    x = np.asarray(world, float)[rest]
    # s = (p x + q) / (r x + 1)  <=>  p x + q - r x s = s
    A = np.column_stack([x, np.ones_like(x), -x * s])
    p, q, r = np.linalg.lstsq(A, s, rcond=None)[0]
    den = r * world[i] + 1.0
    if abs(den) < 1e-12:
        return math.inf
    s_pred = (p * world[i] + q) / den
    d = img[i] - ctr
    return float(math.hypot(d @ u - s_pred, d @ n))


def cross_ratio_check(px: dict, image_h: float, *, undistort=None,
                      tol_px_720: float = CROSS_TOL_PX_720):
    """-> (outliers, report). For every `court.COLLINEAR_SETS` line with >=4
    detected points, predict each point from the others. A point is an OUTLIER
    when its miss is the line's largest, above tolerance, and every other
    point's miss is within tolerance once it is removed - so only a line with
    >=5 points can name one (with 4, one bad point spoils every prediction).
    `report` lists (line, n_points, worst miss px) for every line checked."""
    from . import court
    tol = tol_px_720 * image_h / 720.0
    outliers, report = set(), []
    for line, names in court.COLLINEAR_SETS.items():
        have = [n for n in names if n in px]
        if len(have) < 4:
            continue
        axis = 0 if line.endswith("baseline") else 1      # position along the line
        img = np.array([px[n] for n in have], float)
        if undistort is not None:
            img = np.asarray(undistort(img), float)
        world = [court.LANDMARKS_3D[n][axis] for n in have]
        miss = [_held_out_px(world, img, i) for i in range(len(have))]
        worst = int(np.argmax(miss))
        report.append((line, len(have), float(miss[worst])))
        if len(have) < 5 or miss[worst] <= tol:
            continue
        keep = [k for k in range(len(have)) if k != worst]
        w2, i2 = [world[k] for k in keep], img[keep]
        if all(_held_out_px(w2, i2, j) <= tol for j in range(len(keep))):
            outliers.add(have[worst])
    return outliers, report
