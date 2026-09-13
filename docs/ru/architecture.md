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
| `knowledge_db.py` + `knowledge_write.py` + `knowledge_read.py` | Общее локальное хранилище `~/.tausik-knowledge` (`--global` у `decide` / `memory add`; входит в `memory search`) |
| `publication_boundary.py` + `knowledge_export.py` | Единственное место, где содержимое общего хранилища покидает машину (`knowledge export --redacted`) |
| `cq_client.py` | Cross-project queue клиент |
| `doc_extract.py` | markitdown интеграция |
| `docs_lint.py` | Warning-only stale-version линтер |
| `plan_parser.py` | Парсер markdown-планов для `/run` |
| `model_routing.py` | Helper выбора модели |
| `ide_utils.py` | Определение IDE, пути, реестр |
| `tausik_utils.py` + `tausik_version.py` + `project_types.py` | Хелперы, версия, типы |
| `gen_doc_constants.py` | Точка входа доковых проверок: `--check`, `--write`, перегенерация `constants.json` |
| `doc_drift_common.py` | Общие таблицы регулярных выражений, цели сканов, текстовые помощники |
| `doc_drift_scanners.py` | Шесть сканов дрейфа: версии, счётчики MCP, закрытые перечни, числа тестов и кода |
| `doc_drift_tables.py` | Числовые ячейки колонок таблиц markdown и реестр их предметов |
| `doc_drift_fixes.py` | Автопочинщик, который запускает `--write` |
| `code_counts.py` | Считает состояние репозитория: хуки, стеки, роли, агенты ревью, скиллы |
| `mcp_tool_counts.py` | Считает поверхность MCP, которую объявляет каждый сервер |
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
| `analyzer.py` | ~260 | Детекция расширяющих скиллов и обход дерева |

### MCP-сервер

| Файл | Назначение |
|------|------------|
| `harness/claude/mcp/project/server.py` | JSON-RPC stdio-сервер |
| `harness/claude/mcp/project/tools.py` | core tool definitions |
| `harness/claude/mcp/project/tools_extra.py` | расширенные tool definitions (skills, gates, doctor, verify, roles, stacks) |
| `harness/claude/mcp/project/handlers.py` | Только диспетчеризация: счётчик вызовов, `handle_tool`, слияние доменных таблиц |
| `harness/claude/mcp/project/handlers_<домен>.py` | Обработчики по доменам: `task`, `session`, `status`, `knowledge`, `hierarchy`, `stack`, `role`, `verification`, `cq`, `skill`, `spec`, `adapt`. Каждый модуль экспортирует `<DOMAIN>_HANDLERS`, `handlers.py` сливает их в `_DISPATCH` |
| `harness/claude/mcp/project/handlers_render.py` | Общий рендер списков (`render_list`) — пустой результат обязан читаться как «ничего нет», а не как пустая строка |

Полный MCP-surface: **146 project-инструментов** (опциональный
`codebase-rag` добавляет ещё 7; не в основном счёте).

**ЦЕНА ЭТОЙ ПОВЕРХНОСТИ ПЛАТИТСЯ НА КАЖДОМ ХОДУ, И ОНА РАЗНАЯ ПО ХОСТАМ.**
Протокол MCP пересылает имя И схему каждого инструмента на каждом ходу, если
клиент не откладывает схемы. Замер смены #229: сериализованные определения
project-сервера весят 56 108 байт (порядка 14 000 токенов), одни имена — 3 201
байт (около 800 токенов), разница в 17.5 раза. Claude Code схемы откладывает и
платит имена — это НАБЛЮДАЛОСЬ; хост без отложенной загрузки платит всё — это
следует из протокола и здесь не наблюдалось.

Числа выше даны для чтения, а не как источник истины: источник — храповик
`mcp_surface` в `tausik/gates.json`, который `tests/test_mcp_surface_ratchet.py`
пересчитывает на каждом прогоне и краснит при росте. Так сделано потому, что
предыдущая редакция этого числа сгнила ровно здесь: задача записала 117
инструментов и 44 501 байт в сессии #178, а к #229 стало 145 и 56 108 — рост на
24% и 26%, которого никто не заметил, пока число жило в тексте.

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

**Как это измерено, и чем измерить снова.** Заголовки не «выглядят полезными» —
их выигрыш посчитан воспроизводимым прибором `scripts/rag_retrieval_bench.py`
(`python scripts/rag_retrieval_bench.py [--limit N] [--json]`). Он выводит
запросы МЕХАНИЧЕСКИ из корпуса и выбирает их детерминированно, поэтому набор
нельзя подогнать под лестный результат, а два прогона по одному дереву задают
одни и те же вопросы. Меряет recall@K по КОНКРЕТНОМУ ЧАНКУ и держит два набора
сразу: `context` — случай, ради которого заголовок заведён, и `control` —
запросы из слов, уже лежащих в теле чанка, где заголовок помогать не должен и
особенно не должен вредить. Результат при n=115: recall@3 в наборе context
0.4870 → 0.8348, в control 0.5739 → 0.6435; регрессии нет ни на одном K.

### Поддержка разных сред разработки

