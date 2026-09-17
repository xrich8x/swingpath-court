# 03 — Writing agent definitions (the reusable role)

A teammate is only as good as the definition behind it. A definition written
once in `.claude/agents/` is reusable **both** as a delegated subagent and as a
team teammate — this is the highest-leverage artifact in multi-agent work.

## Scopes and precedence

| Location | Scope | Priority |
| --- | --- | --- |
| Managed settings | Organization-wide | 1 (highest) |
| `--agents` CLI flag (JSON) | Current session | 2 |
| `.claude/agents/` | Current project | 3 |
| `~/.claude/agents/` | All projects | 4 |
| Plugin's `agents/` | Where the plugin is enabled | 5 (lowest) |

**Check project agents into version control.**

## Complete frontmatter reference

```yaml
---
name: unique-id                    # required: lowercase + hyphens, no colons
description: When to use this      # required: this is what Claude reads to decide to delegate

# Model & performance
model: sonnet|opus|haiku|fable|inherit|claude-opus-5   # default: inherit
effort: low|medium|high|xhigh|max                      # overrides session effort

# Tool access
tools: Read, Grep, Glob, Bash      # allowlist
disallowedTools: Write, Edit       # denylist — takes precedence over tools

# Permissions & isolation
permissionMode: default|acceptEdits|auto|dontAsk|bypassPermissions|plan
isolation: worktree                # run in a separate git worktree
background: true|false             # keep in background even when Claude wants foreground

# Knowledge & context
skills:                            # preload full skill content at startup
  - api-conventions
memory: user|project|local         # persistent memory scope

# MCP
mcpServers:
  - server-name
  - playwright:
      type: stdio
      command: npx
      args: ["-y", "@playwright/mcp@latest"]

# Lifecycle
hooks:
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "./scripts/validate.sh"
maxTurns: 10

initialPrompt: Auto-submitted text  # first user turn when the agent is the main session
color: red|blue|green|yellow|purple|orange|pink|cyan
---

The Markdown body becomes the system prompt.
```

### The team caveat, again

When a definition runs **as a teammate**, `skills` and `mcpServers` are
**ignored**. If a role depends on preloaded skill content, that content must be
in the body, in CLAUDE.md, or in the spawn prompt — not in `skills:`.

## Tool resolution

- Neither `tools` nor `disallowedTools`: inherits every tool available to
  subagents.
- `tools` only: exactly those tools.
- `disallowedTools` only: every parent tool except those.
- Both: `disallowedTools` wins for anything in both lists.

Patterns worth knowing:

```yaml
tools: Agent(worker, researcher), Read, Bash   # may only spawn those two agent types
disallowedTools: mcp__github                   # drop one MCP server's tools
disallowedTools: mcp__*                        # drop all MCP tools
```

**Always removed from subagents:** `AskUserQuestion`, `EndConversation`,
`EnterPlanMode`/`ExitPlanMode` (unless `permissionMode: plan`), `ScheduleWakeup`,
`TaskOutput`, `WaitForMcpServers`, `Workflow`, and `Agent` at the depth limit.

**Background subagents keep a reduced set:** `Read`, `Grep`, `Glob`, `Bash`,
`PowerShell`, `Edit`, `Write`, `NotebookEdit`, `WebFetch`, `WebSearch`,
`TodoWrite`, `Skill`, `ToolSearch`, `EnterWorktree`, `ExitWorktree`, `Monitor`,
`TaskStop`, `SendMessage`, `Artifact`, plus all MCP tools. Foreground subagents
and forks get the full parent pool.

## What loads at a teammate/subagent's startup

1. Its own system prompt (definition body + environment details — **not** the
   full Claude Code prompt)
2. The task message / spawn prompt
3. **CLAUDE.md hierarchy** (Explore and Plan skip this)
4. Git status snapshot from the parent session's start (Explore and Plan skip)
5. Preloaded `skills` content — **subagents only, not teammates**
6. Sibling roster of named agents as valid `SendMessage` targets (v2.1.206+)

**Not included:** the lead's conversation history, previously invoked skills,
files already read, output style, auto memory, or the parent's context size.

> This is the single most common cause of a useless teammate: it does not know
> what you and the lead spent an hour establishing. Put it in the spawn prompt.

## Persistent agent memory

```yaml
memory: project
```

