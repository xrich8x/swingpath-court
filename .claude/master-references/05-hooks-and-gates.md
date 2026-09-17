# 05 — Hooks and quality gates around a team

Hooks are the only way to enforce a rule on a teammate you are not watching.
They are also the cheapest: a shell script costs no tokens.

## The team-relevant events

| Event | Fires when | Exit 2 does | Matcher |
| --- | --- | --- | --- |
| `SubagentStart` | A subagent/teammate is spawned | Shows stderr to you only; it proceeds anyway | on `agent_type` |
| `SubagentStop` | A subagent finishes | **Blocks the stop** — it keeps working | on `agent_type` |
| `TeammateIdle` | A teammate is about to go idle | **Blocks idle** — it keeps working, with your feedback | none, always fires |
| `TaskCreated` | A task is being created | **Rolls back the creation** | none |
| `TaskCompleted` | A task is being marked complete | **Prevents completion** | none |
| `Stop` | Claude finishes responding | **Prevents stopping** | none |
| `PreToolUse` | Before a tool call | **Blocks the call** | on `tool_name` |
| `PostToolUse` | After a tool succeeds | stderr to Claude; cannot block | on `tool_name` |

Exit `0` = pass. Exit `2` = the blocking behaviour above, with stderr as the
feedback. Any other code = non-blocking error.

Blocking can also be expressed as JSON:
`hookSpecificOutput.permissionDecision: "deny"`.

## Payload fields you will actually use

Every payload carries `session_id`, `prompt_id`, `transcript_path`, `cwd`,
`permission_mode`, `hook_event_name`. On top of that:

```jsonc
// SubagentStart
{ "agent_id": "...", "agent_type": "security-reviewer", "reason": "why it was spawned" }

// SubagentStop
{ "agent_id": "...", "agent_type": "...", "last_assistant_message": "final text" }

// TeammateIdle
{ "agent_id": "...", "agent_type": "..." }

// TaskCreated
{ "agent_id": "...", "agent_type": "...", "task_input": { "title": "...", "description": "..." } }

// TaskCompleted
{ "agent_id": "...", "agent_type": "...", "task_id": "...", "task_input": { "title": "..." } }

// PreToolUse / PostToolUse
{ "agent_id": "...", "agent_type": "...", "tool_name": "Bash",
  "tool_input": {...}, "tool_use_id": "...", "tool_result": "..." }
```

`agent_id` / `agent_type` are present **only** when the event came from a
subagent or teammate — which is exactly how you write a rule that applies to
teammates but not to your own main-thread work.

## Configuration shape

```json
{
  "hooks": {
    "SubagentStart": [
      {
        "matcher": "Explore",
        "hooks": [
          { "type": "command", "command": "/path/to/log-agent-start.sh", "args": [] }
        ]
      }
    ],
    "TaskCompleted": [
      {
        "hooks": [
          { "type": "command", "command": "./.claude/hooks/task-done-gate.sh", "timeout": 30 }
        ]
      }
    ],
    "TeammateIdle": [
      {
        "hooks": [
          {
            "type": "prompt",
            "prompt": "Should the teammate continue working? Input: $ARGUMENTS",
            "model": "claude-opus-4-1-20250805"
          }
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "mcp__.*__.*",
        "hooks": [
          { "type": "command", "if": "mcp__memory__write.*",
            "command": "/path/to/validate-mcp-write.sh", "timeout": 30 }
        ]
      }
    ]
  }
}
```

Hook types: `command` (a script; `$ARGUMENTS` carries the payload) and `prompt`
/ `agent` (an LLM judge, as this repo's `Stop` gate uses). An LLM-judge hook
costs tokens on every fire — reserve it for the gate that genuinely needs
judgement and use scripts for everything checkable.

Hooks can also live in a subagent's own frontmatter (`hooks:` block), scoped to
that agent. Project-level subagent hooks need workspace trust accepted;
user-level (`~/.claude/agents/`) run without the trust check.

## Three gates worth having on any team

### 1. "Don't go idle with nothing delivered"

The core team failure: a teammate finishes and the lead learns only that it went
idle. `TeammateIdle` + exit 2 sends it back to work.

```bash
#!/bin/bash
# .claude/hooks/teammate-must-report.sh
payload=$(cat)
# ...check whatever evidence of delivery you require (task list state, a
# findings file, a marker the teammate was told to write)...
if [ ! -s "$CLAUDE_PROJECT_DIR/.claude/findings/$(jq -r .agent_id <<<"$payload").md" ]; then
  echo "You have not written your findings file yet. Write it, then message the lead." >&2
  exit 2
fi
exit 0
```

### 2. "A task is not complete until the check passes"

`TaskCompleted` + exit 2 is the enforcement point for a project gate — tests,
lint, a precision threshold. This is far stronger than asking nicely in the
prompt, because it fires on the teammate that tries to close the task.

### 3. "No task may be created outside the agreed scope"

`TaskCreated` + exit 2 rolls back scope creep at the moment it is written down,
which is much cheaper than discovering it in the diff.

## Interaction with the team's own rules

- `TeammateIdle` has **no matcher** — it fires for every teammate. Branch inside
  the script on `agent_type` if you want per-role rules.
- Blocking hooks can deadlock a team if the condition is unsatisfiable (a
  teammate that can never produce the artifact you demand will never go idle).
  Always give the hook an escape: a max-retry counter, or a condition the agent
  can actually meet.
- Hook feedback is the *only* channel that reaches a teammate you are not
  watching. Write the stderr message as an instruction, not a complaint.
