---
slug: task-cost-in-tokens-is-derivable-but-never-derived
title: "Цена задачи в токенах не считается, хотя данные для неё есть"
status: done
epic: release-110-deferred-from-19
story: deferred-110-audit-hygiene
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/task_cost_report.py"
  - "scripts/project_cli_metrics.py"
  - "scripts/project_parser_ops.py"
  - "tests/test_task_cost_report.py"
scope_paths:
  - "scripts/"
  - "tests/"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-09-29T17:58:32Z"
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

cost_actual_usd заполнен у 0 задач из 1675, tokens_actual у 27. Причина найдена: хук PostToolUse пишет вызов, но не токены (120 строк с токенами из 67 081), а сессионные записи токены несут, но слага задачи у них нет — свёртка по задаче возвращает пусто. При этом 165 смен имеют И токены, И привязку вызовов к задачам, и покрывают 727 задач. Цель: цена задачи в токенах ВЫВОДИТСЯ из сессионной суммы по доле вызовов задачи, называется долевой, а не измеренной, и печатает помесячный тренд — потому что вопрос, на который это отвечает, звучит «подешевела ли разработка».

## Acceptance Criteria

AC-1 tausik metrics cost печатает цену задачи в токенах, выведенную из суммы смены по доле вызовов задачи, и НАЗЫВАЕТ это правило в выводе. ✓ tests/test_task_cost_report.py
AC-2 Охват назван числом: сколько закрытых задач оценка достаёт и сколько нет.
AC-3 НЕГАТИВНЫЙ: задача в смене без записи токенов — ОТСУТСТВИЕ с причиной, никогда не ноль (решение #334).
AC-4 НЕГАТИВНЫЙ: смена с нулём вызовов не делится на ноль — отсутствие с причиной.
AC-5 НЕГАТИВНЫЙ: вывод НИ РАЗУ не называет число измеренным; тест требует слова «долевая»/«apportioned» и запрещает «измерено на задачу».
AC-6 Помесячный тренд напечатан: медиана и p90 по месяцам.
AC-7 Полная лента зелёная.

## Plan

## Rollback

git revert; turn_economy с константой 482k остаётся как был

## Journal

- 2026-09-29T17:58:27Z [implementation] — AC-1 ✓ tausik metrics task-cost печатает долевую цену и НАЗЫВАЕТ правило («A session's tokens are split across its tasks by each task's share of that session's calls»); ✓ tests/test_task_cost_report.py::TestTheApportionment — доля одной смены, две смены на задачу, открытая задача не в отчёте. AC-2 ✓ охват числом: 665 из 1684 закрытых (39%), ещё 195 объявлены отсутствующими; ::test_the_report_states_how_far_it_reaches. AC-3 ✓ НЕГАТИВНЫЙ: задача в смене без токенов — absent, не ноль; ::test_a_task_whose_sessions_recorded_no_tokens_is_absent. AC-4 ✓ НЕГАТИВНЫЙ: смена с нулём вызовов не делится на ноль, как и смена без токенов; ::test_a_session_missing_either_half_cannot_be_divided, три достижимых случая. AC-5 ✓ НЕГАТИВНЫЙ: вывод ни разу не называет число измеренным — ::TestItNeverCallsTheNumberMeasured требует «APPORTIONED, not measured per task», правило раскладки, предупреждение про прайс и слова «Descriptive, not a forecast»; отдельный тест запрещает печатать тренд по одному месяцу. AC-6 ✓ помесячная таблица с медианой и p90. AC-7 ✓ полная лента 12 470 passed, 34 skipped, 0 deselected. ЗАМЕР, РАДИ КОТОРОГО ЭТО ДЕЛАЛОСЬ: в долларах цена задачи упала на 61% (3,04 → 1,19), но цена миллиона токенов прошла 74,43 → 10,32 → 15,76, то есть это прайс. В токенах медиана выросла 41k (май) → 79k (сентябрь), в 1,9 раза; p90 184k → 410k; август хуже сентября (122k). НАЙДЕНО В ХОДЕ РАБОТЫ: фикстура объявляла схему руками и была переписана на canonical_ddl из conftest; один параметр отрицательного теста снят как НЕДОСТИЖИМЫЙ — канон запрещает NULL в tool_calls, и проверять невозможное состояние значит не проверять ничего.
