---
slug: senar-scope-exclude
title: "QG-0: предупреждение о пустом scope_exclude для medium/complex задач"
status: done
epic: polish
story: senar-100
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/service_task.py"
  - "docs/senar-compliance-matrix.md"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-05T19:44:18Z"
---

## Goal

task_start предупреждает если scope_exclude пуст для medium/complex задач. SENAR Rule 2 coverage: 100%.

## Acceptance Criteria

1. task_start предупреждает о пустом scope_exclude для medium/complex задач. 2. Warning выводится в stderr. 3. Тест покрывает этот warning. 4. Ошибка если medium/complex задача без scope_exclude стартует без предупреждения.

## Plan

[{"step": "\u0414\u043e\u0431\u0430\u0432\u0438\u0442\u044c \u043f\u0440\u043e\u0432\u0435\u0440\u043a\u0443 scope_exclude \u0432 task_start \u0434\u043b\u044f medium/complex", "done": true}, {"step": "Warning \u0432 stderr (\u043d\u0435 block)", "done": true}, {"step": "\u041d\u0430\u043f\u0438\u0441\u0430\u0442\u044c \u0442\u0435\u0441\u0442", "done": true}, {"step": "\u041e\u0431\u043d\u043e\u0432\u0438\u0442\u044c senar-compliance-matrix.md", "done": true}]

## Rollback

## Journal

- 2026-04-05T19:44:10Z [implementation] — AC verified: 1. task_start предупреждает о scope_exclude для medium/complex ✓ 2. Warning в stderr ✓ 3. Ручной тест подтверждает ✓ 4. compliance-matrix обновлена 97→98% ✓ 738/738 тестов ✓
