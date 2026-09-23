# Working journal — live state

**If a session or an agent died, read this file first.** It is the durable record of what
is in flight, what is blocked, and what was decided. It is written DURING work, not after,
so a rate-limit kill or a crash leaves it usable.

**Rules for whoever writes here (lead or teammate):**
- Update it as you go, not at the end. A journal written at the end does not survive a kill.
- **NOW** and **BLOCKED** are rewritten in place — they describe the present, not history.
- **LOG** is newest-first and gets **compacted** when it passes ~40 lines: fold resolved
  entries into one line each, delete anything superseded. This file must stay short enough
  to re-read cheaply, or it stops getting read.
- Numbers here are pointers. The authority is `docs/STATE.md` + `docs/evidence/`.
- Never put a result here that belongs in STATE. This is working state, not findings.

**Last updated:** 2026-09-17, on the founder's court-only scope cut. The previous journal is archived at `swingpath:docs/archive/2026-09-17-pre-court-only/.claude/journals/lead.md`.

---

## RESTART CHECKLIST — run this before anything else after a death

A usage limit kills a subagent outright; the session itself resumes
(`autoContinueAtUsageLimit`). The doorman does not know the agent died, because a killed
agent never fires `SubagentStop`. So the corpse keeps holding its slot, and the first
thing you try — re-dispatching the work that just died — is the thing it blocks.

1. **Read the journals.** `.claude/journals/lead.md` first, then the teammate's own.
2. **Reconcile live agents against held slots:**
   ```
   ls .claude/.agent-locks
   ```
   Compare with `ListAgents`. A lock with no matching live agent is a corpse — it frees
   itself after 30 min, or clear it now: `rm .claude/.agent-locks/<id>`.
3. **Check for parked work:** `ls .claude/.agent-queue` — refused dispatches live here and
   survive a death. The directory is gitignored, so nothing else will surface them.
4. **Then resume**, preferring the killed agent's uncommitted files over a restart.

## RUN STATE — the one thing that decides whether to wait for the founder

`NOW` opens with a `RUN-STATE:` line. It has exactly three values. **Read it before anything
else: it is the whole answer to "should I be working right now?"**

| RUN-STATE | Means | What you do |
| --- | --- | --- |
| `RUNNING` | Normal. The default. | Work. Do not ask permission to continue. |
| `KILLED` | A usage limit, crash or closed terminal ended the last session mid-work. | **Resume immediately, without asking.** Then set `RUNNING`. A death is not a pause. |
| `PAUSED-BY-FOUNDER` | The founder said stop. | Stop everything and end the turn. Only the founder's words clear it. |

**A founder pause stops the ENTIRE SESSION — founder ruling 2026-09-05.** Not just agent
dispatch. When the founder says "pause", "im sleeping", "stop for now" or anything like it:

- dispatch no agents;
- **start no background job** — however cheap, however well it seems to fit an unattended
  window. This is the exact mistake of 2026-09-04: "pause im sleeping" was read as "no
  agents", and a 1-3 hour parity run was launched *because* nobody was waiting;
- run no experiment, no training, no analysis, no commit;
- log the pause (below), set `RUN-STATE: PAUSED-BY-FOUNDER`, and **END THE TURN**.

A job that was ALREADY running is left alone — killing it throws away work — but name it in
the pause line and start nothing new.

**Logging a pause is mandatory, in both places:**

1. `NOW`'s state line becomes:
   `RUN-STATE: PAUSED-BY-FOUNDER — <YYYY-MM-DD HH:MM> — "<founder's exact words>" — still running: <job, or nothing>`
2. `## LOG`, newest-first, one line at pause and one at resume:
   `- **<date>** — PAUSED by founder ("<words>"). Left running: <...>.`
   `- **<date>** — RESUMED by founder ("<words>").`

