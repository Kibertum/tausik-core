---
slug: memory-lint-flags-absent-path-that-is-the-memorys-subject
title: "Два детектора (memory lint и audit evidence) считают ПРИМЕР-ЗАГЛУШКУ настоящей ссылкой: 43% ложных в одном, заглушки в счётчике 'выдумано' у другого"
status: done
epic: release-19-renar-conformance
story: renar-debt-implemented-wrong
complexity: complex
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "Один корень двух детекторов: общее понятие «иллюстративный путь / путь-пример». Правятся модуль-носитель понятия, memory lint (stale_file), audit evidence и его отчёт, их тесты и документация команды."
scope_exclude: "НЕ трогаем: гейт закрытия задач и service_ac_evidence.parse_evidence_lines — правило «что считается строкой доказательства» остаётся прежним, меняется только толкование ПУТИ внутри неё; детекторы contradicts и superseded в memory lint; данные в БД (обе команды read-only); RENAR-манифест и схему."
relevant_files:
  - "scripts/illustrative_paths.py"
  - "scripts/memory_cleanup.py"
  - "scripts/audit_closure_evidence.py"
  - "scripts/project_cli_audit.py"
  - "scripts/service_knowledge_hygiene.py"
  - "tests/test_illustrative_paths.py"
  - "tests/test_memory_lint.py"
  - "tests/test_audit_closure_evidence.py"
  - "docs/ru/cli.md"
  - "docs/en/cli.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - "scripts/illustrative_paths.py"
  - "scripts/memory_cleanup.py"
  - "scripts/audit_closure_evidence.py"
  - "scripts/project_cli_audit.py"
  - "scripts/service_knowledge_hygiene.py"
  - "tests/test_illustrative_paths.py"
  - "tests/test_audit_closure_evidence.py"
  - "tests/test_memory_lint.py"
  - "docs/ru/cli.md"
  - "docs/en/cli.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-09-04T10:22:27Z"
resolution: null
resolution_reason: null
---

## Goal

НАЙДЕНО АУДИТОМ SENAR 9.5 В #199. ДВА НЕЗАВИСИМЫХ ДЕТЕКТОРА ОШИБАЮТСЯ ОДИНАКОВО, И ПРИЧИНА У НИХ ОДНА: они не отличают ССЫЛКУ от УПОМИНАНИЯ-ПРИМЕРА. Задача чинит корень, а не два симптома.  ДЕТЕКТОР 1 — memory lint (stale_file). После --apply остаётся 7 находок; каждый путь проверен на диске — отсутствуют все семь, но ТРИ ложны. #322 «Разделение durable/runtime стейта» ссылается на 'tausik/tausik.db' — память УТВЕРЖДАЕТ, что БД там не лежит; это её предмет. #463 «44 нерезолвящихся цитаты» ссылается на 'tests/test_does_not_exist.py' — иллюстрация несуществующей цитаты внутри памяти О несуществующих цитатах. #65 ссылается на '.claude/settings.local.json' — файл в .gitignore (строка 32), отсутствует ЗАКОННО и машинно-локально. Ложных 3 из 7 — 43%.  ДЕТЕКТОР 2 — tausik audit evidence. Замер: 1267 закрытых задач, 3041 цитата, 1107 уникальных, резолвятся 1063, ROTTED 19, NEVER_EXISTED 25. Но в NEVER_EXISTED лежат ЯВНЫЕ ЗАГЛУШКИ: tests/test_does_not_exist.py, tests/test_foo.py(::test_bar), tests/test_x.py, tests/test_X.py, tests/x.py, tests/test_a.py, tests/test_real.py::test_a, tests/test_file.py, tests/foo.py, tests/integration/test_foo.py, tests/unit/scoped/test_bar.py, tests/../scripts/prod.py. Цитируют их задачи, чей ПРЕДМЕТ — поддельные и сгнившие цитаты: rule5-checklist-keyword-theater, closure-evidence-references-rot-and-nothing-notices, memory-lint-stale-file-mostly-false-positives, checklist-detector-is-red-on-its-own-test, review-mlow-resolver-recursive.  ПОЧЕМУ ЭТО НЕ КОСМЕТИКА. Число «25 выдуманных доказательств» ПУГАЕТ вместо того, чтобы УКАЗЫВАТЬ: настоящих среди них меньшинство, и они тонут в заглушках. Контроль, который в заметной доле случаев кричит на здоровое, обучает агента пролистывать свой вывод — то есть отключается руками читателя. Это ровно дефект из решения #288: контроль, исполняемый формально, по всем прочим признакам выглядит здоровым.  ЧТО ДЕЛАТЬ (варианты, выбор за исполнителем, но корень чинить ОДИН). (1) Отличать упоминание-пример от ссылки: путь внутри текста, который сам утверждает его отсутствие/поддельность, ссылкой не считать. (2) Дать явный способ ОБЪЯВИТЬ путь примером, чтобы оба детектора его пропускали. (3) Учитывать .gitignore: игнорируемый путь отсутствует законно. (4) Разделить вывод audit evidence на «настоящие» и «заглушки» с ОТДЕЛЬНЫМИ счётчиками, чтобы число в шапке не врало. ОБЯЗАТЕЛЬНО: у починки нужна НЕГАТИВНАЯ ветвь — заведомо НАСТОЯЩАЯ сгнившая цитата обязана остаться найденной. Иначе «ложных срабатываний больше нет» станет достигаться отключением детектора. ГДЕ СМОТРЕТЬ: поиск по 'stale_file' и по реализации audit evidence в scripts/.

