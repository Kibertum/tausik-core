---
slug: scope-honesty-counts-a-tasks-own-export-as-undeclared
title: "Честность области считает собственный экспорт задачи недекларированным: каждая квитанция выходит under-declared"
status: done
epic: release-19-renar-conformance
story: evidence-primitives
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: verify-handle-dies-on-a-tasks-own-export-file
scope: "scripts/verify_scope_honesty.py — describe_declared_scope и её сигнатура. Вызывающие: scripts/service_verification.py, scripts/verify_cached_run.py, scripts/verify_run_record.py — только передача слага задачи, если он выбран способом передачи. scripts/verify_own_export.py — читатель адреса, БЕЗ изменения его контракта. tests/. CHANGELOG.md и CHANGELOG.ru.md."
scope_exclude: "Подпись квитанции, схема БД и уже подписанные строки НЕ ТРОГАЮТСЯ: перевычисление статуса на исторических квитанциях сломало бы их подпись и подменило бы факт, зафиксированный на момент прогона. Решение #283 не пересматривается — вычитается только СВОЙ экспорт. Правило is_security_sensitive и классификатор security_pattern.py вне предмета. Три места, исправленные в #194 (verify_cached_run, verify_handle_check, verify_cache), уже верны и не переписываются."
relevant_files:
  - "scripts/verify_scope_honesty.py"
  - "scripts/verify_cached_run.py"
  - "scripts/verify_handle_check.py"
  - "tests/test_verify_scope_honesty.py"
  - "tests/test_verify_handle.py"
  - "docs/en/receipts.md"
  - "docs/ru/receipts.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-08-31T13:05:16Z"
---

## Goal

