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
Session: #213 (active) | Branch: v1-9-wave | Version: 1.8.0
Tasks: 1327/1536 done, 0 active, 1 blocked
Blocked: write-gate-reads-prose-arguments-as-redirections

### Memory tail
Context (5):
- #580 Сверка качества SENAR 9.5 в смене #212: три подметания, ни одного нового действия — всё уже под реше
- #481 Сверка SENAR 9.5 в #199: два детектора путают пример-заглушку со ссылкой, остальное здорово (supersedes #463)
- #476 Заявка RENAR-1 снята: TAUSIK печатает несоответствие по §1.5.4, право держит машина
- #472 Инвентарь ADR RENAR закрыт: принятых тринадцать, оценено тринадцать, непроверенных ноль — и шесть по
- #447 Замер #192: треть журнала расхода не попадала ни в один отчёт
Decisions (5):
- #317 ОБЪЁМ 1.9 = 25 ПОСЛЕ СМЕНЫ #213, ФИНАЛЬНЫЙ СЧЁТ СМЕНЫ, снижение с 29 (решение #314) через 26 (решение #316). Пересчитано
- #316 ОБЪЁМ 1.9 = 26 ПОСЛЕ СМЕНЫ #213, снижение с 29 (решение #314). Пересчитано КОМАНДОЙ по шести историям: gates-declare-wha
- #315 МАНИФЕСТ СООТВЕТСТВИЯ ПУБЛИКУЕТ ОСНОВАНИЕ КАЖДОГО ВЕРДИКТА §13.3 (mandatory-clauses-basis, закрытый перечень measured/de
- #314 ОБЪЁМ 1.9 = 29 ПОСЛЕ СМЕНЫ #212, ФИНАЛЬНЫЙ СЧЁТ СМЕНЫ, снижение с 31. Пересчитано КОМАНДОЙ по шести историям: gates-decl
- #313 ОБЪЁМ 1.9 = 30 ПОСЛЕ СМЕНЫ #212, снижение с 31. Пересчитано КОМАНДОЙ по шести историям (память #515): gates-declare-what
Conventions (5):
- #596 Выживший мутант бывает ЭКВИВАЛЕНТНЫМ — объявляй это в исходнике, а не дописывай тест, который не мож
- #594 Меняя опубликованный артефакт, снимай инвентарь ВСЕХ его издателей: у манифеста RENAR их два — YAML 
- #590 Константу в публикуемом артефакте называй константой: у каждого вердикта — basis из закрытого перечн
- #589 Guard в config_trust: дефолт — ФРЕЙМВОРКОВЫЙ, а не строгий; мутация «дефолт перевёрнут» обязана имет
- #578 Норму, у которой нет предмета, ОБЪЯВЛЯЙ — но объявление не есть соответствие, а его премиса требует 
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
