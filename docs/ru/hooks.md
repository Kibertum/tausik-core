[English](/docs/hooks) | **Русский**

# Хуки (v1.4)

TAUSIK использует хуки Claude Code для автоматического контроля качества. Хуки перехватывают действия агента **до** и **после** выполнения — это шлюзы, не инструкции. **20 Python-хуков + 1 shell `pre-commit` = 21 активный хук** идут с v1.4 (1.3.7 имел 16 + 1 = 17; v1.4 добавляет `secret_scan.py`, `posttool_usage.py`, `tool_output_truncation_nudge.py`, `task_cost_budget_check.py`).

## Что такое хуки

Хуки — скрипты, запускающиеся автоматически на каждое действие агента. Они решают, можно ли действие выполнять (PreToolUse), что делать после (PostToolUse) или что записать на границах сессии/агента (SessionStart, Stop, UserPromptSubmit). Общие хелперы живут в `scripts/hooks/_common.py` (сам по себе не хук); regex-набор `scripts/hooks/memory_markers.py` — библиотека, импортируемая `memory_posttool_audit.py` и pipeline'ом скраббинга brain.

## PreToolUse — шлюзы перед действием

| Хук | Когда | Что делает |
|------|-------|-----------|
| `task_gate.py` | Перед Write/Edit | Блокирует изменения файлов, если нет активной задачи (SENAR Rule 9.1) |
| `memory_pretool_block.py` | Перед Write/Edit/MultiEdit в auto-memory | Блокирует cross-project записи без `confirm: cross-project` в промпте |
| `secret_scan.py` (v1.4) | Перед Write/Edit/MultiEdit | Сканирует `tool_input` на типичные секреты (AWS/GitHub/Slack/Stripe/OpenAI/Anthropic токены, JWT, блоки приватного ключа, generic `password`/`api_key`). По умолчанию warning; `TAUSIK_SECRET_SCAN_STRICT=1` — блокировка. (SENAR Rule 10.12) |
| `bash_firewall.py` | Перед Bash | Блокирует опасные команды (rm -rf, DROP TABLE, force push, и т.д.) |
| `brain_search_proactive.py` | Перед WebSearch/WebFetch | Проактивно query'ит shared brain на релевантные decisions/patterns перед web-вызовами |
| `git_push_gate.py` | Перед `git push` (Bash matcher с `if`) | Блокирует push без свежего, одноразового тикета `.tausik/.push_ticket.json`, привязанного к SHA HEAD. `/ship` и `/commit` запускают `tausik push-ok && git push` после вашего "y" — `push-ok` пишет 60-секундный тикет, хук съедает его на следующем push. |

## PostToolUse — реакции после действия

| Хук | Когда | Что делает |
|------|-------|-----------|
| `auto_format.py` | После Write/Edit | Авто-форматирование через ruff/prettier/gofmt + лог "Modified: X" в задачу |
| `memory_posttool_audit.py` | После Write/Edit/MultiEdit в auto-memory | Аудитит cross-project leakage (использует regex-библиотеку `memory_markers.py`) и предупреждает |
| `task_done_verify.py` | После `mcp__tausik-project__tausik_task_done` | Аудитит AC evidence через 5 правило-base проверок (Ralph-mode-lite). |
| `brain_post_webfetch.py` | После WebFetch | Авто-кешит результат в shared brain `web_cache` для token reuse |
| `task_call_counter.py` | После любого tool call | Инкрементирует per-task `call_actual` счётчик; warning'ит на 1.5×budget |
| `posttool_usage.py` (v1.4) | После любого tool call | Записывает token-usage события в `usage_events` для per-task cost rollup |
| `activity_event.py` | После любого tool call | Записывает activity-таймстемпы для **gap-based active-time** метрики (SENAR Rule 9.2) |
| `tool_output_truncation_nudge.py` (v1.4) | После Read/Grep/Bash/Glob | Подсказывает агенту сузить scope, когда вывод превышает порог по строкам (warn-only) |
| `task_cost_budget_check.py` (v1.4) | После любого tool call | Сравнивает `cost_actual` / `tokens_actual` активной задачи с бюджетом; WARN на 1.5×, BLOCKER на 2× (с throttle) |

## SessionStart

| Хук | Когда | Что делает |
|------|-------|-----------|
| `session_start.py` | На старте сессии | Авто-инжектит status + Memory Block + ребилдит skill-профили — без ручного `/start` |

## UserPromptSubmit

