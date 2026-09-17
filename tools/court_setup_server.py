"""Court Setup - the SwingVision-style ADJUSTABLE OVERLAY calibration tool.

Instead of clicking four corners from scratch, you get a whole court overlay you
nudge into place: drag the middle to slide it, pull a corner to scale/tilt it, and
the line-snap tightens it onto the paint. "Auto-detect" seeds the overlay from the
line-fit detector; if it locks onto the wrong rung you just drag it right.

    backend/.venv/Scripts/python.exe tools/court_setup_server.py --clip am_ntrp40
    backend/.venv/Scripts/python.exe tools/court_setup_server.py --frame path/to/frame.jpg
    backend/.venv/Scripts/python.exe tools/court_setup_server.py --video clip.mp4   # first frame

Save writes {landmark: [x_px, y_px]} (the 4 doubles corners) - exactly what
`run.py analyze --keypoints` consumes.
"""

from __future__ import annotations

import argparse
import json
import sys
import threading
import time
import webbrowser
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))
sys.path.insert(0, str(REPO / "tools"))

DBL = ["near_bl_doubles", "near_br_doubles", "far_br_doubles", "far_bl_doubles"]
# A seed must put at least this share of the court template on real white
# paint, or it is not shown. Below it, a plain rectangle is less work than
# correcting a wrong court — measured against verify_court's own 0.40 accept
# bar, set lower here because a SEED only has to be worth nudging.
MIN_SEED_COVERAGE = 0.30


def clean_plate_and_motion(video_path, n=80, span_s=60.0, start_frac=0.30):
    """TEMPORAL FILTERING for the setup tool: a short-window median clean plate
    plus an MTI (moving-target) mask.

    The court is static and the players move, so the per-pixel MEDIAN across a
    short window wipes players/ball/passing shadows off the court and leaves the
    lines UNOCCLUDED — no player standing on the baseline we need to snap to.
    The window must be SHORT (identical light + framing): medianing across a
    whole match blends changing exposure/drift and FADES the lines (measured in
    tools/eval_court_cleanplate.py). Alongside the plate we compute an MTI mask —
    per-pixel temporal spread, so anything that MOVED is flagged — used to keep a
    residual ghost (a player who lingered on a line) out of the snap's polish.

    Returns (plate_bgr, static_mask_uint8) with static_mask==255 where stable, or
    (None, None) if the clip is too short to build a plate (caller uses 1 frame).
    """
    import cv2
    import numpy as np

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return None, None
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    if total <= 0:
        cap.release()
        return None, None
    start = int(total * start_frac)
    span = min(int(span_s * fps), max(1, total - start - 1))
    frames = []
    for i in np.linspace(start, start + span, n).astype(int):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(i))
        ok, im = cap.read()
        if ok:
            frames.append(im)
    cap.release()
    if len(frames) < 20:
        return None, None
    stack = np.stack(frames, axis=0)
    plate = np.median(stack, axis=0).astype(np.uint8)
    # MTI: flag the PLAYERS (compact, high-amplitude movers) so a ghost of a
    # player who lingered on a line stays out of the snap. It must NOT flag
    # diffuse background motion — swaying trees, drifting clouds, compression
    # flicker, small camera shake — or it erodes the very lines we snap to (that
    # over-masking made a real clip keep only 14% of its line pixels). So: a high
    # temporal-std threshold, an open to drop speckle, and keep only LARGE
    # connected components (a body, not leaves). The caller also guards its use.
    gray = stack[..., :3].astype(np.float32).mean(axis=3)
    moving = (gray.std(axis=0) > 30.0).astype(np.uint8)
    moving = cv2.morphologyEx(
        moving, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5)))
    num, lab, st, _ = cv2.connectedComponentsWithStats(moving, 8)
    min_area = 0.0008 * gray.shape[1] * gray.shape[2]   # ~a player, not leaf specks
    big = np.zeros_like(moving)
    for i in range(1, num):
        if st[i, cv2.CC_STAT_AREA] >= min_area:
            big[lab == i] = 1
    moving = cv2.dilate(big, cv2.getStructuringElement(cv2.MORPH_RECT, (11, 11)))
    static = (1 - moving).astype(np.uint8) * 255
    return plate, static


