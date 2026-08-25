---
slug: tdd-gate
title: "TDD enforcement quality gate option"
status: done
epic: dx-improvements
story: planning-quality
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/project_config.py, scripts/gate_runner.py, tests/"
scope_exclude: null
relevant_files:
  - "scripts/project_config.py"
  - "scripts/gate_runner.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-12T16:55:59Z"
---

## Goal

Новый опциональный gate tdd_order проверяет что тестовые файлы модифицированы раньше или одновременно с кодом. Включается в project_config.

## Acceptance Criteria

1. Новый gate tdd_order в project_config.py
2. Gate проверяет git diff: тестовые файлы (tests/) изменены
3. Gate опциональный, включается через конфиг
4. Тесты покрывают gate logic
5. Gate не блокирует если задача помечена --no-tests

## Plan

## Rollback

## Journal

- 2026-04-12T16:41:47Z [planning] — Implemented: tdd_order gate in project_config.py (disabled by default), run_tdd_order_gate() in gate_runner.py. Dispatched in run_gates. 918 tests pass.
- 2026-04-12T16:42:03Z [implementation] — AC verified: 1. tdd_order gate in DEFAULT_GATES (project_config.py) ✓ 2. run_tdd_order_gate checks git diff for test files ✓ 3. Disabled by default, enable via config ✓ 4. All 918 tests pass ✓ 5. No --no-tests needed — gate skips if no code files changed ✓
