"""validate_new_clip.py — intake gate for a clip + its court calibration, run
BEFORE it costs any labeling time (refresh-plan steps 0 and 2).

Two checks:
  0) RESOLUTION gate — is the clip genuinely higher-res than the current 720p pool?
     A 720p re-download is a no-op (the far ball stays ~2-4 px); 1080p/4K is the win.
  2) CALIBRATION sanity — does the corners file give a NON-degenerate homography?
     camera height 2-15 m, near baseline BELOW the far baseline in-frame, corners not
     left/right swapped, and every court line projects as one contiguous in-frame run
     (no horizon crossing). The degenerate data/yt_court_pts_doubles.json failed all
     of these and silently broke the court overlay + ball gating all session.
  3) NET ANCHORS (--net-anchors) - the only check here that is INDEPENDENT of the
     four clicked corners. Checks 0 and 2 are computed from those corners alone, so
     they can only ask whether the four points form a plausible court, never whether
     they are the RIGHT four points. The net line, the net TAPE (0.914 m up) and the
     two net posts (0.914 m outside the doubles sideline) are none of them fitted.
     docs/evidence/net-anchor-calibration-check.md.

  # gate a new clip (+ optional calibration)
  cd backend && ../backend/.venv/Scripts/python.exe ../tools/validate_new_clip.py \
      ../data/<clip>.mp4 --keypoints ../data/<clip>_pts.json

  # audit existing calibration files (no video needed for the corners geometry check)
  ../backend/.venv/Scripts/python.exe ../tools/validate_new_clip.py --audit ../data/*_pts.json

  # ... plus the independent net-anchor rows (and render them:
  #     tools/render_corner_audit.py --net-anchors)
  ../backend/.venv/Scripts/python.exe ../tools/validate_new_clip.py --audit       ../data/<clip>_pts.json --net-anchors
"""
from __future__ import annotations
import argparse, glob, json, sys, time
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))
sys.path.insert(0, str(REPO / "tools"))
import numpy as np
from swingvision import calibration, court, overlay

CORN = ("near_bl_doubles", "near_br_doubles", "far_bl_doubles", "far_br_doubles")


def resolution_gate(video):
    import cv2
    c = cv2.VideoCapture(str(video))
    w, h, fps, n = int(c.get(3)), int(c.get(4)), c.get(5) or 0, int(c.get(7))
    c.release()
    tier = "HIGH (>=1080p)" if h >= 1080 else ("720p — NO-OP vs current pool" if h >= 700
                                               else "LOW (<720p)")
    verdict = "PASS" if h >= 1080 else ("WEAK" if h >= 700 else "FAIL")
    print(f"[resolution] {w}x{h} @{fps:.0f}fps, {n} frames ({n/max(fps,1):.0f}s) -> {tier}  [{verdict}]")
    print(f"[resolution]   far-ball pixels scale ~{h/720:.1f}x vs the current 720p pool")
    return verdict


def frame_size_for(kp_path, default):
    """Frame size of the clip a corners file belongs to, from data/<tag>.mp4.

    The corners are pixel coordinates, so every geometric check here is
    resolution-dependent — auditing a 1080p calibration as if it were 720p reads
    the camera ~20% too high. Falls back to `default` when the clip isn't found.
    """
    tag = Path(kp_path).name.split("_pts")[0]
    # Search every directory clips actually live in, not just data/. Training
    # footage sits in data/train_clips, and looking only in data/ made this fall
    # back to 720p for a pool of 1080p clips — which reads the camera ~20% high
    # and stamped NINE correctly-placed calibrations DEGENERATE (fit 15-56 px).
    # The same files audit at 2.5 px and PASS once the real size is used.
    # SEARCH RECURSIVELY. The list below used to be a flat set of directories,
    # which broke a second time the moment data/incoming was reorganised into
    # data/incoming/<surface>/ — the videos were one level deeper than the check
    # looked, every 4K shell calibration fell back to 720p, and all five audited
    # DEGENERATE at 41-117 px fit residual. Exactly the nine-false-DEGENERATE
    # failure described above, recurring because the fix was a hard-coded list.
    # A recursive search cannot be broken by moving a file, which is the point.
    candidates = [REPO / "data" / f"{tag}.mp4"]
    for sub in ("incoming", "train_clips", "gold_clips", "amateur_clips", "gold"):
        d = REPO / "data" / sub
        if d.is_dir():
            candidates += sorted(d.rglob(f"{tag}.mp4"))
    for vid in candidates:
        if vid.exists():
            import cv2
            c = cv2.VideoCapture(str(vid))
            w, h = int(c.get(3)), int(c.get(4))
            c.release()
            if w and h:
                return (w, h), True
    return default, False


MAX_FIT_PX = 10.0   # beyond this the corners are not any real camera's view
MAX_CAM_H = 15.0    # above this it is not a court-side mount


