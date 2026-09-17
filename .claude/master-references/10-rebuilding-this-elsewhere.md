# 10 — Rebuilding this setup in another project

Everything in `01`–`09` describes the mechanisms. This file is the **recipe**: what we
actually built in SwingVision, in the order that works, with the traps that cost us time
marked so you do not pay for them twice.

Built and verified 2026-08-28. Every number below was measured, not estimated.

## What you are rebuilding

Four layers that are easy to confuse:

| Layer | Path | Lives for | Answers |
| --- | --- | --- | --- |
| **Roles** | `.claude/agents/<name>.md` | forever | who does what, and what they may touch |
| **Memory** | `.claude/agent-memory/<name>/` | across sessions | what this agent has learned |
| **Journal** | `.claude/journals/<name>.md` | one task | where this agent got to before it died |
| **Doorman** | `.claude/hooks/agent_cap.py` | forever | how many agents may run at once |

Roles and memory are standard. **The journal and the doorman are the two pieces nobody
tells you to build**, and they are the two that make a team survive contact with a usage
limit.

## Decide these before writing anything

1. **How many agents may run at once?** Not how many roles — how many *concurrently*. On a
   Pro plan sharing one account, 3 is a sane ceiling. See the cost floor below.
2. **May agents call each other?** If yes, your cap must count the whole tree, not just what
   the lead dispatched. This is the entire reason the doorman exists.
3. **Which agents may write, and to what?** Use an allowlist per agent, not a prohibition
   list. A prohibition list invites "it didn't say I couldn't."

## Step 1 — the roles

One file per agent, `.claude/agents/<name>.md`:

```markdown
---
name: qa
description: One line. This is what the lead matches tasks against — make it specific.
tools: Read, Bash, Grep, Glob, Agent
model: sonnet
memory: project
---

You are ... [role, and the one thing you must never do]

**You MAY write to exactly these:**
- `.claude/journals/qa.md`
- `.claude/agent-memory/qa/`

**You MAY NOT write, edit or create anything under:** `src/`, any test file, ...
```

**Match `tools:` to the work.** Sending execution work to an agent with no `Bash` wastes a
whole run; we did this once and lost the run to it.  Include `Agent` only if that agent may
call others.

**The allowlist is load-bearing.** An agent whose charter says "never fixes anything" will
happily call an agent that fixes things, unless you say so. Verification independence dies
quietly that way.

## Step 2 — journals

One per agent plus one for the lead (`lead.md`) — **the lead dies to usage limits too**.

Template, per agent:

```markdown
# <name> — working journal

**READ THIS FIRST IF YOU ARE RESTARTING.** A usage limit kills an agent outright and
nothing restarts it automatically. Whatever is below is what survived.

**Write DURING the work, after every meaningful step.** You can only write when you call a
tool, so you cannot stream your thinking: the goal is that a kill loses ONE step, not the
whole run. Rewrite TASK/STATE in place; append to LOG; compact LOG past ~30 lines.

Transient working state only. Durable learnings go in `.claude/agent-memory/<name>/`.

## TASK — what I was asked to do
## STATE — where I got to
## LOG — newest first
```

Then **put a pointer in every agent's role file**, not only in CLAUDE.md — subagents never
read the lead's CLAUDE.md sections about themselves:

```markdown
## Your journal — read it first, write it as you go
`.claude/journals/<name>.md` is the ONLY thing that survives if a usage limit kills you.
**On starting: read it.** If TASK or STATE is populated you are RESTARTING — resume from
there and say so in your report.
```

**Track journals in git.** The lead journal accumulates blocked items and decisions; losing
it loses real work. Journals are cheap text.

## Step 3 — the doorman

Copy two files: `.claude/hooks/agent_cap.py` and `.claude/hooks/agent-cap.sh`.

**Why a hook and not a line in CLAUDE.md:** the lead cannot see what its children spawn. A
teammate calling a teammate spends the same quota, and nothing reports it upward. A cap that
is only remembered is a cap that gets forgotten.

**How it counts.** One lock file per live agent, keyed by `agent_id`:

| Event | Wiring | Does |
| --- | --- | --- |
| `SubagentStart` | always | writes `.claude/.agent-locks/<agent_id>` |
| `SubagentStop` | always | removes it |
| `PreToolUse` | matcher `Agent\|Task` | counts locks **+ reservations**; denies at the cap, else takes a reservation |
| `Stop` | always | hands a parked task back when a slot frees |
| `SessionStart` | always | reports slots held from before this session |

**Do not decrement on `PostToolUse`.** The Agent tool returns *immediately* for a background
agent that is still running, so the count would collapse to zero. `SubagentStart` /
`SubagentStop` pair on the same key and cannot drift.

**Reserve the slot at check time, or the gate is racy.** If `PreToolUse` only *reads*
the count, it has no side effect — so N dispatches emitted in a single message all see the
same free slot and all pass. Our QA demonstrated this with two back-to-back checks against
one free slot: both allowed. Write a reservation keyed by `tool_use_id` when you approve,
count it alongside locks, and have `SubagentStart` convert one reservation into a lock.
Expire reservations fast (120 s) — an approved dispatch that never started was abandoned.

**Hash the raw agent id into the lock filename.** Sanitising alone collides:
`team:agent.7` and `team/agent 7` both flatten to `team_agent_7`, two live agents share
one lock, and the count silently runs short. Also demonstrated.

**Refusing is not enough — park the task.** A bare refusal loses the work: the model either
drops it or retries in a loop, and the retry loop burns the quota the cap exists to protect.
Save the whole `tool_input` verbatim, tell the model *"this is saved, do NOT retry, do NOT
shrink it to fit"*, and hand it back from the `Stop` hook once a slot frees.

