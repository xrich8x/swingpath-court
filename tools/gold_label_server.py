"""Browser tool for human gold-labeling of ball positions (HANDOFF §8 fix 1.4).

Serves a single-page labeling UI on localhost. Shows one frame at a time from
a manifest built by select_gold_frames.py; the labeler clicks the ball (a
magnifier loupe follows the cursor for the tiny far-court ball), or marks the
frame NO BALL / UNSURE. Every action is written straight to
data/gold/<clip>.labels.json, so closing the browser loses nothing — reopening
resumes at the first unlabeled frame.

Deliberately blind: the UI never shows any model's prediction or the frame's
selection bucket — otherwise the labels wouldn't be independent ground truth.

Handles any number of clips: every <clip>.manifest.json in the gold dir gets
an entry in the clip picker. To add a clip later, run select_gold_frames.py
on it and refresh the page.

Run from the repo root (stdlib only, no venv needed — but the venv works too):

  py tools/gold_label_server.py
"""

from __future__ import annotations

import argparse
import json
import os
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
LOCK = threading.Lock()


class GoldStore:
    """Manifests + labels for every clip in the gold dir; atomic saves."""

    def __init__(self, gold_dir: Path):
        self.gold_dir = gold_dir

    def clips(self) -> list[dict]:
        out = []
        for mpath in sorted(self.gold_dir.glob("*.manifest.json")):
            if mpath.name.endswith(".court.manifest.json"):
                continue   # court manifests are listed by court_clips()
            man = json.loads(mpath.read_text(encoding="utf-8"))
            labels = self.load_labels(man["clip"])["labels"]
            out.append({
                "clip": man["clip"],
                "total": len(man["frames"]),
                "labeled": sum(1 for f in man["frames"]
                               if str(f["frame"]) in labels),
            })
        return out

    # --- court quality: parallel store, *.court.manifest.json / *.court.labels.json
    def court_clips(self) -> list[dict]:
        out = []
        for mpath in sorted(self.gold_dir.glob("*.court.manifest.json")):
            man = json.loads(mpath.read_text(encoding="utf-8"))
            labels = self.load_court_labels(man["clip"])["labels"]
            out.append({
                "clip": man["clip"],
                "total": len(man["frames"]),
                "labeled": sum(1 for f in man["frames"]
                               if str(f["frame"]) in labels),
            })
        return out

    def court_manifest(self, clip: str) -> dict:
        path = self.gold_dir / f"{clip}.court.manifest.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def court_labels_path(self, clip: str) -> Path:
        return self.gold_dir / f"{clip}.court.labels.json"

    def load_court_labels(self, clip: str) -> dict:
        path = self.court_labels_path(clip)
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return {"clip": clip, "created": time.strftime("%Y-%m-%d %H:%M:%S"),
                "tool": "gold_label_server court v1", "labels": {}}

    def set_court_label(self, clip: str, frame: int, label: dict | None) -> int:
        with LOCK:
            data = self.load_court_labels(clip)
            key = str(frame)
            if label is None:
                data["labels"].pop(key, None)
            else:
                label["t"] = time.strftime("%Y-%m-%d %H:%M:%S")
                data["labels"][key] = label
            data["updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
            tmp = self.court_labels_path(clip).with_suffix(".json.tmp")
            tmp.write_text(json.dumps(data, indent=1), encoding="utf-8")
            os.replace(tmp, self.court_labels_path(clip))
            return len(data["labels"])

    def manifest(self, clip: str) -> dict:
        path = self.gold_dir / f"{clip}.manifest.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def labels_path(self, clip: str) -> Path:
        return self.gold_dir / f"{clip}.labels.json"

    def load_labels(self, clip: str) -> dict:
        path = self.labels_path(clip)
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return {"clip": clip, "created": time.strftime("%Y-%m-%d %H:%M:%S"),
                "tool": "gold_label_server v1", "labels": {}}

    def set_label(self, clip: str, frame: int, label: dict | None) -> int:
        """Set or clear one frame's label; persist atomically. Returns the
        number of labeled frames."""
        with LOCK:
            data = self.load_labels(clip)
            key = str(frame)
            if label is None:
                data["labels"].pop(key, None)
            else:
                label["t"] = time.strftime("%Y-%m-%d %H:%M:%S")
                data["labels"][key] = label
            data["updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
            tmp = self.labels_path(clip).with_suffix(".json.tmp")
            tmp.write_text(json.dumps(data, indent=1), encoding="utf-8")
            os.replace(tmp, self.labels_path(clip))
            return len(data["labels"])


class Handler(BaseHTTPRequestHandler):
    store: GoldStore  # set by main()

    def log_message(self, *a):  # silence per-request console spam
        pass

    def _send(self, code: int, body: bytes, ctype: str, cache: bool = False):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        if cache:
            self.send_header("Cache-Control", "max-age=86400, immutable")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj, code: int = 200):
        self._send(code, json.dumps(obj).encode("utf-8"), "application/json")

    def do_GET(self):
        from urllib.parse import parse_qs, urlparse

        url = urlparse(self.path)
        if url.path == "/":
            self._send(200, PAGE.encode("utf-8"), "text/html; charset=utf-8")
        elif url.path == "/court":
            self._send(200, PAGE_COURT.encode("utf-8"), "text/html; charset=utf-8")
        elif url.path == "/api/clips":
            self._json(self.store.clips())
        elif url.path == "/api/court_clips":
            self._json(self.store.court_clips())
        elif url.path == "/api/state":
            clip = parse_qs(url.query).get("clip", [""])[0]
            try:
                self._json({"manifest": self.store.manifest(clip),
                            "labels": self.store.load_labels(clip)["labels"]})
            except FileNotFoundError:
                self._json({"error": f"no manifest for clip {clip!r}"}, 404)
        elif url.path == "/api/court_state":
            clip = parse_qs(url.query).get("clip", [""])[0]
            try:
                self._json({"manifest": self.store.court_manifest(clip),
                            "labels": self.store.load_court_labels(clip)["labels"]})
            except FileNotFoundError:
                self._json({"error": f"no court manifest for clip {clip!r}"}, 404)
        elif url.path.startswith("/frames/"):
            rel = url.path[len("/frames/"):]
            path = (self.store.gold_dir / "frames" / rel).resolve()
            if (self.store.gold_dir / "frames").resolve() not in path.parents:
                self._send(403, b"forbidden", "text/plain")
            elif path.is_file():
                self._send(200, path.read_bytes(), "image/jpeg", cache=True)
            else:
                self._send(404, b"missing frame (re-run select_gold_frames.py"
                                b" --extract-only?)", "text/plain")
        else:
            self._send(404, b"not found", "text/plain")

    def do_POST(self):
        if self.path not in ("/api/label", "/api/court_label"):
            self._send(404, b"not found", "text/plain")
            return
        n = int(self.headers.get("Content-Length", 0))
        req = json.loads(self.rfile.read(n))
        if self.path == "/api/court_label":
            labeled = self.store.set_court_label(req["clip"], int(req["frame"]),
                                                 req.get("label"))
        else:
            labeled = self.store.set_label(req["clip"], int(req["frame"]),
                                           req.get("label"))
        self._json({"ok": True, "labeled": labeled})


PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Gold ball labeler</title>
<style>
  :root { color-scheme: dark; }
  body { margin: 0; background: #14171c; color: #dfe4ea;
         font: 14px/1.45 system-ui, sans-serif; user-select: none; }
  header { display: flex; align-items: center; gap: 14px; padding: 10px 16px;
           background: #1d2129; flex-wrap: wrap; }
  header h1 { font-size: 15px; margin: 0; font-weight: 600; }
  select, button { font: inherit; border-radius: 6px; border: 1px solid #39404d;
                   background: #262c37; color: #dfe4ea; padding: 6px 12px;
                   cursor: pointer; }
  button:hover { background: #313949; }
  button.noball { background: #7c2d2d; border-color: #a33; font-weight: 700;
                  padding: 6px 18px; }
  button.noball:hover { background: #943636; }
  button.unsure { background: #4d4426; border-color: #776a33; }
  #bar { flex: 1 1 160px; height: 10px; background: #262c37; border-radius: 5px;
         min-width: 120px; }
  #fill { height: 100%; width: 0; background: #4caf7d; border-radius: 5px;
          transition: width .15s; }
  #stage { position: relative; margin: 12px auto; width: fit-content; }
  #view { display: block; cursor: crosshair; border: 1px solid #39404d;
          border-radius: 4px; }
  #loupe { position: fixed; width: 184px; height: 184px; border-radius: 50%;
           border: 2px solid #9ab; pointer-events: none; display: none;
           z-index: 10; box-shadow: 0 4px 18px rgba(0,0,0,.6); }
  #status { text-align: center; min-height: 22px; font-size: 15px; }
  #status .ball { color: #7fd6a4; } #status .nob { color: #ff9c9c; }
  #status .uns { color: #e6d38a; }
  footer { text-align: center; color: #8b93a1; padding: 8px 16px 20px;
           font-size: 13px; }
  /* The rule that decides whether a click is worth anything. It lives on the
     labelling page, not in a doc, because that is where the judgement is made. */
  .rule { max-width: 760px; margin: 10px auto 0; text-align: left;
          background: #191d24; border-left: 3px solid #4a5568; border-radius: 4px;
          padding: 10px 12px; line-height: 1.55; color: #c3cad6; }
  .rule b { color: #e6ecf5; }
  kbd { background: #262c37; border: 1px solid #39404d; border-radius: 4px;
        padding: 0 5px; font-family: inherit; }
  #done { display: none; text-align: center; font-size: 17px; color: #7fd6a4;
          padding: 6px; }
</style>
</head>
<body>
<header>
  <h1>Gold ball labeler</h1>
  <a href="/court" style="color:#8fd6ff;text-decoration:none;font-weight:600">Court quality &rarr;</a>
  <select id="clip"></select>
  <span id="count">–</span>
  <div id="bar"><div id="fill"></div></div>
  <button id="prev" title="left arrow">&#9664; Prev</button>
  <button id="next" title="right arrow">Next &#9654;</button>
  <button id="noball" class="noball" title="N">NO BALL (N)</button>
  <button id="unsure" class="unsure" title="S">Unsure (S)</button>
  <button id="clear" title="U">Clear (U)</button>
</header>
<div id="done">All frames labeled — you can close this window. The file is saved.</div>
<div id="stage">
  <canvas id="view"></canvas>
  <canvas id="loupe" width="184" height="184"></canvas>
</div>
<div id="status"></div>
<footer>
  <b>Click the ball in play</b> — the round magnifier follows your mouse; aim with its + crosshair.
  No ball in play / can't see it &rarr; <kbd>N</kbd>.
  Truly can't decide &rarr; <kbd>S</kbd>.
  <kbd>&larr;</kbd><kbd>&rarr;</kbd> move &middot; <kbd>U</kbd> clear this frame &middot;
  <kbd>+</kbd>/<kbd>&minus;</kbd> magnifier zoom
  <div class="rule"><b>It has to move.</b> Arrow left and right before you commit.
    A ball in play is somewhere different on every frame; a pale dot in the
    <i>same</i> place on three frames is a wall mark, a light, a bag, or a ball
    lying on the net. Clicking one of those is worse than clicking nothing — it is
    exactly the mistake the detector already makes, and your click would teach it
    that the mistake is right. <b><kbd>N</kbd> and <kbd>S</kbd> beat a guess.</b>
    Nothing counts how many balls you found.</div>
</footer>
<script>
"use strict";
const $ = id => document.getElementById(id);
const view = $("view"), vctx = view.getContext("2d");
const loupe = $("loupe"), lctx = loupe.getContext("2d");
let clip = null, frames = [], labels = {}, cur = 0, zoom = 4;
const imgs = new Map();   // frame -> Image (small cache)

function imgFor(f, cb) {
  if (imgs.has(f)) { const im = imgs.get(f); im.complete ? cb(im) : im.addEventListener("load", () => cb(im)); return; }
  const im = new Image();
  im.src = `/frames/${clip}/f${String(f).padStart(5, "0")}.jpg`;
  imgs.set(f, im);
  if (imgs.size > 40) imgs.delete(imgs.keys().next().value);
  im.addEventListener("load", () => cb(im));
}

// Scale UP to fill the window, not just down to fit it. This capped at 1x, which
// was invisible while every clip was 1280x720 and crippling the moment one was
// not: the far-court training frames are 512x288 (their source videos are gone),
// so they rendered at a fifth of the screen and the ball was unfindable for a
// reason that had nothing to do with the ball. Upscaling adds no information, but
// the loupe magnifies from the NATURAL pixels either way, and clicks are stored in
// natural coordinates (see the naturalWidth/r.width conversion below), so display
// scale cannot affect label accuracy. Capped at 4x so a small frame does not turn
// into a wall of blur. The court labeller in this same file always did this.
function fitScale(im) {
  const w = Math.min(im.naturalWidth * 4, window.innerWidth - 40);
  return w / im.naturalWidth;
}

function render() {
  const f = frames[cur];
  imgFor(f, im => {
    if (frames[cur] !== f) return;           // stale load
    const s = fitScale(im);
    view.width = Math.round(im.naturalWidth * s);
    view.height = Math.round(im.naturalHeight * s);
    vctx.drawImage(im, 0, 0, view.width, view.height);
    const lab = labels[f];
    if (lab && lab.ball === true) {
      const x = lab.x * s, y = lab.y * s;
      vctx.strokeStyle = "#4caf7d"; vctx.lineWidth = 2;
      vctx.beginPath(); vctx.arc(x, y, 9, 0, 7); vctx.stroke();
      vctx.beginPath(); vctx.moveTo(x - 14, y); vctx.lineTo(x + 14, y);
      vctx.moveTo(x, y - 14); vctx.lineTo(x, y + 14); vctx.stroke();
    }
    updateStatus();
    // preload the next two frames
    for (const g of [frames[cur + 1], frames[cur + 2]]) if (g !== undefined) imgFor(g, () => {});
  });
}

function updateStatus() {
  const f = frames[cur], lab = labels[f];
  let s = `Frame ${cur + 1} of ${frames.length}`;
  if (lab === undefined) s += " — unlabeled";
  else if (lab.ball === true) s += ` — <span class="ball">ball at (${Math.round(lab.x)}, ${Math.round(lab.y)})</span>`;
  else if (lab.ball === false) s += ' — <span class="nob">NO BALL</span>';
  else s += ' — <span class="uns">unsure (excluded from scoring)</span>';
  $("status").innerHTML = s;
  const n = Object.keys(labels).length;
  $("count").textContent = `${n} / ${frames.length} labeled`;
  $("fill").style.width = (100 * n / frames.length) + "%";
  $("done").style.display = n >= frames.length ? "block" : "none";
}

function firstUnlabeled(from = 0) {
  for (let i = 0; i < frames.length; i++) {
    const k = (from + i) % frames.length;
    if (labels[frames[k]] === undefined) return k;
  }
  return null;
}

async function save(frame, label) {
  if (label) labels[frame] = label; else delete labels[frame];
  updateStatus();
  await fetch("/api/label", { method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ clip, frame, label }) });
}

