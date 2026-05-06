# AGENTS.md — AI Agent Onboarding

**You are an AI agent working on a project that uses TAUSIK.**
This document tells you what TAUSIK is, why it exists, and how to work with it.

## What is TAUSIK?

TAUSIK (**T**ask **A**gent **U**nified **S**upervision, **I**nspection & **K**nowledge) is an engineering governance framework for AI agents. It enforces a disciplined workflow so you don't skip planning, lose context between sessions, or close tasks without evidence.

TAUSIK implements [SENAR v1.3 Core](https://senar.tech) ([GitHub](https://github.com/Kibertum/SENAR)) — an open methodology for AI-native development. SENAR defines:
- **Quality gates** — hard blocks that prevent skipping steps (no code without a task, no completion without evidence)
- **Workflow rules** — task lifecycle, session management, checkpoints, dead end tracking
- **Metrics** — throughput, first-pass success rate, defect escape rate, lead time (all automatic)

**Why this matters to you:** Without TAUSIK, you might hallucinate completion, repeat failed approaches, or lose context. With TAUSIK, every piece of work has a goal, acceptance criteria, and verification evidence — making your output predictable and auditable.

## Your First 60 Seconds

1. **MCP-first** — use `tausik_*` tools (preferred). Full inventory + parameters live in **[docs/en/mcp.md](docs/en/mcp.md)**; for scripted hosts `tausik_status`/`status` accepts optional **compact JSON** (`compact` / `--compact`).
2. **CLI fallback** — `.tausik/tausik <cmd>` mirrors MCP; cheatsheet **[docs/en/cli.md](docs/en/cli.md)**.
3. **Skills / slash wrappers** — if `/start`, `/plan`, `/ship`, … are not expanded by your IDE, execute the numbered procedure inside `agents/skills/<name>/SKILL.md` (**[docs/en/skills.md](docs/en/skills.md)** lists triggers).

Hard workflow rules (`task_start` before edits, **`tausik_verify` before task closure**, `--ac-verified`) are unchanged — see § *The Rules* below.

## Are You a Non-Claude Model? Read This First

TAUSIK was originally built around Claude Code conventions, but the framework is model-agnostic. If you are GPT (5.5+), Cursor Composer, OpenCode, Codex CLI, Qwen Code, Gemini CLI or any other agent, the surface you actually use is different:

| Capability | Claude Code / VS Code Claude Extension | Cursor Composer / GPT-5.5 / OpenCode | Qwen Code |
|---|---|---|---|
| MCP tools (`tausik_*`) | Yes — preferred | **Yes — preferred and primary** | Yes — preferred |
| Slash skills (`/start`, `/plan`, `/ship`) | Native | **Not native** — read `agents/skills/<name>/SKILL.md` and follow the algorithm yourself | Read `.qwen/skills/<name>/SKILL.md` |
| PreToolUse hooks (`task_gate.py` etc.) | Yes (`.claude/settings.json`) | **No hooks API** — Rule 1 is enforced by you reading the rules | Yes (limited subset, see [r14-qwen-parity-or-honesty]) |
| `~/.claude/...` auto-memory | Read/write | **Do not write here** — it is a Claude-only profile dir | Read only |
| Session start | `session_start.py` hook injects status | **Run `tausik_status` and `tausik_session_start` yourself first** | hook (subset) |
| `/checkpoint` reminder | Hook nudges every 30-50 calls | **You** must self-checkpoint via `tausik_session_handoff` | hook (subset) |

### Model / host → tool surface (MCP)

Same governance everywhere; only the **wrapper** (hooks vs self-serve) changes. **Canonical counts** are asserted from `len(TOOLS)` in code — see **[docs/en/mcp.md](docs/en/mcp.md)** / **[docs/ru/mcp.md](docs/ru/mcp.md)**.

| Model / host | Primary TAUSIK surface | Main `tausik_*` tools (two servers) | Notes |
|----------------|------------------------|-------------------------------------|------|
| Claude (Code, VS Code Extension) | MCP `tausik-project` + `tausik-brain` | **99** (92 project + 7 brain) | Hooks + MCP |
| Cursor / Composer / GPT-5.5+ / OpenCode | Same MCP (project MCP config); CLI fallback `.tausik/tausik` | **99** (92+7) | Rule 1 self-serve if no hooks |
| Qwen Code | MCP + skills under `.qwen/skills/` | **99** (92+7) | Subset of hooks |
| Codex CLI / headless agents | Prefer MCP if exposed; else mirror CLI | **99** (92+7) | [docs/en/cli.md](docs/en/cli.md) |

**Optional `codebase-rag` server:** +7 tools → **106** total with the main two servers (not part of the 99 baseline). Same numbers as the header in [docs/en/mcp.md](docs/en/mcp.md).

**Operating contract for non-Claude models:**

1. **MCP-first, always.** Every workflow rule (QG-0, QG-2, session limits, dead-ends) is enforced inside the `tausik-project` MCP server — calling MCP tools gives you the same hard guarantees Claude Code gets. Bash CLI is a fallback only when MCP is unreachable.
2. **No slash commands → read the SKILL files.** If your host doesn't expand `/ship`, open `agents/skills/ship/SKILL.md` and execute its numbered steps. Skills are deliberately written as procedures, not as host-specific magic.
3. **Don't touch `~/.claude/`.** It's a Claude-specific profile. Use the project DB (`.tausik/tausik.db`) via `tausik_memory_*` MCP tools or the local file under `CLAUDE_PLUGIN_DATA` if it is set.
4. **Self-enforce Rule 1 in Cursor.** No PreToolUse hook means nothing prevents you from editing files outside an active task. Always start with `tausik_task_start` (or `tausik_task_quick` for the rapid path) before any Edit/Write.
5. **Verify-First Contract is universal.** Call `tausik_verify` before `tausik_task_done`, exactly like Claude Code does. The 60s per-MCP-tool timeout that VS Code Claude Extension applies is the strictest case; if you keep heavy work inside `verify`, every other host stays in budget too.
6. **`tausik_task_done` returns structured JSON.** v14b consolidated the prior `tausik_task_done_v2` alias back into the canonical `tausik_task_done` — the response is always the structured-JSON dict (`ok`, `gates`, `blocking_failures`, `cache_status`). Non-Claude tool-use loops parse it directly.

## The Rules You Must Follow

1. **No code without a task.** Always create a task (`tausik_task_quick` or `/plan`) before writing code.
2. **QG-0: Define before you start.** Every task needs a goal and acceptance criteria before `task start`. No exceptions.
3. **QG-2: Prove before you close.** Log AC verification evidence via `task log`, then `task done --ac-verified`. No shortcuts.
4. **Log your progress.** Use `tausik_task_log` after each significant step.
5. **Document dead ends.** Failed approach? `tausik_dead_end "what" "why"` — so the next session doesn't repeat it.
6. **Session limit: 180 minutes.** Use `/checkpoint` to save progress. Use `/end` to close properly.
7. **Ask before committing.** Never `git commit` or `git push` without user confirmation.
8. **MCP-first.** Prefer MCP tools over CLI bash commands.

## Testing discipline (agents) — HARD RULES

When you touch TAUSIK core (`scripts/`, `scripts/hooks/`, MCP handlers, gates), or write tests in any project that uses TAUSIK:

1. **Add or extend tests that align with files you changed** so scoped `pytest` on `task done` / `verify --task` stays meaningful.
2. Call **`tausik_verify`** before closure.
3. **Do not duplicate tests.** If a new test has the same structure as an existing one and only differs in inputs — **use `@pytest.mark.parametrize`**. Never add 5 tests where one parametrized test covers the same matrix. Run `python scripts/audit_pytest_dedupe.py` to check.
4. **Do not write tests on trivial getters / `assert callable(f)` / `hasattr(obj, 'attr')` / `assert x is not None` without behavior check** — these tests catch zero bugs and inflate suite time. If the only signal is "the import works", remove the test.
5. **Do not write mock-only tests** where 100% of meaningful calls are mocks and no real code path runs. The test must exercise the SUT.
6. **Do not write tests on implementation detail** (exact log strings, private method names, exact SQL syntax). Test behavior, not implementation.
7. **Security-sensitive paths** (hooks, auth, billing, payment) are **not** exempt — gates and verify-cache rules treat them **stricter**, not looser.

Details, anti-patterns, fake-test detector list: **[docs/en/testing-principles.md](docs/en/testing-principles.md)** · [RU](docs/ru/testing-principles.md).

## Work Cycle

Abbreviated spine: session open (`/start` ↔ `agents/skills/start/SKILL.md` + `tausik_session_*`) → plan (`/plan`, `task_quick`) → **`tausik_task_start` (QG-0)** → implement + `tausik_task_log`/`tausik_dead_end` → **`tausik_verify`** → **`tausik_task_done` (QG‑2)** → optional `/ship` → `/end`.

Canonical narrative + branching detail: **[docs/en/workflow.md](docs/en/workflow.md)** — keep that file authoritative; this header only orients newcomers.

## Documentation Map

| Need | Go to |
|------|-------|
| **Quick start for agents** | [docs/en/quickstart.md](docs/en/quickstart.md) (EN) / [docs/ru/quickstart.md](docs/ru/quickstart.md) (RU) |
| **CLI command reference** | [docs/en/cli.md](docs/en/cli.md) (EN) / [docs/ru/cli.md](docs/ru/cli.md) (RU) |
| **Architecture & internals** | [docs/en/architecture.md](docs/en/architecture.md) (EN) / [docs/ru/architecture.md](docs/ru/architecture.md) (RU) |
| **Testing principles (scoped pytest, when to add tests)** | [docs/en/testing-principles.md](docs/en/testing-principles.md) (EN) / [docs/ru/testing-principles.md](docs/ru/testing-principles.md) (RU) |
| **MCP tools (92 project + 7 brain = 99; verify-first contract)** | [docs/en/mcp.md](docs/en/mcp.md) |
| **Skills reference (12 core + brain conditional, 25+ official opt-in)** | [docs/en/skills.md](docs/en/skills.md) |
| **Quality gates** | [docs/en/hooks.md](docs/en/hooks.md) |
| **User-facing docs index** | [docs/README.md](docs/README.md) |
| **SENAR compliance matrix** | [docs/en/senar-compliance-matrix.md](docs/en/senar-compliance-matrix.md) |

## Repository Structure

```
scripts/           Core Python (CLI → Service → Backend)
docs/              Documentation (en/, ru/, research/)
agents/            Shared resources for all IDEs
  skills/          12 core skill definitions auto-deployed (+ /brain conditionally on Notion config) + 25+ official/vendor opt-in via --include-official
  roles/           5 role profiles (developer, architect, qa, tech-writer, ui-ux)
  stacks/          25 stack guides (python, react, go, rust, ansible, terraform, ...)
  overrides/       IDE-specific overrides (claude/, cursor/, qwen/)
  claude/mcp/      tausik-project (92) + tausik-brain (7) = 99 main; optional codebase-rag +7 → 106 total — see docs/en/mcp.md
bootstrap/         One-command project setup
tests/             pytest suite (2590 tests)
.tausik/           Runtime data (DB, config) — gitignored
```

## Key Entry Points (for framework contributors)

| What you want | Where to look |
|---------------|---------------|
| Run a CLI command | `scripts/project.py` → dispatches to handlers |
| Business logic | `scripts/project_service.py` + `scripts/service_task.py` |
| Database schema | `scripts/backend_schema.py` |
| Quality gates config | `scripts/project_config.py` |
| Gate runner | `scripts/gate_runner.py` |
| MCP server | `agents/claude/mcp/project/server.py` |
| Bootstrap logic | `bootstrap/bootstrap.py` |
| Add a skill | `agents/skills/<name>/SKILL.md` |

## How Things Connect

```
User message → Skill (SKILL.md) → MCP tool or CLI
                                 → project_service.py (business logic)
                                 → project_backend.py (SQLite + FTS5)
                                 → gate_runner.py (quality checks)
```

Three layers, strict separation: **CLI never touches DB. Service validates. Backend executes.**
