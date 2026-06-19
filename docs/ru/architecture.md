[English](/docs/architecture) | **Русский**

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
  │ 27 таблиц + 8 FTS5      │
  └─────────────────────────┘
```

## Ключевые модули

### Скрипты (бизнес-логика)

Модули в `scripts/` (v1.5), каждый ≤400 строк. Хайлайты:

| Файл | Назначение |
|------|------------|
| `project.py` | Точка входа CLI, диспетчеризация |
| `project_parser.py` | Дерево команд argparse |
| `project_cli.py` / `_extra.py` / `_ops.py` | CLI-обработчики (статус, задачи, сессии, память, шлюзы, навыки, FTS, метрики, поиск, события, исследования, аудит, run) |
| `project_cli_doctor.py` / `_role.py` / `_stack.py` / `_verify.py` | CLI-обработчики (doctor, roles, stacks, verify) |
| `project_service.py` + миксины `service_*.py` | Бизнес-логика: задачи, знания, навыки, шлюзы, каскады, роли, верификация |
| `service_verification.py` | Scoped pytest gate + verify cache (10 min TTL) |
| `service_roles.py` | Гибридное хранение ролей (DB-метаданные + harness/roles/*.md) |
| `service_stack_ops.py` | Stack scaffold, lint, diff, reset |
| `project_backend.py` + `backend_*.py` | SQLite + FTS5 backend (WAL mode, 27 таблиц + 8 FTS5-индексов) |
| `backend_session_metrics.py` | Gap-based active-time computation |
| `backend_tier_metrics.py` | call_budget vs call_actual tier-метрики |
| `backend_migrations.py` / `_legacy.py` | Миграции схемы до v37 |
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
| `gen_doc_constants.py` + `mcp_tool_counts.py` | Генерация `docs/_generated/constants.json` (v1.5) |
| `audit_orphan_files.py` / `audit_stale_docs.py` / `audit_unused_python.py` / `audit_pytest_dedupe.py` | Static audit reports (review-only, v1.5) |
| `project_cli_hygiene.py` | `tausik hygiene archive` (read-only гигиена проекта, v1.5) |
| `hooks/check_docs.py` | Pre-commit / CI wrapper для drift-проверки doc-constants (v1.5) |

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
| `harness/claude/mcp/project/server.py` | JSON-RPC stdio-сервер |
| `harness/claude/mcp/project/tools.py` | core tool definitions |
| `harness/claude/mcp/project/tools_extra.py` | расширенные tool definitions (skills, gates, doctor, verify, roles, stacks, brain) |
| `harness/claude/mcp/project/handlers.py` | Диспетчеризация: имя инструмента → метод сервиса |
| `harness/claude/mcp/project/handlers_skill.py` | Обработчики навыков + обслуживания (split) |

Полный MCP-surface: **116 project + 7 brain = 123 инструмента** (опциональный `codebase-rag` добавляет ещё 7; не в основном счёте).

### Поддержка разных сред разработки

Навыки, роли, стеки — общие для всех сред. MCP-серверы — специфичны для среды:
```
harness/
├── skills/           # 13 core auto-deployed + brain условно + 20 в skills-official/ (opt-in через --include-official)
├── roles/            # 5 ролей (developer, architect, qa, tech-writer, ui-ux)
├── stacks/           # Руководства по стекам
├── overrides/        # Переопределения для конкретных сред (claude/, cursor/, qwen/)
├── claude/mcp/       # MCP-серверы (project, codebase-rag)
├── cursor/mcp/       # MCP-серверы для Cursor
└── qwen/ → claude/   # Qwen Code (fallback на Claude MCP)
```

## БД: Таблицы (Schema v37)

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
| `roles` | Реестр ролей (гибрид: метаданные + harness/roles/{slug}.md) |
| `session_activity` | Per-tool-call таймстемпы для gap-based active time |
| `verification_runs` | Verify cache: file_hash + timestamp для QG-2 reuse (10 min TTL) |

## Шлюзы качества

```
default_gates.py        → DEFAULT_GATES (25 гейтов: 5 универсальных + 20 stack-scoped)
                        → UNIVERSAL_GATES (filesize, tdd_order, ruff, mypy, bandit)
                        → stack-scoped gates pulled from stack_registry