def net_anchor_report(kp_path, img_wh):
    """The NET-ANCHOR check, printed alongside the geometry audit.

    Everything above this point is computed from the four clicked corners and
    from nothing else, so it can only ask whether those four points form a
    plausible court - never whether they are the RIGHT four points. The net line,
    the net tape and the two net posts are at known court coordinates that no
    clicked corner touches, so they are independent evidence. See
    tools/net_anchor_check.py and docs/evidence/net-anchor-calibration-check.md.

    Prints numbers only; the picture is the verdict, and
    `render_corner_audit.py --net-anchors` draws it.
    """
    import net_anchor_check as nac
    tag = Path(kp_path).name.split("_pts")[0]
    kp = json.loads(Path(kp_path).read_text(encoding="utf-8"))
    if any(n not in kp for n in CORN):
        return
    hfov = nac.hfov_for(kp, img_wh[0], img_wh[1])
    geo = nac.net_anchor_geometry(kp, img_wh, hfov)
    print(f"[net]   horizon row {geo['horizon_row']}   net GROUND row "
          f"{geo['net_ground_row']}   net TAPE row {geo['net_tape_row']}"
          + ("" if hfov is None else f"   (hfov {hfov:.0f}deg, fitted)"))
    print("[net]   the TAPE row is what a human sees. Comparing the GROUND row to "
          "the white tape is apples to oranges - the tape is 0.914 m up.")
    for name, base in geo["post_bases"].items():
        top = geo["post_tops"].get(name)
        inside = 0 <= base[0] < img_wh[0] and 0 <= base[1] < img_wh[1]
        print(f"[net]   {name}: base ({base[0]:.0f}, {base[1]:.0f})"
              + ("" if top is None else f" top ({top[0]:.0f}, {top[1]:.0f})")
              + ("" if inside else "   OFF-FRAME (normal on a low wide mount)"))
    from render_corner_audit import find_video, grab_frame
    vid = find_video(tag)
    if vid is None:
        print("[net]   no clip found - rows only, no image measurement")
        return
    frame = grab_frame(vid, 0)
    if frame is None:
        return
    meas, _ = nac.measure(frame, kp, img_wh, hfov)
    print(f"[net]   band_ratio {meas['band_ratio']} (best {meas['ratio_best']} at "
          f"dy {meas['dy_best']} px, net {meas['net_px_height']} px tall)")
    print("[net]   NOTE: the band_ratio/dy bars FAILED validation on this corpus "
          "(they invert on yt_match40). Reported, not trusted - open the PNG.")


def camera_fit(kp, img_wh):
    """Fit the physical camera that produces these corners.

    courtfit.cam_fit_quad solves for position, pan, tilt, zoom and bounded roll,
    so it reads the focal off the geometry instead of assuming one. Two things
    come back that the old 70-degree assumption could not give:

      * an honest height — on am_hard_utr the assumption reads 2.1 m, the fit
        reads 1.74 m at hfov 86 deg, either side of the 2 m advice floor;
      * fit_px, the distance from the given quad to the NEAREST legal camera
        view. That residual is the real degeneracy test, and it separates the
        known files cleanly: every KNOWN GOOD calibration fits within 2.5 px
        (yt_match40 0.9, yt_rally2 1.4, yt_court 2.1) and every KNOWN BAD one is
        an order of magnitude out (doubles 54, singles 91, demo30 565). A quad
        no camera can produce has no meaningful height to check.

    Returns (height_m, fit_px, description) — height/fit_px are None if the
    solve is unavailable (needs scipy) or refuses.
    """
    try:
        from swingvision import courtfit
        fit = courtfit.cam_fit_quad({n: kp[n] for n in CORN}, calibration, court,
                                    img_wh[0], img_wh[1], allow_roll=True)
        if fit is not None:
            cam = fit[3]
            hfov = calibration.hfov_from_focal(cam[5], img_wh[0])
            roll = np.degrees(cam[6]) if len(cam) > 6 else 0.0
            return (abs(float(cam[2])), float(fit[2]),
                    f"hfov {hfov:.0f}deg roll {roll:+.1f}deg fit {fit[2]:.1f}px")
    except Exception:
        pass
    return None, None, "camera fit unavailable"


