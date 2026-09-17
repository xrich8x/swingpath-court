# 09 — Preflight checklist

Run this before spawning. Any "no" is a stop.

## Should this be a team at all?

- [ ] Can I name, in one sentence each, the **file set or question** each
      teammate exclusively owns?
- [ ] Do the lanes run **independently** — no teammate waiting on another's
      output to start?
- [ ] Do I want them to **talk to each other**? If not, use subagents; the team
      premium buys discussion and nothing else.
- [ ] Is this research / review / debate / disjoint implementation — rather than
      sequential work, same-file edits, or "just give me the answer"?
- [ ] Is the shared bottleneck (one GPU, one dataset, one service) **not** going
      to serialise them anyway?

## Environment

- [ ] `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` is set in the settings source that
      actually wins (check project / local / `--settings` / managed).
- [ ] Session is **interactive** (not `-p`).
- [ ] I know which display mode I am in — default is now `"in-process"`, not
      `"auto"`.
- [ ] Common operations are pre-approved in permission settings, so teammate
      prompts don't flood the lead.
- [ ] `subagentPromptCacheTtl: "1h"` if teammates will have long gaps between
      turns.
- [ ] Nothing in this project forbids fan-out (in **this** repo, it does — see
      `08-swingvision-rules.md`).

## Each spawn prompt contains

- [ ] A **name** I can address later.
- [ ] The **one lens / file set** it owns, and what it must not touch.
- [ ] The **context it cannot infer** — it has CLAUDE.md and nothing from my
      conversation. No history, no files I read, no decisions we reached.
- [ ] An explicit **deliverable and delivery channel**: message the lead / write
      to this path / update the task. *Idle is not delivery.*
- [ ] The **model** if it should not be the lead's.
- [ ] Plan-approval **criteria** if I am gating it, since the lead approves
      autonomously.

## Team shape

- [ ] 3–5 teammates. Not one per task.
- [ ] 5–6 tasks per teammate, each a self-contained unit with a clear artifact.
- [ ] Sonnet for teammates unless a role needs judgement.
- [ ] File ownership disjoint, or `isolation: worktree`.
- [ ] If the value depends on debate, the prompt says **"try to disprove each
      other"** explicitly.

## Gates

- [ ] Does any project gate (tests, lint, an accuracy threshold, a docs guard)
      currently fire only on the lead's `Stop` or `git commit`? If so, teammates
      are **not** covered — add `TeammateIdle` / `TaskCompleted` hooks or accept
      that the team runs ungated.
- [ ] Any blocking hook has an escape condition the agent can actually satisfy.

## While it runs

- [ ] Check in rather than letting it run unattended.
- [ ] Redirect a teammate going the wrong way (select, Enter, type).
- [ ] `Wait for your teammates to complete their tasks` if the lead starts doing
      the work itself.
- [ ] Re-check the task list (`Ctrl+T`) for tasks stuck in progress.

## Shutting down

- [ ] Every teammate explicitly shut down — hidden idle rows are still running.
- [ ] Findings actually collected, not just "the teammate went idle".
- [ ] `tmux ls` clean if split panes were used.
- [ ] `/usage` checked against what a single session would have cost, and the
      answer recorded for next time.

## The two questions afterwards

1. **Did the teammates message each other?** If not, this should have been
   subagents, and next time it will be.
2. **Did the team produce something a single session would not have?** If not,
   the shape was wrong — write down which shape, so the next run does not repeat
   it.
