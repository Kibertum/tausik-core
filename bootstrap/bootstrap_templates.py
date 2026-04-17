"""Shared markdown templates for CLAUDE.md, AGENTS.md, .cursorrules, QWEN.md.

Hard constraints + workflow + SENAR rules are identical across IDEs; only the
file header and IDE subdir pointers differ. Centralizing them here prevents
drift between IDEs and makes edits single-source.
"""

from __future__ import annotations


HARD_CONSTRAINTS = """## Hard Constraints (non-negotiable)

Quality gates (`.tausik/tausik gates status`) enforce these automatically.

- **No code without a task.** Run `task start <slug>` before any Write/Edit. No exceptions. (SENAR Rule 9.1)
- **QG-0 Context Gate.** `task start` requires goal + acceptance_criteria with at least one negative scenario. Set both before starting.
- **QG-2 Implementation Gate.** `task done --ac-verified` requires evidence in task logs and passing quality gates (pytest, ruff/lint). Log AC verification via `task log` before closing.
- **No commit without gates.** Gates run automatically — fix blocking failures before committing.
- **No direct DB access.** Use MCP tools or CLI. Never raw SQLite.
- **Don't guess CLI arguments.** Run `.tausik/tausik <cmd> --help` or read the CLI reference.
- **MCP-first.** Prefer MCP tools (`tausik_*`) over CLI when equivalent.
- **Git: ask before commit/push.** Always request user confirmation.
- **Max 400 lines per file.** Filesize gate warns. Exceptions: tests, generated code.
- **Continuous logging.** Run `task log <slug> "message"` after every meaningful step. (SENAR Rule 9.4)
- **Document dead ends.** Run `.tausik/tausik dead-end "approach" "reason"` on failed approaches. (SENAR Rule 9.4)
- **Checkpoint every 30-50 tool calls.** Save context periodically. (SENAR Rule 9.3)
- **Session limit: 180 min.** `.tausik/tausik status` warns on overrun. Close the session before starting a new one. (SENAR Rule 9.2)
"""

WORKFLOW = """## Workflow

```
start → plan → task → [review | test] → commit → end
```

- `start` — load session state, active tasks, handoff from previous session
- `plan` — create task with complexity scoring + stack detection
- `task <slug>` — pick up or continue a task
- `review` — code review with parallel sub-agents (bugs, fake tests, drift)
- `test` — run or write tests
- `commit` — standardized commit with SENAR metadata
- `end` — close session with handoff for next agent

**Cost-aware model selection:** `tausik suggest-model <complexity>` prints a recommended Claude model (Haiku for simple 1 SP tasks, Sonnet for medium 3 SP, Opus for complex 8 SP). Claude Code doesn't switch models programmatically — apply the suggestion via `/fast` or settings.
"""

MEMORY = """## Memory (two systems — use the right one)

| System | Where | When |
|---|---|---|
| **TAUSIK memory** (`memory add`) | `.tausik/tausik.db` | Patterns, dead ends, conventions specific to THIS project |
| **Agent auto-memory** | agent-specific (e.g. `~/.claude/...`) | User preferences, cross-project habits |

Memory types: `pattern`, `gotcha`, `convention`, `context`, `dead_end`.

Skills that need persistent data respect the `CLAUDE_PLUGIN_DATA` env var when set; otherwise fall back to `.tausik/plugin_data/`.
"""

SENAR_RULES = """## SENAR Rules Compliance

TAUSIK enforces these rules. Violating them triggers warnings or hard blocks.

| Rule | Purpose | Enforcement |
|---|---|---|
| QG-0 Context Gate | Goal + AC + negative scenario before starting | Hard (blocks task_start) |
| QG-2 Implementation Gate | Evidence + AC verified + gates pass before done | Hard (blocks task_done) |
| Rule 1 Task before code | No Write/Edit without active task | Hard (PreToolUse hook) |
| Rule 2 Scope Boundaries | Declare scope + scope_exclude per task | Warning |
| Rule 3 Verify Against Criteria | Per-criterion evidence | Warning |
| Rule 7 Root Cause | Defect tasks require root cause | Warning |
| Rule 9.2 Session limit | 180 min per session | Hard (blocks task_start) |
| Rule 9.3 Checkpoint | Every 30-50 tool calls | Instruction |
| Rule 9.4 Dead Ends + Logging | Document failed approaches, log progress | Instruction |

Full rule set: [SENAR v1.3](https://senar.tech).
"""

COMMANDS = """## Commands Quick Reference

```bash
.tausik/tausik status                          # project overview + warnings
.tausik/tausik task list                       # list tasks
.tausik/tausik task start <slug>               # activate (QG-0 enforced)
.tausik/tausik task done <slug> --ac-verified  # complete (QG-2 enforced)
.tausik/tausik task log <slug> "message"       # log progress
.tausik/tausik dead-end "approach" "reason"    # document failure
.tausik/tausik metrics                         # SENAR metrics
.tausik/tausik search "<query>"                # FTS5 search
```
"""

QUALITY_GATES = """## Quality Gates

Gates auto-run on commits, task done, and explicit checks. Stack-specific lint/test gates auto-enable by detected stack. Filesize gate warns on files >400 lines.

Check status: `.tausik/tausik gates status`. Fix blocking failures before committing.
"""

RESPONSE_LANGUAGE = """## Response Language

Always respond in the user's language.
"""

DYNAMIC_BLOCK = """<!-- DYNAMIC:START -->
<!-- DYNAMIC:END -->
"""


def build_header(project_name: str, stacks: list[str], agent_name: str) -> str:
    """Header + project metadata. agent_name goes into the opening sentence."""
    stack_str = ", ".join(stacks) if stacks else "not detected"
    return (
        f"You are {agent_name} working on this project. Follow these instructions strictly.\n\n"
        f"## Project: {project_name}\n\n"
        f"Stack: {stack_str}\n"
        f"Framework: [TAUSIK](https://github.com/Kibertum/tausik-core) — AI agent governance implementing [SENAR v1.3](https://senar.tech)\n"
    )


def build_skills_section(ide_subdir: str) -> str:
    return (
        f"## External Skills\n\n"
        f"Skills managed via `skills.json`, auto-synced during bootstrap.\n"
        f"See `{ide_subdir}/references/skill-catalog.md` for the catalog with trigger keywords.\n"
        f"**When a user request matches a trigger keyword for a not-installed skill, proactively suggest installing it.**\n"
    )


def build_roles_section(ide_subdir: str) -> str:
    return (
        f"## Roles\n\n"
        f"Role field is free text. Common: `developer`, `architect`, `qa`, `tech-writer`, `ui-ux`.\n"
        f"Role profiles live in `{ide_subdir}/roles/<role>.md`.\n"
    )


def build_full_body(
    project_name: str,
    stacks: list[str],
    agent_name: str,
    ide_subdir: str,
) -> str:
    """Compose the full shared body used by all IDE-specific generators.

    Caller prepends its own file-level header (e.g. '# CLAUDE.md').
    """
    parts = [
        build_header(project_name, stacks, agent_name),
        HARD_CONSTRAINTS,
        WORKFLOW,
        MEMORY,
        SENAR_RULES,
        COMMANDS,
        QUALITY_GATES,
        build_skills_section(ide_subdir),
        build_roles_section(ide_subdir),
        RESPONSE_LANGUAGE,
        DYNAMIC_BLOCK,
    ]
    return "\n".join(parts)
