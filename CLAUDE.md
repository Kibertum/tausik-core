# CLAUDE.md

# TAUSIK — фреймворк AI-агентов

TAUSIK conforms to SENAR v1.5 Core, self-declared, as of 2026-09-23. Задачи, сессии, качество, проектная память.

Stack: Python 3.11+ stdlib | CLI `.tausik/tausik` | DB SQLite+FTS5 | Tests pytest. Данные в `.tausik/`.

## Принципы

- **Нулевая толерантность к тихим ошибкам.** Ошибка CLI — заведи баг-задачу.
- **Agent-first.** Перед закрытием: "поймёт ли свежий агент?"
- **Dogfooding.** Мы сами пользователь. Неудобно — баг.
- **SENAR.** Контекст важнее кода. Верификация важнее скорости. Знания важнее опыта.

## Ограничения (жёсткие)

- **Нет кода без задачи.** `task start <slug>` перед Write/Edit.
- **QG-0 Context Gate.** `task start` требует goal + acceptance_criteria.
- **QG-2 Verify-First.** `tausik verify --task <slug>` (scoped, cache 10 мин) → `task done --ac-verified`. Edge-cases — `docs/ru/agent-contract.md`.
- **Проверка соразмерна правке.** Scoped verify; полная лента — в CI и один раз у тега. Тест — на поведение, не на число в документе и не на свежесть порождённого файла.
- **Нет коммита без gates.** Исправь blocking failures.
- **Нет прямого доступа к БД.** Только MCP/CLI.
- **Не угадывай аргументы CLI.** `tausik <cmd> --help` или `docs/ru/cli.md`.
- **Исходники в корне** (`scripts/`, `docs/`, `harness/`, `bootstrap/`). Не редактируй `.claude/` напрямую.
- **MCP-first.** MCP > CLI когда equivalent.
- **Git: спроси перед commit/push.**
- **Макс. 500 строк/файл.** Filesize gate (decision #190). Исключения: тесты, generated.
- **Непрерывное журналирование.** `task log <slug> "msg"` после каждого шага.
- **Документируй dead ends.** `tausik dead-end "approach" "reason"`.
- **Checkpoint по сигналу.** `/checkpoint`, `/end`.
- **Время и ёмкость сессии — сигнал, не ворота** (#376).

## Память

| Система | Когда |
|---|---|
| **TAUSIK memory** (`memory add`) | Паттерны/dead ends/conventions ЭТОГО проекта |
| **Общая база** (`memory add --global`) | Факт об инструменте, верный вне проекта; без секретов |
| **Claude auto-memory** (`~/.claude/`) | Привычки пользователя; НЕ знания и правила TAUSIK |

Типы: `pattern`, `gotcha`, `convention`, `context`, `dead_end`.
CLI: ВСЕГДА `.tausik/tausik <команда>`. НИКОГДА `python scripts/project.py` напрямую.

## Компакция

Через сжатие контекста переноси дословно: активную задачу и slug; scope и квитанцию verify; замеры сессии с числами; отменённые правила; запреты владельца; открытые развилки. Выбрасывай нарратив и вывод инструментов — не эти шесть.

## Команды

```bash
.tausik/tausik status                # обзор + предупреждения SENAR
.tausik/tausik task start <slug>     # QG-0
.tausik/tausik verify --task <slug>  # scoped, cache 10 мин
.tausik/tausik task done <slug> --ac-verified
.tausik/tausik task log <slug> "message"
```

Остальное (`dead-end`, `metrics`, `search`, `doctor`) — `docs/ru/cli.md`.

## Reference

Контракт (estimation в tool calls, SENAR, roles, custom_stacks, QG-2): `docs/ru/agent-contract.md`. CLI: `docs/ru/cli.md`. Архитектура: `docs/ru/architecture.md`.

<!-- DYNAMIC:START -->
## Current State
Session: #266 (active) | Branch: v1-9-wave | TAUSIK: 1.9.0
Tasks: 1517/1686 done, 0 active, 0 blocked

### Memory tail
Context (5):
- #726 Дополнение к #725: история I release110-open-defects — эпик #192 с 22 sub-issue (все открытые kind/b
- #725 GitHub-карта, дополнение смены #266: эпик H #188 (сайт, документация, гигиена; 16 sub-issue, новые #
- #723 GitHub-карта после перепланирования 1.10 (смена #266): milestone v1.10.0 = 7 эпиков, v1.11.0 кандида
- #722 Замер сессий #196–#265 (смена #266): ни одна из 70 смен не достигла 180 активных минут; агентов оста
- #720 RENAR 1.1 (19.09.2026) — дельты для TAUSIK: первая сторона §1.4.4, SPEC-UC, комплект описания
Decisions (5):
- #379 1.10 — СОСТАВ ДОПОЛНЕН ИСТОРИЕЙ I: ОТКРЫТЫЕ ДЕФЕКТЫ. Владелец, смена #266: «не забудь посмотреть открытые тикеты, баги, 
- #378 1.10 — СОСТАВ ДОПОЛНЕН ИСТОРИЕЙ H; ПАКЕТ И ПЛАГИН — В 2.0. Владелец, смена #266: «пакет и плагин надо в 2.0; с остальным
- #377 СЛЕДУЮЩИЕ ВЕРСИИ РАСПЛАНИРОВАНЫ (смена #266, указание владельца привести в порядок все задачи). 1.11 — кандидаты, состав
- #376 1.10 — УСТАВ И СОСТАВ ПЕРЕСМОТРЕНЫ. Владелец, смена #266: «планировать 1.10; привести в порядок все задачи, roadmap в Gi
- #375 НАПРАВЛЕНИЕ 1.10 ПЕРЕСМОТРЕНО ВЛАДЕЛЬЦЕМ (смена #266, 23.09.2026), его словами: «Мое пожелание — полное изменение логики
Conventions (5):
- #717 GitHub roadmap — как в Harvester: milestone vX.Y.Z, [KIND]-заголовки, kind/area/priority, [EPIC] с s
- #711 Проверка соразмерна правке: полная лента — CI и релизный гейт, тест — на поведение, порождённое поро
- #701 Owner forbids external artifacts (claude.ai Artifact pages): reports are answered in the terminal or
- #698 Текст отказа в документации для агента снимается с живого вызова и удерживается тестом по фразе из к
- #686 Хост, добавляемый в SCAFFOLD_IDES, проверяется ЗАМЕРОМ БИНАРЯ, а не документацией
Dead ends (3):
- #693 Verify review journal with tracked output documents as relevant files
- #692 Capture Codex PreToolUse JSON through a temporary generated command hook
- #689 Ограничить parent-tree претензии done-задач условием completed_at >= started_at верифицируемой задач

**Shared knowledge — from other projects (11):**
- [decision] v139-D (клиентский mux) НЕ делается в 1.3.9 как «фикс троттлинга». Предпосылка задачи неверна для на
- [decision] Дефект brain move, найденный внутри задачи о property-тесте проекции, заведён отдельной задачей, а н
- [decision] Коэффициент калибровки на окне n=10 непригоден для прогноза срока релиза: за одну сессию #153 он про
- [convention] Windows: команду с вложенными кавычками писать ФАЙЛОМ, а не однострочником
- [convention] TAUSIK 1.8: verify --task без --relevant-files не сертифицирует закрытие задачи
- [gotcha] JDK 21+: обновление openjdk ломает fork/exec у уже запущенной JVM (jspawnhelper сверяет версию) — се
- [gotcha] yes y | ./install.sh под set -o pipefail возвращает 141 (SIGPIPE у yes) при УСПЕШНОМ install.sh — бр
- [gotcha] NPMplus 2026-07-15-r1 / 2026-07-23-r1 молча теряют ACL всех proxy-хостов (GHSA-c8f8-6gxh-hf2g, CVSS 
- [pattern] Смоук интерактива без Playwright: headless Chrome + CDP из Node 22+
- [pattern] Установка TAUSIK в новый клиентский проект — рецепт и подводные камни
- [pattern] Проверять содержимое ответа, а не только HTTP-код
<!-- DYNAMIC:END -->
