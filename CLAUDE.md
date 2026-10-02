# CLAUDE.md

# TAUSIK — фреймворк AI-агентов

TAUSIK conforms to SENAR v1.5 Core, self-declared, as of 2026-09-23.

## Принципы

- **Нулевая толерантность к тихим ошибкам.** Ошибка CLI — заведи баг-задачу.
- **Agent-first.** Перед закрытием: "поймёт ли свежий агент?"
- **Dogfooding.** Мы сами пользователь. Неудобно — баг.

## Ограничения (жёсткие)

**Что имеет право стоять здесь:** `docs/ru/claude-md-guide.md`.


- **Нет кода без задачи.** `task start <slug>` перед Write/Edit.
- **QG-0 Context Gate.** `task start` требует goal + acceptance_criteria.
- **QG-2 Verify-First.** `task done <slug> --ac-verified --verify` — проверка и закрытие одним вызовом.
- **Проверка соразмерна правке.** Scoped verify; полная лента — CI и тег. Тест — на поведение.
- **Нет коммита без gates.** Исправь blocking failures.
- **Нет прямого доступа к БД.** Только MCP/CLI.
- **Не угадывай аргументы CLI.** `tausik <cmd> --help` или `docs/ru/cli.md`.
- **Не редактируй `.claude/`** — исходники в корне (`scripts/`, `docs/`, `harness/`, `bootstrap/`).
- **MCP-first**, если есть MCP-эквивалент.
- **Git: спроси перед commit/push.**
- **Макс. 500 строк/файл** (гейт filesize).
- **Журналируй:** `task log <slug> "msg"` после каждого шага.
- **Время и ёмкость сессии — сигнал, не ворота** (#376).
- **Код и комментарии по-английски** (#404).

## Answer shape (#407)

- Use user's language.
- SHAPE, omit empty: done → verified by → left → your call.
- PROSE (no ASD-STE100 claim): name actor/action; active voice if natural; one action/sentence; one term/concept; short paragraphs.
- BYTE-EXACT: code, shell commands, tool output, file paths, error messages; FULL: acceptance-criteria evidence, decisions, SPEC/ADAPT, task logs, handoffs.
- EXCEPTIONS: explanation asked; destructive action; 3 failed debug turns → assumption + question; ambiguity → one question; rule deletes answer itself.
- Steps: numbered, one action each, last ≤2 min; ≤5/group unless more needed; tangent last; estimate if useful.
- PRE-SEND: delete announcements, recaps, side branches, empty hedges; first line = next action; last = current state.

## Память

| Система | Когда |
|---|---|
| **TAUSIK memory** (`memory add`) | Паттерны/dead ends/conventions ЭТОГО проекта |
| **Общая база** (`memory add --global`) | Факт об инструменте, верный вне проекта; без секретов |
| **Claude auto-memory** (`~/.claude/`) | Привычки пользователя; НЕ знания и правила TAUSIK |

CLI: ВСЕГДА `.tausik/tausik <команда>`. НИКОГДА `python scripts/project.py` напрямую.

## Компакция

Через сжатие контекста переноси дословно: активную задачу и slug; scope и квитанцию verify; замеры сессии с числами; отменённые правила; запреты владельца; открытые развилки. Выбрасывай нарратив и вывод инструментов — не эти шесть.

## Reference

Контракт (estimation в tool calls, SENAR, roles, custom_stacks, QG-2): `docs/ru/agent-contract.md`. Архитектура: `docs/ru/architecture.md`. Что НЕ гарантировано: `docs/ru/known-limitations.md`.

<!-- DYNAMIC:START -->
<!-- DYNAMIC:END -->
