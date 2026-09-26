---
slug: enforcement-coverage-is-two-of-five-hosts
title: "Гарантии есть на двух хостах из пяти, а текст правил одинаков для всех"
status: done
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
relevant_files:
  - "scripts/enforcement_coverage.py"
  - "scripts/service_doctor_enforcement.py"
  - "scripts/service_doctor_external.py"
  - "scripts/project_cli_doctor.py"
  - "bootstrap/bootstrap_templates.py"
  - "bootstrap/bootstrap_generate.py"
  - "bootstrap/bootstrap_qwen.py"
  - "bootstrap/bootstrap_opencode.py"
  - "tests/test_enforcement_coverage.py"
  - "tests/test_doctor_commit_hooks.py"
  - "tests/test_doctor_backlog_hygiene.py"
  - "docs/ru/doctor.md"
  - "docs/en/doctor.md"
  - "docs/ru/troubleshooting.md"
  - "docs/en/troubleshooting.md"
  - QWEN.md
scope_paths:
  - "bootstrap/"
  - "scripts/"
  - "harness/overrides/"
  - "tests/"
  - "docs/ru/"
  - "docs/en/"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on:
  - four-ide-registries-collapse-into-one
completed_at: "2026-09-07T20:45:41Z"
resolution: null
resolution_reason: null
---

## Goal

ЗАМЕР #189, ПЯТЬ ПРОФИЛЕЙ: у .claude и .qwen наборы хуков СОВПАДАЮТ полностью — 22 уникальных хука на шести событиях (PreToolUse, PostToolUse, SessionStart, UserPromptSubmit, Stop, SessionEnd), различий ноль. У .opencode — ОДИН плагин tausik-qg0.js. У .kilo — ноль (в kilo.jsonc слова hook нет вовсе). У .cursor — ноль, там только текстовый .cursorrules.
ПРИ ЭТОМ ВСЕМ ПЯТЕРЫМ BOOTSTRAP КЛАДЁТ ОДИН И ТОТ ЖЕ ТЕКСТ ПРАВИЛ, объявляющий жёсткие ограничения: «нет кода без задачи», «QG-0 требует goal и acceptance_criteria», «нет коммита без гейтов», «правки .claude руками запрещены». На claude и qwen это ПРАВДА, потому что стоит PreToolUse-хук. На cursor и kilo это ПОЖЕЛАНИЕ, и ничто об этом не говорит.
ЭТО РОВНО КЛАСС РЕЛИЗА 1.9, ПЕРЕНЕСЁННЫЙ НА УРОВЕНЬ ХОСТА: гейт, который не может выполниться, не имеет права читаться пройденным. Здесь гейта нет вовсе, а текст утверждает, что он есть. Пользователь на Cursor получает те же обещания и ни одной проверки — и узнать об этом ему неоткуда.
ЧТО ДЕЛАЕТСЯ, И ЭТО ДВЕ РАЗНЫЕ ВЕЩИ. (1) ОБЪЯВИТЬ: каждый профиль получает ЧЕСТНУЮ таблицу — какие правила у него подкреплены механизмом, а какие остаются текстом; `tausik doctor` называет это состояние вслух; сгенерированный текст правил на хосте без механизма не имеет права печатать «enforced». (2) СОКРАТИТЬ РАЗРЫВ там, где хост это позволяет: у opencode есть механизм плагинов и в нём уже живёт QG-0 — значит остальные критичные проверки туда переносимы; у kilo и cursor выяснить, есть ли точка расширения вообще, и если нет — зафиксировать это как ограничение платформы, а не как наш долг.
НЕГАТИВНОЕ ПЕРВОЕ: не притворяться, что паритет достижим везде. Честное «на этом хосте правило не подкреплено» лучше, чем имитация проверки.
НЕГАТИВНОЕ ВТОРОЕ: таблица покрытия обязана строиться ИЗ ФАКТА (что реально развернулось), а не из списка намерений — иначе она разойдётся с деплоем ровно так же, как разошлись текст и механизм.

## Acceptance Criteria

ЗАМЕР СМЕНЫ #230, С ДИСКА, НЕ ИЗ СПИСКА НАМЕРЕНИЙ. claude 23 хука на 6 событиях, qwen 23 на 6 (паритет держится), cursor 0, kilo 0, opencode 1 плагин. Всем пятерым уходит ОДИН И ТОТ ЖЕ текст правил.

