---
slug: call-budget-is-armed-in-autonomous-mode
title: "call_budget становится жёстким стопом в автономном режиме, а не советом"
status: done
epic: release-110-deferred-from-19
story: release110-open-defects
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 35
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/call_budget_guard.py"
  - "scripts/project_cli_task.py"
  - "scripts/project_parser_task.py"
  - "tests/test_call_budget_guard.py"
scope_paths:
  - "scripts/call_budget_guard.py"
  - "scripts/service_recording.py"
  - "scripts/project_cli_task.py"
  - "scripts/project_parser_task.py"
  - "tests/test_call_budget_guard.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-09-27T18:19:40Z"
resolution: null
resolution_reason: null
---

## Goal

ВТОРАЯ ИЗ ПЯТИ ЗАДАЧ АВТОНОМНОСТИ (ревью смены #277).

ЗАМЕР: за смену я пробил call_budget три раза — 106 против 40, 124 против 70, 139 против 90. Каждый раз предупреждение печаталось ПОСЛЕ закрытия, то есть узнать о перерасходе можно было только когда он уже случился.

У kiberza это решено, и решение стоит взять: скилл /run экспортирует KAI_AUTONOMOUS_BUDGET_BLOCK=1 на время батча и после каждого закрытия проверяет `task budget-check` по слагу; ненулевой выход равен отказу и останавливает прогон. Интерактивная работа при снятом флаге не меняется — совет остаётся советом.

ПОЧЕМУ БЕЗ ЭТОГО НЕЛЬЗЯ ЗАПУСКАТЬ ДРАЙВЕР: неприсмотренный прогон с советом вместо потолка сожжёт смену на одной задаче и остановится не по плану, а по исчерпанию. Владелец узнает об этом утром.

ПРОВЕРИТЬ ПЕРВЫМ: есть ли в core эквивалент `task budget-check` или его надо заводить; и на каком множителе ставить потолок — у kiberza 2×, и это число надо либо взять с обоснованием, либо замерить по своим закрытиям.

## Acceptance Criteria

AC-1 ЗАМЕР ПЕРВЫМ: множитель потолка выбран по СВОИМ закрытиям, а не скопирован у kiberza. Названо распределение call_actual к call_budget по закрытым задачам и доля, попадающая за 1.5× и за 2×. AC-2 Есть проверка, вызываемая ВО ВРЕМЯ работы, а не только на закрытии: команда, которая по слагу отвечает кодом выхода. Драйвер должен уметь остановиться, не дожидаясь закрытия. AC-3 ДВА ТИРА: предупреждение на прежнем множителе остаётся советом ВСЕГДА; отказ появляется только при взведённом флаге автономного режима. Интерактивная работа не меняется ни на символ. AC-4 НЕГАТИВ: при снятом флаге проверка НИКОГДА не отказывает, сколько бы ни был перерасход. AC-5 НЕГАТИВ: задача без объявленного бюджета не может нарушить потолок — отсутствие бюджета это не ноль. AC-6 НЕГАТИВ: проверка не может сломать закрытие и не может упасть сама. Сбой подсчёта равен отсутствию нарушения, а не нарушению. AC-7 Сообщение об отказе называет ЧИСЛА (actual, budget, множитель) и то, что делать: пересчитать бюджет или разбить задачу. Отказ без адреса не действие.

## Plan

## Rollback

Новый модуль-страж, одна команда CLI и чтение флага; откат — git revert, потолок снова совет.

## Journal

- 2026-09-27T18:18:36Z [implementation] — AC-1: ✓ множитель выбран по СВОИМ 651 закрытию, не скопирован. Медиана 0,58, p75 0,93, p90 1,60, p99 5,80, макс 47,5. За 1,5× — 11%, за 2× — 8%, за 2,5× — 4%, за 3× — 3%. Предупреждение остаётся 1,5×, отказ берёт 2× — там перерасход перестаёт быть шумом калибровки.
- 2026-09-27T18:18:37Z [implementation] — AC-2: ✓ tests/test_call_budget_guard.py::TestTheDriverCanAskWithAnExitCode — команда `task budget-check` отвечает КОДОМ ВЫХОДА, потому что печатное предупреждение невидимо для `&&`.
- 2026-09-27T18:18:37Z [implementation] — AC-3: ✓ tests/test_call_budget_guard.py::TestUnarmedNeverRefuses — два тира: совет всегда, отказ только при взведённом флаге.
- 2026-09-27T18:18:37Z [implementation] — AC-4: ✓ tests/test_call_budget_guard.py::TestUnarmedNeverRefuses::test_no_overrun_is_a_refusal_without_the_flag — перерасход до 400 000 вызовов не отказ без флага. Плюс test_a_falsy_looking_flag_does_not_arm: `=0` и `=false` не взводят.
- 2026-09-27T18:18:37Z [implementation] — AC-5: ✓ tests/test_call_budget_guard.py::TestAMissingBudgetIsNotAZeroBudget — семь форм отсутствия бюджета или замера, ни одна не может нарушить потолок.
- 2026-09-27T18:18:38Z [implementation] — AC-6: ✓ tests/test_call_budget_guard.py::TestTheGuardCannotBreakACloseOrItself — враждебный dict даёт молчание, не исключение.
- 2026-09-27T18:18:38Z [implementation] — AC-7: ✓ tests/test_call_budget_guard.py::test_the_refusal_names_the_three_numbers_and_a_way_out.
- 2026-09-27T18:18:38Z [implementation] — Domain: проверено на живом CLI и на настоящих закрытиях. 106 вызовов при бюджете 40 (2,6×) с взведённым флагом — код 1 и текст отказа; тот же слаг без флага — код 0 и молчание. Задача на 1,77× молчит даже при взведённом флаге, то есть потолок не тесен.
- 2026-09-27T18:18:38Z [implementation] — Negative: три класса молчания проверены отдельно — снятый флаг при любом перерасходе, отсутствие бюджета или замера, внутренний сбой. Страж, который падает, хуже стража, который промахивается: он останавливает закрытие.
