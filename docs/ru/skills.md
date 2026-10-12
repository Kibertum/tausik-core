[English](../en/skills.md) | **Русский**

# Навыки (v1.4)

<!-- doc-map: reader=user; zone=core-surface -->

Skill'ы — intent-based инструкции, определяющие поведение агента. Не нужно запоминать имена или синтаксис — пишете, что хотите, и агент подбирает подходящий skill. Slash-префикс (`/plan`, `/ship`) явно вызывает один.

После bootstrap идут **13 core skills** из `harness/skills/`. В официальном магазине остаются только `docs`, `excel` и `pdf`. Ставьте нужный навык через `tausik skill install <name>`, чтобы неиспользуемые инструкции не расходовали контекст. **Карта репо-скиллов:** [Экосистема скиллов (one-pager)](skill-ecosystem.md).

> **Правило экономии с v1.4.** Раньше bootstrap раскрывал весь каталог и тратил около 1 520 токенов на список в system reminder. Теперь по умолчанию раскрываются только core-навыки. `--include-official` оставлен для совместимости с локальным checkout, но экономичный поддерживаемый путь — установка по одному навыку.

**Варианты под разные хосты:** у skill может быть каталог **`variants/<profile>.md`** — см. [Профили skills и variants](skill-profiles.md).

## Core skill'ы (13)

Всегда доступны после bootstrap — workflow-примитивы, без которых TAUSIK не работает.

### Workflow

| Skill | Когда |
|-------|-------|
| `/start` | Начать рабочую сессию — загружает handoff, status, memory block |
| `/end` | Завершить сессию — сохраняет метрики + handoff |
| `/checkpoint` | Сохранить контекст без завершения сессии (когда об этом говорит сигнал чекпоинта) |
| `/plan` | Спланировать задачу из свободного описания (interview phase + AC) |
| `/task` | Работать над существующей задачей с QG-0/QG-2 enforcement |
| `/ship` | Завершить задачу: review + test + gates + commit |
| `/commit` | Создать стандартизированный git-коммит |

### Знания

| Skill | Когда |
|-------|-------|
| `/explore` | Time-boxed исследование (default 30 мин) перед коммитом к подходу |
| `/interview` | Сократическая Q&A — макс. 3 вопроса для пиннинга требований |
| `/reason` | Записать структурированный трейс рассуждений (intent→premise→action→verification) на задаче — см. [Трейс рассуждений](reasoning-trace.md) |

### Качество

| Skill | Когда |
|-------|-------|
| `/review` | Code review против 28-point SENAR checklist (5 параллельных агентов, итеративно) |
| `/test` | Запуск/написание тестов, отслеживание coverage |
| `/debug` | Reproduce → isolate root cause → fix |

## Official / Vendor skills

Официальный каталог живёт в отдельном репозитории и не входит в релиз core. В нём намеренно только три нейтральных навыка для документов: `docs`, `excel` и `pdf`. Интеграции должны жить в MCP-серверах или сторонних репозиториях; корпоративным ролям в TAUSIK не место.

- Ставьте одну возможность через `tausik skill install <name>` и активируйте её только при необходимости.
- Используйте `skill bundle` только для стороннего репозитория, который его объявляет, и только если проекту нужны все участники.
- Не используйте `--include-official` в обычных проектах: он раскрывает все записи локального checkout и увеличивает повторяемый префикс промпта.
- Официальный репозиторий не публикует bundle.

## Жизненный цикл

```bash
.tausik/tausik skill list                    # активные + vendored + доступные
.tausik/tausik skill repo add <url>          # зарегистрировать TAUSIK-совместимый репо
.tausik/tausik skill install <name>          # clone + copy + pip deps
.tausik/tausik skill activate <name>         # копирует из harness/skills → .claude/skills
.tausik/tausik skill deactivate <name>       # убрать из .claude/skills (vendored copy остаётся)
.tausik/tausik skill uninstall <name>        # удалить полностью
```

Официальный vendor-репо: `https://github.com/Kibertum/tausik-skills`. Custom-репозитории поддерживаются — см. **[Skill Adaptation Guide](skill-adaptation.md)**.

### Соответствие спеке (agentskills.io)

Формат SKILL.md теперь — кросс-вендорный канон **agentskills.io**. Встроенный
гейт (`skill_spec_conformance`) фейлит close/commit, когда изменённый `SKILL.md`
нарушает машинно-проверяемые правила: `name` — 1–64 символа `a-z0-9` с одиночными
дефисами (без ведущего/замыкающего/сдвоенного дефиса) и **обязан совпадать с
именем каталога**; `description` — 1–1024 символа. Гейт инертен, пока среди
изменённых файлов нет `SKILL.md`. Локальные scaffold'ы, чей каталог начинается с
`_` или `.` (например `_profile-demo`), не являются публикуемыми скиллами и
пропускаются.

> Спека agentskills.io **не версионирована** и не содержит **ни одного положения
> по безопасности** — ничего про доверие, песочницы или права на инструменты.
> Этот гейт — проверка гигиены, держащая прогрессивное раскрытие рабочим; никогда
> не трактуйте соответствие как сигнал доверия.

### Массовая установка через бандлы

`tausik skill install <name>` ставит по одному навыку. Репозиторий может публиковать необязательные **bundles**; проверьте состав перед массовой установкой — см. **[Skill Bundles](skill-bundles.md)**:

```bash
.tausik/tausik skill bundle list                    # посмотреть доступные бандлы
.tausik/tausik skill bundle install <name>           # поставить всех участников bundle
```

## Что дальше

- **[Workflow](workflow.md)** — как skill'ы композятся в рабочий день
- **[CLI команды](cli.md)** — вызов TAUSIK из терминала напрямую
- **[MCP инструменты](mcp.md)** — программный surface для агентов
- **[Vendor skill'ы](vendor-skills.md)** — установка и авторинг skill-пакетов
