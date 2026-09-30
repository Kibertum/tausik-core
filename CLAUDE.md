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

- Responses are in the user's language.
- SHAPE, empty parts omitted: done → verified by → left → your call.
- KEEP BYTE-EXACT: code, shell commands, tool output, file paths, error messages. KEEP FULL PROSE: acceptance-criteria evidence, decisions, SPEC/ADAPT, task logs, handoffs.
- EXCEPTIONS: explanation asked; destructive action; three failed debugging turns → state the assumption, ask; ambiguity → one question; the rule would delete the answer itself.
- Steps numbered, one action each, the last doable in two minutes; five items per group unless completeness needs more. One tangent, once, at the end. Estimates in minutes.
- PRE-SEND: delete announcements, closing recaps, side branches, hedges; first line = next action, last line = current state.

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
Session: #279 (active) | Branch: v1-10 | TAUSIK: 1.10.0
Tasks: 1696/1783 done, 6 obsolete, 2 active, 4 blocked
Active: reading-code-costs-a-third-of-calls, answer-rules-are-in-every-prompt-not-only-consumers
Blocked: we-say-discipline-layer-field-says-harness-engineering, memory-tail-by-relevance-not-recency, site-is-rebuilt-from-the-core-docs-of-the-release, github-milestones-follow-the-rebuilt-composition
Full history (grep it for what a compaction dropped): ~\.claude\projects\d--Work-Kibertum-clients-kibertum-tausik-core\2fb2646a-10b7-4fc5-8fb4-be2e70726533.jsonl

### Memory tail
Context (5):
- #806 Счёт делает КЭШ, а не выход: 94,2% против 5,8%
- #804 Цена задачи: в долларах упала вдвое, в токенах выросла вдвое — это прайс, а не мы
- #800 Перетряска документации 1.10: два пункта из пяти отменены замером
- #798 Цена задачи в ходах выросла впятеро за полгода: медиана 6 → 32, а рычаг — Bash, 87,6% вызовов
- #746 Расход токенов TAUSIK почти целиком в cache_read: 99,5% входа, и главный рычаг — число ходов
Decisions (5):
- #408 1.10 ПЕРЕСОБРАН под три приоритета владельца (#406), утверждено владельцем в смене #279. Новая история release110-owner-
- #407 Дисциплина ответа TAUSIK — НАША, а не вендоренная. Принципы (вести с действия, нумеровать многошаговое, потолок пунктов 
- #406 1.10 ОСТАНОВЛЕН И ПЕРЕСОБИРАЕТСЯ. Указание владельца, смена #278: качество не устраивает. Три приоритета в порядке владе
- #405 Сайт живёт в ОТДЕЛЬНОМ репозитории tausik-site и ТОЛЬКО на GitLab. Публикации сайта на GitHub нет. Указание владельца, с
- #404 Код и комментарии пишутся ПО-АНГЛИЙСКИ. Указание владельца, смена #278. Отменяет часть конвенции #745 «докстринг и комме
Conventions (5):
- #799 Переименовал тест — ответь на цитаты в том же заходе, иначе регистр покраснеет следующей проверкой
- #792 Потолок без запаса есть запрет: у бюджета контекста должен быть проверяемый остаток, а не только пре
- #778 Список «к сведению» без владельца переоткрывают, а не закрывают: каждая строка обязана назвать причи
- #777 Намеренный пробел объявляется тремя строками: что НЕ гарантировано, почему живём, что держит границу
- #776 Отчёт о прогоне называет и deselected, иначе «11592 passed» скрывает выключенную ленту
Dead ends (3):
- #805 Подготовка берёт корень как root_from_service(svc) or '.'
- #802 Подготовка перед проверкой прогоняет ruff format по всему дереву
- #801 Сборщик coherence, разрешающий каждую цитату вида tests/файл.py::имя по всему дереву

**Shared knowledge — from other projects (11):**
- [decision] v139-D (клиентский mux) НЕ делается в 1.3.9 как «фикс троттлинга». Предпосылка задачи неверна для на
- [decision] Дефект brain move, найденный внутри задачи о property-тесте проекции, заведён отдельной задачей, а н
- [decision] Коэффициент калибровки на окне n=10 непригоден для прогноза срока релиза: за одну сессию #153 он про
- [convention] Windows: команду с вложенными кавычками писать ФАЙЛОМ, а не однострочником
- [convention] TAUSIK 1.8: verify --task без --relevant-files не сертифицирует закрытие задачи
- [gotcha] Windows named pipe: GENERIC_WRITE включает FILE_CREATE_PIPE_INSTANCE; сервер проверять через GetName
- [gotcha] Bash-heredoc съедает обратный слэш: regex-escape превращается в управляющий байт и grep его не показ
- [gotcha] PowerShell Set-Content -Encoding utf8 добавляет BOM и ломает bash-скрипт; here-string не идёт в stdi
- [pattern] Смоук интерактива без Playwright: headless Chrome + CDP из Node 22+
- [pattern] Установка TAUSIK в новый клиентский проект — рецепт и подводные камни
- [pattern] Проверять содержимое ответа, а не только HTTP-код
<!-- DYNAMIC:END -->