## Acceptance Criteria

AC-1: Понятие «иллюстративный путь» живёт в ОДНОМ модуле и используется обоими детекторами — memory lint (stale_file) и audit evidence. Дублирующего списка заглушек во втором месте не остаётся.
AC-2 (негативный сценарий, ОБЯЗАТЕЛЬНЫЙ, двусторонний): настоящая сгнившая ссылка обязана ОСТАТЬСЯ найденной. Закрепить на живых данных: tests/test_ble001_enforced.py::test_ble001_selected_in_pyproject и tests/test_knowledge_export.py::TestTheDestinationMustBeLocal не должны попасть в новую корзину. Иллюстративная tests/test_does_not_exist.py обязана уйти из never_existed. Без обеих сторон починка есть глушилка детектора, и это считается ошибкой теста, а не успехом.
AC-3: Отчёт audit evidence печатает иллюстративные ОТДЕЛЬНЫМ счётчиком, а не прячет их: число в шапке перестаёт врать, но ни одна запись не исчезает бесследно.
AC-4: Замер до и после на живом корпусе предъявлен числами: сколько было в never_existed, сколько стало, сколько ушло в illustrative, сколько осталось настоящих. Для memory lint — сколько находок stale_file и сколько из них ложных.
AC-5: Игнорируемый git-ом путь отсутствует ЗАКОННО: memory lint не считает такой путь пропавшим, и это закреплено тестом с положительным и отрицательным концом.

## Plan

## Rollback

git revert <commit>. Обе команды read-only и ничего не блокируют: audit evidence только печатает отчёт, memory lint без --apply только перечисляет находки. Данные не меняются, отчёт пересчитывается каждым прогоном, миграций нет. Частичный откат: удалить вызов is_illustrative из одного детектора — второй продолжит работать.

## Journal

