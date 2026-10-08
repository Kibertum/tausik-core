---
slug: type-fix-verify-baseline-windows-after-mypy
title: "Type fix verify_baseline windows after mypy commit-hook red"
status: done
epic: null
story: null
complexity: null
role: null
stack: null
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/verify_baseline.py"
scope_paths: []
scope_tools: []
assurance_profiles: []
assurance_impact: null
depends_on: []
completed_at: "2026-10-07T17:13:34Z"
resolution: null
resolution_reason: null
tracker_refs: []
started_model_id: null
started_model_version: null
done_model_id: null
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

Fix the 3 mypy arg-type/assignment errors the commit hook found in scripts/verify_baseline.py window handling without changing behavior

## Acceptance Criteria

python -m mypy on the repo is clean (0 errors). AC negative: pytest tests/test_verify_baseline.py stays 4 passed with unchanged assertions - the fix touches typing only, not counting.

## Plan

## Rollback

## Journal

- 2026-10-07T17:13:29Z [implementation] — AC-1: python -m mypy scripts/verify_baseline.py — 0 errors (was 3 arg-type/assignment on the window dict). AC-2 negative: pytest tests/test_verify_baseline.py — 4 passed, assertions unchanged; counting behavior untouched: the fix introduces TypedDict _Window(story, members, runs) and types windows as list[_Window], no logic change. Verified by verify run #3614 (PASS).
