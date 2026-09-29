---
slug: task-cost-trend-blends-a-changing-task-mix
title: "Отчёт цены печатает смешанный тренд, в котором меняется состав задач"
status: done
epic: release-110-deferred-from-19
story: deferred-110-audit-hygiene
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: task-cost-in-tokens-is-derivable-but-never-derived
scope: null
scope_exclude: null
relevant_files:
  - "scripts/task_cost_report.py"
  - "tests/test_task_cost_report.py"
scope_paths:
  - "scripts/task_cost_report.py"
  - "tests/test_task_cost_report.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-09-29T18:13:43Z"
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

metrics task-cost печатает одну медиану на месяц, а состав задач по сложности за это время сдвинулся: май 50/43/11 simple/medium/complex, сентябрь 25/73/33. Смешанная строка 41k→79k (1,9x) читается как подорожание фреймворка, тогда как ВНУТРИ классов картина разная: simple 27k→22k (дешевле на 19%), medium 52k→88k (+69%), complex 68k→130k (+91%). Отчёт, который скрывает это, приводит к неверному выводу — я сам его сделал. Цель: тренд печатается по сложности, а смешанная строка либо уходит, либо несёт предупреждение о смене состава.

## Acceptance Criteria

AC-1 metrics task-cost печатает медиану и p90 ПО СЛОЖНОСТИ на месяц, а не одну смешанную. ✓ tests/test_task_cost_report.py
AC-2 Состав месяца назван числом задач в каждом классе — иначе читатель не увидит, что он сдвинулся.
AC-3 НЕГАТИВНЫЙ: класс с выборкой меньше порога не печатает медиану, а объявляет ОТСУТСТВИЕ — медиана по трём задачам выдаётся за тренд.
AC-4 НЕГАТИВНЫЙ: задача без объявленной сложности не попадает в чужой класс и не молчит — она в отдельной строке.
AC-5 Смешанная строка, если остаётся, несёт предупреждение, что состав между месяцами не постоянен.
AC-6 Полная лента зелёная.

## Plan

## Rollback

git revert; смешанный тренд возвращается

## Journal

- 2026-09-29T18:12:52Z [implementation] — AC-1 ✓ каждый месяц несёт медиану и счёт по классу; ✓ tests/test_task_cost_report.py::TestTheTrendIsSplitByComplexity::test_each_month_carries_a_figure_per_class. AC-2 ✓ состав назван числом задач в каждом классе в той же строке; проверено живым выводом: май simple n=50 medium n=43 complex n=11, сентябрь 25/73/33. AC-3 ✓ НЕГАТИВНЫЙ: класс меньше восьми задач медианы не печатает, но печатает счёт — ::test_a_thin_class_reports_absence_but_still_shows_its_count; скрытый счёт читался бы как «класс не трогали». AC-4 ✓ НЕГАТИВНЫЙ: задача без объявленной сложности идёт отдельной строкой (undeclared), а не вливается в чужой класс — ::test_a_task_with_no_declared_complexity_gets_its_own_line. AC-5 ✓ смешанная строка осталась и несёт предупреждение — ::test_the_blended_line_warns_that_the_mix_moved; отдельно требуется, чтобы класс без медианы на одном из концов НЕ давал отношения. AC-6 ✓ полная лента 12 475 passed, 34 skipped, 0 deselected. Domain: живой вывод разделяет то, что смешивала прежняя строка — simple 27k→22k (0,83x), medium 52k→88k (1,70x), complex 68k→130k (1,92x) при смешанном 1,9x. Побочно: mypy отказал на median|None в отношении — переписано через связывание, а не через игнор.
- 2026-09-29T18:13:01Z [implementation] — см. журнал и предыдущую попытку
- 2026-09-29T18:13:15Z [implementation] — Root cause (edge-case): отчёт сводил месяц одной медианой, неявно предполагая, что состав задач по сложности между месяцами постоянен. Он не постоянен — май 50/43/11 simple/medium/complex, сентябрь 25/73/33, — и смешанная медиана 41k→79k сложила «работа стала тяжелее» с «работа стала дороже», не различая их. Автор отчёта сам прочитал её как второе. Prevention: агрегат по времени, у которого есть категориальная переменная, обязан печатать разрез по ней, а смешанная строка — нести предупреждение о смене состава; класс с выборкой меньше порога объявляет отсутствие медианы, но не скрывает счёт.
- 2026-09-29T18:13:39Z [implementation] — AC-1 ✓ ::TestTheTrendIsSplitByComplexity::test_each_month_carries_a_figure_per_class. AC-2 ✓ состав назван числом задач на класс; живой вывод: май 50/43/11, сентябрь 25/73/33. AC-3 ✓ НЕГАТИВНЫЙ: ::test_a_thin_class_reports_absence_but_still_shows_its_count — класс меньше восьми задач не печатает медиану, но печатает счёт. AC-4 ✓ НЕГАТИВНЫЙ: ::test_a_task_with_no_declared_complexity_gets_its_own_line. AC-5 ✓ ::test_the_blended_line_warns_that_the_mix_moved, плюс отказ печатать отношение при медиане только на одном конце. AC-6 ✓ полная лента 12 475 passed, 34 skipped, 0 deselected. Domain: разделено то, что смешивалось — simple 0,83x, medium 1,70x, complex 1,92x при смешанном 1,9x. Побочно: mypy отказал на median|None — переписано связыванием, не игнором.
