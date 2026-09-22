# qa memory

> **SCOPE: court feature only (founder, 2026-09-17).** The gate definitions, known-hard areas and checker quirks are in this agent's system prompt — read it first; it is the authoritative copy.

## Standing rules

- Never fix what you are checking. Never move a gate to fit a result. A borderline pass is a pass — say borderline.
- `docs/TRAPS.md` (T01-T22) is the catalogue of process failures that have fired here more than once.
- [Where qa may write](qa_does_not_write_to_codebase.md) — evidence/journal/memory only; a brief asking for a STATE row does not override it.
- [Poll background jobs in a foreground loop](background_wait_does_not_survive_ending_turn.md) — ending a turn to "wait" loses the notification.

## Court audits — the live record

- [G8 remediation + G9, 2026-09-22](g9-and-g8-remediation-audit.md) — numbers reproduce; pyramid fails on the run-off STEP not the tape; G9 wrong locks = coherent flow outliers, not lag.
- [G8 far-line instrument, 2026-09-19](g8-far-line-audit.md) — numbers reproduce, but the committed tool cannot rerun its own sweep and an undeclared 3.56x reach widening is what makes BAR 4 fail.
- [G7 photometric separation, 2026-09-18](g7-separation-audit.md) — CONFIRMED and strengthened (independent geometric label: 34/34 at 0/364), but held-out "SEPARATES" holds on only 3 of 10 split seeds and nothing here can see the far baseline.
- [Post-G3 tracker fixes, 2026-09-18](tracker-fixes-hold-on-held-out-seeds.md) — not seed-tuned (fresh seeds 2.41 cm vs dev 3.52 cm), still UNSCORED, still reports `locked` while 56-70 cm out on the far lines.
- [CP1 stage 1, 2026-09-17](cp1-stage1-audit-pass-qualified.md) — PASS QUALIFIED: no leak, bit-identical repro; one dev=score pose, sigma on-grid, codec margin ~1.4 cm, 1% tail >5 cm.
- [Court gold keypoints are derived, 2026-09-16](court-gold-keypoints-are-derived.md) — P8 C2 NOT RUNNABLE; only the 4 corners are human. Read the label WRITER before scoring.
- [Court proposal recall, 2026-09-09](court-proposal-recall-search-binds.md) — the SEARCH binds, not the vote (8/20 refs, 1/5 shell). Grep evidence + data/output for a script's numbers before re-running it.
- [Camera motion vs court agreement, 2026-09-09](camera-motion-vs-court-agreement.md) — the vote penalises motion but rescues ZERO clips; a motion number vs frame 0 is not the within-window covariate.
- [Corner-audit frame-choice risk, 2026-09-09](corner-audit-frame-choice-risk.md) — 7 of 10 founder "wrong court" verdicts sit on a frame the eval never scores; the risk runs both ways.
- [Clip shot map, 2026-09-09](clip-shot-map-single-setup.md) — 8/10 single-setup, but an ORB edge proves "registrable background", not "one homography holds"; the negative control is what validates a grouping.
- [§4.1 mixture vs precision floor, 2026-09-09](mixture-vs-precision-floor-indeterminate.md) — INDETERMINATE, kill condition did not fire; the reading cannot be carried onto shell.
- [Clean-plate / MTI, 2026-09-06](cleanplate-mti-near-baseline-measured.md) — weak/mixed; 1 of 8 clips clears the 2 px bar on both axes; my protocol was not poolable with backend-dev's.
- [Ground-plane blindness, 2026-09-05](ground-plane-blindness-narrows.md) — NARROWS: aniso compression is invisible to every shipped gate, but a computed-but-unused fitted hfov would catch it.
- [Court-mask sweep, 2026-09-02](court-mask-sweep-item-is-already-shipped.md) — the parked item is the already-shipped surface router; verified DEAD, 12/20 across 3 runs.

## Process and environment

- [Dispatch collision, 2026-09-06](dispatch-collision-cleanplate-task.md) — check a coupled teammate's journal EARLY for its protocol and for a deliverable-path collision.
- [Agent-cap doorman verified, 2026-08-28](agent_cap_doorman_verified.md) — cap/parking/hand-back all PASS; three real gaps found (TOCTOU, `safe_name()` collision, prompt truncation), none fixed.
- A stray `claude-md-cap.sh` hook error on an unrelated Bash call is usually cross-talk from another agent mid-edit of CLAUDE.md — retry once or twice before treating it as a real block.

## Archived scope (pre-2026-09-17 court cut)

- [Pre-court verifications](pre-court-verifications.md) — P0-2, P0-3, Core ML export, line-call margin, int8 parity, `seen_frac`, innovation gate, P2 occlusion. History, not work; kept so a measured negative is not re-proposed as untested.