**Only the founder sets `PAUSED-BY-FOUNDER`, and clearing it is not optional** — the moment
they say continue, that line goes back to `RUNNING` in the same turn. A stale PAUSED line is
indistinguishable from a live pause and will stop the next session too; that happened on
2026-09-04 and cost a day. **A kill never sets it** — a kill is `KILLED`, and `KILLED`
resumes on its own.

## REPORTING RULE — founder instruction 2026-09-02

**Do not surface founder-blocked items unless the founder asks for them.** They go in
`docs/DECISIONS_PENDING.md` silently and stay there. Ending a status with "waiting on
you..." is the interrupting this rule exists to stop — the founder asked to be left to
work, and asks for the list when they want it.

Report what was DONE. Keep the queue to yourself until requested.

## RESUME AFTER A KILL — usually automatic; one paste only if the terminal is gone

**This is `RUN-STATE: KILLED`, never a pause. Resume without asking.**

`autoContinueAtUsageLimit: true` is set in `.claude/settings.json`, so a usage limit hit
while the session process is still alive resumes it by itself when the quota rolls over —
no human message needed. Only a CLOSED terminal, a crash or a reboot needs a restart, and
nothing automates that: not this journal, not a scheduled job, not a cloud agent (which
cannot see this local repo). In that case, and only that case, resumption costs one paste:

    /loop Work docs/STATE.md's Open table continuously and autonomously, and ALWAYS
    use the teammate agents for feature work — 3-live-agent project cap, one direct
    child at a time. NEVER stop to ask; append anything needing a founder decision to
    docs/DECISIONS_PENDING.md and keep going. Pre-register a bar before running
    anything, one variable per A/B, a failed bar stays failed, never score a model
    against its own output, inspect the rejects not what a filter kept. Commit to
    master, DO NOT PUSH. Keep this journal's NOW current.

Then, before doing anything else, read in this order:
  1. `docs/STATE.md` — Open table. The live record. Authority for every number.
  2. `docs/DECISIONS_PENDING.md` — what is waiting on the founder, and what was done
     instead so the blocker was not also idle time.
  3. "What has not worked" in STATE — **13 hypotheses died there this week.** Do not
     re-derive them. Each row names the number that killed it.

## NOW — what is running

RUN-STATE: RUNNING — 2026-09-23 — resumed by the founder's handoff ("Do A, but do it for me") — cloud session, branch `claude/swingpath-camera-handoff-rxd7rq`.

**LOCAL HANDOFF 2026-09-23 ~17:00 UTC (founder: "swap back to local environment"; founder asleep, asked for REAL-FOOTAGE video snippets of 5 clips: 2 hard, 2 shell, 1 clay).**
The cloud container cannot reach the clips (YouTube blocked by the environment's network policy; Drive search not enabled; the shell clips are the founder's own recordings anyway). So on the founder's PC:
1. `git fetch origin` then `git checkout -b local-continue origin/claude/swingpath-camera-handoff-rxd7rq` (this branch has everything: jobs 1-4 code, pre-regs, results).
2. `cd backend` then `.venv\Scripts\python.exe ..\tools\court_real_snippets.py` -> `data/output/court_real_snippets/{UHf0LeMU2pg,uR5q2cSM6AY,hillsborough_p02,flexi_joy_p01,sAjkpeRq4P4}.mp4` + `summary.json` (~10 s each; green = whole court verified, amber = near half only, red = not locked). Real footage has NO measured court: these show lock and stability, never accuracy. Show the founder the 5 mp4s.
3. Do NOT re-run jobs 2/3 locally: the cloud session is still running them and pushes to the claude/ branch.

