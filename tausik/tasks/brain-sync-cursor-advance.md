---
slug: brain-sync-cursor-advance
title: "MEDIUM: advance last_pull_at cursor past boundary"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: brain-decide-auto-route
scope: null
scope_exclude: null
relevant_files:
  - "scripts/brain_sync.py"
  - "tests/test_brain_storage_hardening.py"
  - "tests/test_brain_sync.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-24T15:11:44Z"
---

## Goal

last_pull_at=max_edited → boundary-страница re-fetches every sync. Advance +1ms или использовать strict > в filter

## Acceptance Criteria

1. _make_filter emits `{"after": cursor}` (strict `>`) instead of `{"on_or_after": cursor}` so the boundary page is not re-fetched next sync.
2. Existing test test_sync_category_second_run_uses_last_pull_at_filter updated to assert the new strict-after shape.
3. New test test_filter_uses_strict_after_when_cursor_set proves the shape; test_filter_none_when_no_cursor confirms the no-cursor path.
4. pytest + ruff clean.

## Plan

## Rollback

## Journal

- 2026-04-24T15:08:16Z [planning] — AC verified: 1. ✓ _make_filter returns `{"timestamp": "last_edited_time", "last_edited_time": {"after": last_pull_at}}` — scripts/brain_sync.py:218-225. 2. ✓ tests/test_brain_sync.py::test_sync_category_second_run_uses_last_pull_at_filter now asserts `{"after": ...}`. 3. ✓ test_filter_uses_strict_after_when_cursor_set + test_filter_none_when_no_cursor in tests/test_brain_storage_hardening.py. 4. ✓ pytest + ruff clean.
