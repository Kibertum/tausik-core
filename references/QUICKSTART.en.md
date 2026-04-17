# TAUSIK — Quick Start for AI Agents

**English** | [Русский](QUICKSTART.md)

This guide is for an AI agent (Claude Code, Cursor, Qwen Code, Windsurf) connecting to a project with TAUSIK for the first time.
TAUSIK (**T**ask **A**gent **U**nified **S**upervision, **I**nspection & **K**nowledge) implements [SENAR v1.3 Core](https://senar.tech) ([spec](https://github.com/Kibertum/SENAR)).

See also: [AGENTS.md](../AGENTS.md) — onboarding overview and rules.
Full documentation for humans: [docs/](../docs/README.md)

## Prerequisites

**Python >= 3.11** must be available in PATH. Bootstrap will:
1. Find the best Python (venv > python3 > python > py -3 on Windows)
2. Create an isolated `.tausik/venv/` environment
3. Install dependencies (`mcp` and others) into the venv automatically
4. Configure MCP servers to use the venv Python

If Python is not found, bootstrap shows download instructions for each platform.

## Installation

```bash
git submodule add https://github.com/Kibertum/tausik-core .tausik-lib
python .tausik-lib/bootstrap/bootstrap.py --init
echo ".tausik/" >> .gitignore
```

> After bootstrap, **restart your IDE window** so MCP servers are loaded.

## Work Cycle (MCP-first)

Prefer MCP tools (`tausik_task_start`, `tausik_status`) over CLI bash.

### Quick Path

```
User: "start working"           → /start (session + context)
User: "fix the JWT bug"         → /plan (creates task + starts it)
User: "done"                    → /ship (review + gates + commit)
```

### Full Path

```
/start    → tausik_session_start, tausik_status, tausik_session_last_handoff
/plan     → tausik_task_quick or tausik_task_add + tausik_task_update (AC)
/task     → tausik_task_start (QG-0) → work → tausik_task_log → tausik_task_step
/task done → tausik_task_done (QG-2: ac_verified=true)
/review   → 28-item SENAR checklist
/commit   → git commit with gates
/end      → tausik_session_end + tausik_session_handoff
```

## Quality Gates

| Gate | When | What it checks |
|------|------|----------------|
| QG-0 | `tausik_task_start` | goal + AC are filled in |
| QG-2 | `tausik_task_done` | AC verified + gates (pytest, ruff) |

## Key MCP Tools

Full reference: [docs/en/mcp.md](../docs/en/mcp.md)

```
tausik_status              — project overview
tausik_task_quick          — quick task creation
tausik_task_start          — start task (QG-0)
tausik_task_done           — complete task (QG-2, ac_verified=true)
tausik_task_log            — log progress
tausik_dead_end            — document a failed approach
tausik_memory_search       — search project memory
tausik_explore_start/end   — exploration
tausik_metrics             — SENAR metrics
tausik_memory_block        — re-inject recent decisions/conventions/dead ends (v1.2)
tausik_memory_compact      — aggregate recent task_logs into patterns (v1.2)
```

## Anti-Drift Hooks (v1.2.0)

TAUSIK 1.2 adds real-time drift guards so you don't need to remember the framework:

- **SessionStart** auto-injects state (status + active tasks + Memory Block) into every new session
- **UserPromptSubmit** detects coding-intent in your prompts and nudges if no task is active
- **Stop keyword detector** catches "I'll implement" / "сейчас напишу" in agent output and blocks stop
- **PostToolUse verify-fix-loop** audits AC evidence after every `task_done` (5 rule-based checks)
- **`/interview`** runs a Socratic Q&A (≤3 questions) before complex tasks

See [docs/en/hooks.md](../docs/en/hooks.md) for the full hook table.

## What You Must Not Do

- Code without a task — use `/plan` → `/task`
- Close a task without AC evidence — use `tausik_task_log` + `ac_verified=true`
- Work >180 minutes without `/checkpoint`
- Commit without user confirmation
- Access the DB directly — use MCP or CLI only
