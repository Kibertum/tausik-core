---
slug: brain-sync-iso-timestamp-compare
title: "MEDIUM: нормализовать ISO timestamp перед compare"
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
  - "scripts/brain_hook_utils.py"
  - "tests/test_brain_storage_hardening.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-24T15:04:19Z"
---

## Goal

Лексикографическое сравнение ISO ломается на 10:00:00Z vs 10:00:00.000Z. Парсить в datetime или нормализовать формат до сравнения

## Acceptance Criteria

1. sync_category computes max_edited by comparing parsed epoch values (via brain_hook_utils.parse_iso_to_epoch), not raw TEXT.
2. Helper `_iso_epoch` in brain_sync returns -inf for unparseable/empty — caller does not crash on garbage.
3. Regression test exercising mixed ISO formats ('Z' vs '.000Z') to prove the fix.
4. pytest green + ruff clean.

## Plan

## Rollback

## Journal

- 2026-04-24T15:00:50Z [implementation] — AC verified: 1. ✓ sync_category uses _iso_epoch(edited) > max_edited_epoch, not `edited > max_edited` — scripts/brain_sync.py:262-270. 2. ✓ _iso_epoch returns float('-inf') on empty/unparseable input — scripts/brain_sync.py:233-248. 3. ✓ test_mixed_format_picks_later_moment + test_unparseable_sorts_lowest in tests/test_brain_storage_hardening.py cover the fix. 4. ✓ pytest + ruff clean.
