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
Session: #177 (active) | Branch: main | Version: 1.8.0
Tasks: 1221/1342 done, 3 active, 1 blocked
Active: survey-document-conclusions-not-transcripts, roadmap-order-and-cut-not-add, mcp-update-claudemd-erases-the-memory-tail
Blocked: release-18-breaking-change-notes

### Memory tail
Context (5):
- #397 Аудит качества сессии #176: шесть закрытий, две находки гигиены, один дефект приехал из собственной 
- #369 Аудит качества сессии #158: четыре находки, три из них — тихие отказы разной глубины
- #363 Аудит объёма 1.8 по запросу владельца (сессия #155): на shared brain идёт 180 вызовов из 1927, а 85%
- #362 Учёт остатка 1.8 на сессию #155: 1927 вызовов не сдвинулись, потому что вся работа шла по блокерам т
- #358 Аудит качества сессии #153: ревью партии #152 нашло девять дефектов, четыре из них блокируют тег 1.8
Decisions (5):
- #244 ДОРОЖНАЯ КАРТА ПОСТРОЕНА НА ОЧЕРЁДНОСТИ, А НЕ НА СОКРАЩЕНИИ. В бэклоге 113 задач на 5357 вызовов; при расходе 0.63 от бю
- #243 ИССЛЕДОВАНИЕ АНАЛОГОВ ТРЁХ МЕТОДОЛОГИЙ ДАЛО РАЗНЫЕ ОТВЕТЫ, И ЭТО ГЛАВНОЕ. Ниши SENAR и RENAR ПУСТЫ, ниша PHASE ЗАНЯТА со
- #242 ЧУЖАЯ СИЛЬНАЯ СТОРОНА ВСКРЫЛА НАШ СОБСТВЕННЫЙ ПЕРЕБОР В ОБЕЩАНИИ. У HELM офлайновость верификатора закреплена тестом: об
- #241 АДВЕРСАРИАЛЬНЫЙ ОБЗОР ОПРОВЕРГ УТВЕРЖДЕНИЕ ОБ УНИКАЛЬНОСТИ В ЕГО ТЕКУЩЕЙ ФОРМЕ. Три оси из шести (остальные упали на обр
- #240 ИЗ IMMUNE И УРОБОРОСА (github.com/razzant/ouroboros, MIT) ВЗЯТО ДВА ПРИНЦИПА И ОТВЕРГНУТ ОДИН, ЯВНО. Взято в 1.10: буква
Conventions (5):
- #394 Число в константе и обещание в докстринге рядом с ней — одно утверждение, и проверять надо оба
- #392 Вопрос о ТОЖДЕСТВЕ каталога решается realpath; написание сравнивают только тогда, когда спрашивают о
- #389 Читатель развёрнутой копии обязан спрашивать источник у той же функции, что и копировщик
- #386 Тест, закрепляющий адрес, обязан проверять достижимость, а не написание
- #384 Планировать по агрегату per-tier, а не по строке калибровки на окне n=10
Dead ends (3):
- #396 Отсутствие каталога-источника считать поводом отказаться от проверки дрейфа
- #391 Выводить адрес пользовательского тира из config_trust.user_config_path ради единственного источника 
- #370 Добавить decision_delete в _OPS генератора test_state_projection_tracks_db, чтобы храповик наблюдал

**Shared knowledge — from other projects (10):**
- [decision] v139-D (клиентский mux) НЕ делается в 1.3.9 как «фикс троттлинга». Предпосылка задачи неверна для на
- [decision] Дефект brain move, найденный внутри задачи о property-тесте проекции, заведён отдельной задачей, а н
- [decision] Коэффициент калибровки на окне n=10 непригоден для прогноза срока релиза: за одну сессию #153 он про
- [convention] Windows: команду с вложенными кавычками писать ФАЙЛОМ, а не однострочником
- [convention] TAUSIK 1.8: verify --task без --relevant-files не сертифицирует закрытие задачи
- [gotcha] Ansible: модуль uri ВСЕГДА рапортует changed=false — идемпотентность по PLAY RECAP не проверяется
- [gotcha] После bootstrap TAUSIK MCP-сервер держит СТАРЫЙ код — до перезапуска IDE работать через CLI
- [gotcha] TAUSIK 1.8: отвергнутая команда гейта не краснеет, а молча откатывается к дефолту
- [pattern] TAUSIK 1.8: обёртка команды гейта обязана НАЗЫВАТЬСЯ именем инструмента
- [pattern] Mixin composition for Service layer
<!-- DYNAMIC:END -->
