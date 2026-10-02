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
## Current State
Session: #273 (active) | Branch: v1-11 | TAUSIK: 1.11.0
Tasks: 1751/1840 done, 8 obsolete, 4 active, 1 blocked
Active: public-snapshot-tests-read-excluded-files, r111-economy-hardening-acceptance, r111-verification-cycle-replay, audit-and-trim-111-public-release-snapshot
Blocked: memory-tail-by-relevance-not-recency
Full history (grep it for what a compaction dropped): ~\.claude\projects\d--Work-Kibertum-clients-kibertum-tausik-core\2fb2646a-10b7-4fc5-8fb4-be2e70726533.jsonl

### Memory tail
Context (5):
- #851 1.11 Codex economy: cache is already high; next leverage is rounds and routing
- #812 1.11: distinguish model/speed subscription cost from token double counting
- #809 1.11 primary hosts: Claude Code, Kilo/GLM and Codex; bounded Cursor/OpenRouter
- #808 1.11: measured Codex consumption; optimize accepted-task cost with quality held constant
- #806 Счёт делает КЭШ, а не выход: 94,2% против 5,8%
Decisions (5):
- #417 Economy recovery order: host-context guard, affected-test selection, bounded validation output, evidence-based test prun
- #416 1.11 continues with an economy-hardening wave aimed at model rounds and repeated prefix
- #415 1.11 economy acceptance reuses real Codex work and forbids synthetic benchmark fan-out
- #414 1.11 validates economy primarily on Codex; Kilo/GLM is accepted theoretically
- #413 1.11 transport rule: one ProjectService implementation, two thin wrappers; skills choose the workflow, fresh MCP is pref
Conventions (5):
- #799 Переименовал тест — ответь на цитаты в том же заходе, иначе регистр покраснеет следующей проверкой
- #792 Потолок без запаса есть запрет: у бюджета контекста должен быть проверяемый остаток, а не только пре
- #778 Список «к сведению» без владельца переоткрывают, а не закрывают: каждая строка обязана назвать причи
- #777 Намеренный пробел объявляется тремя строками: что НЕ гарантировано, почему живём, что держит границу
- #776 Отчёт о прогоне называет и deselected, иначе «11592 passed» скрывает выключенную ленту
Dead ends (3):
- #866 Put the host fixture in global conftest.py
- #865 Place pytestmark before deferred project imports
- #864 Run final canonical verify with --no-prepare

**Shared knowledge — from other projects (11):**
- [decision] v139-D (клиентский mux) НЕ делается в 1.3.9 как «фикс троттлинга». Предпосылка задачи неверна для на
- [decision] Дефект brain move, найденный внутри задачи о property-тесте проекции, заведён отдельной задачей, а н
- [decision] Коэффициент калибровки на окне n=10 непригоден для прогноза срока релиза: за одну сессию #153 он про
- [convention] Windows: команду с вложенными кавычками писать ФАЙЛОМ, а не однострочником
- [convention] TAUSIK 1.8: verify --task без --relevant-files не сертифицирует закрытие задачи
- [gotcha] Windows PowerShell: одиночный CimInstance не даёт Count
- [gotcha] TAUSIK 1.10: подготовка verify (ruff format) портит JSON-файлы
- [gotcha] TAUSIK 1.10: verify в не-Python проекте — ruff format и 60-секундный конверт
- [pattern] Смоук интерактива без Playwright: headless Chrome + CDP из Node 22+
- [pattern] Установка TAUSIK в новый клиентский проект — рецепт и подводные камни
- [pattern] Проверять содержимое ответа, а не только HTTP-код
<!-- DYNAMIC:END -->
