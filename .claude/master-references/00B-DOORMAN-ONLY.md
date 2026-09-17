# The doorman — complete, self-contained

**Everything about the concurrency doorman: the limit it enforces, why each piece of it
exists, the wiring, how to verify it, and the full source of both files.** Nothing about
the five-agent team except the parts the doorman depends on.

This is an EXTRACT of `00-THE-FULL-SETUP.md` §§3–6 and Appendices A–C, plus qa's
independent verification report. The two code appendices were checked byte-for-byte
against the live `.claude/hooks/` files at extraction time and are identical. Every
number here was measured in the SwingVision repo, not estimated.

Extracted 2026-09-02. Source of truth for the code: `.claude/hooks/agent_cap.py` and
`.claude/hooks/agent-cap.sh`.

## Contents

1. [The agent limitation — three different limits people confuse](#3-the-agent-limitation)
2. [The doorman — what it does and why each piece exists](#4-the-doorman)
3. [Wiring](#5-wiring)
4. [Verifying it cheaply](#6-verifying-it)
5. [Appendix A — `agent_cap.py`, complete](#appendix-a)
6. [Appendix B — `agent-cap.sh`, complete](#appendix-b)
7. [Appendix C — the `settings.json` hook block](#appendix-c)
8. [Appendix D — the independent verification report, verbatim](#appendix-d)

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

<a name="appendix-d"></a>
## Appendix D — the independent verification report, verbatim

`.claude/agent-memory/qa/agent_cap_doorman_verified.md`, written by the qa agent on
2026-08-28. Reproduced unedited — including the three gaps it found. **All three are
fixed in the Appendix A code above** (reservations for the race, a sha1 suffix for the
collision, an explicit truncation notice naming the queue file). It is kept verbatim
because the finding, not the fix, is the reusable part: nine checks passed and three
broke it, and the three came from *invoking* the guard rather than reading it.

```markdown
---
name: agent-cap-doorman-verified
description: Independent verification of the concurrency-cap hook (agent_cap.py) and journal system, 2026-08-28 — what's solid, what's a real gap
metadata:
  type: project
---

Verified `.claude/hooks/agent_cap.py` + `agent-cap.sh` (the "doorman") and the journal
system end to end on 2026-08-28, by feeding synthetic hook payloads directly to the
script — never by re-deriving the logic by reading it. All 10 items in the brief were
checked; full numbers are in that day's report to the lead, not duplicated here.

**Solid (measured, not just read):** cap denies at exactly live>=3 (allow at 0/1/2, deny
at 3/4); every malformed-input shape (bad JSON, empty stdin, plain text, no git repo,
no python on PATH) fails open silently; parking stores `tool_input` verbatim (model +
full prompt) at `.claude/.agent-queue/<sha1-16>.json`; hand-back at Stop emits
`continue:true` + `additionalContext` with the original args and is bounded — offered on
handbacks 1/2/3, dropped with a systemMessage on the 4th; a normally-redispatched
identical `tool_input` self-clears its queued twin (task_key is a sorted-JSON sha1, so
key order doesn't matter); TTL sweep actually removes a lock backdated past 1800s and the
live count reflects the removal in the same call. Root resolution (`Path(__file__).
resolve().parents[2]` in Python, `git rev-parse --show-toplevel` in the wrapper) is
robust to cwd — confirmed correct even when invoked from an unrelated untracked
subfolder inside the repo.

**Real gaps found, not fixed (not my job) — worth a human look:**
1. **TOCTOU race, demonstrated not just argued.** The PreToolUse check has ZERO side
   effect on the live count — locks are only written later at `SubagentStart`. Fired two
   independent PreToolUse checks back-to-back against the same 1-free-slot state with no
   lock created in between: both returned allow. If the lead ever dispatches multiple
   Agent calls in one message (CLAUDE.md tells it to do exactly this) while only 1 slot
   is free, nothing in this code prevents all of them passing. Whether the harness
   serializes tool-call hooks enough to close this in practice is unverified — did not
   test with real concurrent agents (would have corrupted the very measurement).
2. **`safe_name()` collision, demonstrated live.** Two different `agent_id` values
   differing only by punctuation (`team:agent.7` vs `team/agent 7`) sanitize to the
   identical lock filename `team_agent_7`; firing both as separate `SubagentStart`
   events produced ONE lock file, not two — an undercount. Whether real Claude Code
   `agent_id`s can ever contain such characters is unknown from inside this repo (no
   schema doc found) — flag, don't assume exploitable.
3. **Silent truncation over `MAX_PROMPT_ECHO` (8000 chars).** The queue file itself
   stores the full prompt verbatim regardless of length (confirmed at 9000 chars). But
   the Stop-event hand-back's `additionalContext` truncates to 8000 chars with **no
   truncation notice in the message** — a human re-reading the hand-back would not know
   it was cut. Only matters for prompts over 8000 chars; typical dispatch prompts
   round-trip fully.
4. Hook `timeout: 10` in settings.json — fail-open vs fail-closed on an actual timeout
   is a Claude-Code-harness behavior, not this repo's code; not tested (would require
   deliberately hanging a hook mid-session).

Journals: all 6 exist (5 agents + lead) and are git-tracked; each agent role file's
"Your journal" section names its own correct path; `.gitignore` correctly excludes
`.claude/.agent-locks/` and `.claude/.agent-queue/`. `lead.md`'s RESTART CHECKLIST
claims (30-min TTL, queue survives a session, locks reconcilable against `ListAgents`)
all check out against the code — TTL is genuinely 1800s (`TENNIS_AGENT_TTL` unset
anywhere, so the code default holds), no env override for CAP either (genuinely 3).

**Environment note, not a code finding:** this session's declared "working directory"
(`...\Swing Vision\master references`) is NOT the project root — it's an untracked
subfolder inside the real repo with unrelated generic content and its own empty
auto-created `.claude/agent-memory` stub (which is why my first memory-read attempt at
that path 404'd). The real, populated `.claude/` (hooks, journals, agent-memory with
actual history) is one level up at `...\Swing Vision\.claude\`. Used that as root
throughout. Worth a human checking whether this is a harness cwd bug or a deliberately
placed decoy folder — did not touch it beyond confirming it's inert.
```

---

## The doorman in one paragraph

Agents may call agents, so a cap kept only in prose cannot hold — the lead cannot see what
its children spawn, and a nested call spends the same shared account. A hook therefore
counts every agent in the tree with one lock file per live agent, written at
`SubagentStart` and removed at `SubagentStop` (never at `PostToolUse`, which returns
immediately for a background agent and would collapse the count to zero). `PreToolUse`
counts locks **plus reservations** and takes a reservation of its own at approval time, so
several dispatches emitted in one message cannot all walk past a read-only check. A
refused dispatch is **parked verbatim** rather than lost, keyed by a sha1 of its
`tool_input` so a normal re-dispatch un-parks its own twin, and handed back from the
`Stop` hook when a slot frees — at most three times, then dropped with a visible message.
A usage limit kills an agent outright so its lock leaks; a 1800 s TTL sweeps it and
`SessionStart` reports what is still held rather than clearing it, because another window
may genuinely be running agents. Everything fails **open**: bad JSON, empty stdin, no git
repo, no interpreter — step aside, because a broken guard that wedges every dispatch is
worse than no guard. Three live agents, project-wide, whole tree — because a one-word
agent costs ~38k tokens.
