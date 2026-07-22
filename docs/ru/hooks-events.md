# Хук-события и покрытие записи файлов

Ревизия хук-контракта TAUSIK (задача `l26-hook-contract-review`, Decision #162).
Отвечает на вопрос AC1: какие события перехватывают запись файлов и покрыта ли
запись через Bash/NotebookEdit штатно.

## Почему это важно

QG-0 (SENAR Rule 1, «нет кода без задачи») и scope-ACL (Rule 2) — это
**PreToolUse-хуки**, привязанные к matcher'ам конкретных инструментов. Значит их
охват ровно такой, какие инструменты перечислены в matcher. Инструмент записи, не
попавший в matcher, обходит проверку целиком — при этом отчёт гейтов выглядит
одинаково зелёным. Это не гипотеза: в сессиях #117/#118 один и тот же файл был
заблокирован через `Write` и тут же создан через Bash-heredoc без единого
возражения.

## События, которые TAUSIK использует сегодня

Источник истины — `bootstrap/bootstrap_hooks.py::build_hooks_dict` (генерирует
`hooks`-блок `.claude/settings.json`). Проверяемо кодом:

| Событие | Matcher'ы | Роль |
|---|---|---|
| `PreToolUse` | `Write\|Edit\|MultiEdit\|NotebookEdit` | `task_gate` (QG-0), `scope_write_gate` (ACL), `memory_pretool_block`, `secret_scan` |
| `PreToolUse` | `Bash` | `bash_firewall`, **`bash_write_gate` (QG-0 + ACL для записи из shell)** |
| `PreToolUse` | `Bash(git push *)` | `git_push_gate` |
| `PreToolUse` | `WebSearch\|WebFetch` | `brain_search_proactive` |
| `PostToolUse` | Write/Bash/Read/… | форматтер, usage/activity-события, cost-budget, `task_done_verify` |
| `SessionStart` / `UserPromptSubmit` / `Stop` / `SessionEnd` | `` | старт-инжект, keyword-detector, cleanup, метрики |

## Покрытие записи файлов

| Вектор записи | Инструмент/команда | Покрытие до 1.8 | Покрытие с 1.8 |
|---|---|---|---|
| Прямая правка | `Write`, `Edit` | ✅ QG-0 + ACL | ✅ |
| Мульти-правка | `MultiEdit` | ⚠️ только ACL (QG-0 matcher был `Write\|Edit`) | ✅ QG-0 + ACL |
| Ноутбук | `NotebookEdit` | ❌ не покрыт | ✅ QG-0 + ACL (по `notebook_path`) |
| Shell-редирект / heredoc | `cat > f`, `echo >> f` | ❌ обход | ✅ `bash_write_gate` |
| In-place / писатели | `sed -i`, `tee`, `dd of=`, `cp`/`mv`/`install` (вкл. `-t`), `truncate`, `touch`, `curl -o`, `wget -O`, `tar -x -C`, `unzip -d` | ❌ обход | ✅ `bash_write_gate` |
| Код интерпретатора | `python -c "open(f,'w')"` | ❌ обход | ⚠️ ловится только литеральный `open(...)` |

Штатно (нативным механизмом хоста) запись через Bash/NotebookEdit **не**
покрывается — Claude Code не эмитит отдельного «write»-события, он даёт хуку сырой
`tool_input`. Поэтому покрытие достигается разбором команды в `bash_write_gate`, а
не опорой на событие хоста.

## Ландшафт событий 2026 (по анализу 2026-07-18)

Набор хук-событий Claude Code в 2026 расширился (примерно до трёх десятков:
`PermissionRequest`, `PermissionDenied` с retry, `PostToolUseFailure`,
`SubagentStart/Stop`, `PreCompact/PostCompact`, `TaskCreated/TaskCompleted`,
`WorktreeCreate/Remove` и др.). Ни одно из них **не** превращает Bash-запись в
отдельно наблюдаемое событие «файл записан», поэтому вывод ревизии: дыру нельзя
закрыть простой подпиской на новое событие — нужен разбор команды. Эти события —
кандидаты для будущей телеметрии (например, `PostToolUseFailure` для fail-open
надзора), но вне охвата данной задачи. Список выше приведён как результат
проектного анализа ландшафта, а не как выверенная спецификация API хоста.

## Остаточная граница

`bash_write_gate` — best-effort по замыслу. Что он осознанно не ловит и почему —
в [`agent-contract.md`](agent-contract.md#граница-принуждения-хуков-что-покрыто-и-что-нет)
(обфускация, путь-в-переменной, писатель за обёрткой). AC2 допускает «закрыть ИЛИ
явно задокументировать границу»; здесь она задокументирована.
