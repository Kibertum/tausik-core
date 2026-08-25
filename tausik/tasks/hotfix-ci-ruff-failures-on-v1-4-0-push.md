---
slug: hotfix-ci-ruff-failures-on-v1-4-0-push
title: "Hotfix: CI ruff failures on v1.4.0 push"
status: done
epic: null
story: null
complexity: null
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "tests/test_push_ok_cli.py, scripts/project_cli_extra.py, tests/test_session_metrics_parse.py, tests/test_subagent_reviewer.py"
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-07T20:54:09Z"
---

## Goal

CI on Kibertum/tausik-core failed v1.4.0 push with 4 ruff errors. 1 introduced by my push-gate hotfix (test_push_ok_cli.py: unused 'timezone' import); 3 are pre-existing baseline drift flagged in last session's handoff (project_cli_extra.py: unused 'tausik_config_path'; test_session_metrics_parse.py: unused 'm' variable; test_subagent_reviewer.py: unused 'tempfile'). Local pre-commit runs only mypy, not ruff — so all four only surface in CI. Fix all four to restore CI green.

## Acceptance Criteria

AC-1: tests/test_push_ok_cli.py — drop unused `timezone` from top-level import (still imported per-method in inner test bodies as needed); AC-2: scripts/project_cli_extra.py — drop unused `tausik_config_path` import; AC-3: tests/test_session_metrics_parse.py — drop or use unused `m` variable; AC-4: tests/test_subagent_reviewer.py — drop unused `tempfile` import; AC-5: `ruff check scripts/ tests/ bootstrap/` exits 0 locally — non-zero exit means a regression in this hotfix; AC-6: pytest scoped on changed test files passes (no negative collateral); AC-7 (negative): if any of the 4 unused-import fixes accidentally remove a still-referenced name, the corresponding test file MUST fail-fast with NameError on import — verified by re-running the four affected test files after edits.

## Plan

## Rollback

## Journal

- 2026-05-07T20:54:04Z [implementation] — All 4 ruff F401/F841 errors fixed: tests/test_push_ok_cli.py:14 (timezone removed from top import — inner test methods import their own copies), scripts/project_cli_extra.py:9 (tausik_config_path removed — was never used), tests/test_session_metrics_parse.py:130 (orphan touch line removed), tests/test_subagent_reviewer.py:16 (tempfile import removed). `ruff check scripts/ tests/ bootstrap/` → All checks passed. Scoped pytest 25/25 PASS — AC-7 negative case verified, no NameError on import.
