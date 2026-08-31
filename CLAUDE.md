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
Session: none | Branch: v1-9-wave | Version: 1.8.0
Tasks: 1254/1468 done, 0 active, 0 blocked

### Memory tail
Context (5):
- #447 Замер #192: треть журнала расхода не попадала ни в один отчёт
- #441 Инвентарь ADR RENAR, пересчитанный машиной: принятых тринадцать, оценено семь, непроверенных шесть
- #434 Реестр рисков 1.9 после расформирования 1.10: 77 задач, веер снят, цепь и миграции остаются
- #433 Замер знания #189: 67 красных verify и ноль тупиков; общая база пишет-мертва 26 дней
- #432 Инвентарь ADR RENAR: принятых двенадцать, оценивали три; оценки сложности 1.9
Decisions (5):
- #283 СОБСТВЕННЫЙ ЭКСПОРТ ЗАДАЧИ ВЫЧИТАЕТСЯ ИЗ ПОКРЫТИЯ КВИТАНЦИИ — НА ОБЕИХ СТОРОНАХ, И ТОЛЬКО СВОЙ. Пустое после вычитания п
- #282 tests/tools/ СЧИТАЕТСЯ ИСХОДНИКОМ, А НЕ ТЕСТОМ. Вселенная возможных изменений храповика видимости (_tracked_sources) вкл
- #281 ГЕЙТ, НЕ СУМЕВШИЙ ИСПОЛНИТЬСЯ, ВОЗВРАЩАЕТ GateOutcome.could_not_run И БЛОКИРУЕТ; ЛЕГАСИ-ПАРА (True, "unavailable") ЗАПРЕ
- #280 АТРИБУЦИЯ РАСХОДА КЛЮЧУЕТСЯ ЗАДАЧЕЙ (схема v48, ЛОМАЮЩЕЕ). usage_events.session_id перестаёт быть NOT NULL, FK на sessio
- #279 АУДИТ-ХУК ЖИВЁТ В tests/tools/, А НЕ КОРНЕВЫМ sitecustomize.py; ГЕЙТ, ПОВТОРЯЮЩИЙ КОНФИГ ИНСТРУМЕНТА, ЗАВОДИТ ВТОРОЙ ИСТ
Conventions (5):
- #454 Вычитание бухгалтерии фреймворка вводится ВМЕСТЕ с охраной пустого покрытия — иначе снятие невыполни
- #451 Описание гейта живёт в ТРЁХ местах: правка поведения обязана пройти по всем
- #449 Мутацию гейта ставь на КАЖДОЕ исправленное место по отдельности, а не на файл целиком
- #446 SQLiteBackend и ProjectService забаселайнены: новый код кладётся модульной функцией, а не публичным 
- #445 Миграция, перестраивающая таблицу, обязана быть охраняемым пост-шагом, а не списком SQL
Dead ends (3):
- #427 Храповик видимости считает рёбра резолвера САМ (basename_reachable_tests + top_level_imports + read_
- #407 Дозаполнить 5722 существующие функции pytest ссылками на нормативные утверждения, чтобы они стали TC
- #400 Объявить бинарный PDF в relevant_files, чтобы закрыть задачу через verify вместо флага --no-file-cha

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
