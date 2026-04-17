# Changelog

All notable changes to this project will be documented in this file.

This project adheres to [Semantic Versioning](https://semver.org/).

## [1.2.0] — 2026-04-17

### Claude-Hardening Epic — anti-drift infrastructure

Inspired by [oh-my-claudecode](https://github.com/Yeachan-Heo/oh-my-claudecode) (staged pipelines, Ralph mode, keyword-detector), [prompt-master](https://github.com/nidhinjs/prompt-master) (load-bearing text, Memory Block, 9 dimensions of intent), and the leaked Claude Code architecture analysis on Habr (KAIROS always-on assistant, Dream System memory consolidation). Addresses the real-world problem that agents "drift" — ignore the framework, skip task creation, forget conventions between sessions. 18 tasks shipped across 4 stories (P0/P1/P2/P3).

### Added / Добавлено

- **Load-bearing CLAUDE.md / AGENTS.md / .cursorrules / QWEN.md templates** — generated IDE instructions went from ~30 lines to ~104 lines each, with 13 hard constraints, workflow graph, memory types table, SENAR rules reference, DYNAMIC block. All four IDE files share a single source of truth in `bootstrap/bootstrap_templates.py` (no more drift between IDEs) — Единый источник CLAUDE/AGENTS/cursorrules/QWEN
- **SessionStart hook** (`scripts/hooks/session_start.py`) — auto-injects TAUSIK state (status, active tasks, blocked tasks, Memory Block) into every new Claude Code / Qwen Code session; no manual `/start` needed — SessionStart хук с автоинъекцией состояния
- **UserPromptSubmit hook** (`scripts/hooks/user_prompt_submit.py`) — detects coding-intent keywords in user prompts (EN+RU) and nudges the agent to check for an active task before writing code — Детектор coding-intent с напоминанием
- **Stop hooks** — `scripts/hooks/keyword_detector.py` (drift-announcement detection in agent's last message — blocks stop if "I'll implement" without active task) and `scripts/hooks/session_cleanup_check.py` (warns about open exploration, review-tasks, session timeout) — Два Stop hook'а: keyword detector и session hygiene
- **PostToolUse verify-fix-loop hook** (`scripts/hooks/task_done_verify.py`) — after every successful `task_done`, 5 rule-based heuristics audit the AC evidence (file paths, ✓ markers, test counts, file refs, lint status); 2+ failures trigger a `/review` recommendation — Rule-based Ralph-mode-lite
- **Memory Block re-injection** — new `memory_block()` method + `tausik memory block` CLI + `tausik_memory_block` MCP tool returning compact markdown (recent decisions + conventions + dead ends, ≤50 lines) consumed by `/start`, `/checkpoint`, SessionStart hook — Повторная инъекция проектной памяти для anti-drift
- **`tausik memory compact`** CLI + `tausik_memory_compact` MCP — Dream-System-inspired aggregation of recent `task_logs` into phases / top opening words / top files mentioned — Консолидация логов в паттерны
- **QG-0 9-dimension intent completeness** — `qg0_dimensions_score()` in `service_gates.py` scores every task against {goal, acceptance_criteria, scope, scope_exclude, role, stack, complexity, story_link, evidence_plan}; <5 dims triggers a "CONTEXT" warning (prompt-master principle) — QG-0 расширен до 9 измерений
- **Adversarial critic in `/review`** — new sixth parallel review agent `agents/skills/review/agents/critic.md` hunting for exactly 3 weaknesses the other 5 agents miss (hidden failure modes, silent contract drift, assumption gaps); opt-in "deep mode" runs two critic passes — Adversarial критик в /review
- **`/interview` skill** — Socratic Q&A before complex tasks (max 3 clarifying questions, prompt-master principle) — Сократический Q&A скилл
- **`tausik hud`** CLI — one-screen live dashboard (session + active task + recent logs + gates) inspired by oh-my-claudecode HUD — Live HUD
- **`tausik suggest-model`** CLI + `scripts/model_routing.py` — model recommendation by complexity tier (simple→Haiku 4.5, medium→Sonnet 4.6, complex→Opus 4.7) for manual application via `/fast` — Cost-aware model routing
- **Webhook notifications** (`scripts/notifier.py` + `scripts/hooks/notify_on_done.py`) — Slack / Discord / Telegram webhooks fired on `task_done`; configured via `TAUSIK_SLACK_WEBHOOK` / `TAUSIK_DISCORD_WEBHOOK` / `TAUSIK_TELEGRAM_WEBHOOK` env vars — Webhook-уведомления в 3 канала
- **`CLAUDE_PLUGIN_DATA` env support** — `scripts/plugin_data.py` respects Claude Code's plugin-data convention for skill persistent state; falls back to `.tausik/plugin_data/` — Поддержка CLAUDE_PLUGIN_DATA
- **Mandatory Gotchas section lint** — `tests/test_skills_have_gotchas.py` enforces every SKILL.md has a "## Gotchas" section with real content (Habr recommendation) — Обязательная секция Gotchas
- **No-boilerplate lint** — `tests/test_skills_no_boilerplate.py` blocks re-introduction of "Always respond in user's language" in SKILLs (already covered by CLAUDE.md) — Лин для boilerplate

### Changed / Изменено

- **Bootstrap no longer copies `lib/AGENTS.md`** (which was dogfooding-specific, referenced `scripts/`/`agents/` structure); `generate_agents_md()` now produces a universal AGENTS.md with shared hard constraints — AGENTS.md теперь генерируется, не копируется из lib
- **Skills cleanup** — 12 SKILL.md files had "Always respond in the user's language" boilerplate removed (duplicate of CLAUDE.md Response Language section) — Чистка boilerplate в 12 skill-файлах
- **Shared hook helpers** — `scripts/hooks/_common.py` extracts `tausik_path()`, `has_active_task()`, `is_task_done_invocation()`, `extract_task_done_slug_from_bash()` previously duplicated across 5 hooks (convention #2: Mixin composition) — Рефакторинг общих helper-ов hooks
- **`bootstrap/bootstrap_venv.py`** gets `install_cli_wrapper()` helper (extracted from bootstrap.py to stay under 400-line gate) — CLI wrapper install вынесен
- **Skills count:** 34 → 35 (added `/interview`) — 35 скиллов
- **MCP tools:** 80 → 82 (added `tausik_memory_block`, `tausik_memory_compact`) — 82 MCP инструмента

### Fixed / Исправлено

- **H1 — Bash `"task done"` false-positive** — PostToolUse hooks (`notify_on_done`, `task_done_verify`) used substring match that triggered on `echo "task done today"`, `git log --grep="task done"`, etc. Replaced with a proper regex anchored to the actual `tausik[.cmd] task done <slug>` CLI shape in `_common.py`
- **H2 — `_check_ac_checkmarks` matched too loosely** — `"complete"` substring fired on `incomplete`/`completion`/`completeness`, and the heuristic ran on the full `task show` output (title + goal) rather than notes. Fixed with word-boundary regex `[✓✔]|\b(passed|verified|ok|complete[d]?)\b` plus `_extract_notes_section()`

### Test Coverage / Тесты

- **+177 new tests** — 918 → 1095 passing. Every new module (hooks, templates, routing, aggregates) ships with its own test file.

## [1.1.0] — 2026-04-12

### DX & Adoption Improvements

Inspired by ideas from [Molyanov AI Dev Framework](https://github.com/pavel-molyanov/molyanov-ai-dev) — two-phase planning, TDD enforcement, skill auto-testing. Community request for Qwen Code support ([#1](https://github.com/Kibertum/tausik-core/issues/1)).

### Added / Добавлено

- **Qwen Code (GigaCode) support** — full IDE integration: `.qwen/` directory, `QWEN.md` rules file, MCP config + SENAR hooks in `.qwen/settings.json`, 80 MCP tools + 4 enforcement hooks (task gate, bash firewall, push gate, auto-format) ([#1](https://github.com/Kibertum/tausik-core/issues/1)) — Полная поддержка Qwen Code CLI с хуками
- **TDD enforcement gate** — optional `tdd_order` quality gate verifies test files are modified alongside source code; disabled by default, enable via config — Опциональный gate для TDD-контроля
- **Two-phase planning** — `/plan` now starts with an interview phase (3+ clarifying questions) before decomposition; skip with `--skip-interview` — Двухфазное планирование с интервью
- **Auto-docs update on /ship** — after commit, `/ship` checks for structural changes and suggests updating `references/` documentation — Автообновление документации при /ship
- **`/skill-test` skill** — auto-generates 3-5 test scenarios for any skill and validates them through subagents — Автотестирование скиллов
- **IDE-aware skill catalog** — `skill-catalog.md` now uses correct IDE directory paths instead of hardcoded `.claude/` — Параметризованный каталог скиллов

### Changed / Изменено

- **`--smart` is now default** — stack detection and skill auto-enable run automatically; use `--no-detect` to skip — `--smart` теперь по умолчанию
- **`--init` no longer requires a name** — project name auto-derived from directory; `--init my-name` still works — `--init` без обязательного имени
- `bootstrap.py --ide` now accepts `qwen` and includes it in `all` — Qwen добавлен в выбор IDE
- Supported IDEs: Claude Code, Cursor, **Qwen Code**, Windsurf, Codex — 5 IDE
- Skills count: 33 → 34 (added `/skill-test`) — 34 скилла
- Filesize gate exempts `agents/qwen/mcp/` directory — Исключение для qwen mcp
## [1.1.1] — 2026-04-14

### Fixed

- **MCP tags coercion** — `tausik_dead_end` and `tausik_memory_add` now accept `tags` as both JSON array and string. MCP clients (Claude Code) may serialize array params as JSON strings; added `_coerce_tags()` helper to handle both formats gracefully.

## [1.0.0] — 2026-04-05

### Public Release / Публичный релиз

First public release of TAUSIK. Cross-IDE AI agent framework implementing [SENAR v1.3 Core](https://senar.tech).
Первый публичный релиз TAUSIK. Кросс-IDE фреймворк для AI-агентов, реализующий [SENAR v1.3 Core](https://senar.tech).

### Highlights / Основное

- **Cross-IDE support** — Claude Code, Cursor, Windsurf, Codex with unified skill/role/stack system — Поддержка Claude Code, Cursor, Windsurf, Codex с единой системой скиллов/ролей/стеков
- **31 skills** — from `/start` to `/ship`, covering the full development lifecycle — 31 скилл, покрывающих полный цикл разработки
- **SENAR v1.3 Core compliance (100%)** — Quality gates, metrics, dead ends, explorations, verification checklists — Полное соответствие SENAR v1.3 Core
- **Graph memory** — Project knowledge base with edges, soft-invalidation, FTS5 search — Графовая память проекта с рёбрами, soft-invalidation, FTS5 поиском
- **Autonomous batch mode** — `/run plan.md` executes multi-task plans with subagents — Автономный batch-режим для выполнения планов

### Added / Добавлено

- **Quality Gates** — QG-0 (context gate: goal + AC + negative scenario) and QG-2 (implementation gate: evidence + tests + ac-verified) — Quality gates с жёстким enforcement
- **Claude Code Hooks** — task gate, bash firewall, git push gate, auto-format — Хуки для контроля в реальном времени
- **SENAR Metrics** — Throughput, Lead Time, FPSR, DER, Dead End Rate, Cost per Task — Автоматические метрики
- **Multi-language gates** — pytest, ruff, go-vet, clippy, phpstan, eslint, tsc, and more — Gates для 10+ языков
- **5-agent review pipeline** — quality, implementation, testing, simplification, documentation agents with iterative cycle — 5 параллельных review-агентов с итеративным циклом
- **Dead ends & explorations** — `dead-end` for documenting failures, `explore` for time-bounded research — Документирование тупиков и исследования
- **Graph memory** — Polymorphic edges between memory/decision nodes, 4 relation types, recursive CTE traversal — Полиморфные рёбра, 4 типа связей, обход графа через CTE
- **Structured task logs** — `task_logs` table with phase tracking and FTS5 index — Структурированные логи задач
- **Vendor skills** — `skills.example.json` + `skill activate/deactivate` for third-party extensions — Поддержка сторонних скиллов
- **Bootstrap** — `bootstrap.py --smart --init` for one-command setup with stack detection — Настройка одной командой с детекцией стека
- **Apache 2.0 license** — Open source license — Лицензия Apache 2.0
- **Bilingual docs** — Full documentation in English and Russian — Полная документация на EN и RU
- **CONTRIBUTING.md** — Contributor guide — Гайд для контрибьюторов
- **837 tests** — Comprehensive test suite — Полный набор тестов
