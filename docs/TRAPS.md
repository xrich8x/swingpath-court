# TRAPS.md — process failures this project has hit more than once

Each one cost real work. They live here rather than in docs/STATE.md because they
have a different lifecycle: STATE is *state* (what is true now, rewritten as
it changes) while this is *history* (append-only, corrected only by marking a
correction). Keeping them in one file made SCOREBOARD 430 lines, of which 202 were
these, and the mixture is what let a correction in one section rot a copy in
another.

**APPEND-ONLY. IDs are never reused and never renumbered.** `T01`-`T22` are
permanent identifiers, cited from 13 files including code (`backend/run.py`,
`backend/swingvision/ball.py`, two test files) and from CLAUDE.md,
PM_REVIEW_PROMPT.md and the pm-review skill. They are not in file order and that
is fine — they are identifiers, not an ordering. A withdrawn or superseded trap
keeps its ID and gets a correction note; its ID does not pass to anything else.

**Re-keyed 2026-08-26** from bare numbers to `T##`. The old numbering had run out
of shape: it carried a `5b`, so a "21 traps" count was wrong, and a bare `15` was
ambiguous with the many other numbers in this file. The mapping preserved every
old number's identity — old `n` became `T0n`/`T{n}` — with the single exception
of `5b`, which took the new id **T22** rather than shifting 16 other IDs and
silently changing what every existing citation pointed at.

**Adding one:** a mistake earns a trap the SECOND time it happens, not the first.
The first time is bad luck; the second is a pattern the process failed to catch.
Append with the next free ID (**T23**) and say what it cost.

Covered by `.claude/hooks/withdrawn-guard.sh` like every other live doc: a figure
listed in docs/STATE.md's "Withdrawn figures" table may not appear here without a
withdrawal marker in the same block.

---

T01. **Quoting a `--frame-step 1` number as shipped behaviour.** It doubles `fps_eff` and
   every time-threshold's frame count. Two wrong mechanism conclusions came from this —
   the second *after* the rule was written down. Use step 1 only for A/B deltas and for
   clips whose gold parity demands it.
T02. **Trusting a stale cache.** Perception caches are calibration- and
   settings-dependent. A whole set of published figures was withdrawn over this.
   Re-perceive; the provenance stamp exists to catch it.
T03. **Unscaled pixel constants.** Anything tuned at 720p silently deletes real balls at
   1080p. Scale by `frame_height/720` — except the fixture radius, where measurement
   says otherwise.
T04. **A scorer that mis-aligns frames.** Gold frame `f` compared against track index
   `f//step` without checking `f` was processed understated the tracker for a whole
   session and forced a retraction.
T05. **Measuring against a model instead of a human.** Every leaderboard this project
   built before the gold set was measuring its own reflection.
T22. **Trusting the flat z=0 projection for an AIRBORNE ball.** Measured against
   simulated truth: back-projecting the whole arc onto the court plane and
   integrating path length reads **+72% median, p90 +25,000%** — a near-grazing ray
   runs to infinity. Under 1 m of height it is +15% bias. This is precisely why
   `gate_ball_to_court` and the physics arc fit exist, and why the `approx` speed
   path is a floor rather than a measurement.
T06. **Letting the test set into the training set.** The ball side has enforced a one-way
   gold/train split since Session 2. The COURT side never did: **17 of the 20
   hand-labelled court gold clips were also in `data/court_dataset/`**, and
   `train_courtnet.py` had no guard at all, so every figure in
   `data/gold/court_scores.md` was the model scored on its own homework. Fixed
   2026-08-06 with `data/gold/court_split.json` + `assert_no_court_gold_leak()`. The
   lesson generalises: a discipline enforced on one model is not enforced on the
   project. Check each new model for its own guard.
T07. **Fanning out to parallel agents.** The bottleneck here is one GPU and one gold set,
   not context. Two multi-agent research runs burned ~971k tokens and returned **zero**
   results; the same research done inline took two searches and four fetches.
