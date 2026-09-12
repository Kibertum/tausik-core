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
Session: #244 (active) | Branch: v1-9-wave | Version: 1.9.0
Tasks: 1451/1616 done, 1 active, 2 blocked
Active: codex-live-acceptance-proves-the-host
Blocked: v14b-rag-nudge-replay-benchmark, scoped-pytest

### Memory tail
Context (5):
- #684 Трекеры на момент остановки смены #241: 13 открытых в GitLab, 2 в GitHub
- #683 Большое ревью 1.9, смена #241: двенадцать осей проверено, мёртвого кода ноль, три оси дали находки
- #677 Сверка шести условий выпуска 1.9, смена #239: четыре держатся, одно починено, одно у владельца
- #674 Аудит SENAR 9.5 за смены #235-#238: одна новая находка, и она в файле, который инструктирует агентов
- #670 Ревью пяти закрытий смен #235-#236: одна выдуманная цитата класса, ноль мёртвых объявлений, и гейт ё
Decisions (5):
- #362 Backlog release map after owner confirmation: 1.9 is limited to owner decisions #358, #360 and #361 (Notion removal, pro
- #361 1.9 scope is extended by owner approval: release19-proof-integrity and release19-effective-context join the release stor
- #360 1.9 scope is restated and supersedes decision #337: agent-output-discipline, context-carries-over-between-sessions, guar
- #359 Codex sub-agent TOML files are generated from harness/claude/subagents Markdown as the sole canonical instruction source
- #358 ОТ NOTION ОТКАЗЫВАЕМСЯ ЦЕЛИКОМ. Решение владельца, смена #241. Следствия шире задачи об удалении мастера настройки: уход
Conventions (5):
- #686 Хост, добавляемый в SCAFFOLD_IDES, проверяется ЗАМЕРОМ БИНАРЯ, а не документацией
- #682 Мёртвый код ищут по СИМВОЛАМ, а не по модулям, и повторяемо — потому что удаление обнажает следующий
- #673 Столбец с числом в документе обязан быть СОСЧИТАН чем-то, иначе он гниёт молча
- #669 Имя КЛАССА теста опаснее имени функции: оба выдуманных случая за две смены были классами
- #664 Критерий, требующий НОВОЙ СУЩНОСТИ В ЗАКРЫТОМ ПЕРЕЧНЕ, проверяй на совместимость с критерием «схему 
Dead ends (3):
- #689 Ограничить parent-tree претензии done-задач условием completed_at >= started_at верифицируемой задач
- #688 Treat the scoped review pytest FAIL as a test failure, then re-run with TAUSIK_VERIFY_FULL=1.
- #687 Use the standard MCP verify receipt as immediate closure evidence for verify-dynamic-state.

**Shared knowledge — from other projects (11):**
- [decision] v139-D (клиентский mux) НЕ делается в 1.3.9 как «фикс троттлинга». Предпосылка задачи неверна для на
- [decision] Дефект brain move, найденный внутри задачи о property-тесте проекции, заведён отдельной задачей, а н
- [decision] Коэффициент калибровки на окне n=10 непригоден для прогноза срока релиза: за одну сессию #153 он про
- [convention] Windows: команду с вложенными кавычками писать ФАЙЛОМ, а не однострочником
- [convention] TAUSIK 1.8: verify --task без --relevant-files не сертифицирует закрытие задачи
- [gotcha] iptables-persistent и Docker на одной машине конфликтуют
- [gotcha] Ansible copy кладёт файлы побайтово — CRLF ломает шебанг
- [gotcha] Ansible молча игнорирует ansible.cfg в world-writable каталоге
- [pattern] Проверять содержимое ответа, а не только HTTP-код
- [pattern] Мониторинг без heartbeat неотличим от мёртвого
- [pattern] TAUSIK 1.8: обёртка команды гейта обязана НАЗЫВАТЬСЯ именем инструмента
<!-- DYNAMIC:END -->
