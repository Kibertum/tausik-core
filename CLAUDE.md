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
Tasks: 1238/1411 done, 0 active, 1 blocked
Blocked: release-18-breaking-change-notes

### Memory tail
Context (5):
- #414 Аудит качества сессий #177-#181: страховочная сеть полного прогона натянута в CI и отключена от розе
- #412 Замер трекеров #179: внешних авторов у пяти исправленных тикетов нет — посылка плана 1.9 неверна
- #406 Разбор поля 178: три оси августовского обзора, которые не вернулись, прогнаны — четыре находки, две 
- #404 Замер вырожденности наших контролей по принципу RENAR §13.9.4: три контроля дают нулевое или почти н
- #397 Аудит качества сессии #176: шесть закрытий, две находки гигиены, один дефект приехал из собственной 
Decisions (5):
- #266 СЛЕПОТА ДЕШЁВОГО ПРОГОНА ЛЕЧИТСЯ РЕБРОМ ГРАФА ИМПОРТОВ, А НЕ РУЧНЫМИ ДЕКЛАРАЦИЯМИ. План задачи (объявить CROSSCUTTING_SC
- #265 БОЛЬ «ТЕСТЫ ДУШАТ РАЗРАБОТКУ» ЛЕЧИТСЯ ТРЕМЯ СЛОЯМИ ПРОГОНА, А НЕ СОКРАЩЕНИЕМ КОРПУСА. Ни один тест не вычёркивается. Сло
- #264 РАЗРЕШИМОСТЬ ССЫЛОК НА ДОКАЗАТЕЛЬСТВА ПРОВЕРЯЕТСЯ ПЕРИОДИЧЕСКИМ АУДИТОМ, А НЕ ГЕЙТОМ ЗАКРЫТИЯ. Из трёх вариантов задачи 
- #263 ПРИНЕСЁННЫЙ ВЛАДЕЛЬЦЕМ ПЛАГИН i-have-adhd РАЗОБРАН В ДВЕ ЗАДАЧИ И ОДНО ДОПОЛНЕНИЕ, А НЕ В ПЯТЬ. Из десяти его правил в б
- #262 НЕОБЪЯВЛЕННЫЙ SCOPE (пустые relevant_files) ОСТАЁТСЯ НЕ БЛОКИРУЮЩИМ — NOT_APPLICABLE с собственным кодом причины no_scop
Conventions (5):
- #425 Правило «подмешивай пять имён к любой выборке» ОТМЕНЕНО: теперь тест выбирается по импорту, а невиди
- #424 Ложное срабатывание отсекается историей git, а не списком исключений
- #422 Коммит, расщепляющий работу двух задач, собирается содержимым файла, а не хирургией по ханкам патча
- #421 Выборка тестов по имени файла не видит гейтов, связанных со ВСЕМ деревом — они по имени не совпадают
- #419 Фоновый полный прогон, начатый ДО правок, не является ни базовой линией, ни проверкой — дерево едет 
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
