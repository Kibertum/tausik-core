---
slug: scope-widening-costs-two-calls-and-a-restatement
title: "Расширение области стоит два вызова и перечисление всего списка заново"
status: done
epic: release-110-deferred-from-19
story: release110-verification-is-cheap
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/task_scope_widen.py"
  - "scripts/project_cli_task.py"
  - "scripts/project_parser_task.py"
  - "scripts/hooks/scope_write_gate.py"
  - "scripts/hooks/bash_write_gate.py"
  - "tests/test_scope_widening_cost.py"
  - "tests/test_scope_write_gate_hook.py"
scope_paths:
  - "scripts/project_parser_task.py"
  - "scripts/project_cli_task.py"
  - "scripts/task_scope_widen.py"
  - "scripts/hooks/"
  - "tests/"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - "docs/"
  - "tests/test_scope_write_gate_hook.py"
scope_tools: []
depends_on: []
completed_at: "2026-09-29T16:48:36Z"
resolution: null
resolution_reason: null
tracker_refs: []
started_model_id: claude-opus-5
started_model_version: null
done_model_id: claude-opus-5
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

Область задачи объявляется ДО того, как стало известно, какие файлы появятся, поэтому scope ACL отказывает почти в каждой нетривиальной задаче. Замер смены #278: 6 отказов на двух задачах подряд. Каждый стоит вызов отказа плюс вызов task update, в котором надо ПЕРЕЧИСЛИТЬ ВЕСЬ список заново — это и лишний ход (около 482 000 токенов), и риск молча уронить путь. Правило Rule 2 не ослабляется: расширение остаётся явным актом агента.

## Acceptance Criteria

AC-1 tausik task update <slug> --add-scope-paths <пути> ДОБАВЛЯЕТ пути к объявленным, не требуя перечислить существующие. ✓ tests/test_scope_widening_cost.py
AC-2 Отказ обоих хуков (scope_write_gate, bash_write_gate) печатает ДОБАВЛЯЮЩУЮ команду ровно с заблокированными путями, а не с полным списком. ✓ tests/test_scope_widening_cost.py
AC-3 НЕГАТИВНЫЙ: --add-scope-paths вместе с --scope-paths отказывает — одна команда, задающая список двумя способами, оставляет неясным, какой победил.
AC-4 НЕГАТИВНЫЙ: --add-scope-paths без путей отказывает, а не молча стирает область: пустой список почти всегда шаблон оболочки, не совпавший ни с чем.
AC-5 Повтор уже объявленного пути не дублирует его и говорит об этом.
AC-6 Полная лента зелёная.

## Plan

## Rollback

git revert; --scope-paths с полным списком не тронут

## Journal

- 2026-09-29T16:37:36Z [implementation] — Седьмой отказ области подряд — на задаче, которая его чинит: новый модуль scripts/task_scope_widen.py не мог существовать в объявлении, сделанном до его появления. Это и есть предмет: область объявляется до того, как работа покажет свои файлы.
- 2026-09-29T16:42:32Z [implementation] — AC-1 ✓ task update --add-scope-paths добавляет, сохраняя объявленное; проверено на самой этой задаче дважды («scope widened by docs/ (8 total)», затем «(9 total)»). ✓ tests/test_scope_widening_cost.py::TestWideningKeepsWhatWasThere. AC-2 ✓ оба хука строят отказ из widen_command и печатают только заблокированные пути; ::TestTheRefusalPrintsTheCheapCommand::test_both_hooks_build_their_refusal_from_that_one_command; живой отказ хука проверен end-to-end в tests/test_scope_write_gate_hook.py::TestHook::test_write_outside_scope_blocked — там теперь требуется «--add-scope-paths docs/x.md» и отсутствие формы «<existing». AC-3 ✓ НЕГАТИВНЫЙ: два флага вместе — ServiceError, называющий оба; плюс четыре случая, где один или ни одного не трогают. AC-4 ✓ НЕГАТИВНЫЙ: пустой список — отказ, ничего не записано. AC-5 ✓ повтор не дублирует и говорит об этом. AC-6 — лента следом. Domain: семь отказов области за три задачи этой смены; теперь второй вызов короткий и перечислять нечего. Правило 2 не ослаблено. ПОБОЧНО: первый заход закрытия был ОТКЛОНЁН красным прогоном — тест хука был пришит к старому тексту отказа; это первое живое срабатывание AC-3 предыдущей задачи, закрытие не состоялось и задача осталась открытой.
- 2026-09-29T16:46:42Z [implementation] — см. журнал задачи
- 2026-09-29T16:46:56Z [implementation] — NO-DEAD-END: красный прогон был не тупиком, а ПРЕДМЕТОМ задачи, сработавшим по себе. tests/test_scope_write_gate_hook.py требовал подстроку «--scope-paths» в тексте отказа; новый текст печатает «--add-scope-paths», в котором этой подстроки нет. Тест был пришит к форме команды, а не к её смыслу — переписан на то, что проверяет: отказ называет ДОБАВЛЯЮЩУЮ команду ровно с заблокированным путём и не содержит формы «<existing». Подход не отвергнут, ошибка была в одной строке ожидания.
- 2026-09-29T16:48:32Z [implementation] — AC-1 ✓ --add-scope-paths добавляет, сохраняя объявленное; проверено на самой задаче дважды (8 total, затем 9 total). ✓ tests/test_scope_widening_cost.py::TestWideningKeepsWhatWasThere. AC-2 ✓ оба хука строят отказ из widen_command; ::TestTheRefusalPrintsTheCheapCommand::test_both_hooks_build_their_refusal_from_that_one_command, плюс живой отказ end-to-end в tests/test_scope_write_gate_hook.py::TestHook::test_write_outside_scope_blocked. AC-3 ✓ НЕГАТИВНЫЙ: два флага вместе — ServiceError, называющий оба. AC-4 ✓ НЕГАТИВНЫЙ: пустой список — отказ, ничего не записано. AC-5 ✓ повтор не дублирует и говорит об этом. AC-6 ✓ полная лента 12 430 passed, 34 skipped, 0 deselected. Domain: семь отказов области за три задачи этой смены, каждый стоил вызов отказа плюс вызов с перечислением всего списка; теперь второй короткий. Правило 2 не ослаблено — расширение остаётся явным актом, путь за путём.
