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

Модули в `scripts/`, каждый ≤500 строк (гейт `filesize`; поднято с 400 как
промежуточная мера решением #190 — более тесный лимит деформировал архитектуру,
а не улучшал её). Число строк — не единственный контроль размера: гейт
`class_surface` отдельно ограничивает составную публичную поверхность класса
после наследования, которую пофайловый лимит видеть структурно не может.
Хайлайты:

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
| `harness/claude/mcp/project/handlers.py` | Только диспетчеризация: счётчик вызовов, `handle_tool`, слияние доменных таблиц |
| `harness/claude/mcp/project/handlers_<домен>.py` | Обработчики по доменам: `task`, `session`, `status`, `knowledge`, `hierarchy`, `stack`, `role`, `verification`, `cq`, `skill`, `spec`, `adapt`. Каждый модуль экспортирует `<DOMAIN>_HANDLERS`, `handlers.py` сливает их в `_DISPATCH` |
| `harness/claude/mcp/project/handlers_render.py` | Общий рендер списков (`render_list`) — пустой результат обязан читаться как «ничего нет», а не как пустая строка |

Полный MCP-surface: **117 project + 7 brain = 124 инструмента** (опциональный `codebase-rag` добавляет ещё 7; не в основном счёте).

### Контекстные заголовки чанков (codebase-rag)

Чанк, вырезанный из файла, перестаёт нести то, о чём файл был, и запрос,
сформулированный в терминах документа, до такого пассажа не дотягивается.
Поэтому каждый индексируемый чанк несёт короткий заголовок, который строит
`harness/claude/mcp/codebase-rag/rag_context.py`: слова пути, символ, который
чанк определяет, — или тот, внутри которого он находится, если это
чанк-продолжение, — и строку-сводку самого файла.

Это contextual retrieval с изъятой из него моделью. Опубликованная техника
просит LLM написать по предложению контекста на чанк; здесь заголовок берётся
из метаданных, которые у индексатора уже есть, поэтому один и тот же вход даёт
одни и те же байты, а индексация остаётся воспроизводимой и офлайновой.

Заголовок живёт в собственной индексируемой колонке
(`rag_chunks.context_prefix`), а не в содержимом чанка: слово, присутствующее
только в заголовке, находится — и в выдаче поиска не появляется. Индекс,
собранный до v1.8, дорастает до новой раскладки при первом открытии: колонка
добавляется, а FTS-таблица перестраивается из чанков, которые и есть источник
истины.

### Поддержка разных сред разработки

Навыки, роли, стеки — общие для всех сред. MCP-серверы тоже: `harness/claude/mcp/` —
единственное каноническое дерево, и `copy_mcp` отдаёт его каждой среде, у которой нет
своего (сегодня — всем). Отдельная копия под IDE была бы зеркалом, обречённым разъехаться:
такое лежало в `harness/cursor/` и удалено в v1.7.0.
```
harness/
├── skills/           # 13 core auto-deployed + brain условно + 20 в skills-official/ (opt-in через --include-official)
├── roles/            # 6 ролей (architect, developer, devops, qa, tech-writer, ui-ux)
├── stacks/           # Руководства по стекам
├── overrides/        # Переопределения для конкретных сред (claude/, cursor/, qwen/)
├── claude/mcp/       # MCP-серверы (project, brain, codebase-rag) — канон для ВСЕХ сред
└── opencode/plugins/ # Плагин дисциплины QG-0 для OpenCode (tool.execute.before)
```

#### Среда (IDE) × Модель — две ортогональные оси (Решение #119)

TAUSIK разделяет *где* он работает и *какая модель* отвечает:

| Ось | Что задаёт | Цель `bootstrap --ide` | Определение активной модели |
|-----|------------|------------------------|-----------------------------|
| **claude** | Claude Code (VSCode/CLI) | `.claude/` + `.mcp.json` | JSONL-транскрипт (поле `model`) |
| **cursor** | Cursor | `.cursor/` + `.cursor/mcp.json` | — |
| **qwen** | Qwen Code | `.qwen/settings.json` | — |
| **kilo** | Kilo Code (аддон + CLI) | `.kilo/kilo.jsonc` **и** `.kilocode/mcp.json` | env `KILO_MODEL` / конфиг `.kilo` |
| **opencode** | OpenCode (SST) | `opencode.json` + `.opencode/plugins/` | — |

