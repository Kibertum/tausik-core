[English](/docs/cli) | **Русский**

# TAUSIK CLI — Справочник команд (v1.5)

Все команды запускаются через обёртку: `.tausik/tausik <команда> [подкоманда] [аргументы]`.
На Windows обёртка — `.tausik/tausik.cmd`. Тот же surface также доступен через MCP (`tausik_*` инструменты); см. `mcp.md`.

## Инициализация

```bash
init --name <slug>             # Инициализация проекта (создаёт .tausik/tausik.db)
init --template aidd [--force] # Скаффолдит AIDD-слои (idea.md/vision.md/conventions.md) в корень проекта.
                               #   Существующие файлы → 4-option prompt: overwrite / merge-append / skip / abort-all.
                               #   Default (Enter) = skip. `--force` перезаписывает без вопросов.
                               #   Неизвестное значение --template — exit ≠ 0, сообщение в stderr.
aidd autogen [--write] [--force] # Черновик vision.md, заполненный сигналами репо (имя+описание пакета,
                               #   заголовок/интро README, top-level каталоги, языки, тест-фреймворк).
                               #   По умолчанию печатает черновик в stdout (ничего не пишет); --write пишет в vision.md
                               #   через AIDD-prompt конфликтов (--force перезаписывает). Нет сигнала → placeholder,
                               #   никогда не падает. Только stdlib, без вызова LLM.
aidd validate                  # Проверяет claim'ы из conventions.md ## Code (язык/версия, lint/format, тест-фреймворк,
                               #   макс. размер файла) против реального состояния репо. Каждый claim →
                               #   ok / drift / unverifiable. Exit 1 при hard drift, 2 если нет conventions.md,
                               #   0 иначе. Пустой/непарсимый claim → unverifiable, никогда не падает. Только stdlib.
status [--compact]             # Обзор проекта + SENAR; --compact → JSON одной строкой
metrics                        # Метрики SENAR: Throughput, Lead Time, FPSR, DER, Dead End Rate, Cost per Task
metrics [--cost]               # С --cost: агрегат по usage_events по task_slug (то же что `metrics cost`)
metrics record-session         # Записать LLM usage (tokens/cost/tool/model) для текущей или явной сессии
metrics log-usage              # Одна строка manual в usage_events (--task-slug опционально; session_usage_metrics не трогаем)
metrics cost [--since ISO] [--until ISO]   # SUM токенов/cost и COUNT по task (slug NULL исключены)
metrics tokens [--since ISO] [--until ISO] [--task SLUG]    # Rollup токенов по task (sum input/output/cache tokens)
                                # Источник: PostToolUse hook scripts/hooks/posttool_usage.py пишет
                                #   одну usage_events строку на каждый tool call (source='posttool',
                                #   tool_name=<инструмент>) с привязкой к активной задаче.
                                # Прайсинг: scripts/cost_pricing.py — единый source of truth.
                                # Подробности: docs/{en,ru}/cost-telemetry.md.
doctor                         # Health check: venv + DB + MCP + skills + drift
```

## Иерархия

```bash
epic add <slug> <title> [--description TEXT]
epic list
epic done <slug>
epic delete <slug>             # CASCADE: удаляет все стори + задачи

story add <epic_slug> <slug> <title> [--description TEXT]
story list [--epic EPIC_SLUG]
story done <slug>
story delete <slug>            # CASCADE: удаляет все задачи
```

## Задачи