| Scope | Location |
| --- | --- |
| `user` | `~/.claude/agent-memory/<name>/` |
| `project` | `.claude/agent-memory/<name>/` (check in) |
| `local` | `.claude/agent-memory-local/<name>/` (do not check in) |

The first 200 lines / 25KB of that directory's `MEMORY.md` is injected into the
system prompt. The agent should maintain it proactively — say so in the body, or
it will not.

## Built-in agent types

| Agent | Model | Tools | Purpose |
| --- | --- | --- | --- |
| `Explore` | inherited (capped at Opus on Claude API) | read-only | Fast codebase search; skips CLAUDE.md and git status |
| `Plan` | inherited | read-only | Research for plan mode; skips CLAUDE.md and git status |
| `general-purpose` | inherited | all subagent tools | Multi-step explore-and-act |
| `claude` | inherited | all subagent tools | Catch-all fallback |
| `statusline-setup` | Sonnet | — | `/statusline` config |
| `claude-code-guide` | Haiku | — | Questions about Claude Code |

## Invoking

```text
Use the code-reviewer subagent to suggest improvements
@"code-reviewer (agent)" review the auth changes      # guaranteed delegation
@agent-my-plugin:code-reviewer check this file
```

```bash
claude --agent code-reviewer          # session-wide default
```

```bash
claude --agents '{
  "code-reviewer": {
    "description": "Expert code reviewer",
    "prompt": "You are a senior code reviewer...",
    "tools": ["Read", "Grep", "Glob", "Bash"],
    "model": "sonnet"
  }
}'
```

## Nesting and concurrency

- Spawn depth: default **3 layers** below main
  (`CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH`).
- Concurrent subagents: default **20** before a spawn fails
  (`CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS`).
- **Teammates cannot nest at all.**

## Forks vs normal subagents

| | Fork | Non-fork subagent |
| --- | --- | --- |
| Context | Full parent conversation | Fresh only |
| System prompt | Parent's | Its own |
| Tools | Parent's, full | Filtered by definition |
| Model | Parent's | Its own `model` |
| Permissions | Prompts in terminal | Prompts in main session |
| Cache | Shared with parent | Separate |

`/subtask <task>` creates one. Fork mode defaults ON in interactive sessions;
`CLAUDE_CODE_FORK_SUBAGENT=0|1` overrides. To keep fork mode but stop Claude
spawning forks: `{"permissions": {"deny": ["Agent(fork)"]}}`.

## Resuming

Non-fork subagents (except Explore and Plan) can be resumed. A `SendMessage` to a
completed subagent auto-resumes it with full history. Transcripts live at
`~/.claude/projects/{project}/{sessionId}/subagents/agent-{agentId}.jsonl`.

## Definition-writing rules that actually matter

1. **One job per agent.** A definition that does "review and fix and document"
   does all three badly.
2. **The `description` is a routing decision, not a title.** Claude reads it to
   choose. Write when to use it *and* when not to — the repo's `qa-verifier`
   does this well: *"Never used to write or fix code."*
3. **Restrict tools deliberately.** A verifier with `Write` will fix what it
   finds and destroy its own independence. A researcher with `Bash` will start
   running experiments instead of reporting.
4. **State the anti-goals in the body.** "You never edit code, and you never
   adjust a test or gate to make something pass" is worth more than three
   paragraphs of role description.
5. **Put the acceptance criteria in the body**, not in the prompt you type each
   time — that is what makes the role reusable.
6. **Assume zero shared history.** Write the body so the agent is competent from
   a cold start.
7. **Ask for the uncertainty.** "Say what is borderline even if it technically
   passes" gets you far more than a PASS/FAIL bit.

## Template

```markdown
---
name: <role-slug>
description: <what it does, when to use it, and explicitly when NOT to>
tools: <smallest set that can do the job>
model: <opus for judgement, sonnet for volume, haiku for mechanical>
memory: project
---

You are <role> for <system>. <One line of context they cannot infer.>

When invoked:
1. <first concrete action — usually "read X to establish what was supposed to happen">
2. <the core work>
3. <how to verify it yourself rather than trusting a claim>

Report:
- <the exact shape of output the caller needs>
- <what to flag as uncertain>

You never <the anti-goal that would corrupt this role>.
Consult your agent memory before starting; update it when you finish.
```
