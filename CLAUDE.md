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
- **Макс. 500 строк/файл.** Filesize gate (промежуточный лимит, decision #190). Исключения: тесты, generated.
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
Session: #166 (active) | Branch: main | Version: 1.8.0
Tasks: 1208/1278 done, 0 active, 1 blocked
Blocked: release-18-breaking-change-notes

### Memory tail
Context (5):
- #369 Аудит качества сессии #158: четыре находки, три из них — тихие отказы разной глубины
- #363 Аудит объёма 1.8 по запросу владельца (сессия #155): на shared brain идёт 180 вызовов из 1927, а 85%
- #362 Учёт остатка 1.8 на сессию #155: 1927 вызовов не сдвинулись, потому что вся работа шла по блокерам т
- #358 Аудит качества сессии #153: ревью партии #152 нашло девять дефектов, четыре из них блокируют тег 1.8
- #337 Quality sweep сессии #147: репо чистое, накопленный незакоммиченный батч размывает расписки
Decisions (5):
- #234 ПОРЯДОК ВЫКЛАДКИ ЗЕРКАЛА ПОПРАВЛЕН для выпусков с внешним вкладом. До сих пор каждый релиз ложился на github/main ОДНИМ 
- #233 Внешний PR #5 (Okianiwa, покрытие хуков) ИДЁТ В 1.9 и вливается МЕРЖЕМ в ветку release/1.9 зеркала, а не переписывается 
- #232 Публичное зеркало github.com/Kibertum/tausik-core везёт из проекции tausik/ ТОЛЬКО gates.json, а историю задач и решений
- #231 Дефект cmd-wrapper-silently-truncates-multiline-arguments ВЫНОСИТСЯ В 1.9 явным решением, а не умалчивается местом хране
- #230 Задача throwaway-db-guard-has-no-caller-while-its-docstring-names-one ВЫНОСИТСЯ В 1.9 явным решением, а не остаётся молч
Conventions (5):
- #383 Правка «сказать главное первым» применяется к КАЖДОЙ двери в релиз, а не к той, на которую показали
- #382 Вклад снаружи остаётся вкладом автора: зеркало не имеет права стереть авторство squash'ем
- #381 Гейт проверяет ИСТИННОСТЬ сказанного, но не ПОРЯДОК — главное называют первым руками
- #378 Предикат о ФОРМЕ пути читает написание, а не спрашивает платформу
- #375 Дефект относят к релизу по ДОСТУПНОСТИ СНАРУЖИ, а не по месту кода
Dead ends (3):
- #370 Добавить decision_delete в _OPS генератора test_state_projection_tracks_db, чтобы храповик наблюдал
- #355 Рэтчет покрытия через AST: искать в сервисных модулях методы, вызывающие self.be.&lt;метод с литерал
- #324 Исправить «2× байтовый штраф за кириллицу» в лимите поля decision (tausik_decide)

**Shared knowledge — from other projects (6):**
- [decision] v139-D (клиентский mux) НЕ делается в 1.3.9 как «фикс троттлинга». Предпосылка задачи неверна для на
- [decision] Дефект brain move, найденный внутри задачи о property-тесте проекции, заведён отдельной задачей, а н
- [decision] Коэффициент калибровки на окне n=10 непригоден для прогноза срока релиза: за одну сессию #153 он про
- [gotcha] Mobile mux must be opt-in: yamux optimistic-open can't detect non-mux servers
- [gotcha] FTS5 MATCH dash trap
- [pattern] Mixin composition for Service layer
<!-- DYNAMIC:END -->
