[English](../en/cli-admin.md) | **Русский**

# CLI: обслуживание проекта

<!-- doc-map: reader=user; zone=core-surface -->

Состояние, стеки, роли, навыки, гигиена, константы. Часть справочника команд. Начало и рабочий набор — [cli.md](cli.md).
## Состояние в git (state / sync)

Проекция durable-состояния БД (`.tausik/tausik.db`) в git-native дерево `tausik/` —
одно детерминированное .md-файл на сущность (задачи, task_logs, эпики, стори,
решения, память, рёбра памяти). БД — рабочий кэш; дерево `tausik/` — канонический,
привязанный к ветке источник истины. Round-trip: `export` (БД → файлы), `import`
(файлы → БД, git выигрывает при расхождении). `sync` — короткий алиас `state import`,
команда после `git pull` / `git checkout`.

```bash
state export [--out DIR] [--check]   # Сериализовать БД → дерево tausik/ (по файлу на сущность).
                                     # --check: exit 1 если дерево устарело против live-БД (CI-гейт,
                                     # тот же контракт, что renar export --check).
state import [--out DIR] [--dry-run] # Пересобрать кэш БД из дерева tausik/ (идемпотентная дельта).
                                     # --dry-run: показать план add/update/journal/edge без записи в БД.
sync [--out DIR] [--dry-run]         # Алиас `state import`. Запусти после git pull/checkout.
```

Пример: `.tausik/tausik state export` перед коммитом ветки; `.tausik/tausik sync`
сразу после `git pull`, чтобы локальный кэш БД догнал дерево. Автоматизация
round-trip (экспорт при durable-записи, детекция расхождения при старте сессии)
гейтится конфигом `state.auto_export`.

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
                                # НЕ уменьшает дерево: экспортёр выбирает FROM tasks
                                # без фильтра archived_at, файл проекции остаётся.

hygiene unarchive --slug S      # Dry-run: что раскроет снятие archived_at у S.
hygiene unarchive --archived-within DAYS
                                # Выбор по свежести — откат только что применённой партии.
                                # НЕ «старше»: самые старые архивные строки — это те,
                                # которые должны остаться скрытыми.
                                # Селектор ОБЯЗАТЕЛЕН; голый unarchive отклоняется.
      ... --confirm             # Write: снимает только archived_at. status и completed_at
                                # не трогаются — строка раскрывается, а не открывается заново.
                                # Работает при task_archive.enabled=false: конфиг управляет
                                # скрытием, а не восстановлением.
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

## Порождённые документы

```bash
doc constants [--check]         # docs/_generated/constants.json из pyproject + счётчиков MCP
doc roadmap [--check]           # ROADMAP.md из живой БД; --check — exit 1, если карта протухла
```

`doc roadmap` перевыпускает дорожную карту релиза в корне проекта. Состав
релиза берётся из решений владельца (последнее решение, называющее истории
релиза), счётчики — из живой БД; в файле не пишется руками ничего. Закрытие
задачи двигает счётчики, поэтому перевыпуск делается **после `task done` и
перед коммитом** — иначе `tests/test_release_roadmap.py` покраснеет и назовёт
эту же команду.

## Обслуживание

```bash
update-claudemd [--claudemd PATH] [--dry-run]  # Обновить секцию <!-- DYNAMIC --> в CLAUDE.md И в соседнем AGENTS.md (v1.5: --dry-run печатает diff и возвращает exit 1 при drift). Файл без маркера пропускается с notice.
fts optimize                          # Оптимизировать FTS5 индексы
hud                                   # Live dashboard: задача + сессия + gates + логи
suggest-model [complexity]            # Рекомендация Claude-модели: simple→Haiku, medium→Sonnet, complex→Opus
```

## Команды, не попавшие в разделы выше

Раздел заведён замером: из 53 команд парсера четырнадцать не были
названы в этом файле нигде, и агент не имел способа о них узнать. Порядок —
алфавитный; подробности у каждой по `--help`.

