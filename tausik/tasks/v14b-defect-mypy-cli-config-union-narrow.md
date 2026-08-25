---
slug: v14b-defect-mypy-cli-config-union-narrow
title: v14b-defect-mypy-cli-config-union-narrow
status: done
epic: null
story: null
complexity: null
role: developer
stack: python
tier: null
call_budget: null
defect_of: b8-pre-model-profile-auto-detect-interactive-promp
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-07T08:44:18Z"
---

## Goal

Fix mypy union-attr error in scripts/project_cli_config.py:59 — narrow result['errors'] from union to dict[str, str] before .items() iteration. Surfaced by pre-commit hook.

## Acceptance Criteria

1. Narrow result['errors'] union to dict[str, str] before .items() iteration in scripts/project_cli_config.py::cmd_skill_rebuild. 2. mypy clean on scripts/project_cli_config.py. 3. Pre-commit hook passes for batched commit.

## Plan

## Rollback

## Journal

- 2026-05-07T08:44:18Z [implementation] — AC verified: 1.✓ result['errors'] narrowed via isinstance(errors, dict). 2.✓ mypy Success no issues found in 1 source file. 3.✓ pre-commit passed; commit landed (58 files, +3065/-426).
