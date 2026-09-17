# Master References — Agent Teams

A working reference for designing, launching and running **agent teams** and
**subagents** in Claude Code. Written to be read by a future session (human or
Claude) that is about to build a team and wants to get it right the first time.

Source: `https://code.claude.com/docs/en/agent-teams` and its linked pages
(`sub-agents`, `hooks`, `tools-reference`, `costs`, `cross-session-messaging`),
fetched **2026-08-28**. Agent teams are an **experimental** feature and the docs
carry per-version behaviour notes — re-check the live page before relying on a
version-gated detail. Version numbers quoted below are the ones the docs give.

## Read order

| If you are… | Read |
| --- | --- |
| Reading the whole of **our** setup — doorman, cap, team prompts — in one place | `00-THE-FULL-SETUP.md` |
| Just the **team** — roles, prompts, dispatch, journals, no cap | `00A-TEAM-ONLY.md` |
| Just the **doorman** — cap, parking, wiring, both source files, the verification report | `00B-DOORMAN-ONLY.md` |
| Deciding *whether* to use a team at all | `01-choosing-the-mechanism.md` |
| Turning teams on / running one for the first time | `02-agent-teams-reference.md` |
| Writing a reusable teammate role (`.claude/agents/*.md`) | `03-subagent-definitions.md` |
| Copying a known-good team shape | `04-team-recipes.md` |
| Adding automated quality gates around a team | `05-hooks-and-gates.md` |
| Worried about token burn | `06-cost-and-scaling.md` |
| Something went wrong | `07-failure-modes.md` |
| Working in **this** repo (SwingVision) | `08-swingvision-rules.md` — **read before spawning anything here** |
| About to press go | `09-preflight-checklist.md` |
| Rebuilding this whole setup in **another** project | `10-rebuilding-this-elsewhere.md` |

## The one-paragraph version

A team is one **lead** session plus N independent Claude Code sessions
(**teammates**), each with its own context window, coordinating through a
**shared task list** and a **mailbox**. Teammates do not inherit the lead's
conversation — only CLAUDE.md, MCP servers, skills and the spawn prompt. Teams
cost roughly linearly in the number of teammates (the docs quote **~7x** a
single session for a plan-mode team), so they pay off only when the work
genuinely splits into independent lanes that benefit from parallel exploration
or adversarial debate. Everything else — focused delegation where only the
result matters — is a **subagent**, which is cheaper and returns its output to
the caller instead of just an idle notification.
