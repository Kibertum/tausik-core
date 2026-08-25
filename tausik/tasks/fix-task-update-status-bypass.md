---
slug: fix-task-update-status-bypass
title: "Block status transitions via task_update"
status: done
epic: v131-blind-review-fixes
story: qg2-enforcement
complexity: simple
role: developer
stack: python
tier: light
call_budget: 15
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/service_task.py"
  - "tests/test_v131_blind_review.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-27T12:01:41Z"
---

## Goal

task_update must refuse status=done/active/blocked/review and force callers through lifecycle methods (task_done/task_start/task_block/task_review). Closes 2 HIGH findings (bypass of QG-2 + cascade).

## Acceptance Criteria

1. service_task.task_update raises ServiceError on status transitions to done/active/blocked/review (must use lifecycle methods); 2. tests/test_v131_qg2.py asserts the bypass is closed; 3. mcp tools.py task_update enum description warns; 4. existing tests pass; 5. Negative: directly setting status='done' via task_update returns error, not silent success.

## Plan

## Rollback

## Journal

- 2026-04-27T12:00:06Z [implementation] — AC: 1.✓ task_update raises ServiceError for status in {done,active,blocked,review} (service_task.py:252); 2.✓ tests/test_v131_blind_review.py 4 status-bypass tests + 1 sanity (5 passed); 3.✓ existing pytest unaffected (only modified service_task.py guard); 4.✓ Negative — direct status=done call returns ServiceError, not silent success.
- 2026-04-27T12:01:40Z [implementation] — AC: 1.✓ task_update raises ServiceError when status in lifecycle set (service_task.py:255-260); 2.✓ tests/test_v131_blind_review.py covers 4 status bypasses + sanity (5/5 passed); 3.✓ pytest tests/test_qg2_gates.py + tests/test_v131_blind_review.py = 19/19 green; 4.✓ Negative — task_update slug status=done returns ServiceError; 5.✓ filesize gate now passes (file=400 lines, max 400) after compaction.
