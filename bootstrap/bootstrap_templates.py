"""Shared markdown templates for CLAUDE.md, AGENTS.md, .cursorrules, QWEN.md.

Hard constraints + workflow + SENAR rules are identical across IDEs; only the
file header and IDE subdir pointers differ. Centralizing them here prevents
drift between IDEs and makes edits single-source.
"""

from __future__ import annotations

import os


HARD_CONSTRAINTS = """## Hard Constraints (non-negotiable)

Quality gates (`.tausik/tausik gates status`) enforce these automatically.

- **No code without a task.** Run `task start <slug>` before any Write/Edit. No exceptions. (SENAR Rule 9.1)
- **QG-0 Context Gate.** `task start` requires goal + acceptance_criteria with at least one negative scenario. Set both before starting.
- **QG-2 Implementation Gate (Verify-First v1.4).** Heavy gates (pytest, tsc, cargo, phpstan, …) live on a separate `verify` step. Sequence: run `tausik verify --task <slug>` once everything is in place — it caches a green; then `task done --ac-verified` looks the cache up and closes the task in milliseconds. If the cache is missing or stale → `task done` blocks with the explicit remediation command. Opt-out for CI: `.tausik/config.json` → `{ "task_done": { "auto_verify": true } }` (legacy inline behavior).
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
| QG-0 Context Gate | Goal + AC + negative scenario before starting | Hard (CLI/MCP — blocks `task_start`) |
| QG-2 Implementation Gate | Evidence + AC verified + fresh `tausik verify` green before done (Verify-First v1.4) | Hard (CLI/MCP — blocks `task_done`) |
| Rule 1 Task before code | No Write/Edit without active task | Hard (PreToolUse hook) in Claude Code, VS Code Claude Extension, Qwen Code; **Instruction-only in Cursor** (no hooks API) |
| Rule 2 Scope Boundaries | Declare scope + scope_exclude per task | Warning |
| Rule 3 Verify Against Criteria | Per-criterion evidence | Warning |
| Rule 7 Root Cause | Defect tasks require root cause | Warning |
| Rule 9.2 Session limit | 180 min per session | Hard (blocks `task_start`) |
| Rule 9.3 Checkpoint | Every 30-50 tool calls | Instruction |
| Rule 9.4 Dead Ends + Logging | Document failed approaches, log progress | Instruction |

> **Cursor caveat.** Cursor does not yet expose a PreToolUse hooks API equivalent to Claude Code's `.claude/settings.json`. TAUSIK's Cursor bootstrap therefore ships only `.cursorrules` + MCP servers — Rule 1 is enforced by the agent reading the rules, not by a process gate. Other quality gates (QG-0, QG-2, session limit) still run inside the `tausik-project` MCP server and remain Hard. If your team needs a process-level Rule 1 in Cursor, route writes through the `tausik_task_start` / `tausik_task_done_v2` MCP tools and treat raw file edits as non-conformant in code review.

Full rule set: [SENAR v1.3](https://senar.tech).
"""

COMMANDS = """## Commands Quick Reference

```bash
.tausik/tausik status                          # project overview + warnings
.tausik/tausik task list                       # list tasks
.tausik/tausik task start <slug>               # activate (QG-0 enforced)
.tausik/tausik verify --task <slug>            # heavy gates (pytest etc.) → cached green
.tausik/tausik task done <slug> --ac-verified  # complete (QG-2 enforced via verify cache)
.tausik/tausik task log <slug> "message"       # log progress
.tausik/tausik dead-end "approach" "reason"    # document failure
.tausik/tausik metrics                         # SENAR metrics
.tausik/tausik search "<query>"                # FTS5 search
```
"""

QUALITY_GATES = """## Quality Gates

Gates run on three triggers:

- **`task-done`** — cheap-only (filesize, tdd_order). Closes a task in milliseconds.
- **`verify`** — heavy (pytest, tsc, cargo, phpstan, javac, js-test, terraform-validate, helm-lint, kubeval, hadolint, ansible-lint). Run via `.tausik/tausik verify --task <slug>`. Result cached for 10 min; `task done` reads the cache.
- **`commit`** — local lint (ruff, eslint, phpcs, golangci-lint).

Stack-specific gates auto-enable by detected stack. Filesize gate warns on files >400 lines.

Check status: `.tausik/tausik gates status`. Fix blocking failures before committing. Verify-First Contract opt-out: `.tausik/config.json` → `{ "task_done": { "auto_verify": true } }` runs the heavy gates inside `task done` instead of as a separate step.
"""