T08. **Scoring on a population where the decision is easy.** Pooled line-call agreement
   reads **87–99%** across camera heights from 1 m to 12 m — it cannot tell a worthless
   mount from a good one, because most simulated bounces land nowhere near a line and
   metres of error still call them correctly. Restricted to bounces within 0.5 m of a
   line it reads **54% → 81%** over the same range. This is the same shape as
   "per-frame false-fire is not the product" (Session F): *pick the population where
   the answer is actually in doubt.* And **always state the majority-class floor** — on
   that population, answering "in" every time scores 56.2%, so the 1 m camera's 54% is
   not "slightly better than chance", it is worse than a constant.
T09. **Calling "no effect" without checking the test could have seen one.** The solid-ghost
   gate has been run **nine times** and never once alongside its own resolution. It is a
   count of ~14 out of **74** no-ball frames, where sampling alone moves the count by
   **±3.4**: near-elimination is detectable (needs 62 frames), but *halving* the ghost
   rate needs **212** frames and a 30% cut needs **656**. So nine null results license
   only "nothing has come close to eliminating the ghost ball" — not "none of these did
   anything". `tools/gate_verdict.py` now prints the required-n next to the verdict so
   the claim can never again outrun the evidence. Contrast the detector table, where 204
   no-ball frames over six clips resolved an 11.7-point effect comfortably: the method
   is fine, the *chain* metric is just restricted to three calibrated clips.
T10. **Running an A/B with more than one variable.** `train_ballnet.py` had **no seed** —
   no `manual_seed`, no `random.seed` — so Session I's two arms differed by weight
   initialisation, batch order and augmentation draws as well as by the flag under test.
   The tell was the three clips disagreeing in **sign** on every axis. Same family as the
   `ballnet_v21.pt` provenance gap that forced the session to spend an hour training its
   own control. Fixed with `--seed` and `recipe_stamp`; the standing rule is that a
   checkpoint must say how it was made, and an arm must differ from its control in
   exactly one recorded way.
T11. **Reading a clip-level correlation as the cause.** The far-court pilot's clips split
   cleanly into "human agreed with the tracker to 0.6–7.2 px" and "human was 112–645 px
   out", and the split was attributed to the four clips carrying a burned-in scoreboard.
   It was really the four clips where the tracker had been tracking a **ball** rather
   than a wall — two of the "HUD" clips have no overlay at all. The fix that followed
   from the wrong cause (mask the graphics) is worth 5 of 36 labels; the fix that follows
   from the right one is worth 21. **When a per-clip split explains a result, check the
   per-FRAME pixels before naming the variable** — clips differ in many ways at once, and
   n=12 clips is one observation of each.
T17. **Trimming a clip renames it, and the gold guard matches on the NAME.** Caught
   live, not hypothetically: gold clip `hd_shortcourt_1` is `7 UTR vs 8 UTR
   [UHf0LeMU2pg].mp4`, a training set had been built from `UHf0LeMU2pg.mp4` — the same
   match, cut shorter — and `assert_no_gold_leak` reported **no leak**, because the
   filenames differ. Every one of the 12 clips trimmed that day carried the same hole,
   so the exam set was one training run away from being inside the revision. The guard
   was correct for the world it was written in, where `data/` held whole recordings
   under their own names; cutting clips created a lineage the identity check could not
   see. Fixed by recording {cut: source} in `data/train_clips/lineage.json` at cut time
   and expanding gold through it. **A provenance check keyed on a name breaks the moment
   the pipeline gains a step that renames things** — and the new step will not know it
   is supposed to tell the old check.
T16. **A default that is silently wrong for a whole new pool.** `validate_new_clip`
   looked for a clip's video at `data/<tag>.mp4` only, and fell back to "assume 1280x720"
   when it missed. The new training footage lives in `data/train_clips/` and is all
   1080p, so every calibration the user hand-placed audited at the wrong resolution and
   came back **DEGENERATE, fit residual 15.9-56.3 px** — nine of them, i.e. the entire
   session's manual work. At the true 1920x1080 the same files read **0.3-6.5 px, six
   PASS and three LOW-CAMERA**. Corners are pixel coordinates, so every geometric check
   is resolution-dependent; the fallback was reasonable when `data/` held every clip and
   became a lie the moment a subdirectory appeared. It now searches the directories clips
   actually live in. **A fallback that cannot tell "not found" from "found and fine" will
   eventually indict good work** — and the tell was that ALL of them failed, which is
   almost never what a real quality problem looks like.
