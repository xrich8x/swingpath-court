"""Render every calibration's CLICKED CORNERS onto a real frame, so a human can
audit them by looking instead of by reading a residual.

This exists because of trap T23. `data/yt_match40_pts.json` is stamped PASS at a
**0.9 px** fit residual with all four clicked corners off any court line. A residual
only asks whether four points form a plausible court; four points on a plausible
trapezoid in the wrong place fit perfectly. The pipeline then put the net line
35-75 px low and labelled the NEAR player FAR, and P0-2 published that mislabel as
an 11.0% far-player detection rate.

So: `validate_new_clip.py --audit` is a screen, not a verdict. The verdict is the
frame. This tool renders it.

What is drawn, and deliberately what is not:
  * the four clicked corners, each labelled by name, as a cross plus a ring
  * the quad they form, edge by edge
  * NOTHING derived from the homography - no projected court model, no net line.
    A projected court is a *consequence* of the clicks. Drawing it invites the
    reader to check the clicks against the thing the clicks produced, which is
    circular, and is close to how T23 survived a written gate in the first place.
    The reader's job is only: does each corner sit on the court line it is named
    for? That is answerable from paint and clicks alone.

Corners off-frame are normal on a low wide mount (`am_hard_utr` clicks x=-41 and
x=2090 on a 1920-wide frame) and are reported in the caption rather than drawn, so
their absence is never read as a missing click.

WHICH FRAME IS RENDERED, and why it is not frame 0 any more (fixed 2026-09-09).
This tool used to default to `--frame 0`, while `eval/run_refs.py` scores k=8
frames spread over 5%-95% of the clip. So the sheet a human audited could show a
frame the scoring never looks at. On a locked-off tripod that is harmless; on any
clip where the camera moves it is misleading, and **nothing in a `*_pts.json`
records whether the camera moves, or which frame the corners were placed
against** - so the harmless case cannot be told from the misleading one by
reading the calibration. The default is now one of the eval's own eight samples
(imported from `run_refs.frame_positions`, not copied), and the caption states
the index and how it was chosen. `--eval-frames` renders all eight; that is the
honest answer when the mount is in doubt, because ONE frame cannot show camera
motion and this tool renders one frame at a time.

Output files carry the frame index (`<tag>_corners_f<N>.png`). They did not
before, so rendering one clip at several frames overwrote a single file and
destroyed every earlier sheet with no error.

Run from the repo root:
  ./backend/.venv/Scripts/python.exe tools/render_corner_audit.py
  ./backend/.venv/Scripts/python.exe tools/render_corner_audit.py --pts data/yt_match40_pts.json
  ./backend/.venv/Scripts/python.exe tools/render_corner_audit.py --eval-frames
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

import cv2
import numpy as np

import net_anchor_check

REPO = pathlib.Path(__file__).resolve().parents[1]

CORNERS = ["near_bl_doubles", "near_br_doubles", "far_br_doubles", "far_bl_doubles"]
COL = {
    "near_bl_doubles": (80, 255, 80),
    "near_br_doubles": (80, 255, 255),
    "far_br_doubles": (255, 160, 80),
    "far_bl_doubles": (255, 80, 255),
}
WHITE = (255, 255, 255)
GREY = (140, 140, 140)
RED = (0, 0, 255)
AMBER = (0, 190, 255)


def find_video(tag):
    """Same recursive search validate_new_clip.py uses - a hard-coded directory
    list has broken twice here when data/ was reorganised."""
    cands = [REPO / "data" / f"{tag}.mp4"]
    for sub in ("incoming", "train_clips", "gold_clips", "amateur_clips", "gold"):
        d = REPO / "data" / sub
        if d.is_dir():
            cands += sorted(d.rglob(f"{tag}.mp4"))
    for v in cands:
        if v.exists():
            return v
    return None


def grab_frame(video, index=0, seek=False):
    """Sequential decode by default, no seeking.

    `seek=True` uses `CAP_PROP_POS_FRAMES` - the SAME call sequence
    `eval/run_refs.frames_from` uses. That is deliberate: for an eval-sampled
    index the point is to show the human the frame the scoring actually saw, and
    if the decoder lands somewhere else on a seek, it lands there for both."""
    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        return None
    if seek and index > 0:
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(index))
        ok, f = cap.read()
        cap.release()
        return f if ok else None
    fr = None
    for i in range(index + 1):
        ok, f = cap.read()
        if not ok:
            break
        fr = f
    cap.release()
    return fr


EVAL_K = 8          # eval/run_refs.py scores this many frames per clip


def eval_positions(total, k=EVAL_K):
    """The frame indices `eval/run_refs.py` scores, IMPORTED from it.

    Not re-implemented here on purpose: a copied formula is exactly how this
    tool and the eval drifted apart in the first place. An ImportError is left
    to propagate - a silent fallback to frame 0 is the defect, not the fix."""
    p = str(REPO / "eval")
    if p not in sys.path:
        sys.path.insert(0, p)
    from run_refs import frame_positions
    return frame_positions(int(total), int(k))


def frame_count(video):
    cap = cv2.VideoCapture(str(video))
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) if cap.isOpened() else 0
    cap.release()
    return max(n, 0)


def default_frame(total, k=EVAL_K):
    """(index, how-it-was-chosen) for the caption.

    The lower-middle eval sample. One frame cannot prove a camera never moved,
    so the choice is only that it be a frame the scoring OWNS - frame 0 is not
    one, and was the old default."""
    pos = eval_positions(total, k)
    if not pos:
        return 0, ("frame 0 (first decodable) - frame count UNKNOWN, so the "
                   "eval's sampling could not be reproduced")
    idx = pos[(len(pos) - 1) // 2]
    return idx, (f"frame {idx} = eval sample {(len(pos) - 1) // 2 + 1}/{len(pos)} "
                 f"(run_refs, 5%-95% of {total})")


def render(pts_path, frame_index, out_dir, tag_override=None, video_tag=None):
    """`frame_index=None` means "let the eval choose" - see default_frame."""
    tag = tag_override or pts_path.stem.replace("_pts", "")
    blob = json.loads(pts_path.read_text(encoding="utf-8"))
    kp = {k: blob[k] for k in CORNERS if k in blob}
    if len(kp) < 4:
        return {"tag": tag, "status": "SKIP", "note": f"only {len(kp)}/4 named corners"}

    video = find_video(video_tag or tag)
    if video is None:
        return {"tag": tag, "status": "NO VIDEO", "note": "no matching .mp4 found"}
    total = frame_count(video)
    if frame_index is None:
        frame_index, how = default_frame(total)
    else:
        pos = eval_positions(total)
        how = (f"frame {frame_index} - REQUESTED with --frame"
               + (f"; this IS eval sample {pos.index(frame_index) + 1} of {len(pos)}"
                  if frame_index in pos else
                  f"; NOT one of the {len(pos)} frames run_refs scores"
                  if pos else "; clip frame count unknown"))
    frame = grab_frame(video, frame_index, seek=True)
    if frame is None:
        return {"tag": tag, "status": "NO FRAME",
                "note": f"cannot decode {video.name} at frame {frame_index}"}

    h, w = frame.shape[:2]
    img = frame.copy()
    audit = blob.get("_audit", {})
    stamped_wh = audit.get("img_wh")
    # A calibration clicked at one resolution and rendered at another lands
    # nowhere. This is the exact failure the auditor's own comments describe.
    sx = sy = 1.0
    if stamped_wh and (stamped_wh[0] != w or stamped_wh[1] != h):
        sx, sy = w / float(stamped_wh[0]), h / float(stamped_wh[1])

    off = []
    P = {}
    for name in CORNERS:
        x, y = kp[name][0] * sx, kp[name][1] * sy
        P[name] = (x, y)
        if not (0 <= x < w and 0 <= y < h):
            off.append(name)

    for a, b in zip(CORNERS, CORNERS[1:] + CORNERS[:1]):
        cv2.line(img, tuple(np.int32(P[a])), tuple(np.int32(P[b])), WHITE, 2, cv2.LINE_AA)
    for name in CORNERS:
        x, y = np.int32(P[name])
        if 0 <= x < w and 0 <= y < h:
            cv2.drawMarker(img, (x, y), COL[name], cv2.MARKER_CROSS, 34, 2)
            cv2.circle(img, (x, y), 15, COL[name], 2, cv2.LINE_AA)
            cv2.putText(img, name.replace("_doubles", ""), (x + 19, y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.62, COL[name], 2, cv2.LINE_AA)

    scale = 1280.0 / w
    if abs(scale - 1.0) > 0.01:
        img = cv2.resize(img, (1280, int(h * scale)), interpolation=cv2.INTER_AREA)

    cap_h = 168
    cap = np.zeros((cap_h, img.shape[1], 3), np.uint8)
    verdict = audit.get("verdict", "not stamped")
    resid = audit.get("fit_residual_px")
    camh = audit.get("camera_height_m")
    vcol = AMBER if verdict != "PASS" else GREY
    rows = [
        (f"{tag}   {video.name}   {how}   {w}x{h}", WHITE),
        ("ONE frame shown; run_refs scores EIGHT. A single frame cannot show camera "
         "motion - --eval-frames renders all 8.", GREY),
        (f"stamped: {verdict}"
         + (f"   residual {resid} px" if resid is not None else "")
         + (f"   camera {camh} m" if camh is not None else "")
         + ("   [clicked at %dx%d, RESCALED to render]" % tuple(stamped_wh)
            if sx != 1.0 or sy != 1.0 else ""), vcol),
        ("THE RESIDUAL IS NOT THE VERDICT (T23). Ask only: does each corner sit on "
         "the court line it is named for?", GREY),
        (("off-frame, not drawn: " + ", ".join(n.replace("_doubles", "") for n in off)
          + "  (normal on a low wide mount)") if off else
         "all four corners are inside the frame", AMBER if off else GREY),
    ]
    for i, (t, c) in enumerate(rows):
        cv2.putText(cap, t, (8, 22 + i * 25), cv2.FONT_HERSHEY_SIMPLEX, 0.52, c, 1, cv2.LINE_AA)

    # The frame index is IN THE FILENAME. Without it, rendering one clip at five
    # frame indices produced one file and silently destroyed the other four.
    out = out_dir / f"{tag}_corners_f{frame_index}.png"
    cv2.imwrite(str(out), np.vstack([cap, img]))
    flag = "CHECK" if (camh is not None and camh > 6.0) else "ok"
    return {"tag": tag, "status": "rendered", "out": out.name, "verdict": verdict,
            "residual_px": resid, "camera_h_m": camh, "off_frame": off, "flag": flag,
            "frame": frame_index, "frame_choice": how, "video": video.name}


def post_height_row(video, kp, img_wh, hfov):
    """The NET-POST camera height, for the caption. Imported lazily so this
    module keeps working if the post tool is absent.

    THE POST NUMBER FAILED ITS PRE-REGISTERED BAR - 3 of 11 confident clips within
    10% of the fitted height, against a 2/3 bar, with confident rows off by up to
    +261.7% (docs/evidence/net-post-detector.md). It is carried here as a
    diagnostic beside the tape, never as a gate and never as something to show a
    user. The tape (13/15) is the number that works."""
    try:
        import net_post_height as nph
        import net_tape_height as nth
    except Exception:                                # noqa: BLE001
        return None
    plate = nth.clean_plate(video)
    if plate is None:
        return None
    w, h = img_wh
    h_fit = nth.fitted_height(kp, w, h)
    if h_fit is None:
        return None
    return nph.measure_post_height(plate[0], kp, img_wh, hfov, h_fit)


def render_net_anchors(pts_path, frame_index, out_dir, tag_override=None,
                       video_tag=None, post_height=False):
    """The NET-ANCHOR check, rendered to its OWN image.

    Deliberately a separate PNG from the corner sheet above. The corner sheet's
    entire value is that it shows evidence and clicks and nothing derived from
    them; mixing a projection into it would re-create the confusion it exists to
    prevent. This image is the complementary question: given those clicks, does
    the NET land on the net? See tools/net_anchor_check.py for why that is not
    circular and what the two pre-registered bars are.
    """
    tag = tag_override or pts_path.stem.replace("_pts", "")
    blob = json.loads(pts_path.read_text(encoding="utf-8"))
    kp = {k: blob[k] for k in CORNERS if k in blob}
    if len(kp) < 4:
        return {"tag": tag, "status": "SKIP", "note": f"only {len(kp)}/4 named corners"}
    video = find_video(video_tag or tag)
    if video is None:
        return {"tag": tag, "status": "NO VIDEO", "note": "no matching .mp4 found"}
    if frame_index is None:
        frame_index, how = default_frame(frame_count(video))
    else:
        how = f"frame {frame_index} - REQUESTED with --frame"
    frame = grab_frame(video, frame_index, seek=True)
    if frame is None:
        return {"tag": tag, "status": "NO FRAME",
                "note": f"cannot decode {video.name} at frame {frame_index}"}

    h, w = frame.shape[:2]
    audit = blob.get("_audit", {})
    stamped_wh = audit.get("img_wh")
    sx = sy = 1.0
    if stamped_wh and (stamped_wh[0] != w or stamped_wh[1] != h):
        sx, sy = w / float(stamped_wh[0]), h / float(stamped_wh[1])
    kp = {n: (kp[n][0] * sx, kp[n][1] * sy) for n in CORNERS}

    hfov = net_anchor_check.hfov_for(kp, w, h)
    meas, geo = net_anchor_check.measure(frame, kp, (w, h), hfov)
    post = post_height_row(video, kp, (w, h), hfov) if post_height else None
    rows = [
        (f"{tag}   {video.name}   {how}   {w}x{h}   "
         + (f"hfov {hfov:.0f}deg (fitted)" if hfov else "hfov UNKNOWN"), WHITE),
        (f"stamped {audit.get('verdict', 'not stamped')} at "
         f"{audit.get('fit_residual_px')} px, camera {audit.get('camera_height_m')} m"
         f"   |   band_ratio {meas['band_ratio']}   best {meas['ratio_best']} at "
         f"dy {meas['dy_best']}   net {meas['net_px_height']} px", GREY),
        (f"rows: horizon {meas['horizon_row']}   net GROUND {meas['net_ground_row']}   "
         f"net TAPE {meas['net_tape_row']}   (tape = horizon + (ground-horizon)*(H-0.914)/H)",
         GREY),
        ("NET AND POSTS ARE NOT FITTED POINTS. Ask only: does the YELLOW tape line lie "
         "along the real white tape, and do the red sticks stand on the real posts?", GREY),
        ("Do NOT read the GREEN ground line against the tape - that is the apples-to-"
         "oranges error; the tape is 0.914 m up and MUST image higher.", AMBER),
    ]
    if post is not None:
        rows.append(
            (f"POST-implied camera height {post.get('post_H_m')} m "
             f"({post.get('pct_per_px_post')} %/px)  vs fitted "
             f"{audit.get('camera_height_m')} m"
             + (f"   REFUSED: {post['refused']}" if post.get("refused") else ""), GREY))
        rows.append(
            ("The POST number FAILED its pre-registered bar (3/11 within 10%; "
             "docs/evidence/net-post-detector.md). Diagnostic only - do not show a user.",
             AMBER))
    out = out_dir / f"{tag}_netanchor_f{frame_index}.png"
    cv2.imwrite(str(out), net_anchor_check.draw(frame, geo, meas, rows))
    extra = {} if post is None else {
        "post_H_m": post.get("post_H_m"), "post_refused": post.get("refused"),
        "pct_per_px_post": post.get("pct_per_px_post"),
        "pct_per_px_tape": post.get("pct_per_px_tape")}
    return {"tag": tag, "status": "rendered", "out": out.name, **extra,
            "frame": frame_index, "frame_choice": how,
            "verdict": audit.get("verdict"),
            "residual_px": audit.get("fit_residual_px"),
            "camera_h_m": audit.get("camera_height_m"),
            "hfov_deg": None if hfov is None else round(hfov, 1),
            **meas, "flag": "FLAG" if meas["flags"] else "ok"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pts", nargs="*", default=None)
    ap.add_argument("--frame", type=int, default=None,
                    help="render this exact frame index. Default: the middle of "
                         "the eight frames eval/run_refs.py scores (5%%-95%% of "
                         "the clip). The old default was frame 0, which the "
                         "scoring never looks at")
    ap.add_argument("--eval-frames", action="store_true",
                    help="render ALL %d frames run_refs.py scores, not one. The "
                         "honest answer when it matters whether the camera moved "
                         "- one sheet cannot show that" % EVAL_K)
    ap.add_argument("--out-dir", default="data/output/corner_audit")
    ap.add_argument("--tag", default=None,
                    help="name this run something other than the filename "
                         "stem (for auditing a .bak or a variant file). Honoured "
                         "on BOTH the corner and --net-anchors paths; it was "
                         "silently ignored on the corner path before 2026-09-09")
    ap.add_argument("--video-tag", default=None,
                    help="clip tag to find the frame under, when --tag is not it")
    ap.add_argument("--post-height", action="store_true",
                    help="with --net-anchors, also measure the NET POSTS and print "
                         "the post-implied camera height in the caption. Off by "
                         "default: it costs a second decode for the clean plate, and "
                         "the number FAILED its pre-registered bar - it is a "
                         "diagnostic, never something to show a user. See "
                         "docs/evidence/net-post-detector.md")
    ap.add_argument("--net-anchors", action="store_true",
                    help="render the NET-ANCHOR check instead: the net line and "
                         "both net posts, none of which is one of the four fitted "
                         "corners, drawn over the frame and measured")
    args = ap.parse_args()

    # A flag that is accepted and then ignored is the defect being fixed here,
    # so the two remaining combinations that cannot work are refused out loud.
    if args.post_height and not args.net_anchors:
        ap.error("--post-height only applies to --net-anchors; the corner sheet "
                 "deliberately draws nothing derived from the homography")
    if args.eval_frames and args.frame is not None:
        ap.error("--eval-frames and --frame are mutually exclusive")
    if args.tag and len(args.pts or []) > 1:
        ap.error("--tag renames the OUTPUT, so it cannot be shared by several "
                 "--pts files; pass one file at a time")

    files = ([pathlib.Path(p) for p in args.pts] if args.pts
             else sorted((REPO / "data").rglob("*_pts.json")))
    out_dir = REPO / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    fn = render_net_anchors if args.net_anchors else render
    rows = []
    for f in files:
        idxs = [args.frame]
        if args.eval_frames:
            vt = args.video_tag or (args.tag or f.stem.replace("_pts", ""))
            vid = find_video(vt)
            idxs = eval_positions(frame_count(vid)) if vid else [None]
            idxs = idxs or [None]
        for idx in idxs:
            try:
                rows.append(fn(f, idx, out_dir, args.tag, args.video_tag,
                               args.post_height)
                            if args.net_anchors
                            else fn(f, idx, out_dir, args.tag, args.video_tag))
            except Exception as e:                   # noqa: BLE001
                rows.append({"tag": f.stem, "status": "ERROR", "note": repr(e)[:110]})
            r = rows[-1]
            note = (f"ratio {r.get('band_ratio')} dy {r.get('dy_best')} {r.get('flag')}"
                    if args.net_anchors and r["status"] == "rendered"
                    else r.get("verdict", r.get("note", "")))
            print(f"  {r['tag']:28s} {r['status']:9s} f{r.get('frame')}  {note}")

    if args.net_anchors:
        done = [r for r in rows if r["status"] == "rendered"]
        flagged = [r for r in done if r["flag"] == "FLAG"]
        print(f"\n[net] {len(done)} sheet(s) from {len(files)} calibration(s) "
              f"-> {out_dir}")
        print(f"[net] {len(flagged)} FLAGGED by the pre-registered bars "
              f"(band_ratio < {net_anchor_check.BAR_BAND_RATIO}, or |dy| > "
              f"{net_anchor_check.BAR_DY_FRAC} x net px height):")
        for r in flagged:
            print(f"      {r['tag']:28s} ratio {r['band_ratio']} -> {r['ratio_best']} "
                  f"at dy {r['dy_best']}  netpx {r['net_px_height']}  "
                  f"stamped {r['verdict']} @ {r['residual_px']} px")
        print("[net] A BAR IS A TRIAGE ORDER, NOT A VERDICT - open the PNG (T23).")
        (out_dir / "net_index.json").write_text(json.dumps(rows, indent=2),
                                                encoding="utf-8")
        return 0

    done = [r for r in rows if r["status"] == "rendered"]
    tall = [r for r in done if r["flag"] == "CHECK"]
    print(f"\n[corners] {len(done)} sheet(s) from {len(files)} calibration(s) "
          f"-> {out_dir}")
    if tall:
        # An implausible camera height was the ONE real signal the T23 audit gave
        # and it was ignored, so surface it here rather than leaving it in a field.
        print("[corners] implausibly TALL camera for a court-side mount - look at "
              "these first:")
        for r in tall:
            print(f"          {r['tag']:28s} {r['camera_h_m']} m   "
                  f"stamped {r['verdict']} at {r['residual_px']} px")
    (out_dir / "index.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
