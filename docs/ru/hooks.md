[English](../en/hooks.md) | **Русский**

# Хуки (v1.3)

TAUSIK использует хуки Claude Code для автоматического контроля качества. Хуки перехватывают действия агента **до** и **после** выполнения — это шлюзы, не инструкции. **19 хуков** идут с v1.3.

## Что такое хуки

Хуки — скрипты, запускающиеся автоматически на каждое действие агента. Они решают, можно ли действие выполнять (PreToolUse), что делать после (PostToolUse) или что записать на границах сессии/агента (SessionStart, Stop, UserPromptSubmit). Общие хелперы живут в `scripts/hooks/_common.py`.

## PreToolUse — шлюзы перед действием

| Хук | Когда | Что делает |
|------|-------|-----------|
| `task_gate.py` | Перед Write/Edit | Блокирует изменения файлов, если нет активной задачи (SENAR Rule 9.1) |
| `bash_firewall.py` | Перед Bash | Блокирует опасные команды (rm -rf, DROP TABLE, force push, и т.д.) |
| `git_push_gate.py` | Перед git push | Блокирует прямой push — используйте `/ship` или `/commit` |
| `memory_pretool_block.py` | Перед Write в auto-memory | Блокирует cross-project записи без `confirm: cross-project` в промпте |

## PostToolUse — реакции после действия

| Хук | Когда | Что делает |
|------|-------|-----------|
| `auto_format.py` | После Write/Edit | Авто-форматирование через ruff/prettier/gofmt + лог "Modified: X" в задачу |
| `task_call_counter.py` | После любого tool call | Инкрементирует per-task `call_actual` счётчик; warning'ит на 1.5×budget |
| `activity_event.py` | После любого tool call | Записывает activity-таймстемпы для **gap-based active-time** метрики (SENAR Rule 9.2) |
| `memory_markers.py` | После Write/Edit | Распознаёт memory marker patterns и роутит в TAUSIK memory store |
| `memory_posttool_audit.py` | После Write в auto-memory | Аудитит cross-project leakage и предупреждает |
| `brain_post_webfetch.py` | После WebFetch | Авто-кешит результат в shared brain `web_cache` для token reuse |
| `task_done_verify.py` | После `task_done` | Аудитит AC evidence через 5 правило-base проверок (Ralph-mode-lite) |
| `notify_on_done.py` | После `task_done` (опционально) | Шлёт webhook в Slack/Discord/Telegram, если настроен |

## SessionStart / SessionEnd

| Хук | Когда | Что делает |
|------|-------|-----------|
| `session_start.py` | На старте сессии | Авто-инжектит status + Memory Block — без ручного `/start` |
| `session_metrics.py` | На завершении сессии | Записывает session metrics (active vs wall, throughput) в БД |
| `session_cleanup_check.py` | На остановке агента | Предупреждает об открытом exploration / review-задачах / session timeout |

## UserPromptSubmit / Stop

| Хук | Когда | Что делает |
|------|-------|-----------|
| `user_prompt_submit.py` | На пользовательском промпте | Распознаёт coding-intent (EN+RU) → подталкивает, если нет активной задачи |
| `keyword_detector.py` | На остановке агента | Ловит "I'll implement"/"сейчас напишу" drift-фразы → блокирует stop |
| `brain_search_proactive.py` | На пользовательском промпте | Проактивно query'ит shared brain на релевантные decisions/patterns |

## Git pre-commit

| Хук | Когда | Что делает |
|------|-------|-----------|
| `pre-commit` (shell) | Перед `git commit` | Запускает scoped quality gates; блокирует commit при failure |

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
  → notify_on_done.py: опциональный webhook
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
