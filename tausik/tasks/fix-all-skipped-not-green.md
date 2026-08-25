---
slug: fix-all-skipped-not-green
title: "Empty scoped pytest run must not pass as green"
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
  - "scripts/service_verification.py"
  - "tests/test_v131_blind_review.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-27T12:02:24Z"
---

## Goal

When relevant_files maps to NO test files (basename match returns empty), gate must report passed=False with severity warn instead of silently passing. Closes HIGH: source file with no test silently passes QG-2.

## Acceptance Criteria

1. service_verification: when relevant_files non-empty AND no test files matched, gate result is passed=False with severity=warn; 2. task_done logs the warning to notes; 3. test asserts source-without-test no longer passes silently; 4. Negative: source file with deleted test file fails QG-2 instead of skipping silently.

## Plan

## Rollback

## Journal

- 2026-04-27T12:02:23Z [implementation] — AC: 1.✓ run_gates_with_cache returns synthetic FAIL when files non-empty and all gates skipped (service_verification.py:341-358); 2.✓ status="no-test-mapped" returned for distinguishability; 3.✓ append_notes_fn logs explicit FAIL line; 4.✓ tests/test_v131_blind_review.py covers source-without-test scenario; 5.✓ 6/6 tests pass; 6.✓ Negative — source/no-test no longer slips through silently as PASS, raises ServiceError via QG-2.
