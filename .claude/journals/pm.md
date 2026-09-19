# pm — working journal

**READ THIS FIRST IF YOU ARE RESTARTING.** A usage limit kills an agent outright and nothing restarts it
automatically. Whatever is below is what survived.

**SCOPE: the court feature only (founder, 2026-09-17).**

---

## TASK — feasibility check of the founder's four-item per-frame roadmap (2026-09-18)

Deliverable: ONE appended section in `docs/DECISIONS_PENDING.md` titled
"PM feasibility check: the founder's per-frame roadmap (2026-09-18)", covering (a) item-by-item
verdicts, (b) rule-3 check against CLOSED.md branch by branch, (c) sequencing, (d) accuracy floor
per item, (e) what I would not build, (f) founder decisions. No other file may be edited.
NOTE: researcher agent deleted 2026-09-18; do not reference it.

## STATE — DONE. Section appended to docs/DECISIONS_PENDING.md; memories written; reporting back.
- Read: journal, STATE.md (all), CLOSED.md, DECISIONS_PENDING.md, SPEC.md, evidence/court-camera3d.md.
- NOTE: Glob/Grep return nothing for backend/** in this session (code not readable from my scope);
  worked entirely from docs/evidence. Did not need code.
- Verdicts: 1 Tier1-as-camera CONTRADICTED (K0 6.65 m), 1 Tier1-as-seed FEASIBLE-W-COND (= item 2),
  1 Tier2 NOT YET, 1 fallback = founder call F1; 2 FEASIBLE-W-COND (net-guided pose half contradicted
  by net-baseline-solve falsifier, keep only as height prior); 3 multi-anchor FEASIBLE-W-COND +
  net-clearance-as-written CONTRADICTED (overlap is CORRECT below 2.2 m); 4 multi-scale FEASIBLE,
  global re-loc NOT YET (blocked on item 2).
- First build: re-score arm K's existing 400 trials for a wrong-camera cost discriminator (1 session,
  no new data) — 3 items depend on that selector.
- Biggest blocking decision: F1, does the stateless per-frame mandate stand.
- Memories written: seed-vs-answer-is-the-court-cut-line, latency-vs-5cm-is-the-recurring-trade,
  no-researcher-agent (+ MEMORY.md index).

## LOG
- 2026-09-17: journal reset to court scope.
- 2026-09-18: task started. Key numbers in hand: arm K p90 far baseline 4.43 cm L / 1.18 cm M,
  8.75% wrong camera (seed height err 0.69 m vs 0.13 m); K0 KILL far baseline 6.65 m; G3 tracking
  KILL worst line p90 11.0 m, one seed wrong-paint lock reporting `tracking`; timings 9.6 s paint
  fit, 0.020 s tracker step, 0.003 s paint_check at 1080p desktop CPU.
