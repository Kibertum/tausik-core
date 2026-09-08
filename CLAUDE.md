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
Session: #240 (active) | Branch: v1-9-wave | Version: 1.8.0
Tasks: 1414/1581 done, 1 active, 1 blocked
Active: the-tree-still-says-1-8-0-everywhere-while-shippin
Blocked: ci-lane-runs-on-main-only-so-the-release-branch-is

### Memory tail
Context (5):
- #677 Сверка шести условий выпуска 1.9, смена #239: четыре держатся, одно починено, одно у владельца
- #674 Аудит SENAR 9.5 за смены #235-#238: одна новая находка, и она в файле, который инструктирует агентов
- #670 Ревью пяти закрытий смен #235-#236: одна выдуманная цитата класса, ноль мёртвых объявлений, и гейт ё
- #666 Ревью пяти закрытий смены #235: одно мёртвое объявление, одна обрезанная цитата, обе мои — и сканер 
- #660 Ревью четырёх закрытий смены #233: мёртвое объявление в моей же правке о выборе инструмента
Decisions (5):
- #357 ДЕЯТЕЛЬ ЕСТЬ СОДЕРЖИМОЕ ПОДПИСАННОЙ КВИТАНЦИИ, А НЕ ВТОРОЙ ПОДПИСАНТ, И СРАВНЕНИЕ ДАЁТ ТРИ ИСХОДА. Второй ключ означал б
- #356 КРАСНАЯ ИСТОРИЯ ХРАНИТ ТОЛЬКО КРАСНОЕ, СУДИТ ПО ЗАКРЫТИЮ И СНАЧАЛА ТОЛЬКО СООБЩАЕТ. Зелёный исход не несёт сведений — те
- #355 САМОПРОВЕРКА СООТВЕТСТВИЯ МЕРЯЕТ ЦЕЛОСТНОСТЬ ДОКАЗАТЕЛЬСТВ, А НЕ СООТВЕТСТВИЕ, И ГОВОРИТ ЭТО ПЕРВОЙ СТРОКОЙ. Нормативног
- #354 СТРУКТУРНЫЕ ДЕТЕКТОРЫ ДОПОЛНЯЮТ ТЕКСТОВЫЕ RENAR, НЕ ЗАМЕНЯЮТ, И НИ ОДИН НЕ СНИМАЕТСЯ. Проверено чтением того, что тексто
- #353 ГРАФ ОТВЕЧАЕТ НА СТРУКТУРНЫЕ ВОПРОСЫ, RAG — НА СМЫСЛОВЫЕ, И ЭТО ГРАНИЦА, А НЕ ПРЕДПОЧТЕНИЕ. В проекте уже 16850 чанков c
Conventions (5):
- #673 Столбец с числом в документе обязан быть СОСЧИТАН чем-то, иначе он гниёт молча
- #669 Имя КЛАССА теста опаснее имени функции: оба выдуманных случая за две смены были классами
- #664 Критерий, требующий НОВОЙ СУЩНОСТИ В ЗАКРЫТОМ ПЕРЕЧНЕ, проверяй на совместимость с критерием «схему 
- #661 Храповик, который пинается тестом «никогда не растёт», не поднимают — работу переносят туда, где она
- #648 Сложность объявляется ДО замера и потому есть догадка — переставляй её сразу, как замер изменил объё
Dead ends (3):
- #680 Считать дрейф cli.md артефактом счётчика: комментарии '# --- ... ---' внутри блоков кода принимаются
- #678 Добавить релизную ветку v*-wave в триггер push у .github/workflows/tests.yml, чтобы опубликованная л
- #663 Гейт «утверждение упоминает символ, которого нет»: сверять имена в обратных кавычках с символьным ин

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
