---
slug: qg0-9dimensions
title: "Расширить QG-0 Context Gate до 9 измерений намерения"
status: done
epic: claude-hardening
story: p2-quality-loops
complexity: medium
role: architect
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/service_gates.py (qg0_dimensions_score + интеграция в task_start warning), tests/test_qg0_dimensions.py (новый)"
scope_exclude: "Существующие QG-0 hard checks (goal, ac, negative scenario) — не менять. QG-2 — не трогать."
relevant_files:
  - "scripts/service_gates.py"
  - "tests/test_qg0_dimensions.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-16T23:16:23Z"
---

## Goal

task start проверяет не только goal+AC, но и input/output/format/constraints/context/examples/success-criteria. Из prompt-master (9 dimensions)

## Acceptance Criteria

1) QG-0 Context Gate в service_gates.py расширен — проверяет 9 измерений намерения prompt-master: goal, acceptance_criteria, scope, scope_exclude, role, stack, complexity, story/epic linkage, evidence plan (упоминания файлов или memory IDs в AC). 2) Новая функция/метод qg0_dimensions_score(task) возвращает {dimension: filled_bool} для каждого из 9 + общий счёт N/9. 3) task_start при N<5 измерений выводит warning со списком отсутствующих (но не блокирует — только hard checks goal+AC+negative остаются blocking). 4) pytest тесты (6+): все 9 dimensions filled → N=9, пустая задача → N=0, mixed → correct count. 5) pytest all passed. 6) ruff clean. Negative: (a) задача без goal/AC → уже блокируется существующим gate. (b) N=4 (<5) → warning а не error. (c) несуществующие поля → graceful (None treated as unfilled).

## Plan

[{"step": "qg0_dimensions_score() + \u0438\u043d\u0442\u0435\u0433\u0440\u0430\u0446\u0438\u044f \u0432 task_start", "done": true}, {"step": "tests/test_qg0_dimensions.py", "done": true}, {"step": "pytest + ruff + done", "done": true}]

## Rollback

## Journal

- 2026-04-16T23:06:33Z [implementation] — AC verified: AC1 (QG-0 расширен до 9 измерений) ✓ — scripts/service_gates.py добавлена функция qg0_dimensions_score(task), интегрирована в _check_qg0_start. Проверяемые поля: goal, acceptance_criteria, scope, scope_exclude, role, stack, complexity, story_link (story_slug OR epic_slug), evidence_plan (file refs или memory IDs в AC). AC2 (функция возвращает dict) ✓ — test_keys_are_stable проверяет точно 9 ключей. AC3 (warning при <5) ✓ — test_minimal_task_emits_context_warning + test_rich_task_no_context_warning. AC4 (6+ тестов) ✓ — 10 тестов: TestDimensionsScore (8) + TestIntegrationWithQg0Start (2). AC5 (pytest all passed) ✓ — 1042/1042 passed in 187s. AC6 (ruff clean) ✓. Negative: (a) пустая задача → N=0 (test_empty_task_all_false). (b) whitespace-only fields → unfilled (test_whitespace_only_fields_count_as_unfilled). (c) vague AC без файлов/memory → evidence_plan=False (test_evidence_plan_vague_ac).