**Key the queue on a hash of the task.** A task dispatched normally then un-parks itself, so
nothing fires twice. Without this the Stop hook re-offers a task that already ran.

**Bound the hand-back loop.** Count hand-backs, drop the task after 3 with a visible message.
Otherwise a model that ignores the offer can prevent the turn from ever ending.

**Sweep stale locks, and say so at session start.** A killed agent never fires
`SubagentStop`, so its lock pins a slot until the TTL expires it — measured: still denying
at 29 minutes, allowed at 31. That is exactly when you come back from a usage-limit reset,
so the first thing you meet is an unexplained refusal claiming agents are live when none
are. Wire `SessionStart` to REPORT held slots with the clearing command. Do not clear
automatically: the cap is project-wide, and another window may have agents genuinely
running.

## Step 4 — wiring

In `.claude/settings.json`. `PreToolUse` takes a matcher; the other three do not:

```jsonc
"hooks": {
  "PreToolUse": [
    { "matcher": "Agent|Task",
      "hooks": [{ "type": "command", "timeout": 10,
                  "command": "\"$CLAUDE_PROJECT_DIR/.claude/hooks/agent-cap.sh\"" }] }
  ],
  "SubagentStart": [ { "hooks": [{ "type": "command", "timeout": 10, "command": "…same…" }] } ],
  "SubagentStop":  [ { "hooks": [{ "type": "command", "timeout": 10, "command": "…same…" }] } ],
  "Stop":          [ { "hooks": [{ "type": "command", "timeout": 10, "command": "…same…" }] } ]
}
```

Gitignore the transient dirs: `.claude/.agent-locks/`, `.claude/.agent-queue/`,
`.claude/.agent-reservations/`.

## Step 5 — verify it cheaply

Do not fill the cap with four real agents; that is the thing you are trying not to spend.

1. **Fake the slots.**
   `mkdir -p .claude/.agent-locks && for a in A B C; do date +%s > .claude/.agent-locks/$a; done`
   Then make ONE real dispatch. It should be refused and parked at almost no cost — the agent
   never runs.
2. **Test the hand-back.** Delete one fake lock, then end your turn. The turn should refuse to
   end and hand the task back with its exact arguments.
3. **Prove real agents register** — the step people skip, and without it the cap is decorative.
   Launch one background agent and poll `.claude/.agent-locks` while it runs. A lock should
   appear under its real `agent_id` and vanish on completion.
4. **Prove nesting counts.** Dispatch one cheap agent whose task is to spawn one more, where
   the inner agent's whole job is `ls .claude/.agent-locks`. The inner must report **2**.
5. **Test the race.** With one slot free, fire two `PreToolUse` checks back to back
   without a `SubagentStart` in between. The second must deny. If both pass, your gate is
   read-only and a single message with several dispatches will walk straight past it.
6. **Delete your fake locks.** They never fire `SubagentStop` and will block real work until
   the TTL sweeps them.

Our results: `BEFORE=1, INNER=2, AFTER=1`. Nesting counts.

## Traps that cost us time

- **A trivial agent costs ~38k tokens.** Measured: 38,347 for a one-word reply; 42,847 and
  47,600 for small file-reading tasks. Three at once is ~115k before any useful result. This
  is the number that justifies a cap at all.
- **A flat per-brief allowance does not sum to a global cap.** "You may spawn one each" with
  unbounded depth is unbounded total. Either hand down a *decrementing* budget, or count for
  real — we count for real.
- **A read-only check is not a gate.** Counting without reserving loses to any message
  that dispatches more than once. This is the hole an independent reviewer found in ours
  after everything else had passed — write the reservation at approval time.
- **A hook must fail open.** Garbage input, missing interpreter, no repo — step aside. A
  broken guard that wedges every dispatch is worse than no guard.
- **`PreToolUse` DOES fire inside subagents**, carrying `agent_id` and `agent_type`. This is
  what makes tree-wide counting possible; verify it still holds in your version.
- **Deny works even in bypass-permissions mode.** We assumed it might not; it does.
- **Python's `write_text` rewrites a whole LF file to CRLF on Windows.** This silently
  converted seven files, inflated a line-count guard by 2, and produced a 368-line diff for a
  2-line change. Pass `newline="\n"`, or write bytes.
- **The kill that journals exist for is the kill that leaks locks.** A usage limit kills the
  agent, the session resumes, reads the journal, tries to re-dispatch the dead work — and the
  doorman refuses, because the corpse still holds the slot. Put a **restart checklist** in the
  lead journal: reconcile `ls .claude/.agent-locks` against `ListAgents`, and check
  `.claude/.agent-queue` for parked work.

## Tuning

| Knob | Default | Raise if | Lower if |
| --- | --- | --- | --- |
| `TENNIS_AGENT_CAP` | 3 | you are on a bigger plan | you are hitting limits |
| `TENNIS_AGENT_TTL` | 1800s | agents legitimately run longer | corpses block you too long |
| `MAX_HANDBACKS` | 3 | — | the model keeps ignoring offers |
| `RESV_TTL` | 120s | agents are slow to start | approvals are abandoned often |

TTL must exceed your longest legitimate agent run, or a live agent's lock is swept and the cap
over-subscribes. The robust alternative is a heartbeat — touch the lock on every tool call, so
age means *time since last activity* — but that needs the hook on every tool call project-wide,
~100–200 ms each, forever. We judged the tax not worth an occasional, self-healing fault.
Reconsider if your agents are long-running.

## What to change per project

Rename the env vars off `TENNIS_`. Replace the project-specific refusal text in
`agent_cap.py` (the T07 reference and the quota wording). Everything else is generic.
