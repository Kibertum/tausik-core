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
Session: #129 (active) | Branch: release/1.8-batch-s126 | Version: 1.7.0
Tasks: 1025/1096 done, 0 active, 0 blocked

### Memory tail
Context (5):
- #279 Большое ревью сессии #129: четыре аудита релиза 1.8 (diff, архитектура, доки, продукт)
- #267 Escape-rate #126: risk_score НЕ предсказывает побеги, verified-задачи сбегают ЧАЩЕ (селекция)
- #255 Спека MCP 2026-07-28: что депрекировано, что выжило и что это значит для TAUSIK
- #233 Волна роя сессии #117: верифицированные находки по 7 задачам релиза 1.8
- #229 Зачем нужен TAUSIK: защита от ИСКРЕННЕГО агента, а не от лжеца. Тезис релиза 1.8
Decisions (5):
- #165 Changelog-гейт судит СОДЕРЖАНИЕ (добавленная непустая строка) и засчитывает коммиты, сделанные во время задачи (окно sin
- #164 v14c-visual-cost-dashboard ЗАКРЫТ как won't-do: Plotly/Dash-дашборд НЕ реализуется — противоречит stdlib-принципу проект
- #163 l26-signing-key-boundary: подписи receipt/anchor документируются как tamper-evidence против ВНЕШНИХ правок tausik.db, но
- #162 AC2 хук-контракта: закрыть Bash-write дыру НОВЫМ PreToolUse-гейтом (matcher Bash + NotebookEdit), переиспользующим token
- #161 Релиз 1.8 = эпики {landscape-2026-h2, shared-knowledge} + v14c-visual-cost-dashboard + v14c-skill-web-catalog. v2-global
Conventions (5):
- #277 Гейт, шипящийся в чужие проекты: механизм общий, политика в конфиге
- #276 Adversarial-review запускать НА ФИКСЫ находок, не только на исходную реализацию
- #275 CHANGELOG ведётся непрерывно: каждая задача 1.8 обновляет [Unreleased] + зеркало ru
- #274 Best-effort telemetry-писатель обязан возвращать landed/miss bool — иначе caller ложно утверждает ус
- #273 Кросс-харнесс телеметрия: не-Python харнесс пишет events через CLI-команду к единому Python-эмиттеру
Dead ends (3):
- #230 Восстановить тело страницы BRAIN 3a16b6ed-07ff-8141-96b6-c8d7fd22aefa (решение с опровержениями 3 из
- #198 Ужесточить `tausik push-ok`: выдавать push-тикет только при наличии зелёного verify-receipt на текущ
- #191 Chain 'tausik push-ok && git push' in a single Bash tool call to authorize + push atomically
<!-- DYNAMIC:END -->