def start_live_camera(state, index=0, width=1280, height=720):
    """LIVE mode: stream a real camera and keep the framing verdict up to date.

    Two threads, deliberately decoupled so the UI never stutters:
      * grabber - reads the newest frame as fast as the camera delivers it, so
        what you see is what the camera sees RIGHT NOW while you aim it;
      * analyser - re-runs court auto-detect + the setup verdict on the latest
        frame in a loop. Detection costs ~1-3 s on a 720p CPU frame, so the
        guidance updates every few seconds rather than every frame - "near-live",
        the same honest caveat the ball detector carries (see CLAUDE.md). That is
        fine for aiming a tripod: you move the camera, then read the verdict.
    Returns the VideoCapture so the caller can release it.
    """
    import cv2
    from swingvision import calibration, court, courtfit

    cap = cv2.VideoCapture(index, cv2.CAP_DSHOW if hasattr(cv2, "CAP_DSHOW") else 0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    ok, first = cap.read()
    if not ok or first is None:
        cap.release()
        raise SystemExit(f"cannot open camera {index} (is another app using it?)")
    state["frame"] = first
    state["live"] = True
    state["seq"] = 0

    def grab():
        while not state.get("stop"):
            ok, im = cap.read()
            if ok and im is not None:
                state["frame"] = im
                state["seq"] = state.get("seq", 0) + 1
            else:
                time.sleep(0.05)

    def analyse():
        while not state.get("stop"):
            frame = state.get("frame")
            if frame is None:
                time.sleep(0.2); continue
            state["detecting"] = True
            try:
                pts = courtfit.auto_fit_frame(frame, calibration, court)
                if pts is not None:
                    named = {k: [float(pts[k][0]), float(pts[k][1])] for k in DBL}
                    state["live_corners"] = named
                    state["live_verdict"] = courtfit.setup_verdict(
                        frame, named, calibration, court)
                else:
                    state["live_corners"] = None
                    state["live_verdict"] = {
                        "view": {"level": "poor", "corners_visible": 0,
                                 "centrality": 0.0, "coverage": 0.0,
                                 "msg": "No court detected - aim the camera at the "
                                        "whole court, or place the overlay by hand."},
                        "angle": {"level": "idle", "msg": "Waiting for a court.",
                                  "reliable_frac": None}}
            except Exception as e:
                state["live_verdict"] = {
                    "view": {"level": "poor", "corners_visible": 0, "centrality": 0.0,
                             "coverage": 0.0, "msg": f"check failed: {e}"},
                    "angle": {"level": "idle", "msg": "-", "reliable_frac": None}}
            finally:
                state["detecting"] = False
            time.sleep(0.4)

    threading.Thread(target=grab, daemon=True).start()
    threading.Thread(target=analyse, daemon=True).start()
    return cap


def auto_fit(frame):
    """Auto-detect the court, snap it onto the lines, re-lock the shape to a real
    camera view (courtfit.auto_fit_frame — the same recipe the pipeline and the
    eval scorecards use). Returns {corner:[x,y]} or None if no lock."""
    from swingvision import calibration, court, courtfit
    use = courtfit.auto_fit_frame(frame, calibration, court)
    if use is None:
        return None
    # auto_fit_frame locks roll-FROZEN (it is shared with the multi-frame consensus
    # candidate path, where the confidence law needs roll=0). This seed is the
    # tool's own trusted opening display, so re-lock it roll-ALLOWED and polish it
    # onto the paint: a mildly rolled phone/fence camera then opens already ON the
    # lines instead of a few px off (see lock_shape for the roll rationale).
    h, w = frame.shape[:2]
    try:
        locked, _moved, _fit = courtfit.lock_quad(
            use, calibration, court, w, h,
            dt=courtfit.line_distance_map(frame, calibration), allow_roll=True)
        use = locked
    except Exception:
        pass   # keep the roll-frozen seed if the trusted re-lock can't fit

    # REFUSE A SEED THE DETECTOR DOES NOT BELIEVE.
    # `verify_court` samples real pixels along the projected lines and reports how
    # much of the template lands on actual white paint.
    #
    # MEASURED, AND IT IS A WEAK GUARD: on the 10 hand-calibrated clips in this
    # pool, comparing each single-frame seed against the corners a human then
    # placed, 2 produced no lock and 5 were 174-438 px out — a WRONG RUNG, the
    # service line taken for the baseline or the court next door. Coverage does
    # not separate those: the 221 px-wrong seed scored 61% on paint and a
    # 122 px-wrong one scored 94%, because a wrong-rung court still lies along
    # real white lines. So this catches only a seed that is on nothing at all.
    # The check that DOES separate them is multi-frame consensus (>=6 of 8
    # agreeing frames, Session H part 2), which a single frame cannot run — which
    # is why gallery mode gates seeding on the consensus verdict instead.
    try:
        H = calibration.compute_homography(
            [court.LANDMARKS[k] for k in DBL], [use[k] for k in DBL])
        chk = calibration.verify_court(frame, H)
        cov = float(getattr(chk, "coverage", 1.0))
        if cov < MIN_SEED_COVERAGE:
            print(f"[setup] auto-fit REFUSED: only {cov * 100:.0f}% of the court "
                  f"template lands on white paint (need "
                  f"{MIN_SEED_COVERAGE * 100:.0f}%). Opening on a plain overlay — "
                  f"dragging a fresh rectangle beats correcting a wrong court.")
            return None
        print(f"[setup] auto-fit court ({cov * 100:.0f}% of the template on paint)")
        return {k: [float(use[k][0]), float(use[k][1])] for k in DBL}
    except Exception:
        pass   # verifier unavailable: fall through and show the seed as before
    print("[setup] auto-fit court")
    return {k: [float(use[k][0]), float(use[k][1])] for k in DBL}

PAGE = r"""<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Court Setup</title>
<style>
  :root{--bg:#0e141b;--panel:#161f2a;--ink:#e7edf3;--muted:#93a2b3;--line:#26323f;
    --accent:#c8e04a;--ok:#34d17c;--warn:#ffb84a;}
  *{box-sizing:border-box} html,body{margin:0}
  body{background:var(--bg);color:var(--ink);font:15px/1.5 ui-sans-serif,system-ui,Segoe UI,Roboto,sans-serif;}
  header{display:flex;flex-wrap:wrap;align-items:center;gap:10px;padding:12px 16px;
    border-bottom:1px solid var(--line);position:sticky;top:0;background:var(--bg);z-index:5}
  h1{font-size:15px;margin:0 12px 0 0;font-weight:700;letter-spacing:-.01em}
  button{font:inherit;font-weight:600;color:var(--ink);background:var(--panel);
    border:1px solid var(--line);border-radius:9px;padding:8px 13px;cursor:pointer}
  button:hover{border-color:var(--accent)} button:disabled{opacity:.5;cursor:default}
  button.primary{background:var(--accent);color:#182200;border-color:var(--accent)}
  button.ok{border-color:var(--ok);color:var(--ok)}
  .sp{flex:1}
  #status{padding:8px 16px;color:var(--muted);font-size:13.5px;min-height:20px}
  #status b{color:var(--ink)} #status .g{color:var(--ok)} #status .w{color:var(--warn)}
  .wrap{padding:8px 16px 40px;overflow:auto}
  canvas{background:#0c0e12;border-radius:10px;touch-action:none;cursor:grab}
  canvas.grabbing{cursor:grabbing}
  kbd{background:var(--panel);border:1px solid var(--line);border-bottom-width:2px;
    border-radius:5px;padding:0 5px;font:12px ui-monospace,Menlo,Consolas,monospace}
  /* Clip strip: every court in the queue, always visible, one click apart. */
  #clips{display:flex;flex-wrap:wrap;gap:6px;padding:10px 16px;
    border-bottom:1px solid var(--line);background:#111823}
  #clips button{padding:6px 11px;border-radius:8px;font-size:13px;font-weight:600}
  #clips button.on{background:var(--accent);color:#182200;border-color:var(--accent)}
  #clips button.done{border-color:var(--ok);color:var(--ok)}
  #clips button.done.on{background:var(--ok);color:#04220f;border-color:var(--ok)}
  #clips .lbl{color:var(--muted);font-size:12.5px;align-self:center;margin-right:4px}
  .hint{color:var(--muted);font-size:12.5px;padding:0 16px 10px}
  /* Setup checks: view (framing) + angle (camera height) */
  #checks{display:flex;flex-wrap:wrap;gap:10px;padding:2px 16px 10px}
  .chk{flex:1 1 320px;display:flex;gap:10px;align-items:flex-start;background:var(--panel);
    border:1px solid var(--line);border-left-width:4px;border-radius:10px;padding:10px 12px}
  .chk .ico{font-size:15px;line-height:1.35}
  .chk .ttl{font-weight:700;font-size:13px;letter-spacing:.01em}
  .chk .txt{color:var(--muted);font-size:12.5px}
  .chk.good{border-left-color:var(--ok)} .chk.good .ico{color:var(--ok)}
  .chk.warn{border-left-color:var(--warn)} .chk.warn .ico{color:var(--warn)}
  .chk.poor{border-left-color:#ff6b5a} .chk.poor .ico{color:#ff6b5a}
  .chk.idle{border-left-color:var(--line)}
  .meter{height:5px;border-radius:3px;background:#0c1219;margin-top:7px;overflow:hidden}
  .meter i{display:block;height:100%;background:var(--accent);border-radius:3px}
  /* The guided flow. The framing question is asked BEFORE the corners are
     placed, because that is the only moment a low camera is still fixable; the
     confirm list is the only thing that produces `confirmed_by_user`. */
  #framing,#confirm{margin:8px 16px;padding:12px 14px;background:#141a22;
    border:1px solid var(--line);border-radius:9px}
  #framing .q,#confirm .q{font-weight:700;margin-bottom:5px}
  .qnote{color:var(--muted);font-size:12.5px;line-height:1.5}
  .qrow{display:flex;gap:8px;flex-wrap:wrap;margin-top:9px}
  .fb{background:#0c1219;border:1px solid var(--line);color:var(--muted);
    border-radius:999px;padding:6px 12px;font-size:12.5px;cursor:pointer}
  .fb.on{background:var(--accent);color:#101418;border-color:var(--accent);font-weight:700}
  .qnotice{margin-top:10px;padding:10px 12px;border-radius:8px;
    background:rgba(227,160,8,0.1);border-left:3px solid #e3a008;font-size:12.5px;line-height:1.5}
  #cbox label{display:grid;grid-template-columns:20px 150px 1fr;gap:8px;
    align-items:baseline;padding:7px 0;border-top:1px solid var(--line);cursor:pointer}
  #cbox .nm{font-weight:600;font-size:12.5px}
  #cbox label.on .nm{color:var(--accent)}
</style></head><body>
<header>
  <h1>Court Setup</h1>
  <button id="auto">Auto-detect</button>
  <button id="snap" class="primary">Snap to lines</button>
  <button id="big">Bigger</button>
  <button id="small">Smaller</button>
  <button id="reset">Reset</button>
  <label style="display:flex;align-items:center;gap:6px;font-size:13.5px;cursor:pointer"
         title="ON: the court always stays a shape a real camera could see (corners re-solve together). OFF: place each corner exactly where you want it - use when a wide lens bends the real lines.">
    <input type="checkbox" id="lockchk" checked> Shape lock</label>
  <span class="sp"></span>
  <button id="save" class="ok">Save calibration</button>
</header>
<div id="clips" style="display:none"></div>
<div id="status">Drag the <b>middle</b> of the court to move it, a <b>corner</b> to reshape. Then <b>Snap to lines</b>.</div>
<div id="framing">
  <div class="q">Looking at the far end of the court: can you see the far baseline as a separate line BELOW the top of the net?</div>
  <div class="qnote">If the net covers it, you can still record and review the match &ndash; speed, bounce positions and line calls on the far half will be marked as approximate.</div>
  <div class="qrow">
    <button class="fb" data-fb="yes">Yes &ndash; I can see it below the net</button>
    <button class="fb" data-fb="no">No &ndash; the net covers it</button>
    <button class="fb on" data-fb="unsure">Not sure</button>
  </div>
  <div id="fb-notice" class="qnotice" style="display:none"></div>
</div>
<div id="confirm">
  <div class="q">Check each corner on the frame, then tick it</div>
  <div class="qnote">Only a calibration with all four corners ticked is recorded as
    <b>user-confirmed</b>. Anything else saves as <b>provisional</b> and its court
    measurements are never presented as verified.</div>
  <div id="cbox"></div>
  <div id="confirm-state" class="qnote">0 of 4 confirmed.</div>
</div>
<div id="checks">
  <div class="chk idle" id="chk-view"><div class="ico">•</div><div>
    <div class="ttl">Court view</div><div class="txt" id="view-txt">Checking the framing…</div></div></div>
  <div class="chk idle" id="chk-angle"><div class="ico">•</div><div>
    <div class="ttl">Camera angle</div><div class="txt" id="angle-txt">Checking the angle…</div>
    <div class="meter" id="angle-meter" style="display:none"><i id="angle-bar" style="width:0%"></i></div></div></div>
</div>
<div class="wrap"><canvas id="view"></canvas></div>
<div class="hint">Corners may sit outside the frame (in the dark margin) - place them where the lines would meet. <kbd>+</kbd>/<kbd>&minus;</kbd> resize &middot; arrow keys nudge.</div>
<script>
"use strict";
const $=id=>document.getElementById(id);
const view=$("view"), ctx=view.getContext("2d");
// PLAIN LANGUAGE, not landmark keys. Nobody outside this repo knows what a
// "doubles corner" is; everybody can find the outermost corner at the far end.
const CORNERS=[
  {key:"near_bl_doubles",m:[0,0],nm:"Near end, left corner",
   where:"The near end, on your left - outside the tramline."},
  {key:"near_br_doubles",m:[10.97,0],nm:"Near end, right corner",
   where:"The near end, on your right - outside the tramline."},
  {key:"far_br_doubles",m:[10.97,23.77],nm:"Far end, right corner",
   where:"The far end, on your right - where the back line meets the outside tramline."},
  {key:"far_bl_doubles",m:[0,23.77],nm:"Far end, left corner",
   where:"The far end, on your left - where the back line meets the outside tramline."}];
const KP={far_bl_doubles:[0,23.77],far_br_doubles:[10.97,23.77],near_bl_doubles:[0,0],
  near_br_doubles:[10.97,0],far_bl_singles:[1.37,23.77],near_bl_singles:[1.37,0],
  far_br_singles:[9.6,23.77],near_br_singles:[9.6,0],far_sl_left:[1.37,18.285],
  far_sl_right:[9.6,18.285],near_sl_left:[1.37,5.485],near_sl_right:[9.6,5.485],
  far_t:[5.485,18.285],near_t:[5.485,5.485]};
const LINES=[[[0,0],[10.97,0]],[[0,23.77],[10.97,23.77]],[[0,0],[0,23.77]],
  [[10.97,0],[10.97,23.77]],[[1.37,0],[1.37,23.77]],[[9.6,0],[9.6,23.77]],
  [[1.37,5.485],[9.6,5.485]],[[1.37,18.285],[9.6,18.285]],[[5.485,5.485],[5.485,18.285]]];
const NET=[[0,11.885],[10.97,11.885]];

function solveH(src,dst){const A=[],b=[];for(let i=0;i<4;i++){const[X,Y]=src[i],[u,v]=dst[i];
  A.push([X,Y,1,0,0,0,-X*u,-Y*u]);b.push(u);A.push([0,0,0,X,Y,1,-X*v,-Y*v]);b.push(v);}
  for(let c=0;c<8;c++){let p=c;for(let r=c+1;r<8;r++)if(Math.abs(A[r][c])>Math.abs(A[p][c]))p=r;
    [A[c],A[p]]=[A[p],A[c]];[b[c],b[p]]=[b[p],b[c]];if(Math.abs(A[c][c])<1e-12)return null;
    for(let r=0;r<8;r++){if(r===c)continue;const f=A[r][c]/A[c][c];
      for(let k=c;k<8;k++)A[r][k]-=f*A[c][k];b[r]-=f*b[c];}}
  const h=b.map((v,i)=>v/A[i][i]);return[[h[0],h[1],h[2]],[h[3],h[4],h[5]],[h[6],h[7],1]];}
function applyH(H,X,Y){const d=H[2][0]*X+H[2][1]*Y+1;
  return[(H[0][0]*X+H[0][1]*Y+H[0][2])/d,(H[1][0]*X+H[1][1]*Y+H[1][2])/d];}

let W=0,H=0,scale=1,padx=0,pady=0;const PAD=0.35;
let corners=[null,null,null,null], drag=null, mode=null, last=null;
const img=new Image();

function fit(){const avail=Math.max(320,(window.innerWidth||1000)-40);
  scale=Math.min(Math.max(avail/(W*(1+2*PAD)),0.1),1);
  padx=Math.round(PAD*W*scale);pady=Math.round(PAD*H*scale);
  view.width=Math.round(W*scale)+2*padx;view.height=Math.round(H*scale)+2*pady;}
function toImg(e){const r=view.getBoundingClientRect();
  const cx=(e.clientX-r.left)*view.width/r.width,cy=(e.clientY-r.top)*view.height/r.height;
  return[(cx-padx)/scale,(cy-pady)/scale];}
function centroid(){let x=0,y=0;for(const c of corners){x+=c[0];y+=c[1];}return[x/4,y/4];}
function isOff(c){return c[0]<0||c[1]<0||c[0]>W||c[1]>H;}
function inQuad(x,y){let hit=false;for(let i=0,j=3;i<4;j=i++){const[xi,yi]=corners[i],[xj,yj]=corners[j];
  if(((yi>y)!=(yj>y))&&(x<(xj-xi)*(y-yi)/(yj-yi)+xi))hit=!hit;}return hit;}
function nearest(x,y){let best=null,bd=12/scale;for(let i=0;i<4;i++){
  const d=Math.hypot(corners[i][0]-x,corners[i][1]-y);if(d<bd){bd=d;best=i;}}return best;}

function defaultCourt(){corners=[[0.14*W,0.98*H],[0.86*W,0.98*H],[0.72*W,0.30*H],[0.28*W,0.30*H]];}

function render(){const s=scale;
  ctx.fillStyle="#0c0e12";ctx.fillRect(0,0,view.width,view.height);
  ctx.drawImage(img,padx,pady,Math.round(W*s),Math.round(H*s));
  ctx.strokeStyle="rgba(255,255,255,.28)";ctx.lineWidth=1;
  ctx.strokeRect(padx+.5,pady+.5,Math.round(W*s),Math.round(H*s));
  const P=(X,Y,Hm)=>{const p=applyH(Hm,X,Y);return[padx+p[0]*s,pady+p[1]*s];};
  const Hm=solveH(CORNERS.map(c=>c.m),corners);
  if(Hm){ctx.lineWidth=2;ctx.strokeStyle="rgba(120,220,160,.95)";
    for(const[a,b]of LINES){const p=P(a[0],a[1],Hm),q=P(b[0],b[1],Hm);
      ctx.beginPath();ctx.moveTo(p[0],p[1]);ctx.lineTo(q[0],q[1]);ctx.stroke();}
    ctx.strokeStyle="rgba(255,210,120,.95)";const n0=P(NET[0][0],NET[0][1],Hm),n1=P(NET[1][0],NET[1][1],Hm);
    ctx.beginPath();ctx.moveTo(n0[0],n0[1]);ctx.lineTo(n1[0],n1[1]);ctx.stroke();
    ctx.fillStyle="rgba(140,200,255,.9)";for(const k in KP){const p=P(KP[k][0],KP[k][1],Hm);
      ctx.beginPath();ctx.arc(p[0],p[1],2.3,0,7);ctx.fill();}}
  for(let i=0;i<4;i++){const c=corners[i],x=padx+c[0]*s,y=pady+c[1]*s,off=isOff(c);
    ctx.lineWidth=off?2.5:2;ctx.strokeStyle=off?"#ff9c4a":"#14171c";ctx.fillStyle="#ffd24a";
    ctx.beginPath();ctx.arc(x,y,7,0,7);if(!off)ctx.fill();ctx.stroke();
    ctx.fillStyle=off?"#ff9c4a":"#14171c";ctx.font="bold 11px system-ui";
    ctx.fillText(String(i+1)+(off?"*":""),x-3,off?y-11:y+4);}}

function setStatus(msg){$("status").innerHTML=msg;}
function corDict(){const o={};CORNERS.forEach((c,i)=>o[c.key]=[corners[i][0],corners[i][1]]);return o;}
function setDict(o){corners=CORNERS.map(c=>o[c.key].slice());}

view.addEventListener("pointerdown",e=>{const[x,y]=toImg(e);const h=nearest(x,y);
  if(h!==null){mode="corner";drag=h;}else if(inQuad(x,y)){mode="move";last=[x,y];view.classList.add("grabbing");}
  view.setPointerCapture(e.pointerId);});
view.addEventListener("pointermove",e=>{if(!mode)return;const[x,y]=toImg(e);
  if(mode==="corner"){corners[drag]=[x,y];}
  else{const dx=x-last[0],dy=y-last[1];for(const c of corners){c[0]+=dx;c[1]+=dy;}last=[x,y];}
  render();});
const lockOn=()=>$("lockchk").checked;
async function regularize(){const r=await api("/api/regularize",{corners:corDict()});
  if(r.corners){setDict(r.corners);render();
    if(r.moved>3)setStatus('Shape locked to a <b>real camera view</b> (adjusted '+r.moved.toFixed(0)+'px). Courts can’t warp — drag corners to steer, the shape stays legal. Untick <b>Shape lock</b> to place corners exactly.');}}
function endDrag(){const wasCorner=(mode==="corner");mode=null;drag=null;
  view.classList.remove("grabbing");
  if(wasCorner&&lockOn())regularize().then(scheduleChecks);else scheduleChecks();}
view.addEventListener("pointerup",endDrag);view.addEventListener("pointercancel",endDrag);
$("lockchk").addEventListener("change",()=>{
  if(lockOn()){setStatus("Shape lock ON — corners re-solve together as one rigid court.");regularize();}
  else setStatus("Shape lock <b>OFF</b> — each corner stays exactly where you put it (for lenses that bend the lines). Save will keep your exact points.");});

function scaleBy(f){const[cx,cy]=centroid();for(const c of corners){c[0]=cx+(c[0]-cx)*f;c[1]=cy+(c[1]-cy)*f;}render();scheduleChecks();}
$("big").onclick=()=>scaleBy(1.06);$("small").onclick=()=>scaleBy(1/1.06);
$("reset").onclick=()=>{defaultCourt();render();scheduleChecks();setStatus("Overlay reset. Drag it over the court, then <b>Snap</b>.");};
document.addEventListener("keydown",e=>{const N={ArrowLeft:[-2,0],ArrowRight:[2,0],ArrowUp:[0,-2],ArrowDown:[0,2]}[e.key];
  if(N){for(const c of corners){c[0]+=N[0];c[1]+=N[1];}render();scheduleChecks();e.preventDefault();}
  else if(e.key==="+"||e.key==="=")scaleBy(1.06);else if(e.key==="-")scaleBy(1/1.06);});

async function api(path,body){const r=await fetch(path,{method:"POST",
  headers:{"Content-Type":"application/json"},body:JSON.stringify(body||{})});return r.json();}

// --- Setup checks: is the court properly in VIEW, and is the ANGLE good enough?
const ICO={good:"✓",warn:"!",poor:"✕",idle:"•"};
function setChk(el,txtEl,level,text){
  el.className="chk "+level; el.querySelector(".ico").textContent=ICO[level]||"•";
  txtEl.textContent=text;}
let checkSeq=0;
async function refreshChecks(){
  const my=++checkSeq;                      // ignore results from stale drags
  const r=await api("/api/framing",{corners:corDict()});
  if(my!==checkSeq||!r||r.error)return;
  setChk($("chk-view"),$("view-txt"),r.view.level,
    r.view.msg+"  ("+r.view.corners_visible+"/4 corners in frame, lines "+
    Math.round(r.view.coverage*100)+"%)");
  setChk($("chk-angle"),$("angle-txt"),r.angle.level,r.angle.msg);
  const m=$("angle-meter"),b=$("angle-bar");
  if(r.angle.reliable_frac!=null){m.style.display="block";
    b.style.width=Math.round(r.angle.reliable_frac*100)+"%";
    b.style.background=r.angle.level==="good"?"var(--ok)":
      (r.angle.level==="warn"?"var(--warn)":"#ff6b5a");}
  else m.style.display="none";}
let checkTimer=null;
// Every corner mutation in this page funnels through scheduleChecks, so this is
// the one place a moved corner has to un-confirm the placement. Hooking it here
// rather than in each handler is deliberate: a new handler added later inherits
// the invalidation instead of forgetting it.
function scheduleChecks(){unconfirm();clearTimeout(checkTimer);checkTimer=setTimeout(refreshChecks,220);}
$("auto").onclick=async()=>{setStatus("Auto-detecting the court...");$("auto").disabled=true;
  const r=await api("/api/autodetect",{});$("auto").disabled=false;
  if(r.corners){setDict(r.corners);render();scheduleChecks();setStatus('Auto-detected (line support '+(r.score*100|0)+'%). If it grabbed the wrong court, <b>drag it</b> onto the right one, then <b>Snap</b>.');}
  else setStatus('<span class="w">Auto-detect couldn’t lock a court</span> - drag the overlay onto it by hand, then <b>Snap</b>.');};
$("snap").onclick=async()=>{setStatus("Snapping to the lines...");$("snap").disabled=true;
  const r=await api("/api/snap",{corners:corDict()});$("snap").disabled=false;
  if(r.corners){setDict(r.corners);render();scheduleChecks();
    setStatus(r.snapped?'<span class="g">Snapped onto the '+(r.mode==="clay"?'clay':'white')+' lines</span> (coverage '+(r.coverage*100|0)+'%). Adjust if needed, then <b>Save</b>.'
      :'<span class="w">Snap didn’t improve the fit</span> (coverage '+(r.coverage*100|0)+'%) - nudge it closer and try again, or place corners by hand.');}};
// --- the guided flow -------------------------------------------------------
// FEATURE 1: the framing question. Asked before anything is measured, because
// that is the only moment a low camera can still be fixed - and because there is
// no honest automatic answer in a preview, where no homography exists yet.
let FB=null;                       // true | false | null (unsure / not asked)
const FB_OVERLAP_TITLE="The net hides the far baseline";
const FB_OVERLAP_BODY="You can still record and review this match. Court "+
  "measurements may be less reliable, especially on the far half. Raising the "+
  "phone gives better results.";
document.querySelectorAll(".fb").forEach(b=>b.onclick=()=>{
  document.querySelectorAll(".fb").forEach(o=>o.classList.remove("on"));
  b.classList.add("on");
  FB=b.dataset.fb==="yes"?true:(b.dataset.fb==="no"?false:null);
  const n=$("fb-notice");
  if(FB===false){n.style.display="";
    n.innerHTML="<b>"+FB_OVERLAP_TITLE+"</b><br>"+FB_OVERLAP_BODY+
      "<br><br>✓ Continue with this setup – keep going, set the corners "+
      "below and save. The match is still analysed; it is simply marked as having "+
      "limited court accuracy.";}
  else n.style.display="none";});

// FEATURE 2: confirm the four corners by name. This is the ONLY thing that
// writes `confirmed_by_user`, and therefore the only thing that makes a
// calibration `user_confirmed` instead of `provisional` downstream. `_exact`
// never meant this and was read as if it did (trap T26).
let CONFIRMED={};
function renderConfirm(){
  const box=$("cbox");
  if(!box.dataset.built){
    box.innerHTML=CORNERS.map(c=>
      '<label data-k="'+c.key+'"><input type="checkbox" data-k="'+c.key+'">'+
      '<span class="nm">'+c.nm+'</span><span class="qnote">'+c.where+'</span></label>').join("");
    box.dataset.built="1";
    box.querySelectorAll("input").forEach(i=>i.onchange=()=>{
      CONFIRMED[i.dataset.k]=i.checked;renderConfirm();});}
  box.querySelectorAll("input").forEach(i=>{i.checked=!!CONFIRMED[i.dataset.k];
    i.closest("label").classList.toggle("on",!!CONFIRMED[i.dataset.k]);});
  const n=CORNERS.filter(c=>CONFIRMED[c.key]).length;
  $("confirm-state").innerHTML = n===4
    ? '<span class="g">✓ All four corners confirmed - saving records this as a '+
      'user-confirmed calibration.</span>'
    : n+' of 4 confirmed. You can still save: the calibration is then recorded as '+
      '<b>provisional</b>, and court measurements are not presented as verified.';
  $("save").textContent = n===4 ? "Save confirmed calibration" : "Save as provisional";}

// ANY edit to a corner un-confirms every corner. A confirmation is a claim about
// one specific placement, and carrying it across an edit is how a stale
// attestation ends up in a file.
function unconfirm(){if(Object.keys(CONFIRMED).length){CONFIRMED={};renderConfirm();}}
renderConfirm();

$("save").onclick=async()=>{const r=await api("/api/save",{corners:corDict(),lock:lockOn(),
    confirmed:CORNERS.every(c=>CONFIRMED[c.key]),
    confirmed_corners:CORNERS.filter(c=>CONFIRMED[c.key]).map(c=>c.key),
    far_baseline:FB});
  if(r.ok){if(r.corners){setDict(r.corners);render();}
    setStatus('<span class="g">Saved</span> to <b>'+r.path+'</b>'+
      (r.exact?' (exact corners - your points, untouched)':
       (r.moved>3?' (shape locked to a real camera view, adjusted '+r.moved.toFixed(0)+'px)':''))+
      (r.confirmation_dropped
        ? ' <span class="w">The shape lock moved a corner you had confirmed by '+
          r.moved.toFixed(0)+'px, so the confirmation was DROPPED and this saved as '+
          'provisional - check the corners and confirm again.</span>'
        : (r.confirmed?' <span class="g">(user-confirmed)</span>':' (provisional)'))+
      ' - use it with <kbd>run.py analyze --keypoints</kbd>.');
    if(r.confirmation_dropped){CONFIRMED={};renderConfirm();}
    // Tick this clip in the strip, then step to the next unsaved one so a queue
    // of ten is Snap-Save-Snap-Save rather than Snap-Save-find-the-next-button.
    await refreshClips();
    const next=CLIPS.findIndex((c,i)=>!c.done&&i>IDX);
    const any=next>=0?next:CLIPS.findIndex(c=>!c.done);
    if(any>=0)loadClip(any);
    else setStatus('<span class="g">All '+CLIPS.length+
      ' courts saved.</span> You can close this tab.');}
  else setStatus('Save failed.');};

// --- LIVE mode: keep the picture and the verdict current while you aim ---
let LIVE=false, liveTimer=null, liveBusy=false;
function startLive(){
  setStatus('<b>LIVE</b> - aim the camera at the whole court. The checks below update as you move it; press <b>Save</b> once both are green.');
  const tick=async()=>{
    if(!liveBusy){liveBusy=true;
      const im=new Image();
      im.onload=()=>{ctx.drawImage&&(img.src=im.src);liveBusy=false;};
      im.onerror=()=>{liveBusy=false;};
      im.src="/frame.jpg?t="+Date.now();          // bust the cache: newest frame
    }
    try{const r=await (await fetch("/api/live")).json();
      if(r.corners){setDict(r.corners);render();}
      if(r.verdict){
        setChk($("chk-view"),$("view-txt"),r.verdict.view.level,
          r.verdict.view.msg+"  ("+r.verdict.view.corners_visible+"/4 corners in frame)");
        setChk($("chk-angle"),$("angle-txt"),r.verdict.angle.level,r.verdict.angle.msg);
        const m=$("angle-meter"),b=$("angle-bar");
        if(r.verdict.angle.reliable_frac!=null){m.style.display="block";
          b.style.width=Math.round(r.verdict.angle.reliable_frac*100)+"%";
          b.style.background=r.verdict.angle.level==="good"?"var(--ok)":
            (r.verdict.angle.level==="warn"?"var(--warn)":"#ff6b5a");}
        else m.style.display="none";}
    }catch(e){}
  };
  tick(); liveTimer=setInterval(tick,700);
}
img.onload=()=>{if(!W)return;render();};

// ---- clip strip -------------------------------------------------------------
// Every court in the queue is one click away and stays on screen. Loading a clip
// swaps the frame in place: no restart, no new port, no reload.
let CLIPS=[], IDX=0;
function paintClips(){
  const box=$("clips");
  if(!CLIPS.length){box.style.display="none";return;}
  box.style.display="flex";
  const nDone=CLIPS.filter(c=>c.done).length;
  box.innerHTML='<span class="lbl">'+nDone+' of '+CLIPS.length+' saved</span>';
  CLIPS.forEach((c,i)=>{
    const b=document.createElement("button");
    b.textContent=(c.done?"✓ ":"")+c.name;
    b.className=(c.done?"done":"")+(i===IDX?" on":"");
    b.onclick=()=>loadClip(i);
    box.appendChild(b);
  });
}
function refreshClips(){
  return fetch("/api/clips").then(r=>r.json())
    .then(d=>{CLIPS=d.clips||[];IDX=d.idx||0;paintClips();});
}
function loadClip(i){
  setStatus("Loading <b>"+(CLIPS[i]||{}).name+"</b>…");
  return fetch("/api/select",{method:"POST",body:String(i)}).then(r=>r.json())
    .then(d=>{
      if(!d.ok){setStatus('<span class="w">Could not open that clip.</span>');return;}
      IDX=d.idx;
      return fetch("/api/meta").then(r=>r.json()).then(m=>{
        W=m.w;H=m.h;
        img.onload=()=>{fit();
          if(m.seed){setDict(m.seed);
            setStatus('<b>'+d.clip+'</b> — auto-seeded. Drag to fit, then <b>Snap</b>.');}
          else{defaultCourt();
            setStatus('<b>'+d.clip+'</b> — drag the court onto the lines, then <b>Snap</b>.');}
          render(); img.onload=()=>render(); refreshChecks();};
        img.src="/frame.jpg?t="+Date.now();   // per-clip frame; never reuse the cache
        paintClips();
      });
    });
}

fetch("/api/meta").then(r=>r.json()).then(m=>{W=m.w;H=m.h;LIVE=!!m.live;
  img.onload=()=>{fit();
    if(m.seed){setDict(m.seed);setStatus('Auto-seeded a court - <b>drag</b> to fit, then <b>Snap</b>.');}
    else if(!LIVE){defaultCourt();setStatus('Drag the <b>middle</b> of the court to move it, a <b>corner</b> to reshape. Then <b>Snap to lines</b>.');}
    else defaultCourt();
    render();
    img.onload=()=>render();          // later frames just repaint
    if(LIVE)startLive(); else refreshChecks();};
  img.src="/frame.jpg";});
refreshClips();
window.addEventListener("resize",()=>{if(W){fit();render();}});
</script></body></html>"""


PLACED_BY_UNKNOWN = "unattributed"


def provenance_block(state, shape_lock: bool, moved_px: float,
                     confirmed: bool = False, confirmed_corners=None,
                     far_baseline: bool | None = None) -> dict:
    """The `_provenance` block stamped onto every save.

    WHY THIS EXISTS. Until 2026-09-09 a saved calibration recorded NOTHING about
    where its corners came from. `_exact` was read downstream (eval/run_refs.py)
    as "a human deliberately placed these", but it only ever meant "the browser's
    Shape lock checkbox was unchecked" — an agent driving this tool with the box
    unticked produced a file indistinguishable from a human's. Worse, the
    shape-lock-ON path threw `moved_px` away, so there was no record of how far
    the solver had shifted the placement it was handed.

    `placed_by` is honestly `"unattributed"`: this tool serves a localhost page
    and cannot tell a person's mouse from an agent's HTTP POST. It is a slot for
    a human or a commit to fill in, NOT a claim. Do not read a missing or
    "unattributed" value as "human".

    `confirmed_by_user` IS the claim `_exact` was wrongly read as. It is true only
    when the caller ticked all four corners by name in the confirm step, and it is
    the ONE thing that makes a downstream calibration `user_confirmed` rather than
    `provisional` (backend/swingvision/setup_state.py). It says an explicit
    confirmation happened; combined with `placed_by` still reading "unattributed"
    it does NOT say a human was at the keyboard, because this tool still cannot
    know that. The two fields answer different questions and neither is allowed to
    stand in for the other.

    `far_baseline_visible` carries the recorder's own answer to
    setup_state.FAR_BASELINE_QUESTION, so a clip whose far baseline is out of
    frame entirely - and therefore has no measurable clearance - can still say
    something honest about its framing.
    """
    src = state.get("source") or {"kind": "unknown"}
    return {
        "placed_by": PLACED_BY_UNKNOWN,
        "tool": "tools/court_setup_server.py",
        "shape_lock": bool(shape_lock),
        "moved_px": float(moved_px),
        "confirmed_by_user": bool(confirmed),
        "confirmed_corners": list(confirmed_corners or []) if confirmed else [],
        "far_baseline_visible": (None if far_baseline is None
                                 else bool(far_baseline)),
        "saved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": src,
    }


def source_desc(args) -> dict:
    """What frame the corners were placed on, as far as the tool can honestly say.

    Only `--frame` and `--gallery` identify a single image on disk. `--clip` picks
    a middle frame out of a directory, so the directory is recorded but not which
    jpg. `--video` DEFAULT is a temporal median clean plate over ~80 frames — there
    IS no single source frame, and inventing a frame index would be a lie, so
    `frame` stays null and the plate is declared. `--camera` has no file at all.
    """
    if getattr(args, "frame", None):
        return {"kind": "image", "path": str(args.frame)}
    if getattr(args, "clip", None):
        return {"kind": "gold_clip_middle_frame", "clip": str(args.clip),
                "frame": None,
                "note": "middle jpg of data/gold/frames/<clip>; index not recorded"}
    if getattr(args, "video", None):
        plate = not getattr(args, "no_plate", False)
        return {"kind": "video_clean_plate" if plate else "video_single_frame",
                "video": str(args.video), "frame": None,
                "note": ("temporal median over ~80 frames - no single source frame"
                         if plate else "middle frame; index not recorded")}
    if getattr(args, "camera", None) is not None:
        return {"kind": "live_camera", "index": int(args.camera), "frame": None,
                "note": "live stream - the frame is not persisted anywhere"}
    return {"kind": "unknown"}


def save_text(named: dict, exact: bool, provenance: dict | None = None) -> str:
    """The exact JSON text a save writes.

    CONTRACT (pinned by backend/tests/test_court_setup_save_provenance.py): the
    four corner entries serialise byte-for-byte as they did before provenance
    existed. `_exact` and `_provenance` are appended AFTER them, so removing
    `_provenance` from the parsed dict and re-dumping reproduces the old file
    character for character. Never insert a key ahead of the corners.
    """
    data = dict(named)
    if exact:
        data["_exact"] = True
    if provenance is not None:
        data["_provenance"] = provenance
    return json.dumps(data, indent=2)


def gallery_list(state):
    """[{name, done}] for the clip strip. `done` is read from disk every time so
    a save made in this session, or one made last week, look identical."""
    out = []
    for c in state.get("gallery") or []:
        p = Path(c["out"])
        out.append({"name": c["name"], "done": p.is_file(),
                    "size": p.stat().st_size if p.is_file() else 0})
    return out


def select_clip(state, idx: int):
    """Point the editor at gallery[idx]: its frame, its output path, its seed."""
    import cv2

    g = state.get("gallery") or []
    if not (0 <= idx < len(g)):
        return False
    c = g[idx]
    frame = cv2.imread(str(c["image"]))
    if frame is None:
        return False
    state["frame"] = frame
    state["out"] = str(c["out"])
    state["clip_name"] = c["name"]
    # Gallery is the ONE mode that knows exactly which image is on screen.
    state["source"] = {"kind": "gallery_image", "path": str(c["image"])}
    state["idx"] = idx
    state["static_mask"] = None
    # Bump the frame counter so the distance-to-line map, which is cached per
    # frame, is rebuilt for the new clip instead of snapping to the old one's.
    state["seq"] = state.get("seq", 0) + 1
    # If this clip was calibrated before, reopen it where it was left rather
    # than re-detecting over the top of a human's placement.
    prev = Path(c["out"])
    if prev.is_file():
        try:
            d = json.loads(prev.read_text(encoding="utf-8"))
            pts = {k: v for k, v in d.items() if not k.startswith("_")}
            if all(k in pts for k in DBL):
                state["seed"] = {k: [float(pts[k][0]), float(pts[k][1])] for k in DBL}
                return True
        except (json.JSONDecodeError, OSError, TypeError, ValueError, KeyError):
            pass
    # Seed ONLY when multi-frame consensus accepted this clip's court.
    # A single-frame seed was measured at 174-438 px out on 5 of 10 clips
    # here, and dragging a wrong court into place is more work than dragging
    # a fresh rectangle. Consensus is the project's own bar for "this court
    # is real"; below it, show nothing and let the user place it.
    if c.get("seed_ok"):
        state["seed"] = auto_fit(frame)
    else:
        state["seed"] = None
        print(f"[setup] {c['name']}: auto-detect did not reach consensus on "
              f"this clip — opening on a plain overlay rather than a guess.")
    return True


def build_handler(state):
    import cv2
    import numpy as np
    from swingvision import calibration, court
    from swingvision import courtfit as ad

    # LIVE mode (--camera): the frame is whatever the camera is seeing right now,
    # so nothing can be precomputed. STATIC mode: one frame/plate, computed once.
    live = state.get("live", False)

    def cur():
        """The frame to work on: the newest camera frame, or the static plate."""
        return state["frame"]

    def dims():
        """(w, h) of the CURRENT frame.

        Read per call, not captured once: in gallery mode the frame changes when
        another clip is picked, and clips differ in size. A stale w/h here would
        silently shift every corner the shape-lock solves.
        """
        fh, fw = state["frame"].shape[:2]
        return fw, fh

    # Snap's polish samples this distance-to-line map. Build it from the plate's
    # ridge mask with any MTI-flagged moving pixels removed, so a lingering player
    # ghost can't pull the polish off the real paint (temporal filtering, cont.).
    # GUARDED: the MTI mask is applied only if it keeps most of the line signal —
    # if it would erase the paint (background motion leaking in), it is ignored,
    # since the median plate already removed the movers. MTI can only help here.
    def _ridge(f):
        m = calibration.line_ridge_mask(f)
        static = state.get("static_mask")
        if static is not None and static.shape == m.shape:
            masked = cv2.bitwise_and(m, static)
            total = int((m > 0).sum())
            if total and int((masked > 0).sum()) >= 0.60 * total:
                return masked      # MTI trimmed a mover, kept the lines -> use it
        return m                   # MTI too aggressive (or absent) -> plate only

    _dt_cache = {}

    def dt_map():
        """Distance-to-line map for the current frame (cached per frame in live)."""
        key = state.get("seq", 0)
        if key not in _dt_cache:
            _dt_cache.clear()
            _dt_cache[key] = ad.line_distance_map(cur(), calibration, mask_fn=_ridge)
        return _dt_cache[key]

    def corners_named(d):
        return {k: [float(d[k][0]), float(d[k][1])] for k in DBL}

    def lock_shape(named, use_dt=False):
        """Closest physical camera view of the quad -> (corners, moved_px).

        TRUSTED path (allow_roll=True): the user placed/snapped these corners, so
        the camera fit may use its bounded roll DOF. Phones and fence clips are
        only ROUGHLY level - forcing roll=0 takes a correctly-snapped overlay and
        shoves it OFF the paint (measured: ~1.6px at 1deg, ~5px at 2deg, ~10px at
        3deg of camera roll). This mirrors courtfit.shape_lock and
        pipeline.calibrate_video; only the auto-detect CANDIDATE search keeps roll
        frozen (see courtfit.cam_fit_quad) - a different regime, don't confuse them."""
        w_, h_ = dims()
        locked, moved, _fit = ad.lock_quad(named, calibration, court, w_, h_,
                                           dt=dt_map() if use_dt else None,
                                           allow_roll=True)
        return locked, moved

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _send(self, code, body, ctype="application/json"):
            data = body if isinstance(body, bytes) else json.dumps(body).encode()
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if self.path == "/" or self.path.startswith("/index"):
                self._send(200, PAGE.encode(), "text/html; charset=utf-8")
            elif self.path.startswith("/frame.jpg"):
                ok, buf = cv2.imencode(".jpg", cur())
                self._send(200, buf.tobytes(), "image/jpeg")
            elif self.path == "/api/meta":
                w_, h_ = dims()
                self._send(200, {"w": w_, "h": h_, "seed": state.get("seed"),
                                 "live": bool(live),
                                 "clip": state.get("clip_name")})
            elif self.path == "/api/clips":
                self._send(200, {"clips": gallery_list(state),
                                 "idx": state.get("idx", 0)})
            elif self.path.startswith("/api/live"):
                # Live framing guide: the newest auto-detected court + verdict,
                # produced by the background worker (never blocks the browser).
                self._send(200, {"seq": state.get("seq", 0),
                                 "corners": state.get("live_corners"),
                                 "verdict": state.get("live_verdict"),
                                 "detecting": bool(state.get("detecting"))})
            else:
                self._send(404, {"error": "not found"})

        def _body(self):
            n = int(self.headers.get("Content-Length", 0))
            return json.loads(self.rfile.read(n) or b"{}")

        def do_POST(self):
            if self.path == "/api/select":
                n = int(self.rfile.read(
                    int(self.headers.get("Content-Length", 0)) or 0)
                    .decode() or 0) if self.headers.get("Content-Length") else 0
                ok = select_clip(state, n)
                _dt_cache.clear()
                self._send(200 if ok else 400,
                           {"ok": ok, "idx": state.get("idx", 0),
                            "clip": state.get("clip_name")})
                return
            if self.path == "/api/meta":
                self._send(200, {"w": w, "h": h, "seed": state.get("seed")})
            elif self.path == "/api/autodetect":
                res = ad.autodetect(cur(), calibration, court)
                if res is None:
                    self._send(200, {"corners": None})
                else:
                    Hd, score, ref = res
                    self._send(200, {"corners": corners_named(ref), "score": float(score)})
            elif self.path == "/api/snap":
                named = corners_named(self._body()["corners"])
                # Interactive snap: refine from wherever the user placed it and
                # keep any improvement (min_coverage=0 -> no absolute gate; the
                # user is looking at the result). snap_court owns the
                # white-then-clay retry policy; wider basin than the pipeline.
                # resolvability_weight: weight the fit by measurement precision so
                # the well-resolved near/mid court (service boxes, near baseline,
                # sidelines) drives angle + depth and a crushed/horizon-grazing far
                # court can't drag it off. This is the interactive path (the user
                # confirms by eye); the automatic pipeline stays equal-weight.
                _Hs, out, snapped, tag, c1 = ad.snap_court(
                    cur(), named, calibration, court,
                    min_coverage=0.0, max_move_px=60.0, resolvability_weight=True)
                use = out if all(k in out for k in DBL) else named
                # The corner-snap moves 4 corners independently — re-lock to a
                # physical camera view (with the paint polish) before returning.
                use, _ = lock_shape(use, use_dt=True)
                self._send(200, {"corners": corners_named(use),
                                 "mode": "clay" if tag == "snap-clay" else "white",
                                 "snapped": bool(snapped), "coverage": float(c1)})
            elif self.path == "/api/framing":
                # SwingVision-style setup check: is the court properly in VIEW,
                # and is the camera ANGLE good enough to measure it?
                named = corners_named(self._body()["corners"])
                try:
                    self._send(200, ad.setup_verdict(cur(), named, calibration, court))
                except Exception as e:
                    self._send(200, {"error": str(e)})
            elif self.path == "/api/regularize":
                # After a corner drag: keep the user's steering but resolve the
                # whole overlay as a rigid regulation court seen from a camera.
                named = corners_named(self._body()["corners"])
                locked, moved = lock_shape(named, use_dt=False)
                self._send(200, {"corners": corners_named(locked), "moved": float(moved)})
            elif self.path == "/api/save":
                body = self._body()
                named = corners_named(body["corners"])
                # The confirm step. `confirmed` is only honoured when all four
                # corners were ticked by name; anything less saves as provisional
                # rather than partially confirmed, because "three of four" is not
                # a claim the trust layer has a state for.
                ticked = [c for c in (body.get("confirmed_corners") or [])
                          if c in DBL]
                confirmed = bool(body.get("confirmed")) and len(set(ticked)) == 4
                far_baseline = body.get("far_baseline")
                if far_baseline not in (True, False):
                    far_baseline = None
                Path(state["out"]).parent.mkdir(parents=True, exist_ok=True)
                if body.get("lock", True):
                    # Never save an impossible court: pure shape lock (no paint
                    # pull — at Save time the user's placement is the authority).
                    locked, moved = lock_shape(named, use_dt=False)
                    # NEVER SILENTLY MOVE A CONFIRMED POINT. If the lock shifted a
                    # corner the caller had just confirmed, the confirmation was
                    # about a placement that is no longer being saved, so it is
                    # dropped and the reply says how far it moved. The alternative
                    # - shipping an attestation about points nobody looked at - is
                    # trap T26 rebuilt with better paperwork.
                    kept = confirmed and float(moved) <= 1.0
                    Path(state["out"]).write_text(
                        save_text(corners_named(locked), exact=False,
                                  provenance=provenance_block(
                                      state, True, moved, kept, DBL,
                                      far_baseline)),
                        encoding="utf-8")
                    self._send(200, {"ok": True, "path": state["out"],
                                     "corners": corners_named(locked),
                                     "moved": float(moved),
                                     "confirmed": kept,
                                     "confirmation_dropped": confirmed and not kept})
                else:
                    # Shape lock OFF: the user chose to place corners EXACTLY
                    # (e.g. a wide lens bends the real lines away from any
                    # pinhole view). Saved with the _exact marker so the
                    # pipeline also skips its snap + shape lock.
                    Path(state["out"]).write_text(
                        save_text(corners_named(named), exact=True,
                                  provenance=provenance_block(
                                      state, False, 0.0, confirmed, DBL,
                                      far_baseline)),
                        encoding="utf-8")
                    self._send(200, {"ok": True, "path": state["out"],
                                     "corners": corners_named(named),
                                     "moved": 0.0, "exact": True,
                                     "confirmed": confirmed})
            else:
                self._send(404, {"error": "not found"})

    return Handler


def load_frame(args):
    import cv2
    if args.frame:
        img = cv2.imread(args.frame)
        if img is None:
            raise SystemExit(f"cannot read image: {args.frame}")
        return img
    if args.clip:
        d = REPO / "data" / "gold" / "frames" / args.clip
        jpgs = sorted(d.glob("*.jpg"))
        if not jpgs:
            raise SystemExit(f"no frames in {d}")
        return cv2.imread(str(jpgs[len(jpgs) // 2]))
    if args.video:
        # A MIDDLE frame (a rally, not the intro) — the plate below replaces this
        # when temporal filtering is on; this is the single-frame fallback.
        cap = cv2.VideoCapture(args.video)
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        if total > 1:
            cap.set(cv2.CAP_PROP_POS_FRAMES, total // 2)
        ok, im = cap.read()
        cap.release()
        if not ok:
            raise SystemExit(f"cannot read a frame of {args.video}")
        return im
    raise SystemExit("pass --clip, --frame, or --video")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--clip", help="gold clip id (uses a middle frame)")
    ap.add_argument("--frame", help="path to a single image")
    ap.add_argument("--video", help="path to a video (temporal clean plate by default)")
    ap.add_argument("--out", default="court_pts.json", help="where Save writes the keypoints")
    ap.add_argument("--no-auto", action="store_true",
                    help="skip the auto-detect+snap at startup (start from a plain overlay)")
    ap.add_argument("--no-plate", action="store_true",
                    help="skip the temporal clean plate for --video (use one raw frame)")
    ap.add_argument("--camera", type=int, metavar="INDEX", nargs="?", const=0,
                    help="LIVE mode: check framing against a real camera "
                         "(--camera or --camera 1 for a second device)")
    ap.add_argument("--gallery", metavar="DIR",
                    help="GALLERY MODE: every image in DIR becomes a clip in one "
                         "page, switchable with a click. Save writes "
                         "<out-dir>/<name>_pts.json and steps to the next unsaved "
                         "one. This is the mode for a queue of courts — one "
                         "server, one tab, no restarts")
    ap.add_argument("--out-dir", default="data",
                    help="where gallery saves land")
    ap.add_argument("--port", type=int, default=8770)
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args()

    # LIVE mode: aim a real camera and read the verdict as you move it.
    if args.camera is not None:
        state = {"out": args.out, "seed": None, "static_mask": None,
                 "frame": None, "live": True, "source": source_desc(args)}
        print(f"[setup] opening camera {args.camera} ...")
        start_live_camera(state, args.camera)
        Handler = build_handler(state)
        url = f"http://127.0.0.1:{args.port}/"
        fh, fw = state["frame"].shape[:2]
        print(f"Court Setup LIVE at {url}  (camera {args.camera}, {fw}x{fh})")
        print("  Aim the camera; the view/angle checks update as you move it. "
              "Ctrl+C to stop.")
        if not args.no_browser:
            threading.Timer(0.6, webbrowser.open, [url]).start()
        try:
            ThreadingHTTPServer(("127.0.0.1", args.port), Handler).serve_forever()
        finally:
            state["stop"] = True
        return

    if args.gallery:
        gdir, odir = Path(args.gallery), Path(args.out_dir)
        imgs = sorted(p for p in gdir.iterdir()
                      if p.suffix.lower() in (".png", ".jpg", ".jpeg"))
        if not imgs:
            raise SystemExit(f"no images in {gdir}")
        # Which clips earned a seed: those the pipeline's own multi-frame
        # consensus accepted. Read from the audit if one exists; without it
        # nothing is seeded, which is the safe direction.
        seed_ok = set()
        audit = REPO / "data" / "output" / "new_clip_audit.json"
        if audit.is_file():
            try:
                seed_ok = {r["clip"] for r in json.loads(
                    audit.read_text(encoding="utf-8"))["clips"]
                    if r.get("calibrated")}
            except (json.JSONDecodeError, OSError, KeyError):
                pass
        state = {"gallery": [{"name": p.stem, "image": str(p),
                              "out": str(odir / f"{p.stem}_pts.json"),
                              "seed_ok": p.stem in seed_ok}
                             for p in imgs],
                 "seq": 0}
        # Open on the first UNSAVED clip, so resuming a queue lands where it
        # left off instead of on one that is already done.
        start = next((i for i, c in enumerate(state["gallery"])
                      if not Path(c["out"]).is_file()), 0)
        if not select_clip(state, start):
            raise SystemExit(f"could not read {imgs[start]}")
        n_done = sum(1 for c in state["gallery"] if Path(c["out"]).is_file())
        url = f"http://127.0.0.1:{args.port}/"
        print(f"Court Setup — GALLERY of {len(imgs)} clip(s), {n_done} already "
              f"saved.\n  {url}\n  Click a clip to load it. Snap, Save, and it "
              f"steps to the next unsaved one. Ctrl+C to stop.")
        Handler = build_handler(state)
        if not args.no_browser:
            threading.Timer(0.6, webbrowser.open, [url]).start()
        ThreadingHTTPServer(("127.0.0.1", args.port), Handler).serve_forever()
        return

    frame = load_frame(args)
    static_mask = None

    # TEMPORAL FILTERING (default for --video): calibrate on a short-window median
    # clean plate — players/ball wiped off, lines unoccluded — so the snap has the
    # cleanest possible paint to lock onto. Falls back to one frame if too short.
    if args.video and not args.no_plate:
        print("[setup] building a temporal clean plate (players removed)...")
        plate, static_mask = clean_plate_and_motion(args.video)
        if plate is not None:
            frame = plate
            static_pct = 100.0 * float((static_mask > 0).mean())
            print(f"[setup] clean plate ready; MTI marks {static_pct:.0f}% of the "
                  "frame static (moving pixels kept out of the snap)")
        else:
            print("[setup] clip too short for a clean plate; using one frame")

    state = {"frame": frame, "out": args.out, "seed": None,
             "static_mask": static_mask, "source": source_desc(args)}

    # Auto-fit on startup by default: detect the court, then snap it onto the lines,
    # so the overlay opens already fitted and the user only nudges if it's off.
    if not args.no_auto:
        state["seed"] = auto_fit(frame)

    Handler = build_handler(state)
    url = f"http://127.0.0.1:{args.port}/"
    print(f"Court Setup at {url}  (frame {frame.shape[1]}x{frame.shape[0]})")
    print("  Drag the overlay onto the court, Snap to lines, Save. Ctrl+C to stop.")
    if not args.no_browser:
        threading.Timer(0.6, webbrowser.open, [url]).start()
    ThreadingHTTPServer(("127.0.0.1", args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