```bash
task add <title> [--story STORY_SLUG] [--slug SLUG] [--stack STACK]
                 [--complexity {simple,medium,complex}] [--goal TEXT] [--role ROLE]
                 [--defect-of PARENT_SLUG]
                 [--call-budget N] [--tier {trivial,light,moderate,substantial,deep}]
task quick <title> [--goal TEXT] [--role ROLE] [--stack STACK]
task next [--agent AGENT_ID]    # Выбрать следующую planning-задачу (по score)
task list [--status STATUS] [--story STORY] [--epic EPIC] [--role ROLE] [--stack STACK] [--limit N]
task show <slug>                # Полная информация: план, заметки, решения, defect_of, AC
task start <slug> [--force]     # planning → active (QG-0: требует goal + AC + negative scenario)
                                # --force байпасит session capacity gate (audit event + note)
task done <slug> --ac-verified [--no-knowledge] [--relevant-files FILE1 FILE2 ...] [--evidence "..."]
                                # QG-2: --ac-verified подтверждает проверку AC (требует evidence в notes
                                #       ИЛИ --evidence inline). v1.5 Verify-First Contract: heavy gates
                                #       (pytest, tsc, cargo, ...) НЕ запускаются здесь — они на отдельной
                                #       команде `verify`. task done проверяет наличие свежего green из
                                #       verify cache (10 min TTL, тот же files_hash) и закрывается за
                                #       миллисекунды. Если verify не запускался — блок с remediation.
                                #       Opt-out: .tausik/config.json → {"task_done":{"auto_verify":true}}
                                #       — старое поведение (heavy гейты inline). НЕТ --force.
task block <slug> [--reason TEXT]
task unblock <slug>             # blocked → active
task review <slug>              # active → review
task update <slug> [--title T] [--goal G] [--notes N] [--notes-overwrite] [--acceptance-criteria AC]
                  [--scope S] [--scope-exclude S] [--stack S] [--complexity C] [--role ROLE]
                  [--call-budget N] [--tier TIER]
                                # ⚠ --notes ЗАМЕНЯЕТ весь журнал (notes — append-only история,
                                #   пишется через `task log`). По умолчанию перезапись непустого
                                #   журнала ОТКЛОНЯЕТСЯ; чтобы дописать — `task log`, чтобы
                                #   намеренно заменить — добавь --notes-overwrite.
task delete <slug>
task delegate <slug>            # Orchestrator-worker: делегировать задачу complexity<=medium воркеру-сабагенту (рекоменд. модель + parent session; complex отвергается)
task undelegate <slug>          # Очистить делегирование
task handoff <slug>             # Печать детерминированного handoff-контракта воркера (JSON: goal/AC/scope/model/skills) для spawn через Agent tool
task summary-back <slug> "<summary>" [--changed F] [--gates S] [--ac-evidence E] [--follow-ups U]  # Воркер -> координатор структурный результат
task plan <slug> <шаг1> <шаг2> ...   # Задать шаги плана
task step <slug> <номер_шага>  # Отметить шаг N выполненным (нумерация с 1)
task log <slug> <сообщение>    # Таймстемп-заметка (crash-safe журнал)
task logs <slug> [--phase PHASE] # Чтение структурированных логов (planning/implementation/review/testing/done)
task reason-step <slug> <kind> <content>  # RENAR шаг рассуждения (kind: intent|premise|action|verification)
task replay <slug> [--output FILE]  # Хронологический таймлайн: logs + reasoning + events + verification
task move <slug> <new_story>   # Переместить задачу в другую стори
task claim <slug> <agent_id>   # Мульти-агент: занять задачу
task unclaim <slug>            # Освободить задачу
```

**Опциональные подсказки модели Claude:** если в `.tausik/config.json` задано `{"task_next":{"model_hint":true}}`, команды `task next` и `hud` выводят дополнительную строку с рекомендуемой моделью по сложности задачи (та же логика, что у `suggest-model`). Только opt-in; без ключа или при `false` поведение как раньше.

**Допустимые стеки (DEFAULT_STACKS, 25):** python, fastapi, django, flask, react, next, vue, nuxt, svelte, typescript, javascript, go, rust, java, kotlin, swift, flutter, laravel, php, blade, ansible, terraform, helm, kubernetes, docker. Custom-стеки добавляются через `.tausik/config.json` → `custom_stacks`.

**Tier ↔ call_budget map:** trivial ≤10, light ≤25, moderate ≤60, substantial ≤150, deep ≤400. Бюджеты >400 принимаются; tier label cap'ается на `deep`.

## Верификация

**v1.5 Verify-First Contract.** Тяжёлые гейты (pytest, tsc, cargo, phpstan, javac, js-test, terraform-validate, helm-lint, kubeval, hadolint, ansible-lint) живут на триггере `verify`, а не `task-done`. Это разделяет «закрытие задачи» (миллисекунды) от «полной проверки» (минуты на больших проектах). Результат `verify` кешируется в таблице `verification_runs` на 10 минут (TTL настраивается через `verify_cache_ttl_seconds` в config.json), и `task done` использует кеш для немедленного закрытия.