| Хук | Когда | Что делает |
|------|-------|-----------|
| `user_prompt_submit.py` | На пользовательском промпте | Распознаёт coding-intent (EN+RU) → подталкивает, если нет активной задачи |

## Stop

| Хук | Когда | Что делает |
|------|-------|-----------|
| `keyword_detector.py` | На остановке агента | Ловит "I'll implement"/"сейчас напишу" drift-фразы → блокирует stop |
| `session_cleanup_check.py` | На остановке агента | Предупреждает об открытом exploration / review-задачах / session timeout |

## SessionEnd

| Хук | Когда | Что делает |
|------|-------|-----------|
| `session_metrics.py` | На завершении сессии | Записывает session metrics (active vs wall, throughput) в БД |

## Git pre-commit

| Хук | Когда | Что делает |
|------|-------|-----------|
| `pre-commit` (shell) | Перед `git commit` | Запускает `python -m mypy` против `scripts/` (конфиг из `pyproject.toml`). На exit ≠ 0 — **блокирует commit**. Опционально гонит инкрементальный `codebase-rag` reindex (warn-only, лимит 5с); никогда не блокирует commit из-за RAG. |

Это **не** «scoped quality gates» — те запускаются через `tausik verify` (тяжёлый стек: pytest/tsc/cargo/phpstan/…) и развязаны с `git commit` начиная с v1.4 Verify-First Contract.

### Установка (один раз)

```bash
# Вариант A: скопировать файл
cp scripts/hooks/pre-commit .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit

# Вариант B (рекомендуется): указать git на in-repo hooks-папку, чтобы обновления подхватывались автоматически
git config core.hooksPath scripts/hooks
```

> **Windows caveat.** `pre-commit` — bash-скрипт с `timeout(1)` и POSIX-ом `[ -f … ]`. Чистый `cmd.exe` его не запустит. Используй Git Bash, WSL или терминал, в котором есть Bash + `timeout` в `PATH`. Если команда работает только под Windows — замени скрипт на `pre-commit.cmd`-обёртку, которая зовёт `python -m mypy` напрямую и держит тот же контракт по exit code.

### Отключение / bypass

- Разово: `git commit --no-verify` (полностью пропускает `core.hooksPath`).
- Временно: `git config --unset core.hooksPath`.
- На CI без mypy: на CI-раннере не выставляй `core.hooksPath`; тяжёлая верификация всё равно идёт через `tausik verify`.

## Как это работает

```
Вы: "добавь кнопку на главную"

Агент хочет редактировать index.html
  → task_gate.py проверяет: есть ли активная задача? Нет → ЗАБЛОКИРОВАНО
  → Агент создаёт задачу через /plan, стартует
  → task_gate.py проверяет снова: задача есть → РАЗРЕШЕНО

Агент редактирует index.html
  → auto_format.py: форматирует prettier'ом
  → auto_format.py: пишет "Modified: index.html" в задачу
  → task_call_counter.py: бампит call_actual; warning на 1.5×budget
  → activity_event.py: штампует activity-таймстемп (active-time)

Агент: tausik task done my-button --ac-verified
  → task_done_verify.py: 5-проверочный AC-аудит
```

## Коды возврата

| Код | Значение | Поведение |
|------|---------|----------|
| 0 | Успех | Действие разрешено |
| 1 | Warning | Действие разрешено; warning записан |
| 2 | Block | Действие **отменено**; агент получает причину |

## Что блокирует `bash_firewall`

- `rm -rf /` и `rm -rf .` — удаление файловой системы
- `DROP TABLE`, `DROP DATABASE`, `TRUNCATE TABLE` — удаление данных
- `git reset --hard` — потеря локальных изменений
- `git push --force` — перезапись remote-истории
- `git clean -fd` — удаление untracked-файлов
- `dd if=/dev/zero`, `mkfs.` — форматирование диска
- Fork bombs

## Отключение хуков

Для тестирования или дебага: установите `TAUSIK_SKIP_HOOKS=1`.

В `.claude/settings.json` хуки генерируются автоматически на bootstrap. Чтобы отключить конкретный хук, удалите его из секции `hooks`. Для регенерации файла запустите `python .tausik-lib/bootstrap/bootstrap.py --refresh`.

## См. также

- **[Workflow](workflow.md)** — как хуки вписываются в рабочий цикл
- **[Session Active Time](session-active-time.md)** — что питает `activity_event.py`
- **[CLI команды](cli.md)** — управление задачами из терминала
