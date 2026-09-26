# AGENTS.md — AI Agent Onboarding

**You are an AI agent working on a project that uses TAUSIK.**
This document tells you what TAUSIK is, why it exists, and how to work with it.

## What is TAUSIK?

TAUSIK (**T**ask **A**gent **U**nified **S**upervision, **I**nspection & **K**nowledge) is an engineering governance framework for AI agents. It enforces a disciplined workflow so you don't skip planning, lose context between sessions, or close tasks without evidence.

TAUSIK implements [SENAR v1.5 Core](https://senar.tech) ([GitHub](https://github.com/Kibertum/SENAR)) — an open methodology for AI-native development. SENAR defines:
- **Quality gates** — hard blocks that prevent skipping steps (no code without a task, no completion without evidence)
- **Workflow rules** — task lifecycle, session management, checkpoints, dead end tracking
- **Metrics** — throughput, first-pass success rate, defect escape rate, lead time (all automatic)

**Why this matters to you:** Without TAUSIK, you might hallucinate completion, repeat failed approaches, or lose context. With TAUSIK, every piece of work has a goal, acceptance criteria, and verification evidence — making your output predictable and auditable.

## Your First 60 Seconds

0. **New here?** [docs/en/agent-quickstart.md](docs/en/agent-quickstart.md) ([RU](docs/ru/agent-quickstart.md)) is this page as a PROCEDURE: connect on your host, check, then the cycle as exact calls with the replies and refusals you will see.
1. **MCP-first** — use `tausik_*` tools (preferred). Full inventory + parameters live in **[docs/en/mcp.md](docs/en/mcp.md)**; for scripted hosts `tausik_status`/`status` accepts optional **compact JSON** (`compact` / `--compact`).
2. **CLI fallback** — `.tausik/tausik <cmd>` mirrors MCP; cheatsheet **[docs/en/cli.md](docs/en/cli.md)**.
3. **Skills / slash wrappers** — if `/start`, `/plan`, `/ship`, … are not expanded by your IDE, execute the numbered procedure inside `harness/skills/<name>/SKILL.md` (**[docs/en/skills.md](docs/en/skills.md)** lists triggers).

Hard workflow rules (`task_start` before edits, **`tausik_verify` before task closure**, `--ac-verified`) are unchanged — see § *The Rules* below.

## Are You a Non-Claude Model? Read This First

TAUSIK was originally built around Claude Code conventions, but the framework is model-agnostic. If you are GPT (5.5+), Cursor Composer, OpenCode, Codex CLI, Qwen Code, Gemini CLI or any other agent, the surface you actually use is different:

| Capability | Claude Code / VS Code Claude Extension | Cursor Composer / GPT-5.5 / OpenCode | Qwen Code | Codex CLI |
|---|---|---|---|---|
| MCP tools (`tausik_*`) | Yes — preferred | **Yes — preferred and primary** | Yes — preferred | Yes — `.codex/config.toml` (project); live-verified in 1.9 |
| Slash skills (`/start`, `/plan`, `/ship`) | Native | **Not native** — read `harness/skills/<name>/SKILL.md` and follow the algorithm yourself | Read `.qwen/skills/<name>/SKILL.md` | Skill catalog from `.codex/skills/<name>/SKILL.md`; sub-agents from `.codex/agents/*.toml` |
| PreToolUse hooks (`task_gate.py` etc.) | Yes (`.claude/settings.json`) | **No hooks API** — Rule 1 is enforced by you reading the rules | Yes (limited subset, see [r14-qwen-parity-or-honesty]) | Yes (`.codex/hooks.json`, same declaration as Claude) — **only after the user has trusted the project hooks**; untrusted = nothing enforced |
| `~/.claude/...` auto-memory | Read/write | **Do not write here** — it is a Claude-only profile dir | Read only | **Do not write here** |
| Session start | `session_start.py` hook injects status | **Run `tausik_status` and `tausik_session_start` yourself first** | hook (subset) | hook when trusted; otherwise run `tausik_status` and `tausik_session_start` yourself |
| `/checkpoint` reminder | Hook nudges every 30-50 calls | **You** must self-checkpoint via `tausik_session_handoff` | hook (subset) | hook when trusted; otherwise self-checkpoint |

### Model / host → tool surface (MCP)

Same governance everywhere; only the **wrapper** (hooks vs self-serve) changes. **Canonical counts** are asserted from `len(TOOLS)` in code — see **[docs/en/mcp.md](docs/en/mcp.md)** / **[docs/ru/mcp.md](docs/ru/mcp.md)**.

| Model / host | Primary TAUSIK surface | Main `tausik_*` tools | Notes |
|----------------|------------------------|-------------------------------------|------|
| Claude (Code, VS Code Extension) | MCP `tausik-project` | **147** | Hooks + MCP |
| Cursor / Composer / GPT-5.5+ / OpenCode | Same MCP (project MCP config); CLI fallback `.tausik/tausik` | **147** | Rule 1 self-serve if no hooks |
| Qwen Code | MCP + skills under `.qwen/skills/` | **147** | Subset of hooks |
| Codex CLI | MCP `tausik-project` from `.codex/config.toml`; skills `.codex/skills/`; agents `.codex/agents/` | **147** | Hooks via `.codex/hooks.json` once trusted — [enforcement matrix](docs/en/model-providers.md#codex-enforcement-matrix) |
| Headless agents | Mirror the CLI `.tausik/tausik` | **147** | [docs/en/cli.md](docs/en/cli.md) |

**Optional `codebase-rag` server:** +7 tools → **154** total with the main server (not part of the baseline). Same numbers as the header in [docs/en/mcp.md](docs/en/mcp.md).

**Operating contract for non-Claude models:**

1. **MCP-first, always.** Every workflow rule (QG-0, QG-2, session limits, dead-ends) is enforced inside the `tausik-project` MCP server — calling MCP tools gives you the same hard guarantees Claude Code gets. Bash CLI is a fallback only when MCP is unreachable.
2. **No slash commands → read the SKILL files.** If your host doesn't expand `/ship`, open `harness/skills/ship/SKILL.md` and execute its numbered steps. Skills are deliberately written as procedures, not as host-specific magic.
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

Abbreviated spine: session open (`/start` ↔ `harness/skills/start/SKILL.md` + `tausik_session_*`) → plan (`/plan`, `task_quick`) → **`tausik_task_start` (QG-0)** → implement + `tausik_task_log`/`tausik_dead_end` → **`tausik_verify`** → **`tausik_task_done` (QG‑2)** → optional `/ship` → `/end`.

Canonical narrative + branching detail: **[docs/en/workflow.md](docs/en/workflow.md)** — keep that file authoritative; this header only orients newcomers.

## Documentation Map

| Need | Go to |
|------|-------|
| **Quick start for agents** | [docs/en/agent-quickstart.md](docs/en/agent-quickstart.md) (EN) / [docs/ru/agent-quickstart.md](docs/ru/agent-quickstart.md) (RU) — exact calls, replies and refusals |
| **Quick start for people** | [docs/en/quickstart.md](docs/en/quickstart.md) (EN) / [docs/ru/quickstart.md](docs/ru/quickstart.md) (RU) |
| **CLI command reference** | [docs/en/cli.md](docs/en/cli.md) (EN) / [docs/ru/cli.md](docs/ru/cli.md) (RU) |
| **Architecture & internals** | [docs/en/architecture.md](docs/en/architecture.md) (EN) / [docs/ru/architecture.md](docs/ru/architecture.md) (RU) |
| **Testing principles (scoped pytest, when to add tests)** | [docs/en/testing-principles.md](docs/en/testing-principles.md) (EN) / [docs/ru/testing-principles.md](docs/ru/testing-principles.md) (RU) |
| **MCP tools (146; verify-first contract)** | [docs/en/mcp.md](docs/en/mcp.md) |
| **Skills reference (13 core skills, 20 official skills opt-in)** | [docs/en/skills.md](docs/en/skills.md) |
| **Quality gates** | [docs/en/hooks.md](docs/en/hooks.md) |
| **User-facing docs index** | [docs/README.md](docs/README.md) |
| **SENAR compliance matrix** | [docs/en/senar-compliance-matrix.md](docs/en/senar-compliance-matrix.md) |

## Repository Structure

```
scripts/           Core Python (CLI → Service → Backend)
docs/              Documentation (en/, ru/, research/)
harness/           Shared resources for all IDEs (renamed from agents/ in v1.4 to avoid collision with .claude/agents/)
  skills/          13 core skills auto-deployed + 20 official skills opt-in via --include-official
  roles/           6 roles (developer, architect, devops, qa, tech-writer, ui-ux)
  stacks/          25 stack guides (python, react, go, rust, ansible, terraform, ...)
  overrides/       IDE-specific overrides (claude/, cursor/, qwen/)
  claude/mcp/      tausik-project (147) main; optional codebase-rag +7 -> 154 total — see docs/en/mcp.md
bootstrap/         One-command project setup
tests/             pytest suite (3355 tests)
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
| MCP server | `harness/claude/mcp/project/server.py` |
| Bootstrap logic | `bootstrap/bootstrap.py` |
| Add a skill | `harness/skills/<name>/SKILL.md` |

## How Things Connect

```
User message → Skill (SKILL.md) → MCP tool or CLI
                                 → project_service.py (business logic)
                                 → project_backend.py (SQLite + FTS5)
                                 → gate_runner.py (quality checks)
```

Three layers, strict separation: **CLI never touches DB. Service validates. Backend executes.**

<!-- DYNAMIC:START -->
## Current State
Session: #277 (active) | Branch: v1-10 | TAUSIK: 1.9.0
Tasks: 1609/1718 done, 3 obsolete, 1 active, 0 blocked
Active: closure-citations-rot-is-detected-but-never-acted-on
Full history (grep it for what a compaction dropped): ~\.claude\projects\d--Work-Kibertum-clients-kibertum-tausik-core\117ec53f-dbde-45ea-93f1-eb22c72335fd.jsonl

### Memory tail
Context (5):
- #746 Расход токенов TAUSIK почти целиком в cache_read: 99,5% входа, и главный рычаг — число ходов
- #726 Дополнение к #725: история I release110-open-defects — эпик #192 с 22 sub-issue (все открытые kind/b
- #725 GitHub-карта, дополнение смены #266: эпик H #188 (сайт, документация, гигиена; 16 sub-issue, новые #
- #723 GitHub-карта после перепланирования 1.10 (смена #266): milestone v1.10.0 = 7 эпиков, v1.11.0 кандида
- #722 Замер сессий #196–#265 (смена #266): ни одна из 70 смен не достигла 180 активных минут; агентов оста
Decisions (5):
- #397 1.10 ДОПОЛНЕН ИСТОРИЕЙ generated-code-is-lean-and-ascii. Указание владельца, смена #277: проекты на старых TAUSIK объявл
- #396 1.10 ДОПОЛНЕН ИСТОРИЕЙ harness-costs-less-per-task. Указание владельца, смена #275: внедрить лучшие практики из разбора 
- #395 Разделение обязанностей L3 проверяется при ЗАПИСИ: review record --type L3 требует модели ревьюера и автора и отказывает
- #394 tools/list отдаёт ttlMs=0 и cacheScope=private, скрытие по scope_tools сохраняется (github#91)
- #393 Пользовательский тир с 1.10 — ~/.config/tausik/config.json. Старый ~/.tausik/config.json читается, только если он единст
Conventions (5):
- #745 Имя латиницей, проза на любом языке; исключение объявляется замером цены, а не вкусом
- #742 Generated trees are declared once in scripts/derived_trees.py; exporters and checks read it
- #738 Ответ владельцу: итог первой строкой, дальше только факты списком; без пересказа процесса
- #728 Не объявлять CHANGELOG и общие страницы docs в --relevant-files задачи: следующая запись в CHANGELOG
- #717 GitHub roadmap — как в Harvester: milestone vX.Y.Z, [KIND]-заголовки, kind/area/priority, [EPIC] с s
Dead ends (3):
- #749 Крупный ответ инструмента писать в файл и возвращать путь с хвостом
- #748 Вынести динамический блок из CLAUDE.md в отдельный файл, чтобы инструкции попали в кэшируемый префик
- #693 Verify review journal with tracked output documents as relevant files
<!-- DYNAMIC:END -->