```bash
verify [--task SLUG] [--scope {lightweight,standard,high,critical,manual}]
                                # Запустить scoped verify-trigger gates ad-hoc; пишет в verify cache.
                                # С --task: гейты scoped по relevant_files задачи.
                                # Без --task: гейты с пустым file scope (full suite для pytest).
                                # Cache hit (тот же files_hash, < 10 мин) пропускает запуск.
                                # Security-sensitive файлы (auth/payment/hooks) обходят cache.
```

**Workflow с verify-first:**

```bash
.tausik/tausik task start my-task                    # QG-0
# … работа над кодом …
.tausik/tausik verify --task my-task                 # heavy: pytest etc.
.tausik/tausik task done my-task --ac-verified       # lightweight: cache lookup
```

**Opt-out на legacy (CI/inline):** установите в `.tausik/config.json`:

```json
{ "task_done": { "auto_verify": true } }
```

Тогда `task done` сам запустит verify-гейты внутри транзакции — старое поведение v1.3. Полезно для CI-окружений, где один длинный шаг лучше двух.

**Pytest fast lane (v1.5.x).** Дефолтная конфигурация pytest (`pyproject.toml` → `[tool.pytest.ini_options]` → `addopts = "-m 'not slow'"`) пропускает тесты, помеченные `@pytest.mark.slow` (subprocess-тяжёлый bootstrap, MCP integration, e2e, stress). Это сокращает чистый прогон `tausik verify` на TAUSIK с ~12 минут до ~1.5 минут. Три escape-hatch'а, когда нужна полная батарея:

```bash
# 1. Прямой pytest, override addopts
pytest --override-ini='addopts=' tests/

# 2. Только marker-фильтр (перекрывает наследуемый -m 'not slow')
pytest -m '' tests/                        # все тесты
pytest -m 'slow' tests/                    # только slow (CI nightly)

# 3. Через verify-гейт — выставите env var до вызова tausik
TAUSIK_VERIFY_FULL=1 .tausik/tausik verify --task my-task
```

Чтобы пометить новый тест slow: file-level `pytestmark = pytest.mark.slow` (предпочтительно для целых файлов) или per-test `@pytest.mark.slow`. Применяй когда тест запускает subprocess'ы, ходит в сеть/MCP или спит > 200 ms — всё, что выпадает за бюджет интерактивного verify в < 60 с.

**Терминология:** [Глоссарий verify / QG](verify-glossary.md) — opt-out, bypass и тестовый shim.

## Шлюзы качества

```bash
gates status                    # Все gates и их конфигурация
gates list                      # Список gates с состоянием вкл/выкл
gates enable <name>             # Включить gate
gates disable <name>            # Выключить gate
```

## RENAR drift-детекторы (§3.11)

RENAR §3.11 определяет 8 классов дрифта. Реализованы 2 (рекомендация R4 аудита),
оба в **warning-режиме** — находки не блокируют, агент читает листинг и реагирует.

```bash
drift                          # Запустить все реализованные детекторы
drift --detector schema        # Только drift-1 (схема артефактов)
drift --detector provenance    # Только drift-7 (провенанс TC↔требование)
```

- **drift-1 (schema)** — ре-валидация SPEC/ADAPT против closed-lists + cross-field
  инвариантов, которые DB CHECK выразить не может: `delta_n ↔ parent_adapt`
  (delta_n>0 без parent_adapt / delta_n=0 с parent_adapt), `signed ↔ двойная
  подпись` (§7.5),
  пустая version. Ловит прямые правки БД и пробелы миграций.
- **drift-7 (TC↔requirement provenance)** — у TAUSIK нет first-class TC; единица
  верификации — задача (её acceptance_criteria = «TC»), связанная со SPEC
  (требование) через `task_specs`. Два сигнала: `stale-verification` (done-задача,
  но SPEC отредактирован после связывания → верификация устарела) и
  `deprecated-requirement` (незавершённая задача на deprecated-SPEC).

Также подключены как gates `renar_drift_schema` / `renar_drift_provenance`
(severity=warn, trigger=task-done). Остальные 6 классов — вне scope.

## RENAR conformance (§14.4)