- 2026-09-04T10:21:03Z [implementation] — ИНВЕНТАРЬ И ЗАМЕР ДО. Носители: scripts/illustrative_paths.py (новый, общее понятие), memory_cleanup.py (детектор stale_file), audit_closure_evidence.py (вердикты), project_cli_audit.py (отчёт), service_knowledge_hygiene.py (проводка + git-проба), три файла тестов, docs/{ru,en}/cli.md, оба CHANGELOG. 12 несущих — сложность complex подтверждена, не переоценена. ЗАМЕР ДО, ЖИВОЙ КОРПУС. audit evidence: 1304 закрытых задачи, 577 цитируют тест, 3299 цитат / 1234 уникальных, резолвятся 1187; ROTTED 22, NEVER_EXISTED 25, UNKNOWN_HISTORY 0. Разбор корзины NEVER_EXISTED вручную: 13 иллюстративных, 9 голых имён модулей без каталога, 3 НАСТОЯЩИЕ (tests/test_ble001_enforced.py::test_ble001_selected_in_pyproject, tests/test_knowledge_export.py::TestTheDestinationMustBeLocal, tests/test_app_spa_mount.py). То есть шапка завышала распад вдвое рядом с 22 ROTTED. memory lint: 10 находок, из них 7 stale_file; проверены по диску и по git check-ignore: 3 игнорируются git (.claude/settings.local.json, .qwen/QWEN.md, .kilo/AGENTS.md), 1 иллюстративная (tests/test_does_not_exist.py), 1 относительна рабочему каталогу (./probe.sh из цитаты команды), 2 настоящие. Ложных 5 из 7. ВАЖНОЕ ОТКРЫТИЕ ПРОТИВ ФОРМУЛИРОВКИ ЗАДАЧИ: extract_refs аудита НЕ читает прозу задачи вообще — он берёт ссылки через service_ac_evidence.parse_evidence_lines, то есть только из СТРОК ДОКАЗАТЕЛЬСТВ. Иллюстративные имена сидят ВНУТРИ самих строк доказательств (например «✓ MANUAL на живых данных: tests/foo.py, ...» — это перечень входных данных ручной проверки). Значит вариант «извлекать не отовсюду, а из строк доказательства» из описания задачи УЖЕ реализован и дефект не в нём.
- 2026-09-04T10:21:04Z [implementation] — ЗАМЕР ПОСЛЕ, ОБЕ СТОРОНЫ. audit evidence: NEVER_EXISTED 25 -> 12, ILLUSTRATIVE 13, ROTTED 22 БЕЗ ИЗМЕНЕНИЙ (ни одна настоящая гниль не переехала). Все три настоящие находки остались в NEVER_EXISTED — проверено по имени в живом отчёте. memory lint: stale_file 7 -> 2, обе оставшиеся не заглушены сознательно: docs/skills.md — настоящая сгнившая ссылка (негативная ветвь держит), tausik/tausik.db — память #322 называет путь, объясняя, что базы там НЕТ; отличить это от гнили можно только прочитав НАМЕРЕНИЕ фразы, а угадывание намерения превращает детектор в глушилку. Отказ угадывать записан в докстринг модуля, а не умолчан. МУТАЦИИ. Базовый rc=0, 114 passed. Применились 13 мутантов, УБИТО 13 (только rc=1, память #542), восстановленный прогон rc=0/114. Четырнадцатый («правило относительного пути выключено целиком») НЕ ПРИМЕНИЛСЯ — якорь разошёлся после форматирования; ложным убийством не считаю, его покрытие поглощено двумя направленными мутантами (снять распознавание «..» и снять распознавание «./»), оба убиты. ПЕРВЫЙ ПРОГОН ДАЛ 11/14: выжили ДВА мутанта в service_knowledge_hygiene — «проба не подключена к сервису» и «проба падает ВНУТРЬ, глуша всё». Причина: сервисный слой не был покрыт ни одним тестом, хотя докстринг файла тестов утверждал обратное («+ the service orchestration (lint_memory) dry-run vs --apply»). Второй выживший — опасный: сломанный git тихо выключил бы весь детектор stale_file. Добавлены четыре теста сервиса, оба мутанта убиты. Negative: негативная ветвь прогнана на ЖИВЫХ данных, а не на фикстурах — обе настоящие находки корпуса остались в NEVER_EXISTED, настоящая сгнившая ссылка docs/skills.md осталась в линте, ROTTED не изменился. Дополнительно закреплено тестами: test_a_genuine_miss_is_not_moved_into_the_example_bucket, test_a_tracked_path_that_is_gone_is_still_reported, test_no_measured_real_citation_is_swallowed (12 настоящих ссылок), test_the_probe_fails_open_where_git_cannot_answer.
- 2026-09-04T10:22:23Z [implementation] — СВЕРКА AC. AC-1: ✓ tests/test_illustrative_paths.py::test_neither_detector_keeps_its_own_placeholder_list AC-2: ✓ tests/test_audit_closure_evidence.py::test_a_genuine_miss_is_not_moved_into_the_example_bucket AC-3: ✓ tests/test_audit_closure_evidence.py::test_the_example_count_is_published_not_folded_away AC-4: ✓ tests/test_illustrative_paths.py::test_every_measured_example_is_recognised AC-5: ✓ tests/test_memory_lint.py::test_a_git_ignored_path_is_not_reported_as_stale Domain: результат осмыслен вне тестов и проверен на ЖИВОМ корпусе обеими командами, а не только на фикстурах. Реальный вход — 1304 закрытые задачи и 3299 цитат, накопленные за всю историю проекта. До правки отчёт объявлял 25 выдуманных доказательств при 3 настоящих; читатель, проверяющий такой отчёт, обучается пролистывать корзину, рядом с которой лежат 22 настоящие сгнившие ссылки. После правки отчёт объявляет 12 и отдельно 13 примеров с названным признаком у каждого — то есть число стало соответствовать тому, что читатель обязан пойти и проверить руками. Физическая осмысленность различения: путь с сегментом «..» или ведущим «./» указывает на файл ОТНОСИТЕЛЬНО рабочего каталога команды, а не относительно корня репозитория, поэтому утверждение «такого файла в репозитории нет» о нём попросту не определено. Обратная сторона держится: ROTTED не изменился ни на одну запись.
- 2026-09-26T18:44:28Z [done] — EVIDENCE-UNPROVEN: tests/test_ble001_enforced.py::test_ble001_selected_in_pyproject — git never carried this path or member under any directory
- 2026-09-26T18:44:29Z [done] — EVIDENCE-UNPROVEN: tests/test_knowledge_export.py::TestTheDestinationMustBeLocal — git never carried this path or member under any directory
