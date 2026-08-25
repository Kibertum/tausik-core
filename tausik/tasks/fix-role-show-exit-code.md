---
slug: fix-role-show-exit-code
title: "role CLI swallows ServiceError → exits 0 (silent error)"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: null
tier: light
call_budget: 18
defect_of: null
scope: "scripts/project_cli_role.py (handler error propagation); tests/test_service_roles.py (add CLI exit-code regression test)."
scope_exclude: "scripts/project_cli_specs.py, scripts/project_cli_adapts.py (identical bug — sibling task); scripts/service_roles.py logic; project.py top-level handler (already correct)."
relevant_files:
  - "scripts/project_cli_role.py"
  - "tests/test_project_cli_role.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-26T10:21:12Z"
---

## Goal

Fix a silent-error violation (CLAUDE.md zero-tolerance): the role subcommands (show/create/update/delete) catch the exception locally, print 'Error:' to STDOUT, and return — yielding exit 0 on a real failure. task-family handlers instead let ServiceError propagate to project.py:159 which prints to stderr + sys.exit(1). Make role errors behave the same: non-zero exit + stderr, consistent with the rest of the CLI. (specs/adapts share the identical bug — filed as a sibling task.)

## Acceptance Criteria

1. `tausik role show <nonexistent>` exits non-zero (1), matching `task show <missing>`. 2. The error message goes to STDERR, not stdout. 3. The same non-zero-on-error behavior holds for role create/update/delete failure paths (e.g. duplicate/invalid slug). 4. A regression test (subprocess, asserting returncode != 0) covers `role show <missing>`. 5. NEGATIVE/EDGE: a SUCCESSFUL `role show <existing>` still exits 0 and prints the profile (happy path unbroken); `role list` unaffected.

## Plan

## Rollback

git checkout -- scripts/project_cli_role.py tests/test_service_roles.py

## Journal

- 2026-07-26T10:21:10Z [implementation] — AC1 role show missing exit=1 (was 0). AC2 error to stderr, stdout empty. AC3 create/update/delete non-zero (test_role_create_failure). AC4 regression test tests/test_project_cli_role.py (3 tests, pytest PASS scoped run #1344). AC5 happy path role show existing exits 0 (test_role_show_existing). Full role suite 20/20. Deployed via bootstrap. Domain: a CI/script checking $? now correctly detects role-command failures.