**STATE OF THE FOUR JOBS (all four DONE, cloud, 2026-09-23 ~20:00 UTC):**
NEXT, candidates, none registered: (1) make the tracker snap with the step-aware model (job 1's ~7 cm bias - the biggest open precision problem); (2) re-score the hold-off with the scorer counting fires only on frames that claimed a lock; (3) phone cost of the step-fit (~3-7 s per check; cache photometry from setup); (4) real footage on the PC.
- Job 1 DONE (`c4fd618`): the run-off step breaks the TRACKER too (far_baseline p90 1.46 -> 9.68 cm; 48 steady wrong locks). Remedy hypothesis: snap with the step-aware model, needs its own pre-reg.
- Job 2 = G10 DONE, PASS (`0a00043`): all five bars. Shipped as the default in `d969233` (FAR_LINES_DEFAULT True, stepfit, tol 0.35 px@720). Caveat recorded: on the run-off scene the tracker's ~7 cm bias gives 4-5 steady whole_court locks at 10-12 cm per run.
- Job 3 = G11 DONE, FAIL as registered (`b520cd0`): H1 PASS (0 wrong locks over 30 knocks); H2/H3 fail, all from seed 1300's honestly-failed setup. Hold-off stays OFF by default.
- Job 4 = G12 DONE, FAIL (`6d79714`): height priors 9.0% wrong vs shipped checked fit 4.0%; 0 locked-and-wrong anywhere. Clay / 16-clip real-footage items need the PC.

**WHERE PHASE 1 LANDED (qa-audited 2026-09-22, see evidence QA AUDIT 2026-09-22):**
- G8 at the registered 2.25 px window FAILS bar 3; bar 4 passes only because the check sees nothing on CP1. `FAR_LINES_DEFAULT` stays False.
- The far-baseline failure is the SURFACE/RUN-OFF BRIGHTNESS STEP (+0.9-1.0 px ridge bias, no clutter needed) — NOT the net tape. The lead told the founder 'net tape'; corrected 2026-09-22. The tracking sim has no run-off step, so G8 bars 1-3 and G9 ran without this bias.
- G9: precision passes (p90 1.45 cm), KILL on the silent-failure bar: 5/6 knock frames locked while 41-65 cm out. Cause: 27-34 coherent same-sign sideline outliers on the knock frame bend the pose; it passes because far lines are unchecked and whole-length sidelines are pooled. NOT a lag.
- Open process faults: lock-claim forgery via a self-consistent `whole_court` block; G8 bar-3 OFF-arm file stamped `far_lines: True`; four G8R artifacts written before `0783ff0` (they reproduce bit-exactly).
- Candidate next steps, none scored: a shock-triggered lock hold-off; per-half sideline scoring; a far-line instrument that models the run-off step; add a run-off step to the tracking sim. Never score a remedy on seeds 500-505.

**RESUME POINT — branch `camera3d-pnp-paintfit`, HEAD `572fd6d`, nothing pushed.**
1. **Re-run the suite first** (`cd backend && pytest tests/`, baseline 414 pass / 10 skip / 2
   pre-existing fail). `572fd6d` is backend-dev's MID-FLIGHT work, stopped by the pause: it
   was on Fault A's `cases()` call sites and the pyramid reach. Nothing in it is scored.
2. **Finish the G8 re-decision** (the dispatched brief, in full): fix Fault A (the tool calls
   `paint_check` without `far_lines=True`, so it cannot rerun its own published table);
   re-run BAR 4 — and then 1/2/3 — at the PRE-REGISTERED reach `3 * far_tol` = 2.25 px@720
   rather than the undeclared hard-coded 8.0; re-decide BAR 4 on those numbers and say what
   it means for `FAR_LINES_DEFAULT`; DECLARE the deviation in the evidence rather than
   rewriting it; run the founder's Gaussian-pyramid arm against BAR 4 (it wins on catch,
   1.000 vs 0.9167, and was never scored on that bar); close qa's lock-claim hole
   (`lock_scope: whole_court` + a non-empty `lock_unverified` still claims every line was
   checked); record qa's smaller corrections (6 and 4 segments not 8; +0.094 px with noise;
   394/389 not 400/394; `far_min_z` not inert at tol 1.00; the deterministic profile runs
   at 14.5x CP1's bitrate).