T15. **Re-implementing the thing you are trying to predict.** `audit_new_clips.py` was
   written to tell a user which new clips will auto-calibrate. Its first version drove
   `auto_fit_frame`/`consensus` by hand instead of calling `pipeline._sample_calib_frames`
   + `courtfit.fit_video_frames`, and sampled 15-85% of the clip where the pipeline
   samples 2-98%. It reported **1 of 12** clips calibrating; the shipped path gets more,
   and two clips flipped from refuse to accept once it called the real code. An audit
   that disagrees with the product is worse than no audit — it sends you to hand-calibrate
   clips that calibrate themselves. **Predict a behaviour by invoking it, never by
   re-deriving it.** Related: the same tool first reported a confident camera height
   (4.35 m, close calls 74%) from a **2-of-8** consensus, against a bar measured at 6 —
   a wrong court yields a wrong height that looks exactly like a right one.
   **IT HAD ALREADY HAPPENED IN THE SHIPPED CLI, and nobody looked** (found 2026-08-14).
   `run.py check` — the user-facing pre-flight — read ONE frame through
   `detect_court_learned` -> `detect_court`, while `analyze` runs `courtfit`
   consensus over 8 frames and accepts only >=6 agreeing. Measured on demo30 with no
   keypoints: the old check returned a court and graded it `[POOR] elevation 2.68`,
   while analyze **refuses the clip outright**. So the pre-flight's verdict was about a
   court the product would never use, and a user could act on either answer. Fixed by
   calling `pipeline.calibrate_video` itself. **The tell was that the audit tool got
   this exact fix a session earlier and the CLI was never checked for the same shape** —
   when a trap is found in one caller, grep for the other callers of the thing it was
   re-deriving, because the pattern is a habit, not an incident.
T14. **Judging a filter by what it KEPT.** Three versions of the play-segment finder
   were written for the nine new match uploads. Each reported a plausible kept-percentage
   and each was wrong in a way the percentage could not show: version 1 discarded real
   tennis on 6 of 9 clips, version 2 on 5 of 9 — including **ten minutes of rallies from
   one clip while reporting 58% kept**. Both were caught the same way, by rendering the
   frames they THREW AWAY rather than the ones they kept. The root cause was shared:
   "looks unlike the average frame" is not "is not tennis", and over half an hour outdoors
   shadows crawl and exposure drifts. The fix was to detect the thing being REMOVED (a
   face filling the frame) so the failure mode flips to keeping too much. Even that has
   blind spots the count cannot reveal — a face in profile, and a sponsor read that cuts
   to close-ups of a book with no face in it at all. **Always inspect the rejects.**
T12. **Scoring a HUMAN against a model, which is self-grading wearing a disguise.** The
   far-court queue accepts a labelled gap when the human's click on an anchor agrees
   with the tracker's position there. On the masked re-run that agreement rate went
   **42% → 75% on the same twelve gaps** — and inspection showed at least two of the
   flips were the human clicking a static wall mark or a window, on one clip the *same*
   mark the tracker had locked onto, agreeing to 2–5 px. A labeller who cannot find the
   ball clicks the most ball-like thing in the frame, which is what the detector locked
   onto for the same reasons, so agreement rises while truth does not. The tell was
   motion: human clicks moved **1–8 px** across a gap where the tracker's own prior moved
   **60–583 px**. Rule 1 of ML_PRACTICES applies to human graders too — *what independent
   ground truth is this measured against?*
T13. **Reusing a verification method across a change of scale.** The round-trip check for
   "is this built sample the frame the human labelled?" reached for the dHash that
   verified the window mapping in Session I. That question was ±1600 frames and a
   different scene; this one is ±1 frame on a 60 fps static court, where **every
   candidate frame reads 14 bits** and JPEG plus the 1080p→512×288 resize contribute 6–8
   of their own. The test would have passed identically whether the mapping was right or
   wrong. Replaced with an argmin of mean-abs-diff over ±3 frames, which resolves it —
   and which reports its margin, so a frozen scene declares itself unresolvable instead
   of quietly passing.