function label(lab) {
  save(frames[cur], lab);
  render();
  setTimeout(() => {                           // auto-advance to next unlabeled
    const nxt = firstUnlabeled(cur + 1);
    if (nxt !== null) { cur = nxt; render(); }
    else updateStatus();
  }, 220);
}

function nav(d) { cur = Math.min(frames.length - 1, Math.max(0, cur + d)); loupe.style.display = "none"; render(); }

view.addEventListener("click", e => {
  const r = view.getBoundingClientRect(), f = frames[cur];
  imgFor(f, im => {
    const nx = (e.clientX - r.left) * im.naturalWidth / r.width;
    const ny = (e.clientY - r.top) * im.naturalHeight / r.height;
    label({ ball: true, x: Math.round(nx * 10) / 10, y: Math.round(ny * 10) / 10 });
  });
});

view.addEventListener("mousemove", e => {
  const f = frames[cur];
  imgFor(f, im => {
    if (frames[cur] !== f) return;
    const r = view.getBoundingClientRect();
    const nx = (e.clientX - r.left) * im.naturalWidth / r.width;
    const ny = (e.clientY - r.top) * im.naturalHeight / r.height;
    const L = loupe.width, src = L / zoom;
    lctx.imageSmoothingEnabled = zoom <= 2;
    lctx.fillStyle = "#000"; lctx.fillRect(0, 0, L, L);
    lctx.drawImage(im, nx - src / 2, ny - src / 2, src, src, 0, 0, L, L);
    lctx.strokeStyle = "rgba(120,220,160,.9)"; lctx.lineWidth = 1;
    lctx.beginPath(); lctx.moveTo(L / 2 - 12, L / 2); lctx.lineTo(L / 2 + 12, L / 2);
    lctx.moveTo(L / 2, L / 2 - 12); lctx.lineTo(L / 2, L / 2 + 12); lctx.stroke();
    let lx = e.clientX + 26, ly = e.clientY + 26;
    if (lx + L + 8 > window.innerWidth) lx = e.clientX - L - 26;
    if (ly + L + 8 > window.innerHeight) ly = e.clientY - L - 26;
    loupe.style.left = lx + "px"; loupe.style.top = ly + "px";
    loupe.style.display = "block";
  });
});
view.addEventListener("mouseleave", () => loupe.style.display = "none");

