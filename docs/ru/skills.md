[English](../en/skills.md) | **Русский**

# Навыки (v1.3)

Skill'ы — intent-based инструкции, определяющие поведение агента. Не нужно запоминать имена или синтаксис — пишете, что хотите, и агент подбирает подходящий skill. Slash-префикс (`/plan`, `/ship`) явно вызывает один.

После bootstrap идут **13 core skills** из `agents/skills/`. Дополнительные **vendor / official skills** (25+) ставятся по запросу через `tausik skill install <name>` из репо `tausik-skills` (или из встроенной директории `skills-official/`).

## Core skill'ы (13)

Всегда доступны после bootstrap — workflow-примитивы, без которых TAUSIK не работает.

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
| `/brain` | Query/store cross-project знания в Shared Brain (Notion + local mirror) — headline-фича v1.3 |
| `/explore` | Time-boxed исследование (default 30 мин) перед коммитом к подходу |
| `/interview` | Сократическая Q&A — макс. 3 вопроса для пиннинга требований |

### Качество

| Skill | Когда |
|-------|-------|
| `/review` | Code review против 28-point SENAR checklist (5 параллельных агентов, итеративно) |
| `/test` | Запуск/написание тестов, отслеживание coverage |
| `/debug` | Reproduce → isolate root cause → fix |

## Vendor / Official skill'ы (25+)

Не разворачиваются автоматически — ставятся по запросу. Лежат в `skills-official/` (встроенно) и в репо `tausik-skills` (внешне). `tausik skill install <name>` для добавления, `tausik skill activate <name>` для включения.

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
| `/go` | One-phrase quick-start: фраза → задача создана → стартована |
| `/next` | Выбрать лучшую следующую задачу |
| `/daily` | Сводка за сегодня: выполненные задачи, коммиты, время |
| `/diff` | Анализ git diff с риск-хайлайтом |
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
| `/onboard` | Project onboarding: структура, конвенции, активная работа |
| `/retro` | Ретро по недавней работе |
| `/presale` | Presale-оценка — capacity planning + proposal |
| `/init` | Инициализация нового CLAUDE.md из свежей кодбазы |

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
.tausik/tausik skill activate <name>         # копирует из agents/skills → .claude/skills
.tausik/tausik skill deactivate <name>       # убрать из .claude/skills (vendored copy остаётся)
.tausik/tausik skill uninstall <name>        # удалить полностью
```

Официальный vendor-репо: `https://github.com/Kibertum/tausik-skills`. Custom-репозитории поддерживаются — см. **[Skill Adaptation Guide](skill-adaptation.md)**.

## Что дальше

- **[Workflow](workflow.md)** — как skill'ы композятся в рабочий день
- **[CLI команды](cli.md)** — вызов TAUSIK из терминала напрямую
- **[MCP инструменты](mcp.md)** — программный surface для агентов
- **[Vendor skill'ы](vendor-skills.md)** — установка и авторинг skill-пакетов
