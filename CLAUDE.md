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

Остальное — `docs/ru/cli.md`.

## Reference

Контракт (estimation в tool calls, SENAR, roles, custom_stacks, QG-2): `docs/ru/agent-contract.md`. Архитектура: `docs/ru/architecture.md`. Что НЕ гарантировано: `docs/ru/known-limitations.md`.

<!-- DYNAMIC:START -->
## Current State
Session: #277 (active) | Branch: v1-10 | TAUSIK: 1.9.0
Tasks: 1609/1718 done, 3 obsolete, 1 active, 0 blocked
Active: closure-citations-rot-is-detected-but-never-acted-on
Full history (grep it for what a compaction dropped): ~\.claude\projects\d--Work-Kibertum-clients-kibertum-tausik-core\117ec53f-dbde-45ea-93f1-eb22c72335fd.jsonl

### Memory tail
Context (5):
- #746 Расход токенов TAUSIK почти целиком в cache_read: 99,5% входа, и главный рычаг — число ходов
- #726 Дополнение к #725: история I release110-open-defects — эпик #192 с 22 sub-issue (все открытые kind/b
- #725 GitHub-карта, дополнение смены #266: эпик H #188 (сайт, документация, гигиена; 16 sub-issue, новые #
- #723 GitHub-карта после перепланирования 1.10 (смена #266): milestone v1.10.0 = 7 эпиков, v1.11.0 кандида
- #722 Замер сессий #196–#265 (смена #266): ни одна из 70 смен не достигла 180 активных минут; агентов оста
Decisions (5):
- #397 1.10 ДОПОЛНЕН ИСТОРИЕЙ generated-code-is-lean-and-ascii. Указание владельца, смена #277: проекты на старых TAUSIK объявл
- #396 1.10 ДОПОЛНЕН ИСТОРИЕЙ harness-costs-less-per-task. Указание владельца, смена #275: внедрить лучшие практики из разбора 
- #395 Разделение обязанностей L3 проверяется при ЗАПИСИ: review record --type L3 требует модели ревьюера и автора и отказывает
- #394 tools/list отдаёт ttlMs=0 и cacheScope=private, скрытие по scope_tools сохраняется (github#91)
- #393 Пользовательский тир с 1.10 — ~/.config/tausik/config.json. Старый ~/.tausik/config.json читается, только если он единст
Conventions (5):
- #745 Имя латиницей, проза на любом языке; исключение объявляется замером цены, а не вкусом
- #742 Generated trees are declared once in scripts/derived_trees.py; exporters and checks read it
- #738 Ответ владельцу: итог первой строкой, дальше только факты списком; без пересказа процесса
- #728 Не объявлять CHANGELOG и общие страницы docs в --relevant-files задачи: следующая запись в CHANGELOG
- #717 GitHub roadmap — как в Harvester: milestone vX.Y.Z, [KIND]-заголовки, kind/area/priority, [EPIC] с s
Dead ends (3):
- #749 Крупный ответ инструмента писать в файл и возвращать путь с хвостом
- #748 Вынести динамический блок из CLAUDE.md в отдельный файл, чтобы инструкции попали в кэшируемый префик
- #693 Verify review journal with tracked output documents as relevant files

**Shared knowledge — from other projects (11):**
- [decision] v139-D (клиентский mux) НЕ делается в 1.3.9 как «фикс троттлинга». Предпосылка задачи неверна для на
- [decision] Дефект brain move, найденный внутри задачи о property-тесте проекции, заведён отдельной задачей, а н
- [decision] Коэффициент калибровки на окне n=10 непригоден для прогноза срока релиза: за одну сессию #153 он про
- [convention] Windows: команду с вложенными кавычками писать ФАЙЛОМ, а не однострочником
- [convention] TAUSIK 1.8: verify --task без --relevant-files не сертифицирует закрытие задачи
- [gotcha] PowerShell Set-Content -Encoding utf8 добавляет BOM и ломает bash-скрипт; here-string не идёт в stdi
- [gotcha] pgrep -f в ssh-команде ловит сам себя — проверять по PID-файлу, а не по имени процесса
- [gotcha] sh (Git Bash на Windows): кириллица в ИМЕНАХ переменных — не переменная, а команда
- [pattern] Смоук интерактива без Playwright: headless Chrome + CDP из Node 22+
- [pattern] Установка TAUSIK в новый клиентский проект — рецепт и подводные камни
- [pattern] Проверять содержимое ответа, а не только HTTP-код
<!-- DYNAMIC:END -->
