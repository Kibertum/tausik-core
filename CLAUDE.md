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
Session: #229 (active) | Branch: v1-9-wave | Version: 1.8.0
Tasks: 1365/1558 done, 0 active, 1 blocked
Blocked: write-gate-reads-prose-arguments-as-redirections

### Memory tail
Context (5):
- #647 Ревью пяти закрытых задач в смене #228: одна находка в собственной правке, четыре подтверждения
- #644 Сверка качества SENAR 9.5 в смене #227: четыре находки, одна из них — дефект внутри моего же закрыти
- #641 Замер двух обещаний релиза 1.9 в смене #225: экономию токенов измерить нечем, гарантии есть на двух 
- #625 Сверка качества SENAR 9.5 в смене #221: три подметания, четыре гнилых ссылки в моём же закрытии найд
- #616 Сверка качества SENAR 9.5 в смене #218: три подметания, одно наблюдение вынесено в текст, новых дейс
Decisions (5):
- #338 ЭКОНОМИЯ ТОКЕНОВ ЕСТЬ СНИЖЕНИЕ ОБЪЁМА КОНТЕКСТА НА ЕДИНИЦУ РАБОТЫ, и меряется она ТОЛЬКО величиной context_tokens = inpu
- #337 ОБЪЁМ 1.9 = 22 ЗАДАЧИ ПОСЛЕ СМЕНЫ #226, сокращение с 71 (решение #326 = 74). Релиз выпускается под ДВА публичных обещани
- #336 ПУБЛИЧНО ЗАЯВЛЯЕМ SENAR 1.3. Решение владельца, смена #225. Версия 1.5 ГОТОВИТСЯ, но не готова, поэтому заявлять её нель
- #335 РЕЕСТР ПРОВЕРОК ОБЯЗАН ИМЕТЬ ТЕСТ, ТРЕБУЮЩИЙ ЖИВОГО СОВПАДЕНИЯ НА КАЖДУЮ ЗАПИСЬ. Запись, не совпавшая ни с одним настоящ
- #334 ВЕЛИЧИНА, КОТОРУЮ НЕЛЬЗЯ ИЗМЕРИТЬ ЗДЕСЬ, ДАЁТ ОТСУТСТВИЕ (None), А НЕ НОЛЬ, и потребитель сохраняет прежде записанное зн
Conventions (5):
- #646 Миграция держит ЗАМОРОЖЕННЫЙ литерал схемы, а не читает живую — иначе правка задним числом меняет пр
- #642 Цены моделей задаются в конфиге проекта и его слово главнее поставляемой таблицы; тариф — это ПАРА i
- #640 Сканер номеров обязан различать ЗАЯВЛЕНИЕ, ЦИТАТУ и ЛОКАТОР, а неоднозначную форму ОТКЛОНЯТЬ с подск
- #638 Числовое совпадение — не привязка: смотри на СУЩЕСТВИТЕЛЬНОЕ после числа, прежде чем связывать его с
- #634 Отчёты пользователю — на РУССКОМ и по существу, без пересказа проделанных шагов
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
