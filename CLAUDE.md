# CLAUDE.md

Инструкции для AI-агента в этом репозитории. Следуй им строго.

# TAUSIK — фреймворк AI-агентов

Реализует [SENAR v1.3](https://senar.tech). Задачи, сессии, качество, проектная память.

Stack: Python 3.11+ stdlib | CLI `.tausik/tausik` | DB SQLite+FTS5 | Tests pytest. Все данные в `.tausik/` (единственный .gitignore).

## Принципы

- **Нулевая толерантность к тихим ошибкам.** Ошибка CLI — заведи баг-задачу.
- **Agent-first.** Перед закрытием: "поймёт ли свежий агент?"
- **Dogfooding.** Этот фреймворк — наш же пользователь. Неудобно — баг.
- **SENAR.** Контекст важнее кода. Верификация важнее скорости. Знания важнее опыта.

## Ограничения (жёсткие)

- **Нет кода без задачи.** `task start <slug>` перед Write/Edit.
- **QG-0 Context Gate.** `task start` требует goal + acceptance_criteria.
- **QG-2 Verify-First.** Heavy gates через `tausik verify --task <slug>` (cache 10 мин), затем `task done --ac-verified` читает кэш. Edge-cases — `docs/ru/agent-contract.md`.
- **Нет коммита без gates.** Исправь blocking failures.
- **Нет прямого доступа к БД.** Только MCP/CLI.
- **Не угадывай аргументы CLI.** `tausik <cmd> --help` или `docs/ru/cli.md`.
- **Исходники в корне** (`scripts/`, `docs/`, `harness/`, `bootstrap/`). Не редактируй `.claude/` напрямую.
- **MCP-first.** MCP > CLI когда equivalent.
- **Git: спроси перед commit/push.**
- **Макс. 400 строк/файл.** Filesize gate. Исключения: тесты, generated.
- **Непрерывное журналирование.** `task log <slug> "msg"` после каждого шага.
- **Документируй dead ends.** `tausik dead-end "approach" "reason"`.
- **Checkpoint каждые 30-50 tool calls.** `/checkpoint`, `/end`.
- **Лимит сессии 180 мин ACTIVE** (gap-based ≥10мин = AFK).
- **Знания фреймворка остаются здесь.** Не сохраняй инструкции TAUSIK в auto-memory.

## Память

| Система | Когда |
|---|---|
| **TAUSIK memory** (`memory add`, `.tausik/tausik.db`) | Паттерны/dead ends/conventions ЭТОГО проекта |
| **Claude auto-memory** (`~/.claude/`) | Кросс-проектные привычки пользователя |

Типы: `pattern`, `gotcha`, `convention`, `context`, `dead_end`.
CLI: ВСЕГДА `.tausik/tausik <команда>`. НИКОГДА `python scripts/project.py` напрямую.

## Команды

```bash
.tausik/tausik status                          # обзор + предупреждения SENAR
.tausik/tausik task start <slug>               # активировать (QG-0)
.tausik/tausik verify --task <slug>            # heavy gates, cache 10 мин
.tausik/tausik task done <slug> --ac-verified  # завершить (QG-2)
.tausik/tausik task log <slug> "message"       # журнал
.tausik/tausik dead-end "approach" "reason"    # dead end
.tausik/tausik metrics                         # SENAR метрики + LLM cost
.tausik/tausik search "<query>"                # FTS5 поиск
.tausik/tausik doctor                          # health check
```

Статусы: `planning → active → blocked|review → done`.

## Reference

Полный контракт (estimation, SENAR matrix, roles, custom_stacks, QG-2): `docs/ru/agent-contract.md`. CLI: `docs/ru/cli.md`. Архитектура: `docs/ru/architecture.md`. Quickstart: `docs/ru/quickstart.md`. Changelog: `CHANGELOG.md`.

<!-- DYNAMIC:START -->
## Current State
Session: #81 (active) | Branch: main | Version: 1.5.0
Tasks: 795/842 done, 1 active, 0 blocked
Active: v15p-release-150

### Memory tail
Decisions (5):
- #96 v15s-rule7: keyword hard-gate (3f1d70c) остаётся жёстким полом; structured-часть = парсер root-cause (closed-list катего
- #95 Срез v1.5 = полировка (v15p) + SENAR (v15s) + единственная фича v15mr-fable-tier-fix (P0). Snippet ×5, orchestrator, ост
- #94 Глобальная установка TAUSIK (отказ от сабмодуля, user-scope MCP) отложена из v1.5 в major-веху 2.0
- #93 L3-эскалация: measured score >= 0.66 И покрытие измеренными факторами >= 0.75 весов (4 из 5)
- #92 Risk-модель: взвешенная сумма 5 факторов (gates .25, tests .20, AC-evidence .20, security .20, churn .15), пороги 0.33/0
Conventions (5):
- #131 Токен-экономия: лаконичный вывод агента
- #122 filesize gate exempt: docs/{en,ru}/research/*
- #101 After editing scripts/* — bootstrap before dogfood via .tausik/tausik CLI
- #94 Cross-IDE hook parity test: bootstrap_qwen mirrors bootstrap_hooks
- #91 Filesize debt: extract via Mixin inheritance for stateful methods
Dead ends (3):
- #128 Real-screenshot + asciinema-cast in HomeLanding
- #119 Edit tool с string-match для слияния тестов содержащих невидимые Unicode separators (U+2028, U+2029,
- #109 v14b-token-t12-todo-reminder: гейтить TodoWrite reminder hook условиями (>5 tool calls без update +
<!-- DYNAMIC:END -->
