# 01 — Choosing the mechanism

Claude Code has **six** ways to run more than one thread of work. Picking wrong
is the single most expensive mistake in multi-agent work, because the wrong
mechanism still *appears* to work while burning 5–10x the tokens.

## The decision table

| Mechanism | Context | How results come back | Cost | Use when |
| --- | --- | --- | --- | --- |
| **Single session** | One | — | 1x | Sequential work, same-file edits, heavy dependencies, quick targeted changes, anything needing frequent back-and-forth |
| **Subagent** (`Agent` tool) | Own, fresh | **Result returned to the caller** | Low–med | Focused task where only the answer matters; verbose output you want kept out of main context (tests, logs, doc fetches); parallel research |
| **Fork** (`/subtask`) | **Inherits the full parent conversation** | Result to caller | Med | Side task that needs everything you have already established, without re-deriving it |
| **Agent team** | Own, fresh, fully independent | **Idle notification only** — teammate must message or update the task list to share output | High (~7x) | Independent lanes that must *discuss*, challenge each other, or self-coordinate |
| **Cross-session messaging** | Separate sessions you start yourself | Plain-text messages both ways | You control | Two sessions you are steering by hand that need to warn/inform each other |
| **Git worktrees** | Separate checkouts | You read them | You control | Parallel implementation on the same repo with zero file collision |

## Subagent vs team — the one difference that bites

- A **subagent** completes and its output lands in the caller's context.
- A **teammate** completes and the lead is told only *"it went idle."* The
  output does **not** ride along. The teammate must send a message or write to
  the shared task list, or the work is effectively invisible.

Consequence: **an orchestration flow that waits on subagent results will stall
if those subagents launch as teammates instead.** That happens silently — see
below.

## The silent-promotion trap

With `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`, **any subagent Claude gives a
`name` launches as a teammate.** Claude names subagents on its own so it can
message them later. So a team can form during ordinary delegation you never
framed as team work.

Symptoms: your "spawn 3 researchers and synthesise" flow returns nothing;
agents appear in the panel but the lead has no findings.

Fix: set `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` to `"0"` (no restart needed —
settings-file `env` values are reapplied on save and the variable is re-read at
every spawn), or design the flow to expect idle notifications and pull results
via messages/task list.

## When a team genuinely wins

The docs' strongest four, and *why* each one wins:

1. **Research and review** — independent lenses on the same artifact (security /
   performance / tests) each get full attention instead of one reviewer
   drifting to a single issue class.
2. **New modules or features** — each teammate owns disjoint files, so parallel
   implementation without overwrites.
3. **Debugging with competing hypotheses** — the big one. Sequential
   investigation **anchors**: the first plausible theory biases everything
   after it. N investigators actively trying to *disprove each other* means the
   surviving theory is far more likely to be the real cause.
4. **Cross-layer coordination** — frontend / backend / tests, one owner each.

## When a team loses

- Sequential work with dependencies (teammates block on each other; you pay for
  idle context windows).
- Same-file edits (two teammates writing one file = overwrites).
- Anything where you just want an answer back — that is a subagent.
- Non-interactive runs: with `-p` (including Agent SDK sessions) **teammates are
  never spawned**; a named subagent runs as an ordinary subagent.

## Rule of thumb

> If you cannot name, in one sentence each, what **file set** or **question**
> each teammate exclusively owns, you do not have a team — you have N copies of
> the same session.
