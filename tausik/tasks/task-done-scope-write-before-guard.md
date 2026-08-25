---
slug: task-done-scope-write-before-guard
title: "task done overwrites a certified task's scope before the already-done guard fires"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: python
tier: light
call_budget: 12
defect_of: null
scope: "scripts/service_task_done.py, tests/test_verify_scope_pointer.py (or a new test)"
scope_exclude: "scripts/task_done_scope.py (persist logic itself is correct), any gate/verify infra"
relevant_files:
  - "scripts/service_task_done.py"
  - "tests/test_verify_scope_pointer.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-25T06:12:01Z"
---

## Goal

persist_declared_scope() in _task_done_report runs and WRITES relevant_files to the task row before the `if task['status'] == 'done'` guard. So `task done <already-done-slug> --relevant-files X` silently mutates the scope of a closed, certified task (the scope that fed its risk_score/verify-cache hash/receipt), then raises 'already done'. The caller sees only the error; the corruption is invisible. Move the already-done guard ahead of any write so a call that itself fails can never rewrite a closed task's scope.

## Acceptance Criteria

1. In service_task_done._task_done_report, the `task['status'] == 'done'` guard raises BEFORE persist_declared_scope is ever called (no DB write reachable on an already-done slug). 2. Happy path: a non-done task closed with --relevant-files still persists scope and closes — no regression in test_verify_scope_pointer.py. 3. Negative/boundary scenario: calling task_done on an ALREADY-DONE task with a DIFFERENT --relevant-files must raise 'already done' AND leave the stored relevant_files UNCHANGED (regression test asserts the row is not mutated). 4. Negative: an unknown slug still raises cleanly (no partial write). 5. Full scoped verify green.

## Plan

## Rollback

## Journal

- 2026-07-25T06:10:34Z [implementation] — Fixed: moved the `status=='done'` guard ahead of persist_declared_scope in _task_done_report (service_task_done.py). No DB write is now reachable on an already-done slug. Added regression class TestAnAlreadyDoneTaskScopeIsNotRewritten in test_verify_scope_pointer.py: re-closing a done task with different --relevant-files raises 'already done' AND leaves stored relevant_files byte-identical. Ran tests/test_verify_scope_pointer.py: 9 passed.
- 2026-07-25T06:11:00Z [implementation] — AC verified: 1. ✓ service_task_done.py: `if task['status']=='done': raise` now precedes persist_declared_scope — no write reachable on a done slug 2. ✓ tests/test_verify_scope_pointer.py TestADeclarationSurvivesABlockedClose still green (9 passed) — happy-path close still persists scope 3. ✓ tests/test_verify_scope_pointer.py::TestAnAlreadyDoneTaskScopeIsNotRewritten::test_reclosing_with_different_files_neither_mutates_nor_succeeds — raises ServiceError('already done') AND asserts stored relevant_files byte-identical 4. ✓ unknown slug: _require_task raises before any write (guard path unchanged); no partial write possible 5. ✓ verify run #1297 exit=0, pytest scoped over tests/test_verify_scope_pointer.py PASS
- 2026-07-25T06:11:59Z [implementation] — AC verified: 1. ✓ service_task_done.py: `if task['status']=='done': raise` now precedes persist_declared_scope — no write reachable on a done slug 2. ✓ tests/test_verify_scope_pointer.py TestADeclarationSurvivesABlockedClose still green (9 passed) — happy-path close still persists scope 3. ✓ tests/test_verify_scope_pointer.py::TestAnAlreadyDoneTaskScopeIsNotRewritten — raises ServiceError('already done') AND asserts stored relevant_files byte-identical 4. ✓ unknown slug: _require_task raises before any write; no partial write possible 5. ✓ verify run #1297 exit=0, pytest scoped over tests/test_verify_scope_pointer.py PASS