**Ось модели — это данные, а не код**: `scripts/model_profiles.py` отображает семейства
вендоров (`claude`, `glm`/z.ai) × ранги способностей → конкретные id моделей;
переопределяется в `.tausik/config.json`, ключ `model_profiles.families`. Матрица
маршрутизации выдаёт абстрактный ранг, активное семейство резолвит его в реальную модель —
поэтому сессия на z.ai GLM уезжает к GLM-моделям без единой правки кода. См.
[Kilo + z.ai](kilo-zai.md).

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
gate_registry.py        → GATE_REGISTRY: одно объявление на встроенный гейт
                        → GateSpec(name, phase, default_config, impl)
                        → phase: scoped | post_scope
default_gates.py        → DEFAULT_GATES = универсальные (из реестра)
                                        ∪ stack-scoped (из stack_registry)
                                        ∪ post-scope (из реестра)
gate_runner.py          → run_gates(trigger, files)   [только фаза scoped]
                        → диспетч через GATE_REGISTRY[name].impl,
                          имя вне реестра → run_command_gate()
gate_post_scope.py      → run_post_scope_gates()      [фаза post_scope]
                        → verify_first, changelog + по строке в gate_runs
service_task.py         → _run_quality_gates() (вызывается из task_done)
```

Добавить встроенный гейт — это один `GateSpec`. До `gate-registry-single-source`
требовалось четыре правки, а два post-scope гейта жили лишь в одном из четырёх
мест: `gates status` их не перечислял, `gates enable/disable` до них не доставал,
и они не писали строку в `gate_runs` — то есть НИЧТО не могло доказать, что
QG-2-гейт отработал.

**Scoped-гейты** — `(gate_config, files) -> (passed, output)`, судят объявленный
скоуп задачи. Универсальные (всегда включены): `filesize`, `class_surface`,
`tdd_order`, `ruff`, `mypy`, `bandit`, `bootstrap_drift`, `memory_route`,
`renar_drift_schema`, `renar_drift_provenance`.

`class_surface` — единственное исключение из «судят объявленный скоуп»: он
игнорирует список файлов и мерит **весь репозиторий** (~0.65 с). Класс уезжает за
лимит через свои *базы*, поэтому пофайловый прогон этого не увидит никогда — та
же слепота, из-за которой модуль дорос до 406 строк, никого не заблокировав. Гейт
ограничивает составную публичную поверхность класса после наследования, которую
пофайловый `filesize` структурно видеть не может: god-объект, собранный из
миксинов, держит каждый файл ниже строкового лимита. Они **дополняют** друг
друга — «этот класс делает слишком много» и «этот файл слишком длинный, чтобы его
читать» суть разные дефекты. Счёт объявлен **нижней границей** (AST, никогда
`import`, чтобы гейт мог измерить ветку, которую ещё никто не читал), а известные
превышающие классы держит baseline-храповик в `tausik/gates.json`, который может
только сокращаться.

**Post-scope гейты** — принимают контекст закрытия и правят QG-2-отчёт:
`verify_first` (обязателен свежий подписанный зелёный verify) и `changelog`
(конвенция #275). `get_gates_for_trigger` их отфильтровывает, поэтому
`run_gates` никогда не вызовет их с чужой сигнатурой.

Stack-scoped гейты: `pytest`, `tsc`, `eslint`, `js-test`, `go-vet`, `go-test`, `golangci-lint`,
`cargo-check`, `cargo-test`, `clippy`, `phpstan`, `phpcs`, `phpunit`, `javac`, `ktlint`,
`ansible-lint`, `terraform-validate`, `helm-lint`, `kubeconform`, `hadolint`.

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
pytest tests/ -v                    # все тесты (6096)
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