document.addEventListener("keydown", e => {
  if (e.target.tagName === "SELECT") return;
  if (e.repeat) return;   // a held key must not spray labels across frames
  const k = e.key.toLowerCase();
  if (k === "arrowright" || k === ".") nav(1);
  else if (k === "arrowleft" || k === ",") nav(-1);
  else if (k === "n") label({ ball: false });
  else if (k === "s") label({ ball: null, unsure: true });
  else if (k === "u") { save(frames[cur], null); render(); }
  else if (k === "+" || k === "=") { zoom = Math.min(10, zoom + 1); }
  else if (k === "-") { zoom = Math.max(2, zoom - 1); }
  else return;
  e.preventDefault();
});

$("prev").onclick = () => nav(-1);
$("next").onclick = () => nav(1);
$("noball").onclick = () => label({ ball: false });
$("unsure").onclick = () => label({ ball: null, unsure: true });
$("clear").onclick = () => { save(frames[cur], null); render(); };

async function loadClip(name) {
  const res = await fetch(`/api/state?clip=${encodeURIComponent(name)}`);
  const st = await res.json();
  clip = name;
  frames = st.manifest.frames.map(r => r.frame);
  labels = {};
  for (const [k, v] of Object.entries(st.labels)) labels[Number(k)] = v;
  imgs.clear();
  cur = firstUnlabeled() ?? 0;
  render();
}

