---
slug: enforcement-coverage-is-two-of-five-hosts
title: "Гарантии есть на двух хостах из пяти, а текст правил одинаков для всех"
status: planning
epic: release-19-renar-conformance
story: guarantees-are-not-claude-only
complexity: complex
role: architect
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on:
  - four-ide-registries-collapse-into-one
completed_at: null
---

## Goal

ЗАМЕР #189, ПЯТЬ ПРОФИЛЕЙ: у .claude и .qwen наборы хуков СОВПАДАЮТ полностью — 22 уникальных хука на шести событиях (PreToolUse, PostToolUse, SessionStart, UserPromptSubmit, Stop, SessionEnd), различий ноль. У .opencode — ОДИН плагин tausik-qg0.js. У .kilo — ноль (в kilo.jsonc слова hook нет вовсе). У .cursor — ноль, там только текстовый .cursorrules.
ПРИ ЭТОМ ВСЕМ ПЯТЕРЫМ BOOTSTRAP КЛАДЁТ ОДИН И ТОТ ЖЕ ТЕКСТ ПРАВИЛ, объявляющий жёсткие ограничения: «нет кода без задачи», «QG-0 требует goal и acceptance_criteria», «нет коммита без гейтов», «правки .claude руками запрещены». На claude и qwen это ПРАВДА, потому что стоит PreToolUse-хук. На cursor и kilo это ПОЖЕЛАНИЕ, и ничто об этом не говорит.
ЭТО РОВНО КЛАСС РЕЛИЗА 1.9, ПЕРЕНЕСЁННЫЙ НА УРОВЕНЬ ХОСТА: гейт, который не может выполниться, не имеет права читаться пройденным. Здесь гейта нет вовсе, а текст утверждает, что он есть. Пользователь на Cursor получает те же обещания и ни одной проверки — и узнать об этом ему неоткуда.
ЧТО ДЕЛАЕТСЯ, И ЭТО ДВЕ РАЗНЫЕ ВЕЩИ. (1) ОБЪЯВИТЬ: каждый профиль получает ЧЕСТНУЮ таблицу — какие правила у него подкреплены механизмом, а какие остаются текстом; `tausik doctor` называет это состояние вслух; сгенерированный текст правил на хосте без механизма не имеет права печатать «enforced». (2) СОКРАТИТЬ РАЗРЫВ там, где хост это позволяет: у opencode есть механизм плагинов и в нём уже живёт QG-0 — значит остальные критичные проверки туда переносимы; у kilo и cursor выяснить, есть ли точка расширения вообще, и если нет — зафиксировать это как ограничение платформы, а не как наш долг.
НЕГАТИВНОЕ ПЕРВОЕ: не притворяться, что паритет достижим везде. Честное «на этом хосте правило не подкреплено» лучше, чем имитация проверки.
НЕГАТИВНОЕ ВТОРОЕ: таблица покрытия обязана строиться ИЗ ФАКТА (что реально развернулось), а не из списка намерений — иначе она разойдётся с деплоем ровно так же, как разошлись текст и механизм.

## Acceptance Criteria

## Plan

## Rollback

Генерация честной таблицы покрытия плюс, где возможно, перенос проверок в механизм хоста. Откат — git revert; развёрнутые профили перегенерируются bootstrap.

## Journal