ЗАМЕР #195, ПРЯМОЙ. verify #1892 напечатал «NOTE: 1 file(s) changed since task start but not declared in relevant_files» — этим одним файлом был tausik/tasks/<slug>.md, СОБСТВЕННЫЙ экспорт задачи. git status подтвердил: ни одного другого недекларированного файла не было.
ЧЕТВЁРТОЕ МЕСТО ТОГО ЖЕ КЛАССА. Решение #283 постановило вычитать собственный экспорт задачи из ПОКРЫТИЯ квитанции на обеих сторонах, и в #194 это сделано в трёх местах (verify_cached_run:151 запись, verify_handle_check:297 предъявление, verify_cache:124 безхендловый путь). Четвёртое найдено не было: describe_declared_scope в scripts/verify_scope_honesty.py:108 считает undeclared = actual - declared_set без всякого вычитания бухгалтерии фреймворка. Разбор #193 утверждал «три точки правки», #194 нашла пять; это шестая, и найдена она не чтением, а живым прогоном.
ПОЧЕМУ ЭТО НЕ КОСМЕТИКА. Экспорт переписывается САМИМ фреймворком между task start и verify — task start пишет started_at, каждый task log пересобирает файл. Значит under-declared выпадает практически КАЖДОЙ задаче, независимо от честности агента, и статус COMPLETE недостижим по построению для любой задачи, которая хоть раз вела журнал. Это ровно то, о чём предупреждает докстринг этого же модуля: «A rule firing on ~100% of honest work would be disabled first» (Decision #138, память #223). Статус, который у всех одинаковый, не различает ничего, а он попадает в ПОДПИСАННУЮ квитанцию (crypto_receipt:163) и читается при предъявлении хендла (verify_handle_check:423).

## Acceptance Criteria

AC1. describe_declared_scope ВЫЧИТАЕТ собственный экспорт задачи из множества недекларированных — и ТОЛЬКО свой, по решению #283. Адрес выводится через scripts/verify_own_export.py (own_export_abspath / coverage_files), литерала «tausik/tasks/» в этом модуле не появляется. Функция сегодня не знает слага задачи: передача слага (или уже готового пути) — часть задачи, и способ передачи выбирается явно, а не подгоняется под первый компилирующийся вариант.
AC2. ЧУЖОЙ ЭКСПОРТ ОСТАЁТСЯ НЕДЕКЛАРИРОВАННЫМ. Задача планирования, переставившая десять чужих задач, обязана по-прежнему получать under-declared с их именами. Вычитание всего tausik/tasks/ — провал критерия, а не упрощение.
AC3. СТАТУС COMPLETE СТАНОВИТСЯ ДОСТИЖИМЫМ. Замер, а не рассуждение: задача, объявившая ровно свои изменённые файлы и ведшая журнал, получает status=complete. Сегодня она получает under-declared. Предъявить обе цифры, до и после, на одном и том же входе.
AC4. ПУСТОЕ ПОСЛЕ ВЫЧИТАНИЯ НЕ СТАНОВИТСЯ ТИХИМ ЗЕЛЁНЫМ (память #454, оплаченная в #194 на этом же классе). Если после вычитания actual пусто, статус обязан остаться осмысленным: «no git-visible changes» и «все изменения были бухгалтерией фреймворка» — разные факты, и второй не имеет права печататься как первый. Решить явно и записать цену.
AC5. security_undeclared НЕ ОСЛАБЛЯЕТСЯ. Вычитание касается ровно одного файла — экспорта своей задачи, который не проходит is_security_sensitive. Тест обязан предъявить, что чувствительный недекларированный файл по-прежнему попадает в security_undeclared и по-прежнему блокирует.
AC6. НЕГАТИВНЫЙ СЦЕНАРИЙ, ОБЯЗАТЕЛЕН. Тест, где агент реально не объявил изменённый исходник, обязан краснеть как и раньше. Проверка, после которой under-declared не выпадает никому, есть ровно тот дефект, против которого задача заводится.
AC7. Мутация на КАЖДОЕ исправленное место отдельно (конвенция #449 — в #194 это нашло пять непокрытых мест, в #195 одно). Якорь однострочный, харнесс падает отдельным исходом SETUP-FAIL при count != 1 (память #457). Возврат побайтовой копией со сверкой sha256, git checkout запрещён.
AC8. Полная лента зелёная: pytest -q из PATH, 0 failed (память #450). Перед первым verify — python bootstrap/bootstrap.py --ide all (память #453).

## Plan

## Rollback

git revert коммита. Правка сужает множество недекларированных файлов на один элемент — собственный экспорт задачи — и не трогает ни правило сравнения, ни подпись, ни схему. Откат возвращает нынешнее поведение, где статус under-declared выпадает почти каждой задаче. Уже подписанные квитанции откатом не затрагиваются: они хранят вычисленное на момент подписи значение, и перевычисления не происходит.

## Journal

- 2026-08-31T12:49:34Z [implementation] — Разбор: 2 живых вызова describe_declared_scope (verify_cached_run:171 запись, verify_handle_check:406 предъявление), оба держат слаг. Способ передачи выбран ЯВНО: keyword-only task_slug, а не готовый путь — путь дал бы вызывающему право написать литерал 'tausik/tasks/' и открыл бы #249 заново. Вычитание делается через coverage_files (тот же шов, что у трёх точек #194), потому что оно сравнивает abspath+normcase — на Windows это ещё и правильный регистр, чего строковое сравнение repo-путей не даёт.
- 2026-08-31T12:54:57Z [implementation] — Scope РАСШИРЕН явно (память #451): описание контроля живёт также в docs/en/receipts.md и docs/ru/receipts.md — 'два свойства' стали тремя, третье называет вычитание собственного экспорта и границу 'только свой'. Без этого документация продолжала бы обещать under-declared там, где код его больше не выдаёт.
- 2026-08-31T13:02:35Z [implementation] — AC3 ЖИВОЙ ЗАМЕР на РЕАЛЬНОМ дереве (не тест): declared = 7 действительно изменённых файлов, окно как у задачи, заведённой в этой сессии. ДО (без слага): under-declared, count=1, единственный недекларированный — tausik/tasks/<свой слаг>.md. ПОСЛЕ (task_slug): complete, count=0, reason 'declared set covers all 7 changed file(s)'. Ровно тот дефект, что напечатал verify #1892, и ровно его исчезновение.
- 2026-08-31T13:02:41Z [implementation] — AC7: 5 мутаций, КАЖДАЯ на отдельное исправленное место, все УБИТЫ первым прогоном, SETUP-FAIL ни разу. M1 вычитания нет вовсе (падают 5 тестов), M2 вычитается ВЕСЬ tausik/tasks/ (падает только тест чужого экспорта), M3 опустевшее покрытие переиспользует чужую фразу (падает тест AC4), M4 запись перестаёт называть слаг, M5 предъявление перестаёт называть слаг. Возврат побайтовый со сверкой sha256, git checkout не применялся. Полная лента: 7448 passed, 24 skipped, 0 failed.
- 2026-08-31T13:03:29Z [implementation] — ПОДПИСАННАЯ КВИТАНЦИЯ run #1894: declared_scope_status=complete, undeclared_count=0. Это первая квитанция этого репозитория со статусом complete — до правки любая задача, ведшая журнал, получала under-declared из-за собственного экспорта. Статус снова различает добросовестную и недообъявленную область.
- 2026-08-31T13:04:33Z [implementation] — Конвенция #275: закрытие требует записи в ОБОИХ changelog. Добавлены разделы в CHANGELOG.md и CHANGELOG.ru.md, область расширена до 9 файлов.
- 2026-08-31T13:05:48Z [done] — AC-1: ✓ tests/test_verify_scope_honesty.py::TestOwnExportIsNotUndeclared::test_before_and_after_on_one_input — адрес выведен через verify_own_export.coverage_files, литерала tausik/tasks/ в scripts/verify_scope_honesty.py нет; способ передачи — keyword-only task_slug, обоснован в докстринге
- 2026-08-31T13:05:48Z [done] — AC-2: ✓ tests/test_verify_scope_honesty.py::TestOwnExportIsNotUndeclared::test_foreign_export_stays_undeclared — чужой экспорт остаётся недекларированным; мутация M2 (вычесть весь tausik/tasks/) убита именно этим тестом
- 2026-08-31T13:05:49Z [done] — AC-3: ✓ tests/test_verify_scope_honesty.py::TestOwnExportIsNotUndeclared::test_before_and_after_on_one_input плюс ЖИВОЙ замер: до — under-declared count=1 (собственный экспорт), после — complete count=0; подписанная квитанция run #1896 несёт declared_scope_status=complete, undeclared_count=0
- 2026-08-31T13:05:49Z [done] — AC-4: ✓ tests/test_verify_scope_honesty.py::TestOwnExportIsNotUndeclared::test_emptied_coverage_says_what_emptied_it и ::test_genuinely_empty_diff_keeps_its_own_sentence — опустевшее вычитанием покрытие получает СВОЮ фразу с именем экспорта, честно пустой diff сохраняет прежнюю
- 2026-08-31T13:05:49Z [done] — AC-5: ✓ tests/test_verify_scope_honesty.py::TestOwnExportIsNotUndeclared::test_security_undeclared_is_not_weakened — чувствительный недекларированный файл по-прежнему в security_undeclared и по-прежнему блокирует
- 2026-08-31T13:05:50Z [done] — AC-6: ✓ tests/test_verify_scope_honesty.py::TestOwnExportIsNotUndeclared::test_undeclared_source_still_under_declared — реально необъявленный исходник по-прежнему краснеет
- 2026-08-31T13:05:50Z [done] — AC-7: ✓ 5 мутаций на 4 исправленных места плюс направление пере-вычитания, все убиты первым прогоном, SETUP-FAIL ноль, возврат побайтовый со сверкой sha256
- 2026-08-31T13:05:51Z [done] — AC-8: ✓ pytest -q из PATH: 7448 passed, 24 skipped, 0 failed; bootstrap --ide all выполнен ДО первого verify (память #453), расхождения хешей не было
- 2026-08-31T13:05:51Z [done] — Domain: статус области снова различает разные прогоны. До правки under-declared выпадал ЛЮБОЙ задаче, которая вела журнал, независимо от честности агента — значение, одинаковое у всех, не несёт информации, но подписывается в квитанцию. После правки честная область даёт complete (run #1896), а недообъявленная — по-прежнему under-declared с именами файлов.
- 2026-08-31T13:05:51Z [done] — Root cause (logic-error): describe_declared_scope считала undeclared = actual - declared, где actual берётся из git и потому включает файлы, которые между task start и verify пишет САМ фреймворк — собственный экспорт задачи. Проверка про действия АГЕНТА измеряла сумму действий агента и фреймворка. Prevention: у любой проверки вида что изменил агент вычитание бухгалтерии фреймворка обязано стоять на КАЖДОМ месте класса, а не на первых найденных чтением — три места закрыты в #194, четвёртое нашёл живой прогон, а не чтение.