НАЙДЕНО ТОЧНОЕ МЕСТО ЛЖИ: HARD_CONSTRAINTS открывается строкой «Quality gates enforce these automatically», и она уходит хостам с НУЛЁМ хуков. Оговорка существует, но она рукописная, покрывает ОДНО правило из одиннадцати (Rule 1) и только у Cursor, и вдобавок называет НЕВЕРНУЮ причину — «no hooks API», тогда как у Cursor механизм есть (hooks.json с failClosed), и мы его просто не генерируем.

AC1. УТВЕРЖДЕНИЕ О ПРИНУЖДЕНИИ СТАНОВИТСЯ УСЛОВНЫМ. Строка «Quality gates enforce these automatically» на хосте без механизма реального времени НЕ печатается; вместо неё печатается честное «на этом хосте перечисленное ниже — инструкции, а не проверки».
AC2. ТАБЛИЦА ПОКРЫТИЯ ВЫВОДИТСЯ ИЗ ФАКТА. Блок строится из ТОГО, ЧТО РЕАЛЬНО РАЗВОРАЧИВАЕТСЯ для этого хоста (полезная нагрузка хуков, которую кладёт bootstrap), а не из перечня в тексте. Реестр «правило -> хук» НЕ заводится: он разошёлся бы с деплоем ровно так же, как разошлись текст и механизм (решение #335).
AC3. ПРИЧИНА НАЗВАНА ВЕРНО. Там, где механизм у хоста ЕСТЬ, а мы его не генерируем (Cursor), текст говорит именно это, а не «платформа не умеет». Неверная причина хуже отсутствия причины: она закрывает вопрос, который открыт.
AC4. doctor НАЗЫВАЕТ СОСТОЯНИЕ ВСЛУХ. `tausik doctor` печатает, сколько правил на текущем хосте подкреплено механизмом, а сколько остаются текстом.
AC5 (НЕГАТИВНОЕ ПЕРВОЕ ИЗ ЗАДАЧИ). Паритет НЕ имитируется: на хосте без механизма ничего не притворяется проверкой, и генерируемый текст не печатает «enforced». Проверяется тестом на сгенерированном теле для каждого из пяти хостов.
AC6 (НЕГАТИВНОЕ ВТОРОЕ ИЗ ЗАДАЧИ, ПРОВЕРКА МУТАЦИЕЙ). Таблица обязана СЛЕДОВАТЬ за деплоем: тест снимает у хоста механизм и убеждается, что блок покрытия меняется на честный, а не остаётся прежним. Блок, не меняющийся при исчезновении механизма, есть список намерений.
AC7. ГРАНИЦА СОБЛЮДЕНА. Разрыв ОБЪЯВЛЯЕТСЯ, а не закрывается: hooks.json для Cursor здесь НЕ генерируется, плагины для kilo не пишутся. Проверяется тем, что число развёрнутых хуков у cursor и kilo остаётся нулём.

## Plan

## Rollback

Генерация честной таблицы покрытия плюс, где возможно, перенос проверок в механизм хоста. Откат — git revert; развёрнутые профили перегенерируются bootstrap.

## Journal

- 2026-08-29T13:57:38Z [planning] — [#189] ПЕРЕСЕЧЕНИЕ С ОТЛОЖЕННЫМ ЭПИКОМ РАСШИРЕНИЯ — НАЙДЕНО ДО НАЧАЛА РАБОТЫ, ВТОРОЙ ПЕРЕЧЕНЬ НЕ ЗАВОДИТСЯ. Задача ext-p3-enforcement-provider-ux (эпик vscode-extension, planning, без оценки) уже содержит разбор паритета enforcement по хостам: «Qwen: gates port near-free via the Claude-identical hook contract», «Cursor: build an adapter emitting .cursor/hooks.json (beforeMCPExecution/beforeShellExecution allow/deny + failClosed) so SENAR gates hard-deny», «Kilo: accept advisory-only (re-verify no hook mechanism first)». ЭТО ПОПРАВЛЯЕТ МОЙ ЗАМЕР В ВАЖНОМ МЕСТЕ: у Cursor ноль хуков не потому, что механизма НЕТ, а потому, что мы его НЕ ГЕНЕРИРУЕМ — по их разбору у Cursor есть hooks.json с failClosed. То есть «Cursor: 0» читать как «не развёрнуто», а не как «невозможно». Для Kilo их же текст требует ПЕРЕПРОВЕРИТЬ наличие механизма, а не принимать отсутствие на веру. Задача ext-p1-provider-refactor содержит ещё два куска ровно этой работы: G6 «session model recording for non-Claude hosts (TAUSIK_AGENT_MODEL) so cost/pinning survive under GLM» — это половина задачи telemetry-and-pricing-know-one-vendor-only; G4 «collapse the four unsynchronized IDE registries (IDE_DIRS / ide_utils.IDE_REGISTRY / skill_profile_detect.VALID_IDES / providers) into one source of truth with a guard test» — это подложка таблицы покрытия, которую строит данная задача. СЛЕДСТВИЕ ДЛЯ ПЛАНА: настоящая работа по кроссмодельности НЕ новая — она заведена, не оценена ни одной задачей и отложена решением #153 («речи о расширении сейчас не идёт»). Здесь я строю ЧЕСТНОЕ ОБЪЯВЛЕНИЕ разрыва; закрытие разрыва живёт там. Разделение намеренное: объявить разрыв дёшево и обязано войти в 1.9, закрыть его — программа масштаба мажорного релиза.
- 2026-08-29T14:22:53Z [planning] — [#189] ПОПРАВКА К ССЫЛКЕ: задача ext-p1-provider-refactor, упомянутая выше, УДАЛЕНА 29.08 после расщепления на четыре оценённые задачи (provider-generates-artifacts-not-the-if-ide-ladder, four-ide-registries-collapse-into-one, session-model-recorded-on-non-claude-hosts, bundled-root-separate-from-vendored-copy). Ссылка сохранена как происхождение формулировок, а не как указатель на живую задачу — искать её в базе бесполезно. Найдено собственной проверкой плана: это ровно тот класс сгнившей ссылки, который чинит audit evidence.
- 2026-09-07T12:50:51Z [planning] — [ЗАМЕР #225, ЖИВОЙ BOOTSTRAP, НЕ ЧТЕНИЕ КОДА] Пять чистых проектов, в каждый выполнен `bootstrap.py --ide <host> --no-detect`, затем посчитано то, что реально легло на диск. Премиса замера #189 подтверждается и уточняется до чисел: | хост | хуков реального времени | правила | MCP | |---|---|---|---| | claude | 22 (PreToolUse 8, PostToolUse 9, SessionStart 1, UserPromptSubmit 1, Stop 2, SessionEnd 1) | CLAUDE.md + AGENTS.md | отдельный .mcp.json | | qwen | 22 (те же события, тот же разбор) | QWEN.md + AGENTS.md | 3 | | cursor | 0 — файла настроек с хуками нет вовсе | .cursorrules + AGENTS.md | .cursor/mcp.json | | kilo | 0 | AGENTS.md | 3 | | opencode | 0 хуков + 1 JS-плагин .opencode/plugins/tausik-qg0.js (только QG-0) | .opencode/tausik-rules.md через ключ instructions | 3 | ПОПРАВКА К СОБСТВЕННОМУ ПЕРВОМУ ПРОЧТЕНИЮ: сначала я записал «opencode не получает файла правил вовсе» — неверно, файл называется tausik-rules.md, и мой поиск по именам AGENTS.md/CLAUDE.md его не нашёл. Проверять ФАКТ, а не наличие ожидаемого имени: лог bootstrap называет файл прямо. ГЛАВНОЕ, И ОНО ХУЖЕ ФОРМУЛИРОВКИ ИСТОРИИ. Текст правил не просто «одинаков для всех пятерых» — он содержит абзац о хуках, который НЕВЕРЕН НА ВСЕХ ПЯТИ СРАЗУ, и байт-в-байт одинаков: «**PreToolUse hooks may not exist.** Cursor and a number of GPT-style agents have no hooks API: task_gate.py will not protect Rule 1. Self-enforce...». На claude и qwen, где 22 хука ЕСТЬ, он преуменьшает работающую гарантию и подталкивает агента к самоконтролю вместо опоры на рельс. На cursor, kilo и opencode, где хуков НЕТ, он говорит «может не быть» — то есть не сообщает факт, а оставляет возможность, при том что соседние строки того же файла заявляют «No exceptions» и описывают гейты как жёсткие блокировки. Ни один из пяти хостов не узнаёт из своего файла правил, что у НЕГО есть и чего у него нет. Это ровно класс «сказанное шире сделанного», под который собран весь объём 1.9, и он живёт в файле, который агент читает первым.
- 2026-09-07T20:42:22Z [implementation] — ЗАМЕР ДО ПРОЕКТИРОВАНИЯ (смена #230, живое дерево): claude 23 команды хуков / 6 событий, qwen 23/6, opencode 1 плагин, cursor 0, kilo 0. Все пятеро получали ОДИН текст, открывавшийся строкой Quality gates enforce these automatically. На двух из пяти она была ложью.
- 2026-09-07T20:42:23Z [implementation] — РЕШЕНИЕ: утверждение о принуждении ВЫВОДИТСЯ из артефактов на диске (scripts/enforcement_coverage.py), а не берётся из таблицы правило->механизм. Такая таблица записала бы намерение и разошлась бы с делом ровно так же, как разошёлся текст правил с механизмом (решение #335). Считаются ДВЕ формы артефакта: команды хуков в settings.json и плагины в plugins/ — у opencode механизм плагинный, и назвать его хуком было бы ложью того же семейства.
- 2026-09-07T20:42:23Z [implementation] — ТРИ ОТВЕТА, НЕ ДВА. Хост с механизмом получает счётный claim; хост без механизма — честное ON THIS HOST THE RULES BELOW ARE INSTRUCTIONS, NOT CHECKS; файл, который читают НЕСКОЛЬКО хостов (AGENTS.md у codex и kilo), получает UNKNOWN. Отсутствие, а не ноль (решение #334): ответить там not enforced значило бы угадать хост, которого никто не назвал.
- 2026-09-07T20:42:37Z [implementation] — ДЕФЕКТ В СОБСТВЕННОЙ ПЕРВОЙ РЕДАКЦИИ, пойман doctor: проба лежала в bootstrap/, а doctor в развёрнутом профиле выдал could not validate: No module named bootstrap_enforcement. Bootstrap кладёт в профиль scripts/ и НЕ кладёт bootstrap/ — зависимость обязана идти только в эту сторону. Модуль перенесён в scripts/. Вторая находка того же захода: мой словарь host->rules_file был копией ide_utils.IDE_REGISTRY, который уже держит и config_dir, и rules_file. Копия удалена; host-agnostic выводится из самого реестра — файл, на который ссылаются два хоста, не говорит ни за одного.
- 2026-09-07T20:42:37Z [implementation] — НАЙДЕНО ПО ХОДУ, ИСПРАВЛЕНО: (1) вторая копия неверной причины — MULTIMODEL_NOTE утверждал Cursor and a number of GPT-style agents have no hooks API; это заявление о ЧУЖОЙ платформе, которое нам делать не из чего. Заменено на факт о нас: TAUSIK не генерирует для хоста payload с хуками. (2) те же слова в docs/{ru,en}/troubleshooting.md — обе языковые пары правлены разом. (3) строка таблицы Rule 1 держала список хостов руками — убрана, теперь отсылает к выведенному уведомлению.
- 2026-09-07T20:44:45Z [implementation] — AC verified: 1. ✓ строка про автоматическое принуждение печатается только там, где механизм РАЗВЁРНУТ; на хосте без него печатается ON THIS HOST THE RULES BELOW ARE INSTRUCTIONS, NOT CHECKS. Проверено на настоящем дереве и на сгенерированных файлах: .cursorrules несёт честную фразу, QWEN.md — 23 hook commands, .opencode/tausik-rules.md — 1 plugin. 2. ✓ блок ВЫВЕДЕН из развёрнутого (scripts/enforcement_coverage.py считает settings.json и plugins/), реестра правило->хук нет; собственный словарь host->rules_file удалён в пользу ide_utils.IDE_REGISTRY. 3. ✓ причина названа верно: TAUSIK does not generate a real-time payload for this host — вместо неверного no hooks API; правка сделана и в MULTIMODEL_NOTE, и в обеих языковых версиях troubleshooting.md. 4. ✓ doctor произносит вслух: OK Enforcement coverage claude: 23 hook commands; opencode: 1 plugin; qwen: 23 hook commands; cursor: none; kilo: none. 5. ✓ имитации паритета нет: строка Rule 1 больше не держит рукописный список хостов. 6. ✓ мутационный тест снимает механизм и требует смены блока (tests/test_enforcement_coverage.py, класс TestTakingTheMechanismAwayChangesTheSentence, в т.ч. пустой список хуков при живом файле). 7. ✓ граница соблюдена: hooks.json для Cursor не генерируется, плагины для kilo не пишутся, счётчики обоих остаются нулевыми — тест test_bootstrap_writes_no_hooks_payload_for_cursor.
