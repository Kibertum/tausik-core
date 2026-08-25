---
slug: tests-qg2-gates
title: "Тесты для _run_quality_gates и verification checklist"
status: done
epic: polish
story: test-gaps
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "tests/test_qg2_gates.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-05T19:37:21Z"
---

## Goal

_run_quality_gates тестируется с mock gate_runner (не пропускается через FRAI_SKIP_GATES). _check_verification_checklist возвращает non-empty warning. _verify_ac per-criterion path покрыт.

## Acceptance Criteria

1. Тест для _run_quality_gates с mock gate_runner (без FRAI_SKIP_GATES). 2. Тест: blocking gate failure → ServiceError. 3. Тест: _check_verification_checklist returns warning string. 4. Тест: _verify_ac per-criterion warning path. 5. Ошибка если _run_quality_gates пропускается во всех тестах.

## Plan

[{"step": "\u041d\u0430\u043f\u0438\u0441\u0430\u0442\u044c \u0442\u0435\u0441\u0442 _run_quality_gates \u0441 mock gate_runner (unset FRAI_SKIP_GATES)", "done": false}, {"step": "\u041d\u0430\u043f\u0438\u0441\u0430\u0442\u044c \u0442\u0435\u0441\u0442: blocking gate \u2192 ServiceError", "done": false}, {"step": "\u041d\u0430\u043f\u0438\u0441\u0430\u0442\u044c \u0442\u0435\u0441\u0442 _check_verification_checklist returns warning", "done": false}, {"step": "\u041d\u0430\u043f\u0438\u0441\u0430\u0442\u044c \u0442\u0435\u0441\u0442 _verify_ac per-criterion warning", "done": false}, {"step": "\u041f\u0440\u043e\u0433\u043d\u0430\u0442\u044c \u0442\u0435\u0441\u0442\u044b", "done": false}]

## Rollback

## Journal

- 2026-04-05T19:37:12Z [implementation] — AC verified: 10 тестов — _run_quality_gates с mock (без SKIP), checklist warning, AC per-criterion ✓
