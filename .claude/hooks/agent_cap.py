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
