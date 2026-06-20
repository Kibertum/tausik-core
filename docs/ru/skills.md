[English](/docs/skills) | **Русский**

# Навыки (v1.4)

Skill'ы — intent-based инструкции, определяющие поведение агента. Не нужно запоминать имена или синтаксис — пишете, что хотите, и агент подбирает подходящий skill. Slash-префикс (`/plan`, `/ship`) явно вызывает один.

После bootstrap идут **13 core skills** из `harness/skills/` (плюс `/brain` *условно* — когда у проекта настроен Notion, см. [Shared Brain](shared-brain.md)). Дополнительные **official / vendor skills** (20) ставятся по запросу: per-skill через `tausik skill install <name>`, либо вся пачка через `python .tausik-lib/bootstrap/bootstrap.py --include-official` (alias `--include-vendor`). **Карта репо-скиллов:** [Экосистема скиллов (one-pager)](skill-ecosystem.md). **Bulk-install по группам:** [Skill Bundles](skill-bundles.md).

> **Изменение default в v1.4.x.** До v1.4.x bootstrap автоматически разворачивал все 38 source+registry скиллов (~1,520 токенов в system-reminder). С v1.4.x default — 13 + brain conditional (~480 токенов), экономия ~1,040 токенов на ход. Перезапусти bootstrap с `--include-official`, если нужен старый полный набор. **В v1.4.0 также удалены 5 избыточных скиллов** (`/go`, `/next`, `/diff`, `/onboard`, `/init`) — vendor count теперь 20. См. **[Skill Bundles Migration](skill-bundles-migration.md)**.

**Варианты под разные хосты:** у skill может быть каталог **`variants/<profile>.md`** — см. [Профили skills и variants](skill-profiles.md).

## Core skill'ы (13 + brain conditional)

Всегда доступны после bootstrap — workflow-примитивы, без которых TAUSIK не работает. `/brain` — 14-й core skill, но разворачивается, только когда `tausik brain init` настроил Notion-конфигурацию (чтобы проекты, не использующие shared brain, не платили его token-цену).

### Workflow

| Skill | Когда |
|-------|-------|
| `/start` | Начать рабочую сессию — загружает handoff, status, memory block |
| `/end` | Завершить сессию — сохраняет метрики + handoff |
| `/checkpoint` | Сохранить контекст без завершения сессии (рекомендовано каждые 30–50 tool calls) |
| `/plan` | Спланировать задачу из свободного описания (interview phase + AC) |
| `/task` | Работать над существующей задачей с QG-0/QG-2 enforcement |
| `/ship` | Завершить задачу: review + test + gates + commit |
| `/commit` | Создать стандартизированный git-коммит |

### Знания

| Skill | Когда |
|-------|-------|
| `/brain` *(условно)* | Query/store cross-project знания в Shared Brain (Notion + local mirror). Разворачивается только если `tausik brain init` заполнил `brain.notion_db_ids` в `.tausik/config.json`. |
| `/explore` | Time-boxed исследование (default 30 мин) перед коммитом к подходу |
| `/interview` | Сократическая Q&A — макс. 3 вопроса для пиннинга требований |
| `/reason` | Записать структурированный трейс рассуждений (intent→premise→action→verification) на задаче — см. [Трейс рассуждений](reasoning-trace.md) |

### Качество

| Skill | Когда |
|-------|-------|
| `/review` | Code review против 28-point SENAR checklist (5 параллельных агентов, итеративно) |
| `/test` | Запуск/написание тестов, отслеживание coverage |
| `/debug` | Reproduce → isolate root cause → fix |

## Official / Vendor skill'ы (20)

По default не разворачиваются. Два способа поднять их:

- **Per-skill (рекомендуется).** `tausik skill install <name>` из `skills-official/` или репо `tausik-skills`, затем `tausik skill activate <name>`. В system-reminder добавляется только то, что ты явно попросил.
- **Вся пачка.** `python .tausik-lib/bootstrap/bootstrap.py --include-official` (alias `--include-vendor`). Сгенерит lightweight stubs для каждой записи `skills-official/registry.json`. Используй, если хочешь поведение v1.3.x (~38 skills всегда видны).

### Качество / Дисциплина (opt-in)

| Skill | Когда |
|-------|-------|
| `/zero-defect` | Session-scoped precision mode для high-stakes работы (auth/payment/migration). Замедляет velocity 2–3×, но снижает дефекты. Maestro-inspired. |
| `/skill-test` | Мета-инструмент для авторов скиллов — auto-generate и запускать сценарии |

### Извлечение документов (opt-in)

| Skill | Когда |
|-------|-------|
| `/markitdown` | Конвертация DOCX/PPTX/XLSX/HTML/EPUB/PDF в markdown через markitdown CLI (требует `pip install markitdown`) |

Устанавливаются из репо `tausik-skills`. Используйте `tausik skill install <name>` для добавления, `tausik skill activate <name>` для включения.

### Productivity / Wrap-up

| Skill | Когда |
|-------|-------|
| `/daily` | Сводка за сегодня: выполненные задачи, коммиты, время |
| `/run` | Автономное batch-выполнение markdown-плана |
| `/loop-task` | Автономный task-execution loop с fresh-контекстом |
| `/dispatch` | Оркестрация параллельных worker-агентов на независимых задачах |

### Анализ

| Skill | Когда |
|-------|-------|
| `/audit` | Code-quality audit — статический анализ, метрики, actionable-отчёт |
| `/security` | Security audit (OWASP Top 10, secrets scan) |
| `/optimize` | Performance optimization — анализ узких мест |
| `/ultra` | Глубокий 10-point анализ для сложных архитектурных решений |
| `/retro` | Ретро по недавней работе |
| `/presale` | Presale-оценка — capacity planning + proposal |

### Интеграции (внешние сервисы через MCP)

| Skill | Когда |
|-------|-------|
| `/jira` | Jira issue management (create/update/search) через MCP |
| `/bitrix24` | Bitrix24 CRM — задачи, сделки, контакты через webhook API |
| `/confluence` | Confluence-публикация — create/update страницы |
| `/sentry` | Sentry error monitoring через MCP |

### Документация / Извлечение

| Skill | Когда |
|-------|-------|
| `/markitdown` | Конвертация DOCX/PPTX/XLSX/HTML/EPUB/PDF в markdown через markitdown CLI (требует `pip install markitdown`) |
| `/excel` | Чтение/анализ/генерация Excel/CSV |
| `/pdf` | Чтение/извлечение/анализ PDF документов |
| `/docs` | Генерация или обновление документации (jsdoc/docstrings) |

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

## Что дальше

- **[Workflow](workflow.md)** — как skill'ы композятся в рабочий день
- **[CLI команды](cli.md)** — вызов TAUSIK из терминала напрямую
- **[MCP инструменты](mcp.md)** — программный surface для агентов
- **[Vendor skill'ы](vendor-skills.md)** — установка и авторинг skill-пакетов
