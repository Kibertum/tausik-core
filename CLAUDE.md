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
Session: #96 (active) | Branch: main | Version: 1.5.1
Tasks: 879/901 done, 0 active, 0 blocked

### Memory tail
Context (5):
- #172 v1.5 swarm-review: accepted-by-design LOW findings (post-release backlog)
- #163 TAUSIK reached RENAR-1 on honest data via the renar-adoption ТЗ/ADAPT
- #86 v1.5 roadmap: Cursor/Qwen parity for v1.4 Claude-only features
- #74 session-44-handoff (extended, post-trim)
- #31 cq (Mozilla) — план интеграции
Decisions (5):
- #117 REVERSE Decision #116: implement v15-orchestrator-worker epic INTO 1.5 (user direction). TAUSIK provides delegation SCAF
- #116 Defer v15-orchestrator-worker epic (6 tasks) OUT of 1.5 → 1.5.x/2.0. 1.5 is a hardening release; orchestrator-worker is 
- #115 RENAR adoption is ADVISORY-FIRST ('lite') — TAUSIK is a lightweight zero-dep framework. Ladder: (1) artifacts SPEC/ADAPT
- #114 Decomposed v15-orchestrator-worker-pattern (single complex placeholder) into epic v15-orchestrator-worker → story v15-ow
- #113 Plan the v15-cross-ide-parity (AIDD) epic INTO 1.5 — one concrete task per existing story, no invented padding. autogen 
Conventions (5):
- #171 meta kv: delete with meta_delete, not empty-string tombstone; sibling aggregates share defensive pos
- #166 Co-locate message text with its data module near filesize cap
- #155 Don't re-run 'tausik <cmd> --help' for a subcommand you already used this session
- #150 Adding a new schema migration (vN)
- #146 Adding an MCP tool requires syncing 3 mirrors + bumping 6 doc-count sites
Dead ends (3):
- #151 FTS5 query WHERE <alias> MATCH ? (aliased fts table in MATCH)
- #145 Hash-chain events на insert-time (event_add вычисляет prev_hash/entry_hash при вставке)
- #128 Real-screenshot + asciinema-cast in HomeLanding
<!-- DYNAMIC:END -->
