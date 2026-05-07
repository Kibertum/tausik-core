[English](README.md) | **Русский**

# TAUSIK

**Фреймворк для AI-разработки — планируй, создавай, выпускай с контролем качества.**

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB.svg)](https://python.org)
[![Tests](https://github.com/Kibertum/tausik-core/actions/workflows/tests.yml/badge.svg)](https://github.com/Kibertum/tausik-core/actions/workflows/tests.yml)
[![3362 tests](https://img.shields.io/badge/tests-3362%20passed-brightgreen.svg)](#dogfooding-tausik-создан-с-помощью-себя)
[![Zero deps](https://img.shields.io/badge/dependencies-0-brightgreen.svg)](#что-внутри)

> ⚠️ **v1.4 — околостабильный pre-2.0 релиз.** Это последний минорный релиз
> 1.x перед мажорным переходом к **2.0**. v1.4 несёт очень большой объём
> изменений (B+C polish phases — verify-first контракт, brain artifact pipeline,
> audit suite, skill bundles, two-axis variants, per-task cost/token бюджеты) —
> возможен рассинхрон в документации и редкие нестабильности на edge-cases.
> Ядро покрыто 3362 тестами и используется на dogfood'е каждый день; если
> наткнётесь на расхождение docs ↔ behaviour — заведите issue, постараемся
> доехать до 2.0 без regression'ов.

**TAUSIK — фреймворк контроля качества для AI-агентов разработки** —
Claude Code, Cursor, VSCode Claude Extension, Qwen Code, Windsurf.
Он навязывает дисциплину senior-инженера: планировать перед кодом,
верифицировать перед заявкой о готовности, помнить решения между
сессиями и никогда молча не пропускать тесты/линтер.

**Это как Git для AI-разработки.** Сессии, задачи, решения и тупики
хранятся в локальной SQLite. Quality gates физически блокируют агента
в двух точках — старт (нет цели — заблокировано) и финиш (нет
доказательств — заблокировано) — так что «постараюсь не забыть тесты
в следующий раз» перестаёт быть сценарием.

Три сообщения. Полный инженерный цикл. Quality gates, которые агент не может обойти.

> Работает в Claude Code, VSCode Claude Extension, Cursor, Qwen Code (GigaCode), Windsurf.

## Попробуйте прямо сейчас

Скажите вашему ИИ-агенту:

```
Добавь https://github.com/Kibertum/tausik-core как git submodule в .tausik-lib,
запусти python .tausik-lib/bootstrap/bootstrap.py --init,
добавь .tausik/ в .gitignore
```

Агент выполнит все три шага. Перезапустите IDE после — готово.

Дальше — три сообщения:

```
начинай работу
```
```
исправь баг — кнопка не работает на мобильной версии
```
```
готово, отправляй
```

Всё. Агент откроет сессию, создаст задачу с критериями приёмки, напишет код, запустит тесты и код-ревью, проверит каждый критерий с доказательствами, закоммитит и предложит запушить. Полный инженерный цикл — вы просто описываете, что хотите.

## Token Efficiency

В v1.4.x по default разворачивается меньше скиллов — только те, что реально нужны каждому проекту TAUSIK. Меньше system-reminder список = ниже стоимость каждого хода без потери функциональности.

| Компонент | До v1.4.x | После v1.4.x | Экономия |
|---|---|---|---|
| Список skills в `system-reminder` | 38 skills (~1,520 ток/ход) | 12 + 1 conditional (~480 ток/ход) | **−1,040 ток/ход (−68%)** |

Как это устроено:

- **12 core-скиллов** разворачиваются автоматически: `/start`, `/end`, `/checkpoint`, `/plan`, `/task`, `/ship`, `/commit`, `/review`, `/test`, `/debug`, `/explore`, `/interview`.
- **`/brain` условно** — появляется только после `tausik brain init` (когда заполнен `brain.notion_db_ids`). Проекты, не использующие shared brain, не платят его ~600 ток/ход.
- **Extras по запросу** — перезапусти `python .tausik-lib/bootstrap/bootstrap.py --include-official` (alias `--include-vendor`) для полного набора 38 skills, либо `tausik skill install <name>` для одного. Bundle CLI (`tausik skill bundle install`) появится в следующем релизе.
- **`tausik status` предупреждает**, если развёрнутый skill-set расходится с активным флагом (например, 38 развёрнуто без `--include-official`) — чтобы ты заметил случайный bloat.

## Функционал

| Категория | Что делает | Как использовать |
|---|---|---|
| **Lifecycle** | Иерархия Epic → Story → Task с state machine (planning → active → review → done) | `/plan`, `/task`, `/start`, `/end` |
| **Quality Gates** | QG-0 блокирует `task start` без goal+AC. QG-2 блокирует `task done` без verify-cache hit. Scoped по задаче — только нужные тесты | Авто на `task start` / `task done` |
| **Verify-First Contract** *(v1.4)* | Тяжёлые gates (pytest, tsc, cargo, phpstan…) на trigger `verify`, отдельно от `task done`. Закрытие задачи — миллисекунды. Envelope timeout 60s — нет молчаливых зависаний | `tausik verify --task X` затем `task done X` |
| **Память проекта** | Паттерны, gotchas, конвенции, dead ends, решения в SQLite+FTS5. Re-инжектятся при старте сессии | `/brain`, `tausik memory add`, авто на `/start` |
| **Verification Engine** | 25 stack-aware проверок (pytest, ruff, mypy, tsc, eslint, cargo, go-vet, phpstan, helm-lint, hadolint…). Scoped по relevant_files. Cache на 10 мин | Стек авто-определяется bootstrap |
| **Real-time хуки** | 19 хуков: task gate (нет кода без задачи), bash firewall, push gate, auto-format, drift detection (SessionStart/UserPromptSubmit/Stop), memory pre/post audit | Авто в Claude Code и Qwen Code |
| **Метрики** | Throughput, First-Pass Success Rate, Defect Escape Rate, Lead Time, Dead End Rate, Cost-per-task | `tausik metrics`, `tausik metrics --cost` |
| **Multi-IDE** | Те же MCP-инструменты (100) + skills во всех хостах | VSCode/Claude, Cursor, Qwen Code, Windsurf, Codex, CLI |
| **Skill Ecosystem** | 12 core skills auto-deployed (+ `/brain` если настроен Notion) — см. [Token Efficiency](#token-efficiency). 25+ official/vendor skills opt-in через `--include-official` или `tausik skill install`. Multi-model профили через `variants/<model>.md` *(v1.4)* | `tausik skill install <name>` |
| **Cross-project Brain** *(опционально)* | Notion-mirror решений / паттернов / gotchas / web-кэша между проектами. v1.4 добавляет artifact pipeline: propose → audit (scrubbing секретов) → publish, со stack-aware bm25 ранжированием. Приватность через SHA256-хеши имён | `/brain` query, `tausik brain init`, `tausik brain propose-artifact`, `tausik brain publish` |
| **Гигиена & Audit** *(v1.4)* | `tausik hygiene archive` списком показывает старые done-задачи (dry-run). Audit-скрипты: `audit_orphan_files`, `audit_stale_docs`, `audit_unused_python`, `audit_pytest_dedupe` — инвентаризация мёртвого кода, висячих доков, скопированных тестов | `tausik hygiene archive`, `python scripts/audit_*.py` |
| **Task Archive** *(v1.4)* | Read-only спека архивирования done-задач старше N дней. Active / blocked / planning никогда не архивируются; `--confirm` зарезервирован под будущие деструктивные операции | `tausik hygiene archive` |
| **Batch Execution** | Автономное выполнение многозадачных markdown-планов | `/run plan.md` |
| **Сессии** | Active-time tracking (gap-based, 10-мин idle threshold), лимит 180 мин, capacity gate (200 tool calls), handoff persistence | Авто на `/start`, `/end`, `/checkpoint` |

## Что вы получаете

| Без TAUSIK | С TAUSIK |
|---|---|
| Агент сразу пишет код | Обязан определить цель и критерии приёмки |
| Заявляет «готово» без доказательств | Закрытие заблокировано, пока каждый критерий не подтверждён |
| Контекст теряется между сессиями | Решения, закономерности и тупики сохраняются |
| Одна ошибка повторяется 3 раза | Неудачные подходы записаны — агент видит, что не сработало |
| Ни тестов, ни линтера | 25 проверок для вашего стека запускаются автоматически |
| Нет видимости процесса | 6 метрик считаются автоматически — производительность, дефекты, скорость |

**Ключевое отличие:** quality gates TAUSIK — это _принудительный контроль_. Агент физически не может пропустить шаги — никаких промптов, надежд и «пожалуйста, не забудь запустить тесты».

## Ручная установка

Если предпочитаете настроить вручную:

```bash
cd your-project
git submodule add https://github.com/Kibertum/tausik-core .tausik-lib
python .tausik-lib/bootstrap/bootstrap.py --init
```

Bootstrap автоматически определяет стек и включает подходящие проверки. Имя проекта берётся из названия папки.

> После bootstrap перезапустите IDE, чтобы MCP-серверы загрузились. Без перезапуска агент будет работать через CLI.

**[Подробный быстрый старт ->](docs/ru/quickstart.md)**

## Как это работает

**Планирование перед кодом.** `/plan` начинает с интервью — агент задаёт уточняющие вопросы о поведении, граничных случаях, ограничениях. Затем создаёт задачи с критериями приёмки. Никакого кода, пока цель не определена.

**Выпуск с уверенностью.** `/ship` запускает код-ревью (5 параллельных агентов), тесты, проверяет каждый критерий приёмки, коммитит и предлагает обновить документацию. Одна команда — полный конвейер качества.

**Помнит всё.** Решения, закономерности, соглашения и неудачные подходы хранятся в локальной SQLite-базе с полнотекстовым поиском. Новая сессия? Агент продолжает с того места, где остановился.

**Контроль, а не рекомендации.** Quality gates блокируют агента в двух точках: QG-0 (нельзя начать без цели и критериев) и QG-2 (нельзя закрыть без доказательств и пройденных тестов). Хуки блокируют редактирование кода без задачи и опасные shell-команды в реальном времени.

## Продвинутые возможности

- **Anti-drift защита** — хуки SessionStart / UserPromptSubmit / Stop детектят coding intent без активной задачи, re-инжектят Memory Block на `/start`, аудитят `task_done` evidence (пути файлов, ✓ маркеры, test counts, lint status). Adversarial critic — 6-й параллельный агент `/review` находит слабости, которые упустили другие. [Детали →](docs/ru/hooks.md)
- **Дисциплина памяти** — TAUSIK memory (`.tausik/tausik.db`, project-scoped) и Claude auto-memory (`~/.claude/`, cross-project) разделены через PreToolUse блок + PostToolUse audit. Утечки проектных следов в cross-project память блокируются у источника. [Детали →](docs/ru/memory-merge-guidelines.md)
- **Shared Brain** *(опционально)* — второй слой знаний на Notion для cross-project паттернов + gotchas. Локальное SQLite FTS5 зеркало, bm25-ранжированный поиск, SHA256-хеши имён проектов. Stdlib-only Notion client. [Детали →](docs/ru/shared-brain.md)
- **Brain artifact pipeline** *(v1.4)* — формальная таксономия (artifact / pattern / snippet) + JSON Schema валидатор + propose→audit→publish flow со scrubbing'ом секретов и явным `confirm_high_risk` gate. Stack-aware ранжирование в `brain_search`. [Таксономия →](docs/ru/brain-artifact-taxonomy.md) · [Search ranking →](docs/ru/brain-search-ranking.md)
- **Надёжность pipeline** *(v1.4)* — Verify-First contract отделяет heavy gates от `task done`. Envelope timeout (60с default), relaxed cache для manual-scope verify, relevant_files fallback из verify-row. Никаких молчаливых зависаний. [Детали →](docs/ru/verify-glossary.md)
- **Audit-набор** *(v1.4)* — orphan-file / stale-doc / unused-python / pytest-dedupe скрипты находят мёртвый код и копипасту в долгоживущих проектах. `tausik hygiene archive` + read-only спека архива задач. CI doc-constants drift check. [Детали →](docs/ru/dev-doc-checks.md)
- **Interview & live dashboard** — `/interview` запускает Сократический Q&A перед complex задачей. `tausik hud` показывает live dashboard на один экран. `tausik suggest-model` маршрутизирует Haiku/Sonnet/Opus по сложности задачи. Webhook-уведомления в Slack/Discord/Telegram.

## Что внутри

- **12 core навыков + `/brain` conditional** (auto-deployed) — `/start`, `/end`, `/checkpoint`, `/plan`, `/task`, `/ship`, `/commit`, `/review`, `/test`, `/debug`, `/explore`, `/interview` всегда; `/brain` только после `tausik brain init`. Плюс **25+ official/vendor навыков** (`/audit`, `/zero-defect`, `/markitdown`, `/docs`, `/security`, `/onboard`, …) opt-in через `bootstrap --include-official` или `tausik skill install <name>`.
- **103 MCP-инструмента** (96 project + 7 brain) — полный программный доступ к базе проекта
- **25 проверок качества** — pytest, ruff, tsc, eslint, cargo check, go vet и другие для вашего стека
- **6 автоматических метрик** — производительность, FPSR, уровень дефектов, активное время сессий
- **Проектная память** — SQLite + FTS5, граф связей, трекинг тупиков, Memory Block re-injection
- **Cross-project Brain** — Notion-mirror для обмена знаний между проектами (опционально)
- **19 Claude Code hooks** — task gate, bash firewall, push gate, auto-format, activity event, SessionStart, UserPromptSubmit, Stop × 2, PostToolUse verify, memory pre/post audit, brain proactive lookup и кэш WebFetch, notify, session metrics
- **Пакетное выполнение** — `/run plan.md` автономно выполняет многозадачные планы
- **Ноль зависимостей** — Python 3.11+ stdlib; MCP-deps в изолированном `.tausik/venv/`

## Поддерживаемые среды разработки

**Политика валидации:** TAUSIK проектируется как мульти-IDE фреймворк, но статус тестирования указываем явно.
Официально прогнано end-to-end сейчас: **VSCode + Claude Extension** и **Cursor**.
Остальные среды поддерживаются архитектурно, но помечаются как expected/partial до расширения матрицы автотестов.

| Среда | Инструменты | Навыки | Хуки | Правила | Статус валидации |
|-------|-------------|--------|------|---------|------------------|
| VSCode + Claude Extension | 103 инстр. | 12 core + brain conditional, 25+ on demand | 19 хуков (task gate, bash firewall, push gate, auto-format, activity, memory guards, brain auto-cache, ...) | CLAUDE.md + .mcp.json | **Официально протестировано** |
| Cursor | 103 инстр. | 12 core + brain conditional, 25+ on demand | — | .cursorrules + .cursor/mcp.json | **Официально протестировано** |
| Claude Code (CLI) | 103 инстр. | 12 core + brain conditional, 25+ on demand | 19 хуков | CLAUDE.md + .mcp.json | Ожидается (частичная матрица) |
| Qwen Code | 103 инстр. | 12 core + brain conditional, 25+ on demand | 19 хуков (как у Claude) | QWEN.md + .mcp.json | Ожидается (частичная матрица) |
| Windsurf | 103 инстр. | 12 core + brain conditional, 25+ on demand | — | .windsurfrules + .mcp.json | Ожидается (частичная матрица) |
| Codex / OpenCode-подобные агенты | MCP + rules-driven при поддержке хоста | Зависит от хоста | Специфично для хоста | AGENTS.md | Ожидается (ручная валидация) |

**Хуки** блокируют редактирование кода без задачи, опасные shell-команды и прямой push в main — в реальном времени. Доступны в Claude Code и Qwen Code. Cursor и Windsurf получают те же MCP-инструменты и навыки, с quality gates на `task start` и `task done`.

## Dogfooding: TAUSIK создан с помощью себя

TAUSIK создавался с помощью самого себя. Реальные цифры:

| Метрика | Значение |
|---|---|
| Задач завершено | 526 |
| Сессий | 39 |
| Производительность | ~13 задач/сессию |
| Тестов | 2590 |
| Зависимостей | 0 в ядре |

Каждая новая возможность, каждая переработка, каждое исправление прошли через те же quality gates, которые поставляются с фреймворком.

## Методология

TAUSIK реализует [SENAR](https://senar.tech) ([GitHub](https://github.com/Kibertum/SENAR)) — открытый инженерный стандарт для разработки с помощью ИИ. Quality gates, управление сессиями, метрики, чеклисты верификации — всё определено в SENAR.

**[Подробнее о SENAR ->](docs/ru/senar.md)**

## Документация

| Документ | Описание |
|----------|----------|
| **[Быстрый старт](docs/ru/quickstart.md)** | Первое знакомство — 10-15 минут |
| **[Что такое SENAR?](docs/ru/senar.md)** | Методология за TAUSIK |
| **[Рабочий процесс](docs/ru/workflow.md)** | Типичный день с TAUSIK |
| **[Навыки](docs/ru/skills.md)** | 12 core + brain conditional, 25+ official skills opt-in (38 total) |
| **[Хуки](docs/ru/hooks.md)** | Контроль в реальном времени |
| **[CLI-команды](docs/ru/cli.md)** | Справочник команд терминала |
| **[MCP-инструменты](docs/ru/mcp.md)** | 103 инструмента для ИИ-агента |
| **[Архитектура](docs/ru/architecture.md)** | Как устроен фреймворк внутри |

**[Полная документация ->](docs/README.md)**

## Лицензия

[Apache License 2.0](LICENSE)