(async () => {
  const clips = await (await fetch("/api/clips")).json();
  const sel = $("clip");
  for (const c of clips) {
    const o = document.createElement("option");
    o.value = c.clip; o.textContent = `${c.clip} (${c.labeled}/${c.total})`;
    sel.appendChild(o);
  }
  sel.onchange = () => loadClip(sel.value);
  const start = clips.find(c => c.labeled < c.total) || clips[0];
  if (!start) { $("status").textContent = "No manifests found — run select_gold_frames.py first."; return; }
  sel.value = start.clip;
  await loadClip(start.clip);
})();
window.addEventListener("resize", render);
</script>
</body>
</html>
"""


PAGE_COURT = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Gold court labeler</title>
<style>
  :root { color-scheme: dark; }
  body { margin: 0; background: #14171c; color: #dfe4ea;
         font: 14px/1.45 system-ui, sans-serif; user-select: none; }
  header { display: flex; align-items: center; gap: 14px; padding: 10px 16px;
           background: #1d2129; flex-wrap: wrap; }
  header h1 { font-size: 15px; margin: 0; font-weight: 600; }
  a.nav { color:#8fd6ff; text-decoration:none; font-weight:600; }
  select, button { font: inherit; border-radius: 6px; border: 1px solid #39404d;
                   background: #262c37; color: #dfe4ea; padding: 6px 12px;
                   cursor: pointer; }
  button:hover { background: #313949; }
  button.bad { background: #7c2d2d; border-color: #a33; font-weight: 700; }
  button.bad:hover { background: #943636; }
  #bar { flex: 1 1 160px; height: 10px; background: #262c37; border-radius: 5px;
         min-width: 120px; }
  #fill { height: 100%; width: 0; background: #4caf7d; border-radius: 5px;
          transition: width .15s; }
  #stage { position: relative; margin: 12px auto; width: fit-content; }
  #view { display: block; cursor: crosshair; border: 1px solid #39404d;
          border-radius: 4px; }
  #loupe { position: fixed; width: 184px; height: 184px; border-radius: 50%;
           border: 2px solid #9ab; pointer-events: none; display: none;
           z-index: 10; box-shadow: 0 4px 18px rgba(0,0,0,.6); }
  #status { text-align: center; min-height: 22px; font-size: 15px; }
  #status .ok { color: #7fd6a4; } #status .bad { color: #ff9c9c; }
  #status .todo { color: #e6d38a; }
  footer { text-align: center; color: #8b93a1; padding: 8px 16px 20px; font-size: 13px; }
  kbd { background: #262c37; border: 1px solid #39404d; border-radius: 4px;
        padding: 0 5px; font-family: inherit; }
  #done { display: none; text-align: center; font-size: 17px; color: #7fd6a4; padding: 6px; }
</style>
</head>
<body>
<header>
  <h1>Gold court labeler</h1>
  <a class="nav" href="/">&larr; Ball</a>
  <select id="clip"></select>
  <span id="count">-</span>
  <div id="bar"><div id="fill"></div></div>
  <button id="prev" title="left arrow">&#9664; Prev</button>
  <button id="next" title="right arrow">Next &#9654;</button>
  <button id="reset" title="R">Reset corners (R)</button>
  <button id="bad" class="bad" title="G">Court not usable (G)</button>
</header>
<div id="done">All frames labeled - you can close this window. The file is saved.</div>
<div id="stage">
  <canvas id="view"></canvas>
  <canvas id="loupe" width="184" height="184"></canvas>
</div>
<div id="status"></div>
<footer>
  <b>Click the 4 baseline corners in order.</b> If a corner is <b>off the edge of the
  frame</b>, click/drag it out into the dark margin - the drawn lines that ARE visible
  should sit on the real lines; the geometry extrapolates the rest. Off-frame corners
  show <span style="color:#ff9c4a">hollow orange with a *</span>. <b>Drag any corner</b> to fit.
  Next frame pre-loads the last court - just nudge for drift, then press
  <kbd>Enter</kbd>. <b><kbd>Enter</kbd> = confirm &amp; jump to next unlabeled</b> (the fast path).
  <kbd>R</kbd> re-place &middot; <kbd>G</kbd> court not usable &middot;
  <kbd>&larr;</kbd><kbd>&rarr;</kbd> review &middot; <kbd>+</kbd>/<kbd>&minus;</kbd> zoom
</footer>
<script>
"use strict";
const $ = id => document.getElementById(id);
const view = $("view"), vctx = view.getContext("2d");
const loupe = $("loupe"), lctx = loupe.getContext("2d");

// Court geometry in metres (mirrors backend court.py / frontend court.js).
const CORNERS = [
  { key: "near_bl_doubles", short: "1 - NEAR-LEFT",  m: [0, 0] },
  { key: "near_br_doubles", short: "2 - NEAR-RIGHT", m: [10.97, 0] },
  { key: "far_br_doubles",  short: "3 - FAR-RIGHT",  m: [10.97, 23.77] },
  { key: "far_bl_doubles",  short: "4 - FAR-LEFT",   m: [0, 23.77] },
];
const KP = {
  far_bl_doubles: [0, 23.77], far_br_doubles: [10.97, 23.77],
  near_bl_doubles: [0, 0], near_br_doubles: [10.97, 0],
  far_bl_singles: [1.37, 23.77], near_bl_singles: [1.37, 0],
  far_br_singles: [9.6, 23.77], near_br_singles: [9.6, 0],
  far_sl_left: [1.37, 18.285], far_sl_right: [9.6, 18.285],
  near_sl_left: [1.37, 5.485], near_sl_right: [9.6, 5.485],
  far_t: [5.485, 18.285], near_t: [5.485, 5.485],
};
const LINES = [
  [[0,0],[10.97,0]], [[0,23.77],[10.97,23.77]],
  [[0,0],[0,23.77]], [[10.97,0],[10.97,23.77]],
  [[1.37,0],[1.37,23.77]], [[9.6,0],[9.6,23.77]],
  [[1.37,5.485],[9.6,5.485]], [[1.37,18.285],[9.6,18.285]],
  [[5.485,5.485],[5.485,18.285]],
];
const NET = [[0,11.885],[10.97,11.885]];

// Solve a 3x3 homography mapping 4 metre points -> 4 image points (8x8 linear).
function solveH(src, dst) {
  const A = [], b = [];
  for (let i = 0; i < 4; i++) {
    const [X, Y] = src[i], [u, v] = dst[i];
    A.push([X, Y, 1, 0, 0, 0, -X*u, -Y*u]); b.push(u);
    A.push([0, 0, 0, X, Y, 1, -X*v, -Y*v]); b.push(v);
  }
  // Gaussian elimination with partial pivoting.
  for (let c = 0; c < 8; c++) {
    let p = c;
    for (let r = c + 1; r < 8; r++) if (Math.abs(A[r][c]) > Math.abs(A[p][c])) p = r;
    [A[c], A[p]] = [A[p], A[c]]; [b[c], b[p]] = [b[p], b[c]];
    if (Math.abs(A[c][c]) < 1e-12) return null;
    for (let r = 0; r < 8; r++) {
      if (r === c) continue;
      const f = A[r][c] / A[c][c];
      for (let k = c; k < 8; k++) A[r][k] -= f * A[c][k];
      b[r] -= f * b[c];
    }
  }
  const h = b.map((v, i) => v / A[i][i]);
  return [[h[0], h[1], h[2]], [h[3], h[4], h[5]], [h[6], h[7], 1]];
}
function applyH(H, X, Y) {
  const d = H[2][0]*X + H[2][1]*Y + 1;
  return [(H[0][0]*X + H[0][1]*Y + H[0][2]) / d,
          (H[1][0]*X + H[1][1]*Y + H[1][2]) / d];
}

let clip = null, frames = [], labels = {}, cur = 0, zoom = 4;
let corners = [null, null, null, null];   // image-px per CORNERS index (may be off-frame)
let placed = 0, drag = null, scale = 1, lastCorners = null;
let padx = 0, pady = 0, natW = 0, natH = 0;   // extrapolation margin + frame size
const PADF = 0.35;   // margin as a fraction of the image on each side (room for off-frame corners)
const imgs = new Map();

// A corner is "estimated" when it lies outside the real frame (extrapolated).
function isOff(c) { return !c || c[0] < 0 || c[1] < 0 || c[0] > natW || c[1] > natH; }

function imgFor(f, cb) {
  if (imgs.has(f)) { const im = imgs.get(f); im.complete ? cb(im) : im.addEventListener("load", () => cb(im)); return; }
  const im = new Image();
  im.src = `/frames/${clip}/f${String(f).padStart(5, "0")}.jpg`;
  imgs.set(f, im);
  if (imgs.size > 30) imgs.delete(imgs.keys().next().value);
  im.addEventListener("load", () => cb(im));
}
function fitScale(im) {
  const avail = Math.max(320, (window.innerWidth || 1000) - 40);
  const s = avail / (im.naturalWidth * (1 + 2 * PADF));
  return Math.min(Math.max(s, 0.1), 1);   // clamp: never <=0, never upscale past native
}

function render() {
  const f = frames[cur];
  imgFor(f, im => {
    if (frames[cur] !== f) return;
    scale = fitScale(im);
    const s = scale;
    natW = im.naturalWidth; natH = im.naturalHeight;
    padx = Math.round(PADF * natW * s); pady = Math.round(PADF * natH * s);
    const iw = Math.round(natW * s), ih = Math.round(natH * s);
    view.width = iw + 2 * padx; view.height = ih + 2 * pady;
    // margin (extrapolation zone) then the real frame inside it
    vctx.fillStyle = "#0c0e12"; vctx.fillRect(0, 0, view.width, view.height);
    vctx.drawImage(im, padx, pady, iw, ih);
    vctx.strokeStyle = "rgba(255,255,255,.28)"; vctx.lineWidth = 1;
    vctx.strokeRect(padx + 0.5, pady + 0.5, iw, ih);   // frame edge; corners may go outside
    const P = (X, Y, H) => { const p = applyH(H, X, Y); return [padx + p[0]*s, pady + p[1]*s]; };
    if (placed === 4) {
      const H = solveH(CORNERS.map(c => c.m), corners);
      if (H) {
        vctx.lineWidth = 2; vctx.strokeStyle = "rgba(120,220,160,.95)";
        for (const [a, b] of LINES) {
          const p = P(a[0], a[1], H), q = P(b[0], b[1], H);
          vctx.beginPath(); vctx.moveTo(p[0], p[1]); vctx.lineTo(q[0], q[1]); vctx.stroke();
        }
        vctx.strokeStyle = "rgba(255,210,120,.95)";
        const n0 = P(NET[0][0], NET[0][1], H), n1 = P(NET[1][0], NET[1][1], H);
        vctx.beginPath(); vctx.moveTo(n0[0], n0[1]); vctx.lineTo(n1[0], n1[1]); vctx.stroke();
        vctx.fillStyle = "rgba(140,200,255,.9)";
        for (const k in KP) { const p = P(KP[k][0], KP[k][1], H);
          vctx.beginPath(); vctx.arc(p[0], p[1], 2.5, 0, 7); vctx.fill(); }
      }
    }
    // corner handles (hollow orange = extrapolated, outside the frame)
    for (let i = 0; i < 4; i++) {
      if (!corners[i]) continue;
      const x = padx + corners[i][0]*s, y = pady + corners[i][1]*s, off = isOff(corners[i]);
      vctx.lineWidth = off ? 2.5 : 2;
      vctx.strokeStyle = off ? "#ff9c4a" : "#14171c"; vctx.fillStyle = "#ffd24a";
      vctx.beginPath(); vctx.arc(x, y, 7, 0, 7); if (!off) vctx.fill(); vctx.stroke();
      vctx.fillStyle = off ? "#ff9c4a" : "#14171c"; vctx.font = "bold 11px system-ui";
      vctx.fillText(String(i+1) + (off ? "*" : ""), x - 3, off ? y - 11 : y + 4);
    }
    updateStatus();
    for (const g of [frames[cur+1], frames[cur+2]]) if (g !== undefined) imgFor(g, () => {});
  });
}

function updateStatus() {
  const f = frames[cur], lab = labels[f];
  let s = `Frame ${cur+1} of ${frames.length}`;
  if (lab && lab.court === false) s += ' - <span class="bad">court not usable</span>';
  else if (placed === 4) s += ' - <span class="ok">court set (drag to fit, or Next)</span>';
  else s += ` - <span class="todo">click corner ${CORNERS[placed].short}</span>`;
  $("status").innerHTML = s;
  const n = Object.keys(labels).length;
  $("count").textContent = `${n} / ${frames.length} labeled`;
  $("fill").style.width = (100 * n / frames.length) + "%";
  $("done").style.display = n >= frames.length ? "block" : "none";
}

function firstUnlabeled(from = 0) {
  for (let i = 0; i < frames.length; i++) {
    const k = (from + i) % frames.length;
    if (labels[frames[k]] === undefined) return k;
  }
  return null;
}

function cornersToLabel() {
  const H = solveH(CORNERS.map(c => c.m), corners);
  const cobj = {}, kobj = {}, est = [];
  CORNERS.forEach((c, i) => {
    cobj[c.key] = [Math.round(corners[i][0]*10)/10, Math.round(corners[i][1]*10)/10];
    if (isOff(corners[i])) est.push(c.key);   // corner extrapolated outside the frame
  });
  if (H) for (const k in KP) { const p = applyH(H, KP[k][0], KP[k][1]);
    kobj[k] = [Math.round(p[0]*10)/10, Math.round(p[1]*10)/10]; }
  return { court: true, corners: cobj, keypoints: kobj, estimated_corners: est };
}

async function post(frame, label) {
  if (label) labels[frame] = label; else delete labels[frame];
  updateStatus();
  await fetch("/api/court_label", { method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ clip, frame, label }) });
}
function saveCourt() {
  if (placed !== 4) return;
  const lab = cornersToLabel();
  lastCorners = corners.map(c => c.slice());
  post(frames[cur], lab);
}

function loadFrameState() {
  const lab = labels[frames[cur]];
  if (lab && lab.court && lab.corners) {
    corners = CORNERS.map(c => (lab.corners[c.key] || null));
    placed = corners.every(Boolean) ? 4 : 0;
  } else if (lab && lab.court === false) {
    corners = [null,null,null,null]; placed = 0;
  } else if (lastCorners) {                 // seed an unlabeled frame from the last court
    corners = lastCorners.map(c => c.slice()); placed = 4;
  } else { corners = [null,null,null,null]; placed = 0; }
}

function saveAndNext() {          // confirm this court, jump to next UNLABELED (Enter)
  if (placed === 4) saveCourt();
  const nxt = firstUnlabeled(cur + 1);
  if (nxt !== null) { cur = nxt; loupe.style.display = "none"; drag = null; loadFrameState(); render(); }
  else { updateStatus(); }
}

function nav(d) {
  if (placed === 4) saveCourt();   // persist the fitted court when leaving a frame,
                                   // so Next/arrows save like Enter does (not just
                                   // hand-placed frames) — on a fixed camera the
                                   // carried-over court is correct for every frame.
  cur = Math.min(frames.length - 1, Math.max(0, cur + d));
  loupe.style.display = "none"; drag = null;
  loadFrameState(); render();
}

function toImg(e, im) {
  const r = view.getBoundingClientRect();
  const cx = (e.clientX - r.left) * view.width / r.width;    // client -> canvas px
  const cy = (e.clientY - r.top) * view.height / r.height;
  return [(cx - padx) / scale, (cy - pady) / scale];         // canvas -> image px (may be off-frame)
}
function nearestCorner(x, y) {
  let best = null, bd = 18 / scale;   // ~18 screen px
  for (let i = 0; i < 4; i++) if (corners[i]) {
    const d = Math.hypot(corners[i][0]-x, corners[i][1]-y);
    if (d < bd) { bd = d; best = i; }
  }
  return best;
}

view.addEventListener("mousedown", e => {
  const f = frames[cur];
  imgFor(f, im => {
    const [x, y] = toImg(e, im);
    if (placed === 4) { const c = nearestCorner(x, y); if (c !== null) { drag = c; return; } }
    if (placed < 4) { corners[placed] = [x, y]; placed++; render();
      if (placed === 4) saveCourt(); }
  });
});
view.addEventListener("mousemove", e => {
  const f = frames[cur];
  imgFor(f, im => {
    if (frames[cur] !== f) return;
    const [x, y] = toImg(e, im);
    if (drag !== null) { corners[drag] = [x, y]; render(); }
    // magnifier loupe
    const L = loupe.width, src = L / zoom;
    lctx.imageSmoothingEnabled = zoom <= 2;
    lctx.fillStyle = "#000"; lctx.fillRect(0, 0, L, L);
    lctx.drawImage(im, x - src/2, y - src/2, src, src, 0, 0, L, L);
    lctx.strokeStyle = "rgba(120,220,160,.9)"; lctx.lineWidth = 1;
    lctx.beginPath(); lctx.moveTo(L/2-12, L/2); lctx.lineTo(L/2+12, L/2);
    lctx.moveTo(L/2, L/2-12); lctx.lineTo(L/2, L/2+12); lctx.stroke();
    let lx = e.clientX + 26, ly = e.clientY + 26;
    if (lx + L + 8 > window.innerWidth) lx = e.clientX - L - 26;
    if (ly + L + 8 > window.innerHeight) ly = e.clientY - L - 26;
    loupe.style.left = lx + "px"; loupe.style.top = ly + "px"; loupe.style.display = "block";
  });
});
window.addEventListener("mouseup", () => { if (drag !== null) { drag = null; saveCourt(); } });
view.addEventListener("mouseleave", () => loupe.style.display = "none");

function resetCorners() { corners = [null,null,null,null]; placed = 0; drag = null;
  post(frames[cur], null); render(); }

document.addEventListener("keydown", e => {
  if (e.target.tagName === "SELECT") return;
  if (e.repeat) return;
  const k = e.key.toLowerCase();
  if (k === "enter" || k === " ") saveAndNext();
  else if (k === "arrowright" || k === ".") nav(1);
  else if (k === "arrowleft" || k === ",") nav(-1);
  else if (k === "g") { corners = [null,null,null,null]; placed = 0; post(frames[cur], { court: false, unusable: true }); render(); }
  else if (k === "r") resetCorners();
  else if (k === "+" || k === "=") zoom = Math.min(10, zoom + 1);
  else if (k === "-") zoom = Math.max(2, zoom - 1);
  else return;
  e.preventDefault();
});
$("prev").onclick = () => nav(-1);
$("next").onclick = () => nav(1);
$("reset").onclick = resetCorners;
$("bad").onclick = () => { corners = [null,null,null,null]; placed = 0; post(frames[cur], { court: false, unusable: true }); render(); };

async function loadClip(name) {
  const st = await (await fetch(`/api/court_state?clip=${encodeURIComponent(name)}`)).json();
  clip = name;
  frames = st.manifest.frames.map(r => r.frame);
  labels = {};
  for (const [k, v] of Object.entries(st.labels)) labels[Number(k)] = v;
  imgs.clear(); lastCorners = null;
  for (const g of frames) imgFor(g, () => {});    // warm every frame up front (all tiny)
  // seed the carry-over court from the last already-labeled frame, if any
  for (const f of frames) { const l = labels[f];
    if (l && l.court && l.corners) lastCorners = CORNERS.map(c => l.corners[c.key]); }
  cur = firstUnlabeled() ?? 0;
  loadFrameState(); render();
}

(async () => {
  const clips = await (await fetch("/api/court_clips")).json();
  const sel = $("clip");
  for (const c of clips) {
    const o = document.createElement("option");
    o.value = c.clip; o.textContent = `${c.clip} (${c.labeled}/${c.total})`;
    sel.appendChild(o);
  }
  sel.onchange = () => loadClip(sel.value);
  const start = clips.find(c => c.labeled < c.total) || clips[0];
  if (!start) { $("status").innerHTML = 'No court clips yet - run <kbd>tools/court_gold_frames.py your_clip.mp4</kbd> then refresh.'; return; }
  sel.value = start.clip;
  await loadClip(start.clip);
})();
window.addEventListener("resize", render);
</script>
</body>
</html>
"""


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--gold-dir", default=str(REPO / "data" / "gold"))
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args()

    Handler.store = GoldStore(Path(args.gold_dir))
    clips = Handler.store.clips()
    court_clips = Handler.store.court_clips()
    url = f"http://127.0.0.1:{args.port}/"
    print(f"Gold labeler running at {url}")
    print("  BALL clips (page /):")
    for c in clips:
        print(f"    {c['clip']}: {c['labeled']}/{c['total']} labeled")
    if not clips:
        print("    (none — run select_gold_frames.py first)")
    print(f"  COURT clips (page /court):")
    for c in court_clips:
        print(f"    {c['clip']}: {c['labeled']}/{c['total']} labeled")
    if not court_clips:
        print("    (none — run tools/court_gold_frames.py <clip.mp4> first)")
    print("Press Ctrl+C in this window to stop. Progress is saved on every click.")
    if not args.no_browser:
        threading.Timer(0.6, webbrowser.open, [url]).start()
    ThreadingHTTPServer(("127.0.0.1", args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