```bash
renar conformance              # Сгенерировать RENAR-CONFORMANCE.yaml (в stdout)
renar conformance --write      # Записать в RENAR-CONFORMANCE.yaml в корне проекта
renar conformance --assessor <id>
renar export [--out DIR] [--check]  # Сериализовать specs+adapts+conformance в дерево renar/; --check — CI drift-гейт (exit 1 при stale)
```

Self-assessment-манифест со всеми mandatory-полями §14.4.2. Уровень RENAR-1..5
вычисляется **честно из live-БД** (§14.4.3), не декларативно: нарушение любой
mandatory clause → `pre_adoption: true` + `level: null` (паттерн kai, аудит
§0.2.3). Секция `assessment-evidence` показывает raw-counts + per-signal met/unmet
и где именно заблокирован уровень — агенту видно, что нужно до следующего уровня.
Машинные клаузы (closed-lists, V1–V6, QG-0/QG-2, schema-validation hook = наш
drift-1) подтверждаются capability; data-клаузы (`adapt-per-tz`) — только при
наличии артефактов.

## Стеки

```bash
stack info <stack>              # Резолвленный стек: gates per language + override info
stack list                      # Список встроенных + custom-стеков
stack export <stack>            # Печать резолвленного декларации как JSON
stack diff <stack>              # Diff между встроенным и user override
stack reset <stack>             # Удалить user override в .tausik/stacks/<stack>/
stack lint                      # Валидировать user-override stack.json против схемы
stack scaffold <name>           # Создать .tausik/stacks/<name>/{stack.json,guide.md} skeleton
```

## Роли

```bash
role list
role show <slug>
role create <slug> <title> [--description TEXT] [--extends BASE_ROLE]
role update <slug> [--title T] [--description D]
role delete <slug>
role seed                       # Bootstrap из harness/roles/*.md и использования в задачах
```

Хранение ролей гибридное: SQLite-метаданные + markdown-профиль `harness/roles/{role}.md`. Роли в задачах остаются свободным текстом (`--role developer/architect/qa/...`).

## Сессии

```bash
session start                   # Начать новую сессию (возвращает ID)
session end [--summary TEXT]    # Завершить активную сессию
session current                 # Показать активную сессию
session list [--limit N]        # Последние сессии (default: 10)
session handoff <json_data>     # Сохранить данные передачи для следующей сессии
session last-handoff            # Получить передачу предыдущей сессии
session extend [--minutes N]    # Продлить active-time лимит сверх 180 мин (SENAR Rule 9.2)
session recompute               # Retro: сравнить wall-clock vs active (gap-based) минуты
```

Лимит сессии — 180 мин **active** time (gap-based, паузится после 10 мин idle), не wall clock. Threshold настраивается в `.tausik/config.json` → `session_idle_threshold_minutes`. См. `session-active-time.md`.
На `session end` TAUSIK также делает best-effort запись usage через `scripts/hooks/session_metrics.py --auto --record` (поддержаны transcript roots и Claude, и Cursor).

## Знания

```bash
decide <text> [--task SLUG] [--rationale TEXT]
decisions [--limit N]           # Список решений (default: 20)

memory add <type> <title> <content> [--tags T1 T2 ...] [--task SLUG]
memory list [--type TYPE] [--limit N]
memory search <query>           # FTS5 полнотекстовый поиск
memory show <id>
memory delete <id>

# Графовая память (Graphiti-inspired)
memory link <source_type> <source_id> <target_type> <target_id> <relation>
            [--confidence 0.0-1.0] [--created-by AGENT]
memory unlink <edge_id> [--replacement EDGE_ID]   # Soft-invalidate (никогда не удаляет)
memory related <node_type> <node_id> [--hops N] [--include-invalid]
memory graph [--type {memory,decision}] [--id N]
             [--relation {supersedes,caused_by,relates_to,contradicts}]
             [--include-invalid] [--limit N]

# Агрегаторы
memory block [--max-decisions N] [--max-conventions N] [--max-deadends N] [--max-lines N]
memory compact [--last N]

# Гигиена памяти (v1.5)
memory archive --before <duration> [--confirm]    # Soft-archive памяти старше duration
                                                   # (90d / 12w / 2m / 1y). По умолчанию dry-run;
                                                   # --confirm проставляет archived_at, идемпотентно.
memory dedupe [--threshold 0.85] [--limit 200]     # Список near-duplicate пар выше порога
                                                   # similarity (difflib.SequenceMatcher.ratio()
                                                   # по title || content). Read-only.
```