- 2026-08-29T13:57:38Z [planning] — [#189] ПЕРЕСЕЧЕНИЕ С ОТЛОЖЕННЫМ ЭПИКОМ РАСШИРЕНИЯ — НАЙДЕНО ДО НАЧАЛА РАБОТЫ, ВТОРОЙ ПЕРЕЧЕНЬ НЕ ЗАВОДИТСЯ. Задача ext-p3-enforcement-provider-ux (эпик vscode-extension, planning, без оценки) уже содержит разбор паритета enforcement по хостам: «Qwen: gates port near-free via the Claude-identical hook contract», «Cursor: build an adapter emitting .cursor/hooks.json (beforeMCPExecution/beforeShellExecution allow/deny + failClosed) so SENAR gates hard-deny», «Kilo: accept advisory-only (re-verify no hook mechanism first)». ЭТО ПОПРАВЛЯЕТ МОЙ ЗАМЕР В ВАЖНОМ МЕСТЕ: у Cursor ноль хуков не потому, что механизма НЕТ, а потому, что мы его НЕ ГЕНЕРИРУЕМ — по их разбору у Cursor есть hooks.json с failClosed. То есть «Cursor: 0» читать как «не развёрнуто», а не как «невозможно». Для Kilo их же текст требует ПЕРЕПРОВЕРИТЬ наличие механизма, а не принимать отсутствие на веру. Задача ext-p1-provider-refactor содержит ещё два куска ровно этой работы: G6 «session model recording for non-Claude hosts (TAUSIK_AGENT_MODEL) so cost/pinning survive under GLM» — это половина задачи telemetry-and-pricing-know-one-vendor-only; G4 «collapse the four unsynchronized IDE registries (IDE_DIRS / ide_utils.IDE_REGISTRY / skill_profile_detect.VALID_IDES / providers) into one source of truth with a guard test» — это подложка таблицы покрытия, которую строит данная задача. СЛЕДСТВИЕ ДЛЯ ПЛАНА: настоящая работа по кроссмодельности НЕ новая — она заведена, не оценена ни одной задачей и отложена решением #153 («речи о расширении сейчас не идёт»). Здесь я строю ЧЕСТНОЕ ОБЪЯВЛЕНИЕ разрыва; закрытие разрыва живёт там. Разделение намеренное: объявить разрыв дёшево и обязано войти в 1.9, закрыть его — программа масштаба мажорного релиза.
- 2026-08-29T14:22:53Z [planning] — [#189] ПОПРАВКА К ССЫЛКЕ: задача ext-p1-provider-refactor, упомянутая выше, УДАЛЕНА 29.08 после расщепления на четыре оценённые задачи (provider-generates-artifacts-not-the-if-ide-ladder, four-ide-registries-collapse-into-one, session-model-recorded-on-non-claude-hosts, bundled-root-separate-from-vendored-copy). Ссылка сохранена как происхождение формулировок, а не как указатель на живую задачу — искать её в базе бесполезно. Найдено собственной проверкой плана: это ровно тот класс сгнившей ссылки, который чинит audit evidence.
- 2026-09-07T12:50:51Z [planning] — [ЗАМЕР #225, ЖИВОЙ BOOTSTRAP, НЕ ЧТЕНИЕ КОДА] Пять чистых проектов, в каждый выполнен `bootstrap.py --ide <host> --no-detect`, затем посчитано то, что реально легло на диск. Премиса замера #189 подтверждается и уточняется до чисел: | хост | хуков реального времени | правила | MCP | |---|---|---|---| | claude | 22 (PreToolUse 8, PostToolUse 9, SessionStart 1, UserPromptSubmit 1, Stop 2, SessionEnd 1) | CLAUDE.md + AGENTS.md | отдельный .mcp.json | | qwen | 22 (те же события, тот же разбор) | QWEN.md + AGENTS.md | 3 | | cursor | 0 — файла настроек с хуками нет вовсе | .cursorrules + AGENTS.md | .cursor/mcp.json | | kilo | 0 | AGENTS.md | 3 | | opencode | 0 хуков + 1 JS-плагин .opencode/plugins/tausik-qg0.js (только QG-0) | .opencode/tausik-rules.md через ключ instructions | 3 | ПОПРАВКА К СОБСТВЕННОМУ ПЕРВОМУ ПРОЧТЕНИЮ: сначала я записал «opencode не получает файла правил вовсе» — неверно, файл называется tausik-rules.md, и мой поиск по именам AGENTS.md/CLAUDE.md его не нашёл. Проверять ФАКТ, а не наличие ожидаемого имени: лог bootstrap называет файл прямо. ГЛАВНОЕ, И ОНО ХУЖЕ ФОРМУЛИРОВКИ ИСТОРИИ. Текст правил не просто «одинаков для всех пятерых» — он содержит абзац о хуках, который НЕВЕРЕН НА ВСЕХ ПЯТИ СРАЗУ, и байт-в-байт одинаков: «**PreToolUse hooks may not exist.** Cursor and a number of GPT-style agents have no hooks API: task_gate.py will not protect Rule 1. Self-enforce...». На claude и qwen, где 22 хука ЕСТЬ, он преуменьшает работающую гарантию и подталкивает агента к самоконтролю вместо опоры на рельс. На cursor, kilo и opencode, где хуков НЕТ, он говорит «может не быть» — то есть не сообщает факт, а оставляет возможность, при том что соседние строки того же файла заявляют «No exceptions» и описывают гейты как жёсткие блокировки. Ни один из пяти хостов не узнаёт из своего файла правил, что у НЕГО есть и чего у него нет. Это ровно класс «сказанное шире сделанного», под который собран весь объём 1.9, и он живёт в файле, который агент читает первым.
