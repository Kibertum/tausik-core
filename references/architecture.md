# TAUSIK Architecture Reference

## Архитектура: CLI → Service → Backend

Три слоя с чёткими границами. Service layer содержит бизнес-логику,
backend — только CRUD и SQL. CLI и MCP — два равноправных входа.

```
  Инженер (свободный текст)
       ↓
  AI-агент (Claude Code / Cursor)
       ↓
  ┌─────────────────────────┐
  │ Skills (SKILL.md)       │  ← инструкции для агента
  └─────────────────────────┘
       ↓                ↓
  ┌─────────┐    ┌─────────┐
  │ MCP     │    │ CLI     │  ← два входа
  │ (tools) │    │ (bash)  │
  └────┬────┘    └────┬────┘
       └──────┬───────┘
              ↓
  ┌─────────────────────────┐
  │ Service Layer           │  ← бизнес-логика, QG-0, QG-2
  │ project_service.py      │
  │ + service_task.py       │
  │ + service_knowledge.py  │
  └─────────────────────────┘
              ↓
  ┌─────────────────────────┐
  │ Backend Layer           │  ← SQLite CRUD, FTS5, метрики
  │ project_backend.py      │
  │ + backend_queries.py    │
  │ + backend_graph.py      │
  │ + backend_schema.py     │
  │ + backend_migrations.py │
  └─────────────────────────┘
              ↓
  ┌─────────────────────────┐
  │ SQLite (WAL mode)       │  ← .tausik/tausik.db
  │ 11 таблиц + 4 FTS5     │
  └─────────────────────────┘
```

## Ключевые модули

### Scripts (бизнес-логика)

| Файл | Строк | Назначение |
|------|-------|------------|
| `project.py` | ~120 | Точка входа CLI, dispatch |
| `project_parser.py` | ~380 | argparse дерево команд |
| `project_cli.py` | ~345 | CLI handlers (status, task, session, roadmap) |
| `project_cli_extra.py` | ~375 | CLI handlers (memory, gates, skills, fts) |
| `project_cli_ops.py` | ~145 | CLI handlers (metrics, search, events, explore, audit, run) |
| `project_service.py` | ~340 | ProjectService + SessionMixin + HierarchyMixin |
| `service_task.py` | ~375 | TaskMixin: task lifecycle, QG-0, QG-2 |
| `service_knowledge.py` | ~325 | KnowledgeMixin: memory, decisions, graph, explorations |
| `service_skills.py` | ~220 | SkillsMixin: activate, deactivate, list, install |
| `service_gates.py` | ~340 | GatesMixin: QG-0, QG-2, SENAR checklist |
| `service_cascade.py` | ~45 | CascadeMixin: auto-start/close story/epic |
| `project_backend.py` | ~395 | SQLiteBackend: WAL, FTS5, hierarchy + task CRUD |
| `backend_crud.py` | ~230 | BackendCrudMixin: session, decision, memory, meta, events |
| `backend_queries.py` | ~375 | Метрики, roadmap, поиск, graph traversal |
| `backend_graph.py` | ~110 | Graph memory (edges) + explorations |
| `backend_schema.py` | ~240 | DDL: 11 таблиц + 4 FTS + triggers + indexes |
| `backend_migrations.py` | ~160 | Миграции v10→v15 + import legacy |
| `backend_migrations_legacy.py` | ~280 | Legacy миграции v2→v9 |
| `project_config.py` | ~350 | Config loader, gates config, auto-enable |
| `gate_runner.py` | ~215 | Выполнение quality gates |
| `skill_manager.py` | ~360 | Установка/удаление скиллов из репозиториев |
| `skill_repos.py` | ~200 | Управление skill-репозиториями |
| `ide_utils.py` | ~125 | Определение IDE, пути, реестр |
| `plan_parser.py` | ~125 | Парсер markdown-планов для /run |
| `tausik_utils.py` | ~50 | Slug validation, timestamps, slugify |
| `project_types.py` | ~40 | TypedDict, constants |
| `tausik_version.py` | ~3 | Версия |

### Bootstrap (генерация)

| Файл | Строк | Назначение |
|------|-------|------------|
| `bootstrap.py` | ~320 | Оркестрация: vendor sync, copy, generate |
| `bootstrap_vendor.py` | ~280 | Скачивание vendor skills из GitHub (tarball) |
| `bootstrap_copy.py` | ~180 | Копирование skills, scripts, MCP, references |
| `bootstrap_config.py` | ~70 | Конфигурация, стек-детекция |
| `bootstrap_generate.py` | ~300 | Генерация settings.json, CLAUDE.md, skill catalog |
| `analyzer.py` | ~330 | Расширенная стек-детекция, анализ кодовой базы |

### MCP Server

| Файл | Назначение |
|------|------------|
| `agents/claude/mcp/project/server.py` | JSON-RPC stdio server |
| `agents/claude/mcp/project/tools.py` | 54 tool definitions (core) |
| `agents/claude/mcp/project/tools_extra.py` | 19 tool definitions (skills, gates, maintenance) |
| `agents/claude/mcp/project/handlers.py` | Dispatch: tool name → service method |
| `agents/claude/mcp/project/handlers_skill.py` | Skill + maintenance handlers (split) |

### Cross-IDE Support

Skills, roles, stacks — shared across IDEs. MCP servers are IDE-specific:
```
agents/
├── skills/           # 34 skill (core + extension + solo)
├── roles/            # 5 ролей (developer, architect, qa, tech-writer, ui-ux)
├── stacks/           # Гайды по стекам
├── overrides/        # Переопределения для сред (claude/, cursor/, qwen/)
├── claude/mcp/       # MCP-серверы (project, codebase-rag)
├── cursor/mcp/       # MCP-серверы для Cursor
└── qwen/ → claude/   # Qwen Code (fallback на Claude MCP)
```

## БД: Таблицы (Schema v15)

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
| `memory_edges` | Графовые связи между memory/decision (Graphiti) |
| `fts_tasks` | FTS5 полнотекстовый индекс по задачам |
| `fts_memory` | FTS5 индекс по памяти |
| `fts_decisions` | FTS5 индекс по решениям |
| `task_logs` | Структурированные логи задач (phase, message) |
| `fts_task_logs` | FTS5 индекс по логам задач |

## Quality Gates

```
project_config.py       → DEFAULT_GATES (16 gates)
                        → STACK_GATE_MAP (auto-enable по стеку)
                        → auto_enable_gates_for_stacks()
gate_runner.py          → run_gates(trigger, files)
                        → run_command_gate() / run_filesize_gate() / run_tdd_order_gate()
service_task.py         → _run_quality_gates() (вызывается из task_done)
```

Gates: `pytest`, `ruff`, `mypy`, `bandit`, `filesize`, `tdd_order`, `tsc`, `eslint`,
`go-vet`, `golangci-lint`, `cargo-check`, `clippy`, `phpstan`, `phpcs`, `javac`, `ktlint`.

## Тестирование

```bash
pytest tests/ -v                    # все тесты (918)
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