gate_runner.py          → run_gates(trigger, files)
                        → run_command_gate() / run_filesize_gate() / run_tdd_order_gate()
service_task.py         → _run_quality_gates() (вызывается из task_done)
```

Универсальные гейты (всегда включены): `filesize`, `tdd_order`, `ruff`, `mypy`, `bandit`.

Stack-scoped гейты: `pytest`, `tsc`, `eslint`, `js-test`, `go-vet`, `go-test`, `golangci-lint`,
`cargo-check`, `cargo-test`, `clippy`, `phpstan`, `phpcs`, `phpunit`, `javac`, `ktlint`,
`ansible-lint`, `terraform-validate`, `helm-lint`, `kubeval`, `hadolint`.

## Адаптация RENAR — advisory-first («лайт»)

TAUSIK — лёгкий zero-dep фреймворк, поэтому [RENAR](https://renar.tech) (стандарт
рассуждения/управления) внедряется **advisory-first**, а не тяжёлой обязательной
церемонией. Адаптация поднимается по лестнице с явными условиями входа на каждую
ступень (Decision #115):

| Ступень | Что | Статус |
|---|---|---|
| 1. Артефакты | SPEC / ADAPT / conformance в SQLite-субстрате + one-way экспорт `renar/` | done (RENAR-1) |
| 2. Advisory-сигналы | QG-0 выдаёт **неблокирующий** нудж, когда high-stakes задача (tier `substantial`/`deep` или `complex`) стартует без связанного SPEC и без ADAPT — `gate_qg0_renar.renar_qg0_advisory`, тоггл `renar.qg0_advisory` (по умолчанию вкл) | done (1.5) |
| 3. Хардгейт по доказательству | повысить конкретный advisory до **блокирующего** только когда реальный дефект упрётся в его отсутствие (аудит #91) | 2.0 |
| 4. RENAR-2 подписанный/неизменяемый ADAPT | подпись ADAPT (ed25519) → `tz_immutable=true` + delta-ADAPT — **необратимо, только по команде пользователя** | 2.0 |

Философия: RENAR усиливает SENAR, делая интерпретацию **видимой** на естественном
гейте (QG-0), не блокируя агента — fail-soft на advisory, fail-closed только на
доказанных гейтах. Это осознанная политика лёгкой адаптации, а не «недоделанный RENAR».

## Orchestrator-worker (авто-переключение модели через сабагентов)

Главная сессия — **координатор** (планирование, AC, ревью). Задачу complexity ≤
medium можно **делегировать** **воркеру-сабагенту**, поднятому через Agent tool с
`model=recommended` — единственный программный механизм выбора модели в Claude
Code (паттерн orchestrator-workers от Anthropic). TAUSIK даёт **scaffolding/state**
делегирования; сам spawn делает агент.

| Шаг | Команда / механизм |
|---|---|
| Делегировать | `tausik task delegate <slug>` — пишет {рекоменд. модель, parent session} в `meta` kv (без миграции). **complex отвергается** (остаётся у координатора). |
| Handoff-контракт | `tausik task handoff <slug>` — детерминированный JSON {slug, goal, acceptance_criteria, scope, scope_exclude, model, skills}; trimmed профиль `WORKER_SKILLS` (без plan/explore/brain). Оркестратор передаёт его в Agent tool; воркер возвращает обратно (round-trip identity). |
| Распознавание in-session | `task start` делегированной задачи показывает **worker mode** (operating contract) и подавляет orchestrator-only баннер модели. |
| Scope hard-gate | воркер ограничен scope — `scope_write_gate` блокирует edits вне `scope_paths`, а делегированная задача **без** scope блокируется до объявления (нет legacy fail-open для воркеров). |
| Summary-back | `tausik task summary-back <slug> "<summary>" [--gates …]` — воркер возвращает структурный результат (в `meta`, виден в `task show`), чтобы координатор взял его **без** транскрипта воркера. |

Состояние делегирования — CLI-first (без MCP, чтобы избежать doc-count drift) и
целиком в таблице `meta` (`delegation:<slug>`, `worker_summary:<slug>`).

## Hooks (anti-drift, см. [hooks.md](hooks.md))

Все hook-файлы в `scripts/hooks/` регистрируются через `bootstrap/bootstrap_generate.py` (Claude Code) и `bootstrap/bootstrap_qwen.py` (Qwen Code). Hook-скрипты non-blocking (exit 0), ошибки в stderr. Общие helper'ы в `scripts/hooks/_common.py`.

Brain-хуки делят helpers в `scripts/brain_hook_utils.py` — одна реализация mirror-lookup + TTL семантики. Brain-connection setup в `scripts/brain_runtime.py`: `open_brain_deps() -> (conn, client, cfg)`. Skill `/brain` — диалоговый UI.

## Memory Aggregates

`service_knowledge_aggregates.py` содержит чистые функции для re-injection памяти:

- `build_memory_block(be, ...)` — компактный markdown (decisions + conventions + dead ends) ≤50 строк, вызывается из `/start`, `/checkpoint`, SessionStart hook
- `build_memory_compact(be, last_n)` — агрегация `task_logs`: фазы + топ-слова + топ-файлы

Аналогично `scripts/model_routing.py` + `plugin_data.py` — чистые модули, импортируемые из CLI/MCP handlers.

## Prompt caching

TAUSIK опирается на автоматический prompt caching от Anthropic — это удерживает
стоимость агентских прогонов в разумных границах. Сам фреймворк не делает
API-вызовов (это делает Claude Code), но *структура* того, что TAUSIK
кладёт в каждый ход, определяет: попадёт префикс в кеш или перебиллится
заново. Кешируемая поверхность по приоритету:

| Поверхность | Где живёт | Почему кешируется хорошо |
|---|---|---|
| System prompt + схемы инструментов | Инжектится Claude Code'ом из `.claude/mcp/project/tools.py` и `tools_extra.py` | Идентично между ходами в рамках сессии — самый длинный стабильный префикс |
| `CLAUDE.md` | Корень проекта | Читается раз за сессию и реинжектится; стабилен пока `tausik_update_claudemd` не перепишет dynamic-блок |
| Описания MCP-инструментов | Те же `tools.py` | Любая правка инвалидирует кеш — изменение формулировки переписывает весь префикс |
| Skills (`SKILL.md`) | `harness/skills/<name>/SKILL.md` | Подгружаются только при активации скилла |

**Что инвалидирует кеш в середине сессии.** Любая правка перечисленных файлов
между ходами переписывает префикс и заставляет следующий ход платить
`cache_creation_input_tokens` вместо `cache_read_input_tokens`. Главный
нарушитель — `tausik_update_claudemd`: его прогон в середине сессии
переписывает dynamic-state блок (номер сессии, счётчики задач и т.д.), и
весь префикс `CLAUDE.md` перекешируется. Зови его на границах сессии
(`/start`, `/checkpoint`, `/end`), а не между рядовыми tool-вызовами.

**Как проверить, что caching реально работает.** Anthropic возвращает
`cache_creation_input_tokens` (префикс только что записан) и
`cache_read_input_tokens` (последующий ход попал в кеш) в `usage`-блоке
каждого ответа. `scripts/validate_prompt_caching.py` парсит транскрипт
Claude Code (JSONL) и выдаёт обе суммы + hit-rate:

```bash
python scripts/validate_prompt_caching.py --auto
# или
python scripts/validate_prompt_caching.py path/to/transcript.jsonl
```

Exit code `0` = caching активен (`cache_read_input_tokens > 0`);
`1` = префикс нестабилен (creation > 0, reads = 0);
`2` = API вообще не вернул cache-поля. См. [troubleshooting.md](troubleshooting.md)
секцию «Prompt caching не активен» — типовые причины.

## Тестирование

```bash
pytest tests/ -v                    # все тесты (4101)
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

См. **[Принципы тестирования](testing-principles.md)** — когда добавлять тесты, маппинг scoped pytest, анти-паттерны (в т.ч. копипаста без нового поведения).
