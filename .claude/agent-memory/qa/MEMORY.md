# qa memory

> **SCOPE: court feature only (founder, 2026-09-17).** Non-court memories were moved to `archive-pre-court-only/` in this folder — history, not work. The full previous index is at `swingpath:docs/archive/2026-09-17-pre-court-only/.claude/agent-memory/<agent>/MEMORY.md`.


Inherited 2026-08-28. The gate definitions, known-hard areas and checker quirks are in
this agent's system prompt — read it first; it is the authoritative copy.

## Live results to check against

- **P0-2 pose downscale: FAILED its gate, 2026-08-27.** Far-player detection
  `yt_match40` 11.0% @1280 -> 0.1% @640 -> 0.0% @384; `am_hard_utr` 1.0% -> 0.0% -> 0.0%.
  Near player barely moves. Gate allowed 2 points absolute. Recorded as a measured
  negative; do not let it be re-proposed as untested.
- **P0-3 crop-around-contact: UNMEASURED, not negative.** A first attempt reporting 78.8%
  was invalidated on visual inspection — the 448 px box catches the near player
  regardless, and the contact population was wrong. Any retry needs a correct population.
- **Core ML export needs macOS.** `coremltools`' Windows wheel cannot serialize weights
  (`BlobWriter not loaded`). `.github/workflows/coreml-export.yml` runs it on a GitHub
  Actions macOS runner; untested end-to-end as of 2026-08-28.

- **Line-call margin curve measured, 2026-08-28** (pm queue item 5).
  below the majority floor under 10 cm from a line, clear it from ~20 cm; recommended
  band 0.20 m, refuses 39% of close (0.5 m) calls. Not built, measurement only.

- **Doorman (concurrency cap) + journal system verified, 2026-08-28.**
  [agent_cap_doorman_verified.md](agent_cap_doorman_verified.md) — cap/fail-open/
  parking/hand-back/no-double-fire/TTL-sweep/wiring/journals all measured PASS by
  feeding synthetic hook payloads directly to `agent_cap.py`. Three real gaps found
  (not fixed): a TOCTOU race at the PreToolUse check (no reservation side-effect,
  demonstrated), a `safe_name()` collision that undercounts live agents (demonstrated),
  and silent >8000-char prompt truncation in the Stop-event hand-back (queue storage
  itself is not truncated). Also: this session's declared cwd was a decoy/stale
  subfolder, not the real repo root — see that file for the path note.

- **Court-mask-sweep parked item verified DEAD, 2026-09-02.**
  [court-mask-sweep-item-is-already-shipped.md](court-mask-sweep-item-is-already-shipped.md)
  — the "12 vs 11" sweep result is the already-shipped surface router (f41a489,
  2026-08-21), re-banked not re-proposed; 3 independent runs agree 12/20, 0 wrong,
  median 8.1px range 1.7-13.9 vs human clicks. Evidence committed: docs/evidence/
  court-mask-sweep-item-is-already-shipped.md (333d38b).
- **Process trap: ending a turn to "wait" on a backgrounded Bash job does not keep you
  listening for its notification.** [background-wait-does-not-survive-ending-turn.md]
  (background_wait_does_not_survive_ending_turn.md) — poll in a foreground loop within
  one tool call instead; hit this on the court-mask-sweep task, coordinator had to
  intervene.

- **int8 ball-graph parity headline verified 2026-09-03, close-race mechanism corrected.**
  — 5/528, 3/6 clips CONFIRMED exactly; Arm B/C mitigation rejections CONFIRMED from
  hashes+op counts+blob dumps; but the "close race" 0.15px threshold was picked after
  seeing the 5 failures — "all 5 are close races" is NOT threshold-robust (2/5 at 0.05),
  while "0 close races in the 2 clean clips" IS robust across 0.05-0.30.

