---
slug: task-done-closes-a-task-that-never-started
title: "task done closes a task that never started: planning -> done skips QG-0 and leaves no started_at"
status: done
epic: release-110-deferred-from-19
story: release110-open-defects
complexity: medium
role: backend
stack: null
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/service_task_done.py"
  - "scripts/task_obsolete.py"
  - "tests/test_task_obsolete.py"
scope_paths:
  - "scripts/service_task_done.py"
  - "scripts/task_obsolete.py"
  - "tests/*.py"
  - "docs/ru/*.md"
  - "docs/en/*.md"
  - "CHANGELOG*.md"
scope_tools: []
depends_on: []
completed_at: "2026-09-24T06:10:52Z"
---

## Goal

A task that never passed task start (QG-0) cannot be closed as done: today task_done refuses only an already-done task, so 52 of 1571 done tasks have no started_at, six of them in September 2026.

## Acceptance Criteria

1. task done on a task in planning is refused with a message that names task start (and, once it exists, the obsolete exit) as the way forward. 2. NEGATIVE: a test starts nothing, calls task_done on a planning task with full evidence, and fails if the task closes. 3. NEGATIVE: active, blocked and review tasks close exactly as before; the 52 historical rows are reported, not rewritten. 4. Sequenced with a-task-cannot-be-closed-as-obsolete: blocking this path before an obsolete exit exists leaves owner-ordered closes of obsolete tasks with only delete — the owner decides the order.

## Plan

## Rollback

git revert; the status precondition is one check in service_task_done

## Journal

- 2026-09-24T06:09:40Z [implementation] — AC-1: ✓ tests/test_task_obsolete.py::test_task_done_refuses_a_task_that_never_started — task_done on a planning task raises 'was never started' naming 'task start <slug>' and 'task obsolete <slug> --reason'; the check lives in task_obsolete.refuse_unclosable, called before any write (service_task_done.py 509 -> 498 lines).
- 2026-09-24T06:09:40Z [implementation] — AC-2: ✓ tests/test_task_obsolete.py::test_task_done_refuses_a_task_that_never_started — negative, full evidence logged, the task stays planning; mutation (planning branch disabled) -> 1 failed, 8 passed; restored.
- 2026-09-24T06:09:40Z [implementation] — Root cause: service_task_done.task_done refused only status 'done'; nothing checked that the task had ever passed task start, so planning -> done went around QG-0.
- 2026-09-24T06:09:41Z [implementation] — AC-3: ✓ measurement — negative: the full suite with the refusal in place: 10906 passed, 23 skipped (active/blocked/review closes unchanged, no fixture relied on planning -> done); the 52 historical rows are not rewritten.
- 2026-09-24T06:09:41Z [implementation] — AC-4: ✓ review — sequenced as decided (#390): the obsolete exit landed first in a-task-cannot-be-closed-as-obsolete, so owner-ordered closes of stale tasks keep an honest path.
