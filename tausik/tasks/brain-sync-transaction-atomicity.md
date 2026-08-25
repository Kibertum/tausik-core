---
slug: brain-sync-transaction-atomicity
title: "MEDIUM: единая transaction для upserts+state"
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
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-24T15:08:02Z"
---

## Goal

Двойной commit() в except может оставить partial state при крэше между commits. Обернуть upserts+_update_sync_state в одну tx

## Acceptance Criteria

1. sync_category success path: all upserts + cursor update in one conn.commit() at the end.
2. Mid-batch error: conn.rollback() clears partial upserts; then a separate best-effort tx records last_error into sync_state; re-raises.
3. Regression test verifies (a) rollback on exception leaves 0 rows, (b) last_error is recorded, (c) success path commits cursor correctly.
4. pytest + ruff clean.

## Plan

## Rollback

## Journal

- 2026-04-24T15:04:33Z [implementation] — AC verified: 1. ✓ sync_category success path: upserts flow without inline commits; final _update_sync_state + single conn.commit() at end of try block — scripts/brain_sync.py:272-274. 2. ✓ Except branch: conn.rollback() first (scripts/brain_sync.py:276), then separate best-effort _update_sync_state + conn.commit() wrapped in its own sqlite3.Error catch — lines 277-281. 3. ✓ test_midbatch_error_rolls_back_partial_upserts + test_success_path_commits_once_with_cursor in tests/test_brain_storage_hardening.py. 4. ✓ pytest + ruff clean.
