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
Session: #300 (active) | Branch: v1-11-3 | TAUSIK: 1.11.2
Tasks: 1814/1895 done, 9 obsolete, 1 active, 0 blocked
Active: cut-release-1-11-3-version-changelogs-doc
Full history (grep it for what a compaction dropped): ~\.claude\projects\d--Work-Kibertum-clients-kibertum-tausik-core\2fb2646a-10b7-4fc5-8fb4-be2e70726533.jsonl

### Memory tail
Context (5):
- #925 Хвост памяти: слои и релевантность (v74, 1.11.3)
- #924 Escape-парадокс решён: левое цензурирование + умершее лечение, а не вред verify
- #922 Tier call budgets recalibrated 2026-10-06 against measured percentiles
- #851 1.11 Codex economy: cache is already high; next leverage is rounds and routing
- #812 1.11: distinguish model/speed subscription cost from token double counting
Decisions (5):
- #426 selected_tests is removed from cohort identity inputs; identity placeholders 'declared-at-run'/'selection-evidence-of-ru
- #425 Per-test provenance granularity is a declared non-goal of the verification-cohort contract: cohort identity binds conten
- #424 Escape-задача investigate-the-verified-vs-unverified-escape: политику verify оставляем как есть; агрегатную строку by_ve
- #423 Не переномеровывать эпики бэклога заранее: слот релиза освобождается только после того, как релиз фактически вышел (суще
- #422 TAUSIK 1.x завершается линией 1.11.x: после 1.11.1 выпускаются только патч-релизы 1.11.x, а следующая версия вне этой ли
Conventions (5):
- #799 Переименовал тест — ответь на цитаты в том же заходе, иначе регистр покраснеет следующей проверкой
- #792 Потолок без запаса есть запрет: у бюджета контекста должен быть проверяемый остаток, а не только пре
- #778 Список «к сведению» без владельца переоткрывают, а не закрывают: каждая строка обязана назвать причи
- #777 Намеренный пробел объявляется тремя строками: что НЕ гарантировано, почему живём, что держит границу
- #776 Отчёт о прогоне называет и deselected, иначе «11592 passed» скрывает выключенную ленту
Dead ends (3):
- #930 Duplicating the force-retired unblock test in both test_session_capacity.py and test_session_signal_
- #929 Copy the v49 'is registered' test shape verbatim for the v76 migration test (two bare asserts: N in
- #918 Verify #3521/#3522 red

**Shared knowledge — from other projects (11):**
- [decision] v139-D (клиентский mux) НЕ делается в 1.3.9 как «фикс троттлинга». Предпосылка задачи неверна для на
- [decision] Дефект brain move, найденный внутри задачи о property-тесте проекции, заведён отдельной задачей, а н
- [decision] Коэффициент калибровки на окне n=10 непригоден для прогноза срока релиза: за одну сессию #153 он про
- [convention] Windows: команду с вложенными кавычками писать ФАЙЛОМ, а не однострочником
- [convention] TAUSIK 1.8: verify --task без --relevant-files не сертифицирует закрытие задачи
- [gotcha] PWA beforeinstallprompt cannot be the sole install-action visibility trigger
- [gotcha] PECL Redis 6.3.0 breaks unpinned Docker builds
- [gotcha] Kilo после обновления отвергает tools:-строку Claude-стиля в frontmatter агентов: нужна объектная фо
- [pattern] Смоук интерактива без Playwright: headless Chrome + CDP из Node 22+
- [pattern] Установка TAUSIK в новый клиентский проект — рецепт и подводные камни
- [pattern] Проверять содержимое ответа, а не только HTTP-код
<!-- DYNAMIC:END -->