TOOL_ROUTING = """## Tool Routing — when to use which

Don't reach for `Grep`/`Glob` first. TAUSIK ships dedicated retrieval MCP servers; using them keeps context lean and surfaces project-specific knowledge that raw text search cannot.

| Need | Primary | Fallback |
|---|---|---|
| Find a function/symbol/usage in code | `mcp__codebase-rag__search_code` | `Grep` (only if RAG returns no hits or index is stale) |
| Recall a past project decision | `tausik_decisions_list` / `tausik_memory_search` (`type=convention/pattern`) | — |
| Cross-project pattern or gotcha | `mcp__tausik-brain__brain_search` | — |
| Web lookup (docs, API, errors) | `mcp__tausik-brain__brain_get` against the cached web result first | `WebFetch` (auto-cached on success) |
| Understand the project structure | `tausik_status` + `tausik_roadmap` | `Glob` for raw file listing |

Run `mcp__codebase-rag__rag_status` once per session to confirm the index is fresh. If `chunks=0`, run `mcp__codebase-rag__reindex` before any `search_code` call.
"""

CURSOR_MCP_SETUP = """## Local MCP in Cursor (this workspace)

Bootstrap (`python bootstrap/bootstrap.py --ide cursor` or `--ide all`) generates:

- **`.cursor/mcp.json`** — TAUSIK MCP servers for Cursor (absolute paths to `.tausik/venv`, server entrypoints under **`.cursor/mcp/`**).
- **`.mcp.json` at repo root** — always points at **`.claude/mcp/`** (VS Code Claude Extension / shared); **Cursor reads `.cursor/mcp.json`** for project-scoped tools.

If tools do not appear: open **Cursor Settings → MCP**, ensure project MCP is enabled, then **Developer: Reload Window**.

Servers: `tausik-project`, `tausik-brain`, optional `codebase-rag`.

"""

MULTIMODEL_NOTE = """## Are you a non-Claude agent? (GPT-5.5, Composer, Codex, OpenCode, Gemini …)

TAUSIK is model-agnostic, but the surface you actually use differs from Claude Code:

- **MCP tools first.** Every quality gate (QG-0, QG-2, session limit, dead-end tracking) is enforced inside the `tausik-project` MCP server. Calling MCP tools gives you the same hard guarantees Claude Code gets. Bash CLI is a fallback only when MCP is unreachable.
- **Slash commands may not exist.** If your host doesn't expand `/start`, `/plan`, `/ship`, `/end`, open the matching `agents/skills/<name>/SKILL.md` and execute its numbered steps. Skills are written as procedures, not host-specific magic.
- **PreToolUse hooks may not exist.** Cursor and a number of GPT-style agents have no hooks API: `task_gate.py` will not protect Rule 1 ("no code without a task"). Self-enforce — always call `tausik_task_start` (or `tausik_task_quick`) before any Edit/Write.
- **Don't write to `~/.claude/`.** It is a Claude-specific profile. Use the project DB (`.tausik/tausik.db`) via `tausik_memory_*` MCP tools, or the path under `CLAUDE_PLUGIN_DATA` if your host sets it.
- **Verify-First Contract is universal.** Run `tausik_verify` before `tausik_task_done_v2`, regardless of model. The 60s per-MCP-tool timeout that VS Code Claude Extension applies is the strictest case; if you keep heavy work inside `verify`, every other host stays in budget too.
- **`task_done_v2` over `task_done`.** When the MCP server publishes both, prefer `tausik_task_done_v2` — its structured JSON response (`stage`, `gate_results`, `blocking_failures`) is much friendlier to non-Claude tool-use loops that expect typed payloads.
"""

RESPONSE_LANGUAGE = """## Response Language

Always respond in the user's language.
"""

DYNAMIC_BLOCK = """<!-- DYNAMIC:START -->
<!-- DYNAMIC:END -->
"""

MINIMAL_WORKFLOW = """## Workflow (minimal tier)

`/start` → `/plan` or `task start` → implement → `.tausik/tausik verify --task <slug>` →
`task done --ac-verified` → `/end`.

Full diagram: [Workflow](docs/en/workflow.md) (or `docs/ru/workflow.md`).
"""

MINIMAL_MEMORY = """## Memory (minimal)

- Project patterns / dead ends: TAUSIK `memory add` (SQLite `.tausik/tausik.db`).
- Host prefs: agent-specific auto-memory (`~/.claude/` is Claude-only — see glossary).
"""

MINIMAL_COMMANDS = """## Commands (minimal)

```bash
.tausik/tausik status
.tausik/tausik verify --task <slug>
.tausik/tausik task done <slug> --ac-verified
.tausik/tausik task log <slug> "…"
```

Full CLI: [docs/en/cli.md](docs/en/cli.md).
"""

MINIMAL_TIER_FOOTER = """## Rule pack size

This body was generated with **`context_tier: minimal`** (`.tausik/config.json`). Switch to
`standard` or `full` and re-run TAUSIK bootstrap / refresh for long-form tool routing, full
SENAR tables, and skill/role sections.
"""

