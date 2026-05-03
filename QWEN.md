# QWEN.md

You are Qwen Code (an AI coding agent) working on this project. Follow these instructions strictly.

## Project: my-project

Stack: python
Framework: [TAUSIK](https://github.com/Kibertum/tausik-core) — AI agent governance implementing [SENAR v1.3](https://senar.tech)

## Hard Constraints (non-negotiable)

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

## Workflow

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

## Tool Routing — when to use which

Don't reach for `Grep`/`Glob` first. TAUSIK ships dedicated retrieval MCP servers; using them keeps context lean and surfaces project-specific knowledge that raw text search cannot.

| Need | Primary | Fallback |
|---|---|---|
| Find a function/symbol/usage in code | `mcp__codebase-rag__search_code` | `Grep` (only if RAG returns no hits or index is stale) |
| Recall a past project decision | `tausik_decisions_list` / `tausik_memory_search` (`type=convention/pattern`) | — |
| Cross-project pattern or gotcha | `mcp__tausik-brain__brain_search` | — |
| Web lookup (docs, API, errors) | `mcp__tausik-brain__brain_get` against the cached web result first | `WebFetch` (auto-cached on success) |
| Understand the project structure | `tausik_status` + `tausik_roadmap` | `Glob` for raw file listing |

Run `mcp__codebase-rag__rag_status` once per session to confirm the index is fresh. If `chunks=0`, run `mcp__codebase-rag__reindex` before any `search_code` call.

## Memory (two systems — use the right one)

| System | Where | When |
|---|---|---|
| **TAUSIK memory** (`memory add`) | `.tausik/tausik.db` | Patterns, dead ends, conventions specific to THIS project |
| **Agent auto-memory** | agent-specific (e.g. `~/.claude/...`) | User preferences, cross-project habits |

Memory types: `pattern`, `gotcha`, `convention`, `context`, `dead_end`.

Skills that need persistent data respect the `CLAUDE_PLUGIN_DATA` env var when set; otherwise fall back to `.tausik/plugin_data/`.

## SENAR Rules Compliance

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

## Commands Quick Reference

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

## Quality Gates

Gates run on three triggers:

- **`task-done`** — cheap-only (filesize, tdd_order). Closes a task in milliseconds.
- **`verify`** — heavy (pytest, tsc, cargo, phpstan, javac, js-test, terraform-validate, helm-lint, kubeval, hadolint, ansible-lint). Run via `.tausik/tausik verify --task <slug>`. Result cached for 10 min; `task done` reads the cache.
- **`commit`** — local lint (ruff, eslint, phpcs, golangci-lint).

Stack-specific gates auto-enable by detected stack. Filesize gate warns on files >400 lines.

Check status: `.tausik/tausik gates status`. Fix blocking failures before committing. Verify-First Contract opt-out: `.tausik/config.json` → `{ "task_done": { "auto_verify": true } }` runs the heavy gates inside `task done` instead of as a separate step.

## Skills

After bootstrap, **13 core skills** ship from `agents/skills/` and are always available: `/start`, `/end`, `/checkpoint`, `/plan`, `/task`, `/ship`, `/commit`, `/review`, `/test`, `/debug`, `/explore`, `/interview`, `/brain`.

**25+ official/vendor skills** install on demand via `tausik skill install <name>` from the `tausik-skills` repo or `skills-official/`: `/audit`, `/zero-defect`, `/markitdown`, `/excel`, `/pdf`, `/docs`, `/security`, `/onboard`, `/retro`, `/ultra`, `/jira`, `/bitrix24`, `/sentry`, ... See `.qwen/references/skill-catalog.md`.

When a user request matches a trigger keyword for a not-installed skill, proactively suggest installing it.

## Roles

Role field is free text. Common: `developer`, `architect`, `qa`, `tech-writer`, `ui-ux`.
Role profiles live in `.qwen/roles/<role>.md`.

## Are you a non-Claude agent? (GPT-5.5, Composer, Codex, OpenCode, Gemini …)

TAUSIK is model-agnostic, but the surface you actually use differs from Claude Code:

- **MCP tools first.** Every quality gate (QG-0, QG-2, session limit, dead-end tracking) is enforced inside the `tausik-project` MCP server. Calling MCP tools gives you the same hard guarantees Claude Code gets. Bash CLI is a fallback only when MCP is unreachable.
- **Slash commands may not exist.** If your host doesn't expand `/start`, `/plan`, `/ship`, `/end`, open the matching `agents/skills/<name>/SKILL.md` and execute its numbered steps. Skills are written as procedures, not host-specific magic.
- **PreToolUse hooks may not exist.** Cursor and a number of GPT-style agents have no hooks API: `task_gate.py` will not protect Rule 1 ("no code without a task"). Self-enforce — always call `tausik_task_start` (or `tausik_task_quick`) before any Edit/Write.
- **Don't write to `~/.claude/`.** It is a Claude-specific profile. Use the project DB (`.tausik/tausik.db`) via `tausik_memory_*` MCP tools, or the path under `CLAUDE_PLUGIN_DATA` if your host sets it.
- **Verify-First Contract is universal.** Run `tausik_verify` before `tausik_task_done_v2`, regardless of model. The 60s per-MCP-tool timeout that VS Code Claude Extension applies is the strictest case; if you keep heavy work inside `verify`, every other host stays in budget too.
- **`task_done_v2` over `task_done`.** When the MCP server publishes both, prefer `tausik_task_done_v2` — its structured JSON response (`stage`, `gate_results`, `blocking_failures`) is much friendlier to non-Claude tool-use loops that expect typed payloads.

## Response Language

Always respond in the user's language.


## IDE-specific overrides (qwen)

# Qwen Code Rules — TAUSIK Framework

## TAUSIK Integration
- Skills are in `.qwen/skills/` — invoked via `/skill-name`
- CLI: `.tausik/tausik <command>`
- Database: `.tausik/tausik.db` (SQLite, shared across IDEs if multiple installed)
- **MCP-first:** Prefer MCP tools (`tausik_*`) over CLI when available

## Workflow Discipline
- NEVER start coding without a task (`task start <slug>`)
- **QG-0 Context Gate:** Every task must have `goal` + `acceptance_criteria` before `task start`
- **QG-2 Implementation Gate:** Log AC evidence via `task log`, then `task done <slug> --ac-verified`
- Record architectural decisions with `decide` command
- Save useful patterns to project memory
- **Session limit: 180 min.** Use `/checkpoint` to save progress

## Quality Gates
- Quality gates run automatically on `task done` — fix blocking failures before proceeding
- Gates include: pytest, ruff, filesize, and stack-specific checks (tsc, eslint, go-vet, etc.)

## Key Commands
```bash
.tausik/tausik status
.tausik/tausik task list
.tausik/tausik task quick "Fix the bug"
.tausik/tausik task start <slug>
.tausik/tausik task done <slug> --ac-verified
.tausik/tausik task log <slug> "AC verified: ..."
.tausik/tausik memory add pattern "title" "content"
.tausik/tausik dead-end "approach" "reason"
```

<!-- DYNAMIC:START -->
<!-- DYNAMIC:END -->
