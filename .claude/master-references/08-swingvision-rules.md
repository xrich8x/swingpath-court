# 08 — Applying this in the SwingVision repo

**Read this before spawning anything in this project.** The generic advice in
files 01–07 is correct; this file says where the repo overrides it.

## Standing rule: do not fan out here

`CLAUDE.md`, Gotchas:

> **Don't fan out to parallel agents.** The bottleneck is one GPU and one gold
> set. Two multi-agent runs burned ~971k tokens for zero results.

This is a **measured** result in this repo, not a preference. Two things make
teams structurally bad here:

1. **One GPU.** Parallel teammates that all want to train or run inference
   serialise on the same device. You pay N context windows for 1x throughput.
2. **One gold set.** Every teammate scoring against the same held-out clips
   multiplies the chance of the thing rule 1 of CLAUDE.md exists to prevent —
   a number measured against something that is not independent truth.

Add the harness rule already in force in this session: **do not call the Agent
tool unless the user requests it.**

## The workflow this repo uses instead

`CLAUDE.md`'s feature workflow is **four sequential stages in four separate
sessions**, gated on express user approval at each stop:

1. `pm-agent` → spec. **STOP**, show, wait for approval.
2. `researcher-agent` with the approved spec, **in its own new chat session**.
   **STOP**, show, wait.
3. Implement, **in its own new chat session**, handed the approved spec and
   findings.
4. `qa-verifier` → independent check, **in its own new session**. **STOP**, show
   the report. On FAIL, fix and re-verify from this step.

Done only when qa-verifier reports PASS **and** the user expressly approves.

This is the **opposite shape** to an agent team, deliberately:

| | Agent team | This repo's workflow |
| --- | --- | --- |
| Concurrency | Parallel | Strictly sequential |
| Context | Each teammate cold | Each stage gets **only** the approved output of the one before |
| Gate | Lead approves autonomously | **The user approves, expressly** |
| Coupling | Teammates message each other | Stages never talk; the artifact is the interface |

Do not "improve" it by running the four as a team. The separation is the point:
the researcher must not inherit the PM back-and-forth, the coder must not
inherit the research dead ends, and **QA must read the diff fresh, not inherit
the coder's framing of what it did.** A team shares a mailbox, which is exactly
the contamination this design removes.

Also note: with `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`, invoking these three
roles could **silently promote them to teammates** (see 07), which would break
stage isolation and swap each stage's report for an idle notification. If teams
are ever enabled in this project, the workflow must be run with them off.

## What the three existing definitions get right

`.claude/agents/` holds `pm-agent`, `researcher-agent`, `qa-verifier` — all
`model: opus`, `memory: project`, with deliberately narrow tools:

- **`qa-verifier`: `Read, Bash, Grep, Glob`** — and the body says *"You never
  edit or write code, and you never adjust a test or gate to make something
  pass."* That is the model: the tool list and the anti-goal say the same thing
  twice, so neither the harness nor the prompt alone has to hold the line.
- **`researcher-agent`: `Read, WebSearch, WebFetch, Grep, Glob`** — no `Bash`,
  so it cannot start running the experiment it is supposed to *design*.
- **`pm-agent`: `Read, Grep, Glob`** — read-only. It produces briefs, not code.
- All three carry `memory: project`, so `.claude/agent-memory/<name>/MEMORY.md`
  accumulates across sessions. The body of each tells it to consult and update
  that memory — without that instruction it will not.

Reuse this pattern for any new role: **narrowest tools + the anti-goal written
out + project memory + an explicit output shape.**

**Caveat observed 2026-08-28:** all three files on disk list narrower `tools:`
than the agent types registered in the running session, which still show
`Write, Edit` on each. Agent definitions are read **at session start** — editing
`.claude/agents/*.md` mid-session does not re-register the type. After narrowing
a definition, start a new session before relying on the restriction, and never
assume the running session's allowlist matches the file you just edited.

## Where a team *would* be legitimate here

Only where the work is genuinely read-only, does not touch the GPU, and does not
score against gold:

- **Documentation reconciliation** — `docs/STATE.md` vs the evidence files vs
  `README.md` / `USER_GUIDE.md`, one owner per doc set.
- **Adversarial audit of a claim already made** — e.g. three lenses on "is this
  number measured against independent truth?", which is Recipe 2 applied to
  CLAUDE.md rule 1. Read-only, no runs.
- **Frontend/backend split** where the contract (`schema.py`) is frozen and file
  ownership is strictly disjoint.

Everything involving training, evaluation, or a gold-set number stays single
session, because of the GPU and the leak guards
(`assert_no_gold_leak`, `assert_no_court_gold_leak`, `assert_no_swingvision_leak`).

## Repo-specific gates already in place

`.claude/settings.json` runs:

- Four `PreToolUse` command hooks on `git commit` — `state-guard.sh`,
  `docs-guard.sh`, `withdrawn-guard.sh`, `claude-md-cap.sh`.
- A `Stop` hook of `type: agent` (Opus, 90s) acting as a **PM gate**: it runs
  `git status` / `git diff` itself and blocks the turn on undisclosed threshold
  changes, physically-untrue fixes, re-proposed dead ends, **unqualified
  numbers**, scope creep, unilateral product calls, and quietly weakened
  guardrails.

If a team is ever run here, those gates fire on the **lead's** commits and stop.
A teammate that commits, or that ends its own turn, is **not** covered by the
lead's `Stop` hook — you would need `TeammateIdle` / `TaskCompleted` equivalents
(see 05) to extend the same discipline to teammates. **Assume the existing gates
do not protect a team until that is built.**