T18. **Reading a crop as if it were the frame.** Reviewing arm B's 166 false fires from
   140 px context tiles, four `am_hard_utr` locks looked like close-ups of a face and
   were written up as "the clip cuts to commentary — footage no ball detector can be
   scored on", with a follow-on recommendation to trim the old gold clips. Pulling the
   **full** frames killed it: every one is an ordinary wide tennis shot with a player
   walking past the near corner, whose head fills a 140 px tile taken from 1920×1080.
   The shipped face test agreed — 0 big faces in all 308 no-ball frames — and the
   correct response was to believe it and go look, not to assume the cascade had missed
   a cap and sunglasses. Same shape as calling the user's hand calibrations misplaced
   from 560 px thumbnails, twice. **A crop is evidence about a crop.** Before any claim
   about what a frame *is* — a cutaway, an overlay, a scene cut — render the frame.
   (The overlay version of the same hypothesis was then killed by measurement rather
   than by eye: several gold clips do carry a burned-in scoreboard, but only **1 of 166**
   locks lands in the top-left corner where they sit, and 17 anywhere in the outer 12%
   band. Burned-in graphics are not where these false fires come from.)
T19. **Reading a detection RATE as evidence the detector found the right thing.** Session G
   part 4 reported "stock racket detection genuinely works on this footage — a racket is
   found on 64–100% of sampled frames per clip, so the ceiling here is the CRITERION, not
   the detector", and that sentence shaped two sessions of follow-up. Re-measured: on the
   clip where racquet confusers dominate, a racket is found on 79.5% of frames and sits
   **737–869 px** from the lock every time. It was finding the near player's racket while
   the ball detector fired on the far player's. A coverage percentage answers *did the
   model output something*, never *did it output the thing this argument needs*. **Score
   the association, not the presence** — distance from the lock to the nearest box was one
   line of code and reverses the conclusion.
T20. **Inferring a defect's SIZE from an assumption about the footage.** Rally
   segmentation was written up as "63 rallies where reality is 8–15 points, the score is
   badly wrong" — from a real symptom (0 of 62 inter-rally gaps ≥10 s) plus an unstated
   assumption that the clip contained unedited between-point dead time. It does not: only
   **12%** of yt_match40's human-labelled frames are no-ball, where an unedited match is
   mostly dead time. The replacement figure — **~35–40 points against 63 rallies, a
   1.6× over-split rather than 5×** — was read off the clip's own burned-in scoreboard
   and is itself **WITHDRAWN (2026-08-17)** with the rest of that family, so the
   over-split is now **UNSIZED**. Two further numbers in the same write-up were
   artefacts: the "median gap 0.00 s" measured `start_s − end_s` where `end_s` is the
   last shot's *bounce*, not the criterion the code splits on. **Before sizing a defect,
   establish what the correct answer is** — and note this trap has now fired TWICE on
   the same defect, the second time on its own correction. The closing advice used to
   read *"it was sitting in the pixels of three clips, free"*; it was free because it
   was somebody's **data entry**, not the court.
T21. **Re-deriving a rule instead of sharing it — then trusting the copy over the pixels.**
   `build()` numbers each training triplet by its POSITION in the usable-frame list and drops
   `unsure` labels; the round-trip gate re-derived that list and KEPT them, so on any clip
   with an unsure label every later sample was checked against the wrong source frame. It
   presented as a clean, alarming **+2/+3 frame offset with a 20–30% lead** — exactly what a
   real data corruption looks like — and the first response was to write it up as one and
   plan to exclude the clips. What settled it was **sequential decode from frame 0**, the one
   read path that uses no seeking: `build()` was exact to **MAD 0.0000**. The tell had been
   free all along — the only two clips that failed were the only two with an `unsure` label,
   and all 19 with none passed. **When a checker and the thing it checks disagree, the checker
   is a suspect too**, and a rule with two implementations will eventually have two meanings.
   Now one function, `labels_to_dataset.usable_frames`, called by both, with an assertion in
   `build()` that it still selects exactly what gets written.
