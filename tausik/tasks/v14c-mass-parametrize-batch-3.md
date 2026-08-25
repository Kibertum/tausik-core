---
slug: v14c-mass-parametrize-batch-3
title: "[WONT FIX 1.4] C1c: mass parametrize — Long-tail (=2 tests, ~145 групп)"
status: done
epic: v14-polish-followup
story: v14-polish-c-followup
complexity: simple
role: qa
stack: python
tier: trivial
call_budget: 10
defect_of: null
scope: "notes update + tausik_decide call + CHANGELOG.md/CHANGELOG.ru.md entries"
scope_exclude: "tests/* (no parametrize edits in 1.4); .tausik/* (no infra changes); production code"
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-07T19:59:36Z"
---

## Goal

[DEFERRED to 1.4.1] Long-tail #68-212 (size = 2 tests, 145 групп, 290 тестов) из 2026-05-07 audit. Net potential -145 тестов, но 2-test группы — высокий риск false-positive (structural identity ≠ semantic identity); часто это legit happy/sad pairs, не дубли. Per-group верификация ~5 минут на удаление 1 теста — плохой ROI для 1.4 polish. Re-evaluate в 1.4.1: explore-first проход с фильтрацией false positives перед parametrize.

## Acceptance Criteria

AC-1: Stop-gap rationale зафиксирован в notes + Decision recorded — НЕ обрабатываем 145 size=2 групп в 1.4.0; closure как WONT FIX (а не deferral в 1.4.1, по требованию пользователя «не дробить минор»). AC-2: N/A (no parametrize work in 1.4 scope). AC-3: N/A (no test count delta from this task). AC-4: ruff + mypy unchanged from baseline (no edits to test sources). AC-5: Negative — если в будущем audit перегенерируется и пара групп окажутся real dupes — отдельный point-fix в 1.4.x вместо bulk batch. AC-6: scope = только notes + decision + CHANGELOG (no source files). AC-7: tausik_decide id зафиксирован в notes как final decision link.

## Plan

## Rollback

## Journal

- 2026-05-07T19:59:34Z [implementation] — AC verified: 1. ✓ Stop-gap rationale recorded — Decision #83 (WONT FIX в 1.4.0, не переносим в 1.4.1 per user). 2. N/A — no parametrize work. 3. N/A — no test count delta. 4. ✓ ruff + mypy не трогали (no source edits). 5. ✓ Negative path documented: post-1.4 audit re-flag → точечный fix в 1.4.x. 6. ✓ scope только notes + decision + CHANGELOG. 7. ✓ Decision #83 link зафиксирован.
