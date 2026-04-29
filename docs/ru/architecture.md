[English](../en/architecture.md) | **Русский**

# Архитектура TAUSIK

## Три слоя: CLI → Сервис → Хранилище

Три слоя с чёткими границами. Сервисный слой содержит бизнес-логику,
хранилище — только CRUD и SQL. CLI и MCP — два равноправных входа.

```
  Инженер (свободный текст)
       ↓
  ИИ-агент (Claude Code / Cursor)
       ↓
  ┌─────────────────────────┐
  │ Навыки (SKILL.md)       │  ← инструкции для агента
  └─────────────────────────┘
       ↓                ↓
  ┌─────────┐    ┌─────────┐
  │ MCP     │    │ CLI     │  ← два входа
  │ (tools) │    │ (bash)  │
  └────┬────┘    └────┬────┘
       └──────┬───────┘
              ↓
  ┌─────────────────────────┐
  │ Сервисный слой          │  ← бизнес-логика, QG-0, QG-2
  │ project_service.py      │
  │ + service_task.py       │
  │ + service_knowledge.py  │
  └─────────────────────────┘
              ↓
  ┌─────────────────────────┐
  │ Слой хранилища          │  ← SQLite CRUD, FTS5, метрики
  │ project_backend.py      │
  │ + backend_queries.py    │
  │ + backend_graph.py      │
  │ + backend_schema.py     │
  │ + backend_migrations.py │
  └─────────────────────────┘
              ↓
  ┌─────────────────────────┐
  │ SQLite (WAL mode)       │  ← .tausik/tausik.db
  │ 18 таблиц + FTS5        │
  └─────────────────────────┘
```

## Ключевые модули

### Скрипты (бизнес-логика)

73 source-файла в `scripts/` (v1.3). Хайлайты:

| Файл | Назначение |
|------|------------|
| `project.py` | Точка входа CLI, диспетчеризация |
| `project_parser.py` | Дерево команд argparse |
| `project_cli.py` / `_extra.py` / `_ops.py` | CLI-обработчики (статус, задачи, сессии, память, шлюзы, навыки, FTS, метрики, поиск, события, исследования, аудит, run) |
| `project_cli_doctor.py` / `_role.py` / `_stack.py` / `_verify.py` | v1.3 CLI-обработчики (doctor, roles, stacks, verify) |
| `project_service.py` + миксины `service_*.py` | Бизнес-логика: задачи, знания, навыки, шлюзы, каскады, роли, верификация |
| `service_verification.py` | Scoped pytest gate + verify cache (10 min TTL) |
| `service_roles.py` | Гибридное хранение ролей (DB-метаданные + agents/roles/*.md) |
| `service_stack_ops.py` | Stack scaffold, lint, diff, reset |
| `project_backend.py` + `backend_*.py` | SQLite + FTS5 backend (WAL mode, 18 таблиц) |
| `backend_session_metrics.py` | Gap-based active-time computation |
| `backend_tier_metrics.py` | call_budget vs call_actual tier-метрики |
| `backend_migrations.py` / `_legacy.py` | Миграции схемы до v18 |
| `project_config.py` + `default_gates.py` | Загрузчик конфигурации, настройка шлюзов, автовключение |
| `gate_runner.py` + `gate_stack_dispatch.py` + `gate_test_resolver.py` | Scoped pytest mapping + dispatch |
| `skill_manager.py` + `skill_repos.py` | Установка/удаление навыков из репозиториев |
| `brain_*.py` | Shared Brain (Notion mirror, sync, classifier, registry) |
| `cq_client.py` | Cross-project queue клиент |
| `doc_extract.py` | markitdown интеграция |
| `docs_lint.py` | Warning-only stale-version линтер |
| `plan_parser.py` | Парсер markdown-планов для `/run` |
| `model_routing.py` | Helper выбора модели |
| `ide_utils.py` | Определение IDE, пути, реестр |
| `tausik_utils.py` + `tausik_version.py` + `project_types.py` | Хелперы, версия, типы |

### Начальная настройка (генерация)

| Файл | Строк | Назначение |
|------|-------|------------|
| `bootstrap.py` | ~320 | Оркестрация: vendor sync, copy, generate |
| `bootstrap_vendor.py` | ~280 | Скачивание внешних навыков из GitHub (tarball) |
| `bootstrap_copy.py` | ~180 | Копирование навыков, скриптов, MCP в `.claude/` |
| `bootstrap_config.py` | ~70 | Конфигурация, стек-детекция |
| `bootstrap_generate.py` | ~300 | Генерация settings.json, CLAUDE.md, каталога навыков |
| `analyzer.py` | ~330 | Расширенная стек-детекция, анализ кодовой базы |

### MCP-сервер

| Файл | Назначение |
|------|------------|
| `agents/claude/mcp/project/server.py` | JSON-RPC stdio-сервер |
| `agents/claude/mcp/project/tools.py` | core tool definitions |
| `agents/claude/mcp/project/tools_extra.py` | расширенные tool definitions (skills, gates, doctor, verify, roles, stacks, brain) |
| `agents/claude/mcp/project/handlers.py` | Диспетчеризация: имя инструмента → метод сервиса |
| `agents/claude/mcp/project/handlers_skill.py` | Обработчики навыков + обслуживания (split) |

Полный MCP-surface: **90 project + 6 brain = 96 инструментов**.

### Поддержка разных сред разработки

Навыки, роли, стеки — общие для всех сред. MCP-серверы — специфичны для среды:
```
agents/
├── skills/           # 13 core (auto-deployed) + 25+ в skills-official/ (по запросу)
├── roles/            # 5 ролей (developer, architect, qa, tech-writer, ui-ux)
├── stacks/           # Руководства по стекам
├── overrides/        # Переопределения для конкретных сред (claude/, cursor/, qwen/)
├── claude/mcp/       # MCP-серверы (project, codebase-rag)
├── cursor/mcp/       # MCP-серверы для Cursor
└── qwen/ → claude/   # Qwen Code (fallback на Claude MCP)
```

## БД: Таблицы (Schema v18)

| Таблица | Назначение |
|---------|------------|
| `meta` | Метаданные (schema_version) |
| `epics` | Эпики |
| `stories` | Стори (→ epic) |
| `tasks` | Задачи (→ story, scope, defect_of, plan, AC) |
| `sessions` | Сессии (start, end, summary, handoff) |
| `memory` | Память проекта (pattern, gotcha, convention, context, dead_end) |
| `decisions` | Архитектурные решения |
| `events` | Аудит-лог (gate_bypass, status_changed, claimed) |
| `explorations` | Исследования (time-boxed) |
| `memory_edges` | Графовые связи между записями памяти и решениями |
| `fts_tasks` | FTS5 полнотекстовый индекс по задачам |
| `fts_memory` | FTS5 индекс по памяти |
| `fts_decisions` | FTS5 индекс по решениям |
| `task_logs` | Структурированные логи задач (phase, message) |
| `fts_task_logs` | FTS5 индекс по логам задач |
| `roles` | Реестр ролей (гибрид: метаданные + agents/roles/{slug}.md) |
| `session_activity` | Per-tool-call таймстемпы для gap-based active time |
| `verification_runs` | Verify cache: file_hash + timestamp для QG-2 reuse (10 min TTL) |

## Шлюзы качества

```
project_config.py       → DEFAULT_GATES (16 шлюзов)
                        → STACK_GATE_MAP (автовключение по стеку)
                        → auto_enable_gates_for_stacks()
gate_runner.py          → run_gates(trigger, files)
                        → run_command_gate() / run_filesize_gate() / run_tdd_order_gate()
service_task.py         → _run_quality_gates() (вызывается из task_done)
```

Gates: `pytest`, `ruff`, `mypy`, `bandit`, `filesize`, `tdd_order`, `tsc`, `eslint`,
`go-vet`, `golangci-lint`, `cargo-check`, `clippy`, `phpstan`, `phpcs`, `javac`, `ktlint`.

## Hooks (anti-drift, см. [hooks.md](hooks.md))

Все hook-файлы в `scripts/hooks/` регистрируются через `bootstrap/bootstrap_generate.py` (Claude Code) и `bootstrap/bootstrap_qwen.py` (Qwen Code). Hook-скрипты non-blocking (exit 0), ошибки в stderr. Общие helper'ы в `scripts/hooks/_common.py`.

Brain-хуки делят helpers в `scripts/brain_hook_utils.py` — одна реализация mirror-lookup + TTL семантики. Brain-connection setup в `scripts/brain_runtime.py`: `open_brain_deps() -> (conn, client, cfg)`. Skill `/brain` — диалоговый UI.

## Memory Aggregates

`service_knowledge_aggregates.py` содержит чистые функции для re-injection памяти:

- `build_memory_block(be, ...)` — компактный markdown (decisions + conventions + dead ends) ≤50 строк, вызывается из `/start`, `/checkpoint`, SessionStart hook
- `build_memory_compact(be, last_n)` — агрегация `task_logs`: фазы + топ-слова + топ-файлы

Аналогично `scripts/model_routing.py` + `plugin_data.py` — чистые модули, импортируемые из CLI/MCP handlers.

## Тестирование

```bash
pytest tests/ -v                    # все тесты (2318)
pytest tests/test_tausik_backend.py   # backend CRUD
pytest tests/test_tausik_service.py   # service logic
pytest tests/test_tausik_cli.py       # CLI smoke
pytest tests/test_gates.py          # quality gates + stack auto-enable
pytest tests/test_vendor.py         # vendor skills + persistence
pytest tests/test_graph_memory.py   # graph memory edges
pytest tests/test_mcp_integration.py # MCP handlers
pytest tests/test_senar.py          # SENAR compliance
pytest tests/test_e2e_workflow.py   # E2E workflow
```