```bash
# --- контрактный контур RENAR ---
actz create|point|sign|verify|show|list|delta|link|unlink|delete|search
actz decided-in|decided-in-remove|final-tz|orphans   # ACTZ: акты и итоговое ТЗ
adapt create|interpret|finding|sign|verify|show|list|delta|link|unlink|delete|search
                                                    # адаптация нормы под проект
spec list|show|add|update|delete|link|unlink|search  # требования и их привязки
at create|show|list|delete|search                    # приёмочные тесты
at check-freshness|record-result|diagnose|release-readiness

# --- доказательства и подписи ---
key init                       # завести пару ключей проекта в .tausik/keys/
key show                       # показать отпечаток открытого ключа
receipt show                   # напечатать и ПЕРЕПРОВЕРИТЬ последнюю квитанцию
receipt export|verify          # выгрузить и сверить квитанцию отдельно

# --- навигация по коду (см. graph.md и symbol-index.md) ---
graph build                    # наполнить граф артефактов: индекс и оба слоя рёбер
graph show <путь>              # что связано с файлом и на каком основании
graph status                   # сколько хранится, что протухло, какие корни
symbol <имя>                   # определение, его файл:строка и вызывающие
coherence [--json]             # собрать материал о связности дерева для судьи

# --- работа с деревом и хранилищем ---
knowledge export|restore|import-brain   # общее хранилище знаний в файл и обратно
knowledge export --to <dir> --redacted  # копия в дорогу: пути, e-mail, приватные URL, имена проектов -> плейсхолдеры
db prune [--keep N] [--dry-run] # бэкапы БД: оставить N новейших .bak.v<N>, удалить все прочие .bak.*
config show                    # показать разрешённую конфигурацию с её тирами
config set <ключ> <значение>   # записать переопределение в .tausik/config.json
redact --pattern <шаблон>      # вычистить секрет из истории знаний (--apply — не сухой прогон)
                               # только CLI, намеренно: инструмента MCP нет (scripts/mcp_cli_only.py)
redact list                    # показать применённые вычистки

# --- выпуск и сеть ---
publish snapshot --from <ref> --parent <sha> [--dry-run]   # публичный снимок: отфильтрованное дерево поверх публичной головы
publish verify --snapshot <sha> --from <ref>               # снимок == отфильтрованное дерево источника, байт в байт
push-ok [--ttl N]              # выписать билет на git push (по умолчанию 60 секунд)
serve [--host H] [--port P]    # поднять локальную точку проверки квитанций
```

> `serve` по умолчанию слушает `127.0.0.1`. Выставление наружу требует
> `--yes-expose` — отдельного явного согласия, а не флага по умолчанию.
>
> Порт эндпоинт НЕ делит. На Windows `SO_REUSEADDR`, который
> `http.server` включает по умолчанию, разрешает привязку к адресу, уже
> занятому другим процессом, — и до 1.9 два сервера действительно
> привязывались к одному порту, обе привязки успешно. Теперь вторая
> отбивается: эндпоинт, чей порт можно тихо разделить, — не тот, чьим
> ответам о квитанциях можно доверять. На POSIX флаг сохранён, там он
> означает лишь перепривязку порта из `TIME_WAIT`.

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
| Время сессии | Сигнал с порогом `session_max_minutes` по active time (idle: `session_idle_threshold_minutes`); не отказывает |

### Цена в деньгах: `token_price` в `.tausik/config.json`

`tausik metrics tokens` печатает расход по ЧЕТЫРЁМ видам оплаты — output, input
(некэшированный), cache_create, cache_read — и, если заданы ставки, цену каждого.
Ставки живут в `.tausik/config.json`:

```json
{ "token_price": { "claude-opus": { "output": 75.0, "input": 15.0,
                                    "cache_create": 18.75, "cache_read": 1.5 } } }
```

Ключ — ПРЕФИКС имени модели (совпадает самый длинный), значения — доллары за
миллион токенов. Ставок по умолчанию нет намеренно: ставка это внешний факт с
датой и договором, прайс двигается, соглашения различаются, и число, вписанное в
код, не подошло бы никому и гнило бы молча. Модель без ставки сообщается как
UNPRICED, а не как ноль: ноль читался бы как бесплатная работа.

Ниже — та же цена ПО ЗАДАЧАМ, с числом ходов и долей попаданий в кэш. Замер
на 5964 вызовах: cache_read 99,5% всего входа, то есть расход почти целиком в
повторной пересылке префикса. Отсюда правило: мерить цену на ЗАВЕРШЁННУЮ ЗАДАЧУ, а
не на запрос — лишний ход стоит порядка полумиллиона токенов cache_read, и правка,
экономящая токены запроса ценой хода, проигрывает примерно в сто раз.