- **seen_frac gate evidence verified 2026-09-03, positive control partially passes.**
  (gate doesn't predict error, INDETERMINATE, accept-precision≈base-rate) CONFIRMED via
  independent rebuild; positive control shows the harness responds to an injected true
  correlation on all 3 clips but weakly/saturates on 2 of 3 camera geometries; band-ratio
  DIGITS diverge from backend-dev's (one clip flips sign) — see
  the general lesson (classifier-shape numbers reproduce, fine per-clip ratios don't).

- **Ground-plane-blindness claim tested via synthetic corruption, 2026-09-05.**
  [ground-plane-blindness-narrows.md](ground-plane-blindness-narrows.md) — NARROWS: the
  claim's own anchoring anecdote (yt_match40 residual 0.0/height 1.64/coverage 0.944) was
  itself WITHDRAWN as a correct calibration the same hour it was written — no confirmed
  wrong court in this repo has ever scored well on ground-plane stats, and the camera-height
  screen DID catch the one real confirmed-wrong case (11.3 m). But the core mechanism
  reproduces synthetically: depth-anisotropic corner compression is invisible to every
  SHIPPED gate across the full tested range on 2 clips, while isotropic scale IS caught by
  coverage (confirms researcher's aniso/iso distinction) — and a computed-but-unused
  quantity (fitted hfov from the same cam_fit_quad call) would catch the compression at
  ~15% severity, so "blind by construction" overstates a reporting gap as a geometric law.

- **Clean-plate/MTI vs the near-baseline-only solve, measured 2026-09-06.**
  [cleanplate-mti-near-baseline-measured.md](cleanplate-mti-near-baseline-measured.md) —
  weak/mixed: only 1 of 8 double-locked clips clears the founder's <=2px bar on both
  near-baseline row+width with the plate; width sharpens on a majority (5/7), row does
  not (3/7); shipped n=80/span=60 fails a pre-registered "as well as n=150/span=90" bar
  decisively on width. Late-discovered protocol mismatch with backend-dev's px@640/
  raw-detector measurement means my numbers aren't directly poolable with theirs —
  written up as an honest correction, not hidden. Net-line side corrected: NOT
  actually unmeasurable (projectable via homography), just not done this run.
- **Process: SendMessage tool absent + duplicate dispatch, 2026-09-06.**
  [dispatch-collision-cleanplate-task.md](dispatch-collision-cleanplate-task.md) —
  a brief claimed I had SendMessage; I didn't. Also backend-dev was independently
  given the identical deliverable path concurrently. Check a coupled teammate's
  journal EARLY for both its protocol and a path collision, before spending budget.

- **Court proposal recall measured 2026-09-09 — the SEARCH binds, not the vote.**
  [court-proposal-recall-search-binds.md](court-proposal-recall-search-binds.md) — 8/20
  refs (40%) and 1/5 shell recordings ever produce a court within 20px of the clicks;
  pre-registered <=0.60 = search binds, so SEARCH BINDS (shell borderline, exactly on
  its 1/5 line). Mount-height mechanism FAILED its 40pp bar at 16.7pp and is confounded
  with surface. `truth_would_pass 9/20` is a withdrawn-genre artifact — the real
  accept-side number is 19/20 from the §10 neighbourhood sweep. Also: candidate_audit.py's
  "UNRUN" docstring is STALE (Session O ran it on shell 2026-08-24, 3/10 then vs 2/10 now)
  — grep docs/evidence + data/output for a script's numbers BEFORE running it.

- **Camera motion vs court inter-frame agreement, measured 2026-09-09.**
  [camera-motion-vs-court-agreement.md](camera-motion-vs-court-agreement.md) — the vote does
  penalise motion (24.0 px@640 removed on 5 moving clips) but rescues ZERO clips: static
  clips sit at the same ~25 px@640 floor, 1 of 16 crosses the line, 0 of 20 change
  acceptance. BAR1 INDETERMINATE (rho .474 / gap 18.6, both in the dead band), BAR2 PARTIAL,
  BAR3 width-zoom LINKED at n=3 but does NOT explain STATE's width row. Two lessons: a
  motion number measured vs video frame 0 is NOT the within-eval-window covariate
  (sAjkpeRq4P4 80.4 vs 3.6), and AGREE_PX's resolution problem was already in
  docs/evidence/agree-px-is-6-tighter-on-4k.md — grep before claiming.
- **Corner-audit verdicts are frame-choice contaminated, measured 2026-09-09.**
  [corner-audit-frame-choice-risk.md](corner-audit-frame-choice-risk.md) — 7 of the 10
  founder "wrong court" verdicts sit on a frame the eval never scores (frame 0 vs the
  5-95% samples); A7vXlWIlyrI's frame 0 is a monochrome intro, sAjkpeRq4P4's matches 0 of
  8 scored frames, HoHxFSX_gLk_s3 spans two venues. Risk runs BOTH ways (2 "correct"
  verdicts equally unsupported). Motion is confounded with clip type, not a cause.

- **Clip shot map measured 2026-09-09 — 8/10 single-setup, but the edge test is weaker
  than it looks.** [clip-shot-map-single-setup.md](clip-shot-map-single-setup.md) —
  control sAjkpeRq4P4 G=8 PASS; only HoHxFSX_gLk_s1 (5) and _s3 (4) FAIL-RESTRICT, zero
  FAIL-DROP; pool loses N=1 (5%) by the bar vs N=4 (20%) tight. Lesson: an ORB similarity
  edge proves "registrable background", NOT "one homography holds" — A7vXlWIlyrI passes
  G=8 at 188 px@640 / 40% zoom. Negative control (frame vs a DIFFERENT clip) is what
  validates a grouping; null+positive only prove the estimator runs.

- **§4.1 modality falsifier ran 2026-09-09 — INDETERMINATE, kill condition did not fire.**
  [mixture-vs-precision-floor-indeterminate.md](mixture-vs-precision-floor-indeterminate.md)
  — strict-16 n=11: MIX 4 / PF 1 / IND 6 vs a >=6 bar; all 5 MIXTURE verdicts are 1920-wide
  and 0 of 5 measurable 4K shell clips is MIXTURE, so the reading cannot be carried onto
  shell. The 4 motivating tripods rest on 1-10 pairs (flexi_joy_p01's 29.9 px is ONE pair).
  Bar has an all-singleton specification gap; flagged, not patched.

- **Innovation-gate diagnostic §5 (K3 + K1) independently verified 2026-09-10.**
  CONFIRMED (K3 discarded 914/492/48 and +6.557/+5.142/+3.534 pts, higher than the reported
  902/479/47 and +6.492/+4.926/+3.450; K1 pooled median 0.11272 on n=291, 12.30x below
  chi2_2, sign-test p=1.9e-29). TWO DEFECTS: a post-hoc run-reconstruction undercount, and
  `yt_match40`'s calibration silently resolving to a DIFFERENT court (86 vs 186 shots, hfov
  91.28 vs 26.43) between 2026-09-02 and 2026-09-10 — so its "reproduces the published
  baseline" claim is false and every span-derived number on that clip is in question.

- **P2 occlusion census sheet built 2026-09-16, UNLABELLED.**
  yt_match40; demo30.perception.json is not demo30's; yt_match40 HUD shows SwingVision bounce dots
  (mask it); audio A/V membership is chance-level -> negative-space audit, not capture-recapture.

- **P8 C2 NOT RUNNABLE, 2026-09-16 — court gold keypoints are homography-derived.**
  [court-gold-keypoints-are-derived.md](court-gold-keypoints-are-derived.md) — only the 4 corners
  are human; C2 median 0.048 px = rounding (void). demo30/yt_match40 height gap is a quad
  disagreement, demo30's is off the paint. Read the label WRITER before scoring.

- **CP1 stage 1 audited 2026-09-17: PASS QUALIFIED.** [cp1-stage1-audit-pass-qualified.md](cp1-stage1-audit-pass-qualified.md)
  — no leak, bit-identical repro; one dev=score pose, sigma on-grid, codec margin ~1.4 cm, tail 1% >5 cm.

## Standing

Never fix what you are checking. Never move a gate to fit a result. A borderline pass is
a pass — say borderline. `docs/TRAPS.md` (T01-T22) is the catalogue of process failures
that have fired here more than once.
[qa_does_not_write_to_codebase.md](qa_does_not_write_to_codebase.md) — a task brief
asking for an evidence file/STATE row does not override this; findings go in the report
text only. Also: a stray `claude-md-cap.sh` hook error on an unrelated Bash call is
likely cross-talk from another concurrent agent mid-edit of CLAUDE.md — retry once or
twice before treating it as a real block.
