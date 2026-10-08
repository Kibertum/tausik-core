---
slug: task-cost-in-turns-is-not-measured
title: "Цена задачи не измерена в ходах, а рычаг именно там"
status: done
epic: release-110-deferred-from-19
story: release110-terse-answers
complexity: medium
role: developer
stack: null
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/turn_economy.py"
  - "tests/test_turn_economy.py"
  - "docs/ru/cost-telemetry.md"
  - "docs/en/cost-telemetry.md"
scope_paths:
  - "scripts/turn_economy.py"
  - "tests/test_turn_economy.py"
  - "docs/ru/cost-telemetry.md"
  - "docs/en/cost-telemetry.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-09-29T12:15:10Z"
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

Цена измерена НА ЗАВЕРШЁННУЮ ЗАДАЧУ в ходах, а не на запрос. Память #746: 99,5% входа — cache_read, средний ход стоит ~482 000 токенов, значит лишний ХОД стоит около полумиллиона, и правка, экономящая длину запроса ценой лишнего хода, проигрывает примерно в сто раз. Отчёт должен назвать распределение ходов на задачу и то, что их порождает.

## Acceptance Criteria

1. Отчёт даёт ходы на завершённую задачу: медиана, p90, и сколько это в токенах по измеренной цене хода. 2. Названы категории того, что порождает ходы, с долями — из данных, а не из догадки. 3. НЕГАТИВНЫЙ: величина, которой нет в данных, объявляется отсутствующей, а не нулём; отчёт на пустых данных говорит это словами. 4. НЕГАТИВНЫЙ: отчёт НЕ предлагает экономить длину запроса там, где это стоит лишнего хода — вывод обязан следовать из замера #746, а не противоречить ему. 5. Полная лента зелёная.

## Plan

## Rollback

git revert; добавляется читающий отчёт, ничего не меняющий в поведении.

## Journal

- 2026-09-29T12:14:43Z [implementation] — AC-1: ✓ scripts/turn_economy.py на живых данных: 1230 закрытий, медиана 20 ходов, p90 78, максимум 1900; при измеренной цене хода 482 000 токенов это 9,6 млн на медианную задачу и 37,6 млн на p90. Тренд по месяцам: 2026-04 медиана 6 → 2026-09 медиана 32, p90 35 → 114 — впятеро за полгода. AC-2: ✓ распределение из данных, 8195 вызовов: Bash 87,6% и 3,64 из 4,07 млрд cache_read, Write 7,7%, Edit 2,7%, остальное меньше 2%. Тесты ::TestTurnsPerFinishedTask и ::TestWhereTheTurnsGo.
- 2026-09-29T12:14:54Z [implementation] — AC-3 НЕГАТИВНЫЙ: ✓ ::TestAbsenceIsStatedInWords — нет базы, закрытий меньше MIN_TASKS=20, нет сайдкара: три случая, все словами; задача без записанного счётчика НЕ считается нулём (::test_a_task_without_a_count_is_not_a_zero), иначе работа выглядела бы дешевеющей там, где тоньше стала запись. AC-4 НЕГАТИВНЫЙ: ✓ ::test_the_report_says_fewer_turns_not_shorter_ones — вывод обязан следовать замеру #746, а не интуиции; ::test_the_money_line_uses_the_measured_price_of_a_turn держит константу вместе с фразой, которая её тратит. AC-5: ✓ полная лента 12260 прошли, 34 пропущены. Domain: отчёт прогнан на живых 1230 закрытиях и 8195 вызовах, не на фикстуре. Замер записан памятью #798.