FULL_TIER_NOTE = """## Deep onboarding (full tier)

Use this only when you routinely change gates, MCP tooling, or bootstrap templates. Read
[Architecture](docs/en/architecture.md) and [SENAR compliance matrix](docs/en/senar-compliance-matrix.md)
alongside this file.
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
        f"## Skills\n\n"
        f"After bootstrap, **13 core skills** ship from `agents/skills/` and are always available: "
        f"`/start`, `/end`, `/checkpoint`, `/plan`, `/task`, `/ship`, `/commit`, "
        f"`/review`, `/test`, `/debug`, `/explore`, `/interview`, `/brain`.\n\n"
        f"**25+ official/vendor skills** install on demand via "
        f"`tausik skill install <name>` from the `tausik-skills` repo or "
        f"`skills-official/`: `/audit`, `/zero-defect`, `/markitdown`, `/excel`, "
        f"`/pdf`, `/docs`, `/security`, `/onboard`, `/retro`, `/ultra`, `/jira`, "
        f"`/bitrix24`, `/sentry`, ... See `{ide_subdir}/references/skill-catalog.md`.\n\n"
        f"**Security — external skill repos are arbitrary code + instructions.** "
        f"Adding a repo clones remote content; installing may run pip/scripts. "
        f"Only use `tausik skill repo add <url>` for trusted sources; third-party URLs "
        f"require `--force` after review. See `docs/en/vendor-skills.md` and "
        f"`docs/en/skill-ecosystem.md`.\n\n"
        f"When a user request matches a trigger keyword for a not-installed skill, proactively suggest installing it.\n"
    )


def build_roles_section(ide_subdir: str) -> str:
    return (
        f"## Roles\n\n"
        f"Role field is free text. Common: `developer`, `architect`, `qa`, `tech-writer`, `ui-ux`.\n"
        f"Role profiles live in `{ide_subdir}/roles/<role>.md`.\n"
    )


def _load_ide_override(ide: str | None) -> str:
    """Load IDE-specific override block from agents/overrides/{ide}/rules.md.

    Returns "" if `ide` is None/unknown or the override file is missing.
    Wrapped so a missing file never breaks bootstrap.
    """
    if not ide:
        return ""
    here = os.path.dirname(os.path.abspath(__file__))
    candidate = os.path.normpath(
        os.path.join(here, "..", "agents", "overrides", ide, "rules.md")
    )
    if not os.path.isfile(candidate):
        return ""
    try:
        with open(candidate, encoding="utf-8") as f:
            body = f.read().strip()
        if not body:
            return ""
        return f"\n## IDE-specific overrides ({ide})\n\n{body}\n"
    except OSError:
        return ""


def build_full_body(
    project_name: str,
    stacks: list[str],
    agent_name: str,
    ide_subdir: str,
    ide: str | None = None,
    context_tier: str = "standard",
) -> str:
    """Compose the shared body used by all IDE-specific generators.

    Caller prepends its own file-level header (e.g. '# CLAUDE.md'). When
    `ide` is supplied, the matching `agents/overrides/<ide>/rules.md`
    block (if present) is appended right before the dynamic state block —
    closing the audit gap r14-overrides-integration where these files
    existed but were never wired into the generated CLAUDE.md/.cursorrules
    /QWEN.md.

    ``context_tier`` (from ``.tausik/config.json``) selects how verbose the
    generated rules are: ``minimal`` (short), ``standard`` (default), or
    ``full`` (standard + extra pointers for framework work).
    """
    tier = (context_tier or "standard").strip().lower()
    if tier not in ("minimal", "standard", "full"):
        tier = "standard"

    header = build_header(project_name, stacks, agent_name)
    if tier == "minimal":
        parts = [
            header,
            HARD_CONSTRAINTS,
            MINIMAL_WORKFLOW,
            MINIMAL_MEMORY,
            MINIMAL_COMMANDS,
            RESPONSE_LANGUAGE,
            MINIMAL_TIER_FOOTER,
            DYNAMIC_BLOCK,
        ]
        return "\n".join(p for p in parts if p)

    parts = [
        header,
        HARD_CONSTRAINTS,
        WORKFLOW,
        TOOL_ROUTING,
        MEMORY,
        SENAR_RULES,
        COMMANDS,
        QUALITY_GATES,
        build_skills_section(ide_subdir),
        build_roles_section(ide_subdir),
        MULTIMODEL_NOTE,
        RESPONSE_LANGUAGE,
        _load_ide_override(ide),
    ]
    if ide == "cursor":
        idx = parts.index(MULTIMODEL_NOTE)
        parts.insert(idx, CURSOR_MCP_SETUP)
    if tier == "full":
        parts.append(FULL_TIER_NOTE)
    parts.append(DYNAMIC_BLOCK)
    return "\n".join(p for p in parts if p)
