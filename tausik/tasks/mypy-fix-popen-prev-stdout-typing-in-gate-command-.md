---
slug: mypy-fix-popen-prev-stdout-typing-in-gate-command-
title: "mypy fix: Popen prev_stdout typing in gate_command_runner"
status: done
epic: null
story: null
complexity: null
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/gate_command_runner.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-13T09:14:32Z"
---

## Goal

Pre-commit mypy упал на _exec_pipeline: prev:object не имеет .close(). Заменить на IO[str]|None + Popen[str]. AC: mypy зелёный, pytest gate-тесты зелёные.

## Acceptance Criteria

1. mypy зелёный (python -m mypy без ошибок). 2. pytest tests/test_gate_shellless.py + tests/test_gate_truncation_pipe.py зелёные. 3. Негативный: многостадийный pipe (a | b) при ошибке промежуточной стадии не вешает раннер и возвращает rc!=0.

## Plan

## Rollback

## Journal

- 2026-06-13T09:14:25Z [implementation] — AC verified: 1. mypy Success no issues. 2. pytest 29 passed. 3. многостадийный pipe покрыт test_real_pipe_chains; intermediate stderr->DEVNULL, kill+wait при timeout — раннер не виснет.
