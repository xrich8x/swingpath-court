# The full setup — the doorman, the agent limit, and how tennis-team is built

**One document, self-contained.** Everything about the concurrency doorman, the agent
limitation it enforces, and how the five-agent team is wired — prompts and logic.
Written to be read cold and copied into another project.

Assembled 2026-08-29 from the live system in this repo. Every number here was measured
in this project, not estimated. Files `01`–`10` in this folder are the wider reference;
this file is the part that is *ours*.

---

## Contents

1. [The four layers](#1-the-four-layers)
2. [The mechanism choice — why subagents, not an agent team](#2-the-mechanism-choice)
3. [The agent limitation — three different limits people confuse](#3-the-agent-limitation)
4. [The doorman — what it does and why each piece exists](#4-the-doorman)
5. [The doorman — wiring](#5-wiring)
6. [The doorman — how to verify it cheaply](#6-verifying-it)
7. [The team — architecture and the shared prompt skeleton](#7-the-team)
8. [The team — the five role prompts in full](#8-the-five-roles-in-full)
9. [The lead's dispatch logic](#9-the-leads-dispatch-logic)
10. [Journals and memory — the two survival layers](#10-journals-and-memory)
11. [The other hooks in this repo](#11-the-other-hooks)
12. [Rebuilding this in another project — ordered checklist](#12-rebuilding-elsewhere)
13. [Appendix A — `agent_cap.py`, complete](#appendix-a)
14. [Appendix B — `agent-cap.sh`, complete](#appendix-b)
15. [Appendix C — the `settings.json` hook block](#appendix-c)

---

<a name="1-the-four-layers"></a>
## 1. The four layers

Four things that are easy to confuse. Each answers a different question and lives for a
different length of time.

| Layer | Path | Lives for | Answers |
| --- | --- | --- | --- |
| **Roles** | `.claude/agents/<name>.md` | forever | who does what, and what they may touch |
| **Memory** | `.claude/agent-memory/<name>/` | across sessions | what this agent has learned |
| **Journal** | `.claude/journals/<name>.md` | one task | where this agent got to before it died |
| **Doorman** | `.claude/hooks/agent_cap.py` | forever | how many agents may run at once |

Roles and memory are standard Claude Code features. **The journal and the doorman are the
two pieces nobody tells you to build**, and they are the two that make a team survive
contact with a usage limit.

---

<a name="2-the-mechanism-choice"></a>
## 2. The mechanism choice — why subagents, not an agent team

Claude Code has six ways to run more than one thread of work. Picking wrong is the most
expensive mistake in multi-agent work, because the wrong mechanism still *appears* to
work while burning 5–10× the tokens.

| Mechanism | Context | How results come back | Cost | Use when |
| --- | --- | --- | --- | --- |
| **Single session** | One | — | 1× | Sequential work, same-file edits, heavy dependencies |
| **Subagent** (`Agent` tool) | Own, fresh | **Result returned to the caller** | Low–med | Focused task where only the answer matters |
| **Fork** (`/subtask`) | **Inherits the full parent conversation** | Result to caller | Med | Side task needing everything already established |
| **Agent team** | Own, fresh, independent | **Idle notification only** | High (~7×) | Independent lanes that must *discuss* |
| **Cross-session messaging** | Separate sessions | Plain-text messages both ways | You control | Two sessions you steer by hand |
| **Git worktrees** | Separate checkouts | You read them | You control | Parallel implementation, zero file collision |

### The one difference that bites

- A **subagent** completes and its output lands in the caller's context.
- A **teammate** completes and the lead is told only *"it went idle."* The output does
  **not** ride along. The teammate must send a message or write to the shared task list,
  or the work is effectively invisible.

**Consequence: an orchestration flow that waits on subagent results will stall if those
subagents launch as teammates instead.** That happens silently.

### The silent-promotion trap

With `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` — **which is set in this repo's
`settings.json`** — **any subagent Claude gives a `name` launches as a teammate.** Claude
names subagents on its own so it can message them later. A team can therefore form during
ordinary delegation you never framed as team work.

Symptom: your "spawn 3 researchers and synthesise" flow returns nothing; agents appear in
the panel but the lead has no findings.

Fix: set the variable to `"0"` (no restart needed — settings-file `env` values are
reapplied on save and the variable is re-read at every spawn), or design the flow to
expect idle notifications and pull results via messages.

### What this repo actually does

**tennis-team is dispatched as subagents, one at a time, with the lead synthesising.**
Not as a plan-mode agent team. The reasons are repo-specific and measured:

1. **One GPU.** Parallel teammates that all want to train or run inference serialise on
   the same device. You pay N context windows for 1× throughput.
2. **One gold set.** Every teammate scoring against the same held-out clips multiplies
   the chance of the exact thing rule 1 of CLAUDE.md exists to prevent — a number
   measured against something that is not independent truth.
3. **Two multi-agent fan-out runs burned ~971k tokens for zero results.** That is a
   measured result in this repo, recorded as trap T07.

The rule that came out of it: **never several agents on one question.** Decompose into
disjoint questions or run one.

### Where a team *would* be legitimate here

Only where the work is genuinely read-only, does not touch the GPU, and does not score
against gold:

- Documentation reconciliation — `docs/STATE.md` vs evidence files vs `README.md`, one
  owner per doc set.
- Adversarial audit of a claim already made — three lenses on "is this number measured
  against independent truth?"
- Frontend/backend split where the contract (`schema.py`) is frozen and file ownership is
  strictly disjoint.

Everything involving training, evaluation, or a gold-set number stays single-session.

---

<a name="3-the-agent-limitation"></a>
## 3. The agent limitation — three different limits people confuse

There are three separate ceilings. Only the third is ours.

### (a) Claude Code's own structural limits

- **Spawn depth:** default **3 layers** below main (`CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH`).
- **Concurrent subagents:** default **20** before a spawn fails
  (`CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS`).
- **Teammates cannot nest at all** — only the lead manages a team.
- **No background subagents from in-process teammates** — a teammate's subagents run in
  the foreground; `background: true` errors.
- **No session resumption with in-process teammates** — `/resume` and `/rewind` do not
  restore them. The task list survives; the workers do not.
- **Under `-p` (headless / Agent SDK) no teammates are spawned at all** — a named
  subagent runs as an ordinary subagent.

### (b) The plan quota — the real economic limit

This is a **Pro-plan QUOTA cap, not machine load.** Every agent anywhere in the tree
spends the same shared account.

**Measured in this project:**

| What | Tokens |
| --- | --- |
| A one-word reply from a trivial agent | **38,347** |
| A small file-reading task | 42,847 |
| Another small file-reading task | 47,600 |
| Three at once, before any useful result | **~115k** |
| One large agent run | **253k** |

That ~38k floor is the number that justifies having a cap at all. It costs 38k tokens to
ask an agent for one word.

### (c) Our cap — three live agents, project-wide

> **THREE LIVE AGENTS PROJECT-WIDE.** The counter counts the *whole tree*, so a teammate
> calling a teammate spends the same quota: lead → backend-dev → qa is **two of three**.

Corollaries, all load-bearing:

- **Teammates MAY call each other.** That is precisely why the cap must count the tree —
  the lead cannot see what its children spawn.
- **A refusal is PARKED, not lost** — handed back when a slot frees. Never retry, never
  shrink the task to fit.
- **The lead holds ONE direct child at a time**, one task per brief. Two deliverables is
  two runs in one.

### Why a hook and not a line in CLAUDE.md

A cap that is only *remembered* is a cap that gets forgotten. Two specific failures:

1. **The lead cannot see what its children spawn.** A nested call spends the same quota
   and nothing reports it upward.
2. **A flat per-brief allowance does not sum to a global cap.** "You may spawn one each"
   with unbounded depth is unbounded total. Either hand down a *decrementing* budget, or
   count for real. We count for real.

---

<a name="4-the-doorman"></a>
## 4. The doorman — what it does and why each piece exists

`.claude/hooks/agent_cap.py` plus a thin wrapper `.claude/hooks/agent-cap.sh`.

### How it counts

One lock file per live agent, keyed by `agent_id`.

| Event | Matcher | Does |
| --- | --- | --- |
| `SubagentStart` | always | writes `.claude/.agent-locks/<agent_id>`; consumes one reservation |
| `SubagentStop` | always | removes the lock |
| `PreToolUse` | `Agent\|Task` | counts locks **+ reservations**; denies at the cap, else **takes a reservation** |
| `Stop` | always | hands a parked task back when a slot frees |
| `SessionStart` | always | reports slots held from before this session |

### The eight design decisions, each of which was earned

**1. Do not decrement on `PostToolUse`.**
The Agent tool returns *immediately* for a background agent that is still running, so
the count would collapse to zero. `SubagentStart` / `SubagentStop` pair on the same key
and cannot drift.

**2. Reserve the slot at check time, or the gate is racy.**
If `PreToolUse` only *reads* the count it has no side effect — so N dispatches emitted in
a single message all see the same free slot and all pass. **qa demonstrated this** with
two back-to-back checks against one free slot: both allowed. Fix: write a reservation
keyed by `tool_use_id` at approval time, count it alongside locks, and have
`SubagentStart` convert one reservation into a lock. Expire reservations fast (**120 s**)
— an approved dispatch that never started was abandoned.

> This is the hole an independent reviewer found *after everything else had passed*.
> **A read-only check is not a gate.**

**3. Hash the raw agent id into the lock filename.**
Sanitising alone collides: `team:agent.7` and `team/agent 7` both flatten to
`team_agent_7`, two live agents share one lock, and the count silently runs short. Also
demonstrated by qa — firing both as separate `SubagentStart` events produced ONE lock
file, not two. Fix: `safe_name()` appends an 8-char sha1 of the raw id.

**4. Refusing is not enough — park the task.**
A bare refusal loses the work: the model either drops it or retries in a loop, and the
retry loop burns the quota the cap exists to protect. So save the whole `tool_input`
verbatim, tell the model *"this is saved, do NOT retry, do NOT shrink it to fit"*, and
hand it back from the `Stop` hook once a slot frees.

**5. Key the queue on a hash of the task.**
`task_key()` is a sha1 of the sorted-JSON `tool_input`, so key order doesn't matter. A
task dispatched normally silently un-parks its own queued twin — nothing fires twice.
Without this the Stop hook re-offers a task that already ran.

**6. Bound the hand-back loop.**
Count hand-backs; drop the task after **3** with a visible message. Otherwise a model
that ignores the offer can prevent the turn from ever ending.

**7. Sweep stale locks, and say so at session start.**
A killed agent never fires `SubagentStop`, so its lock pins a slot until the TTL expires
it. **Measured: still denying at 29 minutes, allowed at 31.** That is exactly when you
come back from a usage-limit reset, so the first thing you meet is an unexplained refusal
claiming agents are live when none are.

`SessionStart` therefore **REPORTS** held slots with the clearing command. It does **not**
clear automatically — the cap is project-wide and another window may have agents genuinely
running.

**8. Fail open on everything.**
Garbage input, missing interpreter, no git repo — step aside. A broken guard that wedges
every dispatch is worse than no guard. Verified against bad JSON, empty stdin, plain text,
no repo, and no python on PATH.

### The refusal message the model actually sees

```
N agents are already live across this project; the cap is 3.

THIS TASK IS SAVED, NOT LOST. It has been parked verbatim (N task(s) now parked)
and will be handed back to you automatically as soon as a slot frees. Do NOT retry
it now, and do NOT re-plan or shrink it — a retry loop burns the quota this cap
exists to protect.

Carry on with work that does not need an agent, or end the turn; the parked task
will be re-offered before the turn is allowed to finish.

This is a Pro-plan QUOTA cap, not machine load: every agent anywhere in the tree
spends the same shared account, and nested teammate-to-teammate calls count the
same as the lead's own dispatches.

If you believe no agent is actually running, locks leaked from a killed session:
rm -rf .claude/.agent-locks .claude/.agent-queue
```

The wording is doing real work. "SAVED, NOT LOST", "do NOT retry", "do NOT shrink it to
fit" and the escape hatch are each there because the model did the opposite without them.

### Tuning knobs

| Knob | Default | Raise if | Lower if |
| --- | --- | --- | --- |
| `TENNIS_AGENT_CAP` | 3 | you are on a bigger plan | you are hitting limits |
| `TENNIS_AGENT_TTL` | 1800 s | agents legitimately run longer | corpses block you too long |
| `MAX_HANDBACKS` | 3 | — | the model keeps ignoring offers |
| `RESV_TTL` | 120 s | agents are slow to start | approvals are abandoned often |
| `MAX_PROMPT_ECHO` | 8000 chars | — | — |

**TTL must exceed your longest legitimate agent run**, or a live agent's lock is swept and
the cap over-subscribes. The robust alternative is a heartbeat — touch the lock on every
tool call, so age means *time since last activity* — but that needs a hook on every tool
call project-wide, ~100–200 ms each, forever. Judged not worth an occasional, self-healing
fault. Reconsider if your agents are long-running.

### Known gaps, recorded not fixed

- **Hook `timeout: 10`** — whether a genuine timeout fails open or closed is Claude Code
  harness behaviour, not this repo's code. Untested.
- **`MAX_PROMPT_ECHO` truncation** used to be silent; it now carries a truncation notice
  naming the queue file that holds the full text.

---

<a name="5-wiring"></a>
## 5. Wiring

In `.claude/settings.json`. `PreToolUse` takes a matcher; the other four do not.

```jsonc
"hooks": {
  "PreToolUse": [
    { "matcher": "Agent|Task",
      "hooks": [{ "type": "command", "timeout": 10,
                  "command": "\"$CLAUDE_PROJECT_DIR/.claude/hooks/agent-cap.sh\"",
                  "statusMessage": "Checking the project-wide concurrent-agent cap" }] }
  ],
  "SubagentStart": [ { "hooks": [{ "type": "command", "timeout": 10, "command": "…same…" }] } ],
  "SubagentStop":  [ { "hooks": [{ "type": "command", "timeout": 10, "command": "…same…" }] } ],
  "Stop":          [ { "hooks": [{ "type": "command", "timeout": 10, "command": "…same…" }] } ],
  "SessionStart":  [ { "hooks": [{ "type": "command", "timeout": 10, "command": "…same…" }] } ]
}
```

Gitignore the transient dirs:

```
.claude/.agent-locks/
.claude/.agent-queue/
.claude/.agent-reservations/
```

**Facts about hooks that make this possible**, verified here:

- **`PreToolUse` DOES fire inside subagents**, carrying `agent_id` and `agent_type`. This
  is what makes tree-wide counting possible. Verify it still holds in your version.
- **Deny works even in bypass-permissions mode.** We assumed it might not; it does.
- `agent_id` / `agent_type` are present **only** when the event came from a subagent or
  teammate — which is exactly how you write a rule that applies to agents but not to your
  own main-thread work.

---

<a name="6-verifying-it"></a>
## 6. Verifying it cheaply

Do not fill the cap with four real agents; that is the thing you are trying not to spend.

1. **Fake the slots.**
   ```bash
   mkdir -p .claude/.agent-locks && for a in A B C; do date +%s > .claude/.agent-locks/$a; done
   ```
   Then make ONE real dispatch. It should be refused and parked at almost no cost — the
   agent never runs.

2. **Test the hand-back.** Delete one fake lock, then end your turn. The turn should
   refuse to end and hand the task back with its exact arguments.

3. **Prove real agents register** — the step people skip, and without it the cap is
   decorative. Launch one background agent and poll `.claude/.agent-locks` while it runs.
   A lock should appear under its real `agent_id` and vanish on completion.

4. **Prove nesting counts.** Dispatch one cheap agent whose task is to spawn one more,
   where the inner agent's whole job is `ls .claude/.agent-locks`. The inner must report
   **2**. *Our result: `BEFORE=1, INNER=2, AFTER=1`.*

5. **Test the race.** With one slot free, fire two `PreToolUse` checks back to back
   without a `SubagentStart` in between. **The second must deny.** If both pass, your gate
   is read-only and a single message with several dispatches walks straight past it.

6. **Delete your fake locks.** They never fire `SubagentStop` and will block real work
   until the TTL sweeps them.

### What independent verification actually found

qa verified the doorman on 2026-08-28 by feeding synthetic hook payloads directly to the
script — never by re-deriving the logic from reading it. **Nine checks passed; three
broke it.** The three: the read-only-gate race, the `safe_name()` collision, and silent
prompt truncation in the hand-back. All three are fixed in the code in Appendix A.

That ratio is the argument for testing a guard by *invoking* it rather than reading it.

---

<a name="7-the-team"></a>
## 7. The team — architecture and the shared prompt skeleton

Five roles in `.claude/agents/`, each with memory in `.claude/agent-memory/<name>/` and a
journal in `.claude/journals/<name>.md`.

| Teammate | Model | Owns | Writes code | Tools |
| --- | --- | --- | --- | --- |
| **pm** | opus | Scope, sequencing, the cut line, accuracy floors | no | Read, Write, Edit, Grep, Glob, Agent |
| **researcher** | sonnet | ML/CV for court, player, ball, shot; on-device iOS inference | no | Read, Write, Edit, WebSearch, WebFetch, Grep, Glob, Agent |
| **backend-dev** | opus | Inference pipeline, the four detections, match storage, the port | **yes** | Read, Write, Edit, Bash, Grep, Glob, Agent |
| **frontend-dev** | sonnet | The iPhone app: UI/UX, capture, calling the pipeline, rendering | **yes** | Read, Write, Edit, Bash, Grep, Glob, Agent |
| **qa** | sonnet | Independent verification of both layers. Reports, **never fixes** | no | Read, Write, Edit, Bash, Grep, Glob, Agent |

All five carry `memory: project`.

### Three constraints bind all five

1. **iOS/iPadOS only, A13+**, Core ML/ANE the only inference target.
2. **100% on-device forever** — a proposed network dependency is a scope violation, not
   an optimisation.
3. **This project folder only** — no global installs, no system or account settings.

Settled, not reopened. Each role file states them in its own words rather than pointing at
a shared doc, because **a subagent does not inherit the lead's conversation.**

### The frontmatter pattern

```yaml
---
name: qa
description: One line. This is what the lead matches tasks against — make it specific,
             and say when NOT to use it.
tools: Read, Write, Edit, Bash, Grep, Glob, Agent
model: sonnet
memory: project
---
```

**Match `tools:` to the work.** Sending execution work to an agent with no `Bash` wastes a
whole run — we did this once, to `researcher`, and lost the run to it. Include `Agent`
only if that agent may call others.

**Caveat that cost time:** agent definitions are read **at session start**. Editing
`.claude/agents/*.md` mid-session does not re-register the type. After narrowing a
definition, start a new session before relying on the restriction, and never assume the
running session's allowlist matches the file you just edited.

### The seven sections every role file has

Every one of the five follows the same skeleton. The order matters — identity and
constraints before detail, because a truncated read still leaves the agent safe.

1. **Identity + the one thing it must never do**, in the opening paragraph.
2. **Hard constraints** — iOS-only, on-device, folder boundary. Restated per file.
3. **What you own / what you do not own** — ownership stated as a pair, so the anti-goal
   is as explicit as the goal.
4. **Standing facts it must not re-derive** — the measured numbers, the killed ideas, the
   traps. This is what a cold-start agent cannot infer and would otherwise waste a run
   rediscovering.
5. **Output shape** — the exact headings the caller needs back.
6. **Calling another teammate** — the cap, the parking rule, and the role-specific
   integrity clause (below).
7. **Journal + write allowlist** — where it may write, as an allowlist.

### The write allowlist — the load-bearing part

All five hold `Write` and `Edit` so their journals and memory work reliably. **Nothing in
the harness stops them writing anywhere**, so the allowlist in the prompt is the constraint:

```markdown
**You MAY write to exactly these:**
- `.claude/journals/<your-name>.md` — your working state
- `.claude/agent-memory/<your-name>/` — your durable learnings
- `docs/evidence/<slug>.md` — a findings writeup, when you have a finding

**You MAY NOT write, edit or create anything under:** `backend/`, `tools/`, `frontend/`,
`mobile/`, `ball_physics/`, any test file, `docs/STATE.md`, `docs/TRAPS.md`, `CLAUDE.md`,
or any `.claude/agents/` or `.claude/hooks/` file.

This is not enforced by the harness; the lead reviews `git status` before every commit and
a write outside this list will be visible there.
```

**Use an allowlist, not a prohibition list.** A prohibition list invites "it didn't say I
couldn't."

### The integrity clause — per role, and the reason it exists

An agent whose charter says "never fixes anything" will happily *call an agent that fixes
things* unless you say so. Verification independence dies quietly that way. So each role's
"calling another teammate" section carries its own clause:

- **qa:** *"You still never fix anything. Never call backend-dev or frontend-dev to repair
  what you found — calling a builder to make your finding go away is the same violation as
  fixing it yourself. Report it and stop."*
- **researcher:** *"You still do not write code. Never call backend-dev or frontend-dev to
  make a change on your behalf — that is the same violation as writing it yourself,
  wearing someone else's name."*
- **backend-dev / frontend-dev:** *"If you call qa, you do not own its verdict. Report what
  qa returned verbatim, pass or fail, in your own return. The lead cannot see a verdict you
  were given and did not pass on, and a builder that chooses which of its own gradings get
  reported is grading itself."*
- **pm:** *"Calling a builder is still a handoff, not authorship. You brief them and
  interrogate the result; you do not direct the diff. You still do not overrule qa's
  numbers, and calling qa yourself does not make its verdict yours to soften."*

### The shared cap paragraph, verbatim in all five files

```markdown
## Calling another teammate

You may call another teammate directly. **Three agents may be live across the whole project
at once** — a cap enforced by `.claude/hooks/agent-cap.sh`, which counts every agent anywhere
in the tree, not just the ones you started. If your call is refused, your task was **PARKED,
not lost**: do not retry it, and do not shrink it to fit. It is handed back automatically as
soon as a slot frees. Announce the teammate by name and label its output as theirs, never as
your own. A one-word agent still costs ~38k tokens, so call one only when the answer is
genuinely outside what you can establish yourself.
```

### The shared journal paragraph, verbatim in all five files

```markdown
## Your journal — read it first, write it as you go

`.claude/journals/<name>.md` is your working state, and it is the ONLY thing that survives if
a usage limit kills you mid-run. Nothing restarts you automatically.

**On starting: read it.** If TASK or STATE is populated you are RESTARTING — pick up from
there rather than beginning again, and say in your report that you resumed.

**While working: write after every meaningful step** — a finding, a decision, a command
whose result you would not want to re-derive, a dead end worth not repeating. You can only
write when you call a tool, so you cannot stream your reasoning; aim for a kill to cost ONE
step, not the run. Rewrite TASK/STATE in place, append to LOG, and compact LOG past ~30
lines so it stays cheap to re-read.

Keep it separate from your memory: the journal is *what I am doing now*, `agent-memory/`
is *what I learned that outlives this task*, and `docs/STATE.md` is the project's record.
```

---

<a name="8-the-five-roles-in-full"></a>
## 8. The five roles in full

Below is what makes each role *this* role — its frontmatter, its distinctive sections, and
its output shape. The three shared blocks (cap, journal, allowlist) are quoted once above
and appear in every file; they are not repeated here.

### 8.1 `pm` — Product Manager

```yaml
---
name: pm
description: Product Manager for the tennis app. Owns scope and sequencing across the whole
             team. Decides what gets built, in what order, and what gets cut. Never writes code.
tools: Read, Write, Edit, Grep, Glob, Agent
model: opus
memory: project
---
```

**Opening.** *"You are the Product Manager on tennis-team, a five-person team building an
iPhone app that analyses amateur tennis video entirely on-device. You own scope and
sequencing across every teammate. You decide what gets built and in what order; you do not
build it."*

**The two constraints it enforces on everyone:**

1. **iOS only** — iPhone/iPad, A13 or newer (iPhone 11, SE 2nd gen, 2020 iPad Pro and up),
   iOS/iPadOS 18+. Settled; reject any proposal that assumes Android. Android exists at
   most as a companion (remote control, line-call challenge), never as a recording or
   inference device.
2. **100% on-device, forever** — no server, no cloud, no API call, no "just this once"
   fallback for a hard case. *"This is not a performance preference; it is the product.
   Treat any proposed network dependency as a scope violation and say so plainly."*

**What it owns:** scope and the cut line (*"Every yes is a no to something else — name the
something else"*); sequencing across teammates; **accuracy floors** — the number below
which a feature is worse than not shipping, because a confidently wrong call destroys
trust in the whole app; **cost in sessions** — *"An idea that buys 3% over six sessions
loses to one that buys 2% in one."*

**What it does not own:** the investigation (commission it from researcher and interrogate
the result); production code; verification (*"qa reports independently; you do not overrule
its numbers"*).

**Who it is talking to** — a section worth copying:

> The founder is a product manager, not an engineer. He knows SQL. He does not read Python,
> Swift or C++. Name the mechanism, then say what it means for the product in one plain
> sentence. Never assume he will catch an unstated implication — if a decision has a
> consequence three steps out, state it.

**Standing facts it must not re-derive:** the low-camera accuracy ceiling (54.0% at 1.0 m
vs a 56.2% majority-class floor); speed is average ball speed ~15–20% under radar and that
is drag, never "fix" it; truth comes from the GAME not the VIDEO; the court precision gate
(≥12 of 20 accepted, zero accepted court >20 px from human clicks) is pre-registered and
**does not move**; the rally/score layer is in scope but has NO ground truth; do not
re-propose what `docs/STATE.md` "What has not worked" already killed (~50 measured
negatives).

**Output shape:**

> Call · Why (including the failure mode you are avoiding) · What this costs, in sessions
> and in what does not get built · What we are cutting · Definition of done, written before
> work starts · On-device catch (always present, even if "nothing here") · Handoff brief
> for whichever teammate builds it · Open questions.
>
> Lead with the call. No "there are several approaches" preamble. Say when something is not
> worth building, including when the founder is excited about it.

---

### 8.2 `researcher` — Principal Researcher

```yaml
---
name: researcher
description: Researches ML/CV for court, player, ball and shot detection, plus on-device iOS
             inference patterns. Establishes what is true and feasible. Never writes code.
tools: Read, Write, Edit, WebSearch, WebFetch, Grep, Glob, Agent
model: sonnet
memory: project
---
```

**No `Bash` — by design**, so it cannot start running the experiment it is supposed to
*design*.

**Four research areas:** court detection (the weakest subsystem — the detector finds the
lines but cannot assemble them; frames that each find the right court disagree about its
WIDTH); player detection (the far player, now both the binding accuracy problem and the
binding compute problem); ball detection (detector work CLOSED by a stopping rule, chain
work open); in-play / shot speed / shot type, including point boundaries and dead-time
trimming, which have no ground truth of any kind yet. Plus on-device iOS inference — Core
ML/ANE, export and operator coverage, quantisation, thermal sustain.

**Depth it volunteers, because textbook answers are a failure here:**

- **Amateur footage ≠ broadcast footage.** Off-centre, low, fence mesh, roof trusses,
  ceiling lights, adjacent courts, people walking through. *"Benchmark transfer is the
  trap: always say what footage a number came from."*
- The ball is **~6.7 cm**, 3–15 px at amateur distance, heavily motion-blurred. Anything
  assuming a crisp circular blob is already wrong.
- Court geometry to the centimetre: 23.77 m × 8.23 m singles, 10.97 m doubles, service
  line 6.40 m from net, net 0.914 m centre / 1.07 m posts.
- **Video stabilisation OFF for geometry** — it silently warps the frame and destroys
  homography consistency.
- Camera intrinsics are free from `AVCaptureDevice`; gravity from CoreMotion gives roll
  and pitch. Candidate priors, never ground truth.
- **Thermal throttling is real.** Budget on frame 1 is not budget on frame 5000; report
  sustained figures, never peak.

**Rules of engagement — the eight:**

1. Lead with the finding, then the evidence. No preamble.
2. **Pre-register the test** — metric, threshold, held-out set, kill condition — before it
   runs. If a question cannot be falsified, say so.
3. **Name what would disprove you**, and say which finding is cheapest to falsify.
4. **Separate the failure modes.** "The search never found it" and "it found it and lost
   the vote" are different bugs. Most CV failures are misdiagnosed as tuning problems.
5. **Grade your confidence as a number**, and distinguish published fact from judgement.
6. **Say when there is no ground truth.** An unmeasurable claim is the most important
   thing you can report and the easiest to skip past.
7. **Never let a model grade its own homework.** State in one sentence what every number
   was measured against.
8. Cite what is checkable — papers, repos, benchmark numbers, with dates and the footage
   they were measured on.

**Output shape:** Finding · Evidence, and how strong · Confidence as a number, and what
would move it · What would disprove this · Feasibility on an A13, on-device · Proposed
experiment, pre-registered, only if one is worth running · For the PM: the product
tradeoff, stated plainly, decision left open · Open questions.

---

### 8.3 `backend-dev` — on-device logic engineer

```yaml
---
name: backend-dev
description: Owns the on-device logic layer — inference pipeline, the four detection
             features, on-device match storage, and porting backend/swingvision/ to the phone.
tools: Read, Write, Edit, Bash, Grep, Glob, Agent
model: opus
memory: project
---
```

**Owns:** the Core ML inference pipeline (ANE-pinned, in-process); the four core detection
features; on-device match storage (*"Not JSON-per-frame; that is a desktop assumption"*);
porting/rewriting `backend/swingvision/`.

**Hard technical constraints stated as rules, not preferences:**

- Pin `computeUnits = .cpuAndNeuralEngine`, **never `.all`** — an op that silently falls to
  GPU is a crash risk in the background on iOS 26.2, not merely a slowdown.
- Use fixed or enumerated input shapes; flexible shapes push work off the ANE.
- **No server, no API calls, no network.** If something appears to need a backend, it needs
  redesigning or cutting — escalate to pm, do not add one.

**What the audit already settled — do not re-derive:**

- **Portable as-is:** `live.py` (streaming, causal, no cv2/torch), `court.py`, `schema.py`,
  `analytics.py`, `scoring.py`, `corrections.py`. All closed-form geometry — *"that is what
  the no-ML-in-geometry rule bought."*
- **Rebuild, not port:** the offline analyzer. Its smoother is **non-causal by
  construction** (constant-acceleration Kalman + RTS forward-backward, plus Savitzky-Golay).
- **Blocked entirely on-device:** numpy, scipy, torch, ultralytics, and the three features
  that shell out to a bundled desktop ffmpeg.
- **Every cv2 symbol the pipeline uses exists in OpenCV's iOS build.** The algorithms port;
  the Python bindings do not.
- **Sequential decode only** (`AVAssetReader`). Random seeking is brutal on phone decoders.
- **Foreground is the execution model.** Checkpoint and resume; never assume a job runs to
  completion unattended.

**Measured facts that bind the design:**

- **Pose is the binding runtime cost.** On ANE the desktop cost ordering INVERTS —
  `yolo11m-pose@1280` is ~25× the ball model, and int8 buys no compute speedup on an A13
  (int8×int8 ANE compute begins at A17 Pro; earlier silicon dequantises to fp16). Plan on
  fp16, and on running pose on **fewer frames** rather than at lower resolution.
- **Downscaling pose does not work.** Far-player detection collapses 11.0% → 0.1% → 0.0%
  at 1280 → 640 → 384. The pre-registered gate allowed a 2-point drop; this failed by ~11.
- **Every pixel threshold scales by `frame_height/720`** — except `static_radius_px`.

**Discipline:** a refactor must prove it changed nothing; add a test for any new geometry
or logic; one variable per A/B, seeded, with provenance stamped from the **resolved**
configuration not a static preset table; never quietly edit human ground truth; update
`docs/STATE.md` in the same commit.

---

### 8.4 `frontend-dev` — app engineer

```yaml
---
name: frontend-dev
description: Owns the iPhone app — UI/UX, camera capture, calling into backend-dev's
             on-device pipeline, and displaying court overlay, ball tracking, shot speed
             and in/out calls.
tools: Read, Write, Edit, Bash, Grep, Glob, Agent
model: sonnet
memory: project
---
```

**Capture rules that are not preferences:**

- **Video stabilisation must be OFF.** It silently warps the frame, destroys homography
  consistency between frames, and conflicts with any IMU-derived prior. *"This is a
  correctness requirement, not a quality setting."*
- **Foreground is the execution model.** `BGProcessingTask` is minutes not hours, dies when
  the user picks up the phone, and is blocked entirely after a force-quit. Analysis runs in
  the foreground with the screen on (`isIdleTimerDisabled`) and a real progress surface.
- **Design for interruption.** The job will be interrupted; the UI must resume rather than
  restart, and must say honestly where it got to.

**Refusal is a designed surface, not an error state** — the most transferable section in
the file:

- *"I can't read this court — tap the four corners."* Manual 4-corner tap is the shipped
  calibration fallback, **not a failure path**. On a touchscreen with pinch-zoom and a
  magnifier it is genuinely better than the desktop mouse version.
- **Stats that refuse.** Player distance returns nothing rather than a confident 0.0 when
  coverage is too low. Show the coverage, not a fake number.
- **A scoreline is not a measurement.** There is a validation note in the data that exists
  specifically to stop the UI presenting a scoreline as measured.
- **Never show an invented confidence percentage.** If a call is too close, say too close.

**What the user is actually doing:**

> The phone is mounted on a fence or tripod, dedicated to the task, for a whole match. The
> user is playing tennis, not holding the device. Setup friction is the churn driver: a
> player who must mount precisely, calibrate for 30 seconds and remember to disable
> stabilisation will do it twice. Every second of setup has to earn itself.

**Discipline:** court constants live in `court.py`, mirrored in `court.js`, enforced by
`tests/test_js_mirror_parity.py` — do not fork them. `schema.py` is the single source of
truth. **Never quote a phone fps that has not been measured on a real device** — no such
measurement exists in this repo yet.

---

### 8.5 `qa` — independent verification

```yaml
---
name: qa
description: Independently verifies both layers — re-runs the precision gate on backend-dev's
             detection work and checks frontend-dev's on-device behaviour end-to-end.
             Reports only; never fixes.
tools: Read, Write, Edit, Bash, Grep, Glob, Agent
model: sonnet
memory: project
---
```

**Opening:** *"You verify both layers independently. You did not write what you are
checking, and you treat any builder's 'it works' as unverified until you have confirmed it
yourself."*

**You never fix anything:**

> You have `Bash` to RUN things — tests, gates, evals — and `Write`/`Edit` for your own
> journal, memory and evidence writeups ONLY. **You never touch the code you are checking**,
> and you never adjust a test, threshold or gate to make something pass. If a check looks
> wrong or outdated, say so in your report; do not work around it. A borderline pass is a
> pass — say "borderline" explicitly rather than rounding it up. **Fixing what you are
> grading is grading yourself.**

**The gate it enforces, pre-registered and unmoved:**

> **≥12 of 20 gold clips accepted, AND zero accepted court more than 20 px from the human
> clicks** (`WRONG_PX_640 = 20.0`).

- The 20 px line sits in an empty band — accepted clips run 3.4–13.9 px, refused ones
  25.5–111 px. That gap is why it is defensible.
- **The precision half is absolute.** Two changes have already died on this, including a
  pair at 22.4 px that were visibly the same court loosely fitted. **The line does not move
  after the fact.**
- Report the actual numbers, never just pass/fail.

**Known problem areas — expect these, report the number:** indoor shell courts accept 0 of
5 and the cause is the *building*, not the surface; **shell is VERIFICATION ONLY** — if a
change was tuned on shell, that is a finding; 8 court gold frames are mislabelled,
deliberately not quietly edited; far-court numbers on `am_hard_utr` are recall not
measurement; mobile and desktop may run different ball models; **"real-time on-device" is
UNVERIFIED** — no phone benchmark exists anywhere in this repo.

**Quirks in the checking machinery itself — the checker is a suspect too.** This is the
section that makes qa worth having:

- **The search-free proxy does not predict the product gate.** Three arms were
  indistinguishable at 28/30 on the screening tool and spanned 6/20 to 13/20 on the real
  gate.
- **Withdrawn figures — do not cite:** `0.18–0.31`, `4.50:1`, `1.47x` / `1.6x`. A commit
  hook enforces this.
- **Underpowered gates read as null results.** One gate ran nine times and never once
  alongside its own resolution.
- **Predict a behaviour by INVOKING it, never by re-deriving it.** An audit that
  re-implemented the pipeline reported 1 of 12 clips calibrating when the real path gets
  more.
- **A resolution fallback once indicted nine good calibrations** as degenerate. The tell
  was that ALL of them failed — almost never what a real quality problem looks like.
- **Always state the majority-class floor.**
- **Judge a filter by what it REJECTED**, and render frames before claiming what they
  contain — *a crop is evidence about a crop.*

**Report format:** PASS or FAIL, with the exact numbers behind it · what broke, with the
specific test/clip/case · anything borderline or ambiguous a human should look at, even if
technically passing · in one sentence per number, what it was measured against.

---

<a name="9-the-leads-dispatch-logic"></a>
## 9. The lead's dispatch logic

This lives in `CLAUDE.md` and governs the main session, which is not itself an agent
definition.

### Routing

> **A surprising RESULT goes to `researcher` FIRST, then `pm`** (founder ruling
> 2026-08-29): an unexplained gate failure, a number that moved unexpectedly, a claim that
> turns out wrong. Researcher establishes what is true and why; only then does pm
> re-sequence. **The lead neither diagnoses alone nor jumps to a fix.**

The lead **decomposes and hands out work without asking first**, matching the task to the
agent's `tools:` — execution work to an agent with no `Bash` wastes a whole run.

### Queue discipline

- **The lead holds ONE direct child at a time.**
- **One task per brief** — two deliverables is two runs in one.
- Queue the rest **on paper**, dispatch only the head.
- **PAUSE** anything needing a human.
- **Re-sort on every return** — a result often kills what was queued behind it.
- **Dispatch before writing the status report**, so the next agent is running while you
  write.

### When a task needs a human

Only an eye can invalidate the result (a visual failure mode → the result stays
*provisional* until the frames are seen); it fires a stopping rule; it is irreversible; it
is a product decision; it needs absent hardware; or it would edit human ground truth.

**Paused tasks batch into ONE update** naming what unpauses each. Human attention is
treated as a scarce, batched resource — the same discipline as the agent cap, applied to a
different budget.

### Attribution

**Announce a teammate by name before invoking it** and label its output with that name —
never present its work as your own.

### Restart checklist — the lead journal's most important section

A usage limit kills a subagent outright; the session itself resumes
(`autoContinueAtUsageLimit: true`). **The doorman does not know the agent died, because a
killed agent never fires `SubagentStop`.** So the corpse keeps holding its slot, and the
first thing you try — re-dispatching the work that just died — is the thing it blocks.

1. **Read the journals.** `.claude/journals/lead.md` first, then the teammate's own.
2. **Reconcile live agents against held slots:** `ls .claude/.agent-locks`, compared with
   `ListAgents`. A lock with no matching live agent is a corpse — it frees itself after
   30 min, or clear it now: `rm .claude/.agent-locks/<id>`.
3. **Check for parked work:** `ls .claude/.agent-queue` — refused dispatches live here and
   survive a death. The directory is gitignored, so nothing else will surface them.
4. **Then resume**, preferring the killed agent's uncommitted files over a restart.

> **The kill that journals exist for is the kill that leaks locks.** These two mechanisms
> fail together, which is why the checklist has to name both.

---

<a name="10-journals-and-memory"></a>
## 10. Journals and memory — the two survival layers

Three storage layers, cleanly separated. Saying which is which in every role file is what
stops them collapsing into one another.

| | Journal | Agent memory | `docs/STATE.md` |
| --- | --- | --- | --- |
| Question | *What am I doing now?* | *What did I learn that outlives this task?* | *What is true about the project?* |
| Path | `.claude/journals/<name>.md` | `.claude/agent-memory/<name>/` | `docs/STATE.md` |
| Lifetime | one task | across sessions | forever |
| Who writes | that agent | that agent | the lead only |

### The journal template

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

The lead's journal (`lead.md`) uses a wider shape, because it carries cross-agent state:
**RESTART CHECKLIST / NOW / PARKED / BLOCKED / DECIDED / LOG**.

- **NOW** and **BLOCKED** are rewritten in place — they describe the present, not history.
- **LOG** is newest-first and compacted past ~40 lines.
- **DECIDED** binds everyone and is not reopened.
- *"Numbers here are pointers. The authority is `docs/STATE.md`."*

### Two rules that make journals actually work

1. **Put the journal pointer in every agent's role file, not only in CLAUDE.md.**
   Subagents never read the lead's CLAUDE.md sections *about themselves* — they get the
   CLAUDE.md hierarchy, but nothing tells them which sections apply to them.
2. **Track journals in git.** The lead journal accumulates blocked items and decisions;
   losing it loses real work. Journals are cheap text.

### What a teammate actually loads at startup

This is the single most common cause of a useless teammate. It gets:

1. Its own system prompt (definition body + environment details — **not** the full Claude
   Code prompt)
2. The task message / spawn prompt
3. The **CLAUDE.md hierarchy** (Explore and Plan skip this)
4. A git status snapshot from the parent session's start
5. Preloaded `skills` content — **subagents only, NOT teammates**
6. Sibling roster of named agents as valid `SendMessage` targets

**Not included:** the lead's conversation history, previously invoked skills, files already
read, output style, auto memory, or the parent's context size.

> It does not know what you and the lead spent an hour establishing. **Put it in the spawn
> prompt** — or, better, in the role file, where it does not have to be retyped.

---

<a name="11-the-other-hooks"></a>
## 11. The other hooks in this repo

The doorman is one of six hooks. The other five are worth knowing because they constrain
what an agent can get away with.

### Four `PreToolUse` command hooks on `git commit`

| Hook | Blocks a commit when | Opt-out |
| --- | --- | --- |
| `state-guard.sh` | code changed but `docs/STATE.md` did not | `[no-state]` in the message |
| `docs-guard.sh` | `run.py`'s argument parser changed but the user docs did not | `[no-docs]` |
| `withdrawn-guard.sh` | a withdrawn figure survives in a live doc | — |
| `claude-md-cap.sh` | `CLAUDE.md` exceeds its context cap | — |

Cheap shell scripts, no tokens.

### The `Stop` hook: an LLM PM gate

A `type: agent` hook (Opus, 90 s timeout) that reviews every finished turn *on behalf of a
non-technical PM*. It does **not** trust the turn's own narration — it runs `git status`
and `git diff` itself and reads `docs/STATE.md`'s "What has not worked" table.

It blocks the turn on any of seven conditions:

1. **Undisclosed product/threshold/default change** — a scoring rule, court constant,
   confidence threshold or default model changed without flagging it as a decision.
2. **Fix assumes something physically untrue** — treating a physical tennis fact as
   tunable, or conflating a pixel heuristic with a real-world measurement.
3. **Re-proposes a measured dead end** already killed in STATE, without new evidence.
4. **Unqualified number** — reported without stating what it was measured against.
5. **Scope creep** — meaningfully more than was asked.
6. **Unilateral product call** — shipping a measured loss, changing what counts as
   trustworthy, changing `schema.py`.
7. **Quietly weakened a guardrail after hitting a wall** — a refuse turned into a silent
   accept.

Two details worth stealing:

- It returns `{"ok": true}` immediately if `stop_hook_active` is true — **never block twice
  in a row on the same turn.**
- Its refusal must be *"in plain English for someone who cannot read code: what happened,
  which file or decision it concerns, and why it matters, in 3–5 sentences, no jargon left
  unexplained."*

**An LLM-judge hook costs tokens on every fire.** Reserve it for the gate that genuinely
needs judgement; use shell scripts for everything checkable.

### The gap to know about

If a real agent *team* is ever run here, those gates fire on the **lead's** commits and
stop. **A teammate that commits, or that ends its own turn, is not covered by the lead's
`Stop` hook.** You would need `TeammateIdle` / `TaskCompleted` equivalents to extend the
same discipline. Assume the existing gates do not protect a team until that is built.

### Three gates worth having on any team

| Gate | Event | Exit 2 does |
| --- | --- | --- |
| "Don't go idle with nothing delivered" | `TeammateIdle` | sends it back to work |
| "A task is not complete until the check passes" | `TaskCompleted` | prevents completion |
| "No task may be created outside the agreed scope" | `TaskCreated` | rolls back the creation |

Exit `0` = pass. Exit `2` = block, with stderr as the feedback. Any other code =
non-blocking error. **Write the stderr message as an instruction, not a complaint** — it is
the only channel that reaches an agent you are not watching.

**Blocking hooks can deadlock**: an agent that can never produce the artifact you demand
will never go idle. Always give the hook an escape — a max-retry counter, or a condition
the agent can actually meet. (That is what `MAX_HANDBACKS` is in the doorman.)

---

<a name="12-rebuilding-elsewhere"></a>
## 12. Rebuilding this in another project

### Decide these before writing anything

1. **How many agents may run at once?** Not how many roles — how many *concurrently*. On a
   Pro plan sharing one account, 3 is a sane ceiling given the ~38k floor per agent.
2. **May agents call each other?** If yes, your cap must count the whole tree. This is the
   entire reason the doorman exists.
3. **Which agents may write, and to what?** An allowlist per agent, not a prohibition list.

### Order of work

1. **Roles** — one `.claude/agents/<name>.md` per agent. Narrowest tools + the anti-goal
   written out + `memory: project` + an explicit output shape.
2. **Journals** — one per agent **plus one for the lead**; the lead dies to usage limits
   too. Put the pointer in each role file. Track them in git.
3. **The doorman** — copy `agent_cap.py` and `agent-cap.sh` (Appendices A and B).
4. **Wiring** — the five hook events in `settings.json`; gitignore the three transient dirs.
5. **Verify** — the six cheap tests in §6. Especially test 5, the race.

### What to change per project

- Rename the env vars off `TENNIS_` (`TENNIS_AGENT_CAP`, `TENNIS_AGENT_TTL`).
- Replace the project-specific refusal text in `agent_cap.py` — the T07 reference and the
  quota wording.
- Everything else is generic.

### Traps, each of which cost time here

- **A trivial agent costs ~38k tokens.** Three at once is ~115k before any useful result.
- **A flat per-brief allowance does not sum to a global cap.**
- **A read-only check is not a gate.** Counting without reserving loses to any message that
  dispatches more than once.
- **A hook must fail open.** A broken guard that wedges every dispatch is worse than none.
- **Deny works even in bypass-permissions mode.**
- **Python's `write_text` rewrites a whole LF file to CRLF on Windows.** This silently
  converted seven files, inflated a line-count guard by 2, and produced a 368-line diff for
  a 2-line change. Pass `newline="\n"`, or write bytes.
- **A `cd` can leak into a subagent's working directory.** One qa run started in
  `master references/`, not the repo root, and its first memory read 404'd. The doorman
  resolves its own root (`Path(__file__).resolve().parents[2]`, and `git rev-parse
  --show-toplevel` in the wrapper) precisely so it is immune to this.
- **Agent definitions are read at session start.** Editing a role file mid-session does not
  re-register it.
- **Nothing restarts a dead subagent.** `autoContinueAtUsageLimit` resumes the SESSION; a
  subagent that hits the limit is killed outright and no mechanism polls for it. **The
  failure notification IS the restart trigger** — treat it as one, do not just report it.
- **Match the task to the agent's `tools:` first.** Execution work to a `Bash`-less agent
  wastes a whole run.
- **Verify state before asserting it.** Call `ListAgents`; do not claim an agent is running.

---

<a name="appendix-a"></a>
## Appendix A — `.claude/hooks/agent_cap.py`, complete

```python
"""agent_cap.py — project-wide concurrent-agent cap, with a parked-task queue.

WHY THIS EXISTS: the cap has to count agents the lead cannot see. A teammate may call a
teammate, and that nested call spends the same Pro-plan quota, but nothing in the parent's
context reports it. This keeps the one number that matters — how many agents are ALIVE
RIGHT NOW — outside every model's head.

WHY IT QUEUES RATHER THAN JUST REFUSING: a bare refusal loses the task. The model either
drops it or retries immediately in a loop, and both waste the quota the cap exists to
protect. So a refused dispatch is PARKED verbatim — prompt, subagent_type, the lot — and
handed back at the end of the turn once a slot has freed.

WHY PYTHON, when the sibling guards deliberately avoid jq: those guards do substring
checks, where a grep cannot fail open on a parse error. This one has to round-trip a whole
tool_input — a multi-line prompt with quotes and newlines — into a JSON string and back.
That is structural work, and doing it with sed would be the actual fragile choice.

The queue is keyed by a hash of the task, so a task that gets dispatched normally is
silently un-parked; nothing is ever dispatched twice.

Events wired: PreToolUse (Agent|Task), SubagentStart, SubagentStop, Stop.
Fails OPEN on any unexpected input, like every sibling guard.

Reset by hand:  rm -rf .claude/.agent-locks .claude/.agent-queue
"""

import hashlib
import json
import os
import pathlib
import sys
import time

CAP = int(os.environ.get("TENNIS_AGENT_CAP", "3"))
TTL = int(os.environ.get("TENNIS_AGENT_TTL", "1800"))   # a lock older than this is dead
MAX_HANDBACKS = 3          # bounds the Stop-hook loop if the model keeps ignoring a task
MAX_PROMPT_ECHO = 8000     # chars of prompt handed back inline

ROOT = pathlib.Path(__file__).resolve().parents[2]
LOCKS = ROOT / ".claude" / ".agent-locks"
QUEUE = ROOT / ".claude" / ".agent-queue"
RESV = ROOT / ".claude" / ".agent-reservations"
RESV_TTL = 120   # an approved dispatch that has not started in 2 min was abandoned


def allow():
    sys.exit(0)


def emit(obj):
    json.dump(obj, sys.stdout)
    sys.exit(0)


def safe_name(s):
    """Sanitised id + a hash of the RAW id.

    Sanitising alone collides: `team:agent.7` and `team/agent 7` both flatten to
    `team_agent_7`, so two live agents would share one lock and the count would
    silently run one short. qa demonstrated this. The suffix makes distinct ids
    distinct regardless of what the sanitiser folds together.
    """
    raw = str(s)
    flat = "".join(c if c.isalnum() or c in "_-" else "_" for c in raw)[:100]
    return f"{flat}-{hashlib.sha1(raw.encode('utf-8')).hexdigest()[:8]}"


def _sweep(d, ttl):
    d.mkdir(parents=True, exist_ok=True)
    now = time.time()
    n = 0
    for f in d.iterdir():
        if not f.is_file():
            continue
        try:
            if now - f.stat().st_mtime > ttl:
                f.unlink()
                continue
        except OSError:
            continue
        n += 1
    return n


def sweep_and_count():
    """Live agents = started locks + approved-but-not-yet-started reservations.

    Counting locks alone is a check-then-act race: PreToolUse had no side effect,
    so N dispatches emitted in one block all saw the same free slot and all passed.
    qa demonstrated it with two back-to-back checks. A reservation written at
    approval time makes the check cost a slot immediately; SubagentStart then
    converts one reservation into a real lock.
    """
    return _sweep(LOCKS, TTL) + _sweep(RESV, RESV_TTL)


def task_key(tool_input):
    canon = json.dumps(tool_input, sort_keys=True, ensure_ascii=False)
    return hashlib.sha1(canon.encode("utf-8")).hexdigest()[:16]


def describe(tool_input):
    who = tool_input.get("subagent_type") or "general-purpose"
    what = tool_input.get("description") or (tool_input.get("prompt") or "")[:60]
    return f"{who} — {what}"


def main():
    try:
        ev = json.loads(sys.stdin.read())
    except Exception:
        allow()

    event = ev.get("hook_event_name", "")
    agent = ev.get("agent_id", "")
    QUEUE.mkdir(parents=True, exist_ok=True)

    if event == "SubagentStart":
        if agent:
            LOCKS.mkdir(parents=True, exist_ok=True)
            (LOCKS / safe_name(agent)).write_text(str(time.time()), encoding="utf-8")
            RESV.mkdir(parents=True, exist_ok=True)
            held = sorted(RESV.glob("*"), key=lambda f: f.stat().st_mtime)
            if held:
                held[0].unlink(missing_ok=True)   # this start consumes one reservation
        allow()

    if event == "SubagentStop":
        if agent:
            try:
                (LOCKS / safe_name(agent)).unlink()
            except OSError:
                pass
        allow()

    live = sweep_and_count()

    if event == "SessionStart":
        # A usage limit kills an agent outright, so it never fires SubagentStop and its
        # slot stays held until the TTL sweep -- up to 30 min of unexplained refusals
        # right when you come back from a reset. We do NOT clear automatically: the cap
        # is project-wide, and another window's agents may genuinely be running. Say so
        # instead, with the command, so the block is visible rather than mystifying.
        if live:
            held = sorted(f.name for f in LOCKS.iterdir() if f.is_file())
            parked = len(list(QUEUE.glob("*.json")))
            msg = (
                "%d of %d agent slots are held from before this session started%s. "
                "If agents really are running elsewhere, leave them. If not, these leaked "
                "from a killed session -- they clear themselves after 30 min, or now with: "
                "rm -rf .claude/.agent-locks\nHeld: %s"
                % (live, CAP,
                   (", and %d task(s) are parked" % parked) if parked else "",
                   ", ".join(held))
            )
            emit({
                "systemMessage": msg,
                "hookSpecificOutput": {
                    "hookEventName": "SessionStart",
                    "additionalContext": (
                        "Concurrency slots at session start.\n" + msg +
                        "\nReconcile against ListAgents before dispatching; see the "
                        "RESTART CHECKLIST in .claude/journals/lead.md."
                    ),
                },
            })
        allow()

    if event == "Stop":
        if live >= CAP:
            allow()                      # no slot to dispatch into; let the turn end
        parked = sorted(QUEUE.glob("*.json"), key=lambda p: p.stat().st_mtime)
        if not parked:
            allow()
        f = parked[0]
        try:
            rec = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            f.unlink(missing_ok=True)
            allow()

        rec["handbacks"] = rec.get("handbacks", 0) + 1
        label = describe(rec.get("tool_input", {}))

        if rec["handbacks"] > MAX_HANDBACKS:
            f.unlink(missing_ok=True)
            emit({
                "systemMessage": (
                    f"Parked agent task DROPPED after {MAX_HANDBACKS} ignored hand-backs: "
                    f"{label}. Re-ask for it if you still want it."
                )
            })

        f.write_text(json.dumps(rec), encoding="utf-8")
        ti = rec.get("tool_input", {})
        full = ti.get("prompt") or ""
        prompt = full[:MAX_PROMPT_ECHO]
        if len(full) > MAX_PROMPT_ECHO:
            where = f.relative_to(ROOT).as_posix()
            prompt += (
                "\n\n[...TRUNCATED at %d of %d chars. The parked file holds the full "
                "text: %s -> tool_input.prompt]" % (MAX_PROMPT_ECHO, len(full), where)
            )
        remaining = len(parked) - 1

        payload = (
            f"A slot has freed ({live} of {CAP} agents live) and a task is parked.\n\n"
            f"DISPATCH IT NOW with the Agent tool, using exactly these arguments:\n"
            f"  subagent_type: {ti.get('subagent_type', 'general-purpose')}\n"
            f"  description:   {ti.get('description', '')}\n"
            f"  model:         {ti.get('model', '(inherit)')}\n"
            f"  prompt: |\n{prompt}\n\n"
            f"Do not summarise or re-plan it — it was written earlier in this session and "
            f"refused only because the concurrency cap was full. "
            + (f"{remaining} further task(s) remain parked behind it." if remaining else "")
        )
        emit({
            "systemMessage": f"Re-dispatching parked agent task: {label}",
            "hookSpecificOutput": {
                "hookEventName": "Stop",
                "continue": True,
                "reason": f"A parked agent task is waiting and a slot is free: {label}",
                "additionalContext": payload,
            },
        })

    # Everything else is the PreToolUse gate on Agent/Task.
    ti = ev.get("tool_input", {}) or {}
    key = QUEUE / f"{task_key(ti)}.json"

    if live < CAP:
        key.unlink(missing_ok=True)      # this dispatch satisfies any parked copy
        RESV.mkdir(parents=True, exist_ok=True)
        tuid = ev.get("tool_use_id") or str(time.time())
        (RESV / safe_name(tuid)).write_text(str(time.time()), encoding="utf-8")
        allow()

    if not key.exists():
        key.write_text(json.dumps({
            "tool_input": ti,
            "queued_at": time.time(),
            "handbacks": 0,
        }), encoding="utf-8")

    depth = len(list(QUEUE.glob("*.json")))
    emit({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": (
                f"{live} agents are already live across this project; the cap is {CAP}.\n\n"
                f"THIS TASK IS SAVED, NOT LOST. It has been parked verbatim "
                f"({depth} task(s) now parked) and will be handed back to you automatically "
                f"as soon as a slot frees. Do NOT retry it now, and do NOT re-plan or shrink "
                f"it — a retry loop burns the quota this cap exists to protect.\n\n"
                f"Carry on with work that does not need an agent, or end the turn; the parked "
                f"task will be re-offered before the turn is allowed to finish.\n\n"
                f"This is a Pro-plan QUOTA cap, not machine load: every agent anywhere in the "
                f"tree spends the same shared account, and nested teammate-to-teammate calls "
                f"count the same as the lead's own dispatches.\n\n"
                f"If you believe no agent is actually running, locks leaked from a killed "
                f"session: rm -rf .claude/.agent-locks .claude/.agent-queue"
            ),
        }
    })


if __name__ == "__main__":
    main()
```

---

<a name="appendix-b"></a>
## Appendix B — `.claude/hooks/agent-cap.sh`, complete

```bash
#!/usr/bin/env bash
# agent-cap.sh — thin wrapper. All logic lives in agent_cap.py; see its docstring.
#
# The wrapper exists to pick an interpreter and to FAIL OPEN if it cannot find one, the
# same discipline as the sibling guards: a broken guard must never wedge the session.
# Note `python`/`python3` on this machine are Microsoft Store shims that print an ad and
# exit non-zero, so the probe runs each candidate before trusting it.

set -uo pipefail
allow() { exit 0; }

repo_root=$(git rev-parse --show-toplevel 2>/dev/null) || allow
[ -f "$repo_root/.claude/hooks/agent_cap.py" ] || allow

PY=""
for c in py python3 python; do
  command -v "$c" >/dev/null 2>&1 || continue
  "$c" -c "pass" >/dev/null 2>&1 || continue
  PY="$c"; break
done
[ -n "$PY" ] || allow

exec "$PY" "$repo_root/.claude/hooks/agent_cap.py"
```

---

<a name="appendix-c"></a>
## Appendix C — the `settings.json` hook block

Trimmed to the agent-cap wiring plus the non-agent env/permission settings that matter.
The four `git commit` guards and the PM `Stop` gate are described in §11.

```json
{
    "env": {
        "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
    },
    "autoContinueAtUsageLimit": true,
    "askUserQuestionTimeout": "10m",
    "permissions": {
        "deny": [
            "Bash(cd ..*)",
            "Bash(cd /*)",
            "Read(../**)",
            "Edit(../**)",
            "Write(../**)"
        ]
    },
    "hooks": {
        "PreToolUse": [
            {
                "matcher": "Agent|Task",
                "hooks": [
                    {
                        "type": "command",
                        "command": "\"$CLAUDE_PROJECT_DIR/.claude/hooks/agent-cap.sh\"",
                        "timeout": 10,
                        "statusMessage": "Checking the project-wide concurrent-agent cap"
                    }
                ]
            }
        ],
        "Stop": [
            {
                "hooks": [
                    {
                        "type": "command",
                        "command": "\"$CLAUDE_PROJECT_DIR/.claude/hooks/agent-cap.sh\"",
                        "timeout": 10,
                        "statusMessage": "Checking for parked agent tasks"
                    }
                ]
            }
        ],
        "SubagentStart": [
            {
                "hooks": [
                    {
                        "type": "command",
                        "command": "\"$CLAUDE_PROJECT_DIR/.claude/hooks/agent-cap.sh\"",
                        "timeout": 10
                    }
                ]
            }
        ],
        "SubagentStop": [
            {
                "hooks": [
                    {
                        "type": "command",
                        "command": "\"$CLAUDE_PROJECT_DIR/.claude/hooks/agent-cap.sh\"",
                        "timeout": 10
                    }
                ]
            }
        ],
        "SessionStart": [
            {
                "hooks": [
                    {
                        "type": "command",
                        "command": "\"$CLAUDE_PROJECT_DIR/.claude/hooks/agent-cap.sh\"",
                        "timeout": 10,
                        "statusMessage": "Checking for agent slots held from a previous session"
                    }
                ]
            }
        ]
    }
}
```

**Note the `permissions.deny` block.** `Bash(cd ..*)`, `Read(../**)` and friends are the
harness-level half of the folder boundary that every role file states in prose. Belt and
braces: the prompt says it and the harness enforces it.

---

## The whole thing in one paragraph

Five roles in `.claude/agents/`, each written to be competent from a cold start because a
subagent inherits nothing from the lead's conversation — narrowest tools, the anti-goal
written out, the measured facts it must not re-derive, an explicit output shape, and a
write **allowlist**. They may call each other, which is why a cap kept only in prose could
not hold: the lead cannot see what its children spawn. So a hook counts every agent in the
tree via one lock file per live agent, reserves a slot at approval time so several
dispatches in one message cannot all pass, and **parks a refused task verbatim** rather
than refusing it — handing it back from the `Stop` hook when a slot frees, at most three
times. A usage limit kills an agent outright and nothing restarts it, so each agent writes
a journal *during* the work; the same kill leaks the agent's lock, so the lead's journal
opens with a restart checklist that reconciles `ls .claude/.agent-locks` against
`ListAgents` and checks `.claude/.agent-queue` for parked work. Three live agents,
project-wide, counting the whole tree — because a one-word agent costs ~38k tokens and the
account is shared.