def calib_sanity(kp_path, img_wh=(1280, 720), stamp=False, img_wh_from_clip=True):
    kp = json.loads(Path(kp_path).read_text(encoding="utf-8"))
    missing = [n for n in CORN if n not in kp]
    if missing:
        print(f"[calib] {Path(kp_path).name}: MISSING corners {missing}  [FAIL]")
        return "FAIL"
    H = calibration.compute_homography([court.LANDMARKS[n] for n in CORN], [kp[n] for n in CORN])
    fw, fh = img_wh
    reasons, warns = [], []
    # 1) is this quad a real camera's view at all, and how high is that camera?
    ch, fit_px, lens = camera_fit(kp, img_wh)
    if fit_px is not None and fit_px > MAX_FIT_PX:
        reasons.append(f"corners are not a physical camera view (fit residual {fit_px:.0f} px)")
    elif ch is not None and ch > MAX_CAM_H:
        reasons.append(f"camera height {ch:.1f} m (above {MAX_CAM_H:.0f} m is not a court-side mount)")
    elif ch is not None and ch < 2.0:
        # A low camera is USABLE, not broken — a phone clamped to a fence is the
        # footage this project targets. What it costs is measurable depth, so say
        # that in metres instead of failing the file.
        frac, until = calibration.reliable_court_span(H)
        warns.append(f"low camera {ch:.2f} m — measurable to court-y {until:.1f} m "
                     f"of {court.LENGTH:.1f} ({100*frac:.0f}% of depth)")
    # 2) orientation: near baseline lower in frame than far; near-left left of near-right
    nbl = calibration.court_to_image(H, [court.LANDMARKS["near_bl_doubles"]])[0]
    nbr = calibration.court_to_image(H, [court.LANDMARKS["near_br_doubles"]])[0]
    fbl = calibration.court_to_image(H, [court.LANDMARKS["far_bl_doubles"]])[0]
    if not (nbl[1] > fbl[1]):
        reasons.append(f"near baseline not below far in frame (near y={nbl[1]:.0f}, far y={fbl[1]:.0f})")
    if not (nbl[0] < nbr[0]):
        reasons.append(f"near corners left/right swapped (bl x={nbl[0]:.0f} >= br x={nbr[0]:.0f})")
    # 3) every court line projects as ONE contiguous in-frame run (no horizon crossing)
    bad = 0
    for a, b in court.LINES:
        runs = overlay._project_court_line(H, a, b, (fw, fh))
        if len(runs) != 1:
            bad += 1
    if bad:
        reasons.append(f"{bad}/{len(court.LINES)} court lines cross the horizon / go off-frame")
    verdict = "DEGENERATE" if reasons else ("LOW-CAMERA" if warns else "PASS")
    print(f"[calib] {Path(kp_path).name}: camera ~{('?' if ch is None else round(ch, 2))} m "
          f"@{fw}x{fh} ({lens}) -> {verdict}")
    for r in reasons + warns:
        print(f"[calib]     - {r}")

    if stamp:
        # Persist the verdict INTO the file. The audit has always been able to
        # tell a good calibration from a degenerate one; what it could not do is
        # stop someone tab-completing `court_pts.json` (38 px) instead of
        # `court_pts_refined.json` (2.3 px) months later. Written under a single
        # "_audit" key: every loader in this repo indexes corners by name, so an
        # extra key is inert, and pipeline.calibrate_video now reads it back and
        # refuses to load a DEGENERATE file silently.
        blob = json.loads(Path(kp_path).read_text(encoding="utf-8"))
        blob["_audit"] = {
            "tool": "validate_new_clip.py --stamp",
            "date": time.strftime("%Y-%m-%d"),
            "verdict": verdict,
            "fit_residual_px": None if fit_px is None else round(fit_px, 1),
            "camera_height_m": None if ch is None else round(ch, 2),
            "img_wh": [fw, fh],
            "img_wh_source": "clip" if img_wh_from_clip else "assumed",
            "reasons": reasons + warns,
        }
        Path(kp_path).write_text(json.dumps(blob, indent=1), encoding="utf-8")
        print(f"[calib]     -> stamped _audit verdict={verdict}")

    return "FAIL" if reasons else ("WEAK" if warns else "PASS")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("video", nargs="?", help="clip to resolution-gate")
    ap.add_argument("--keypoints", help="court corners JSON to sanity-check")
    ap.add_argument("--audit", nargs="*", help="calibration files to audit (geometry only)")
    ap.add_argument("--img-wh", default="1280x720", help="frame size for the calib geometry check")
    ap.add_argument("--net-anchors", action="store_true",
                    help="also report the NET-ANCHOR check: the net line, the net "
                         "TAPE row and both net posts, none of which is one of the "
                         "four fitted corners, so it is independent of the fit")
    ap.add_argument("--stamp", action="store_true",
                    help="write the verdict back into each audited file as an "
                         "\"_audit\" key, so a degenerate calibration announces "
                         "itself instead of silently breaking the overlay")
    args = ap.parse_args()
    fw, fh = (int(v) for v in args.img_wh.lower().split("x"))

    results = []
    if args.video:
        results.append(resolution_gate(args.video))
        if args.keypoints:
            import cv2
            c = cv2.VideoCapture(str(args.video)); fw, fh = int(c.get(3)), int(c.get(4)); c.release()
    if args.keypoints:
        results.append(calib_sanity(args.keypoints, (fw, fh), args.stamp,
                                    img_wh_from_clip=bool(args.video)))
        if args.net_anchors:
            net_anchor_report(args.keypoints, (fw, fh))
    for f in (args.audit or []):
        # Each audited file gets ITS OWN clip's frame size where we can find it —
        # one --img-wh for a mixed 720p/1080p batch mis-measures every camera.
        wh, found = frame_size_for(f, (fw, fh))
        if not found:
            print(f"[calib] {Path(f).name}: no data/<tag>.mp4 — assuming {wh[0]}x{wh[1]}")
        results.append(calib_sanity(f, wh, args.stamp, img_wh_from_clip=found))
        if args.net_anchors:
            net_anchor_report(f, wh)
    if not results:
        ap.error("give a video, --keypoints, and/or --audit")
    print(f"\nSUMMARY: {results.count('PASS')} pass, {results.count('WEAK')} weak, "
          f"{results.count('FAIL')} fail")


if __name__ == "__main__":
    main()