3. Then the queue: clay (`sAjkpeRq4P4` fails, `tc8CGFxyRE8` works); height-prior seeding
   (the founder's Task 2 remainder); the 16-clip probe; the amateur detector.

**The founder's correction is on the record and must not be quietly dropped:** the lead
reported "the net tape defeats the instrument, 369/369" to them, and that verdict is
CONDITIONAL on the undeclared reach widening. Re-state it honestly whichever way it lands.

**Earlier context, still true:** the bounded-state ruling (SPEC §1), pm's roadmap feasibility
check (DECISIONS_PENDING), G7 (an independent on-paint measurement separates right from wrong
cameras; the fit's own cost is inverted), and qa's two audits.

## PRE-REGISTRATION — "P8": DOES 3D COURT MAPPING WORK? Founder ask 2026-09-16, runs AFTER P2.

**Founder, verbatim:** "after its done we need to test to see if the 3d spatial mapping of the court
works." This is capability 1. **Nothing this session tested it** — P1/R1/R1b tested the BALL, and
every one of them was handed a PERFECT court (exact corners, exact hfov). Written before any run.

**What capability 1 claims:** from a four-corner tap plus regulation dimensions, place EVERY line
— including lines outside the frame — and solve a 3D camera. **What pins it:** four coplanar
corners, the regulation doubles rectangle, and the focal length.

**A GAP FOUND WHILE WRITING THIS, and it qualifies every P1 number:**
`bridge.camera_from_court_corners` takes `hfov_deg` as an **INPUT (default 70°)**. Four coplanar
taps do not reliably determine focal length, so the 3D camera is only as good as the hfov it is
given. **P1 handed it the EXACT hfov.** A real app must read it from the device, and framing A is
the 0.5x ultra-wide (P5), which is distorted. **P1's results are conditional on a perfect hfov and
perfect corners — this test is what removes that condition.**

### THREE STAGES, cheapest first. Each is measured against something independent of the model.

**C1 — SYNTHETIC. No footage, no founder. Measured against EXACT geometry.**
Known camera -> true corner pixels -> add TAP noise and HFOV error -> solve -> score every one of
the 16 `court.LANDMARKS` and every line, **including off-frame ones**, as ground error in metres
**perpendicular to each line** (the §3 metric pm proposed), plus camera height and pose error.
- Tap noise sweep at 1920x1080: **0 / 1 / 2 / 4 px**, plus the **measured human corner-click spread,
  ~5.8 px @640 (~17 px @1920)** as the realistic rung. That figure is already published (STATE, court
  auto-detection row) and is used as-is, not re-picked.
- hfov error: **0 / ±5° / ±10°**. Mounts 1.5 / 3.0 / 8.0 m; framing A (ultra-wide) and framing B
  (2x far-half) from P5.
- **BAR (PASS):** at realistic tap noise with exact hfov, **p90 perpendicular error <= 5 cm on every
  line.** Reason for 5 cm: court error ADDS to ball error at the call, so the court may spend at most
  half of SPEC §3's 10 cm budget.
- **KILL:** if **any** line exceeds **10 cm at p90** at realistic tap noise, the court model alone
  can spend the whole call budget there, and capability 1 cannot support SPEC §3 on that line.
- **PREDICTION, written down so it can be wrong:** the FAR lines fail. The same `D²/(f·h)` geometry
  as R1 says one pixel of far-corner tap error moves the far baseline ~**37 cm** along the ray at
  1080p / 3 m. If that holds, realistic tapping cannot place the far baseline to 5 cm, and the
  **setup screen needs a magnified (loupe) tap for the far corners** — a concrete UI requirement,
  not a model change. If it does NOT hold, my geometry is wrong somewhere and that is worth knowing.

**C2 — REAL FOOTAGE, IMAGE SPACE. No founder. Measured against INDEPENDENT HUMAN CLICKS.**
> **WRONG, found 2026-09-16 by qa and verified by the lead: the gold's non-corner keypoints are
> NOT independent clicks.** `gold_label_server.py::cornersToLabel()` derives them as a homography of
> the four clicked corners, so this stage as written is self-graded (rule 1) and returned VOID
> (median 0.048 px@640 = save rounding). The bar text below is left as registered. A runnable C2
> needs a new blind click set of non-corner landmarks.
Use `data/gold/*.court.labels.json` — the **20-file, 640-wide pool that the provenance review found
UNCOMPROMISED** (STATE, "court gold pool's provenance" row: the compromised pool is the separate
`data/<clip>_pts.json` references). Take the four human corner clicks -> build the model -> project
the OTHER labelled landmarks -> pixel distance to where the human clicked them.
- **BAR:** median error **<= 5.8 px @640**, i.e. the four-tap model places the unseen-by-the-model
  lines as well as a human places them.
- **Limits, stated now:** pixels not metres; only lines visible in the frame (so it cannot test
  the "lines the camera cannot see" half); both ends are human clicks, so it measures agreement;
  **8 court gold frames are known mislabelled — recorded, never fixed (rule 10).**

**C3 — THE COURT VISIT (P5). The only METRIC truth.** The 8 fiducial tape marks in
`docs/CAPTURE_PROTOCOL.md` give the **first-ever independent measurement of four-tap accuracy in
metres.** Already designed; no extra work beyond the visit.

**OUT OF THIS TEST, named so it is not forgotten:** the §1 **drift** half of capability 1 (tracking
the court when the phone moves). It waits on the founder's P4(ii) ruling (refuse and re-tap vs
recover), because the test depends on which behaviour v1 has.

**REAL-FOOTAGE INPUT FROM P2 (qa, 2026-09-16):** `demo30` is a slice of `yt_match40`, one static
camera, yet its calibrations fit **1.38 m vs 1.64 m**. C2 should report whether the four-tap
explains a 0.26 m height disagreement on one camera — a court-mapping inconsistency already in hand.

**Owner:** C1 is lead or backend-dev (pure geometry, fast); C2 is qa (independent scoring);
C3 is the founder's visit. **Order: P2 finishes first**, per the founder.

## DECIDED — binds everyone, do not reopen

- **2026-09-18 — BOUNDED STATE, and it supersedes the "no dependence on the previous frame" half of
  this morning's ruling.** Founder, after pm's feasibility check put the measurements in front of
  them (stateless cold path 9.6 s/frame; best measured stateless per-frame precision p90 9.2-10.9 cm
  against a 5 cm target): *"the court is found in the image every frame, but the camera may be
  refined across frames."* Never propagate a saved court, never snap; the independent on-paint check
  runs EVERY frame; temporal averaging is allowed. SPEC §1 and `docs/DECISIONS_PENDING.md` F1 carry
  the binding wording. **The 5 cm / 10 cm floor is unchanged.**
- **2026-09-18 — pm's feasibility check on the founder's four-item roadmap is IN
  `docs/DECISIONS_PENDING.md`.** Headlines: a network predicting camera parameters directly IS arm
  K0 (far baseline p90 6.65 m) so it can only ever be a SEED; roadmap items 1 and 2 are one
  deliverable; item 3's net-clearance check as worded would reject correct courts on every amateur
  mount we own (all 1.36-1.74 m, below the ~2.2 m tape crossover); item 2 unblocks the rest. First
  build, dispatched to backend-dev: does a photometric cost separate the 35 wrong cameras from the
  365 right ones in arm K (pre-registered as G7)?

- **2026-09-18 — TRACKING MUST CONTINUOUSLY DETECT THE COURT, NOT SNAP.** Founder, verbatim:
  *"Remember the tracking shouldnt snap but continuously detect the court"*, and asked which of
  three readings applied; they chose **FULL DETECTION EVERY FRAME** — the court is found in each
  frame with **no dependence on the previous frame**. What existed when they ruled (measured, not
  claimed): `camtrack` re-measures the real paint every frame (0.020 s at 1080p) and re-solves the
  full camera, so it is NOT a homography snap — but its search is ±9 px @1080 around the PREVIOUS
  frame's prediction, which is why an ~85 px knock was lost and never recovered. A full re-fit is
  9.6 s/frame, so the current fit cannot run per frame. **This makes the amateur-trained keypoint
  model the blocking dependency** (upstream CourtNet fires on 2-3 of 14 points on amateur footage;
  PnP needs 5), and per-frame CNN cost contradicts `docs/modules.md`'s "one-time, not per-frame"
  note (STATE: 8 frames once per video; one-in-30 called a 91x regression). Real-clip testing is
  PARKED until the route is designed and pre-registered.
- **2026-09-18 — the founder authorised the agent team for this work** ("Yes use any and all of
  them"). The `.claude/hooks/agent-cap.sh` cap (three live project-wide, lead holds one direct
  child) still binds, so they run in sequence. **2026-09-18: the founder deleted the `research`
  agent and its journal — do not recreate it; the lead does that work. pm checks feasibility
  before development, backend-dev builds, qa verifies.**

- **2026-09-17 — court feature only.** Everything else archived in
  `swingpath:docs/archive/2026-09-17-pre-court-only/`. Only the founder reopens any of it.
- **2026-09-17 — the court is found AUTOMATICALLY** (ML learns the 3D court, finds near and far
  lines, infers unseen end points, SwingVision-style). **Never frame court work around tap precision.**
  The lead missed this more than once; do not repeat it.
- **2026-09-17 — live court tracking continues** when the phone moves: re-fit, never refuse.
- **2026-09-17 — indoor shell is in scope.** The old SEARCH failure there is a hard case to solve.
- **2026-09-17 — the 2026-09-06 court-gold edits (`2e49f38`) were the founder's.** They stand.
- **2026-09-17 — no court visit is possible yet.** No metric real-court truth for now.
- **2026-09-16 — do not answer an obstacle by narrowing the product.** Find how; if something cannot be
  done, say exactly what it would take.
- **Standing:** pushes only on the founder's explicit call, per push. iOS only, A13+, on-device
  forever. Do not reopen the Sideloadly line without the founder.

## LOG — newest first (court only; older entries are in the archived journal)

- **2026-09-23** — RESUMED by founder (handoff with four jobs; "Do A, but do it for me cuz im going to the gym"). Cloud session: Python 3.12 venv, numpy 2.5.3 / scipy 1.18.1 / opencv 5.0.0 — not the Windows venv, so numbers are re-baselined here before any comparison.

- **2026-09-22** — PAUSED by founder ("After QA does the checking lets pause and see if things work"). Left running: nothing.

- **2026-09-22** — RESUMED by founder (a four-phase plan; Phase 1 dispatched to backend-dev).

- **2026-09-19** — PAUSED by founder ("Pause the task I ahve to turn pc off"). Left running: nothing; backend-dev stopped mid-G8-re-decision, partial work committed UNVERIFIED as `572fd6d`.

- **2026-09-18** — PAUSED by founder ("Pause first - I want to sleep and turn off the PC"). Left running: nothing.

- **2026-09-17** — **3D court camera built on branch `camera3d-pnp-paintfit` (not pushed).** Founder task: 2D
  homography → 3D PnP + keypoints. Scoped with the founder: court only (ball solver dropped), keypoints
  only SEED, detector = interface only. `camera3d`/`paintfit`/`camtrack`, `court.LANDMARKS_3D`,
  `setup.camera`. Pre-registered in `617cd96`. **G1 arm K PASS** (far baseline L 4.43 cm) **with an
  8.75% wrong-camera tail**; **G2 K0 KILL** (6.65 m); **G3 tracking KILL** (knock lost; one seed re-locked
  on wrong paint while reporting `tracking`). CP1's x265 is non-deterministic (follow-up task offered).
  No real footage: this repo has none and settings forbid reading the main repo's. Evidence:
  `docs/evidence/court-camera3d.md`. **Queue item 3 (tracking precision) now has a number; item 3's
  replacement tracker is not ready.**

- **2026-09-17** — **qa audit of CP1: PASS QUALIFIED** (`b308396`, `docs/evidence/court-fit-cp1-qa.md`). No truth
  leak, bit-identical reproduction, seed-1 spot check passes. Qualified: one dev=score camera pose; undeclared
  shared assumptions (blur on the fitter's grid, linear sensor, flat chroma, step at outer paint edge); far
  margin ~1.4 cm vs a 2.65 cm codec cost; 1% of trials past 5 cm on the far lines. **Before stage 2,
  backend-dev must:** pass `cx` as W/2 (latent A9 leak), fix the duplicate `seed` stamp key and stamp the
  commit at run START, key the render cache on code, add an undeveloped camera pose, run a real-phone-bitrate
  arm. STATE row and CLAUDE.md updated. Founder said "push to https://github.com/xrich8x/swingpath-court".

- **2026-09-17** — **CP1 stage 1 reported PASS** (backend-dev; frozen `4ac52fc`, results `99e1812`): all 14
  lines within 5 cm p90 on arm P, worst far baseline 3.58 cm (L) / 0.97 cm (M); codec off 0.93 cm; route kill
  not fired; suite 721/4. **NOT relayed as settled yet: qa dispatched to audit it** — one agent wrote both
  renderer and fitter, and a docstring near line 274 says f and principal point are "held at truth". Findings
  for stage 2: far baseline sits on the surface/run-off boundary, so paint contrast (kappa) must come from the
  near lines (5% kappa error ~1.3 cm); A5 (10 cm baseline paint) is the highest-risk next arm. When the court
  repo is pushed, CP1 must be added there with its `height_curve` import repointed to `court_camera`.

- **2026-09-17** — **Court-only GitHub repo `swingpath-court`: BUILT LOCALLY, NOT YET ON GITHUB.** Founder
  asked for "a clone of the feature in github that we can push to only for this feature, call it
  swingpath - court" (GitHub forbids spaces, so `swingpath-court`, private like `swingpath`). One commit
  `0a40e67`, 334 files, at the session scratchpad `.../scratchpad/swingpath-court` — **the scratchpad is
  session-scoped; if it is gone, rebuild with `.../scratchpad/build_court_repo.py`** (then delete the six
  ball tests and two ball evidence files as that commit did). Court camera helpers lifted verbatim into
  `tools/court_camera.py`; C1 reproduces BYTE-IDENTICALLY there. Suite 315 pass / 10 skip / 5 fail (the 5
  need local footage). **Blocked on creating the empty GitHub repo:** `gh` is not installed, the GitHub
  connector needs sign-in, and Claude in Chrome is not connected. Project settings deny writes outside
  this folder, so no sibling working folder was made. CP1 resumed after a usage-limit kill.

- **2026-09-17** — **Scope cut to the court feature** at the founder's instruction. Non-court
  instructions archived from CLAUDE.md, SPEC, STATE, DECISIONS_PENDING, this journal, the five agent
  definitions, four agent journals, the agent memory indexes, the ball/measure/data/platform CLOSED
  lists, the capture protocol, LABELLING, REVIEWER, README, USER_GUIDE, SETUP_PROMPT, ML_PLAYBOOK and
  modules. `docs/evidence/` and `data/output/` untouched (records, not instructions).
- **2026-09-17** — Founder rulings: automatic court (ML), live tracking continues, shell in scope,
  gold edits theirs, no visit yet. Applied to SPEC, CLAUDE.md, STATE, court/CLOSED.md.
- **2026-09-17** — the research note's court-precision routes landed and were verified (arithmetic; Apple's
  calibration-data condition). CP1 specified; two pre-run fixes (400 trials; staged build).
  `backend-dev` dispatched on CP1 stage 1.
- **2026-09-16** — **P8 C1: KILL FIRED.** A four-point court misplaces every line past 10 cm at
  realistic corner error; the far baseline needs ~0.1 px corners. **P8 C2 VOID** — the court gold's
  non-corner keypoints are computed from four clicks.
