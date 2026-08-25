---
slug: fix-mypy-no-any-return-in-risk-l3-trigger
title: "Fix mypy no-any-return in risk_l3_trigger"
status: done
epic: null
story: null
complexity: null
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/risk_l3_trigger.py одна строка"
scope_exclude: null
relevant_files:
  - "scripts/risk_l3_trigger.py"
  - "tests/test_risk_l3_trigger.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-12T02:00:19Z"
---

## Goal

pre-commit mypy: measured_score возвращает Any из round(); привести к float

## Acceptance Criteria

1. mypy чистый (0 errors). 2. Негативный: тесты measured_score не регрессируют (None-пути), 15 passed.

## Plan

## Rollback

## Journal

- 2026-06-12T02:00:19Z [implementation] — AC verified: 1. OK mypy 0 errors (153 files на коммите ниже). 2. OK tests/test_risk_l3_trigger.py 15 passed.
