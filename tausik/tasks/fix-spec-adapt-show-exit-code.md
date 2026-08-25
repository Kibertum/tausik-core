---
slug: fix-spec-adapt-show-exit-code
title: "spec/adapt CLI swallow ServiceError → exit 0 (same silent-error as role)"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: null
tier: light
call_budget: 25
defect_of: null
scope: "scripts/project_cli_specs.py, scripts/project_cli_adapts.py (error propagation); tests/test_project_cli_specs.py + tests/test_project_cli_adapts.py (new regression tests)."
scope_exclude: "scripts/project_cli_role.py (already fixed); service layer; project.py top-level (already correct); .claude/ deployed copies."
relevant_files:
  - "scripts/project_cli_specs.py"
  - "scripts/project_cli_adapts.py"
  - "tests/test_project_cli_specs.py"
  - "tests/test_project_cli_adapts.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-26T11:28:50Z"
---

## Goal

Sibling of fix-role-show-exit-code: project_cli_specs.py:56 and project_cli_adapts.py:71 catch ServiceError, print 'Error:' to stdout, and return None → exit 0 on real failure. Same silent-error violation. Apply the same fix: route to stderr + non-zero exit, consistent with the top-level project.py handler and the task-family commands. Add regression tests mirroring test_project_cli_role.py.

## Acceptance Criteria

1. project_cli_specs.py and project_cli_adapts.py no longer swallow ServiceError to exit 0: the handler routes the error to STDERR and exits non-zero, matching project_cli_role.py and the top-level project.py handler. 2. `tausik spec show <missing>` and `tausik adapt show <missing>` (or any spec/adapt error path) exit non-zero (was 0). 3. Regression tests (subprocess-free, mirroring test_project_cli_role.py) assert SystemExit(1) + stderr for at least one spec and one adapt error path. 4. NEGATIVE/EDGE: successful spec/adapt commands still exit 0 (happy path unbroken); the 'Unknown subcommand' path behavior is preserved; no other CLI family touched.

## Plan

## Rollback

git checkout -- scripts/project_cli_specs.py scripts/project_cli_adapts.py && rm -f tests/test_project_cli_specs.py tests/test_project_cli_adapts.py

## Journal

- 2026-07-26T11:28:34Z [implementation] — AC verified: 1. ✓ project_cli_specs.py + project_cli_adapts.py dispatch except-blocks now `print(..., file=sys.stderr); sys.exit(1)` (added import sys), matching project_cli_role.py + project.py:159 contract. 2. ✓ spec/adapt error paths exit non-zero (regression tests assert code==1). 3. ✓ New tests/test_project_cli_specs.py + test_project_cli_adapts.py (2 each): error→SystemExit(1) on stderr, stdout empty; happy path no SystemExit + stdout has message. 4. ✓ NEGATIVE: success path unbroken (test_success_does_not_exit); 'Unknown subcommand' path preserved (after the except, unchanged); no other family touched. 71 passed (new + existing test_specs/test_adapts). Files 107/137 lines (≤400). Domain: a CI/script checking $? now detects spec/adapt command failures — the last two swallow-to-0 families are closed.
