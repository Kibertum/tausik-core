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
  │ 11 таблиц + 4 FTS5     │
  └─────────────────────────┘
```

## Ключевые модули

### Скрипты (бизнес-логика)

| Файл | Строк | Назначение |
|------|-------|------------|
| `project.py` | ~120 | Точка входа CLI, диспетчеризация |
| `project_parser.py` | ~380 | Дерево команд argparse |
| `project_cli.py` | ~345 | Обработчики CLI (статус, задачи, сессии, дорожная карта) |
| `project_cli_extra.py` | ~375 | Обработчики CLI (память, шлюзы, навыки, FTS) |
| `project_cli_ops.py` | ~145 | Обработчики CLI (метрики, поиск, события, исследования, аудит, run) |
| `project_service.py` | ~340 | Сервис проекта + миксины сессий и иерархии |
| `service_task.py` | ~375 | Миксин задач: жизненный цикл, QG-0, QG-2 |
| `service_knowledge.py` | ~325 | Миксин знаний: память, решения, граф, исследования |
| `service_skills.py` | ~220 | Миксин навыков: activate, deactivate, list, install |
| `service_gates.py` | ~340 | Миксин шлюзов: QG-0, QG-2, SENAR чеклист |
| `service_cascade.py` | ~45 | Миксин каскадов: auto-start/close story/epic |
| `project_backend.py` | ~395 | Хранилище SQLite: WAL, FTS5, иерархия + задачи CRUD |
| `backend_crud.py` | ~230 | BackendCrudMixin: сессии, решения, память, мета, события |
| `backend_queries.py` | ~375 | Метрики, дорожная карта, поиск, обход графа |
| `backend_graph.py` | ~110 | Графовая память (связи) + исследования |
| `backend_schema.py` | ~240 | DDL: 11 таблиц + 4 FTS + триггеры + индексы |
| `backend_migrations.py` | ~160 | Миграции v10→v15 + import legacy |
| `backend_migrations_legacy.py` | ~280 | Legacy миграции v2→v9 |
| `project_config.py` | ~350 | Загрузчик конфигурации, настройка шлюзов, автовключение |
| `gate_runner.py` | ~215 | Выполнение шлюзов качества |
| `skill_manager.py` | ~360 | Установка/удаление навыков из репозиториев |
| `skill_repos.py` | ~200 | Управление skill-репозиториями |
| `ide_utils.py` | ~125 | Определение IDE, пути, реестр |
| `plan_parser.py` | ~125 | Парсер markdown-планов для /run |
| `tausik_utils.py` | ~50 | Валидация slug, метки времени, slugify |
| `project_types.py` | ~40 | Типы данных, константы |
| `tausik_version.py` | ~3 | Версия |

### Начальная настройка (генерация)

| Файл | Строк | Назначение |
|------|-------|------------|
| `bootstrap.py` | ~320 | Оркестрация: vendor sync, copy, generate |
| `bootstrap_vendor.py` | ~280 | Скачивание внешних навыков из GitHub (tarball) |
| `bootstrap_copy.py` | ~180 | Копирование навыков, скриптов, MCP, справочников |
| `bootstrap_config.py` | ~70 | Конфигурация, стек-детекция |
| `bootstrap_generate.py` | ~300 | Генерация settings.json, CLAUDE.md, каталога навыков |
| `analyzer.py` | ~330 | Расширенная стек-детекция, анализ кодовой базы |

### MCP-сервер

| Файл | Назначение |
|------|------------|
| `agents/claude/mcp/project/server.py` | JSON-RPC stdio-сервер |
| `agents/claude/mcp/project/tools.py` | 54 определения инструментов (основные) |
| `agents/claude/mcp/project/tools_extra.py` | 19 определений (навыки, шлюзы, обслуживание) |
| `agents/claude/mcp/project/handlers.py` | Диспетчеризация: имя инструмента → метод сервиса |
| `agents/claude/mcp/project/handlers_skill.py` | Обработчики навыков + обслуживания (split) |

### Поддержка разных сред разработки

Навыки, роли, стеки — общие для всех сред. MCP-серверы — специфичны для среды:
```
agents/
├── skills/           # 34 навыка (основные + расширенные + автономные)
├── roles/            # 5 ролей (developer, architect, qa, tech-writer, ui-ux)
├── stacks/           # Руководства по стекам
├── overrides/        # Переопределения для конкретных сред (claude/, cursor/, qwen/)
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
| `memory_edges` | Графовые связи между записями памяти и решениями |
| `fts_tasks` | FTS5 полнотекстовый индекс по задачам |
| `fts_memory` | FTS5 индекс по памяти |
| `fts_decisions` | FTS5 индекс по решениям |
| `task_logs` | Структурированные логи задач (phase, message) |
| `fts_task_logs` | FTS5 индекс по логам задач |

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