Навыки, роли, стеки — общие для всех сред. MCP-серверы тоже: `harness/claude/mcp/` —
единственное каноническое дерево, и `copy_mcp` отдаёт его каждой среде, у которой нет
своего (сегодня — всем). Отдельная копия под IDE была бы зеркалом, обречённым разъехаться:
такое лежало в `harness/cursor/` и удалено в v1.7.0.
```
harness/
├── skills/           # 13 core auto-deployed + 20 в skills-official/ (opt-in через --include-official)
├── roles/            # 7 ролей (architect, developer, devops, qa, researcher, tech-writer, ui-ux)
├── stacks/           # Руководства по стекам
├── overrides/        # Переопределения для конкретных сред (claude/, cursor/, qwen/)
├── claude/mcp/       # MCP-серверы (project, codebase-rag) — канон для ВСЕХ сред
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
`renar_drift_schema`, `renar_drift_provenance`, `cross_model_parity`.

`cross_model_parity` спрашивает одно: не уехала ли возможность к одному хосту
молча. Он ЗАПУСКАЕТ настоящие генераторы механизмов в чистое дерево и сравнивает
хосты, делящие одну точку расширения: хуки claude против хуков qwen, плагины
против плагинов. Сравнения ПОПЕРЁК форм нет — спрашивать, «не потерял ли Claude
плагин OpenCode», значит задавать вопрос без смысла. Гейт НЕ требует одинакового
поведения: у Cursor точки расширения нет вовсе, и равняться там не на что.
Требуется, чтобы различие было НАЗВАНО, с причиной; объявление, которому больше
не соответствует ни одно живое различие, отвергается так же громко, как
необъявленное различие (решение #335). Срабатывает только на правках слоя хостов
(`bootstrap/`, `scripts/hooks/`, `harness/opencode/`) — гейт, спрашивающий про
кроссмодельность на каждой задаче, становится налогом, а налог выключают.

`bootstrap_drift` проверяет три звена цепи «правка → развёртывание → вступает в
силу»: `scripts/` против развёрнутого профиля, `harness/` против его
разворота, и развёрнутый профиль против **процесса, который из него работает**
(`running_source_drift`: снимок содержимого при старте процесса, сравнение на
task-done). Долгоживущий MCP-сервер, под которым перезаписали профиль,
исполняет старую копию; гейт отказывает закрытию и называет лекарство —
перезапустить сервер или закрыть через CLI, который есть свежий процесс.

**Гейт проверяется мутацией, а не тем, что он зелёный.** Зелёный прогон
доказывает лишь, что гейт не возразил, — не то, что он возразил бы хоть чему-то.
Правило держит `tests/test_gates_catch_their_violation.py`: каждый гейт из
`gate_registry.GATE_REGISTRY` стоит ровно в одной из двух таблиц. COVERED —
гейт прогоняется через собственный `impl_for` реестра на ОБОИХ концах:
настоящее нарушение, собранное под `tmp_path`, обязано вернуть failed, чистый
вход, собранный так же, — passed (один конец без другого пуст: гейт, красный на
любом входе, красную проверку проходит не хуже верного). EXCUSED — гейт,
который из синтетического дерева не завести (привязан к сервису, вердикт
внешнего инструмента, severity warn), с причиной и именами красного и зелёного
теста в модуле, который его гоняет; имена сверяются с AST того модуля. Список
закрыт: новый гейт без строки краснит ленту. Мутация не может остаться в дереве
по построению — всё строится под `tmp_path`, и запись за его пределы во время
прогона таблицы ловится перехватом `open`, `sqlite3.connect` и `subprocess`
(три канала, которыми билдеры пользуются), а не снимком `git status`, который
под xdist гонку с соседним воркером проигрывает.

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
| Handoff-контракт | `tausik task handoff <slug>` — детерминированный JSON {slug, goal, acceptance_criteria, scope, scope_exclude, model, skills}; trimmed профиль `WORKER_SKILLS` (без plan/explore). Оркестратор передаёт его в Agent tool; воркер возвращает обратно (round-trip identity). |
| Распознавание in-session | `task start` делегированной задачи показывает **worker mode** (operating contract) и подавляет orchestrator-only баннер модели. |
| Scope hard-gate | воркер ограничен scope — `scope_write_gate` блокирует edits вне `scope_paths`, а делегированная задача **без** scope блокируется до объявления (нет legacy fail-open для воркеров). |
| Summary-back | `tausik task summary-back <slug> "<summary>" [--gates …]` — воркер возвращает структурный результат (в `meta`, виден в `task show`), чтобы координатор взял его **без** транскрипта воркера. |

Состояние делегирования — CLI-first (без MCP, чтобы избежать doc-count drift) и
целиком в таблице `meta` (`delegation:<slug>`, `worker_summary:<slug>`).

## Hooks (anti-drift, см. [hooks.md](hooks.md))

Все hook-файлы в `scripts/hooks/` регистрируются через `bootstrap/bootstrap_generate.py` (Claude Code) и `bootstrap/bootstrap_qwen.py` (Qwen Code). Hook-скрипты non-blocking (exit 0), ошибки в stderr. Общие helper'ы в `scripts/hooks/_common.py`.


## Memory Aggregates

`service_knowledge_aggregates.py` содержит чистые функции для re-injection памяти:

- `build_memory_block(be, ...)` — компактный markdown (decisions + conventions + dead ends) ≤50 строк, вызывается из `/start`, `/checkpoint`, SessionStart hook
- `build_compact_memory_tail(be)` — построчная выжимка, встраиваемая в динамический блок CLAUDE.md
- `build_memory_compact(be, last_n)` — агрегация `task_logs`: фазы + топ-слова + топ-файлы

Обе выжимки спрашивают граф памяти через `memory_supersedes.live_head`: запись,
которую отменило ЖИВОЕ ребро `supersedes`, не печатается, её строка достаётся
следующей живой записи, а выжившая запись говорит `(supersedes #N)` на строке,
которую занимает в любом случае. Скрывает только это отношение и только пока
заменившая запись сама не заархивирована — иначе старая есть лучшее из
оставшегося знания. Нечитаемый граф не отменяет ничего: выжимка вырождается в
то, что печаталось до фильтра.

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