T23. **Trusting a calibration AUDIT that never looks at the frame.** `data/yt_match40_pts.json`
   is stamped **PASS, fit residual 0.9 px**, and all four of its clicked corners sit on blank
   run-off asphalt, on the hedge, and on the fence *behind* the court — not one is on a court
   line (`data/output/p0_3_calib_corners_yt_match40.png`). The residual only asks whether four
   points form a plausible projective image of a regulation court, and four arbitrary points in
   a sane trapezoid do. The cost: the pipeline's net line landed 35–75 px low, so
   `select_players_on_court` labelled the NEAR player FAR whenever they stood forward of it,
   and **P0-2 published that mislabel as an 11.0% far-player detection rate** — `far_kpts`
   non-null on 1125 of 10268 frames, exactly 11.0%. It survived a written gate, a pre-registered
   sweep and a published evidence file. This is the SECOND time a committed `*_pts.json` has been
   silently wrong; the first family was caught by residuals (38–565 px, stamped DEGENERATE), and
   **this one is invisible to that test by construction.** The audit's one real signal was
   ignored: it reported an **11.3 m camera** for a clip that is plainly a tripod behind a public
   court, and the pixels say ~2 m. **Verify a calibration by rendering the clicked corners on the
   frame, not by reading its residual** — and treat an implausible camera height as a failure,
   not a footnote. Related: T19 (a rate is not evidence the model found the right thing) —
   here a rate was not even evidence about the right PERSON.

T24. **Trusting a tool's own docstring about whether it has been RUN.** `eval/movers.py`
   opens with "UNRUN. Written 2026-08-24; no number in this repo has been measured with it
   yet." That was true for about a day. Its primitives ran the **same day** via
   `eval/candidate_audit.py --movers` (which imports `movers` directly) and
   `eval/foot_gate_power.py`, over 30 clips — and **two rows in `docs/STATE.md` already carry
   the results**: `movers.crop_row` at k=1.0 is "safe but inert", and the player-foot gate is
   "DEAD — no discriminative power", sign backwards, over 216 locks. Nobody went back and
   edited the docstring. The lead read it, believed it, and told the founder their idea was
   "half-built and never tested" — when the aggregate form of it was already a measured
   negative sitting in the table the lead had read minutes earlier. The STATE rows do not say
   "movers" in their titles, so reading the table was not enough either.
   **A file's own header is a claim about the past, not a fact about the present. Establish
   run history from `git log`, from what imports it, and from STATE — never from the prose
   inside the thing you are asking about.** This is the second of its species: T02 is trusting
   a stale *cache*, this is trusting a stale *docstring*. Related: T21 (trusting a copy of a
   rule over the source).


T25. **Treating a search tool's "no matches" as evidence something does not exist.** Twice on
   2026-09-04, the harness `Grep`/`Glob` tools returned *no matches* for content that is
   plainly in the repo. The researcher hit it first — Grep/Glob "would not search directories
   in this session", working only when `path` pointed at a single known file — and burned tool
   calls rediscovering it. The lead then hit the same thing hunting `verify_court`: `Grep` for
   `verify_court` returned **"No files found"**, and for `def verify_court` **"No matches
   found"**, for a function that is defined at `backend/swingvision/calibration.py:1087`, is
   called from five sites, and is named in `docs/STATE.md`. The lead had already started
   writing up "the STATE row names a criterion that does not exist in the code" as a finding.
   `grep` via Bash found it immediately.
   **A negative from a search tool is a claim about the tool, not about the repo.** Before
   reporting that something is absent, missing, renamed or deleted, confirm with a *second*
   mechanism — `grep` via Bash, `git log -S`, or an import — because absence is exactly the
   result that a broken searcher and a true fact produce identically. Prefer Bash `grep` in
   this repo. Related: T24 (a stale docstring is a claim about the past), T02 (a stale cache) —
   all three are the same failure of trusting one witness that has no way to say "I don't know".


