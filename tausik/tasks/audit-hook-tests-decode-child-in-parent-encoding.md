---
slug: audit-hook-tests-decode-child-in-parent-encoding
title: "Тесты аудит-хука читают вывод дочернего процесса кодировкой родителя — красный храповик в дереве"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: python
tier: trivial
call_budget: 10
defect_of: take-the-claudemd-audit-hook-into-the-tree
scope: "tests/test_claudemd_audit_hook.py — три вызова subprocess.run (:49, :191, :228)."
scope_exclude: "scripts/**, tests/tools/claudemd_audit/** — сам хук исправен, замер #191 это показал (21 тест, распространение проверено на внуке). tests/test_hook_encoding.py — храповик прав, его не трогать."
relevant_files:
  - "tests/test_claudemd_audit_hook.py"
  - "tests/test_hook_encoding.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-08-31T09:24:48Z"
resolution: null
resolution_reason: null
---

## Goal

ЗАМЕР #192, ПРЯМОЙ: tests/test_hook_encoding.py::TestNoSilentEncodingInheritance::test_no_test_reads_a_subprocess_in_the_parents_encoding КРАСНЫЙ на HEAD=803b2c3. Нарушители: tests/test_claudemd_audit_hook.py:49, :191, :228 — три вызова subprocess.run с capture_output/text, но БЕЗ encoding="utf-8".
ОТКУДА: файл пришёл коммитом 89d1590 (сессия #191, задача take-the-claudemd-audit-hook-into-the-tree, verify #1857). Тот verify закрылся зелёным, потому что tests/test_hook_encoding.py НЕ ПОПАЛ в его scope: relevant_files задачи не отображаются на этот храповик, а он общедеревянный. То есть дефект не в невнимательности, а в том, что храповик, стерегущий ВСЕ тесты, невидим для выборки, ключуемой по изменённым файлам — ровно класс, описанный конвенцией #421.
ПОЧЕМУ ЭТО НЕ КОСМЕТИКА: такой вызов декодирует вывод ребёнка кодировкой родителя, то есть зависит от того, чем запущен pytest. На cp1252 он падает UnicodeDecodeError на любой кириллице в выводе хука — а хук пишет русские сообщения. Тест зелен на машине запускавшего и красен у следующего.
ЗАВЕДЕНО ВНУТРИ usage-attribution-is-keyed-by-task-not-session: обнаружен её scoped-прогоном (127 файлов), к её предмету отношения не имеет, поэтому отдельной задачей, а не довеском к чужому коммиту.

## Acceptance Criteria

AC1. tests/test_hook_encoding.py::TestNoSilentEncodingInheritance::test_no_test_reads_a_subprocess_in_the_parents_encoding ЗЕЛЁНЫЙ: три вызова в tests/test_claudemd_audit_hook.py (:49, :191, :228) несут encoding="utf-8".
AC2. tests/test_claudemd_audit_hook.py остаётся зелёным целиком (21 тест) — правка кодировки не меняет того, что эти тесты утверждают.
AC3. НЕГАТИВНЫЙ СЦЕНАРИЙ: храповик обязан ловить возврат дефекта. Мутация — снять encoding="utf-8" у ОДНОГО из трёх вызовов — красит test_hook_encoding; возврат побайтовой копией со сверкой sha256. Без этого замера правка не доказана: тест уже был зелёным на том дереве, где дефект жил, просто не запускался.
AC4. Правится ТОЛЬКО кодировка вызовов. Ни одно утверждение, ни один payload, ни область видимости фикстур не трогаются — иначе это уже не починка чужого коммита, а его переделка.

## Plan

## Rollback

git revert коммита. Правка добавляет один именованный аргумент в три вызова и не меняет ни поведения продукта, ни схемы, ни данных; откат безопасен в любой момент.

## Journal

- 2026-08-31T09:24:17Z [implementation] — [#192] Три вызова получили encoding="utf-8" (:49, :191, :228 в дореализационной нумерации; git видит РОВНО три вставки и ничего больше — AC4 соблюдён машинно, `git diff --stat` = 3 insertions). МУТАЦИЯ, AC3: снят encoding у ОДНОГО из трёх — test_hook_encoding покраснел (1 failed, 18 passed); возврат побайтовой копией, sha 68a6d4253edd572c совпал до и после; после возврата 40 зелёных. Мутировался именно ОДИН вызов, а не файл целиком: так проверено, что храповик считает ВЫЗОВЫ, а не наличие слова encoding где-нибудь в файле. НАЙДЕНО ПОПУТНО, НЕ ЧИНИЛОСЬ (вне scope, но назвать надо): ЧЕТВЁРТЫЙ subprocess.run с тем же дефектом живёт в строковом литерале около :216 — это код, который исполняет ВНУК. Храповик его не видит, потому что разбирает исходник, а не строки в нём. Вреда сегодня нет (внук печатает только ASCII), но слепое пятно храповика реально: тот же дефект внутри строки пройдёт молча. Отдельной задачи не завожу — предъявляю замером здесь, чтобы решение принимал владелец. ПРИЧИНА, А НЕ СИМПТОМ: verify #1857 сессии #191 был зелёным, потому что tests/test_hook_encoding.py не отобразился на её relevant_files. Общедеревянный храповик невидим для выборки по изменённым файлам — конвенция #421 ровно об этом, и это уже второй её случай.
- 2026-08-31T09:24:46Z [implementation] — AC1 PASS: test_hook_encoding::test_no_test_reads_a_subprocess_in_the_parents_encoding зелёный, три вызова несут encoding=utf-8. AC2 PASS: tests/test_claudemd_audit_hook.py зелёный целиком в том же прогоне (verify #1864, 2 файла в scope, exit=0). AC3 PASS замером: снятие encoding у ОДНОГО из трёх вызовов красит храповик (1 failed, 18 passed), возврат побайтовой копией, sha 68a6d4253edd572c совпал до и после, после возврата 40 зелёных. AC4 PASS машинно: git diff --stat = 3 insertions, 0 deletions — ни одно утверждение не тронуто.
- 2026-08-31T09:25:00Z [done] — Root cause (regression): три subprocess.run в tests/test_claudemd_audit_hook.py декодировали вывод дочернего процесса кодировкой родителя (нет encoding="utf-8"), поэтому тест зависел от того, чем запущен pytest, и на cp1252 падал бы UnicodeDecodeError на кириллице, которую хук печатает. Дефект въехал коммитом 89d1590, а verify #1857 остался зелёным, потому что общедеревянный храповик tests/test_hook_encoding.py НЕ отображается на relevant_files той задачи — выборка тестов ключуется по изменённым файлам и такие храповики не видит (конвенция #421, второй зафиксированный случай). Prevention: храповики, стерегущие ВСЁ дерево, обязаны входить в scope независимо от relevant_files — либо через явное объявление в relevant_files, как сделано здесь (verify #1864 покрывает оба файла), либо через отдельный список always-run для выборки. Пока второго нет, ЗАКРЫВАЯ задачу, чей продукт трогает тесты, объявляй tests/test_hook_encoding.py в relevant_files руками. Negative: AC3 предъявлен мутацией — снятие encoding у ОДНОГО из трёх вызовов красит храповик (1 failed / 18 passed), возврат побайтовой копией со сверкой sha256 (68a6d4253edd572c до и после), после возврата 40 зелёных.
