---
slug: task-ceremony-costs-extra-calls
title: "Обряд задачи стоит лишних вызовов: критерии нельзя задать при создании, бюджет проверяется отдельной командой"
status: done
epic: release-110-deferred-from-19
story: release110-terse-answers
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/project_parser_task.py"
  - "scripts/project_cli_task.py"
  - "tests/test_task_ceremony_calls.py"
scope_paths:
  - "scripts/project_parser_task.py"
  - "scripts/project_cli_task.py"
  - "tests/test_task_ceremony_calls.py"
  - "docs/ru/cli.md"
  - "docs/en/cli.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-09-29T14:14:56Z"
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

Создание задачи и её закрытие перестают требовать лишних вызовов. Замер по этой смене: task add не принимает --acceptance-criteria, хотя QG-0 их требует, поэтому за каждым add идёт update — девять задач, девять лишних вызовов. budget-check после task done — ещё один вызов на задачу. При измеренной цене хода около 482 000 токенов это примерно 10% обряда.

## Acceptance Criteria

1. task add принимает --acceptance-criteria и задача создаётся пригодной к task start одной командой. 2. task done печатает вердикт бюджета вызовов, не требуя отдельной команды. 3. НЕГАТИВНЫЙ: budget-check остаётся отдельной командой с прежним кодом возврата — драйверы читают код, а не текст, и убрать её значило бы сломать цепочку по &&. 4. НЕГАТИВНЫЙ: самопочинка bootstrap_drift НЕ делается — гейт отказывается чинить по записанной причине: перестраивая копии, которые оценивает, он мутировал бы состояние, о котором судит. 5. Полная лента зелёная.

## Plan

## Rollback

git revert; добавляется аргумент и строка вывода, ни одна проверка не снимается — budget-check остаётся отдельной командой с прежним кодом возврата.

## Journal

- 2026-09-29T14:13:58Z [implementation] — AC-1: ✓ tests/test_task_ceremony_calls.py::TestATaskIsStartableAfterOneCommand — три теста; живая проба: task add с --acceptance-criteria создала задачу, task show показал критерии, второй команды не потребовалось. AC-2: ✓ ::TestTheBudgetVerdictArrivesWithTheClosure::test_task_done_prints_it. AC-3 НЕГАТИВНЫЙ: ✓ ::test_budget_check_survives_as_its_own_command и ::test_the_exit_code_path_is_untouched — команда и код возврата на месте, цепочки по && не сломаны. AC-4 НЕГАТИВНЫЙ: ✓ ::TestTheDriftGateStillRefusesToFixItself — проверяет и записанную причину, и отсутствие subprocess в теле гейта. AC-5: ✓ лента 12319 прошли, 34 пропущены.