T26. **An agent PLACING ground truth and then being the sole judge of its own placement.**
   Commit `3399d58` (2026-08-11), "Ten hand-placed court calibrations for the new training
   pool", is written in the first person by a Claude agent and certifies its own work: *"all 10
   were verified by eye with the court projected back onto the frame."* That eye was the
   agent's. The same commit message then retracts itself — *"RETRACTED: I reported uR5q2cSM6AY
   (9.3 px) and HoHxFSX_gLk_s2 (1.0 px) as misplaced. Both are correct. I judged them from
   560-px thumbnails"* — so the batch shipped with a written admission that its verifier had
   already changed its mind once at a different zoom level, and "verified by eye" was published
   as a confidence signal anyway.
   **How it entered the gold pool wearing a human label:** `eval/run_refs.py::references()`
   gates the scoring pool on `"_exact": true`, and its docstring asserts that flag means *"the
   user DELIBERATELY placed these corners... a human placement, not a detector output."*
   It means no such thing. `tools/court_setup_server.py`'s `/api/save` writes `_exact` whenever
   the browser's **Shape lock checkbox happened to be off**. The flag carries a claim about
   *who placed the corners* that no code anywhere ever established.
   **The cost, measured 2026-09-09:** the founder reviewed the 28 rendered corner sheets and
   marked **10 placed wrong**; **8 of those 10** trace to `3399d58` / `ac94aab`, and **9 of the
   20 clips in the scoring pool** come from that batch. Wrong-rate inside the batch **~73%**,
   outside it **~12%**. Every court figure scored against that pool is provisional until it is
   re-established — the 40% proposal recall, the 12/20 gate, shell 1/5.
   **This is the THIRD time a committed `*_pts.json` has been silently wrong** (T23 counts the
   first two) and the first where the cause is named: not a bad click, a bad *chain of
   custody*. Rule 1 — never let a model grade its own homework — is read as being about
   metrics. This is the same violation one stage upstream, in the LABELS, where it is worse:
   a model that produces the reference and then certifies it has graded itself before any
   metric exists to be checked. **A label's provenance is part of the label. Record who placed
   it, by what method, and who verified it, IN THE FILE — a commit message is not a data
   field, and "hand-placed" in prose is not a fact about the JSON.** Where an agent must place
   candidates, a human verifies before they are ever called ground truth. Related: T23 (verify
   by rendering the frame — necessary, but it matters *whose* eye does the looking), T24 (a
   claim in prose about the past is not a fact about the present), T19.


T27. **Reasoning about a filter's REJECTS from properties measured on the chain's SURVIVORS.**
   It fired twice inside a single session (2026-09-10), on two different people, against the same
   stage, and both times it was the load-bearing argument for building something.
   **First**, the lead's case for widening the innovation gate: *"Session I measured all 19 chain
   false locks sitting 208-829 px off the track, so ghosts at 208+ px still cannot enter a gate
   widened to ~45 px."* Those 19 are the ghosts that **survived the whole chain and reached the
   rendered output**. The gate's own reject-ghosts had already been measured, in
   `docs/evidence/smoother-gate-backward-readmit-separation.md` §5, at **24.0, 30.3, 49.8 and
   386.2 px** - three of the four squarely inside the radius the widen would have opened.
   **Second**, the researcher's case for rejection-run coherence: *"all 19 chain false locks have
   `run_len = 1`, so a single-frame ghost cannot form a coherent run and the ghost population is
   excluded by its own measured property."* Same 19 clips of evidence, same swap. Measured the
   same day: **19 of 28 pooled ghost rejects (68%) sit in runs of >= 2.** The mechanism died on
   its pre-registered null control (p = 0.105 / 0.589 / 0.585).
   **Why the swap is so easy to make.** Survivors are the population that gets *written up* -
   they are what the product renders, so they are what evidence files describe and what an agent's
   memory carries. The rejects are invisible by construction: nothing downstream ever sees them,
   so no artefact describes them unless someone deliberately instruments the stage. Reaching for
   the documented population is the path of least resistance, and it silently answers a different
   question. **Survivorship also runs the wrong way for safety**: a ghost survives the chain
   *because* it was extreme enough to hold a lock, so survivor-ghosts are systematically further
   out and better-separated than the ones a gate is actually deciding about. Every bound derived
   from them is optimistic.
   **The rule: before quoting a property of a population, name the selection that produced it, and
   check it is the selection your decision operates on.** If you are changing what a filter
   ACCEPTS, your evidence must come from what it REJECTS - and if nothing measures that, the
   instrumentation pass is the first piece of work, not the last. Here it cost two proposals and
   was settled by one diagnostic run that had been pre-registered to answer something else.
   Related: T19 (a detection rate is not evidence the model found the right thing) and T08 (pick
   the population where the answer is actually in doubt) - all three are the same failure of
   scoring on a population that was selected by the very property under test.