**Типы памяти:** pattern, gotcha, convention, context, dead_end
**Типы узлов графа:** memory, decision
**Типы связей:** supersedes, caused_by, relates_to, contradicts

## Документирование тупиков (SENAR Rule 9.4)

```bash
dead-end <approach> <reason> [--task SLUG] [--tags T1 T2 ...]
# Документирует неудачный подход с причиной. Сохраняется как memory тип dead_end.
```

## Исследования (SENAR Section 5.1)

```bash
explore start <title> [--time-limit MINUTES]    # Начать исследование (default: 30 мин)
explore end [--summary TEXT] [--create-task]    # Завершить (--create-task создаёт задачу)
explore current                                 # Показать активное исследование
```

## Периодический аудит (SENAR Rule 9.5)

```bash
audit check                     # Показать, просрочен ли периодический аудит
audit mark                      # Отметить аудит выполненным
audit vendors [--json]          # Аудит клонированных vendor skill repos (read-only): классифицирует
                                # как 'installed' (в installed_skills config) или 'vendored_unused'
                                # (кандидат на `skill repo remove`). Никогда не удаляет.
audit research [--min-age-days N] [--json]
                                # Аудит docs/{en,ru}/research/ на устаревшие непривязанные файлы
                                # (по умолчанию >30 дней, без ссылок в tests/scripts/CHANGELOG/README).
                                # Read-only — показывает кандидатов на перенос в docs/_archive/research/.
```

## Ревью (SENAR Rule 10.15) — v1.5

Учёт L1/L2/L3 ревью-прогонов и метрика **ADR** (Adversarial Defect Rate).

```bash
review record --task <slug> --type {L1|L2|L3} \
              [--critical N] [--warnings N] [--notes "..."]
review list   [--task <slug>] [--type {L1|L2|L3}] [--limit N] [--json]
review metrics                  # ADR = critical_findings / L3_reviewed_tasks * 100
```

Скилл `/review` сам вызывает `review record --type L3` (он запускает 6 adversarial-агентов в отдельном контексте). В `tausik metrics` появляется блок `Adversarial Review`, как только есть хотя бы один L3-прогон.

## Мульти-агент

```bash
team                            # Задачи сгруппированные по агентам (claimed_by)
```

## Навыки

```bash
skill list                      # Skills: active, vendored, available из configured repos
skill install <name>            # Установить skill из configured репо (clone + copy + activate)
skill uninstall <name>          # Удалить skill полностью (deactivate + drop из config)
skill activate <name>           # Активировать vendored skill (copy из vendor/ в .claude/skills/)
skill deactivate <name>         # Деактивировать активный skill (remove из .claude/skills/)
skill repo add <url> [--force]  # Add TAUSIK skill repo; --force для URL кроме github.com/Kibertum/tausik-skills
skill repo remove <name>        # Удалить configured skill repo
skill repo list                 # Список configured repos и их skills
skill catalog [<repo>] [--json] # Discovery: name/category/repo/description по cloned repos

# Профили и бандлы (v1.5)
skill rebuild [--force]         # Пересобрать SKILL.md варианты под активный (ide, model) профиль;
                                # идемпотентно (sha256-кэш пропускает не изменённые файлы).
skill bundle list               # 6 логических бандлов из skills-official/bundles.json
                                # (integrations, data-formats, quality-pro, automation, workflow-helpers,
                                # ru-locale) + счётчики skills.
skill bundle show <name>        # Содержимое одного бандла (skill-имена + описания).
skill bundle install <name>     # Установить каждый skill из бандла (per-skill ошибка не останавливает).
skill bundle uninstall <name>   # Удалить каждый skill из бандла.
```

Negative-сценарии (unknown skill, untrusted repo URL, missing skill)
печатают friendly `Error: ...` в stderr и выходят с кодом `1`. Python
traceback не показывается (v1.5: `SkillManagerError` ловится наравне
с `ServiceError` в `main()`).

## Shared Brain (cross-project)

