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
Session: none | Branch: main | Version: 1.7.0
Tasks: 973/1038 done, 0 active, 0 blocked

### Memory tail
Context (5):
- #206 caveman: что это, из него ничего не брали, наша поддержка — свой output-режим
- #190 Host x enforcement x GLM-subscription matrix (extension research, session #102)
- #184 Два независимых IDE-реестра: bootstrap-time (IDE_DIRS) vs runtime (ide_utils.IDE_REGISTRY)
- #172 v1.5 swarm-review: accepted-by-design LOW findings (post-release backlog)
- #163 TAUSIK reached RENAR-1 on honest data via the renar-adoption ТЗ/ADAPT
Decisions (5):
- #136 mcp-session-leak: фикс отложен на свежую сессию — требует архитектурного выбора auto-reap vs ручной reap
- #135 Ревью-агентам с правом RUN/reproduce не давать живое рабочее дерево — только изолированную копию (snapshot в temp) с явн
- #134 harness/claude/mcp — ЕДИНСТВЕННОЕ каноническое дерево MCP. Зеркало harness/cursor/mcp (19 файлов) удалено, а не синхрони
- #133 QG-0-плагин OpenCode кэширует вердикт активной задачи, но кэш привязан к ПОДПИСИ БД (size+mtime файлов .tausik/tausik.db
- #132 Работы по v1.7.0 (поддержка OpenCode) ведём прямо в main, без feature-ветки feat/opencode-support.
Conventions (5):
- #215 Формат evidence при закрытии задачи (что парсит task done)
- #214 Списки объектов схемы выводить из sqlite_master, а не хардкодить
- #213 Хуки-гейты команд: токенизировать (shlex), не матчить подстроку
- #204 Добавление MCP-тула: ОДНО каноническое дерево (не три зеркала) + 6 doc-count сайтов
- #196 Внутренний магазин скиллов не утекает в публичный github.com/Kibertum/tausik-skills
Dead ends (3):
- #198 Ужесточить `tausik push-ok`: выдавать push-тикет только при наличии зелёного verify-receipt на текущ
- #191 Chain 'tausik push-ok && git push' in a single Bash tool call to authorize + push atomically
- #151 FTS5 query WHERE <alias> MATCH ? (aliased fts table in MATCH)
<!-- DYNAMIC:END -->
