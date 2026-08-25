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
Tasks: 1232/1400 done, 0 active, 1 blocked
Blocked: release-18-breaking-change-notes

### Memory tail
Context (5):
- #414 Аудит качества сессий #177-#181: страховочная сеть полного прогона натянута в CI и отключена от розе
- #412 Замер трекеров #179: внешних авторов у пяти исправленных тикетов нет — посылка плана 1.9 неверна
- #406 Разбор поля 178: три оси августовского обзора, которые не вернулись, прогнаны — четыре находки, две 
- #404 Замер вырожденности наших контролей по принципу RENAR §13.9.4: три контроля дают нулевое или почти н
- #397 Аудит качества сессии #176: шесть закрытий, две находки гигиены, один дефект приехал из собственной 
Decisions (5):
- #261 ТИКЕТ ПОТРЕБИТЕЛЯ О НАШЕМ ДЕФЕКТЕ ПЕРЕЕЗЖАЕТ В НАШ ТРЕКЕР, А У ПОТРЕБИТЕЛЯ НЕ ТРОГАЕТСЯ НИЧЕГО. Sortula #49 перенесён в 
- #260 ПУБЛИКУЕТСЯ ТЕКУЩЕЕ ДЕРЕВО ЦЕЛИКОМ, ВКЛЮЧАЯ КОММИТ 2c95b81, И ДУБЛИРУЕТСЯ В GITLAB. Владелец выбрал вариант D из четырёх
- #259 ПОРЯДОК РАБОТ ВЫРАЖАЕТСЯ РЕБРОМ МЕЖДУ ЗАДАЧАМИ, А НЕ ЧИСЛОМ ПРИОРИТЕТА. Из трёх вариантов задачи task-next-cannot-expres
- #258 ВЫЧЕРКИВАНИЕ В ПАМЯТИ ЕСТЬ НАДПИСЬ ПОВЕРХ СО СЛЕДОМ, А НЕ УДАЛЕНИЕ. Текст записи меняется, но остаётся проверяемая запис
- #257 GITHUB СТАНОВИТСЯ ОСНОВНЫМ МЕСТОМ РАЗРАБОТКИ, GITLAB — ЗЕРКАЛО И САЙТ. Проекция tausik/ ПУБЛИКУЕТСЯ. Историю НЕ переписы
Conventions (5):
- #417 Тест, утверждающий ЛИТЕРАЛ исходника продукта, ломается на каждом рефакторинге и не проверяет обещан
- #416 Замер, у которого быстрая и медленная тропы меряются РАЗНЫМ окном ожидания, врёт в пользу быстрой
- #413 Отчёт о вычеркивании, перечисляющий вычеркнутое, есть новая утечка — включая доказательство чистоты
- #409 Проверка, читающая рабочее дерево, обязана вычесть из него бухгалтерию самого фреймворка
- #408 Документы владельца живут в репозитории, а не во внешних артефактах
Dead ends (3):
- #407 Дозаполнить 5722 существующие функции pytest ссылками на нормативные утверждения, чтобы они стали TC
- #400 Объявить бинарный PDF в relevant_files, чтобы закрыть задачу через verify вместо флага --no-file-cha
- #396 Отсутствие каталога-источника считать поводом отказаться от проверки дрейфа

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