```bash
brain init                      # Инициализация: 4 Notion DB + конфиг
brain status                    # Mirror freshness, sync state, registered проекты (v1.5: добавлено `stale: N min`)
brain sync [--category C] [--json]  # Подтянуть обновления из Notion в локальное зеркало (v1.5)
brain move <source_id> --to-brain --kind {decision,pattern,gotcha} [--keep-source]
brain move <notion_page_id> --to-local --category {decisions,patterns,gotchas,web_cache} [--force]
```

## Поиск и навигация

```bash
roadmap [--include-done]        # Полное дерево epic → story → task
search <query> [--scope {all,tasks,memory,decisions}]
```

## Гигиена проекта (v1.5)

Хелперы для гигиены. По умолчанию `archive` показывает кандидатов; `--confirm`
проставляет `archived_at` на подходящих строках (идемпотентно — безопасно
запускать повторно). Архивированные строки остаются queryable (видны
`task_show`, FTS, metrics), `task list` их прячет, если не передан
`--include-archived`.

```bash
hygiene archive                 # Dry-run: список done-задач старше task_archive.done_age_days
                                # (no-op если task_archive.enabled false / отсутствует).
                                # Active / blocked / planning / review задачи
                                # НЕ включаются ни при каких настройках.
hygiene archive --confirm       # Write: проставляет archived_at (UTC ISO8601) на каждого кандидата.
                                # НЕ обходит task_archive.enabled=false.
```

Спека: `docs/ru/task-archive-spec.md`. Правила исключений и audit-скрипты
для разработчика (orphan files, stale docs, unused Python, pytest dedupe)
описаны в `docs/ru/dev-doc-checks.md`.

## Пакетное выполнение

```bash
run <plan-file.md>              # Парсинг и показ сводки batch-run плана
```

Планы — markdown с нумерованными задачами, целями и списками файлов. Используйте `/run plan.md` в интерактивной сессии для автономного выполнения.

## Извлечение документов

```bash
doc extract <path>              # Конвертировать DOCX/PPTX/XLSX/HTML/EPUB/PDF в markdown через markitdown
```

Opt-in: требует `markitdown` и Python ≥3.11.

## События (Журнал аудита)

```bash
events [--entity {task,epic,story}] [--id SLUG] [--limit N]
```

## Сниппеты / детекция клонов (v15-snippet)

```bash
snippet detect [--path X] [--threshold N]  # AST-детекция клонов кода: нормализует
                                           #   идентификаторы/литералы → placeholder,
                                           #   хэширует поддеревья def/class, кластеризует
                                           #   ≥2 совпадения и пишет в таблицу snippets
                                           #   (taxonomy_kind='clone'). --threshold = мин.
                                           #   число строк кандидата (по умолч. 10).
                                           #   Идемпотентно (dedup по hash).
```

## Обслуживание

```bash
update-claudemd [--claudemd PATH] [--dry-run]  # Обновить секцию <!-- DYNAMIC --> в CLAUDE.md И в соседнем AGENTS.md (v1.5: --dry-run печатает diff и возвращает exit 1 при drift). Файл без маркера пропускается с notice.
fts optimize                          # Оптимизировать FTS5 индексы
hud                                   # Live dashboard: задача + сессия + gates + логи
suggest-model [complexity]            # Рекомендация Claude-модели: simple→Haiku, medium→Sonnet, complex→Opus
```

## Константы

| Концепция | Значения |
|-----------|----------|
| Статусы задач | `planning → active → blocked ↔ active → review → done` |
| Формат slug | `^[a-z0-9][a-z0-9-]*$` (макс. 64 символа) |
| Сложность → SP | simple=1, medium=3, complex=8 |
| Tiers (call calls) | trivial ≤10, light ≤25, moderate ≤60, substantial ≤150, deep ≤400 |
| Типы памяти | pattern, gotcha, convention, context, dead_end |
| Роли | Свободный текст (без enum); реестр в `harness/roles/{slug}.md` |
| SENAR gates | QG-0 (Context Gate на `task start`), QG-2 (Implementation Gate на `task done`) |
| Лимит сессии | 180 мин **active** по умолчанию (настраивается: `session_max_minutes`, idle threshold: `session_idle_threshold_minutes`) |
