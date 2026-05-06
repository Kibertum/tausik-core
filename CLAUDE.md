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
Session: #62 (active) | Branch: main | Version: 1.4.0
Tasks: 680/704 done, 0 active, 1 blocked
Blocked: v14b-skill-bundles-marketplace

### Memory tail
Decisions (5):
- #66 tausik_session_open compound RPC orchestrator placed in handler layer (not service layer). Each sub-section (session/sta
- #65 Surface SENAR signals (exploration_open, audit_overdue_sessions) directly in tausik_status compact JSON instead of resto
- #64 memory_block re-injection moved from /start MCP call to CLAUDE.md via update_claudemd. New helper build_compact_memory_t
- #63 brain_search read-path uses 5s timeout (SEARCH_TIMEOUT_S); writes keep 10s (DEFAULT_TIMEOUT). Per-call timeout kwarg in 
- #62 Brain discovery uses two-pass title-then-schema matching, NOT a new CLI subcommand. Schema-match is soft: required-prope
Conventions (5):
- #101 After editing scripts/* — bootstrap before dogfood via .tausik/tausik CLI
- #94 Cross-IDE hook parity test: bootstrap_qwen mirrors bootstrap_hooks
- #91 Filesize debt: extract via Mixin inheritance for stateful methods
- #89 Session active-time uses CLIP (not EXCLUDE) semantics
- #85 Claude-first, then Cursor/Qwen for new optimizations
Dead ends (3):
- #109 v14b-token-t12-todo-reminder: гейтить TodoWrite reminder hook условиями (>5 tool calls без update +
- #102 First-volna recon: read brain_init.py up to create_brain_databases (line 188) and rapidly conclude "
- #72 tausik brain init --join-existing --yes --non-interactive on a project where the Notion integration
<!-- DYNAMIC:END -->
