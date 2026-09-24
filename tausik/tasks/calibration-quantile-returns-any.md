---
slug: calibration-quantile-returns-any
title: "mypy: calibration quantile helper returns Any"
status: done
epic: release-110-deferred-from-19
story: release110-open-defects
complexity: simple
role: developer
stack: null
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/backend_tier_metrics.py"
  - "tests/test_metrics_tier.py"
scope_paths:
  - "scripts/backend_tier_metrics.py"
scope_tools: []
depends_on: []
completed_at: "2026-09-24T07:35:27Z"
---

## Goal

The pre-commit mypy check passes: the calibration quantile helper returns a float, not Any.

## Acceptance Criteria

1. mypy over the declared tree is clean. 2. NEGATIVE: tests/test_metrics_tier.py stays green and the returned values are unchanged.

## Plan

## Rollback

git revert

## Journal

- 2026-09-24T07:34:04Z [implementation] — AC-1: ✓ measurement — mypy: Success, no issues found (was: backend_tier_metrics.py:126 Returning Any). AC-2: ✓ tests/test_metrics_tier.py::test_calibration_is_the_median_of_the_last_30_with_its_spread — negative, 12 passed, values unchanged. Root cause: sorted() over row values typed Any; the quantile now wraps its result in float().
- 2026-09-24T07:35:21Z [implementation] — NO-DEAD-END: the red was bootstrap drift at close, cured by bootstrap; the fix itself was right first time.
