---
slug: r14-task-done-v1-msg
title: "task_done v1: surface all blocking_failures or steer agents to v2 only"
status: done
epic: rel-14-readiness
story: rel-14-audit-fixes
complexity: null
role: null
stack: null
tier: moderate
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-01T00:19:26Z"
---

## Goal

Release 1.4 readiness: r14-task-done-v1-msg

## Acceptance Criteria

1. service_task.task_done() v1 raises ServiceError with message that aggregates ALL blocking failures, not just the first. 2. Format: stage-prefixed multiline, 180 char cap per failure. 3. Negative scenario: when blocking_failures is empty, no aggregation - falls back to default 'task_done failed'. 4. Backward compat: ServiceError type unchanged so existing CLI/MCP error handlers keep working.

## Plan

## Rollback

## Journal

- 2026-05-01T00:19:20Z [implementation] — AC: 1. Aggregation works - test_multiple_failures_aggregate verifies '[1]', '[2]', '[3]' numbered. 2. 180-char cap per failure - test_per_failure_message_cap. 3. Negative scenario - empty list falls back to 'task_done failed' (test_no_failures_falls_back_to_default). 4. Backward compat - single failure preserves old wording (test_single_failure_returns_unwrapped_message).
- 2026-05-01T00:19:20Z [implementation] — Implemented _format_task_done_failures helper with multi-failure aggregation. v1 task_done now raises ServiceError containing ALL blocking failures, not just first. 6 tests added.
- 2026-05-01T00:19:26Z [implementation] — AC verified: 1. Aggregation works - all blocking_failures appear in ServiceError message (test_multiple_failures_aggregate) ✓ 2. 180-char cap per failure preserved (test_per_failure_message_cap) ✓ 3. Negative scenario - empty list falls back to 'task_done failed' (test_no_failures_falls_back_to_default) ✓ 4. Backward compat - single failure preserves old wording (test_single_failure_returns_unwrapped_message) ✓
